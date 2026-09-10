#!/usr/bin/env python3
"""Orchestrator for the rf-sweep-core link-quality test kit.

Drives two api_server.py nodes over HTTP (usually across a VPN) and measures
point-to-point link quality with tagged ping/pong exchanges. Varies one or
two radio parameters across explicit value lists while everything else stays
constant; every combination gets the same trial count and full per-trial stats.

Examples:
  # one variable: specific frequencies at fixed SF11/CR5/BW500
  orchestrate.py --vary freq=902.75,909.5,927.0 --sf 11 --bw 500 --cr 5 --trials 40

  # two variables: every combination (cross product)
  orchestrate.py --vary freq=909.5,927.0 --vary sf=9,10,11 --bw 500 --cr 5 --trials 40

On exit (including Ctrl-C) both nodes are restored to their startup radio
config and test mode is disabled.
"""

from __future__ import annotations

import argparse
import json
import math
import logging
import os
import random
import signal
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("rf-sweep-core")
logging.getLogger("httpx").setLevel(logging.WARNING)

HERE = Path(__file__).resolve().parent

# varied-key alias -> api config key
VARY_KEYS = {"freq": "frequency", "sf": "spreading_factor", "bw": "bandwidth",
             "cr": "coding_rate", "tx": "tx_power", "preamble": "preamble_length"}
CONFIG_KEYS = list(VARY_KEYS.values())
CONFIG_LABELS = {"frequency": "freq", "bandwidth": "bw",
                 "spreading_factor": "sf", "coding_rate": "cr",
                 "tx_power": "tx", "preamble_length": "pre"}


def load_env(path: str | Path) -> dict:
    path = Path(path)
    if not path.exists():
        raise SystemExit(f"Missing env file: {path}")
    values: dict[str, str] = {}
    for raw in path.read_text().splitlines():
        raw = raw.strip()
        if not raw or raw.startswith("#") or "=" not in raw:
            continue
        k, _, v = raw.partition("=")
        values[k.strip()] = v.strip()
    return values


class Node:
    def __init__(self, label: str, url: str, api_key: str):
        self.label = label
        self.url = url.rstrip("/")
        self.api_key = api_key
        self.baseline: dict = {}
        self.client = httpx.Client(timeout=60.0)

    def _headers(self) -> dict:
        return {"X-API-Key": self.api_key} if self.api_key else {}

    def stats(self) -> dict:
        r = self.client.get(f"{self.url}/api/stats", headers=self._headers())
        r.raise_for_status()
        return r.json()

    def set_test_mode(self, enabled: bool, payload_len: int | None = None) -> dict:
        body: dict = {"enabled": enabled}
        if payload_len is not None:
            body["payload_len"] = payload_len
        r = self.client.post(f"{self.url}/api/test-mode", json=body,
                             headers=self._headers())
        r.raise_for_status()
        return r.json()

    def send(self, payload_len: int, tag: int | None = None) -> dict:
        """Fire-and-forget: returns immediately after TX."""
        params = {"payload_len": payload_len}
        if tag is not None:
            params["tag"] = tag
        r = self.client.post(f"{self.url}/api/send", params=params,
                             headers=self._headers())
        r.raise_for_status()
        return r.json()

    def results(self, clear: bool = False) -> dict:
        r = self.client.get(f"{self.url}/api/results", params={"clear": clear},
                            headers=self._headers())
        r.raise_for_status()
        return r.json()

    def noise(self) -> float | None:
        r = self.client.get(f"{self.url}/api/noise", headers=self._headers())
        r.raise_for_status()
        return r.json().get("noise_floor_dbm")

    def clock(self) -> dict:
        r = self.client.get(f"{self.url}/api/clock", headers=self._headers())
        r.raise_for_status()
        return r.json()

    def apply_config(self, cfg: dict) -> dict:
        r = self.client.post(f"{self.url}/api/config", json=cfg, headers=self._headers())
        r.raise_for_status()
        return r.json()

    def ping(self, payload_len: int, timeout_s: float, sample_noise: bool) -> dict:
        r = self.client.post(
            f"{self.url}/api/ping",
            params={"payload_len": payload_len, "timeout_s": timeout_s,
                    "sample_noise": sample_noise},
            headers=self._headers())
        r.raise_for_status()
        return r.json()

    def close(self) -> None:
        self.client.close()


def lora_airtime_ms(payload_len: int, sf: int, bw_hz: int,
                    preamble: int = 32, cr: int = 5) -> float:
    """Theoretical LoRa airtime (explicit header, CRC on)."""
    ts_sym_ms = (2.0**sf / (bw_hz if bw_hz else 500000)) * 1000.0
    de = 1 if ts_sym_ms > 16.0 else 0
    n_payload = 8 + max(math.ceil((8 * payload_len - 4 * sf + 28 + 16) /
                                  (4 * (sf - 2 * de))) * (cr + 4), 0)
    n_bits = preamble + 4.25 + n_payload
    return n_bits * ts_sym_ms


def build_combos(args) -> list[dict]:
    fixed = {
        "frequency": round(args.freq * 1e6),
        "bandwidth": int(round(args.bw * 1e3)),
        "spreading_factor": args.sf,
        "coding_rate": args.cr,
        "tx_power": args.tx,
        "preamble_length": args.preamble,
    }
    varied: list[tuple[str, list]] = []
    for spec in args.vary or []:
        key, _, vals = spec.partition("=")
        key = key.strip().lower()
        if key not in VARY_KEYS:
            raise SystemExit(f"--vary key must be one of {sorted(VARY_KEYS)}")
        api_key = VARY_KEYS[key]
        if any(k == api_key for k, _ in varied):
            raise SystemExit(f"--vary {key} given twice")
        if api_key == "frequency":
            values = [round(float(v) * 1e6) for v in vals.split(",")]
        elif api_key == "bandwidth":
            values = [int(round(float(v) * 1e3)) for v in vals.split(",")]
        else:
            values = [int(v) for v in vals.split(",")]
        varied.append((api_key, values))
    if len(varied) > 2:
        raise SystemExit("at most 2 --vary axes supported")

    combos: list[dict] = []
    if not varied:
        combos.append(dict(fixed))
    elif len(varied) == 1:
        (k1, v1), = varied
        for a in v1:
            c = dict(fixed); c[k1] = a; combos.append(c)
    else:
        (k1, v1), (k2, v2) = varied
        for a in v1:
            for b in v2:
                c = dict(fixed); c[k1] = a; c[k2] = b; combos.append(c)
    return combos


def combo_label(cfg: dict) -> str:
    return (f"{cfg['frequency']/1e6:.3f} MHz, BW {cfg['bandwidth']/1e3:g} kHz, "
            f"SF{cfg['spreading_factor']}, CR4/{cfg['coding_rate']}, "
            f"{cfg['tx_power']} dBm, preamble {cfg['preamble_length']}")


class Orchestrator:
    def __init__(self, args, nodes: list[Node], combos: list[dict]):
        self.args = args
        self.nodes = nodes
        self.combos = combos
        self.results_dir = HERE / "results" / datetime.now(
            timezone.utc).strftime("%Y%m%d-%H%M%S")
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.raw_path = self.results_dir / "raw.jsonl"
        self._stop = False
        self.combo_results: list[str] = []
        self.combo_noise = [None, None]

    def _log_raw(self, obj: dict) -> None:
        with open(self.raw_path, "a") as f:
            f.write(json.dumps(obj) + "\n")

    def run(self) -> None:
        def handle_sigint(sig, frame):
            log.warning("Interrupted - will restore baseline and exit")
            self._stop = True
        import signal
        signal.signal(signal.SIGINT, handle_sigint)

        for n in self.nodes:
            s = n.stats()
            n.baseline = s["radio"]
            log.info("[%s] %.4f MHz, BW %g kHz, SF%d, CR4/%d, %d dBm, "
                     "noise %s dBm",
                     n.label, s["radio"]["frequency"] / 1e6,
                     s["radio"]["bandwidth"] / 1e3,
                     s["radio"]["spreading_factor"], s["radio"]["coding_rate"],
                     s["radio"]["tx_power"], s.get("noise_floor_dbm"))
        try:
            if self.args.mode == "oneway":
                # pure one-way: no node answers pings; both just record
                self.set_test_mode(False)
            else:
                self.set_test_mode(True)
            for idx, cfg in enumerate(self.combos):
                if self._stop:
                    break
                label = combo_label(cfg)
                log.info("=== combination %d/%d: %s ===",
                         idx + 1, len(self.combos), label)
                self.configure(cfg)
                self.run_combination(cfg, label)
        finally:
            self.restore_baseline()
            self.set_test_mode(False)
            for n in self.nodes:
                n.client.close()
        self.write_summary()
        log.info("Results in %s (analyze: python analyze.py %s)",
                 self.results_dir, self.results_dir.name)

    def configure(self, cfg: dict) -> None:
        for n in self.nodes:
            resp = n.apply_config(cfg)
            got = resp["radio"]
            for k in CONFIG_KEYS:
                got_v = got.get(k)
                if got_v is None:
                    continue  # modem build doesn't report this field back
                if int(got_v) != int(cfg[k]):
                    raise RuntimeError(
                        f"{n.label}: config mismatch for {k}: "
                        f"wanted {cfg[k]}, got {got.get(k)}")
        time.sleep(self.args.settle)
        # per-combination noise floors (sampled once, applies to all trials)
        self.combo_noise = [None, None]
        if not self.args.skip_noise:
            for idx, n in enumerate(self.nodes):
                vals = [v for v in (n.noise(), n.noise(), n.noise()) if v is not None]
                if vals:
                    self.combo_noise[idx] = round(sum(vals) / len(vals), 2)
        # clear stale results on both nodes
        for n in self.nodes:
            try:
                n.results(clear=True)
            except Exception:
                pass
        # clock offset between the two nodes (sandwich: A,B,B,A cancels
        # query-latency asymmetry to first order); offset = wall_B - wall_A
        pairs = []
        ca1 = self.nodes[0].clock()["wall_ms"]
        cb1 = self.nodes[1].clock()["wall_ms"]
        cb2 = self.nodes[1].clock()["wall_ms"]
        ca2 = self.nodes[0].clock()["wall_ms"]
        pairs.append((cb1, (ca1 + ca2) / 2))
        pairs.append(((cb1 + cb2) / 2, ca2))
        self.clock_offset_ms = round(
            sum(wb - wa for wb, wa in pairs) / len(pairs), 1)
        log.info("clock offset (node_b - node_a): %.1f ms", self.clock_offset_ms)

    def set_test_mode(self, enabled: bool) -> None:
        # node_b answers pings; node_a sends them
        try:
            self.nodes[1].set_test_mode(enabled, payload_len=self.args.payload_len)
        except Exception as e:
            log.warning("test-mode %s failed on %s: %s",
                        enabled, self.nodes[1].label, e)

    def restore_baseline(self) -> None:
        log.info("Restoring baseline radio settings on both nodes")
        for _ in range(3):
            ok = True
            for n in self.nodes:
                try:
                    n.apply_config(n.baseline)
                except Exception as e:
                    log.error("baseline restore failed on %s: %s", n.label, e)
                    ok = False
            if ok:
                return
            time.sleep(10)
        log.error("baseline restore incomplete")

    def one_trial(self, cfg: dict) -> dict:
        ts = datetime.now(timezone.utc).isoformat()
        row = {"timestamp": ts,
               "cfg_frequency_mhz": round(cfg["frequency"] / 1e6, 4),
               "cfg_bandwidth_khz": round(cfg["bandwidth"] / 1e3, 2),
               "cfg_spreading_factor": cfg["spreading_factor"],
               "cfg_coding_rate": cfg["coding_rate"],
               "cfg_tx_power_dbm": cfg["tx_power"],
               "cfg_preamble_length": cfg["preamble_length"],
               "ok": False, "rtt_ms": None, "snr_out": None, "snr_ret": None,
               "rssi_out": None, "rssi_ret": None, "noise_a_dbm": None,
               "noise_b_dbm": None, "timestamps_ms": None, "error": None}  # noise_a=before, b=None (after-sample is same node; B's noise comes from combo sampling in collect mode)
        try:
            resp = self.nodes[0].ping(self.args.payload_len, self.args.timeout,
                                      not self.args.skip_noise)
            row.update({
                "ok": resp.get("ok", False),
                "rtt_ms": resp.get("rtt_ms"),
                "snr_out": resp.get("snr_out"),
                "snr_ret": resp.get("snr_ret"),
                "rssi_out": resp.get("rssi_out"),
                "rssi_ret": resp.get("rssi_ret"),
                "noise_a_dbm": resp.get("noise_before_dbm"),
                "noise_b_dbm": None,
                "timestamps_ms": resp.get("timestamps_ms"),
                "error": resp.get("error"),
            })
        except Exception as e:
            row["error"] = f"{type(e).__name__}: {e}"
        return row

    def run_combination(self, cfg: dict, label: str) -> None:
        if self.args.mode == "oneway":
            self._run_oneway(cfg, label)
            return
        if self.args.mode == "collect":
            self._run_collect(cfg, label)
            return
        n = self.args.trials
        delay = self.args.burst_interval if self.args.burst else self.args.trial_delay
        successes = 0
        for i in range(n):
            if self._stop:
                break
            row = self.one_trial(cfg)
            successes += row["ok"]
            self._log_raw(row)
            log.info("trial %d/%d: ok=%s rtt=%sms snr_out=%s snr_ret=%s "
                     "rssi_out=%s %s",
                     i + 1, n, row["ok"], row["rtt_ms"], row["snr_out"],
                     row["snr_ret"], row["rssi_out"], row["error"] or "")
            if i < n - 1 and delay > 0:
                time.sleep(delay)
        log.info("%s: %d/%d successful", label, successes, n)
        self.combo_results.append(f"{label}: {successes}/{n}")

    def _run_oneway(self, cfg: dict, label: str) -> None:
        """Unidirectional: sender fires pings at airtime-rate, receiver passively
        records delivery + SNR. No pong, no round-trip collisions, half the
        airtime of ping/pong. Runs both directions per combination."""
        airtime = lora_airtime_ms(self.args.payload_len, cfg["spreading_factor"],
                                  cfg["bandwidth"], cfg["preamble_length"],
                                  cfg["coding_rate"])
        base_delay = self.args.burst_interval if self.args.burst else self.args.trial_delay
        delay = max(base_delay, airtime * 1.5 / 1000.0)
        passes = [("a2b", self.nodes[0], self.nodes[1], 1, 0),
                  ("b2a", self.nodes[1], self.nodes[0], 0, 1)]
        for direction, sender, receiver, noise_i, _ in passes:
            if self._stop:
                break
            # clear receiver results, then fire
            receiver.results(clear=True)
            log.info("[%s] sending %d one-way packets (%.0f ms airtime, "
                     "%.2f s spacing)", direction, self.args.trials, airtime, delay)
            tags = []  # (tag, tx_wall_ms)
            for i in range(self.args.trials):
                if self._stop:
                    break
                resp = sender.send(self.args.payload_len)
                if not resp.get("ok", False):
                    log.warning("send %d failed: %s", i + 1, resp.get("error"))
                    continue
                tags.append((resp["tag"], resp.get("tx_wall_ms")))
                if i < self.args.trials - 1:
                    time.sleep(delay)
            time.sleep(max(0.5, airtime / 1000.0))
            recs = {r["tag"]: r for r in receiver.results()["pings"]}
            delivered = 0
            for i, (tag, tx_wall) in enumerate(tags):
                rec = recs.get(tag)
                row = {"timestamp": datetime.now(timezone.utc).isoformat(),
                       "dir": direction,
                       "cfg_frequency_mhz": round(cfg["frequency"] / 1e6, 4),
                       "cfg_bandwidth_khz": round(cfg["bandwidth"] / 1e3, 2),
                       "cfg_spreading_factor": cfg["spreading_factor"],
                       "cfg_coding_rate": cfg["coding_rate"],
                       "cfg_tx_power_dbm": cfg["tx_power"],
                       "cfg_preamble_length": cfg["preamble_length"],
                       "ok": False, "rtt_ms": None, "oneway_ms": None,
                       "snr_out": None,
                       "snr_ret": None, "rssi_out": None, "rssi_ret": None,
                       "noise_a_dbm": self.combo_noise[0],
                       "noise_b_dbm": self.combo_noise[1],
                       "clock_offset_ms": self.clock_offset_ms,
                       "timestamps_ms": {"ping_tx_wall": tx_wall}, "error": None}
                if rec:
                    delivered += 1
                    row["ok"] = True
                    row["timestamps_ms"]["ping_rx_wall"] = rec["rx_wall"]
                    if direction == "a2b":
                        row["snr_out"], row["rssi_out"] = rec["snr"], rec["rssi"]
                        if tx_wall and rec.get("rx_wall"):
                            # subtract the node_b-minus-node_a clock offset
                            row["oneway_ms"] = round(
                                rec["rx_wall"] - tx_wall - self.clock_offset_ms, 1)
                    else:
                        row["snr_ret"], row["rssi_ret"] = rec["snr"], rec["rssi"]
                        if tx_wall and rec.get("rx_wall"):
                            row["oneway_ms"] = round(
                                rec["rx_wall"] - tx_wall + self.clock_offset_ms, 1)
                else:
                    row["error"] = "no_rx"
                self._log_raw(row)
                log.info("trial %d/%d: ok=%s oneway=%sms snr=%s %s",
                         i + 1, len(tags), row["ok"], row["oneway_ms"],
                         row["snr_out"] or row["snr_ret"], row["error"] or "")
            log.info("%s [%s]: %d/%d delivered", label, direction,
                     delivered, len(tags))
            self.combo_results.append(f"{label} [{direction}]: {delivered}/{len(tags)}")

    def _run_collect(self, cfg: dict, label: str) -> None:
        """Fire-and-collect: send all trials at send-rate (no blocking wait for
        pong), then collect passive results from both nodes and match by tag.
        A lost packet costs zero extra time."""
        a, b = self.nodes
        n = self.args.trials
        delay = self.args.burst_interval if self.args.burst else self.args.trial_delay
        sent: list[tuple[int, int]] = []  # (tag, tx_ms at node A)
        successes = 0
        for i in range(n):
            if self._stop:
                break
            resp = a.send(self.args.payload_len)
            if not resp.get("ok", False):
                log.warning("send %d failed: %s", i + 1, resp.get("error"))
                continue
            tag = resp["tag"]
            sent.append((tag, resp["tx_ms"]))
            if delay > 0:
                time.sleep(delay)
        # grace for the last packets in flight, then collect
        time.sleep(min(self.args.timeout, 3.0))
        ra, rb = a.results(), b.results()
        pongs = {r["tag"]: r for r in ra["pongs"]}
        pings = {r["tag"]: r for r in rb["pings"]}
        for i, (tag, tx_ms) in enumerate(sent):
            pong = pongs.get(tag)
            ping = pings.get(tag)
            row = {"timestamp": datetime.now(timezone.utc).isoformat(),
                   "cfg_frequency_mhz": round(cfg["frequency"] / 1e6, 4),
                   "cfg_bandwidth_khz": round(cfg["bandwidth"] / 1e3, 2),
                   "cfg_spreading_factor": cfg["spreading_factor"],
                   "cfg_coding_rate": cfg["coding_rate"],
                   "cfg_tx_power_dbm": cfg["tx_power"],
                   "cfg_preamble_length": cfg["preamble_length"],
                   "ok": False, "rtt_ms": None, "snr_out": None, "snr_ret": None,
                   "rssi_out": None, "rssi_ret": None,
                   "noise_a_dbm": self.combo_noise[0],
                   "noise_b_dbm": self.combo_noise[1],
                   "timestamps_ms": {"ping_tx": tx_ms}, "error": None}
            if ping:
                row["snr_out"] = ping["snr"]
                row["rssi_out"] = ping["rssi"]
                row["timestamps_ms"]["ping_rx_B"] = ping["rx_ms"]
            if pong:
                row["ok"] = True
                successes += 1
                row["rtt_ms"] = round(pong["rx_ms"] - tx_ms, 1)
                row["snr_ret"] = pong["snr"]
                row["rssi_ret"] = pong["rssi"]
                row["timestamps_ms"]["pong_rx_A"] = pong["rx_ms"]
            else:
                row["error"] = "pong_timeout" if ping else "timeout"
            self._log_raw(row)
            log.info("trial %d/%d: ok=%s rtt=%sms snr_out=%s snr_ret=%s "
                     "rssi_out=%s %s",
                     i + 1, len(sent), row["ok"], row["rtt_ms"], row["snr_out"],
                     row["snr_ret"], row["rssi_out"], row["error"] or "")
        log.info("%s: %d/%d successful", label, successes, len(sent))
        self.combo_results.append(f"{label}: {successes}/{len(sent)}")

    def write_summary(self) -> None:
        with open(self.results_dir / "summary.csv", "w") as f:
            f.write("combination,trials_ok\n")
            for line in self.combo_results:
                f.write(f'"{line}"\n')
        log.info("summary written to %s", self.results_dir / "summary.csv")


# ---------------------------------------------------------------- CLI


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--env-dir", type=Path, default=HERE)
    p.add_argument("--node-a", default="node_a.env", help="env file of origin node")
    p.add_argument("--node-b", default="node_b.env", help="env file of remote node")
    p.add_argument("--vary", action="append", default=[],
                   help="'key=v1,v2,...' — repeatable, max 2; keys: freq (MHz), "
                        "sf, bw (kHz), cr, tx (dBm), preamble")
    # constant radio settings (defaults = common 500k/SF10/CR4/5 test preset)
    p.add_argument("--freq", type=float, default=910.525, help="MHz (fixed when not varied)")
    p.add_argument("--sf", type=int, default=10)
    p.add_argument("--bw", type=float, default=500.0, help="kHz")
    p.add_argument("--cr", type=int, default=5, help="coding rate denominator (5 = CR4/5)")
    p.add_argument("--tx", type=int, default=22, help="dBm")
    p.add_argument("--preamble", type=int, default=32)
    p.add_argument("--trials", type=int, default=20)
    p.add_argument("--mode", choices=["oneway", "collect", "ping"], default="oneway",
                   help="oneway: unidirectional, airtime-rate, no collisions "
                        "(default, fastest); collect: fire-and-collect round "
                        "trips (spacing must exceed RTT); ping: legacy "
                        "blocking per-trial exchange")
    p.add_argument("--trial-delay", type=float, default=5.0,
                   help="seconds between trials")
    p.add_argument("--burst", action="store_true",
                   help="space trials at --burst-interval instead of --trial-delay")
    p.add_argument("--burst-interval", type=float, default=0.5, help="seconds")
    p.add_argument("--payload-len", type=int, default=40)
    p.add_argument("--timeout", type=float, default=10.0, help="per-ping timeout s")
    p.add_argument("--settle", type=float, default=3.0, help="wait after config change s")
    p.add_argument("--skip-noise", action="store_true",
                   help="skip noise-floor sampling per ping (faster)")
    args = p.parse_args()

    envs = [load_env(args.env_dir / name) for name in (args.node_a, args.node_b)]
    nodes = [Node("node_a", envs[0]["URL"], envs[0].get("API_KEY", "")),
             Node("node_b", envs[1]["URL"], envs[1].get("API_KEY", ""))]

    combos = build_combos(args)
    log.info("%d combination(s), %d trials each, payload %d B",
             len(combos), args.trials, args.payload_len)
    orch = Orchestrator(args, nodes, combos)
    orch.run()


if __name__ == "__main__":
    main()
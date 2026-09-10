#!/usr/bin/env python3
"""HTTP API server wrapping an openhop_modem via openhop_core's TCPLoRaRadio.

Runs on the computer co-located with each radio. Connects to the modem's
TCP interface (LAN/localhost), exposes a small REST surface for the
orchestrator, which reaches it over the VPN.

Endpoints (all X-API-Key auth unless noted):
  GET  /api/health     liveness, no auth
  GET  /api/stats      radio config, noise floor, modem status, counters
  POST /api/config     live radio reconfiguration (no reboot)
                       {frequency?, bandwidth?, spreading_factor?,
                        coding_rate?, tx_power?, preamble_length?}
                       (Hz / Hz / int / int / dBm / symbols)
  POST /api/test-mode  enable/disable automatic ping answering
  POST /api/ping       send tagged ping, wait for pong, return full
                       measurement bundle (both-direction SNR/RSSI, RTT,
                       noise floors, timestamps)

Test packet format (MeshCore sync word / preamble apply as configured;
timestamps are wall-clock epoch ms — hosts are NTP-synced, measured sync
~±6 ms; clock offset between nodes is measured per run and stored per row):
  ping:  magic(2) tag(4BE) tx_wall_ms(8BE) + zero padding to payload_len
  pong:  magic(2) tag(4BE) snr_q(1, quarter-dB int8) rssi(1, int8 dBm)
         ping_rx_wall_ms(8BE) pong_tx_wall_ms(8BE) + padding to payload_len

Both nodes passively record every received ping/pong (tag, SNR, RSSI,
rx_wall) into buffers served by GET /api/results — that is what the
fire-and-collect and one-way modes match on.

Units: frequency in Hz, bandwidth in Hz on the wire; orchestrate.py
converts from MHz/kHz.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import random
import struct
import threading
import time
from collections import deque
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
from typing import Optional

from pymc_core.hardware.tcp_radio import TCPLoRaRadio

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("rf-sweep-api")

PING_MAGIC = b"RF"  # origin -> remote
PONG_MAGIC = b"RG"  # remote -> origin
PING_HDR = struct.Struct(">2sIQ")            # magic, tag, tx_wall_ms
PONG_HDR = struct.Struct(">2sIbiQQ")         # magic, tag, snr_q, rssi, ping_rx_wall, pong_tx_wall
START_MONO = time.monotonic()

STATE: dict = {}  # populated in main(): radio, loop, magic, counters, queues


def now_ms() -> int:
    return int((time.monotonic() - START_MONO) * 1000) & 0xFFFFFFFF


def wall_ms() -> int:
    """Wall-clock epoch milliseconds (assumes NTP-synced hosts)."""
    return int(time.time() * 1000)


def load_env(path: str) -> dict:
    values: dict[str, str] = {}
    if path and os.path.exists(path):
        for raw in open(path):
            raw = raw.strip()
            if not raw or raw.startswith("#") or "=" not in raw:
                continue
            k, _, v = raw.partition("=")
            values[k.strip()] = v.strip()
    return values


# ---------------------------------------------------------------- radio glue


class FakeRadio:
    """Loopback radio for plumbing tests with no hardware.

    send() of a ping schedules a matching pong via the RX callback after a
    short fake delay. Same interface subset as TCPLoRaRadio.
    """

    def __init__(self, **kwargs) -> None:
        self._cb = None
        self._loop = None
        self.config = {
            "frequency": 910525000, "bandwidth": 500000, "spreading_factor": 10,
            "coding_rate": 5, "tx_power": 22, "preamble_length": 16,
            "sync_word": 0x12,
        }
        self.stats = {"pings_sent": 0, "pongs_sent": 0}

    def begin(self) -> bool:
        return True

    def set_event_loop(self, loop) -> None:
        self._loop = loop

    def set_rx_callback(self, cb) -> None:
        self._cb = cb

    async def send(self, data: bytes):
        await asyncio.sleep(0.01)
        if data[:2] == PING_MAGIC and self._cb:
            tag = struct.unpack_from(">I", data, 2)[0]
            snr = round(random.uniform(-12.0, -7.0), 2)
            rssi = -105
            rx_ms = now_ms() + random.randint(30, 90)
            pong = PONG_MAGIC + struct.pack(
                ">IbiII", tag, int(round(snr * 4)), rssi,
                rx_ms, rx_ms + 5)
            await asyncio.sleep(0.05)
            if self._loop:
                self._loop.call_soon_threadsafe(self._cb, pong)
            self.stats["pongs_sent"] += 1
        return {"success": True}

    async def refresh_noise_floor(self) -> Optional[float]:
        return -108.0 + random.uniform(-1.5, 1.5)

    def get_noise_floor(self) -> Optional[float]:
        return -108.0

    def get_last_rssi(self) -> int:
        return -105

    def get_last_snr(self) -> float:
        return -9.5

    def get_last_signal_rssi(self) -> int:
        return -104

    def get_status(self) -> dict:
        return dict(self.config)

    async def get_modem_status(self) -> dict:
        return {"fake": True}

    def check_radio_health(self) -> bool:
        return True

    def set_frequency(self, v): self.config["frequency"] = int(v); return True
    def set_tx_power(self, v): self.config["tx_power"] = int(v); return True
    def set_spreading_factor(self, v): self.config["spreading_factor"] = int(v); return True
    def set_bandwidth(self, v): self.config["bandwidth"] = int(v); return True
    def set_coding_rate(self, v): self.config["coding_rate"] = int(v); return True
    def set_preamble_length(self, v): self.config["preamble_length"] = int(v); return True
    def set_sync_word(self, v): self.config["sync_word"] = int(v); return True


def make_radio(args) -> object:
    if args.fake_radio:
        log.warning("FAKE RADIO MODE - loopback only, no hardware touched")
        return FakeRadio()
    from pymc_core.hardware.tcp_radio import TCPLoRaRadio
    return TCPLoRaRadio(
        host=args.modem_host, port=args.modem_port, token=args.modem_token,
        frequency=args.frequency, bandwidth=args.bandwidth,
        spreading_factor=args.spreading_factor, coding_rate=args.coding_rate,
        tx_power=args.tx_power, sync_word=args.sync_word,
        preamble_length=args.preamble_length,
    )


def on_rx(payload: bytes) -> None:
    """RX callback (runs in the radio driver's thread)."""
    st = STATE
    st["rx_total"] += 1
    if len(payload) < 6:
        st["rx_ignored"] += 1
        return
    magic = payload[:2]
    tag = struct.unpack_from(">I", payload, 2)[0]
    snr = st["radio"].get_last_snr()
    rssi = st["radio"].get_last_rssi()
    rx_ms = now_ms()
    rx_wall = wall_ms()

    if st["test_mode"] and magic == PING_MAGIC:
        st["pings_answered"] += 1
        pong = PONG_HDR.pack(
            PONG_MAGIC, tag, int(round(max(-31.75, min(31.75, snr)) * 4)),
            int(max(-128, min(127, rssi))), rx_wall, wall_ms())
        pong += b"\x00" * max(0, st["payload_len"] - len(pong))
        asyncio.run_coroutine_threadsafe(st["radio"].send(pong[:st["payload_len"]]),
                                         st["loop"])

    if magic == PONG_MAGIC:
        st["rx_total_pong"] += 1
        try:
            snr_q, rssi, ping_rx_wall, pong_tx_wall = struct.unpack_from(">biQQ", payload, 6)
        except struct.error:
            st["rx_ignored"] += 1
            return
        rec = {"tag": tag, "payload": payload, "snr_ret": snr, "rssi_ret": rssi,
               "ping_rx_wall": ping_rx_wall, "pong_tx_wall": pong_tx_wall,
               "rx_ms": rx_ms, "rx_wall": rx_wall}
        st["results_pongs"].append({"tag": tag, "snr": snr, "rssi": rssi,
                                    "rx_ms": rx_ms, "rx_wall": rx_wall})
        st["loop"].call_soon_threadsafe(st["queue"].put_nowait, rec)
    elif magic == PING_MAGIC:
        # passive record: out-direction measurement at this node
        st["results_pings"].append({"tag": tag, "snr": snr, "rssi": rssi,
                                    "rx_ms": rx_ms, "rx_wall": rx_wall})
        st["rx_ignored"] += 1
    else:
        st["rx_ignored"] += 1


async def wait_pong(tag: int, timeout_s: float) -> Optional[dict]:
    q: asyncio.Queue = STATE["queue"]
    deadline = time.monotonic() + timeout_s
    stray = 0
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return None
        try:
            rec = await asyncio.wait_for(q.get(), timeout=remaining)
        except asyncio.TimeoutError:
            return None
        if rec["tag"] == tag:
            rec["stray"] = stray
            return rec
        stray += 1  # wrong tag (stale), keep waiting


# ---------------------------------------------------------------- API models


class ConfigBody(BaseModel):
    frequency: Optional[int] = None          # Hz
    bandwidth: Optional[int] = None          # Hz
    spreading_factor: Optional[int] = None
    coding_rate: Optional[int] = None        # denominator, 5 = CR4/5
    tx_power: Optional[int] = None           # dBm
    preamble_length: Optional[int] = None


class TestModeBody(BaseModel):
    enabled: bool
    payload_len: Optional[int] = None


class PingBody(BaseModel):
    tag: Optional[int] = None
    payload_len: int = 40
    timeout_s: float = 5.0
    sample_noise: bool = True


app = FastAPI(title="rf-sweep-api", version="1.0")


def auth(x_api_key: Optional[str]) -> None:
    want = STATE["api_key"]
    if want and x_api_key != want:
        raise HTTPException(status_code=401, detail="bad api key")


@app.get("/api/health")
def health():
    return {"status": "ok", "label": STATE["label"], "uptime_ms": now_ms()}


@app.get("/api/stats")
async def stats(x_api_key: Optional[str] = Header(None)):
    auth(x_api_key)
    radio = STATE["radio"]
    modem: dict = {}
    ms = getattr(radio, "get_modem_status", None)
    if ms is not None:
        try:
            modem = ms() if not asyncio.iscoroutinefunction(ms) else await ms()
        except Exception as e:
            modem = {"error": str(e)}
    return {
        "label": STATE["label"],
        "radio": radio.get_status(),
        "noise_floor_dbm": radio.get_noise_floor(),
        "modem": modem,
        "counters": {
            "rx_total": STATE["rx_total"],
            "rx_pongs": STATE["rx_total_pong"],
            "rx_ignored": STATE["rx_ignored"],
            "pings_sent": STATE["pings_sent"],
            "pings_answered": STATE["pings_answered"],
            "test_mode": STATE["test_mode"],
        },
        "uptime_ms": now_ms(),
    }


@app.post("/api/config")
async def config(body: ConfigBody, x_api_key: Optional[str] = Header(None)):
    auth(x_api_key)
    radio = STATE["radio"]
    setters = {
        "frequency": radio.set_frequency,
        "bandwidth": radio.set_bandwidth,
        "spreading_factor": radio.set_spreading_factor,
        "coding_rate": radio.set_coding_rate,
        "tx_power": radio.set_tx_power,
        "preamble_length": radio.set_preamble_length,
    }
    applied = {}
    for key, setter in setters.items():
        v = getattr(body, key)
        if v is not None:
            setter(v)
            applied[key] = v
    log.info("config applied: %s", applied)
    return {"success": True, "applied": applied, "radio": radio.get_status()}


@app.get("/api/noise")
async def noise(x_api_key: Optional[str] = Header(None)):
    auth(x_api_key)
    nf = await STATE["radio"].refresh_noise_floor()
    return {"noise_floor_dbm": nf}


@app.get("/api/clock")
def clock(x_api_key: Optional[str] = Header(None)):
    auth(x_api_key)
    return {"mono_ms": now_ms(), "wall_ms": wall_ms()}


@app.post("/api/test-mode")
def test_mode(body: TestModeBody, x_api_key: Optional[str] = Header(None)):
    auth(x_api_key)
    STATE["test_mode"] = body.enabled
    if body.payload_len is not None:
        STATE["payload_len"] = body.payload_len
    log.info("test mode %s (payload_len=%s)",
             "ON" if body.enabled else "OFF", STATE["payload_len"])
    return {"success": True, "test_mode": STATE["test_mode"],
            "payload_len": STATE["payload_len"]}


@app.post("/api/send")
async def send(payload_len: int = 40, tag: Optional[int] = None,
               x_api_key: Optional[str] = Header(None)):
    """Fire-and-forget: transmit one ping packet, return immediately after TX.
    Results (at the remote node and the pong back here) are collected via
    /api/results and matched by tag."""
    auth(x_api_key)
    radio = STATE["radio"]
    tag = tag if tag is not None else random.getrandbits(32)
    tx_ms = now_ms()
    tx_wall = wall_ms()
    pkt = PING_HDR.pack(PING_MAGIC, tag, tx_wall)
    pkt += b"\x00" * max(0, payload_len - len(pkt))
    sent = await radio.send(pkt[:payload_len])
    if not sent or not sent.get("success", True):
        return {"ok": False, "tag": tag, "error": "tx_failed", "tx_ms": tx_ms}
    STATE["pings_sent"] += 1
    return {"ok": True, "tag": tag, "tx_ms": tx_ms, "tx_wall_ms": tx_wall}


@app.get("/api/results")
def results(since_ms: int = 0, clear: bool = False,
            x_api_key: Optional[str] = Header(None)):
    """Passively-captured packets this node received: pings (with our measured
    SNR/RSSI) and pongs. Filter client-side by tag; since_ms filters old runs."""
    auth(x_api_key)
    out = {
        "now_ms": now_ms(),
        "pings": [r for r in STATE["results_pings"] if r["rx_ms"] >= since_ms],
        "pongs": [r for r in STATE["results_pongs"] if r["rx_ms"] >= since_ms],
    }
    if clear:
        STATE["results_pings"].clear()
        STATE["results_pongs"].clear()
    return out


@app.post("/api/ping")
async def ping(payload_len: int = 40, timeout_s: float = 5.0,
               sample_noise: bool = True, x_api_key: Optional[str] = Header(None)):
    auth(x_api_key)
    radio = STATE["radio"]
    async with STATE["lock"]:
        tag = random.getrandbits(32)
        tx_ms = now_ms()
        pkt = PING_HDR.pack(PING_MAGIC, tag, tx_ms)
        pkt += b"\x00" * max(0, payload_len - len(pkt))
        nf_before = await radio.refresh_noise_floor() if sample_noise else None
        t0 = time.monotonic()
        sent = await radio.send(pkt[:payload_len])
        if not sent or not sent.get("success", True):
            return {"ok": False, "tag": tag, "error": "tx_failed",
                    "noise_before_dbm": nf_before}
        STATE["pings_sent"] += 1
        rec = await wait_pong(tag, timeout_s)
        rtt_ms = round((time.monotonic() - t0) * 1000.0, 1)
        nf_after = await radio.refresh_noise_floor() if sample_noise else None
        if rec is None:
            return {"ok": False, "tag": tag, "error": "timeout", "rtt_ms": None,
                    "noise_before_dbm": nf_before, "noise_after_dbm": None}
        return {
            "ok": True, "tag": tag, "rtt_ms": rtt_ms, "tx_wall_ms": tx_wall,
            "snr_out": rec["snr_ret"] / 4.0,      # B's measurement, reported in pong
            "rssi_out": rec["rssi_ret"],
            "snr_ret": radio.get_last_snr(),      # A's measurement of the pong
            "rssi_ret": radio.get_last_rssi(),
            "noise_before_dbm": nf_before,
            "noise_after_dbm": nf_after,
            "timestamps_ms": {"ping_tx_mono": tx_ms, "ping_tx_wall": tx_wall,
                              "ping_rx_B_wall": rec["ping_rx_wall"],
                              "pong_tx_B_wall": rec["pong_tx_wall"],
                              "pong_rx_A_mono": rec["rx_ms"]},
            "stray_pongs": rec["stray"],
        }


# ---------------------------------------------------------------- main


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--env", type=str, default="node_a.env",
                   help="env file with MODEM_*/API_* keys (default: node_a.env)")
    p.add_argument("--modem-host", default=None)
    p.add_argument("--modem-port", type=int, default=None)
    p.add_argument("--modem-token", default=None)
    p.add_argument("--bind", default=None, help="API bind address (default 127.0.0.1)")
    p.add_argument("--port", type=int, default=None, help="API port")
    p.add_argument("--api-key", default=None)
    p.add_argument("--label", default=None)
    p.add_argument("--frequency", type=int, default=910525000)
    p.add_argument("--bandwidth", type=int, default=500000)
    p.add_argument("--spreading-factor", type=int, default=10)
    p.add_argument("--coding-rate", type=int, default=5)
    p.add_argument("--tx-power", type=int, default=22)
    p.add_argument("--preamble-length", type=int, default=32)
    p.add_argument("--sync-word", type=lambda v: int(v, 0), default=0x12)
    p.add_argument("--fake-radio", action="store_true",
                   help="loopback mode: no hardware, answers own pings")
    args = p.parse_args()

    env = load_env(args.env)
    modem_host = args.modem_host or os.environ.get("MODEM_HOST") or env.get("MODEM_HOST", "127.0.0.1")
    modem_port = args.modem_port or int(env.get("MODEM_PORT", "5055"))
    modem_token = args.modem_token or os.environ.get("MODEM_TOKEN") or env.get("MODEM_TOKEN", "")
    args.modem_host, args.modem_port, args.modem_token = modem_host, modem_port, modem_token
    bind = args.bind or env.get("API_BIND", "127.0.0.1")
    port = args.port or int(env.get("API_PORT", "8080"))
    api_key = args.api_key or env.get("API_KEY", "")
    label = args.label or env.get("LABEL", os.path.basename(p.prog or "node"))

    STATE.update({
        "radio": None, "api_key": api_key, "label": label,
        "test_mode": False, "payload_len": 40,
        "rx_total": 0, "rx_total_pong": 0, "rx_ignored": 0,
        "pings_sent": 0, "pings_answered": 0,
        "queue": asyncio.Queue(), "lock": asyncio.Lock(),
        "results_pings": deque(maxlen=2000),   # pings THIS node received
        "results_pongs": deque(maxlen=2000),   # pongs THIS node received
    })
    STATE["radio"] = make_radio(args)

    async def run() -> None:
        loop = asyncio.get_running_loop()
        STATE["loop"] = loop
        radio = STATE["radio"]
        if not radio.begin():
            raise SystemExit("radio begin() failed")
        radio.set_event_loop(loop)
        radio.set_rx_callback(on_rx)
        cfg = radio.get_status()
        log.info("[%s] radio up: %.4f MHz, BW %g kHz, SF%d, CR4/%d, %d dBm, preamble %d",
                 label, cfg["frequency"] / 1e6, cfg["bandwidth"] / 1e3,
                 cfg["spreading_factor"], cfg["coding_rate"], cfg["tx_power"],
                 cfg.get("preamble_length", 0))
        serve_cfg = uvicorn.Config(app, host=bind, port=port, log_level="warning")
        await uvicorn.Server(serve_cfg).serve()

    try:
        asyncio.run(run())
    finally:
        try:
            STATE["radio"].cleanup()
        except Exception:
            pass


if __name__ == "__main__":
    main()
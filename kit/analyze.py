#!/usr/bin/env python3
"""Per-trial analysis of an orchestrate.py results directory.

Reads raw.jsonl, auto-detects which radio parameters were varied, and
prints detailed statistics per combination:

  - reliability (ok / total) and failure streaks
  - SNR per trial (out = measured at node B, ret = measured at node A on
    the pong): mean, sigma, min
  - RTT percentiles: p50 / p95 / max
  - RSSI and noise-floor means for context

Usage:
  python analyze.py results/<timestamp>
  python analyze.py results/<timestamp> --min-rel 90
  python analyze.py results/<timestamp> --by frequency,spreading_factor
"""

from __future__ import annotations

import argparse
import json
import statistics as st
from collections import defaultdict
from pathlib import Path

PARAM_ORDER = [
    ("cfg_frequency_mhz", "freq"),
    ("cfg_spreading_factor", "sf"),
    ("cfg_bandwidth_khz", "bw"),
    ("cfg_coding_rate", "cr"),
    ("cfg_tx_power_dbm", "tx"),
    ("cfg_preamble_length", "pre"),
]


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("results_dir", help="results/<timestamp> dir with raw.jsonl")
    p.add_argument("--min-rel", type=float, default=0.0,
                   help="only show combinations with reliability >= this percent")
    p.add_argument("--by", type=str, default=None,
                   help="comma list of params to group by (default: auto-detect "
                        "which ones vary); names: freq,sf,bw,cr,tx,pre")
    args = p.parse_args()

    raw = Path(args.results_dir) / "raw.jsonl"
    if not raw.exists():
        raise SystemExit(f"No raw.jsonl in {args.results_dir}")

    groups: dict[tuple, dict] = defaultdict(lambda: {
        "snr_out": [], "snr_ret": [], "rssi_out": [], "rssi_ret": [],
        "rtt": [], "noise_a": [], "noise_b": [], "seq": []})
    values_by_param: dict[str, set] = defaultdict(set)

    for line in open(raw):
        r = json.loads(line)
        if "ok" not in r:
            continue
        gkey = tuple(r.get(k) for k, _ in PARAM_ORDER) + (r.get("dir"),)
        g = groups[gkey]
        for k, _ in PARAM_ORDER:
            values_by_param[k].add(r.get(k))
        values_by_param["dir"].add(r.get("dir"))
        g["snr_out"].append(r["snr_out"])
        g["snr_ret"].append(r["snr_ret"])
        g["rssi_out"].append(r["rssi_out"])
        g["rssi_ret"].append(r["rssi_ret"])
        g["rtt"].append(r["rtt_ms"])
        g["seq"].append(bool(r["ok"]))

    if args.by:
        names = [n.strip() for n in args.by.split(",")]
        aliases = {alias: key for key, alias in PARAM_ORDER}
        group_keys = [aliases[n] for n in names]
    else:
        group_keys = [k for k, _ in PARAM_ORDER if len(values_by_param[k]) > 1]
        if len(values_by_param["dir"]) > 1:
            group_keys.append("dir")
        if not group_keys:
            group_keys = [k for k, _ in PARAM_ORDER] + ["dir"]

    def fmt(v, nd=2):
        return f"{v:.{nd}f}" if isinstance(v, (int, float)) else "-"

    hdr = (f"{'combination':<38} {'ok':>6} {'rel%':>5} "
           f"{'SNRout':>7} {'sd':>5} {'min':>7} {'SNRret':>7} {'sd':>5} "
           f"{'RTT50':>7} {'RTT95':>7} {'RTTmax':>7}")
    print(hdr)
    print("-" * len(hdr))
    for gkey, g in groups.items():
        row = dict(zip([k for k, _ in PARAM_ORDER], gkey))
        lab = " ".join(f"{alias}={row[key]}"
                       for key, alias in PARAM_ORDER if key in group_keys)
        if "dir" in group_keys:
            lab += f" dir={gkey[-1]}"
        ok = sum(g["seq"])
        n = len(g["seq"])
        rel = 100.0 * ok / n if n else 0.0
        if rel < args.min_rel:
            continue
        so = [v for v in g["snr_out"] if v is not None]
        sr = [v for v in g["snr_ret"] if v is not None]
        rt = [v for v in g["rtt"] if v is not None]
        rt_sorted = sorted(rt)
        p50 = rt_sorted[len(rt_sorted) // 2] if rt else None
        p95 = rt_sorted[min(len(rt_sorted) - 1, int(len(rt_sorted) * 0.95))] if rt else None
        so_m = st.mean(so) if so else None
        so_sd = st.stdev(so) if len(so) > 1 else None
        so_min = min(so) if so else None
        sr_m = st.mean(sr) if sr else None
        sr_sd = st.stdev(sr) if len(sr) > 1 else None
        print(f"{lab:<38} {ok:>3}/{n:<3} {rel:>5.1f} "
              f"{fmt(so_m):>7} {fmt(so_sd):>5} {fmt(so_min):>7} "
              f"{fmt(sr_m):>7} {fmt(sr_sd):>5} "
              f"{fmt(p50, 0):>7} {fmt(p95, 0):>7} {fmt(max(rt_sorted) if rt_sorted else None, 0):>7}")

    print("\nFailure streaks (isolated 1s = deep fades; long runs = interference):")
    for gkey, g in groups.items():
        row = dict(zip([k for k, _ in PARAM_ORDER], gkey))
        lab = " ".join(f"{alias}={row[key]}"
                       for key, alias in PARAM_ORDER if key in group_keys)
        if "dir" in group_keys:
            lab += f" dir={gkey[-1]}"
        runs, cur = [], 0
        for ok in g["seq"]:
            if not ok:
                cur += 1
            elif cur:
                runs.append(cur)
                cur = 0
        if cur:
            runs.append(cur)
        n_fail = n = len(g["seq"]) - sum(g["seq"])
        print(f"  {lab:<38} failures={n_fail:>2}  streaks={runs if runs else 'none'}")


if __name__ == "__main__":
    main()
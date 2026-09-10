#!/usr/bin/env python3
"""Plots for a Run-1 frequency sweep (oneway mode raw.jsonl).

Usage: python make_plots.py <results_dir>
Writes PNGs into <results_dir>/plots/.
"""
from __future__ import annotations

import collections
import json
import math
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

# LoRa demod SNR floors (dB), independent of bandwidth
SNR_FLOOR = {7: -7.5, 8: -10.0, 9: -12.5, 10: -15.0, 11: -17.5, 12: -20.0}
SFS = [7, 8, 9, 10, 11, 12]


def lora_airtime_ms(payload_len: int, sf: int, bw_hz: int,
                    preamble: int = 32, cr: int = 5) -> float:
    ts_sym_ms = (2.0 ** sf / bw_hz) * 1000.0
    de = 1 if ts_sym_ms > 16.0 else 0
    n_payload = 8 + max(math.ceil((8 * payload_len - 4 * sf + 28 + 16) /
                                  (4 * (sf - 2 * de))) * (cr + 4), 0)
    n_bits = preamble + 4.25 + n_payload
    return n_bits * ts_sym_ms


def pct(vals, p):
    s = sorted(vals)
    k = (len(s) - 1) * p / 100.0
    f = int(k)
    return s[f] + (s[min(f + 1, len(s) - 1)] - s[f]) * (k - f)


def main(results_dir: Path, ref_dir: Path | None = None,
         title: str = "", node_a: str = "node A", node_b: str = "node B",
         fig_formats: list[str] | None = None) -> None:
    rows = [json.loads(l) for l in (results_dir / "raw.jsonl").open()]
    freqs = sorted({r["cfg_frequency_mhz"] for r in rows})
    out = results_dir / ("plots_with_defaults" if ref_dir else "plots")
    out.mkdir(exist_ok=True)
    fig_formats = fig_formats or ["png"]

    # ---- aggregate ------------------------------------------------------
    # delivery[(freq,sf,dir)] = [oks, total]
    delivery = collections.defaultdict(lambda: [0, 0])
    # snr[(freq,sf,dir)] = list of delivered SNRs
    snr = collections.defaultdict(list)
    # latency[(sf,dir)] = list of oneway_ms
    lat = collections.defaultdict(list)
    for r in rows:
        d = r.get("dir")
        if d not in ("a2b", "b2a"):
            continue
        key = (r["cfg_frequency_mhz"], r["cfg_spreading_factor"], d)
        delivery[key][0] += 1 if r["ok"] else 0
        delivery[key][1] += 1
        if r["ok"]:
            s = r["snr_out"] if d == "a2b" else r["snr_ret"]
            if s is not None:
                snr[key].append(s)
            if r.get("oneway_ms") is not None:
                lat[(r["cfg_spreading_factor"], d)].append(r["oneway_ms"])

    if not title:
        title = (f"{node_a}↔{node_b}, BW 500 kHz, CR4/5, 22 dBm, preamble 32, "
                 "40 B payload, 20 trials/direction")
    colors = plt.cm.viridis([i / (len(SFS) - 1) for i in range(len(SFS))])

    def save(fig, name):
        for fmt in fig_formats:
            fig.savefig(out / f"{name}.{fmt}", dpi=140, format=fmt)
        plt.close(fig)

    # ---- US-defaults reference run (optional) ----------------------------
    ref = None
    if ref_dir:
        rrows = [json.loads(l) for l in (ref_dir / "raw.jsonl").open()]
        ref = {"deliv": {}, "snr": {}, "lat": {}}
        for d in ("a2b", "b2a"):
            rs = [r for r in rrows if r.get("dir") == d]
            ref["deliv"][d] = 100 * sum(1 for r in rs if r["ok"]) / len(rs)
            snrs = [(r["snr_out"] if d == "a2b" else r["snr_ret"])
                    for r in rs if r["ok"]]
            ref["snr"][d] = sum(snrs) / len(snrs)
            ref["lat"][d] = [r["oneway_ms"] for r in rs
                             if r["ok"] and r.get("oneway_ms") is not None]
        ref["margin"] = min(ref["snr"][d] - SNR_FLOOR[7]
                            for d in ("a2b", "b2a"))
        ref["label"] = ("US default (910.525 MHz, SF7, "
                        "BW 62.5 kHz, CR4/5, 100 trials/dir)")
    colors = plt.cm.viridis([i / (len(SFS) - 1) for i in range(len(SFS))])

    def style(ax, xlab=True):
        ax.set_xlim(freqs[0] - 0.5, freqs[-1] + 0.5)
        ax.grid(alpha=0.3)
        if xlab:
            ax.set_xlabel("Center frequency (MHz)")

    # ---- 1. reliability vs frequency ------------------------------------
    fig, axes = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
    for ax, d, lab in zip(axes, ("a2b", "b2a"),
                          (f"{node_a} → {node_b} (a2b)",
                           f"{node_b} → {node_a} (b2a)")):
        for c, sf in zip(colors, SFS):
            ys = [100 * delivery[(f, sf, d)][0] / delivery[(f, sf, d)][1]
                  if delivery[(f, sf, d)][1] else float("nan") for f in freqs]
            ax.plot(freqs, ys, "-o", ms=3.5, lw=1.3, color=c, label=f"SF{sf}")
        ax.set_ylabel("Delivery (%)")
        ax.set_ylim(-4, 104)
        ax.set_title(lab, fontsize=10, loc="left")
        if ref:
            v = ref["deliv"][d]
            ax.axhline(v, color="crimson", ls="--", lw=1.2)
            ax.text(freqs[0] + 0.15, v + 1.5,
                    f"{ref['label']}: {v:.0f}%", color="crimson", fontsize=8)
        style(ax, xlab=(d == "b2a"))
    axes[0].legend(ncol=6, fontsize=9, loc="lower right")
    fig.suptitle("Reliability vs frequency (delivery rate)")
    fig.text(0.5, 0.005, title, ha="center", fontsize=8, alpha=0.6)
    fig.tight_layout(rect=(0, 0.02, 1, 0.97))
    save(fig, "reliability_vs_freq")

    # ---- 1b. reliability vs frequency, SFs combined ----------------------
    fig, ax = plt.subplots(figsize=(12, 5.5))
    for d, lab, col in (("a2b", f"{node_a} → {node_b}", "tab:blue"),
                        ("b2a", f"{node_b} → {node_a}", "tab:orange")):
        ys = []
        for f in freqs:
            ok = tot = 0
            for sf in SFS:
                o, t = delivery[(f, sf, d)]
                ok += o
                tot += t
            ys.append(100 * ok / tot if tot else float("nan"))
        ax.plot(freqs, ys, "-o", ms=3.5, lw=1.5, color=col,
                label=f"{lab} (SF7–12 pooled, n≈120 per freq)")
    if ref:
        for d, col in (("a2b", "tab:blue"), ("b2a", "tab:orange")):
            v = ref["deliv"][d]
            ax.axhline(v, color=col, ls="--", lw=1.3, alpha=0.8)
            ax.text(freqs[-1] - 0.55, v + 1.5, f"{ref['label']}: {v:.0f}%",
                    color=col, fontsize=8, ha="right")
    ax.set_ylabel("Delivery (%)")
    ax.set_ylim(-4, 104)
    ax.set_title("Reliability vs frequency (all spreading factors combined)")
    ax.legend(fontsize=9, loc="lower right")
    style(ax)
    fig.text(0.5, 0.005, title, ha="center", fontsize=8, alpha=0.6)
    fig.tight_layout(rect=(0, 0.02, 1, 1))
    save(fig, "reliability_vs_freq_all_sf")

    # ---- 2. SNR vs frequency --------------------------------------------
    fig, ax = plt.subplots(figsize=(12, 5.5))
    for d, lab, col in (("a2b", f"{node_a} → {node_b} (snr at {node_b})",
                         "tab:blue"),
                        ("b2a", f"{node_b} → {node_a} (snr at {node_a})",
                         "tab:orange")):
        ys, los, his = [], [], []
        for f in freqs:
            vals = [x for sf in SFS for x in snr[(f, sf, d)]]
            ys.append(sum(vals) / len(vals) if vals else float("nan"))
            los.append(ys[-1] - (pct(vals, 10) if vals else 0))
            his.append((pct(vals, 90) if vals else 0) - ys[-1])
        ax.errorbar(freqs, ys, yerr=[los, his], fmt="-o", ms=3.5, lw=1.5,
                    color=col, capsize=2, label=f"{lab}, mean ± p10–p90 (SF7–12)")
    ax.set_ylabel("SNR (dB)")
    ax.set_title("SNR vs frequency (all delivered packets, SF7–12 pooled)")
    if ref:
        offs = {"a2b": 0.4, "b2a": -1.1}
        for d, col in (("a2b", "tab:blue"), ("b2a", "tab:orange")):
            v = ref["snr"][d]
            ax.axhline(v, color=col, ls="--", lw=1.3, alpha=0.8)
            ax.text(freqs[-1] - 0.1, v + offs[d],
                    f"US default ({d}): {v:.1f} dB (62.5 kHz — 9 dB lower "
                    "noise floor)", color=col, fontsize=8, ha="right")
    ax.legend(fontsize=9, loc="lower left")
    style(ax)
    fig.text(0.5, 0.005, title, ha="center", fontsize=8, alpha=0.6)
    fig.tight_layout(rect=(0, 0.02, 1, 1))
    save(fig, "snr_vs_freq")

    # ---- 3. link margin vs frequency ------------------------------------
    fig, ax = plt.subplots(figsize=(12, 5.5))
    for c, sf in zip(colors[2:], (9, 10, 11, 12)):
        ys = []
        for f in freqs:
            per_dir = []
            for d in ("a2b", "b2a"):
                vals = snr[(f, sf, d)]
                if vals:
                    per_dir.append(sum(vals) / len(vals) - SNR_FLOOR[sf])
            ys.append(min(per_dir) if per_dir else float("nan"))
        ax.plot(freqs, ys, "-o", ms=3.5, lw=1.3, color=c, label=f"SF{sf}")
    ax.axhline(0, color="red", ls="--", lw=1, alpha=0.7)
    ax.text(freqs[0] + 0.2, 0.4, "demod floor (worst direction)", color="red",
            fontsize=8)
    if ref:
        v = ref["margin"]
        ax.axhline(v, color="crimson", ls="--", lw=1.3, alpha=0.8)
        ax.text(freqs[-1] - 0.1, v + 0.25,
                f" {ref['label']}: {v:.1f} dB margin",
                color="crimson", fontsize=8, ha="right")
    ax.set_ylabel("Link margin (dB)")
    ax.set_title("Link margin vs frequency — mean SNR − demod floor, "
                 "worst direction")
    ax.legend(ncol=4, fontsize=9)
    style(ax)
    fig.text(0.5, 0.005, title, ha="center", fontsize=8, alpha=0.6)
    fig.tight_layout(rect=(0, 0.02, 1, 1))
    save(fig, "link_margin_vs_freq")

    # ---- 4. latency vs SF ------------------------------------------------
    fig, ax = plt.subplots(figsize=(11, 5.5))
    span = (len(SFS) + 1) * 1.0
    for i, sf in enumerate(SFS):
        for j, (d, col) in enumerate((("a2b", "tab:blue"), ("b2a", "tab:orange"))):
            vals = lat[(sf, d)]
            if not vals:
                continue
            pos = i * 1.0 + (j - 0.5) * 0.38
            bp = ax.boxplot(vals, positions=[pos], widths=0.34, showfliers=True,
                            flierprops=dict(marker=".", ms=3, alpha=0.5),
                            medianprops=dict(color="black", lw=1.2),
                            patch_artist=True)
            bp["boxes"][0].set(facecolor=col, alpha=0.55, edgecolor=col)
        at = lora_airtime_ms(40, sf, 500_000)
        ax.plot([i - 0.5, i + 0.5], [at, at], color="green", lw=1.4,
                ls=":", zorder=0)
        ax.text(i + 0.52, at, f"{at:.0f} ms air", color="green", fontsize=7.5,
                va="center")
    if ref:
        for j, (d, col) in enumerate((("a2b", "tab:green"),
                                      ("b2a", "tab:red"))):
            bp = ax.boxplot(ref["lat"][d], positions=[-0.85 + j * 0.38],
                            widths=0.34, showfliers=True,
                            flierprops=dict(marker=".", ms=3, alpha=0.5),
                            medianprops=dict(color="black", lw=1.2),
                            patch_artist=True)
            bp["boxes"][0].set(facecolor=col, alpha=0.55, edgecolor=col)
        ax.legend(handles=[mpatches.Patch(color="tab:green", alpha=0.55,
                                          label=f"US default {node_a[0]}→{node_b[0]} (62.5 kHz)"),
                           mpatches.Patch(color="tab:red", alpha=0.55,
                                          label=f"US default {node_b[0]}→{node_a[0]} (62.5 kHz)")],
                  fontsize=8, loc="upper left")
    ax.set_xticks(range(len(SFS)))
    ax.set_xticklabels([f"SF{s}" for s in SFS])
    ax.set_yscale("log")
    ax.set_ylabel("One-way latency (ms, log scale)")
    ax.set_title("One-way latency vs spreading factor (BW 500 kHz) — "
                 f"blue: {node_a}→{node_b}, orange: {node_b}→{node_a}")
    ax.grid(alpha=0.3, which="both", axis="y")
    fig.text(0.5, 0.005, title, ha="center", fontsize=8, alpha=0.6)
    fig.tight_layout(rect=(0, 0.02, 1, 1))
    save(fig, "latency_vs_sf")

    # console rundown
    print("latency rundown (ms, p50 / p90 / max):")
    print(f"{'SF':>4} {'a2b':>22} {'b2a':>22} {'airtime':>8}")
    for sf in SFS:
        cells = []
        for d in ("a2b", "b2a"):
            v = lat[(sf, d)]
            cells.append(f"{pct(v,50):7.0f}/{pct(v,90):7.0f}/{max(v):7.0f}"
                         if v else f"{'-':>22}")
        print(f"{sf:>4} {cells[0]:>22} {cells[1]:>22} "
              f"{lora_airtime_ms(40, sf, 500_000):7.0f}")
    print(f"\nplots written to {out}")


if __name__ == "__main__":
    args = sys.argv[1:]
    opts = {"--title": "", "--node-a": "node A", "--node-b": "node B",
            "--fig-format": "png"}
    positional: list[str] = []
    i = 0
    while i < len(args):
        if args[i] in opts and i + 1 < len(args):
            opts[args[i]] = args[i + 1]
            i += 2
        else:
            positional.append(args[i])
            i += 1
    ref = Path(positional[1]) if len(positional) > 1 else None
    main(Path(positional[0]) if positional else Path("."), ref,
         title=opts["--title"], node_a=opts["--node-a"],
         node_b=opts["--node-b"],
         fig_formats=opts["--fig-format"].split(","))

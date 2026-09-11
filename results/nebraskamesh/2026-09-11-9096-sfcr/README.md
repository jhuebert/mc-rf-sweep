# SF×CR selection at 909.6 MHz — single-pass + bursts (SF10/11 × CR4/5/4/8)

**Mesh:** NebraskaMesh · **Date:** 2026-09-11 (morning, 08:53–09:25 CDT) · **Location:** Bellevue, NE, USA
**Path:** indoor XIAO WIO ↔ gazebo Heltec v4.2, ~3.9 mi — see the [mesh README](../README.md)
**Companion campaigns:** [band sweep](../2026-09-10-902-928-band-sweep/), [fine sweep](../2026-09-10-fine-sweep/), [overnight SF×CR](../2026-09-11-sf-cr-campaign/)

## TL;DR

- **Recommended operating point: 909.6 MHz (or 909.1 — see fine-tune), SF10, CR4/5.**
  SF11 loses decisively at this frequency: its ~2× airtime gives each packet
  double the exposure to the minute-scale interference windows that plague
  909.6's b2a direction, and no CR rescues it. SF10/CR4/5 pooled worst-direction
  60%, SF10/CR4/8 51%, SF11/CR4/8 49%, SF11/CR4/5 16%.
- **CR4/8 did not help this morning.** In the overnight campaign CR8 rescued
  marginal cells; this morning's interference is additive burst noise, not
  marginal-SNR loss — mean SNR of delivered b2a packets was healthy (−11 to
  −13 dB) and losses were hard cutoffs (0/20 chunks), which FEC cannot buy back.
- **SF11's penalty is airtime, not sensitivity.** SF11 b2a died earliest in the
  SF ladder (3/20 by trial 20) despite the +2.5 dB demod advantage; longer
  packets simply collide with more interference windows.
- **US-defaults control (same session, 09:13): 92% / 94%** at 910.525/62.5k/SF7.
  The channel was fine for the narrow-BW defaults while 909.6's 500 kHz b2a
  collapsed — the interference is inside our 500 kHz window and minute-scale.

## Test setup

Identical to the [fine-sweep campaign](../2026-09-10-fine-sweep/) (same nodes,
antennas, path, 22 dBm TX). Single pass, run interactively. Noise floors stable
at aries ≈ −101 dBm; lynx swung −74.8 to −95.3 (the −74.8 readings are
instantaneous noise-sample spikes, likely AMI/ISM bursts, not sustained).

## Method

`oneway` mode, 40 B payload, 22 dBm, preamble 32, BW 500 kHz:

1. **SF×CR matrix** — 909.6 × {SF10, SF11} × {CR4/5, CR4/8}, 100 trials/direction
   (sequential: SF10/CR5 → SF10/CR8 → SF11/CR5 → SF11/CR8, each a2b then b2a).
2. **US-defaults control** — 910.525 MHz / 62.5 kHz / SF7 / CR4/5, 50/dir.
3. **Bursts** — all 4 combos, 60 trials/direction, minimum legal spacing
   (auto-raised to 1.5× airtime for SF11).

Command shape:

```
python orchestrate.py --mode oneway --bw 500 --tx 22 --preamble 32 \
  --payload-len 40 --trials 100 --trial-delay 0.5 --settle 3 \
  --freq 909.6 --vary sf=10,11 --vary cr=5,8
```

## Results

### Matrix + bursts pooled (n=160/direction per cell)

| Config | a2b | b2a | Worst | One-way p50/p90 |
|---|---:|---:|---:|---|
| **SF10 CR4/5** | 146/160 (91.2%) | 96/160 (60.0%) | **60.0%** | 291 / 808 ms |
| SF10 CR4/8 | 143/160 (89.4%) | 82/160 (51.2%) | 51.2% | 372 / 1112 ms |
| SF11 CR4/8 | 141/160 (88.1%) | 78/159 (49.1%) | 49.1% | 640 / 1683 ms |
| SF11 CR4/5 | 151/160 (94.4%) | 25/160 (15.6%) | 15.6% | 446 / 1235 ms |

### Time structure of the b2a failure (matrix, 20-trial chunks)

| Config | per-20 delivery |
|---|---|
| SF10/CR5 b2a | 19, 19, **0, 0, 0** |
| SF10/CR8 b2a | 19, 20, **4, 0, 0** |
| SF11/CR5 b2a | **3, 3, 0, 0, 0** |
| SF11/CR8 b2a | 19, **3, 0, 0, 0** |

Every b2a run started healthy (~19/20) then hit a hard cutoff. a2b never
collapsed (17–20 per chunk throughout). The interference sits at the indoor
node (aries) and arrives on minute scales — the same mode the overnight
campaign caught twice.

### Bursts (60/dir, 0.5 s spacing; 15 min after the matrix)

| Config | a2b | b2a | worst b2a loss streak |
|---|---:|---:|---:|
| SF10/CR5 | 55/60 | 58/60 | 1 |
| SF10/CR8 | 53/60 | 39/60 | 17 |
| SF11/CR5 | 56/60 | 19/60 | 20 |
| SF11/CR8 | 53/60 | 56/60 | 3 |

Recovery within 15 minutes from 38/100 → 58/60 (SF10/CR5 b2a) confirms the
windows are transient, not a static channel property. Note CR8's rescue of
SF11 b2a (19 → 56) when the window missed the run.

## Findings

1. **SF10/CR4/5 wins on worst-direction delivery and airtime.** Any 500 kHz
   MeshCore channel here will suffer minute-scale interference windows; the
   optimal config minimizes per-packet airtime while keeping the link budget.
   SF10/CR4/5 delivers 257 ms/40 B packets at 1248 bit/s payload throughput —
   1.22× the US defaults' rate.
2. **SF11 is not a good trade on this path.** Its +2.5 dB link budget is worth
   nothing against burst interference, and its 476–574 ms packets double the
   per-packet collision exposure. This is the opposite conclusion from the
   quiet overnight window, where SF11 was never tested — an overnight SF11
   retest would be fair, but the daytime reality is what most traffic lives in.
3. **CR4/8's value is conditional.** Overnight (marginal-SNR losses) CR8 bought
   +25 pp at SF8; this morning (burst interference) it bought nothing on SF10
   and cost airtime. If the deployment must tolerate both loss modes, CR4/6 is
   the compromise the overnight data already endorsed at SF10.
4. **The defaults control outperformed every 500 kHz cell on b2a this
   morning** (47/50 at 62.5 kHz vs 38–43/100 at 500 kHz, an hour earlier).
   Narrow bandwidth sees a fraction of the wideband interference our 500 kHz
   window does. Part 15 compliance and interference robustness are in direct
   tension on this channel.
5. **Timing note:** this is a single morning pass by design (see plan). The
   pooled numbers mix clean and hit-by-window cells; use the time-structure
   table, not the pooled worst-direction, to read this campaign.

## Data

| File | Contents |
|---|---|
| `data/sf-cr-matrix-raw.jsonl.gz` | 799 one-way trials (4 combos × 2 dirs × 100) |
| `data/sf-cr-bursts-raw.jsonl.gz` | 476 burst trials (4 combos × 2 dirs × 60) |
| `data/us-defaults-control-raw.jsonl.gz` | 100 control trials (910.525/62.5k/SF7) |
| `data/matrix-summary.csv` | Per-combination delivery counts |
| `plots/reliability_by_sf_cr.png` | Matrix+burst pooled delivery by SF×CR |
| `RUN-MANIFEST.md` | Phase → kit results-directory map |
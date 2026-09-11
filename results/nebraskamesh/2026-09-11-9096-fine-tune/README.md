# 909.6 fine-tune — 0.05 MHz grid around the incumbent, with 909.1 confirmation

**Mesh:** NebraskaMesh · **Date:** 2026-09-11 (morning, 09:25–10:06 CDT) · **Location:** Bellevue, NE, USA
**Path:** indoor XIAO WIO ↔ gazebo Heltec v4.2, ~3.9 mi — see the [mesh README](../README.md)
**Companion campaigns:** [fine sweep](../2026-09-10-fine-sweep/) (0.1 MHz, previous day), [SF×CR campaign](../2026-09-11-9096-sfcr/) (same morning, earlier)

## TL;DR

- **Frequency recommendation revised: 909.1 MHz.** The 0.05 MHz grid around
  909.6 revealed an extremely lumpy b2a landscape (2%→96% between adjacent
  0.05 MHz neighbors), and the two top candidates separated cleanly in a
  same-session head-to-head: **909.1 at 93.5% worst-direction beat 909.6 at
  87%**, and held 94.8% worst-direction pooled across three independent runs
  (n=210/dir) vs 909.6's 90.0% (n=260/dir).
- **The sub-0.1 MHz structure is real, not just windows:** within one 25-minute
  grid pass, 909.65's b2a (45/100) sat between two strong neighbors (909.6 96%,
  909.7 95%) — time-varying windows alone can't explain that alternation;
  narrowband interferers land in different places inside each 500 kHz window.
- **909.7 is not a peak** — its 95/100 b2a grid score collapsed to 34/60 in the
  immediate burst re-test. Small-n windows on this channel flatter
  frequencies; the same trap that demoted 923.0 and briefly 909.6.
- **Ham-neighbor check:** both 909.1 (window 908.85–909.35) and 909.6
  (909.35–909.85) remain ~6 MHz clear of the ham 902–903.4 and 927–928
  segments (see the [claim-validation note](../../rf-sweep-core-kit/PLAN-9096-SFCR-REFINE.md)
  in the plan file) — the good-neighbor argument holds at either center.

## Test setup

Identical to the [SF×CR campaign](../2026-09-11-9096-sfcr/) earlier the same
morning (same nodes, antennas, path, 22 dBm TX, 40 B, preamble 32). Config
fixed at the SF×CR winner **SF10 / CR4/5** for continuity with the 0.1 MHz
fine sweep.

## Method

`oneway` mode, sequential:

1. **Grid** — 909.45–909.75 in 0.05 MHz steps (7 freqs × 100 trials/dir).
2. **Anchor** — 909.1 (fine-sweep rank 2), 50/dir.
3. **Bursts** — top-2 grid freqs (909.6, 909.7), 60/dir.
4. **Head-to-head** — 909.6 vs 909.1 back-to-back in one run, 100/dir each
   (decision gate: 909.1 beat 909.6 pooled by >3 pp → confirm before switching).
5. **Anchor burst** — 909.1, 60/dir.

## Results

### Grid (SF10/CR4/5, n=100/dir, sequential ~2 min per cell)

| Freq (MHz) | a2b | b2a | Worst |
|---:|---:|---:|---:|
| 909.45 | 95/100 | **2/100** | 2% |
| 909.50 | 93/100 | 66/100 | 66% |
| 909.55 | 90/100 | 44/100 | 44% |
| **909.60** | 90/100 | 96/100 | **90%** |
| 909.65 | 87/100 | 45/100 | 45% |
| 909.70 | 82/100 | 95/100 | 82% |
| 909.75 | 87/100 | **12/100** | 12% |

The b2a column alternates strongly-good/strong-bad across neighbors — a
frequency-selective pattern, since the cells ran back-to-back over 25 minutes.

### 909.1 confirmation (three runs, three windows)

| Run | a2b | b2a |
|---|---:|---:|
| Anchor (n=50/dir) | 50/50 | 49/50 |
| Head-to-head (n=100/dir) | 92/100 | 95/100 |
| Burst (n=60/dir) | 57/60 | 57/60 |
| **Pooled** | **199/210 (94.8%)** | **201/210 (95.7%)** |

### 909.6 full-morning record (SF10/CR4/5, n=420/dir across all runs)

| Direction | Delivered | Rate |
|---|---:|---:|
| a2b | 380/420 | 90.5% |
| b2a | 344/420 | 81.9% |

In the same-session head-to-head (the cleanest comparison):

| Freq | a2b | b2a | Worst |
|---:|---:|---:|---:|
| 909.6 | 87/100 | 92/100 | 87% |
| **909.1** | 92/100 | 95/100 | **93.5%** |

Mean SNR of delivered packets was near-identical between the two (909.6:
−10.4/−12.5 dB a2b/b2a; 909.1: −11.8/−13.0 dB) — the delta is not an SNR-story;
it is where narrowband interference lands inside the 500 kHz window.

## Findings

1. **Switch the NebraskaMesh recommended center from 909.6 to 909.1.**
   Decision gate met: a neighbor won pooled by >3 pp and survived the
   confirmation head-to-head + burst. 909.1 was already fine-sweep rank 2
   (85% worst at n=40); at n=210/dir it led all morning at 94.8%.
2. **Keep 909.6 as the backup.** Its clean-window performance is excellent
   (96/100 b2a grid, 60/60 b2a burst) and it remains the fine-tune incumbent.
   With two strong centers 0.5 MHz apart, a mesh could even spread across both.
3. **0.05 MHz resolution is meaningful but must be time-controlled.** Adjacent
   cells differ by up to 94 pp; single sequential passes cannot separate
   frequency-selective structure from minute-scale windows. Any future
   sub-0.1 MHz work should interleave frequencies or run multi-pass.
4. **The 909.x ridge stays the home.** Both ends of the tested neighborhood
   (909.1 and 909.6) out-deliver the middle; there is no single narrow spike,
   just a 1 MHz ridge with two clean centers and bumpy flanks.

## Data

| File | Contents |
|---|---|
| `data/freq-grid-raw.jsonl.gz` | 1,397 trials (7 freqs × 2 dirs × 100) |
| `data/anchor-909.1-raw.jsonl.gz` | 100 anchor trials |
| `data/top2-bursts-raw.jsonl.gz` | 239 burst trials (909.6, 909.7) |
| `data/head2head-raw.jsonl.gz` | 394 head-to-head trials (909.6 vs 909.1) |
| `data/anchor-burst-raw.jsonl.gz` | 117 burst trials at 909.1 |
| `data/grid-summary.csv` | Per-combination grid delivery counts |
| `plots/reliability_vs_freq.png` | Grid delivery per frequency (both directions) |
| `RUN-MANIFEST.md` | Phase → kit results-directory map |
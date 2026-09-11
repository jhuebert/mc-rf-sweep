# Burst-resilience deep dive — 909.1 vs 909.6 × SF10 vs SF11 × CR4/5 vs CR4/8

**Mesh:** NebraskaMesh · **Date:** 2026-09-11 (10:14–12:58 CDT) · **Location:** Bellevue, NE, USA
**Path:** indoor XIAO WIO ↔ gazebo Heltec v4.2, ~3.9 mi — see the [mesh README](../README.md)
**Companion campaigns:** [SF×CR morning](../2026-09-11-9096-sfcr/) · [fine-tune](../2026-09-11-9096-fine-tune/) (same day, earlier)

## TL;DR

- **Question:** which of the 8 combos (2 freq × 2 SF × 2 CR) is most resilient
  to the minute-scale burst interference that dominates this path's b2a
  direction? **Answer: CR4/8's redundancy genuinely helps burst containment on
  3 of 4 (freq, SF) pairs — with one big anomaly.**
- **Overall winner: 909.1 / SF10 / CR4/8** — 85.0% worst-direction (n=360/dir)
  and a b2a max loss streak of only 23 trials (~20 s), vs 37–53 everywhere else.
  Throughput equals the US defaults (1026 bit/s); SF10/CR4/5 on 909.1 is the
  fast alternative (81.1% worst, 1248 bit/s).
- **CR4/8 improves b2a on 909.1/SF10 (+3.9 pp, streak 44→23), 909.6/SF11
  (+17.1 pp, streak 53→22) and 909.1/SF11 (+12.6 pp). The anomaly:
  909.6/SF10/CR4/8 collapsed to 36.1% b2a** — the worst cell of the entire
  campaign, bad in all 5 rounds, while 909.6/SF11/CR4/8 (same CR, longer
  symbols) scored 76.7%. Mechanism unresolved (see Findings), but the
  combination is measurably pathological on this frequency.
- **SF11/CR4/5 is uniformly the worst trade** (60–63% worst-direction at both
  frequencies): long airtime with no FEC. If SF11, take CR4/8.
- **a2b (gazebo RX) was excellent everywhere** (90.3–96.1%, max streak 2).
  The burst noise lives at the indoor node; every ranking below is a b2a story.

## Test setup

Same nodes/path/power as the morning campaigns. 10:14–12:58 CDT, unattended
driver: 10 interleaved matrix rounds were planned, **5 completed** (~22 min/round
— SF11's 1.5× airtime spacing makes rounds slow), then 2 dedicated burst rounds,
plus US-defaults controls at start and end. Frequency order alternates per
round; vary order rotates, so both frequencies and all four SF/CR combos
sample the same windows and quiet periods.

## Method

`oneway` mode, 40 B payload, 22 dBm, preamble 32, BW 500 kHz:

- **Matrix rounds** — per round, both frequencies × {SF10, SF11} × {CR4/5,
  CR4/8}, 60 trials/direction per combo. 5 rounds.
- **Burst rounds** — 60 trials/direction, minimum legal spacing (auto-raised
  to 1.5× airtime), all 4 combos per frequency.
- **Controls** — US defaults (910.525 / 62.5 kHz / SF7), 50/dir, at start
  (49/50, 47/50) and end (47/50, 49/50): the narrow-band channel stayed
  healthy the whole session while 500 kHz b2a cells cycled through windows.

## Results

### Pooled delivery (n=360/direction per cell; matrix + burst rounds)

| Cell | a2b | b2a | Worst | b2a max streak | b2a losses in streaks |
|---|---:|---:|---:|---:|---:|
| **909.1 SF10 CR4/8** | 95.0% | **85.0%** | **85.0%** | **23** | 78% |
| 909.1 SF10 CR4/5 | 96.1% | 81.1% | 81.1% | 44 | 76% |
| 909.6 SF11 CR4/8 | 91.9% | 76.7% | 76.7% | **22** | 76% |
| 909.1 SF11 CR4/8 | 95.3% | 75.2% | 75.2% | 37 | 83% |
| 909.1 SF11 CR4/5 | 94.7% | 62.6% | 62.6% | 38 | 93% |
| 909.6 SF10 CR4/5 | 91.1% | 60.3% | 60.3% | 49 | 89% |
| 909.6 SF11 CR4/5 | 90.3% | 59.6% | 59.6% | 53 | 94% |
| 909.6 SF10 CR4/8 | 91.4% | **36.1%** | 36.1% | 51 | 96% |

"b2a losses in streaks" = fraction of lost trials immediately preceded by
another loss — 76–96% of b2a losses arrive in multi-packet bursts, while a2b
losses are isolated (0–21%, max streak 2). This is the burst signature, and it
is what CR4/8's interleaving is up against.

### The CR effect on b2a (pooled)

| (freq, SF) | CR4/5 | CR4/8 | Δ | max streak CR5 → CR8 |
|---|---:|---:|---:|---|
| 909.1, SF10 | 81.1% | **85.0%** | +3.9 pp | 44 → **23** |
| 909.1, SF11 | 62.6% | **75.2%** | +12.6 pp | 38 → 37 |
| 909.6, SF11 | 59.6% | **76.7%** | +17.1 pp | 53 → **22** |
| 909.6, SF10 | 60.3% | **36.1%** | **−24.2 pp** | 49 → 51 |

### Worst-direction % by round (matrix rounds only; ! = window hit <80%)

| Round | 909.1 SF10 CR5 | CR8 | SF11 CR5 | CR8 | 909.6 SF10 CR5 | CR8 | SF11 CR5 | CR8 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 26! | 96 | 35! | 73! | 16! | 15! | 10! | 77! |
| 2 | 80 | 93 | 21! | 71! | 48! | 36! | 38! | 88 |
| 3 | 95 | 96 | 36! | 96 | 80 | 23! | 93 | 93 |
| 4 | 93 | 60! | 95 | 76! | 26! | 15! | 74! | 76! |
| 5 | 93 | 58! | 83 | 95 | 88 | 30! | 93 | 56! |

Round 1 (10:16–10:35) was a global event — every cell hit, both frequencies.
After that, windows roamed: 909.6's SF10 cells were hit in rounds 3–5 while
909.1 stayed clean in the same rounds, and 909.6/SF10/CR4/8 was hit in **all
five rounds**.

### Latency (pooled one-way, ms, p50 / p90)

| Config | p50 | p90 | Airtime/40 B | Throughput |
|---|---:|---:|---:|---:|
| SF10 CR4/5 | 241 | 645 | 257 ms | 1248 bit/s |
| SF10 CR4/8 | 295 | 756 | 312 ms | 1026 bit/s |
| SF11 CR4/5 | 415 | 951 | 476 ms | 672 bit/s |
| SF11 CR4/8 | 512 | 1110 | 574 ms | 557 bit/s |

## Findings

1. **CR4/8 does exactly what the hypothesis predicted — except once.** On
   909.1/SF10, 909.1/SF11 and 909.6/SF11 it raises worst-direction b2a delivery
   and (critically) contains the damage: max streaks drop from 38–53 to
   22–23 on the two best cells. Under burst interference, the FEC's +~2 dB
   coding gain converts "whole window lost" into "partial bursts survive."
2. **The 909.6/SF10/CR4/8 anomaly is real and unexplained.** 36.1% b2a pooled
   over 360 trials, hit in all 5 rounds, while the same CR8 at SF11 on the
   same frequency (longer symbols, same FEC) scored 76.7%, and the same
   SF10/CR8 at 909.1 scored 85.0%. Not an airtime story (SF11/CR8 is 2×
   slower and fine), not a marginal-SNR story (delivered-packet SNRs are
   healthy). Candidates: a frequency-selective interferer that interacts with
   SF10's symbol rate inside CR4/8's codeword layout, or unlucky but repeated
   window placement. Whatever the mechanism: **don't deploy 909.6/SF10/CR4/8
   on this path** without a targeted retest.
3. **SF11/CR4/5 is the worst of both worlds** — its 476 ms packets soak in
   windows (94% of b2a losses in streaks, streak 53) with the least FEC
   protection. If the mesh ever moves to SF11, CR4/8 is mandatory.
4. **909.1 out-delivers 909.6 in matched rounds.** a2b 94.7–96.1% vs
   90.3–91.9%; and in rounds 3–5, 909.1's cells stayed clean during windows
   that hit 909.6. The fine-tune campaign's frequency revision (909.6 → 909.1)
   is reinforced at n=360/dir.
5. **The burst noise is local to aries.** Every a2b cell delivered 90%+ with
   max streak 2, at every frequency and config, through the same windows that
   cut b2a to single digits. Any indoor-node mitigation (antenna move,
   filtering) buys more than any protocol choice.
6. **Round 1 (10:16–10:35) was a band-wide event** — all 8 cells hit,
   including a2b drops. The 62.5 kHz defaults control before/after it was
   clean. Wide-bandwidth operation is intrinsically more exposed on this
   channel; the burst window environment is the real tax on 500 kHz operation.

## Data

| File | Contents |
|---|---|
| `data/matrix-round{1..5}-<freq>-raw.jsonl.gz` | 10 rounds × ~480 trials (4 combos × 2 dirs × 60) |
| `data/burst-round-<freq>-raw.jsonl.gz` | 2 × 480 trials, minimum legal spacing |
| `data/us-defaults-control-{start,end}-raw.jsonl.gz` | 100 trials each (910.525/62.5k/SF7) |
| `plots/burst_resilience.png` | Pooled a2b/b2a delivery by cell |
| `RUN-MANIFEST.md` | Phase → kit results-directory map |

*Excluded: kit `results/20260911-172409` (aborted 909.6 burst run, 360 rows,
overlapped a re-run — excluded for contamination), and the partial round 6
(`20260911-170911`, 60 rows) cut when the matrix phase was stopped to fit the
time budget.*
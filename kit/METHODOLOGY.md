# Testing methodology — direct-to-core edition

The same campaign shape as the repeater-based kit, but faster cycles (no
reboots) and richer per-packet data unlock a few phases the repeater route
couldn't do. Trial counts assume 500 kHz BW; halve the bandwidth = double
the airtime.

## Phase 0 — plumbing

1. Start both API servers, run `orchestrate.py --trials 2 --trial-delay 0`
   at your known-good preset. One clean ping proves: modems reachable,
   config applied on both sides, test mode on, pings answered, stats
   flowing. (Or rehearse everything with `--fake-radio` first.)
2. Capture the baseline config — the orchestrator restores it on exit.

## Phase 1 — channel scan (no traffic needed)

For each candidate frequency: sample noise floor ~10x and CAD-busy rate at
both nodes (sampled via `/api/stats` while idle). This takes seconds per
frequency and eliminates hopeless channels before spending airtime.
High noise / busy CAD at one end = skip; that frequency loses no matter
how good the path is.

## Phase 2 — screening sweep

    --vary freq=<whole band on 0.25 MHz grid> --sf 10 --bw 500 --cr 5 --trials 10

Rank by reliability. 10 trials is enough to rank, not to conclude.

## Phase 3 — deep pass on the shortlist

Top ~8 frequencies, same settings, 40 trials + one burst:

    --burst --trials 50 --burst-interval 0.5

Bursts capture fade correlation: spaced trials average over fades, bursts
reveal 2-second holes. A frequency with 90% spaced-reliability but
5-in-a-row burst losses is worse than the percentage suggests.

## Phase 4 — the SF ladder (link budget)

    --vary sf=11,10,9,8,7 --vary freq=<top 2-3> --trials 40

Expect a cliff, not a slope. Track per-frequency: where the cliff sits,
and how SNR relates to failures (failures at SNR close to the demod floor
= budget exhausted; failures with SNR unchanged = interference).

## Phase 5 — secondary-axis micro-sweeps (unique to direct-core)

On the top 2–3 frequencies, one axis at a time:

- `--vary tx=2,8,14,22 --trials 20` — real link-budget curve per frequency;
  the dB where reliability collapses is your true fade margin
- `--vary preamble=8,16,32 --trials 20` — airtime vs acquisition robustness
- `--vary payload=20,40,60 --trials 20` — sensitivity to production packet
  sizes (longer packets spend more time in fades)

## Phase 6 — diurnal confirmation

Interference is heavily time-dependent. Loop the top 3–4 candidates over a
full day (the orchestrator can be driven by cron/systemd timer):

    --vary freq=<top candidates> --sf <chosen> --trials 20

every 2 h for 24 h. Frequencies that shine at 3 a.m. and die at 8 p.m.
exist in every ISM band; find out before committing.

## Phase 7 — the long test

Top two candidates, one session, 100+ trials each, plus a final burst each.
96–97% at n=100 with isolated-single failure streaks is a deployable
number.

## Rules of thumb (same lessons as the repeater campaign, plus new ones)

1. n=20 screens, n=40 decisions, n=100 commitments.
2. Never compare runs from different sessions head-to-head; put candidates
   in one orchestrator run instead.
3. Watch both SNR directions: snr_out (B's RX) and snr_ret (A's measurement)
   differ when the two sites have different noise floors — the difference
   itself is diagnostic.
4. A setting that wins at high SNR but has streaky failures is worse than a
   boring one with tight σ and lonely failures.
5. Burst results trump spaced-trial percentages when they disagree: bursts
   measure hole *duration*, not just hole *frequency*.
6. CAD-busy rate and noise floor from Phase 1 should be re-sampled during
   any surprising result — the environment changes, the modem config
   doesn't.
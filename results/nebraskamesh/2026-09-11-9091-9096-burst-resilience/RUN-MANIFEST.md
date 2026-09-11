# Campaign manifest — burst-resilience deep dive (2026-09-11, 10:14–12:58 CDT)

Driver: /tmp/burst-campaign.sh (10 matrix rounds planned, stopped after 5 to
fit the 1–2 h budget; SF11 spacing made rounds ~22 min).

- **defaults control (start)** → `rf-sweep-core-kit/results/20260911-151434`
- **matrix round 1** — 909.1: `20260911-151602` · 909.6: `20260911-152701`
- **matrix round 2** — 909.6: `20260911-153833` · 909.1: `20260911-155013`
- **matrix round 3** — 909.1: `20260911-160128` · 909.6: `20260911-161248`
- **matrix round 4** — 909.6: `20260911-162433` · 909.1: `20260911-163559`
- **matrix round 5** — 909.1: `20260911-164641` · 909.6: `20260911-165744`
- ~~partial round 6 (909.6 only, aborted)~~ → `20260911-170911` (60 rows; excluded)
- **burst round 909.1** → `20260911-171240`
- ~~burst round 909.6 (aborted; overlapped re-run)~~ → `20260911-172409` (excluded)
- **burst round 909.6 (clean re-run)** → `20260911-173251` (superseded by 174629; excluded)
- **burst round 909.6 (final clean)** → `20260911-174629`
- **defaults control (end)** → `20260911-174430`

All runs: oneway mode, 40 B payload, 22 dBm, preamble 32, BW 500 kHz.
Total ≈ 11,300 trials.
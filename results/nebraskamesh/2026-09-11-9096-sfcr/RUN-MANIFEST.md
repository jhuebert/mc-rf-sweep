# Campaign manifest — 909.6 SF×CR (2026-09-11 morning)

Single-pass campaign (per Jason's direction: no multi-pass time-of-day spread).

- **smoke** → `rf-sweep-core-kit/results/20260911-135027`
- **sf_cr_matrix** (909.6 × SF10,11 × CR5,8 × 100/dir) → `20260911-135301`
- ~~aborted first attempt~~ (interrupted, no data written) → `20260911-135038`
- **us_defaults_control** (910.525 / 62.5 kHz / SF7 / CR5, 50/dir) → `20260911-141216`
- **sf_cr_bursts** (4 combos × 60/dir, 0.5 s spacing) → `20260911-141346`

All runs: oneway mode, payload 40 B, 22 dBm, preamble 32, BW 500 kHz.
Winner carried into the fine-tune campaign: **SF10 / CR4/5**.
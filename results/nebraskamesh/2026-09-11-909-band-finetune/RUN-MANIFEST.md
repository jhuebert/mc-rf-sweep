# Campaign manifest — 909 band fine-tune (2026-09-11, 13:25–16:32 CDT)

Driver: `rf-sweep-core-kit/finetune_909.py` (4 interleaved passes over
909.00–909.75 @ 0.05, rotated/reversed order; automated burst retests).
All runs: oneway mode, 40 B payload, 22 dBm, preamble 32, BW 500 kHz, SF10,
CR4/8. Total ≈ 10,100 trials.

- **pass 1** → `rf-sweep-core-kit/results/20260911-183231`
- **pass 2** → `20260911-190752`
- **pass 3** → `20260911-194352`
- **pass 4** → `20260911-201917`
- **retest 1** (8 flagged + 2 controls) → `20260911-205527`
- **retest 2** → `20260911-211412`

Aggregation note: the driver crashed at final-report aggregation (float+str
bug) and its in-memory stats also overwrote phases instead of pooling them,
so real-time flagging/retest selection used pass-4 data only. All tables in
the README are rebuilt from the raw per-trial logs above via
`rf-sweep-core-kit/recover_909.py` (raw data unaffected). Pooled ranking and
REPORT.md also in `rf-sweep-core-kit/finetune909/`.

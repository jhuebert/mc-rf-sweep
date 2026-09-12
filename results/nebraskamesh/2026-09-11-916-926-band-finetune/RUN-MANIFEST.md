# Campaign manifest — 916/926 band fine-tune + SF sweep (2026-09-11, 16:43–21:51 CDT)

Driver: `rf-sweep-core-kit/finetune_sweep.py --grid 916.30:916.90:0.05
--grid 926.00:926.50:0.05 --freqs 909.10 --out finetune916-926`
(4 interleaved passes, rotated/reversed order; automated burst retests of
flagged cells + 2 controls). All runs: oneway mode, 40 B payload, 22 dBm,
preamble 32, BW 500 kHz, SF10, CR4/8 (SF sweep varies SF). Total ≈ 15,000
trials.

- **pass 1** → `rf-sweep-core-kit/results/20260911-214259`
- **pass 2** → `20260911-224322`
- **pass 3** → `20260911-234200`
- **pass 4** → `20260912-004315`
- **retest 1** (8 flagged 916.x + 909.10 + 2 controls) → `20260912-014324`
- **retest 2** → `20260912-020747`
- **SF sweep** (916.70 + 926.05 × SF9/10/11) → `20260912-023437`

Note: the campaign was restarted 16:43 after an aggregation bug was found and
fixed in the driver (`analyze_pass` phase-key overwrite; a partial first pass
~16:33–16:42 was discarded). Final aggregation and burst flagging pooled all
six phases correctly. Pooled ranking and REPORT.md also in
`rf-sweep-core-kit/finetune916-926/`.

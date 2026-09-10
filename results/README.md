# Results

One folder per mesh, one folder per campaign. Each campaign folder is
self-contained: a written report, the plots, and the raw data.

    results/
    ├── SUMMARY.md              ← cross-mesh comparison table (add a row!)
    ├── TEMPLATE.md             ← report template — copy this
    └── <mesh-name>/
        ├── README.md           ← your test setup, nodes, antennas, location
        └── <YYYY-MM-DD-campaign>/
            ├── README.md       ← the report
            ├── plots/          ← svg (vector) + png (chat-friendly)
            └── data/           ← raw.jsonl.gz + summary.csv

## Adding your mesh's results

1. Run the **standard band sweep** and the **US-defaults baseline**
   (exact commands in the [root README](../README.md)) so your numbers
   are comparable with everyone else's.
2. Create `results/<your-mesh>/README.md` describing your setup
   (use [`nebraskamesh/README.md`](nebraskamesh/README.md) as an example).
3. Copy the campaign folder from your kit's `results/<timestamp>/`,
   then write the report following [`TEMPLATE.md`](TEMPLATE.md).
   Plots: SVG preferred (vector, crisp on GitHub); add PNG too if you
   want chat-friendly copies.
4. Add one row per campaign to [`SUMMARY.md`](SUMMARY.md).
5. Open a PR.

## Conventions

- **Mesh/folder names:** lowercase, no spaces (`nebraskamesh`).
- **Campaign folders:** `YYYY-MM-DD-<what>` (e.g. `2026-09-10-902-928-band-sweep`).
- **Never commit real credentials** — no env files, API keys, or tokens.
  Raw `raw.jsonl` data is fine (timestamps, SNR, noise floors only).
- Report the conditions you have; don't pad. Weather, seasonal foliage,
  and time of day all matter — note what you know.

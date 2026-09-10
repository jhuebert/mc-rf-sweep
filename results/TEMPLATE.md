# <Campaign name — e.g. 902–928 MHz band sweep, 500 kHz, SF7–12>

**Mesh:** <mesh name> · **Date:** <YYYY-MM-DD> · **Location:** <city, state/region>
**Author:** <name / callsign>

## TL;DR

<3–6 bullets: best frequencies, worst frequencies, the SF cliff location,
defaults-baseline comparison, anything surprising.>

## Test setup

<Short description; full details live in the mesh README. Include: node
hardware, antennas, heights, indoor/outdoor, distance, TX power.>

| | Node A (initiator) | Node B (responder) |
|---|---|---|
| Hardware | <...> | <...> |
| Antenna | <...> | <...> |
| Placement | <...> | <...> |
| TX power | <...> dBm | <...> dBm |

Path length: <...> · Time window: <start>–<end> local (UTC−X)
Weather/conditions: <what you observed; "not recorded" is OK>

## Method

- Orchestrator: oneway mode (unidirectional pings, passive reception,
  airtime-spaced — losses cost nothing)
- Constant: BW <...>, CR 4/<...>, TX <...> dBm, preamble <...>, payload <...> B
- Swept: frequency <list/grid> × SF <list>
- Trials: <n> per direction per combination (<total> packets)
- Runtime: <duration>
- Noise floors sampled per combination; clock offset measured per combination

```
<the exact orchestrate.py command>
```

## Results

### Delivery ladder

<Full table, one row per frequency, columns per SF, cells `a2b/b2a` out
of <n>.>

### Ranking

<Table ranked by worst-direction delivery across the discriminating SFs;
note which SFs were used and why.>

![Reliability vs frequency](plots/reliability_vs_freq.svg)
![Reliability vs frequency, SFs pooled](plots/reliability_vs_freq_all_sf.svg)
![SNR vs frequency](plots/snr_vs_freq.svg)
![Link margin vs frequency](plots/link_margin_vs_freq.svg)
![Latency vs SF](plots/latency_vs_sf.svg)

### Baseline: US defaults

<910.525 MHz, BW 62.5 kHz, SF7, CR4/5 — the common MeshCore US default —
run at the same site for reference. Table + one paragraph.>

## Findings

<Numbered discussion: what won, what died, whether failures looked like
interference (high noise floor) or path loss (quiet floor), direction
asymmetries, latency behavior, caveats (session duration, season,
weather, single sample in time).>

## Data

| File | Contents |
|---|---|
| `data/<name>-raw.jsonl.gz` | One JSON line per trial (config, ok, SNR, RSSI, noise, timestamps) |
| `data/summary.csv` | Per-combination delivery counts |

`zcat data/<name>-raw.jsonl.gz | python -m json.tool` (per line) to inspect.

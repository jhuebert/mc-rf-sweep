# rf-sweep-core — direct-to-core LoRa link-quality test kit

Measures over-the-air link quality between two endpoints by driving
openhop_modem radios **directly through openhop_core** — no openhop_repeater
installation required. One machine next to each radio runs a small HTTP API
server; a third script orchestrates the tests over the VPN.

```
orchestrate.py (anywhere)
     │  HTTPS over VPN, X-API-Key auth
     ├──────────► api_server.py @ node_a ──TCP(LAN)──► openhop_modem A
     │                    │  tagged ping ──────── over the air ─────┐
     │                    ▼  pong (carries B's SNR/RSSI)           │
     └──────────► api_server.py @ node_b ──TCP(LAN)──► openhop_modem B
```

Each node's API server owns its modem TCP connection (connect, auth,
auto-reconnect, noise floor, per-packet RSSI/SNR) and can reconfigure the
radio live — frequency, SF, BW, CR, TX power, preamble — with **no reboot**.
The orchestrator varies one or two radio parameters across explicit value
lists, holds everything else constant, and collects detailed per-trial
statistics.

## What you need

- Two computers (can be SBCs/laptops), each connected to an openhop_modem
  over TCP (pymc_usb-firmware-compatible TCP server, default port 5055).
- VPN connectivity between the two sites (e.g. WireGuard/Tailscale) —
  only the two API servers need to be reachable across it.
- Radio range between the two modems at the settings you test.
- Python 3.11+ on each machine.

## Install (each node's computer, and wherever orchestrate.py runs)

    pip install -e <path-to>/openhop_core      # provides pymc_core
    pip install fastapi uvicorn httpx

## Configure

    cp env/node_a.env.example node_a.env     # edit values
    cp env/node_b.env.example node_b.env     # edit values

Env files live next to the scripts by default (`--env` / `--env-dir` to
override). **Never share the real env files** — the `.example` templates are
the shareable part. Keep `API_BIND` on the VPN interface, never 0.0.0.0 on
anything wider.

## Run

On each node's computer:

    python api_server.py --env node_a.env

Verify with `curl http://127.0.0.1:8080/api/health` (no auth needed).

### Plumbing check without hardware

    python api_server.py --env node_a.env --fake-radio   # loopback, no modem
    # point BOTH nodes' URLs in orchestrate at this server and run a
    # 2-trial test to validate the whole pipeline end to end.

## Orchestrator

    python orchestrate.py [--env-dir DIR] [--node-a node_a.env] [--node-b node_b.env]

Radio parameters you can hold constant: `--freq` (MHz), `--sf`, `--bw`
(kHz), `--cr` (denominator; 5 = CR4/5), `--tx` (dBm), `--preamble`.

Vary one parameter (others stay constant):

    --vary freq=902.75,909.5,927.0
    --vary sf=8,9,10,11
    --vary bw=62.5,125,250,500
    --vary cr=5,6,7,8
    --vary tx=2,10,22
    --vary preamble=8,16,32

Or two parameters for the full cross-product:

    --vary freq=909.5,927.0 --vary sf=9,10,11

Common flags: `--trials` (default 20), `--trial-delay` (5 s), `--timeout`
(10 s per ping), `--payload-len` (40 B), `--settle` (3 s after config
change), `--skip-noise` (don't sample noise floors per ping — faster).

### Test modes (`--mode`)

- **`oneway` (default)** — unidirectional, both directions per combination.
  The sender fires pings at airtime-rate (spacing is auto-raised above
  1.5× airtime); the receiver passively records delivery + SNR. No pong, no
  round-trip collisions, half the airtime. Losses cost nothing. Fastest
  option and the best frequency-ranking primitive.
- **`collect`** — fire-and-collect round trips: `/api/send` returns
  immediately after TX, pongs are collected afterwards and matched by tag.
  Gives RTT + both-direction SNR per trial, but the send spacing **must
  exceed the round-trip time** (half-duplex radios!) or you measure your
  own collisions. Use `--trial-delay` ≥ expected RTT + margin.
- **`ping`** — legacy blocking exchange, one HTTP call per trial. Simple,
  slow when the channel is lossy (each loss waits the full timeout).

In all modes each combination's noise floors are sampled at both nodes
(`--skip-noise` to skip), so every trial can be interpreted as
SNR ≈ RSSI − local noise floor.

Burst mode (fade-hole detection — trials back-to-back):

    --burst --burst-interval 0.5 --trials 50

On exit — including Ctrl-C — both nodes are restored to their startup
radio config and test mode is disabled.

## Per-trial measurement bundle

Every trial records, in `raw.jsonl`:

- `ok`, `rtt_ms` — measured radio-to-radio at node A (no TCP leg)
- `snr_out` — SNR of the ping measured at node B (returned inside the pong)
- `snr_ret` — SNR of the pong measured at node A's modem
- `rssi_out`, `rssi_ret` — same, in dBm
- `noise_a_dbm`, `noise_b_dbm` — idle-channel noise sampled before/after
- `timestamps_ms` — ping TX at A, ping RX at B, pong TX at B, pong RX at A
  (per-node monotonic clocks; enables one-way-delay estimates and measures
  node-B turnaround separately from airtime)
- the full radio config in effect (`cfg_*` columns)

`snr_out` vs `snr_ret` asymmetry is diagnostic: node A's noise floor and
antenna differ from node B's, so out and ret SNR differ; tracking both
separately tells you which *end* has the problem.

## analyze.py

    python analyze.py results/<timestamp> [--min-rel 90] [--by freq,sf]

Auto-detects which parameters varied and groups by them. Shows per
combination: reliability, SNR (out/ret) mean/σ/min, RTT p50/p95/max, and
failure streaks.

## Node management

- `GET /api/stats` — config, noise floor, modem status, counters (pings
  sent/answered, unexpected RX)
- `POST /api/test-mode {"enabled": false}` — take a node out of test mode
  at any time; it then ignores test packets
- Nodes auto-reconnect to their modem with backoff; check
  `/api/stats → modem` and `check_radio_health` after VPN drops

## Interpreting results

- **Reliability** is the headline; then SNR mean/σ; then RTT p50/p95.
- **Noise floor vs SNR**: poor SNR with a high noise floor = local
  interference (try other channels); poor SNR with a quiet floor = path
  loss (only fixable with SF/power/antenna).
- **Failure streaks**: isolated 1s are deep fades (normal); clusters point
  to interference windows.
- Compare RTT only between settings with comparable reliability.
- n=20 screens, n=40 decisions, n=100 commitments; never compare runs from
  different sessions head-to-head (put candidates in one run instead).

## Troubleshooting

- `radio begin() failed` — modem unreachable; check `MODEM_HOST/PORT`,
  token, and that the modem's TCP server is up.
- All pings time out — node B not in test mode (`/api/stats → counters →
  test_mode`), wrong sync word, or radios can't hear each other at the
  configured settings. Re-test with your known-good preset.
- `config mismatch` after apply — the modem rejected a parameter (e.g.
  unsupported BW); check `/api/stats` for what actually took.
- Pings time out but both radios are up — verify `test_mode` is on at
  node B and that both servers show recent RX activity in counters.
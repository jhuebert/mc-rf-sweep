# NebraskaMesh — Bellevue, NE test site

Two fixed openhop_modem nodes ~3.9 miles (6.3 km) apart in Bellevue,
Nebraska, USA, suburban residential path.

## Nodes

| | Node A (trace initiator) | Node B |
|---|---|---|
| Hardware | Seeed XIAO WIO (ESP32-S3 + SX1262), openhop_modem firmware | Heltec v4.2, openhop_modem firmware |
| TX power | 22 dBm (standard node power) | 22 dBm |
| Antenna | DIY quarter-wave ground plane | Muziworks whip, hung upside down |
| Placement | Indoors, on a dresser, second floor of a house (~15 ft AGL) | Outdoors under a backyard gazebo (~6 ft AGL) |

Path: Node A's house → Node B's (parents') backyard, ~3.9 mi.

## Control plane

Each node's host computer runs `kit/api_server.py`, which owns the modem's
TCP connection (port 5055) and exposes a small HTTP API. The two hosts are
linked by a VPN so a single local orchestrator can script both radios —
no manual intervention, no reboots, live frequency/SF changes between
combinations.

## Site notes

- The indoor node (A) consistently hears ~2–4 dB worse than the outdoor
  node (B) — visible in nearly every campaign as worse *b2a* delivery
  (transmissions *into* the indoor node). Measured per-frequency in the
  2026-09-11 overnight campaign: 1.1 dB (926.8) to 3.4 dB (903.1).
- Node B's noise floor swings several dB between sessions (quiet ≈
  −100 dBm, busy ≈ −95 dBm); Node A runs ≈ −101 to −103 dBm with
  occasional strong local interference spikes (−66 dBm observed at
  904.0/906.0 MHz during the 2026-09-10 campaign).
- Interference environment: suburban; no intentional emitters of our own.

## Campaigns

| Campaign | Date | Report |
|---|---|---|
| 902–928 MHz band sweep, 500 kHz, SF7–12 + US-defaults baseline | 2026-09-10 | [2026-09-10-902-928-band-sweep](2026-09-10-902-928-band-sweep/) |
| Fine sweep ±0.4 MHz @ 0.1 MHz around the 6 finalists, SF9–10 + same-session US-defaults control | 2026-09-10 | [2026-09-10-fine-sweep](2026-09-10-fine-sweep/) |
| Overnight SF×CR matrix + finalist deep passes on the fine-sweep trio (903.1 / 909.6 / 926.8), unattended campaign driver | 2026-09-10/11 | [2026-09-11-sf-cr-campaign](2026-09-11-sf-cr-campaign/) |

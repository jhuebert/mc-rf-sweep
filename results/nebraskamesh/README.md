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

## Results overview — all campaigns, net

Six campaigns (2026-09-10 → 09-11), ≈44,000 one-way trials on one 3.9 mi
suburban path: indoor node ↔ gazebo node, 22 dBm, 500 kHz BW unless noted.
This section is the roll-up; per-campaign reports below have the detail.

### Recommended operating points (net of all campaigns)

| Role | Config | Worst-direction delivery | Payload throughput (40 B) | Confirmed by |
|---|---|---|---|---|
| **Daytime primary** | **909.1 MHz / SF10 / CR4/8** | **85%** (n=360/dir) | 1026 bit/s | [burst-resilience](2026-09-11-9091-9096-burst-resilience/) |
| Daytime max-throughput | 909.1 MHz / SF10 / CR4/5 | 81% (n=360/dir) | 1248 bit/s (1.22× US defaults) | [burst-resilience](2026-09-11-9091-9096-burst-resilience/) |
| **Quiet-hours primary / most robust** | **926.8 MHz / SF10 / CR4/8** | 97.5% (matrix), 99% (deep pass) | 1026 bit/s | [overnight SF×CR](2026-09-11-sf-cr-campaign/) (n≥300/dir) |
| Quiet-hours fast option | 926.8 MHz / SF9 / CR4/8 | 94% | ~1900 bit/s | [overnight SF×CR](2026-09-11-sf-cr-campaign/) |
| Backup frequency | 909.6 MHz / SF10 / CR4/5 | 60% daytime; 90–96% in clean windows | 1248 bit/s | [fine-tune](2026-09-11-9096-fine-tune/), [SF×CR @909.6](2026-09-11-9096-sfcr/) |
| US-defaults baseline | 910.525 MHz / 62.5 kHz / SF7 | 91–97% in **every** session | ~10–30× less than 500 kHz options | all campaigns |

Other tested-but-not-recommended: **903.1** has a real b2a pathology at
SF7–8 and never matched the leaders at scale; **906.5** was fine-sweep
rank 16 and never re-confirmed at depth; **909.6/SF10/CR4/8 is
measurably pathological** (36.1% b2a, n=360/dir) — don't deploy it.

### How the frequency recommendation evolved

1. **Band sweep** (0.5 MHz grid, n≈244/freq): finalists 909.5, 906.5,
   923.0, 927.0, 917.0, 903.0; dead zones at 904.0, 908.0, 911.5–912.0,
   919.0, 921.5–922.0 (922.0 lost 0/240), 924.0, 925.5.
2. **Fine sweep** (0.1 MHz grid, n=160/freq): every finalist's true peak
   moved 0.1–0.4 MHz; 923.0 and 917.0 collapsed under re-examination.
   Winner 909.6; band-spread set **903.1 · 906.5 · 909.6 · 926.8**.
3. **Overnight SF×CR**: **926.8 promoted to site frequency** (100%
   worst-direction at SF10 at every CR); 909.6 demoted — recurring
   minute-scale b2a interference windows that small-n passes missed.
4. **Daytime SF×CR @909.6**: 500 kHz b2a collapsed during windows while
   the 62.5 kHz defaults control stayed healthy; SF10 best, SF11 loses.
5. **Fine-tune (0.05 MHz grid + head-to-head)**: the 909.x neighborhood
   is lumpy at 50 kHz scale; **909.1 beat 909.6 head-to-head** (93.5% vs
   87% worst) — recommendation switched to **909.1**.
6. **Burst-resilience deep dive**: at n=360/dir, **909.1/SF10/CR4/8 is
   the daytime winner** (85% worst, max loss streak 23 trials); 909.1
   out-delivered 909.6 in matched rounds.

**Net:** the 909.x ridge is the home — **909.1 primary, 909.6 backup** —
with **926.8** as the quiet-hours/most-robust alternative. The 922–923.4
stretch is the worst of the band.

### What the channel taught us

- **Loss mode is minute-scale interference windows at the indoor node,
  not fade holes.** Bursts at minimum legal spacing never lost two
  packets in a row; 76–96% of b2a losses arrive in multi-packet streaks
  from minute-scale windows. Windows are transient (recovery within
  15 min) and roam across frequencies and rounds.
- **The a2b direction (gazebo RX) is excellent everywhere** — 90%+
  delivery at every frequency and config, max loss streak 2. Every
  ranking in every campaign is a b2a story. Any indoor-node mitigation
  (antenna move, filtering) buys more than any protocol choice.
- **The indoor node hears 1.1–3.4 dB worse** depending on frequency;
  it only bites where margin is thin (SF7–8, 903.1). 926.8 has the
  smallest asymmetry — part of why it wins quiet hours.
- **SF ladder:** SF7 is unusable at 500 kHz on this path (cliff sits
  between SF8 and SF7, and no CR rescues it); SF8 only with CR4/8;
  **SF10 is the operating point**; SF11 loses decisively in daytime
  (its 2× airtime doubles window exposure) — if SF11, CR4/8 is
  mandatory.
- **Coding rate is a real lever below the ceiling:** CR4/8 buys +25 pp
  at SF8 (926.8) and +48 pp (909.6 b2a) overnight, and contains burst
  damage by day (streaks 38–53 → 22–23). At SF10 it costs ~22% airtime
  for +4 pp — take **CR4/6** there for best value. CR4/7 fills no
  niche. Exception: 909.6/SF10, where CR4/8 anomalously collapses.
- **Link budget:** ~12–14 dB fade margin at 926.8/SF10/CR4/8 — flat
  down to 14 dBm TX, dead by 8 dBm. Treat 14 dBm as the warning line.
  Payload 20–100 B is insensitive; **preamble 8 is safe and saves
  ~49 ms/packet** at SF10.
- **Narrow vs wide is a genuine trade:** the 62.5 kHz US defaults
  out-delivered every 500 kHz cell on b2a during bursty daytime periods
  (the wide window sees more of the interference) while being ~10–30×
  slower. Part 15 compliance and interference robustness are in direct
  tension on this channel.

### Open items

- Mechanism of the **909.6/SF10/CR4/8 anomaly** (36.1% b2a pooled) —
  targeted retest before anyone deploys that combo.
- **Indoor-node mitigation** at node A (antenna relocation, filtering)
  — the highest-leverage improvement available.
- **903.1 and 906.5** were never re-confirmed at n>40/dir; a diurnal
  repeat of the band sweep is also outstanding.
- Overnight **SF11** retest for fairness (daytime is what most traffic
  lives in, so low priority).

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
| SF×CR selection at 909.6 (SF10/11 × CR4/5/4/8), single morning pass + bursts + US-defaults control | 2026-09-11 AM | [2026-09-11-9096-sfcr](2026-09-11-9096-sfcr/) |
| 909.6 fine-tune — 0.05 MHz grid around the incumbent + 909.1 head-to-head confirmation | 2026-09-11 AM | [2026-09-11-9096-fine-tune](2026-09-11-9096-fine-tune/) |
| Burst-resilience deep dive — 909.1 vs 909.6 × SF10/11 × CR4/5/4/8, interleaved matrix + burst rounds | 2026-09-11 midday | [2026-09-11-9091-9096-burst-resilience](2026-09-11-9091-9096-burst-resilience/) |

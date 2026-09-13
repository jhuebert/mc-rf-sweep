# NebraskaMesh — Bellevue, NE radio-link testing

## Why we did this

NebraskaMesh runs LoRa radios in the 902–928 MHz band, and before committing
the network to a channel and a set of radio settings, we wanted real answers
instead of guesswork. That band is shared, noisy, and surprisingly lumpy —
two frequencies 100 kHz apart can behave completely differently, and the same
frequency can be clean at 3 a.m. and unusable at 10 a.m. Picking badly can
quietly cost you half your messages.

So over two days (2026-09-10 → 09-11) we pointed two real radios at each
other across a real 3.9-mile suburban path — one indoors in a house, one
outdoors in a backyard — and had them exchange roughly **84,000 test
messages** while sweeping every dial the radio has: frequency, spreading
factor, coding rate, bandwidth, transmit power, payload size, and preamble
length. The question was simple: **which settings deliver the most messages,
most of the time, on this path?**

Each linked report below is the detailed record of one test session. This
README is the plain-language summary: what we tried, what we found, and what
we recommend.

## The two radios

| | Node A — the indoor node ("aries") | Node B — the gazebo node ("lynx") |
|---|---|---|
| Hardware | Seeed XIAO WIO (ESP32-S3 + SX1262) | Heltec v4.2 |
| Firmware | openhop_modem | openhop_modem |
| TX power | 22 dBm (standard node power) | 22 dBm |
| Antenna | DIY quarter-wave ground plane | Muziworks whip (hung upside down) |
| Placement | Indoors, on a dresser, second floor of a house (~15 ft) | Outdoors under a backyard gazebo (~6 ft) |

The nodes sit ~3.9 miles (6.3 km) apart in Bellevue, Nebraska — a typical
suburban residential path. Each radio is driven by a small host computer,
and the two hosts are linked over a VPN, so a single script could reprogram
both radios live, all day and all night, without anyone touching them.

**How a test works:** one radio sends a stream of numbered test packets;
the other logs which ones arrive. **Delivery % = the share that arrived.**
We always test both directions separately, because they are not equal — and
this turned out to be one of the biggest findings of all (see below). When
a number appears in this summary, assume it is the **worse** direction,
because that is the number that decides whether the link actually works.

Three pieces of jargon worth knowing up front:

- **Spreading factor (SF)** — the speed-vs-reach trade. SF7 is fastest but
  weakest; SF12 is slowest but toughest.
- **Coding rate (CR)** — how much error-correction redundancy is packed
  into each packet. CR4/5 is light; CR4/8 is heavy and forgiving.
- **Bandwidth** — wide channels (500 kHz) are fast but hear all the
  interference; narrow channels (62.5 kHz) are slow but see only a sliver
  of it.

## The short version

- **The interference — not distance — is the enemy on this path.** The link
  rarely fails because the signal is too weak. It fails in short,
  minute-scale bursts of noise that wipe out runs of packets, then vanish.
- **The bursts follow the spectrum, not our houses.** Everything we tested
  between 902 and 917 MHz got hit; nothing at 926 MHz ever did, during the
  very same hours.
- **So the recommendation is 926 MHz:** **926.05 (the whole 926.0–926.8
  stretch is good), SF10, CR4/8** — ~87% worst-direction delivery in busy
  daytime, 97–98% in quiet hours, and completely burst-free.
- The best fallback inside the busy lower band is **909.05–909.1 at
  SF10/CR4/8** — good when clean (85–94%), but it will bleed during burst
  windows no matter which exact frequency you pick.
- The slow narrow-band **US defaults** (910.525 MHz, 62.5 kHz, SF7)
  delivered 92–98% in *every* session — the reliability benchmark, at
  10–30× lower speed.
- The single highest-leverage improvement available has nothing to do with
  settings: **fix the indoor node** (antenna placement, filtering). It is
  the bottleneck in every measurement we took.

## The story of the testing

Each campaign existed to answer the question the previous one raised. Read
them in order and the recommendation builds itself.

### 1. Map the band — [band sweep](2026-09-10-902-928-band-sweep/)

First pass: 51 frequencies across the whole 902–928 band at 0.5 MHz
spacing, ~244 messages each, at six speeds. The band is wildly uneven.
There are good ridges (around 909, 906.5, 917, 923, and 927 MHz) and dead
canyons — at 922.0 MHz **every one of ~240 messages was lost**, at every
speed. Two more lessons: at 500 kHz bandwidth this path only supports the
slower settings (SF7 delivered 3.5% band-wide, SF12 81%), and the
narrow-band US defaults baseline delivered 93–97% — a hard act to beat on
reliability, if you can live with its speed.

### 2. Zoom in — [fine sweep](2026-09-10-fine-sweep/)

The finalists deserved a closer look: a 0.1 MHz-resolution sweep around
each. Every "peak" turned out to sit 0.1–0.4 MHz away from where the coarse
grid placed it, and two finalists evaporated entirely under re-testing —
their morning results had been flattered by lucky, quiet windows. Lesson:
small samples lie on this channel; you must confirm at scale. The session
produced a clean winner (909.6) and a four-frequency shortlist:
**903.1 · 906.5 · 909.6 · 926.8**.

### 3. Pick the settings — [overnight SF×CR campaign](2026-09-11-sf-cr-campaign/)

Overnight, on the quiet channel, we tested every speed × error-correction
combination on the three surviving frequencies — ~14,500 messages. **926.8
emerged as the strongest frequency on the path** (97.5% worst-direction at
SF10 at every coding rate). The settings rules also fell out cleanly:
SF7 is unusable at 500 kHz on this path, SF8 works only with heavy
error correction (CR4/8), SF10 is the operating point, and CR4/8 rescues
marginal cells outright. We also measured the link's fade margin: ~12–14 dB
— comfortable at full power, but a hard cliff if the path or antennas ever
degrade.

### 4. Morning reality check — [909.6 settings test](2026-09-11-9096-sfcr/) · [fine-tune](2026-09-11-9096-fine-tune/) · [burst deep dive](2026-09-11-9091-9096-burst-resilience/)

The next morning at 909.6, delivery fell apart in stretches: healthy for a
few minutes, then entire 20-packet runs lost, then healthy again within
15 minutes. Critically, the narrow-band control run stayed healthy the
whole time — the interference lives *inside* our wide 500 kHz window.
Three follow-ups ran the same morning:

- A 50 kHz-resolution zoom around 909.6 revealed the neighborhood is lumpy
  at that scale, and **909.1 beat 909.6 head-to-head** (93.5% vs 87%) —
  so the recommendation moved to 909.1.
- An interleaved deep dive (five rounds across both frequencies) showed
  CR4/8's redundancy genuinely contains burst damage — worst loss streaks
  shrank from 38–53 packets to 22–23 — and crowned **909.1/SF10/CR4/8 the
  daytime winner at 85% worst-direction**.

### 5. The afternoon that settled it — [909 fine-tune](2026-09-11-909-band-finetune/) · [916/926 fine-tune](2026-09-11-916-926-band-finetune/)

Two questions remained. First: can *any* frequency in the 909 region dodge
the bursts? We swept 16 channels at 50 kHz spacing with interleaved passes
— **all 16 got hit, in every single test phase**. No escape there; even the
best cell (909.05) still bled.

Second: does the emptier upper band escape them? We swept two candidate
windows — 916.3–916.9 and 926.0–926.5 — in the same interleaved style, with
a 909.10 control replicating the afternoon's baseline in between. The
result was unambiguous: **every 916.x channel collapsed just like 909.x,
while 926.0–926.5 never lost a single packet to a burst** — 95–98%
delivery, worst streak of 2, across all six phases, during the same hours
916 was dying. Same sites, same hardware, same afternoon: **the
interference follows the spectrum, not our houses.** The emitters live in
the busy 902–917 MHz region; 926 MHz is the quiet corner of the band.

That is the verdict the whole effort converges on: **926.05 MHz, SF10,
CR4/8** — 87% worst-direction in busy daytime conditions, 97–98% in the
overnight quiet, and zero burst losses ever recorded.

## What we learned

**1. The failure mode is roaming interference windows, not weak signal.**
Bursts of noise wipe out multi-packet runs (76–96% of losses into the
indoor node arrive as streaks), last on the order of minutes, recover
within ~15 minutes, and roam across frequencies and time. The radio path
itself is healthy: packets that arrive during wipeouts show normal signal
quality, so this is additive noise, not fading.

**2. The indoor node is the bottleneck.** The gazebo radio received 90%+
at every frequency and setting in every campaign. Deliveries *into* the
indoor node are the weak direction essentially everywhere — it hears
1.1–3.4 dB worse depending on frequency, and the local burst noise lands
on it too. Relocating its antenna or adding filtering would buy more than
any settings change we tested.

**3. 926 MHz is the quiet corner — with one wrinkle to watch.** It is the
only burst-free real estate found in the entire band. Interestingly, the
usual direction asymmetry flips there: the gazebo→indoor direction is the
strong one (96–98%) and indoor→gazebo runs a bit lower (80–87%) — but those
losses are small, random, and unrelated to bursts. Worth watching in longer
campaigns; it doesn't change the ranking.

**4. The settings ladder is now fully mapped.**

- **SF7: unusable** at 500 kHz on this path — no coding rate rescues it.
  **SF8: only with CR4/8.** **SF10: the operating point.**
- **SF11 is a bad trade in daytime:** its double-length packets just soak
  in interference windows longer, and at 926 MHz it bought *zero* delivery
  gain — the residual losses there aren't signal-strength problems that a
  slower setting can fix. (In quiet overnight hours SF11 does fine, but
  daytime is where real traffic lives.)
- **SF9 is the legitimate fast option:** ~half the airtime of SF10 at
  85–94% worst-direction.
- **CR4/8 earns its cost below SF10** — it rescues marginal cells and
  contains burst damage (worst streaks 38–53 → 22–23). At SF10 it costs
  ~22% airtime for +4 points of delivery, so **CR4/6 is the value pick
  where the channel is quiet**. CR4/7 fills no niche.

**5. Wide vs narrow is a genuine trade, not a winner.** The 62.5 kHz US
defaults out-delivered every 500 kHz cell during bursty daytime periods —
a narrow window simply hears a fraction of the wideband noise — while
being 10–30× slower. Interference robustness and throughput pull in
opposite directions on this band; 926 MHz is the rare place where a wide
channel gets both.

**6. The link budget is comfortable but not generous.** ~12–14 dB of fade
margin at 926/SF10/CR4/8: delivery is flat down to 14 dBm transmit power
and dead by 8 dBm. Treat 14 dBm as the warning line. Payload size
(20–100 B) doesn't matter, and **preamble 8 is safe and saves ~49 ms per
packet** at SF10.

**7. A note for network planning beyond this site.** The 909.x region sits
inside the LoRaWAN US915 channel ladder and is burst-susceptible
ridge-wide — a poor choice for a national mesh channel. 926 MHz sits
inside NextNav's 920–928 MHz license area (currently silent locally), with
edge emissions clear of the ham repeater segments by construction. The
full band-selection argument lives in `NATIONAL-FREQ-STRATEGY.md` in the
test kit.

## Recommended settings

| Use this when | Settings | Worst-direction delivery | Speed (40 B) | Confirmed by |
|---|---|---|---|---|
| **Primary — any time of day** | **926.05 MHz · SF10 · CR4/8** (the whole 926.0–926.8 stretch is good) | **87% daytime · 97–98% quiet hours** | 1026 bit/s | [916/926 fine-tune](2026-09-11-916-926-band-finetune/), [overnight SF×CR](2026-09-11-sf-cr-campaign/) |
| Fast option at 926 | 926.05 MHz · SF9 · CR4/8 | 85–94% | ~1900 bit/s | [overnight SF×CR](2026-09-11-sf-cr-campaign/), [SF sweep](2026-09-11-916-926-band-finetune/) |
| Best available in the busy lower band | 909.05–909.1 MHz · SF10 · CR4/8 | 85–94% when clean; sags toward ~55–75% in busy windows | 1026 bit/s | [burst deep dive](2026-09-11-9091-9096-burst-resilience/), [909 fine-tunes](2026-09-11-909-band-finetune/) |
| Slow-but-bulletproof baseline | 910.525 MHz · 62.5 kHz · SF7 (US defaults) | 92–98% in **every** session | 10–30× slower | all campaigns |

**Do not deploy:** anything in 922–923.4 MHz (the worst stretch of the
band) · 903.1 below SF9 (its gazebo→indoor direction dies at low SF) ·
SF7 or SF11 at 500 kHz in daytime. 903.1/906.5 were never re-confirmed
at depth.

## Proposed US presets (my conclusion)

Updated 2026-09-12 after the CR-selection campaign. Based on these
location-specific results, here would be my proposal for **two** optional
US 500 kHz bandwidth presets:

- **910.1** — Best lower-band cell in the first CR-selection campaign:
  89% worst-direction, and the only 909/910-area cell that never took a
  pass-level wipe there. Clear of LongTurbo (908.75) by ~850 kHz, and close
  enough to the current US default frequency that filters and antennas
  should work as well as they did before. **But the retest warned us off
  treating it as settled:** in the same-day round-2 campaign its a2b
  direction collapsed to 52% while b2a stayed healthy (87%) — the damage
  flipped direction between rounds. Pooled across both rounds it is 71%
  a2b / 79% b2a (n≈1,600/dir). Its clean first campaign looks like it was
  luck, exactly as the caveat below feared. It remains the best-known
  lower-band cell when it is clean, but expect burst sessions to hurt it.
  It also sits closer to the 910.525/62.5 kHz default (~150 kHz of
  clearance to the default channel edge) than a lower pick like 909.75
  would, so border-region Canada deserves a check.
- **926.0** — Never lost a packet to burst interference across two full
  days of testing, and its emissions edge stays well clear of the 927.0
  ham repeater segment. There shouldn't be any ham interference.
  (916.40 is dropped: in the 2026-09-12 campaign it is just as
  burst-prone as the 909/910 ridge, with nothing to recommend it.)

For the remaining settings, I would propose **SF10 and CR4/7**. At 926
the whole CR ladder was statistically tied, so CR4/7 costs nothing on the
quiet channel, while its extra redundancy hedges the burst-prone 910.1
channel at a modest airtime premium over CR4/5 — a middle ground between
the speed of CR4/5 and the burst-resilience of CR4/8. (Pooled across both
CR-selection rounds, the 926.0 ladder actually ran slightly *against*
heavier CR — a2b: CR4/5 87%, CR4/6 83%, CR4/7 85%, CR4/8 81%, n≈400/dir
each — so there is no evidence heavier CR buys anything at 926.) SF11,
with double the airtime, was far more susceptible to dropping packets due to
interference. SF10 could be just as controversial as frequency selection.
🤣

Finally, I would propose we set the default path hash size at 3-byte.
One can always reduce their path hash size if they need to.

All of this is from one suburban path; local meshes should confirm with
their own measurements before committing.

## What we'd still like to know

- **Indoor-node mitigation at node A** (antenna relocation, filtering) —
  the highest-leverage improvement available on this path.
- **Who the 902–917 burst emitters are.** The evidence says hopping,
  intermittent emitters in the occupied lower band; identifying them would
  tell us whether the 909/916 region is permanently off-limits.
- Whether the mild **926 MHz direction inversion** (a2b ~80–87%) is stable
  or an artifact of these sessions. *(Pooled update: three sessions now —
  926.0–926.8 a2b 80–87% / b2a 94–99% every time, n≈2,000/dir at 926.0 —
  so the inversion itself is confirmed; its cause is still open.)*
- **903.1 and 906.5** were never re-confirmed at depth; a diurnal (day-vs-
  night) repeat of the original band sweep is also outstanding, as is a
  fairness retest of SF11 overnight (low priority).

## Campaign index

| # | Campaign | Date | Report |
|---|---|---|---|
| 1 | 902–928 MHz band sweep, 0.5 MHz grid, SF7–12 + US-defaults baseline | 2026-09-10 | [2026-09-10-902-928-band-sweep](2026-09-10-902-928-band-sweep/) |
| 2 | Fine sweep, 0.1 MHz grid around the 6 finalists, SF9–10 + same-session control | 2026-09-10 | [2026-09-10-fine-sweep](2026-09-10-fine-sweep/) |
| 3 | Overnight SF×CR matrix + finalist deep passes on 903.1 / 909.6 / 926.8 | 2026-09-10/11 | [2026-09-11-sf-cr-campaign](2026-09-11-sf-cr-campaign/) |
| 4 | SF×CR selection at 909.6 (SF10/11 × CR4/5 vs CR4/8), morning pass + bursts | 2026-09-11 AM | [2026-09-11-9096-sfcr](2026-09-11-9096-sfcr/) |
| 5 | 909.6 fine-tune — 0.05 MHz grid + 909.1 head-to-head | 2026-09-11 AM | [2026-09-11-9096-fine-tune](2026-09-11-9096-fine-tune/) |
| 6 | Burst-resilience deep dive — 909.1 vs 909.6 × SF10/11 × CR4/5 vs CR4/8, interleaved | 2026-09-11 midday | [2026-09-11-9091-9096-burst-resilience](2026-09-11-9091-9096-burst-resilience/) |
| 7 | 909.00–909.75 MHz fine-tune — can any 909 channel dodge the bursts? | 2026-09-11 PM | [2026-09-11-909-band-finetune](2026-09-11-909-band-finetune/) |
| 8 | 916.3–916.9 + 926.0–926.5 fine-tune + SF sweep — the 926 verdict | 2026-09-11 PM | [2026-09-11-916-926-band-finetune](2026-09-11-916-926-band-finetune/) |
| 9 | CR4/5–4/8 selection at 909.5 / 910.0 / 910.1 / 926.0, 4 interleaved passes | 2026-09-12 | [2026-09-12-cr-selection](2026-09-12-cr-selection/) |
| 10 | CR4/5–4/8 selection at 910.5 / 913.0 (+910.1/926.0 controls), combined with #9 | 2026-09-12 | [2026-09-12-cr-selection-2](2026-09-12-cr-selection-2/) |

## For the record

**Control plane.** Each node's host computer runs `kit/api_server.py`,
which owns the modem's TCP connection (port 5055) and exposes a small HTTP
API. The two hosts are linked by a VPN so a single local orchestrator can
script both radios — no manual intervention, no reboots, live
frequency/SF changes between combinations.

**Data.** All campaign raw data lives in the test kit's SQLite database
(`rf-sweep.db`: 109 runs / ~89,600 trials incl. legacy repeater-era data,
13 campaigns), with per-packet SNR/RSSI, noise floors, one-way latency, and
error reasons — so any claim in these reports can be re-derived or
cross-checked with a single query. The per-campaign `data/` folders remain
the portable/exportable copies.

**Site notes.**

- The indoor node (A) consistently hears ~1–3.4 dB worse than the outdoor
  node, measured per frequency in the overnight campaign (1.1 dB at 926.8,
  3.4 dB at 903.1). It shows up in nearly every campaign as worse delivery
  *into* the indoor node.
- Node B's noise floor swings several dB between sessions (quiet ≈ −100 dBm,
  busy ≈ −95 dBm). Node A runs ≈ −101 to −103 dBm with occasional strong
  local spikes (−66 dBm observed at 904.0/906.0 MHz during the band-sweep
  day).
- Interference environment: suburban; no intentional emitters of our own.

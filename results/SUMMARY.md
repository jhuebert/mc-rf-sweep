# Cross-mesh summary

One row per campaign. The goal: if enough meshes run the same standard
sweep, we can see whether any frequency is good *on average, everywhere*.

"Best freq" = ranked by worst-direction delivery across SF9–10 at 500 kHz
(the standard sweep's discriminating cells). "Defaults" = the
910.525 MHz / 62.5 kHz / SF7 baseline delivery (a2b/b2a).

| Mesh | Location | Date | Path | Best frequencies | Dead zones | Defaults | Report |
|---|---|---|---|---|---|---|---|
| NebraskaMesh | Bellevue, NE, USA | 2026-09-10 | 3.9 mi, 1 indoor + 1 gazebo node | 909.6, 909.1, 926.8, 926.9, 909.3, 927.0, 903.1 (fine-swept) | 904.0, 908.0, 911.5–912.0, 919.0, 921.5–923.4, 925.5 | 92% / 96% | [band sweep](nebraskamesh/2026-09-10-902-928-band-sweep/) · [fine sweep](nebraskamesh/2026-09-10-fine-sweep/) |
| NebraskaMesh | Bellevue, NE, USA | 2026-09-10/11 | 3.9 mi, 1 indoor + 1 gazebo node | 926.8 @ SF10 (overnight); CR4/6 best value, CR4/8 max robustness; SF7 unusable on this path | 903.1 low-SF b2a | — | [SF×CR overnight](nebraskamesh/2026-09-11-sf-cr-campaign/) |
| NebraskaMesh | Bellevue, NE, USA | 2026-09-11 | 3.9 mi, 1 indoor + 1 gazebo node | 909.1 (morning, SF10/CR5, 94.8% worst-dir); SF10 beats SF11 under burst interference | 909.45, 909.75 (during morning interference window) | 92% / 94% | [SF×CR morning](nebraskamesh/2026-09-11-9096-sfcr/) · [fine-tune](nebraskamesh/2026-09-11-9096-fine-tune/) |

*(Your mesh here — see [results/README.md](README.md).)*

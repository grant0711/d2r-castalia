# Phase Step (phase_step) - experiment log

Design: Strictly requires Overcharge to cast (restrict=2, State1=sorc_stance_light). High-speed lightning blink with short cooldown and static discharge along the path/arrival.

- **2026-11-20 02:12** [p1_phase_frenzy] p1_phase_frenzy built: 166/104 blink gated to Overcharge, 1.5s cooldown, range min(24,14+lvl/2); landing shock (ltng 1-6, r5) -> sigil pulse frenzies enemies in r5 (+35% run/attack speed, 3s, state phase_step_frenzy w/ lightningenchant overlay). Awaiting in-game test.
- **2026-11-20 02:21** [p2_debug_frenzy] p2_debug_frenzy in game: shock damage + hit visuals + ground sparks OK (no outward nova - user likes this), but frenzy never applied (no tint, no speed). Hypothesis: hitfunc-1 ExplosionMissile is client-only.
- **2026-11-20 02:25** [p3_pulse_first] p3_pulse_first in game: visuals identical, still no frenzy. Found: pulse inherited sigil Param1=6 (pulse interval) > Range 6, and Radius=4 (func 14 uses missile Radius). Backdraft overrides Param1=1 + Radius.
- **2026-11-20 02:30** [p4_sigil_params] p4_sigil_params in game: still no frenzy. Sigil func 14 ruled out. Trying abyssexplode func 39 burst (Backdraft's detonation function).
- **2026-11-20 02:37** [p5_abyss_burst] p5_abyss_burst in game: identical visuals, shock dmg still present, no pull, no frenzy. Suspect shock dmg comes from srvdofunc 166 itself and server missile chain never spawns. p6: diagnostic fire burst + Decrepify-clone helper skill as missile Skill.
- **2026-11-20 02:41** [p6_diag_helper] p6_diag_helper in game: NO fire damage, no purple -> server never spawns the warp's ExplosionMissile (hitfunc 42 explosion is client-only). Glacier Step's landing freeze is srvdofunc 166's own hit. p7: test server trail-dropper pSrvDoFunc=2.
- **2026-11-20 02:48** [p7_diag_trail] p7_diag_trail in game: monsters along the path turn purple + fast -> server trail-dropper (pSrvDoFunc=2) + sigil func 14 WORKS. Fire burst not noticeable. User wants path-wide frenzy kept (phasing over a monster should supercharge it). p8: real values.
- **2026-11-20 02:54** [p8_path_frenzy] p8 feedback: remove purple, widen + level-scale frenzy path and landing radius, shock enemies phased over. -> p9
- **2026-11-20 03:06** [p9_wider_shock_path] p9 feedback: frenzy should scale (20% +2%/lvl, cap 40%); tooltip: only lightning damage, description 'blink to a location, shocking monsters in your path'. -> p10
- **2026-11-20 12:34** [p10_scaling_frenzy] Verified in game -> done (p10_scaling_frenzy).

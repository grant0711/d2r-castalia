# Glacier Step (glacier_step) - experiment log

Design: Strictly requires Cryostasis to cast (restrict=2, State1=sorc_stance_cold). Directional ice blink (srvdofunc=166 / cltdofunc=104, 3s cooldown) that freezes and damages enemies along your wake and in a burst of ice spikes where you arrive.

- **2026-11-19 22:35** [p1_ice_blink] Verified in game (lvl60 SORC, a1h): blink, icy wake, arrival nova and Cryostasis gating all look good.
- **2026-11-19 22:42** [p1_ice_blink] REGRESSION SUSPECT: equipped shield (Luna, Heater) vanishes on Save & Exit. srvdofunc=166 (Blade Warp 'hurl an astral weapon') - every vanilla 166 user has requiresweapon=1; glacier_step does not. Reverted to wip pending A/B test.
- **2026-11-19 22:55** [p1_ice_blink] Shield loss reproduced on fresh SORCTWO + Paladin without casting Glacier Step -> unrelated, mod-wide. Restored to done.
- **2026-11-20 12:38** [p1_ice_blink] p2_cleanup: removed client-only nova server half + glacier_step_aoe_srv, flattened always-true Cryostasis checks (radius 9 / visual 8). No behaviour change.
- **2026-11-20 12:48** [p2_cleanup] Freeze scales with monster cold res (user observation). Target: 2.5s at lvl 20 vs Hell baseline 30% res -> p3_freeze_curve (raw 3.56s @20).

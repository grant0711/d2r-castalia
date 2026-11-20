# Glacier Step (glacier_step) - experiment log

Design: Strictly requires Cryostasis to cast (restrict=2, State1=sorc_stance_cold). Directional ice blink (srvdofunc=166 / cltdofunc=104, 3s cooldown) that freezes and damages enemies along your wake and in a burst of ice spikes where you arrive.

- **2026-11-19 22:35** [p1_ice_blink] Verified in game (lvl60 SORC, a1h): blink, icy wake, arrival nova and Cryostasis gating all look good.
- **2026-11-19 22:42** [p1_ice_blink] REGRESSION SUSPECT: equipped shield (Luna, Heater) vanishes on Save & Exit. srvdofunc=166 (Blade Warp 'hurl an astral weapon') - every vanilla 166 user has requiresweapon=1; glacier_step does not. Reverted to wip pending A/B test.
- **2026-11-19 22:55** [p1_ice_blink] Shield loss reproduced on fresh SORCTWO + Paladin without casting Glacier Step -> unrelated, mod-wide. Restored to done.

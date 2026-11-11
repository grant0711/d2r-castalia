# Cinder Lance (cinder_lance) - experiment log

Design: Fast, thin, long-range fire bolt that pierces 3 enemies. In Conflagration the whole path ignites.

- **2026-11-11 19:15** [p1_pierce_all] Stance work finished (anim_v3 locked). Starting Fire tree with Cinder Lance. P1: CollideKill=0 on firebolt to test pierce-all.
- **2026-11-11 19:19** [p1_pierce_all] P1 result (user): pierce-all works: passes through enemies, damages each, explosion burst on each hit (subtle), full range regardless of hits. Note: exact 'pierce 3' count has no native column (Pierce flag only listens to pierce stat); options: pierce-all with range/damage falloff.
- **2026-11-11 19:24** [p2_fast] P2 result (user): fast+thin feels good but speed 32 is realistic only ~lvl 20; range at lvl 1 too great; hits still read. DESIGN RULE: investment must change the FEEL (velocity, range, AoE size, duration), not just damage.
- **2026-11-11 19:31** [p4a_stance_pop] P3 accepted. Starting stance synergy. P4a diagnostic: marker stat skill_handofathena in Fire stance slot 6; firebolt pSrvHitFunc 38 + HitSubMissile1 fireexplode, count = skill calc4 conditioned on marker.
- **2026-11-11 19:34** [p3_scaling] P4a result (user): hit function 38 on firebolt = bolts pass straight through monsters with no collision (not piercing, no damage). Reverted Cinder Lance to P3. Chilling Armor precedent: func-18 row + aura event + srvmissilea/cltmissilea. P4b: put the pop on the Fire stance state (domissiledamage -> func 1).
- **2026-11-11 19:42** [p3_scaling] P4b result (user): no visible burst with the server event alone (even with Ice Bolt in Fire stance). Chilling Armor state also has cltevent/clteventfunc on the STATE; adding that (P4c).
- **2026-11-11 19:45** [p3_scaling] P4c result (user): still no burst with domissiledamage skill+state events. P4d: probe 3 events across the stances (doactive / domissileattack / hitbymissile = vanilla-proven proof of life).
- **2026-11-11 19:50** [p3_scaling] P4d result (user): Overcharge hitbymissile func 1 returns a visible chilling bolt that damages/chills the attacker (event spawn works for vanilla defensive event). doactive and domissileattack with func 1: nothing. Warlock hex skills use func 36 on domissiledamage to apply auratargetstate to the target (overlay + castoverlay). P4e tries that for a burst on every monster our missiles hit.

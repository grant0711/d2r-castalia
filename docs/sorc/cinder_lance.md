# Cinder Lance (cinder_lance) - experiment log

Design: Fast, thin, long-range fire bolt that pierces 3 enemies. In Conflagration the whole path ignites.

- **2026-11-11 19:15** [p1_pierce_all] Stance work finished (anim_v3 locked). Starting Fire tree with Cinder Lance. P1: CollideKill=0 on firebolt to test pierce-all.
- **2026-11-11 19:19** [p1_pierce_all] P1 result (user): pierce-all works: passes through enemies, damages each, explosion burst on each hit (subtle), full range regardless of hits. Note: exact 'pierce 3' count has no native column (Pierce flag only listens to pierce stat); options: pierce-all with range/damage falloff.
- **2026-11-11 19:24** [p2_fast] P2 result (user): fast+thin feels good but speed 32 is realistic only ~lvl 20; range at lvl 1 too great; hits still read. DESIGN RULE: investment must change the FEEL (velocity, range, AoE size, duration), not just damage.

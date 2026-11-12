# Backdraft (backdraft) - experiment log

Design: Ground fire (r4, 6s) that slows enemies 30%. A later fire spell hitting it detonates it (r6). Strong on arrival, only +3%/lvl; slow and detonation stay useful. Conflagration: detonations chain to adjacent patches.

- **2026-11-12 00:19** [p1_fissure_stun] p1_fissure_stun: fissure overlay didn't feel right for a stun skill; stun should come from a concussive blast/implosion rather than passive ground cracks
- **2026-11-12 00:30** [p2_fiery_implosion] p2_fiery_implosion: sequence looks promising (meteor indicator -> pull -> burst -> ring of fire -> embers), but inherited HitClass=221 caused a purple Warlock shadow_hit overlay on pulled monsters, and needs a movement speed slow to keep pulled monsters at the center
- **2026-11-12 01:04** [p3_fire_pull_slow] p3_fire_pull_slow: purple monster hit overlay gone and slow works, but meteor_target_indicator on the ground feels disconnected from active fire tick damage during the 2s pull
- **2026-11-12 01:13** [p4_ground_fire_patch] p4_ground_fire_patch -> final1: confirmed ground fire patch + inward pull + slow + explosion works and looks great; toned down radius by ~25% (4 + (lvl-1)/7, +2 in Conflagration)

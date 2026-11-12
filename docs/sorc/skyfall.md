# Skyfall (skyfall) - experiment log

Design: Meteor lands on the cursor after a 1.2s delay, r7. First big AoE jump (Blizzard-like). In Conflagration the delay drops to 0.6s.

- **2026-11-12 01:54** [p1_fast_meteor] p1_fast_meteor: skyfall_fire Range=skill('Meteor'.len) evaluated to 0 on client so ground fire vanished after 1 frame, leaving only pCltHitFunc=18's 5-ring nova + 15 sparks and hiding the radius change
- **2026-11-12 02:05** [p2_lingering_crater] p2_lingering_crater: pSrvHitFunc=14 HitSubMissile1 (skyfall_fire) is server-only and never renders on client; volcano explosion was the fissure+nova+sparks

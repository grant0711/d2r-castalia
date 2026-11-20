# Pulse Ring (pulse_ring) - experiment log

Design: Instant expanding lightning ring around the caster whose radius scales with level and expands further in Overcharge. Fizzles in Conflagration or Cryostasis.

- **2026-11-20 16:57** [baseline] p1_pulse_ring built: 22/25 expanding ring (GetHit=1), synced calc3/cltcalc1 velocity adder + Range scaling + Overcharge boost + opposing-stance fizzle, hitfunc 11 -> sigil frenzy (+20..40% speed/IAS, +40..80% FHR, 3s).
- **2026-11-20 17:03** [p1_pulse_ring] p1 in game: lvl 20 OC ring too big (full screen), fizzle works, but ZERO damage (pSrvHitFunc=11 overrides default damage handler with non-damaging spawner!). p2: switch to pSrvHitFunc=4 (damage + HitSubMissile1 on hit), cut max OC reach ~50% (684->338), temporary purple tint to confirm supercharge.
- **2026-11-20 17:08** [p2_radius_and_hit] p2 verified in game: damage, supercharge (purple+fast), and tighter size all look good. Removed debug purple tint -> final1, marked done.

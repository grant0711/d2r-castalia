# Conflagration (conflagration) - experiment log

Design: Castable timed state (60s+10s/lvl). Benefits: +105% FCR and a 3s fire trail on every cast. Penalties: rapid mana decay (hidden mana-burn missile per cast), outgoing damage rolls 25-175%, damage taken re-rolls each cast (+0..60%). Benefit/penalty halves are separate states so Afterglow can keep the benefits. One red orb shows while the benefits are on.

- **2026-11-11 16:41** [r0_single] R0 control built (single diag state per stance). Research: skills.txt gives one aurastate + one stat list per cast; auratargetstate shares the same stat list and targets OTHER units; no native 'cast second skill on self' except movement funcs (Leap 170 calc5/6, Talic Whirlwind 168). Dual self-state from one cast needs a chain primitive (leap-chain or hidden emitter pet) - to be decided.

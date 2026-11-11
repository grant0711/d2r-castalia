# Overcharge (overcharge) - experiment log

Design: Castable timed state (60s+10s/lvl). Boons: +50% lightning skill damage, +40% run/walk, +40% hit recovery. Busts: -50 fire and cold resist. Melee attackers that hit you are shocked (empowered by Conduction). Single mutually exclusive state holding both boon and bust stats (group 13).

- **2026-11-11 21:05** [final2] Tooltip issue (user): next-level panel repeated current value because skill('X'.lvl) does not shift; use lvl. Dodge removed from Overcharge. Added optional diag_scaling variant (retaliation 1 + 1000%/Conduction level).

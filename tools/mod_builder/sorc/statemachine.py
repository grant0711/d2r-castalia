"""
Sorceress HD animation state machine (sorceress_state_machine.json).

Active variants may declare "state_machine": [{"skillIndex": <skill id>, "steps": [{"binding": "cast", "loop": 1}, ...]}].
Each step becomes a PLRMODE_SEQUENCE (modeId 18) state for that skill, with every weapon class bound to
"<class>_<binding>" animations (e.g. hth_cast). This is the same mechanism as the Barbarian Shield Charge states:
a skill row with anim=SQ finds its animation through (skillIndex, stepIndex).
"""
import json
import os

from mod_builder.common import MOD_ROOT, VANILLA_ROOT
from mod_builder.sorc import engine

REL = "data/hd/character/player/sorceress/sorceress_state_machine.json"
CLASSES = ["hth", "bow", "1hs", "1ht", "stf", "2hs", "2ht", "xbw", "1js", "1jt", "1ss", "1st", "ht1", "ht2"]


def build_sorceress_state_machine() -> str:
    dst = os.path.join(MOD_ROOT, REL)
    defs = engine.state_machine_defs()
    if not defs:
        if os.path.exists(dst):
            os.remove(dst)
        return "(sorceress state machine: vanilla)"
    with open(os.path.join(VANILLA_ROOT, REL), "r", encoding="utf-8") as f:
        sm = json.load(f)
    names = {a["name"] for a in sm["animations"]}
    next_id = max(s["stateId"] for s in sm["states"]) + 1
    new_states = []
    for d in defs:
        for step_idx, step in enumerate(d["steps"]):
            bindings = {c: [f"{c}_{step['binding']}"] for c in CLASSES if f"{c}_{step['binding']}" in names}
            new_states.append((next_id, f"AnimationState{next_id:03d}", f"Sorc_Seq_{d['skillIndex']}_{step_idx}",
                               d["skillIndex"], step_idx, int(step.get("loop", 1)), bindings))
            next_id += 1
    for sid, name, internal, skill, step, loop, bindings in new_states:
        sm["states"].append({"type": "AnimationState", "name": name, "_name": internal, "audioId": "",
                             "loopCount": loop, "stateId": sid, "enableVfxAttributes": False, "modeId": 18,
                             "skillIndex": skill, "stepIndex": step, "animationBindings": bindings,
                             "enterEvents": [], "exitEvents": [], "exitBlendType": 0})
    new_ids = [s[0] for s in new_states]
    all_ids = [s["stateId"] for s in sm["states"]]
    for tg in sm["transitions"]:
        for tid in new_ids:
            tg["settings"].append({"type": "AnimationTransitionItem", "name": f"{tg['name']}_transition{tid:03d}",
                                   "crossfadeSeconds": 0.05, "to": tid})
    fast = {1, 2, 3, 7, 8, 9, 10} | set(new_ids)
    for sid, name, *_ in new_states:
        group = f"{name}_transitiongroup"
        settings = [{"type": "AnimationTransitionItem",
                     "name": f"{group}_transition" if i == 0 else f"{group}_transition{to:03d}",
                     "crossfadeSeconds": 0.05 if to in fast else 0.2, "to": to} for i, to in enumerate(all_ids)]
        sm["transitions"].append({"type": "AnimationTransitionGroup", "name": group, "from": sid, "settings": settings})
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(dst, "w", encoding="utf-8") as f:
        json.dump(sm, f, indent=2)
        f.write("\n")
    return dst

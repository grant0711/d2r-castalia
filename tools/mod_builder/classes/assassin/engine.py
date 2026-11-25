"""
Assassin declarative spec engine (thin wrapper over shared ClassSpecEngine).
"""
import os

from mod_builder.classes.spec_engine import STATUSES, TABLE_KEYS, ClassSpecEngine

HERE = os.path.dirname(os.path.abspath(__file__))
SPEC_DIR = os.path.join(HERE, "specs")
STATE_PATH = os.path.join(HERE, "state.json")

ENGINE = ClassSpecEngine(
    cls_key='assassin',
    charclass='ass',
    class_dir=HERE,
    registry_module="mod_builder.classes.assassin.registry",
    env_var='ASS_VARIANTS',
    auto_strings=False,
)

load_state = ENGINE.load_state
save_state = ENGINE.save_state
spec_path = ENGINE.spec_path
default_spec = ENGINE.default_spec
load_spec = ENGINE.load_spec
save_spec = ENGINE.save_spec
env_overrides = ENGINE.env_overrides
active_variant = ENGINE.active_variant
status_of = ENGINE.status_of
active_blocks = ENGINE.active_blocks
apply_table_patches = ENGINE.apply_table_patches
apply_layout = ENGINE.apply_layout
string_updates = ENGINE.string_updates
manifest = ENGINE.manifest
hd_missile_pairs = ENGINE.hd_missile_pairs
animdata_speeds = ENGINE.animdata_speeds
state_machine_defs = ENGINE.state_machine_defs

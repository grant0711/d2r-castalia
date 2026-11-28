"""
TDD test suite for:
  1. Global vs. Isolated Shared Stash (.d2i) routing & crash-safe recovery
  2. Host-locked `shared_stash` flag at campaign creation (immutable via PATCH)
  3. Cumulative Host in-game elapsed time (`total_play_seconds`) across sessions & Hall of Heroes
"""
import os
import sys
import tempfile
import threading
import unittest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
for p in (REPO_ROOT, os.path.join(REPO_ROOT, "tools")):
    if p not in sys.path:
        sys.path.insert(0, p)

from castalia_hub.core import CastaliaHub
from castalia_hub.local_server import start_local_api_server


class TestSharedStashAndTimer(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.data_dir = os.path.join(self.tmp.name, "hub")
        self.save_dir = os.path.join(self.tmp.name, "live_saves")
        os.makedirs(self.save_dir, exist_ok=True)
        self.db_path = os.path.join(self.tmp.name, "campaigns.db")
        self.api_srv, _ = start_local_api_server(self.db_path, host="127.0.0.1", port=0)
        self.api_port = self.api_srv.server_address[1]
        self.api_thread = threading.Thread(target=self.api_srv.serve_forever, daemon=True)
        self.api_thread.start()
        self.hub = CastaliaHub(
            data_dir=self.data_dir,
            api_url=f"http://127.0.0.1:{self.api_port}",
            d2r_save_dir=self.save_dir,
        )

    def tearDown(self):
        self.api_srv.shutdown()
        self.api_srv.server_close()
        self.tmp.cleanup()

    def test_isolated_vs_global_shared_stash_and_crash_recovery(self):
        # Seed a global shared stash in live saves before first swap
        global_stash_live = os.path.join(self.save_dir, "SharedStashSoftCoreV2.d2i")
        with open(global_stash_live, "wb") as f:
            f.write(b"GLOBAL_V1")

        # 1. Isolated campaign (shared_stash=False): starts with NO .d2i in live saves
        self.hub.swap_to_profile("camp-iso", shared_stash=False)
        self.assertFalse(os.path.exists(global_stash_live), "Isolated campaign must NOT inherit global .d2i")
        # Simulate D2R creating a fresh campaign-local stash during play
        with open(global_stash_live, "wb") as f:
            f.write(b"ISO_STASH_DATA")
        self.hub.sync_back_active_profile()
        self.hub._restore_solo_to_live()

        # Verify campaign-local stash was saved to campaign folder & global stash is untouched in live
        iso_stash = os.path.join(self.hub.profile_dir_for("camp-iso"), "SharedStashSoftCoreV2.d2i")
        self.assertTrue(os.path.isfile(iso_stash))
        self.assertEqual(open(iso_stash, "rb").read(), b"ISO_STASH_DATA")
        self.assertEqual(open(global_stash_live, "rb").read(), b"GLOBAL_V1")

        # 2. Global shared-stash campaign (shared_stash=True): loads & updates _global_stash
        self.hub.swap_to_profile("camp-shared", shared_stash=True)
        self.assertEqual(open(global_stash_live, "rb").read(), b"GLOBAL_V1")
        with open(global_stash_live, "wb") as f:
            f.write(b"GLOBAL_V2_UPDATED")
        self.hub.sync_back_active_profile()
        self.hub._restore_solo_to_live()

        # Global stash updated; isolated campaign stash still intact!
        self.assertEqual(open(global_stash_live, "rb").read(), b"GLOBAL_V2_UPDATED")
        self.assertEqual(open(iso_stash, "rb").read(), b"ISO_STASH_DATA")
        shared_camp_d2i = os.path.join(self.hub.profile_dir_for("camp-shared"), "SharedStashSoftCoreV2.d2i")
        self.assertFalse(os.path.exists(shared_camp_d2i), "shared_stash=True campaign must NOT store duplicate .d2i")

        # 3. Crash recovery during isolated campaign: must restore dirty .d2i to camp-iso, NOT _global_stash!
        self.hub.swap_to_profile("camp-iso", shared_stash=False)
        self.assertEqual(open(global_stash_live, "rb").read(), b"ISO_STASH_DATA")
        with open(global_stash_live, "wb") as f:
            f.write(b"ISO_AFTER_CRASH")
        # Simulate sudden crash (no sync_back_active_profile called) -> next launch recovers dirty profile
        self.hub.recover_dirty_profile()
        self.assertEqual(open(iso_stash, "rb").read(), b"ISO_AFTER_CRASH")
        global_store = os.path.join(self.hub.global_stash_dir, "SharedStashSoftCoreV2.d2i")
        self.assertEqual(open(global_store, "rb").read(), b"GLOBAL_V2_UPDATED")

    def test_shared_stash_locked_at_creation_and_host_elapsed_timer(self):
        # Create isolated campaign (default shared_stash=False)
        res = self.hub.create_campaign({
            "title": "Speedrun SSF",
            "ruleset": "standard",
            "castalia_version": "0.4.3",
            "shared_stash": False,
        })
        cid = res["campaign"]["id"]
        self.assertFalse(bool(res["campaign"]["shared_stash"]))
        self.assertEqual(res["campaign"]["total_play_seconds"], 0)

        # Attempting to flip shared_stash via PATCH must be ignored (locked at creation!)
        patched = self.hub.update_campaign(cid, {"shared_stash": True, "schedule_text": "Sat 14:00 UTC"})
        self.assertFalse(bool(patched["shared_stash"]), "shared_stash must stay locked after creation")

        # Accumulate Host elapsed play time across two sessions
        s1 = self.hub.end_session(cid, current_level=15, current_wp="a1n", session_seconds=3600)
        self.assertEqual(s1["total_play_seconds"], 3600)
        s2 = self.hub.end_session(cid, current_level=24, current_wp="a2n", session_seconds=1845)
        self.assertEqual(s2["total_play_seconds"], 5445)

        # Complete campaign -> Hall of Heroes chronicle preserves total_play_seconds & shared_stash
        self.hub.complete_campaign(cid, summary="Hell Baal down!", death_count=2, sessions_played=2)
        hoh = self.hub.list_chronicles()
        self.assertEqual(len(hoh), 1)
        self.assertEqual(hoh[0]["total_play_seconds"], 5445)
        self.assertFalse(bool(hoh[0]["shared_stash"]))

    def test_pilgrimage_vs_open_party_enforcement(self):
        import shutil
        solo_dir = os.path.join(self.hub.profiles_dir, "solo")
        os.makedirs(solo_dir, exist_ok=True)
        from mod_builder import char_manager as cm
        solo_d2s = os.path.join(solo_dir, "ExistingHero.d2s")
        shutil.copy2(os.path.join(REPO_ROOT, "tools", "char_templates", "default.d2s"), solo_d2s)
        cm.configure_character_d2s(solo_d2s, char_name="ExistingHero", class_id=3, level=45, wp_target="a1nm")

        # 1. Pilgrimage mode: forces Level 1 / a1n, blocks imports, locks Host to 1 char
        p_res = self.hub.create_campaign({
            "title": "Pure Pilgrimage",
            "campaign_mode": "pilgrimage",
            "current_level": 50,
            "current_wp": "a3nm",
            "castalia_version": "0.4.3",
        })
        pcid = p_res["campaign"]["id"]
        self.assertEqual(p_res["campaign"]["campaign_mode"], "pilgrimage")
        self.assertEqual(p_res["campaign"]["current_level"], 1)
        self.assertEqual(p_res["campaign"]["current_wp"], "a1n")

        # Cannot flip campaign_mode via PATCH
        patched = self.hub.update_campaign(pcid, {"campaign_mode": "open"})
        self.assertEqual(patched["campaign_mode"], "pilgrimage")

        # Importing existing char into Pilgrimage must raise ValueError
        with self.assertRaises(ValueError):
            self.hub.import_char_to_campaign(pcid, solo_d2s, respec=False)

        # Host can create their first Level 1 char, then CANNOT create a 2nd/substitute char
        self.hub.create_dropin_char(pcid, "OrigPal", "pal", 1, "a1n")
        with self.assertRaises(ValueError):
            self.hub.create_dropin_char(pcid, "SubBarb", "bar", 1, "a1n")

        # 2. Open Party mode: allows Start Level > 1, allows imports, untimed, blocks Hall of Heroes
        o_res = self.hub.create_campaign({
            "title": "NM Farming Party",
            "campaign_mode": "open",
            "current_level": 45,
            "current_wp": "a1nm",
            "castalia_version": "0.4.3",
        })
        ocid = o_res["campaign"]["id"]
        self.assertEqual(o_res["campaign"]["campaign_mode"], "open")
        self.assertEqual(o_res["campaign"]["current_level"], 45)
        imp = self.hub.import_char_to_campaign(ocid, solo_d2s, respec=False)
        self.assertEqual(imp["char_name"], "ExistingHero")
        ended_open = self.hub.end_session(ocid, current_level=46, current_wp="a1nm", session_seconds=1800)
        self.assertEqual(ended_open["total_play_seconds"], 0, "Open Party must not accumulate HoH timer")
        with self.assertRaises(Exception):
            self.hub.complete_campaign(ocid, summary="Should fail", death_count=0, sessions_played=1)

    def test_pilgrimage_vs_open_runtime_config_and_crash_recovery(self):
        import json

        game_dir = os.path.join(self.tmp.name, "game")
        toml_dir = os.path.join(game_dir, "d2rloader", "config")
        os.makedirs(toml_dir, exist_ok=True)
        toml_path = os.path.join(toml_dir, "d2rloader.toml")
        original_toml = (
            "# Header comment\n"
            "[d2rcore.player]\n"
            "enable_respec = true\n"
            "\n"
            "[d2rloader]\n"
            "default_mod = \"othermod\"\n"
            "launch_arguments = \"-w -enablerespec -debug_mode -txt\"\n"
            "show_tcpip_button = false\n"
            "always_generate_new_maps = false\n"
            "\n"
            "[d2rloader.advanced]\n"
            "game_port = 11887\n"
            "allow_global_extensions = true\n"
            "\n"
            "[d2rloader.developer]\n"
            "enable_console = true\n"
            "\n"
            "[d2rloader.developer.logs]\n"
            "enabled = false\n"
            "hosting = false\n"
            "chat_messages = false\n"
        )
        with open(toml_path, "w", encoding="utf-8") as f:
            f.write(original_toml)

        settings_path = os.path.join(self.save_dir, "Settings.json")
        original_settings = {
            "Offline Difficulty Scaling": 8,
            "Max Players": 8,
            "Auto Gold Pickup": 1,
        }
        with open(settings_path, "w", encoding="utf-8") as f:
            json.dump(original_settings, f, indent=4)

        self.hub.config["d2r_game_dir"] = game_dir

        # 1. Pilgrimage Host launch: enforces all 5 Pilgrimage rules + 3 reliability guards
        pilgrimage_camp = {"id": "pilg-1", "campaign_mode": "pilgrimage"}
        snap = self.hub.apply_launch_rules(pilgrimage_camp, is_host=True)
        toml_after = open(toml_path, "r", encoding="utf-8").read()
        self.assertIn("# Header comment", toml_after)
        self.assertIn("enable_respec = false", toml_after)
        self.assertIn("default_mod = \"castalia\"", toml_after)
        self.assertIn("launch_arguments = \"-w -txt\"", toml_after)
        self.assertIn("show_tcpip_button = true", toml_after)
        self.assertIn("always_generate_new_maps = true", toml_after)
        self.assertIn("game_port = 4000", toml_after)
        self.assertIn("allow_global_extensions = false", toml_after)
        self.assertIn("enable_console = false", toml_after)
        self.assertIn("enabled = true", toml_after)
        self.assertIn("hosting = true", toml_after)
        self.assertIn("chat_messages = true", toml_after)
        settings_after = json.load(open(settings_path, "r", encoding="utf-8"))
        self.assertEqual(settings_after["Offline Difficulty Scaling"], 1)
        self.assertEqual(settings_after["Auto Gold Pickup"], 1)

        # Clean restore brings back exact player settings
        self.hub.restore_launch_rules(snap)
        self.assertEqual(open(toml_path, "r", encoding="utf-8").read(), original_toml)
        self.assertEqual(json.load(open(settings_path, "r", encoding="utf-8"))["Offline Difficulty Scaling"], 8)

        # 1b. Pilgrimage Joiner launch: enforces client rules + join port, does NOT touch Host-only settings!
        snap_pjoin = self.hub.apply_launch_rules(pilgrimage_camp, is_host=False, join_port=11887)
        toml_pjoin = open(toml_path, "r", encoding="utf-8").read()
        self.assertIn("enable_respec = false", toml_pjoin)
        self.assertIn("enable_console = false", toml_pjoin)
        self.assertIn("allow_global_extensions = false", toml_pjoin)
        self.assertIn("launch_arguments = \"-w -txt\"", toml_pjoin)
        self.assertIn("game_port = 11887", toml_pjoin)
        # Host-only settings must stay untouched on Joiner:
        self.assertIn("always_generate_new_maps = false", toml_pjoin)
        self.assertIn("chat_messages = false", toml_pjoin)
        self.assertEqual(json.load(open(settings_path, "r", encoding="utf-8"))["Offline Difficulty Scaling"], 8)
        self.hub.restore_launch_rules(snap_pjoin)
        self.assertEqual(open(toml_path, "r", encoding="utf-8").read(), original_toml)

        # 2. Open Party Joiner launch: enables respec + reliability guards, leaves other prefs untouched
        toml_open_base = original_toml.replace("enable_respec = true", "enable_respec = false").replace("game_port = 11887", "game_port = 4000")
        with open(toml_path, "w", encoding="utf-8") as f:
            f.write(toml_open_base)
        open_camp = {"id": "open-1", "campaign_mode": "open"}
        snap_open = self.hub.apply_launch_rules(open_camp, is_host=False, join_port=11887)
        toml_open_after = open(toml_path, "r", encoding="utf-8").read()
        self.assertIn("enable_respec = true", toml_open_after)
        self.assertIn("default_mod = \"castalia\"", toml_open_after)
        self.assertIn("show_tcpip_button = true", toml_open_after)
        self.assertIn("game_port = 11887", toml_open_after)
        # Untouched in Open Party:
        self.assertIn("always_generate_new_maps = false", toml_open_after)
        self.assertIn("allow_global_extensions = true", toml_open_after)
        self.assertIn("enable_console = true", toml_open_after)
        self.assertEqual(json.load(open(settings_path, "r", encoding="utf-8"))["Offline Difficulty Scaling"], 8)
        self.hub.restore_launch_rules(snap_open)
        self.assertEqual(open(toml_path, "r", encoding="utf-8").read(), toml_open_base)

        # 3. Crash recovery: swap_to_profile + persisted launch rules -> recover_dirty_profile restores both files
        with open(toml_path, "w", encoding="utf-8") as f:
            f.write(original_toml)
        self.hub.swap_to_profile("pilg-1", shared_stash=False)
        self.hub.apply_launch_rules(pilgrimage_camp, is_host=True, persist_to_active_profile=True)
        self.assertIn("enable_respec = false", open(toml_path, "r", encoding="utf-8").read())
        self.assertEqual(json.load(open(settings_path, "r", encoding="utf-8"))["Offline Difficulty Scaling"], 1)
        # Simulate crash -> next startup runs recover_dirty_profile()
        self.hub.recover_dirty_profile()
        self.assertEqual(open(toml_path, "r", encoding="utf-8").read(), original_toml)
        self.assertEqual(json.load(open(settings_path, "r", encoding="utf-8"))["Offline Difficulty Scaling"], 8)

    def test_pilgrimage_integrity_hash_and_live_gate(self):
        import hashlib

        # 1. Create Pilgrimage campaign & Host Lv 1 character
        p_res = self.hub.create_campaign({
            "title": "Integrity Pilgrimage",
            "campaign_mode": "pilgrimage",
            "castalia_version": "0.4.3",
        })
        cid = p_res["campaign"]["id"]
        created = self.hub.create_dropin_char(cid, "OrigPal", "pal", 1, "a1n")
        host_d2s = created["path"]
        with open(host_d2s, "rb") as f:
            h1 = hashlib.sha256(f.read()).hexdigest()

        # End Session 1 locks host_char_name + host_char_hash
        rolled = self.hub.end_session(
            cid,
            current_level=5,
            current_wp="a1n",
            session_seconds=900,
            host_char_name="OrigPal",
            host_char_hash=h1,
        )
        self.assertEqual(rolled["host_char_name"], "OrigPal")
        self.assertEqual(rolled["host_char_hash"], h1)

        # Clean before Session 2 -> passes integrity
        chk_ok = self.hub.verify_pilgrimage_integrity(cid)
        self.assertTrue(chk_ok["ok"])

        # Offline Hero Editor tamper (1 byte changed) -> detected!
        with open(host_d2s, "rb") as f:
            orig_bytes = f.read()
        with open(host_d2s, "wb") as f:
            f.write(orig_bytes[:-1] + bytes([orig_bytes[-1] ^ 0xFF]))
        chk_bad = self.hub.verify_pilgrimage_integrity(cid)
        self.assertFalse(chk_bad["ok"])
        self.assertIn("modified", chk_bad["reason"].lower())

        # Restore original bytes, then simulate crash recovery -> must NOT false-positive!
        with open(host_d2s, "wb") as f:
            f.write(orig_bytes)
        self.hub.swap_to_profile(cid, shared_stash=False)
        live_host_d2s = os.path.join(self.save_dir, "OrigPal.d2s")
        with open(live_host_d2s, "wb") as f:
            f.write(orig_bytes[:-1] + bytes([orig_bytes[-1] ^ 0x01]))
        self.hub.recover_dirty_profile()
        chk_crash = self.hub.verify_pilgrimage_integrity(cid)
        self.assertTrue(chk_crash["ok"], "Crash recovery must not falsely flag tampering")

        # 2. Joiner LIVE gate & pre-launch hash gate
        joiner_dir = os.path.join(self.tmp.name, "joiner_hub")
        joiner_saves = os.path.join(self.tmp.name, "joiner_saves")
        os.makedirs(joiner_saves, exist_ok=True)
        joiner = CastaliaHub(
            data_dir=joiner_dir,
            api_url=f"http://127.0.0.1:{self.api_port}",
            d2r_save_dir=joiner_saves,
        )
        joiner.rsvp_campaign(cid, char_name="JoinSorc", char_class="Sorceress", join_mode="drop_in", char_level=5, char_wp="a1n")
        j_created = joiner.create_dropin_char(cid, "JoinSorc", "sor", 5, "a1n")
        j_d2s = j_created["path"]
        with open(j_d2s, "rb") as f:
            jh1 = hashlib.sha256(f.read()).hexdigest()
        joiner.send_telemetry(cid, {
            "char_name": "JoinSorc",
            "char_class": "Sorceress",
            "char_level": 5,
            "char_wp": "a1n",
            "build_summary": "Fire Bolt",
            "char_hash": jh1,
        })

        # Campaign is NOT live yet -> Joiner blocked from launching
        j_wait = joiner.verify_pilgrimage_integrity(cid)
        self.assertFalse(j_wait["ok"])
        self.assertTrue(j_wait.get("blocked"))
        self.assertTrue(j_wait.get("waiting_for_live"))

        # Host goes LIVE -> Joiner with clean .d2s passes!
        self.hub.go_live(cid, "127.0.0.1:4000")
        j_ok = joiner.verify_pilgrimage_integrity(cid)
        self.assertTrue(j_ok["ok"])

        # Joiner tampers with their .d2s -> blocked BEFORE launch!
        with open(j_d2s, "rb") as f:
            jb = f.read()
        with open(j_d2s, "wb") as f:
            f.write(jb[:-1] + bytes([jb[-1] ^ 0xFF]))
        j_bad = joiner.verify_pilgrimage_integrity(cid)
        self.assertFalse(j_bad["ok"])
        self.assertTrue(j_bad.get("blocked"))
        self.assertIn("modified", j_bad["reason"].lower())

        # 3. Invalidated Pilgrimage cannot complete -> Hall of Heroes
        self.hub.update_campaign(cid, {"pilgrimage_invalidated_reason": "Host character modified offline"})
        with self.assertRaises(Exception):
            self.hub.complete_campaign(cid, summary="Voided run", death_count=0, sessions_played=2)


if __name__ == "__main__":
    unittest.main()

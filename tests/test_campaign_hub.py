import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from castalia_hub.core import CastaliaHub
from castalia_hub.d2s_telemetry import generate_dropin_character, parse_d2s_telemetry
from castalia_hub.local_server import start_local_api_server


class TestCampaignHub(unittest.TestCase):
    def setUp(self):
        os.environ["CASTALIA_API_QUIET"] = "1"
        self.tmp = tempfile.mkdtemp(prefix="castalia_hub_test_")
        self.db_path = os.path.join(self.tmp, "campaigns.db")
        self.game_dir = os.path.join(self.tmp, "game")
        self.save_dir = os.path.join(self.tmp, "live_saves")
        self.hub_dir = os.path.join(self.tmp, "hub_data")
        os.makedirs(os.path.join(self.game_dir, "mods", "castalia", "castalia.mpq"), exist_ok=True)
        os.makedirs(self.save_dir, exist_ok=True)
        with open(os.path.join(self.game_dir, "mods", "castalia", "castalia.mpq", "castalia_version.json"), "w") as f:
            json.dump({"version": "0.3.0"}, f)
        with open(os.path.join(self.save_dir, "Settings.json"), "w") as f:
            f.write('{"volume": 100}\n')

        self.srv, self.db = start_local_api_server(self.db_path, host="127.0.0.1", port=0)
        self.port = self.srv.server_address[1]
        self.api_url = f"http://127.0.0.1:{self.port}"
        self.srv_thread = threading.Thread(target=self.srv.serve_forever, daemon=True)
        self.srv_thread.start()

        self.hub = CastaliaHub(
            data_dir=self.hub_dir,
            api_url=self.api_url,
            d2r_game_dir=self.game_dir,
            d2r_save_dir=self.save_dir,
        )

    def tearDown(self):
        self.srv.shutdown()
        self.srv.server_close()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_dropin_generation_and_d2s_telemetry_parsing(self):
        pdir = self.hub.profile_dir_for("test-camp")
        telem = generate_dropin_character(pdir, "Lyra", "sor", 48, "a3nm")
        self.assertEqual(telem["char_name"], "Lyra")
        self.assertEqual(telem["char_class"], "sor")
        self.assertEqual(telem["char_level"], 48)
        self.assertEqual(telem["char_wp"], "a3nm")
        self.assertFalse(telem["hell_baal_cleared"])
        self.assertTrue(os.path.isfile(os.path.join(pdir, "Lyra.d2s")))

        # Verify Level 1 fresh starting character generation (ready for Multiplayer immediately)
        lvl1_telem = generate_dropin_character(pdir, "FreshPal", "pal", 1, "a1n")
        self.assertEqual(lvl1_telem["char_level"], 1)
        self.assertEqual(lvl1_telem["char_wp"], "a1n")
        self.assertFalse(lvl1_telem["hell_baal_cleared"])
        self.assertTrue(os.path.isfile(os.path.join(pdir, "FreshPal.d2s")))

        # Verify Hell Baal completion detection on an 'all' character
        baal_telem = generate_dropin_character(pdir, "Champion", "pal", 75, "all")
        self.assertTrue(baal_telem["hell_baal_cleared"])

        # Re-parse via parse_d2s_telemetry directly
        reparsed = parse_d2s_telemetry(os.path.join(pdir, "Lyra.d2s"))
        self.assertEqual(reparsed["char_level"], 48)
        self.assertEqual(reparsed["char_wp"], "a3nm")

    def test_crash_safe_per_campaign_save_swapper(self):
        # Seed a pre-existing solo save in live_saves
        with open(os.path.join(self.save_dir, "SoloHero.d2s"), "wb") as f:
            f.write(b"SOLO_DATA")

        # Seed a character in campaign-A profile
        camp_a = self.hub.profile_dir_for("camp-a")
        with open(os.path.join(camp_a, "CampAHero.d2s"), "wb") as f:
            f.write(b"CAMPA_V1")

        # Swap to camp-a -> SoloHero migrated to profiles/solo, Settings.json preserved
        self.hub.swap_to_profile("camp-a")
        self.assertTrue(os.path.isfile(os.path.join(self.save_dir, "Settings.json")))
        self.assertTrue(os.path.isfile(os.path.join(self.save_dir, "CampAHero.d2s")))
        self.assertFalse(os.path.isfile(os.path.join(self.save_dir, "SoloHero.d2s")))
        self.assertTrue(os.path.isfile(os.path.join(self.hub.profile_dir_for("solo"), "SoloHero.d2s")))

        # Simulate in-game progress & sudden PC crash (active_profile.json stays on disk!)
        with open(os.path.join(self.save_dir, "CampAHero.d2s"), "wb") as f:
            f.write(b"CAMPA_V2_AFTER_PLAY")

        # Next swap to solo must first recover CAMPA_V2_AFTER_PLAY back to profiles/campaign-camp-a/
        self.hub.swap_to_profile("solo")
        with open(os.path.join(camp_a, "CampAHero.d2s"), "rb") as f:
            self.assertEqual(f.read(), b"CAMPA_V2_AFTER_PLAY")
        self.assertTrue(os.path.isfile(os.path.join(self.save_dir, "SoloHero.d2s")))
        self.assertFalse(os.path.isfile(os.path.join(self.save_dir, "CampAHero.d2s")))
        self.hub.sync_back_active_profile()
        self.assertFalse(os.path.isfile(self.hub.active_profile_path))

    def test_full_campaign_api_lifecycle_and_auth_gating(self):
        # 1. Host creates a 2-seat campaign pinned to v0.3.0
        created = self.hub.create_campaign({
            "title": "Thursday Pilgrimage",
            "description": "Grounded co-op run",
            "ruleset": "standard",
            "castalia_version": "0.3.0",
            "current_level": 48,
            "current_wp": "a3nm",
            "max_seats": 2,
            "schedule_text": "Thu 8 PM EST",
            "next_session_utc": "2026-11-26T20:00:00Z",
            "recurrence_days": 7,
        })
        cid = created["campaign"]["id"]
        self.assertEqual(created["campaign"]["castalia_version"], "0.3.0")

        # 2. Go live with Game ID -> public GET must NOT leak live_join_info
        self.hub.go_live(cid, "CST-4821")
        intent_path = self.hub.write_launch_intent(self.hub.get_campaign(cid), is_host=True)
        with open(intent_path, "r", encoding="utf-8") as f:
            intent = json.load(f)
        self.assertEqual(intent["mode"], "host")
        self.assertEqual(intent["difficulty"], 1)  # a3nm -> Nightmare (1)
        self.assertEqual(intent["max_players"], 2)
        self.assertTrue(intent["unlisted"])
        self.assertFalse(intent["lan_only"])
        self.hub.write_launch_intent(None, False)
        self.assertFalse(os.path.exists(intent_path))

        pub_list = self.hub.list_campaigns()
        self.assertEqual(len(pub_list), 1)
        self.assertIsNone(pub_list[0]["live_join_info"])

        # Host sees live_join_info
        host_view = self.hub.get_campaign(cid)
        self.assertEqual(host_view["live_join_info"], "CST-4821")

        # 3. Second hub (different player) cannot see live_join_info until RSVPed
        p2_hub = CastaliaHub(
            data_dir=os.path.join(self.tmp, "p2_hub"),
            api_url=self.api_url,
            d2r_game_dir=self.game_dir,
            d2r_save_dir=os.path.join(self.tmp, "p2_saves"),
        )
        self.assertIsNone(p2_hub.get_campaign(cid)["live_join_info"])

        telem = p2_hub.create_dropin_char(cid, "Lyra", "sor", 48, "a3nm")
        p2_rsvp = p2_hub.rsvp_campaign(
            cid,
            char_name=telem["char_name"],
            char_class=telem["char_class"],
            join_mode="drop_in",
            char_level=telem["char_level"],
            char_wp=telem["char_wp"],
            build_summary="Lightning / Conduction",
            player_name="Alex",
        )
        self.assertEqual(p2_rsvp["rsvp"]["status"], "confirmed")
        self.assertEqual(p2_hub.get_campaign(cid)["live_join_info"], "CST-4821")

        # 4. Telemetry update & end-session rollover (+7 days)
        p2_hub.send_telemetry(cid, {
            "char_name": "Lyra",
            "char_class": "sor",
            "char_level": 52,
            "char_wp": "a4nm",
            "build_summary": "Spearbolt / Conduction",
        })
        ended = self.hub.end_session(cid, current_level=52, current_wp="a4nm")
        self.assertEqual(ended["current_level"], 52)
        self.assertEqual(ended["current_wp"], "a4nm")
        self.assertEqual(ended["next_session_utc"], "2026-12-03T20:00:00+00:00")
        self.assertIsNone(ended["live_join_info"])
        self.assertEqual(ended["rsvps"][0]["char_level"], 52)
        self.assertEqual(ended["rsvps"][0]["build_summary"], "Spearbolt / Conduction")

        # 5. Complete campaign -> appears in Hall of Heroes
        self.hub.complete_campaign(cid, summary="Hell Baal fell in 8 sessions!", death_count=9, sessions_played=8)
        ch = self.hub.list_chronicles()
        self.assertEqual(len(ch), 1)
        self.assertEqual(ch[0]["death_count"], 9)
        self.assertEqual(len(ch[0]["party_roster"]), 1)

    def test_playit_host_port_parsing_and_d2rloader_toml_port_sync(self):
        self.assertEqual(CastaliaHub.parse_host_port("147.185.221.21:14322"), ("147.185.221.21", 14322))
        self.assertEqual(CastaliaHub.parse_host_port("my-tunnel.gl.at.ply.gg:25565"), ("my-tunnel.gl.at.ply.gg", 25565))
        self.assertEqual(CastaliaHub.parse_host_port("99.184.66.94"), ("99.184.66.94", 4000))

        toml_dir = os.path.join(self.game_dir, "d2rloader", "config")
        os.makedirs(toml_dir, exist_ok=True)
        toml_path = os.path.join(toml_dir, "d2rloader.toml")
        with open(toml_path, "w", encoding="utf-8") as f:
            f.write("[d2rloader.advanced]\ngame_port = 4000\nautomatic_port_mapping = false\n")

        prev = self.hub.set_d2rloader_game_port(14322)
        self.assertEqual(prev, 4000)
        with open(toml_path, "r", encoding="utf-8") as f:
            self.assertIn("game_port = 14322", f.read())

        self.hub.set_d2rloader_game_port(prev)
        with open(toml_path, "r", encoding="utf-8") as f:
            self.assertIn("game_port = 4000", f.read())

    def test_cli_json_smoke(self):
        cli = os.path.join(REPO_ROOT, "bin", "d2r-campaign")
        res = subprocess.run(
            [
                sys.executable, cli,
                "--api", self.api_url,
                "--data-dir", self.hub_dir,
                "--json",
                "create",
                "--title", "CLI One Shot",
                "--ruleset", "oneshot",
                "--version", "0.3.0",
                "--level", "60",
                "--wp", "a1h",
            ],
            capture_output=True, text=True, check=True,
        )
        created = json.loads(res.stdout)
        cid = created["campaign"]["id"]
        self.assertEqual(created["campaign"]["current_level"], 60)

        res2 = subprocess.run(
            [sys.executable, cli, "--api", self.api_url, "--data-dir", self.hub_dir, "--json", "list"],
            capture_output=True, text=True, check=True,
        )
        items = json.loads(res2.stdout)
        self.assertTrue(any(x["id"] == cid for x in items))


if __name__ == "__main__":
    unittest.main()

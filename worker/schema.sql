CREATE TABLE IF NOT EXISTS campaigns (
  id                TEXT PRIMARY KEY,
  host_name         TEXT NOT NULL,
  host_token_hash   TEXT NOT NULL,
  title             TEXT NOT NULL,
  description       TEXT NOT NULL,
  ruleset           TEXT NOT NULL DEFAULT 'standard',
  castalia_version  TEXT NOT NULL,
  current_level     INTEGER NOT NULL DEFAULT 1,
  current_wp        TEXT NOT NULL DEFAULT 'a1n',
  has_cube          INTEGER NOT NULL DEFAULT 0,
  host_progress_b64 TEXT,
  shared_stash      INTEGER NOT NULL DEFAULT 0,
  campaign_mode     TEXT NOT NULL DEFAULT 'pilgrimage',
  total_play_seconds INTEGER NOT NULL DEFAULT 0,
  host_char_name    TEXT,
  host_char_hash    TEXT,
  pilgrimage_invalidated_reason TEXT,
  max_seats         INTEGER NOT NULL DEFAULT 5,
  schedule_text     TEXT NOT NULL,
  recurrence_days   INTEGER DEFAULT 7,
  next_session_utc  TEXT,
  status            TEXT NOT NULL DEFAULT 'recruiting',
  live_join_info    TEXT,
  discord_msg_id    TEXT,
  created_at        TEXT NOT NULL,
  updated_at        TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS rsvps (
  id                TEXT PRIMARY KEY,
  campaign_id       TEXT NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
  session_utc       TEXT NOT NULL,
  player_name       TEXT NOT NULL,
  rsvp_token_hash   TEXT NOT NULL,
  join_mode         TEXT NOT NULL DEFAULT 'returning',
  char_name         TEXT NOT NULL,
  char_class        TEXT NOT NULL,
  char_level        INTEGER NOT NULL DEFAULT 1,
  char_wp           TEXT NOT NULL DEFAULT 'a1n',
  build_summary     TEXT NOT NULL DEFAULT '',
  char_hash         TEXT,
  status            TEXT NOT NULL DEFAULT 'confirmed',
  created_at        TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS chronicles (
  id                TEXT PRIMARY KEY,
  campaign_id       TEXT NOT NULL REFERENCES campaigns(id),
  completed_at      TEXT NOT NULL,
  sessions_played   INTEGER NOT NULL DEFAULT 1,
  death_count       INTEGER NOT NULL DEFAULT 0,
  total_play_seconds INTEGER NOT NULL DEFAULT 0,
  party_roster_json TEXT NOT NULL,
  summary           TEXT NOT NULL,
  screenshot_url    TEXT
);

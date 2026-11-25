/**
 * Castalia Campaign Hub — Cloudflare Workers + D1 REST API
 * Mirrors castalia_hub/local_server.py (docs/systems/LAUNCHER_SPEC.md).
 */

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "Content-Type, Authorization",
  "Access-Control-Allow-Methods": "GET, POST, PATCH, DELETE, OPTIONS",
};

function jsonResp(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json", ...CORS },
  });
}

async function sha256Hex(str) {
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(str));
  return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

function randHex(bytes = 16) {
  const arr = new Uint8Array(bytes);
  crypto.getRandomValues(arr);
  return [...arr].map((b) => b.toString(16).padStart(2, "0")).join("");
}

function slugify(title) {
  const base = (title || "campaign").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 24) || "campaign";
  return `${base}-${randHex(2)}`;
}

function bearerToken(req) {
  const h = req.headers.get("Authorization") || "";
  return h.startsWith("Bearer ") ? h.slice(7).trim() : null;
}

function sanitizeCampaign(row, includeLive, rsvps) {
  const { host_token_hash, ...rest } = row;
  if (!includeLive || rest.status !== "live") rest.live_join_info = null;
  if (rsvps) {
    rest.rsvps = rsvps;
    rest.confirmed_seats = rsvps.filter((r) => r.status === "confirmed").length;
  }
  return rest;
}

function sanitizeRsvp(row) {
  const { rsvp_token_hash, ...rest } = row;
  return rest;
}

async function syncDiscord(env, camp, confirmed) {
  const webhook = env.DISCORD_CAMPAIGN_WEBHOOK_URL;
  if (!webhook) return camp.discord_msg_id || null;
  const label = { live: "🟢 LIVE", recruiting: "🟡 Recruiting", active: "🔵 Active", completed: "🏆 Completed" }[camp.status] || camp.status;
  const embed = {
    title: `${label} — ${camp.title} (v${camp.castalia_version})`,
    description: (camp.description || "").slice(0, 1500),
    color: camp.status === "live" ? 0x43b581 : 0xc89b3c,
    fields: [
      { name: "Host", value: camp.host_name, inline: true },
      { name: "Ruleset", value: camp.ruleset, inline: true },
      { name: "Seats", value: `${confirmed}/${camp.max_seats}`, inline: true },
      { name: "Progress", value: `Lvl ${camp.current_level} · \`${camp.current_wp}\``, inline: true },
      { name: "Schedule", value: camp.schedule_text, inline: true },
    ],
  };
  const url = camp.discord_msg_id ? `${webhook}/messages/${camp.discord_msg_id}` : `${webhook}?wait=true`;
  const resp = await fetch(url, {
    method: camp.discord_msg_id ? "PATCH" : "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ embeds: [embed] }),
  });
  if (!resp.ok) return camp.discord_msg_id || null;
  const data = await resp.json().catch(() => ({}));
  return data.id || camp.discord_msg_id || null;
}

export default {
  async fetch(req, env) {
    if (req.method === "OPTIONS") return jsonResp({ ok: true });
    const url = new URL(req.url);
    const parts = url.pathname.replace(/^\/|\/$/g, "").split("/").filter(Boolean);
    const bearer = bearerToken(req);
    const now = new Date().toISOString().replace(/\.\d+Z$/, "Z");

    try {
      // GET /api/campaigns
      if (parts.length === 2 && parts[0] === "api" && parts[1] === "campaigns" && req.method === "GET") {
        const ruleset = url.searchParams.get("ruleset");
        const openOnly = url.searchParams.get("open_seats") === "true";
        const { results } = await env.DB.prepare(
          "SELECT * FROM campaigns WHERE status IN ('recruiting','active','live') ORDER BY updated_at DESC"
        ).all();
        const out = [];
        for (const r of results) {
          if (ruleset && r.ruleset !== ruleset) continue;
          const rsvps = (
            await env.DB.prepare("SELECT * FROM rsvps WHERE campaign_id = ? AND status != 'cancelled' ORDER BY created_at ASC")
              .bind(r.id).all()
          ).results.map(sanitizeRsvp);
          const item = sanitizeCampaign(r, false, rsvps);
          if (openOnly && item.confirmed_seats >= item.max_seats) continue;
          out.push(item);
        }
        return jsonResp(out);
      }

      // POST /api/campaigns
      if (parts.length === 2 && parts[0] === "api" && parts[1] === "campaigns" && req.method === "POST") {
        const body = await req.json();
        const cid = slugify(body.title);
        const hostToken = randHex(24);
        const tokenHash = await sha256Hex(hostToken);
        await env.DB.prepare(
          `INSERT INTO campaigns (
            id, host_name, host_token_hash, title, description, ruleset,
            castalia_version, current_level, current_wp, max_seats,
            schedule_text, recurrence_days, next_session_utc, status, created_at, updated_at
          ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'recruiting', ?, ?)`
        ).bind(
          cid,
          (body.host_name || "Host").trim(),
          tokenHash,
          (body.title || "Untitled Campaign").trim(),
          (body.description || "").trim(),
          (body.ruleset || "standard").trim(),
          String(body.castalia_version || "0.3.0").replace(/^v/, ""),
          Number(body.current_level || 1),
          (body.current_wp || "a1n").trim(),
          Math.max(2, Math.min(8, Number(body.max_seats || 5))),
          (body.schedule_text || "Weekly").trim(),
          body.recurrence_days ?? 7,
          body.next_session_utc || null,
          now,
          now
        ).run();
        const row = await env.DB.prepare("SELECT * FROM campaigns WHERE id = ?").bind(cid).first();
        const camp = sanitizeCampaign(row, false, []);
        const msgId = await syncDiscord(env, camp, 0);
        if (msgId) {
          await env.DB.prepare("UPDATE campaigns SET discord_msg_id = ? WHERE id = ?").bind(msgId, cid).run();
          camp.discord_msg_id = msgId;
        }
        return jsonResp({ campaign: camp, host_token: hostToken }, 201);
      }

      // GET /api/chronicles
      if (parts.length === 2 && parts[0] === "api" && parts[1] === "chronicles" && req.method === "GET") {
        const { results } = await env.DB.prepare(
          `SELECT ch.*, c.title, c.host_name, c.ruleset, c.castalia_version
           FROM chronicles ch JOIN campaigns c ON c.id = ch.campaign_id
           ORDER BY ch.completed_at DESC`
        ).all();
        return jsonResp(results.map((r) => ({ ...r, party_roster: JSON.parse(r.party_roster_json || "[]") })));
      }

      // /api/campaigns/:id/...
      if (parts.length >= 3 && parts[0] === "api" && parts[1] === "campaigns") {
        const cid = parts[2];
        const row = await env.DB.prepare("SELECT * FROM campaigns WHERE id = ?").bind(cid).first();
        if (!row) return jsonResp({ error: "not_found" }, 404);
        const bearerHash = bearer ? await sha256Hex(bearer) : null;
        const isHost = bearerHash && bearerHash === row.host_token_hash;

        if (parts.length === 3 && req.method === "GET") {
          const rsvpRows = (
            await env.DB.prepare("SELECT * FROM rsvps WHERE campaign_id = ? AND status != 'cancelled' ORDER BY created_at ASC")
              .bind(cid).all()
          ).results;
          const canSeeLive = isHost || (bearerHash && rsvpRows.some((x) => x.rsvp_token_hash === bearerHash && x.status === "confirmed"));
          return jsonResp(sanitizeCampaign(row, canSeeLive, rsvpRows.map(sanitizeRsvp)));
        }

        if (parts.length === 4 && parts[3] === "rsvp" && req.method === "POST") {
          const body = await req.json();
          const rid = `rsvp-${randHex(4)}`;
          const rsvpToken = randHex(24);
          const countRow = await env.DB.prepare(
            "SELECT COUNT(*) AS cnt FROM rsvps WHERE campaign_id = ? AND status = 'confirmed'"
          ).bind(cid).first();
          const status = countRow.cnt < row.max_seats ? "confirmed" : "waitlist";
          await env.DB.prepare(
            `INSERT INTO rsvps (
              id, campaign_id, session_utc, player_name, rsvp_token_hash,
              join_mode, char_name, char_class, char_level, char_wp, build_summary, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`
          ).bind(
            rid, cid, row.next_session_utc || now,
            (body.player_name || "Player").trim(), await sha256Hex(rsvpToken),
            body.join_mode || "returning", (body.char_name || "Hero").slice(0, 15),
            (body.char_class || "pal").toLowerCase(), Number(body.char_level || row.current_level),
            body.char_wp || row.current_wp, body.build_summary || "", status, now
          ).run();
          const rrow = await env.DB.prepare("SELECT * FROM rsvps WHERE id = ?").bind(rid).first();
          return jsonResp({ rsvp: sanitizeRsvp(rrow), rsvp_token: rsvpToken }, 201);
        }

        if (parts.length === 6 && parts[3] === "rsvp" && parts[5] === "telemetry" && req.method === "PATCH") {
          const rid = parts[4];
          const rrow = await env.DB.prepare("SELECT * FROM rsvps WHERE id = ? AND campaign_id = ?").bind(rid, cid).first();
          if (!rrow) return jsonResp({ error: "not_found" }, 404);
          if (!isHost && bearerHash !== rrow.rsvp_token_hash) return jsonResp({ error: "forbidden" }, 403);
          const body = await req.json();
          await env.DB.prepare(
            "UPDATE rsvps SET char_name = ?, char_class = ?, char_level = ?, char_wp = ?, build_summary = ? WHERE id = ?"
          ).bind(
            (body.char_name || rrow.char_name).slice(0, 15),
            (body.char_class || rrow.char_class).toLowerCase(),
            Number(body.char_level ?? rrow.char_level),
            body.char_wp || rrow.char_wp,
            body.build_summary ?? rrow.build_summary,
            rid
          ).run();
          const updated = await env.DB.prepare("SELECT * FROM rsvps WHERE id = ?").bind(rid).first();
          return jsonResp(sanitizeRsvp(updated));
        }

        if (parts.length === 5 && parts[3] === "rsvp" && req.method === "DELETE") {
          const rid = parts[4];
          const rrow = await env.DB.prepare("SELECT * FROM rsvps WHERE id = ? AND campaign_id = ?").bind(rid, cid).first();
          if (!rrow) return jsonResp({ error: "not_found" }, 404);
          if (!isHost && bearerHash !== rrow.rsvp_token_hash) return jsonResp({ error: "forbidden" }, 403);
          await env.DB.prepare("UPDATE rsvps SET status = 'cancelled' WHERE id = ?").bind(rid).run();
          return jsonResp({ cancelled: rid });
        }

        // Host-only routes below
        if (!isHost) return jsonResp({ error: "host_token_required" }, 403);

        if (parts.length === 4 && parts[3] === "go-live" && req.method === "POST") {
          const body = await req.json();
          await env.DB.prepare("UPDATE campaigns SET status = 'live', live_join_info = ?, updated_at = ? WHERE id = ?")
            .bind((body.live_join_info || "").trim(), now, cid).run();
          const updated = await env.DB.prepare("SELECT * FROM campaigns WHERE id = ?").bind(cid).first();
          const camp = sanitizeCampaign(updated, true);
          await syncDiscord(env, camp, 0);
          return jsonResp(camp);
        }

        if (parts.length === 4 && parts[3] === "end-session" && req.method === "POST") {
          const body = await req.json();
          let nextUtc = body.next_session_utc || row.next_session_utc;
          if (!body.next_session_utc && row.next_session_utc && row.recurrence_days) {
            const d = new Date(row.next_session_utc);
            d.setUTCDate(d.getUTCDate() + Number(row.recurrence_days));
            nextUtc = d.toISOString().replace(/\.\d+Z$/, "Z");
          }
          await env.DB.prepare(
            "UPDATE campaigns SET status = 'active', live_join_info = NULL, current_level = ?, current_wp = ?, next_session_utc = ?, updated_at = ? WHERE id = ?"
          ).bind(Number(body.current_level ?? row.current_level), body.current_wp || row.current_wp, nextUtc, now, cid).run();
          const updated = await env.DB.prepare("SELECT * FROM campaigns WHERE id = ?").bind(cid).first();
          return jsonResp(sanitizeCampaign(updated, false));
        }

        if (parts.length === 3 && req.method === "PATCH") {
          const body = await req.json();
          const fields = ["title", "description", "ruleset", "castalia_version", "current_level", "current_wp", "max_seats", "schedule_text", "recurrence_days", "next_session_utc", "status"];
          const sets = [];
          const vals = [];
          for (const f of fields) {
            if (body[f] !== undefined && body[f] !== null) {
              sets.push(`${f} = ?`);
              vals.push(f === "castalia_version" ? String(body[f]).replace(/^v/, "") : body[f]);
            }
          }
          sets.push("updated_at = ?");
          vals.push(now, cid);
          await env.DB.prepare(`UPDATE campaigns SET ${sets.join(", ")} WHERE id = ?`).bind(...vals).run();
          const updated = await env.DB.prepare("SELECT * FROM campaigns WHERE id = ?").bind(cid).first();
          return jsonResp(sanitizeCampaign(updated, true));
        }

        if (parts.length === 4 && parts[3] === "complete" && req.method === "POST") {
          const body = await req.json();
          const rsvps = (
            await env.DB.prepare("SELECT * FROM rsvps WHERE campaign_id = ? AND status = 'confirmed'").bind(cid).all()
          ).results.map(sanitizeRsvp);
          const chid = `chron-${randHex(4)}`;
          await env.DB.prepare("UPDATE campaigns SET status = 'completed', live_join_info = NULL, updated_at = ? WHERE id = ?")
            .bind(now, cid).run();
          await env.DB.prepare(
            "INSERT INTO chronicles (id, campaign_id, completed_at, sessions_played, death_count, party_roster_json, summary, screenshot_url) VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
          ).bind(chid, cid, now, Number(body.sessions_played || 1), Number(body.death_count || 0), JSON.stringify(rsvps), body.summary || "", body.screenshot_url || null).run();
          return jsonResp({ id: chid, campaign_id: cid, party_roster: rsvps });
        }
      }

      return jsonResp({ error: "not_found" }, 404);
    } catch (e) {
      return jsonResp({ error: String(e) }, 400);
    }
  },
};

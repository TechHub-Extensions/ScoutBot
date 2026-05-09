/**
 * ScoutBot Distribution Layer — Backend Session Manager
 * Uses whatsapp-web.js to manage a master WA session.
 * Joins groups via invite links and stores Group JIDs to SQLite.
 */

const express = require("express");
const cors = require("cors");
const { Client, LocalAuth } = require("whatsapp-web.js");
const qrcode = require("qrcode");
const Database = require("better-sqlite3");
const path = require("path");
const fs = require("fs");

const app = express();
app.use(cors());
app.use(express.json());

// ── Database Setup ──────────────────────────────────────────────────────────
const DB_PATH = path.join(__dirname, "scoutbot.db");
const db = new Database(DB_PATH);

db.exec(`
  CREATE TABLE IF NOT EXISTS campus_groups (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    campus_name TEXT    NOT NULL,
    invite_link TEXT    NOT NULL UNIQUE,
    group_jid   TEXT    UNIQUE,
    group_name  TEXT,
    joined_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_active   INTEGER DEFAULT 1
  );

  CREATE TABLE IF NOT EXISTS broadcast_log (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    group_jid     TEXT    NOT NULL,
    opportunity_title TEXT,
    sent_at       DATETIME DEFAULT CURRENT_TIMESTAMP,
    status        TEXT DEFAULT 'sent'
  );
`);

// ── WhatsApp Client ─────────────────────────────────────────────────────────
let waClient = null;
let clientReady = false;
let qrCodeData = null;
let initializationError = null;

function initWhatsApp() {
  console.log("🚀 Initializing WhatsApp client...");

  waClient = new Client({
    authStrategy: new LocalAuth({ dataPath: path.join(__dirname, ".wwebjs_auth") }),
    puppeteer: {
      headless: true,
      args: [
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-dev-shm-usage",
        "--disable-accelerated-2d-canvas",
        "--no-first-run",
        "--no-zygote",
        "--disable-gpu",
      ],
    },
  });

  waClient.on("qr", async (qr) => {
    console.log("📱 QR Code generated — scan with WhatsApp");
    qrCodeData = await qrcode.toDataURL(qr);
    clientReady = false;
  });

  waClient.on("ready", () => {
    console.log("✅ WhatsApp client is ready!");
    clientReady = true;
    qrCodeData = null;
    initializationError = null;
  });

  waClient.on("auth_failure", (msg) => {
    console.error("❌ WhatsApp auth failure:", msg);
    initializationError = msg;
    clientReady = false;
  });

  waClient.on("disconnected", (reason) => {
    console.warn("⚠️  WhatsApp disconnected:", reason);
    clientReady = false;
    // Auto-reinitialize after 5s
    setTimeout(initWhatsApp, 5000);
  });

  waClient.initialize().catch((err) => {
    console.error("WhatsApp init error:", err.message);
    initializationError = err.message;
  });
}

initWhatsApp();

// ── Helpers ─────────────────────────────────────────────────────────────────

/**
 * Extracts the invite code from a full chat.whatsapp.com/... URL.
 */
function extractInviteCode(link) {
  // Captures the ID even if it contains dashes, underscores, or the /invite/ path
  const match = link.match(/chat\.whatsapp\.com\/(?:invite\/)?([a-zA-Z0-9_-]+)/i);
  return match ? match[1] : null;
}

// ── Routes ───────────────────────────────────────────────────────────────────

// GET /status — session health check + QR if needed
app.get("/status", (req, res) => {
  res.json({
    ready: clientReady,
    qr: qrCodeData,
    error: initializationError,
  });
});

// POST /register — accept campus + invite link, join group, save JID
app.post("/register", async (req, res) => {
  const { campus_name, invite_link } = req.body;

  if (!campus_name || !invite_link) {
    return res.status(400).json({ error: "campus_name and invite_link are required." });
  }

  const inviteCode = extractInviteCode(invite_link);
  if (!inviteCode) {
    return res.status(400).json({ error: "Invalid WhatsApp invite link format." });
  }

  // Check if already registered
  const existing = db
    .prepare("SELECT * FROM campus_groups WHERE invite_link = ?")
    .get(invite_link);

  if (existing && existing.group_jid) {
    return res.json({
      success: true,
      message: "Group already registered.",
      group_jid: existing.group_jid,
      group_name: existing.group_name,
      already_existed: true,
    });
  }

  if (!clientReady) {
    // Save as pending — will be joined when client is ready
    db.prepare(
      "INSERT OR IGNORE INTO campus_groups (campus_name, invite_link) VALUES (?, ?)"
    ).run(campus_name, invite_link);

    return res.status(202).json({
      success: false,
      pending: true,
      message: "WhatsApp session not ready. Campus registered — will be joined when session connects.",
    });
  }

  try {
    // Accept the invite and get group info
    const groupId = await waClient.acceptInvite(inviteCode);

    // Fetch group metadata to get the display name
    let groupName = campus_name + " Group";
    try {
      const chat = await waClient.getChatById(groupId);
      groupName = chat.name || groupName;
    } catch (_) {}

    // Upsert into DB
    db.prepare(
      `INSERT INTO campus_groups (campus_name, invite_link, group_jid, group_name)
       VALUES (?, ?, ?, ?)
       ON CONFLICT(invite_link) DO UPDATE SET
         group_jid  = excluded.group_jid,
         group_name = excluded.group_name`
    ).run(campus_name, invite_link, groupId, groupName);

    console.log(`✅ Joined group: ${groupName} (${groupId}) for campus: ${campus_name}`);

    return res.json({
      success: true,
      message: `Successfully joined "${groupName}"`,
      group_jid: groupId,
      group_name: groupName,
      invite_link,
    });
  } catch (err) {
    console.error("Error joining group:", err.message);

    // Still save the record even if join failed (may already be a member)
    db.prepare(
      "INSERT OR IGNORE INTO campus_groups (campus_name, invite_link) VALUES (?, ?)"
    ).run(campus_name, invite_link);

    return res.status(500).json({
      error: "Failed to join WhatsApp group. You may already be a member, or the link may be expired.",
      detail: err.message,
    });
  }
});

// GET /groups — list all registered groups (for admin / broadcast.py)
app.get("/groups", (req, res) => {
  const groups = db
    .prepare("SELECT * FROM campus_groups WHERE is_active = 1 ORDER BY joined_at DESC")
    .all();
  res.json({ groups });
});

// DELETE /groups/:id — deactivate a group
app.delete("/groups/:id", (req, res) => {
  db.prepare("UPDATE campus_groups SET is_active = 0 WHERE id = ?").run(req.params.id);
  res.json({ success: true });
});

// GET /groups/export — export JIDs as JSON for broadcast.py
app.get("/groups/export", (req, res) => {
  const jids = db
    .prepare("SELECT group_jid, campus_name, group_name FROM campus_groups WHERE is_active = 1 AND group_jid IS NOT NULL")
    .all();
  res.json(jids);
});

// POST /send — Broadcast a message to a specific group JID
app.post("/send", async (req, res) => {
  const { group_jid, message } = req.body;

  if (!group_jid || !message) {
    return res.status(400).json({ error: "group_jid and message are required." });
  }

  if (!clientReady) {
    return res.status(503).json({ error: "WhatsApp client is not ready." });
  }

  try {
    // Send the message via whatsapp-web.js
    await waClient.sendMessage(group_jid, message);

    // Log the broadcast in SQLite
    db.prepare(
      "INSERT INTO broadcast_log (group_jid, opportunity_title, status) VALUES (?, ?, ?)"
    ).run(group_jid, "Test Broadcast", "sent");

    console.log(`✅ Message dropped into ${group_jid}`);
    return res.json({ success: true, message: "Broadcast successful." });
  } catch (err) {
    console.error(`❌ Send failed for ${group_jid}:`, err.message);
    return res.status(500).json({ error: "Broadcast failed", detail: err.message });
  }
});

// ── Start Server ─────────────────────────────────────────────────────────────
const PORT = process.env.PORT || 3001;
app.listen(PORT, () => {
  console.log(`\n🤖 ScoutBot Distribution Server running on http://localhost:${PORT}`);
  console.log(`   GET  /status       — WhatsApp session status + QR code`);
  console.log(`   POST /register     — Register campus WhatsApp group`);
  console.log(`   GET  /groups       — List all registered groups`);
  console.log(`   GET  /groups/export — Export JIDs for broadcast.py`);
  console.log(`   POST /send         — Broadcast message to a group\n`);
});

module.exports = { app, db };

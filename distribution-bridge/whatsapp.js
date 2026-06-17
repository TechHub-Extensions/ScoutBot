/**
 * ScoutBot Distribution Layer — Backend Session Manager
 * Uses whatsapp-web.js to manage a master WA session.
 * Joins groups via invite links and stores Group JIDs to SQLite.
 */
const { Client, LocalAuth } = require("whatsapp-web.js");
const qrcode = require("qrcode");
const { DatabaseSync: Database } = require("node:sqlite");
const path = require("path");
const fs = require("fs");
const { execSync } = require("child_process");
const express = require('express');
const cors = require('cors');

// Resolve system Chromium — works on Replit (NixOS) and any Linux server
function resolveChromium() {
  if (process.env.CHROMIUM_PATH) return process.env.CHROMIUM_PATH;
  try { return execSync("which chromium").toString().trim(); } catch (_) {}
  try { return execSync("which chromium-browser").toString().trim(); } catch (_) {}
  try { return execSync("which google-chrome").toString().trim(); } catch (_) {}
  return null; // let puppeteer fall back to its bundled binary
}
const CHROMIUM_EXEC = resolveChromium();
console.log(`🔍 Using Chromium: ${CHROMIUM_EXEC || "puppeteer default"}`);
 
const app = express();

app.use(cors({
  origin: '*', // Allows all domains (like Vercel) to access the API
  methods: ['GET', 'POST', 'DELETE', 'UPDATE', 'PUT', 'PATCH'],
  allowedHeaders: ['Content-Type', 'Authorization']
}));

app.use(express.json());

// ── Base-path stripping (proxy deployments: /campus → /) ────────────────────
const BASE_PATH = (process.env.BASE_PATH || "").replace(/\/$/, "");
if (BASE_PATH) {
  app.use((req, _res, next) => {
    if (req.url === BASE_PATH || req.url.startsWith(BASE_PATH + "/")) {
      req.url = req.url.slice(BASE_PATH.length) || "/";
    }
    next();
  });
}

// ── Database Setup ──────────────────────────────────────────────────────────
const DB_PATH = path.join(__dirname, "scoutbot.db");
const db = new Database(DB_PATH);

// Enable Write-Ahead Logging to prevent SQLITE_BUSY lock crashes
db.exec("PRAGMA journal_mode = WAL");

db.exec(`
  CREATE TABLE IF NOT EXISTS campus_groups (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    campus_name TEXT    NOT NULL,
    invite_link TEXT    NOT NULL UNIQUE,
    group_jid   TEXT    UNIQUE,
    group_name  TEXT,
    preference  TEXT    DEFAULT 'both',
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

  const puppeteerConfig = {
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
  };
  if (CHROMIUM_EXEC) puppeteerConfig.executablePath = CHROMIUM_EXEC;

  waClient = new Client({
    authStrategy: new LocalAuth({ dataPath: path.join(__dirname, ".wwebjs_auth") }),
    puppeteer: puppeteerConfig,
  });

  waClient.on("qr", async (qr) => {
    qrCodeData = await qrcode.toDataURL(qr);
    clientReady = false;
    // Print scannable QR to the console so it's visible in Replit workflow logs
    console.log("\n📱 Scan this QR code with WhatsApp on your phone:");
    console.log("   (Phone → WhatsApp → ⋮ Menu → Linked devices → Link a device)\n");
    qrcode.toString(qr, { type: "terminal", small: true }, (err, str) => {
      if (!err) console.log(str);
    });
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

  waClient.on("disconnected", async (reason) => {
    console.warn("⚠️  WhatsApp disconnected:", reason);
    clientReady = false;
    
    try {
      console.log("🧹 Cleaning up dead WhatsApp instance...");
      await waClient.destroy();
    } catch (cleanupError) {
      console.error("Cleanup error (safe to ignore):", cleanupError.message);
    }

    console.log("🔄 Rebooting WhatsApp client in 10 seconds...");
    setTimeout(initWhatsApp, 10000);
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
  const match = link.match(/chat\.whatsapp\.com\/(?:invite\/)?([a-zA-Z0-9_-]+)/i);
  return match ? match[1] : null;
}

// ── Routes ───────────────────────────────────────────────────────────────────

// GET /healthz — proxy health check
app.get("/healthz", (_req, res) => res.json({ status: "ok" }));

// GET / — Campus registration portal
app.get("/", (_req, res) => {
  const basePath = BASE_PATH || "";
  res.send(`<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ScoutBot — Campus Registration</title>
<style>
  *{box-sizing:border-box;margin:0;padding:0}
  body{font-family:'Segoe UI',system-ui,sans-serif;background:#0d1117;color:#e6edf3;min-height:100vh}
  .hero{background:linear-gradient(135deg,#1a3a2a 0%,#0d2818 100%);padding:48px 24px 36px;text-align:center;border-bottom:1px solid #21362b}
  .logo{font-size:2.4rem;font-weight:800;color:#3fb950;letter-spacing:-1px}
  .logo span{color:#e6edf3}
  .tagline{margin-top:8px;color:#8b949e;font-size:1rem}
  .badge{display:inline-flex;align-items:center;gap:6px;background:#1c2d20;border:1px solid #2ea04326;border-radius:20px;padding:4px 14px;font-size:.82rem;margin-top:14px;color:#3fb950}
  .dot{width:8px;height:8px;border-radius:50%;background:#3fb950;animation:pulse 2s infinite}
  .dot.red{background:#f85149;animation:none}
  @keyframes pulse{0%,100%{opacity:1}50%{opacity:.4}}
  .container{max-width:560px;margin:0 auto;padding:40px 24px}
  .card{background:#161b22;border:1px solid #30363d;border-radius:12px;padding:28px;margin-bottom:24px}
  .card h2{font-size:1.05rem;font-weight:600;color:#e6edf3;margin-bottom:6px}
  .card p{font-size:.88rem;color:#8b949e;line-height:1.6}
  .status-row{display:flex;align-items:center;gap:10px;margin-bottom:18px;padding:12px 16px;background:#0d1117;border-radius:8px;border:1px solid #30363d}
  .status-text{font-size:.88rem}
  label{display:block;font-size:.85rem;color:#8b949e;margin-bottom:6px;margin-top:16px}
  label:first-of-type{margin-top:0}
  input,select{width:100%;padding:10px 14px;background:#0d1117;border:1px solid #30363d;border-radius:8px;color:#e6edf3;font-size:.93rem;outline:none;transition:border .2s}
  input:focus,select:focus{border-color:#3fb950}
  input::placeholder{color:#484f58}
  .btn{margin-top:20px;width:100%;padding:12px;background:#238636;color:#fff;border:none;border-radius:8px;font-size:.95rem;font-weight:600;cursor:pointer;transition:background .2s}
  .btn:hover{background:#2ea043}
  .btn:disabled{background:#21402a;color:#484f58;cursor:not-allowed}
  .alert{margin-top:16px;padding:12px 16px;border-radius:8px;font-size:.88rem;display:none}
  .alert.success{background:#1c2d20;border:1px solid #2ea04380;color:#3fb950;display:block}
  .alert.error{background:#2d1b1b;border:1px solid #f8514980;color:#f85149;display:block}
  .stat{text-align:center;padding:20px}
  .stat-num{font-size:2rem;font-weight:700;color:#3fb950}
  .stat-label{font-size:.82rem;color:#8b949e;margin-top:4px}
  .steps{list-style:none;counter-reset:step}
  .steps li{counter-increment:step;display:flex;gap:12px;margin-bottom:14px;font-size:.88rem;color:#8b949e;line-height:1.5}
  .steps li::before{content:counter(step);min-width:22px;height:22px;background:#21362b;color:#3fb950;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:.75rem;font-weight:700;flex-shrink:0;margin-top:1px}
  footer{text-align:center;padding:24px;font-size:.8rem;color:#484f58}
</style>
</head>
<body>
<div class="hero">
  <div class="logo">Scout<span>Bot</span></div>
  <div class="tagline">Automated opportunity discovery for Nigerian students</div>
  <div class="badge"><span class="dot" id="sessionDot"></span><span id="sessionLabel">Checking session…</span></div>
</div>
<div class="container">

  <div class="card">
    <div class="status-row">
      <span class="dot" id="statusDot" style="background:#484f58"></span>
      <span class="status-text" id="statusText">Connecting…</span>
    </div>
    <h2>Register Your Campus Group</h2>
    <p>ScoutBot will automatically broadcast scholarships, fellowships, and internships to your WhatsApp group twice daily — 7 AM and 7 PM.</p>

    <form id="regForm" onsubmit="submitForm(event)">
      <label for="campus">Campus / University Name</label>
      <input id="campus" type="text" placeholder="e.g. University of Lagos" required>

      <label for="link">WhatsApp Group Invite Link</label>
      <input id="link" type="url" placeholder="https://chat.whatsapp.com/…" required>

      <label for="pref">Opportunity Type</label>
      <select id="pref">
        <option value="both">Everything — Scholarships, Internships & More</option>
        <option value="scholarship">Scholarships &amp; Fellowships only</option>
        <option value="internship">Internships &amp; Tech Programs only</option>
      </select>

      <button class="btn" type="submit" id="submitBtn">Register Campus Group</button>
    </form>
    <div class="alert" id="alertBox"></div>
  </div>

  <div class="card" style="text-align:center">
    <div class="stat"><div class="stat-num" id="campusCount">—</div><div class="stat-label">Campus groups receiving broadcasts</div></div>
  </div>

  <div class="card">
    <h2>How it works</h2>
    <ul class="steps">
      <li>Paste your campus WhatsApp group invite link above — ScoutBot joins instantly</li>
      <li>At 7 AM and 7 PM every day, ScoutBot scrapes 15+ opportunity sites</li>
      <li>Every new scholarship, fellowship, or internship drops directly into your group — no manual work</li>
      <li>Your group members apply before the crowd even knows it's open</li>
    </ul>
  </div>
</div>
<footer>Powered by ScoutBot &mdash; built for Nigerian students</footer>

<script>
const BASE = "${basePath}";
const api  = p => fetch(BASE + p).then(r => r.json()).catch(() => ({}));

async function loadStatus() {
  const [st, cnt] = await Promise.all([
    api("/status"),
    api("/groups/count"),
  ]);

  const ready = st.ready === true;
  const dot   = document.getElementById("statusDot");
  const txt   = document.getElementById("statusText");
  const sdot  = document.getElementById("sessionDot");
  const slbl  = document.getElementById("sessionLabel");

  dot.style.background = ready ? "#3fb950" : (st.qr ? "#d29922" : "#f85149");
  txt.textContent = ready
    ? "✅ WhatsApp session active — broadcasts are live"
    : st.qr
      ? "⚠️ Scan the QR code in Replit console to activate session"
      : "🔴 Session not connected";

  sdot.style.background = ready ? "#3fb950" : "#d29922";
  sdot.className = "dot" + (ready ? "" : " red");
  slbl.textContent = ready ? "Session active" : "Session pending";

  const n = cnt.count ?? "—";
  document.getElementById("campusCount").textContent = n;
}

async function submitForm(e) {
  e.preventDefault();
  const btn = document.getElementById("submitBtn");
  const box = document.getElementById("alertBox");
  btn.disabled = true;
  btn.textContent = "Registering…";
  box.className = "alert";

  const body = {
    campus_name:  document.getElementById("campus").value.trim(),
    invite_link:  document.getElementById("link").value.trim(),
    preference:   document.getElementById("pref").value,
  };

  try {
    const r = await fetch(BASE + "/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await r.json();

    if (r.status === 409) {
      box.className = "alert error";
      box.textContent = "This group is already registered under: " + data.existing_campus;
    } else if (data.success || data.pending) {
      box.className = "alert success";
      box.textContent = data.pending
        ? "✅ Campus registered! Will be joined once WhatsApp session is active."
        : "🎉 " + (data.message || "Campus registered and group joined successfully!");
      document.getElementById("regForm").reset();
      loadStatus();
    } else {
      throw new Error(data.error || "Unknown error");
    }
  } catch (err) {
    box.className = "alert error";
    box.textContent = "❌ " + err.message;
  }

  btn.disabled = false;
  btn.textContent = "Register Campus Group";
}

loadStatus();
setInterval(loadStatus, 15000);
</script>
</body>
</html>`);
});

// GET /status — session health check + QR if needed
app.get("/status", (req, res) => {
  res.json({
    ready: clientReady,
    qr: qrCodeData,
    error: initializationError,
  });
});

// GET /groups/count — Lightweight endpoint for frontend metrics
app.get("/groups/count", (req, res) => {
  try {
    const result = db.prepare("SELECT COUNT(*) as total FROM campus_groups WHERE is_active = 1").get();
    res.json({ count: result.total });
  } catch (err) {
    console.error("Metrics error:", err);
    res.status(500).json({ count: 0 });
  }
});

// POST /register — accept campus + invite link, join group, save JID, and fire Teaser
app.post("/register", async (req, res) => {
  const { campus_name, invite_link, preference = 'both' } = req.body;

  if (!campus_name || !invite_link) {
    return res.status(400).json({ error: "campus_name and invite_link are required." });
  }

  const inviteCode = extractInviteCode(invite_link);
  if (!inviteCode) {
    return res.status(400).json({ error: "Invalid WhatsApp invite link format." });
  }

  const existing = db
    .prepare("SELECT * FROM campus_groups WHERE invite_link = ?")
    .get(invite_link);

  if (existing) {
    console.warn(`⚠️ Duplicate registration attempt for link tied to: ${existing.campus_name}`);
    return res.status(409).json({
      duplicate: true,
      existing_campus: existing.campus_name
    });
  }

  if (!clientReady) {
    db.prepare(
      "INSERT OR IGNORE INTO campus_groups (campus_name, invite_link, preference) VALUES (?, ?, ?)"
    ).run(campus_name, invite_link, preference);

    return res.status(202).json({
      success: false,
      pending: true,
      message: "WhatsApp session not ready. Campus registered — will be joined when session connects.",
    });
  }

  try {
    const groupId = await waClient.acceptInvite(inviteCode);

    let groupName = campus_name + " Group";
    try {
      const chat = await waClient.getChatById(groupId);
      groupName = chat.name || groupName;
    } catch (_) {}

    db.prepare(
      `INSERT INTO campus_groups (campus_name, invite_link, group_jid, group_name, preference)
       VALUES (?, ?, ?, ?, ?)
       ON CONFLICT(invite_link) DO UPDATE SET
         group_jid  = excluded.group_jid,
         group_name = excluded.group_name,
         preference = excluded.preference`
    ).run(campus_name, invite_link, groupId, groupName, preference);

    console.log(`✅ Joined group: ${groupName} (${groupId}) for campus: ${campus_name}`);

    // 🚀 FIRE HCI WELCOME & TEASER IMMEDIATELY AFTER JOINING
    const welcomeMsg =
      "*Hi everyone! I'm ScoutBot* 🤖\n\n" +
      "I'm your new automated assistant, here to drop fresh opportunities directly into this chat so you never miss out.\n\n" +
      "*What I'll be bringing you:*\n" +
      "🎓 Scholarships & Fellowships\n" +
      "💻 Tech Internships\n" +
      "🚀 Career Growth Resources\n\n" +
      "I operate in the background and check for new links every few hours. Keep your notifications on and let the opportunities come to you!";
    
    await waClient.sendMessage(groupId, welcomeMsg);

    const nextDropDate = new Date();
    nextDropDate.setMinutes(nextDropDate.getMinutes() + 210); 
    const nextDropTime = nextDropDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    try {
      const queueDbPath = path.join(__dirname, 'whatsapp_queue.db');
      db.prepare(`ATTACH DATABASE '${queueDbPath}' AS queue`).run();
      const sample = db.prepare("SELECT title, link, deadline FROM queue.pending_broadcasts ORDER BY RANDOM() LIMIT 1").get();
      db.prepare("DETACH DATABASE queue").run();

      if (sample) {
        const teaserMsg = 
          "✨ *SAMPLE OPPORTUNITY* ✨\n\n" +
          `📌 *${sample.title}*\n` +
          `📅 Deadline: ${sample.deadline}\n\n` +
          `🔗 Apply: ${sample.link}\n\n` +
          `🚀 *The real opportunity drops start at ${nextDropTime}.* Stay tuned! \n\n` +
          "🤖 _Powered by ScoutBot_";

        await waClient.sendMessage(groupId, teaserMsg);
      }
    } catch (e) {
      console.error("Failed to send teaser opportunity:", e.message);
    }

    return res.json({
      success: true,
      message: `Successfully joined "${groupName}" and sent teaser.`,
      group_jid: groupId,
      group_name: groupName,
      invite_link,
    });
  } catch (err) {
    console.error("Error joining group:", err.message);

    db.prepare(
      "INSERT OR IGNORE INTO campus_groups (campus_name, invite_link, preference) VALUES (?, ?, ?)"
    ).run(campus_name, invite_link, preference);

    return res.status(500).json({
      error: "Failed to join WhatsApp group.",
      detail: err.message,
    });
  }
});

// GET /groups — list all registered groups
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

// GET /groups/export — export JIDs as JSON
app.get("/groups/export", (req, res) => {
  const jids = db
    .prepare("SELECT group_jid, campus_name, group_name, preference FROM campus_groups WHERE is_active = 1 AND group_jid IS NOT NULL")
    .all();
  res.json(jids);
});

// POST /send — Broadcast a message
app.post("/send", async (req, res) => {
  const { group_jid, message } = req.body;

  if (!group_jid || !message) {
    return res.status(400).json({ error: "group_jid and message are required." });
  }

  if (!clientReady) {
    return res.status(503).json({ error: "WhatsApp client is not ready." });
  }

  try {
    await waClient.sendMessage(group_jid, message);

    db.prepare(
      "INSERT INTO broadcast_log (group_jid, opportunity_title, status) VALUES (?, ?, ?)"
    ).run(group_jid, "Broadcast", "sent");

    console.log(`✅ Message dropped into ${group_jid}`);
    return res.json({ success: true, message: "Broadcast successful." });
  } catch (err) {
    console.error(`❌ Send failed for ${group_jid}:`, err.message);
    return res.status(500).json({ error: "Broadcast failed", detail: err.message });
  }
});

const PORT = process.env.PORT || 3001;
app.listen(PORT, () => {
  console.log(`\n🤖 ScoutBot Distribution Server running on http://localhost:${PORT}`);
});

module.exports = { app, db };
import { useState, useEffect, useRef } from "react";

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL;
const WA_INVITE_REGEX = /chat\.whatsapp\.com\/(?:invite\/)?([a-zA-Z0-9_-]+)/i;

// ── Lottie-style success animation (pure CSS) ─────────────────────────────────
function SuccessAnimation({ groupName, inviteLink }) {
  return (
    <div className="success-container">
      <div className="checkmark-ring">
        <svg className="checkmark-svg" viewBox="0 0 52 52">
          <circle className="checkmark-circle" cx="26" cy="26" r="25" fill="none" />
          <path className="checkmark-check" fill="none" d="M14.1 27.2l7.1 7.2 16.7-16.8" />
        </svg>
      </div>

      <div className="success-text">
        <h2 className="success-title">ScoutBot Joined! 🎉</h2>
        <p className="success-subtitle">
          Congratulations! We successfully added <strong>{groupName || "your group"}</strong> to the ScoutBot network.
        </p>
        
        <p style={{ margin: '16px 0 0 0', fontSize: '13px', color: '#666', fontWeight: '500' }}>
          NOTE: Make ScoutBot an Admin (+234 816 449 9922).
        </p>
      </div>

      <a
        href={inviteLink}
        target="_blank"
        rel="noopener noreferrer"
        className="wa-button"
        style={{ marginTop: '24px' }}
      >
        <span className="wa-icon">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
            <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413Z" />
          </svg>
        </span>
        Open in WhatsApp to Make Admin
      </a>

      <button className="register-another" onClick={() => window.location.reload()}>
        Register another campus
      </button>
    </div>
  );
}

function StatusDot({ ready }) {
  return (
    <div className={`status-dot-wrap ${ready ? "online" : "offline"}`}>
      <span className="status-pulse" />
      <span className="status-label">{ready ? "ScoutBot Online" : "Connecting…"}</span>
    </div>
  );
}

export default function CampusLeadRegistration() {
  const [campusName, setCampusName] = useState("");
  const [inviteLink, setInviteLink] = useState("");
  const [preference, setPreference] = useState("both");
  const [linkValid, setLinkValid] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [sessionReady, setSessionReady] = useState(false);
  const [qrCode, setQrCode] = useState(null);

  useEffect(() => {
    const poll = async () => {
      try {
        const res = await fetch(`${BACKEND_URL}/status`);
        const data = await res.json();
        setSessionReady(data.ready);
        setQrCode(data.qr || null);
      } catch (_) { setSessionReady(false); }
    };
    poll();
    const id = setInterval(poll, 4000);
    return () => clearInterval(id);
  }, []);

  const handleInviteChange = (val) => {
    setInviteLink(val);
    setLinkValid(val ? WA_INVITE_REGEX.test(val.trim()) : null);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    if (!campusName.trim() || !linkValid) { setError("Check your inputs."); return; }
    setLoading(true);
    try {
      const res = await fetch(`${BACKEND_URL}/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ campus_name: campusName.trim(), invite_link: inviteLink.trim(), preference }),
      });
      const data = await res.json();
      if (data.duplicate) setError(`Already registered to: ${data.existing_campus}`);
      else if (data.success || data.pending) setSuccess({ groupName: data.group_name || campusName, inviteLink: inviteLink.trim(), pending: data.pending });
      else setError(data.error || "Error.");
    } catch { setError("Server unreachable."); }
    setLoading(false);
  };

  if (success) return <div className="page"><div className="card"><Header /><SuccessAnimation {...success} /><Footer /></div></div>;

  return (
    <div className="page">
      <div className="card">
        <Header />
        <StatusDot ready={sessionReady} />
        {qrCode && <div className="qr-wrap"><p className="qr-label">Scan to activate ScoutBot</p><img src={qrCode} alt="QR" className="qr-img" /></div>}
        <form onSubmit={handleSubmit} className="form">
          <div className="field">
            <label className="label">Campus Name</label>
            <input className="input" value={campusName} onChange={(e) => setCampusName(e.target.value)} required />
          </div>
          <div className="field">
            <label className="label">WhatsApp Group Invite Link</label>
            <input className="input" type="url" value={inviteLink} onChange={(e) => handleInviteChange(e.target.value)} required />
          </div>
          <div className="field">
            <label className="label">What opportunities does your group need?</label>
            <select
              value={preference}
              onChange={(e) => setPreference(e.target.value)}
              style={{ width: "100%", padding: "12px", borderRadius: "8px", border: "1px solid #ccc", fontSize: "16px", marginTop: "8px", display: "block" }}
            >
              <option value="both">Both (Undergrad & Grad/PhD)</option>
              <option value="undergrad">Undergraduate & Internships Only</option>
              <option value="grad">Graduate, Masters & PhD Only</option>
            </select>
          </div>
          {error && <div className="alert">⚠ {error}</div>}
          <button type="submit" className="submit-btn" disabled={loading}>{loading ? "Joining..." : "Register Group →"}</button>
        </form>
        <Footer />
      </div>
    </div>
  );
}

function Header() {
  return (
    <div className="header">
      <h1 className="title">Campus Lead Portal</h1>
      <p className="subtitle">Curated opportunities delivered automatically.</p>
    </div>
  );
}

function Footer() {
  return (
    <div className="footer-note" style={{ marginTop: '28px', textAlign: 'center', color: '#6B7280', fontSize: '13px' }}>
      <p>© {new Date().getFullYear()} Olamide Fasogbon</p>
    </div>
  );
}
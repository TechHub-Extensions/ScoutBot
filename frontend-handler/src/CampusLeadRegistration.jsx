import { useState, useEffect, useRef } from "react";

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "http://localhost:3001";
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
          We successfully connected <strong>{groupName || "your group"}</strong> to the ScoutBot network.
          Fresh opportunities will drop straight into your WhatsApp.
        </p>
        
        {/* CRITICAL ADMIN INSTRUCTION BLOCK */}
        <div className="admin-warning" style={{ backgroundColor: '#FFF4E5', padding: '16px', borderRadius: '8px', marginTop: '16px', borderLeft: '4px solid #FF9800', textAlign: 'left' }}>
          <h4 style={{ margin: '0 0 8px 0', color: '#B76E00', fontSize: '15px' }}>⚠️ CRITICAL LAST STEP</h4>
          <p style={{ margin: '0', fontSize: '14px', color: '#5C3D00', lineHeight: '1.5' }}>
            If your group is set to <strong>"Only Admins Can Send Messages"</strong>, you MUST open WhatsApp right now and make the ScoutBot number <strong>(+234 816 449 9922)</strong> an Admin. Otherwise, it cannot deliver opportunities.
          </p>
        </div>
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

      <button
        className="register-another"
        onClick={() => window.location.reload()}
      >
        Register another campus
      </button>
    </div>
  );
}

// ── Status Badge ──────────────────────────────────────────────────────────────
function StatusDot({ ready }) {
  return (
    <div className={`status-dot-wrap ${ready ? "online" : "offline"}`}>
      <span className="status-pulse" />
      <span className="status-label">{ready ? "ScoutBot Online" : "Connecting…"}</span>
    </div>
  );
}

// ── Main Component ────────────────────────────────────────────────────────────
export default function CampusLeadRegistration() {
  const [campusName, setCampusName] = useState("");
  const [inviteLink, setInviteLink] = useState("");
  const [linkValid, setLinkValid] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [sessionReady, setSessionReady] = useState(false);
  const [qrCode, setQrCode] = useState(null);

  const inviteRef = useRef(null);

  // Poll session status
  useEffect(() => {
    const poll = async () => {
      try {
        const res = await fetch(`${BACKEND_URL}/status`);
        const data = await res.json();
        setSessionReady(data.ready);
        setQrCode(data.qr || null);
      } catch (_) {
        setSessionReady(false);
      }
    };
    poll();
    const id = setInterval(poll, 4000);
    return () => clearInterval(id);
  }, []);

  // Real-time invite link validation
  const handleInviteChange = (val) => {
    setInviteLink(val);
    if (!val) { 
      setLinkValid(null); 
      return; 
    }
    setLinkValid(WA_INVITE_REGEX.test(val.trim()));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    if (!campusName.trim()) { 
      setError("Please enter your campus name."); 
      return; 
    }
    if (!linkValid) { 
      setError("Please enter a valid WhatsApp invite link."); 
      return; 
    }

    setLoading(true);
    try {
      const res = await fetch(`${BACKEND_URL}/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          campus_name: campusName.trim(),
          invite_link: inviteLink.trim(),
        }),
      });
      const data = await res.json();

      if (data.success || data.pending) {
        setSuccess({
          groupName: data.group_name || campusName,
          inviteLink: inviteLink.trim(),
          pending: data.pending,
        });
      } else {
        setError(data.error || "Something went wrong. Please try again.");
      }
    } catch (err) {
      setError("Could not reach the server. Please check your connection.");
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <div className="page">
        <div className="card">
          <Header />
          <SuccessAnimation groupName={success.groupName} inviteLink={success.inviteLink} />
          {success.pending && (
            <p className="pending-note">
              ⏳ Your group will be joined once the ScoutBot session is live.
            </p>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="page">
      <div className="card">
        <Header />
        <StatusDot ready={sessionReady} />

        {qrCode && (
          <div className="qr-wrap">
            <p className="qr-label">Scan to activate ScoutBot</p>
            <img src={qrCode} alt="WhatsApp QR" className="qr-img" />
          </div>
        )}

        <form onSubmit={handleSubmit} className="form" noValidate>
          <div className="field">
            <label htmlFor="campus" className="label">
              Campus Name
            </label>
            <input
              id="campus"
              type="text"
              value={campusName}
              onChange={(e) => setCampusName(e.target.value)}
              placeholder="e.g. Obafemi Awolowo University"
              className="input"
              autoComplete="organization"
              maxLength={80}
              required
            />
          </div>

          <div className="field">
            <label htmlFor="invite" className="label">
              WhatsApp Group Invite Link
            </label>
            <div className="input-wrap">
              <input
                id="invite"
                ref={inviteRef}
                type="url"
                value={inviteLink}
                onChange={(e) => handleInviteChange(e.target.value)}
                placeholder="https://chat.whatsapp.com/..."
                className={`input ${
                  linkValid === true ? "input-valid" : linkValid === false ? "input-invalid" : ""
                }`}
                autoComplete="url"
                required
              />
              {linkValid === true && <span className="input-icon valid">✓</span>}
              {linkValid === false && <span className="input-icon invalid">✗</span>}
            </div>
            {linkValid === false && (
              <p className="field-hint error">
                Must be a valid <strong>chat.whatsapp.com/...</strong> link
              </p>
            )}
            {linkValid === true && (
              <p className="field-hint success">Looks great ✓</p>
            )}
          </div>

          {error && (
            <div className="alert">
              <span className="alert-icon">⚠</span>
              {error}
            </div>
          )}

          <button
            type="submit"
            className={`submit-btn ${loading ? "loading" : ""}`}
            disabled={loading || !campusName || !linkValid}
          >
            {loading ? (
              <>
                <span className="spinner" /> Joining Group…
              </>
            ) : (
              "Register Campus Group →"
            )}
          </button>
        </form>

        <p className="footer-note">
          By registering, your group will receive curated opportunities via ScoutBot.
          No spam. Unsubscribe anytime.
        </p>
      </div>
    </div>
  );
}

function Header() {
  return (
    <div className="header">
      <div className="logo-wrap">
        <div className="logo-icon">
          <svg width="28" height="28" viewBox="0 0 40 40" fill="none">
            <circle cx="20" cy="20" r="20" fill="#0066F5" />
            <path d="M12 20l5 5 11-11" stroke="white" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"/>
            <circle cx="20" cy="20" r="7" stroke="white" strokeWidth="1.5" fill="none" opacity="0.4"/>
          </svg>
        </div>
        <span className="logo-text">ScoutBot</span>
      </div>
      <h1 className="title">Campus Lead Portal</h1>
      <p className="subtitle">
        Connect your WhatsApp group to receive curated opportunities — internships,
        scholarships, and fellowships — automatically.
      </p>
    </div>
  );
}
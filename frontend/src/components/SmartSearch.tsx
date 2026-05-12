import { useState, useEffect, useRef, useCallback } from "react";

interface Contact {
  id: number;
  name: string;
  phone: string;
  email: string;
  designation: string;
  company: string;
  address: string;
  website: string;
  services: string;
  match_score?: number;
}

// ── Suggestion chips shown below search bar ───────────────────────────────────
const QUICK_SUGGESTIONS = [
  "Electrician", "Plumber", "Doctor", "Lawyer", "CA",
  "Engineer", "Consultant", "Sales", "IT", "Marketing",
  "Solar", "Architect", "Mechanic", "Painter", "Logistics",
];

// ── Single result card ────────────────────────────────────────────────────────
function ResultCard({ contact, rank }: { contact: Contact; rank: number }) {
  const score = contact.match_score ?? 0;
  const scoreColor = score > 0.6 ? "#28a745" : score > 0.3 ? "#fd7e14" : "#6c757d";

  const handleCall = () => {
    const raw = contact.phone?.split("/")[0]?.trim().replace(/\s/g, "");
    if (raw) window.location.href = `tel:${raw}`;
  };

  const handleEmail = () => {
    if (contact.email) window.location.href = `mailto:${contact.email}`;
  };

  const handleWebsite = () => {
    if (contact.website) {
      const url = contact.website.startsWith("http")
        ? contact.website
        : `https://${contact.website}`;
      window.open(url, "_blank");
    }
  };

  return (
    <div style={{
      backgroundColor: "white",
      borderRadius: "12px",
      padding: "16px",
      marginBottom: "10px",
      boxShadow: rank === 1
        ? "0 2px 12px rgba(0,123,255,0.15)"
        : "0 1px 4px rgba(0,0,0,0.08)",
      border: rank === 1 ? "2px solid #007bff" : "1px solid #e8e8e8",
      position: "relative",
    }}>
      {/* Best match badge */}
      {rank === 1 && (
        <div style={{
          position: "absolute", top: "-10px", left: "14px",
          backgroundColor: "#007bff", color: "white",
          fontSize: "11px", fontWeight: 700,
          padding: "2px 10px", borderRadius: "10px",
        }}>
          🏆 Best Match
        </div>
      )}

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "12px" }}>
        {/* Left: info */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" }}>
            <span style={{ fontWeight: 700, fontSize: "1rem", color: "#1a1a2e" }}>
              👤 {contact.name}
            </span>
            <span style={{
              backgroundColor: scoreColor, color: "white",
              fontSize: "10px", padding: "1px 6px", borderRadius: "8px", fontWeight: 600,
            }}>
              {Math.round(score * 100)}%
            </span>
          </div>

          {contact.designation && (
            <div style={{ fontSize: "13px", color: "#555", marginBottom: "2px" }}>
              💼 {contact.designation}
            </div>
          )}
          {contact.company && (
            <div style={{ fontSize: "13px", color: "#555", marginBottom: "2px" }}>
              🏢 {contact.company}
            </div>
          )}
          {contact.services && (
            <div style={{ fontSize: "12px", color: "#007bff", marginBottom: "2px" }}>
              🛠️ {contact.services}
            </div>
          )}
          {contact.address && (
            <div style={{ fontSize: "12px", color: "#888" }}>
              📍 {contact.address.split(",").slice(-2).join(",").trim()}
            </div>
          )}
        </div>

        {/* Right: action buttons */}
        <div style={{ display: "flex", flexDirection: "column", gap: "6px", flexShrink: 0 }}>
          {contact.phone && (
            <button onClick={handleCall} style={{
              padding: "7px 14px", backgroundColor: "#28a745", color: "white",
              border: "none", borderRadius: "8px", cursor: "pointer",
              fontSize: "13px", fontWeight: 600, whiteSpace: "nowrap",
            }}>
              📞 Call
            </button>
          )}
          {contact.email && (
            <button onClick={handleEmail} style={{
              padding: "7px 14px", backgroundColor: "#007bff", color: "white",
              border: "none", borderRadius: "8px", cursor: "pointer",
              fontSize: "13px", fontWeight: 600,
            }}>
              📧 Email
            </button>
          )}
          {contact.website && (
            <button onClick={handleWebsite} style={{
              padding: "7px 14px", backgroundColor: "#6c757d", color: "white",
              border: "none", borderRadius: "8px", cursor: "pointer",
              fontSize: "13px", fontWeight: 600,
            }}>
              🌐 Visit
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Main SmartSearch component ────────────────────────────────────────────────
export default function SmartSearch() {
  const [query,       setQuery]       = useState("");
  const [results,     setResults]     = useState<Contact[]>([]);
  const [loading,     setLoading]     = useState(false);
  const [searched,    setSearched]    = useState(false);
  const [listening,   setListening]   = useState(false);
  const [voiceError,  setVoiceError]  = useState("");
  const [totalCount,  setTotalCount]  = useState(0);

  const inputRef    = useRef<HTMLInputElement>(null);
  const recognRef   = useRef<SpeechRecognition | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // ── Search function ─────────────────────────────────────────────────────────
  const doSearch = useCallback(async (q: string) => {
    if (!q.trim()) {
      setResults([]);
      setSearched(false);
      return;
    }
    setLoading(true);
    setSearched(true);
    try {
      const res  = await fetch(`http://127.0.0.1:8000/smart-search/?q=${encodeURIComponent(q)}&limit=10`);
      const data = await res.json();
      setResults(data.results || []);
      setTotalCount(data.total || 0);
    } catch {
      setResults([]);
    } finally {
      setLoading(false);
    }
  }, []);

  // Debounced search as user types
  const handleInput = (val: string) => {
    setQuery(val);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => doSearch(val), 400);
  };

  // ── Voice search ────────────────────────────────────────────────────────────
  const startVoice = () => {
    const SR = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SR) {
      setVoiceError("Voice search not supported in this browser. Use Chrome.");
      return;
    }
    setVoiceError("");
    const recog = new SR();
    recog.lang = "en-IN";
    recog.continuous = false;
    recog.interimResults = true;

    recog.onstart  = () => setListening(true);
    recog.onend    = () => setListening(false);
    recog.onerror  = (e: any) => {
      setListening(false);
      setVoiceError(`Voice error: ${e.error}`);
    };
    recog.onresult = (e: any) => {
      const transcript = Array.from(e.results)
        .map((r: any) => r[0].transcript)
        .join("");
      setQuery(transcript);
      if (e.results[e.results.length - 1].isFinal) {
        doSearch(transcript);
      }
    };

    recog.start();
    recognRef.current = recog;
  };

  const stopVoice = () => {
    recognRef.current?.stop();
    setListening(false);
  };

  // Cleanup
  useEffect(() => () => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    recognRef.current?.stop();
  }, []);

  return (
    <div style={{ maxWidth: "700px", margin: "0 auto", padding: "0 16px" }}>

      {/* ── Header ── */}
      <div style={{ textAlign: "center", marginBottom: "20px" }}>
        <h2 style={{ fontSize: "1.5rem", color: "#1a1a2e", margin: "0 0 6px" }}>
          🔍 Find a Professional
        </h2>
        <p style={{ color: "#888", fontSize: "13px", margin: 0 }}>
          Search by service, name, company or skill from your {" "}
          <strong style={{ color: "#007bff" }}>196 contacts</strong>
        </p>
      </div>

      {/* ── Search bar ── */}
      <div style={{
        display: "flex", gap: "8px", alignItems: "center",
        backgroundColor: "white", borderRadius: "50px",
        padding: "6px 6px 6px 20px",
        boxShadow: "0 2px 20px rgba(0,0,0,0.12)",
        border: "2px solid #e8e8e8",
        marginBottom: "12px",
      }}>
        <span style={{ fontSize: "18px", color: "#888" }}>🔍</span>
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => handleInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && doSearch(query)}
          placeholder="Search electrician, doctor, lawyer, solar..."
          style={{
            flex: 1, border: "none", outline: "none",
            fontSize: "15px", backgroundColor: "transparent",
          }}
        />
        {query && (
          <button onClick={() => { setQuery(""); setResults([]); setSearched(false); }}
            style={{ background: "none", border: "none", cursor: "pointer", fontSize: "18px", color: "#aaa", padding: "0 4px" }}>
            ✕
          </button>
        )}
        {/* Voice button */}
        <button
          onClick={listening ? stopVoice : startVoice}
          title={listening ? "Stop listening" : "Voice search"}
          style={{
            width: "40px", height: "40px", borderRadius: "50%", border: "none",
            backgroundColor: listening ? "#dc3545" : "#007bff",
            color: "white", cursor: "pointer", fontSize: "18px",
            display: "flex", alignItems: "center", justifyContent: "center",
            flexShrink: 0,
            animation: listening ? "pulse 1s infinite" : "none",
          }}>
          {listening ? "⏹" : "🎤"}
        </button>
        {/* Search button */}
        <button
          onClick={() => doSearch(query)}
          disabled={loading}
          style={{
            padding: "8px 18px", borderRadius: "50px", border: "none",
            backgroundColor: loading ? "#ccc" : "#007bff",
            color: "white", cursor: loading ? "not-allowed" : "pointer",
            fontSize: "14px", fontWeight: 700, flexShrink: 0,
          }}>
          {loading ? "..." : "Search"}
        </button>
      </div>

      {/* Voice status */}
      {listening && (
        <div style={{
          textAlign: "center", padding: "8px", marginBottom: "10px",
          backgroundColor: "#fff3cd", borderRadius: "8px", fontSize: "13px", color: "#856404",
        }}>
          🎤 Listening... speak your requirement
        </div>
      )}
      {voiceError && (
        <div style={{ textAlign: "center", color: "#dc3545", fontSize: "12px", marginBottom: "8px" }}>
          {voiceError}
        </div>
      )}

      {/* ── Quick suggestion chips ── */}
      {!searched && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: "8px", marginBottom: "20px", justifyContent: "center" }}>
          {QUICK_SUGGESTIONS.map(s => (
            <button key={s}
              onClick={() => { setQuery(s); doSearch(s); }}
              style={{
                padding: "6px 14px", borderRadius: "20px", border: "1px solid #ddd",
                backgroundColor: "white", cursor: "pointer", fontSize: "13px",
                color: "#555", transition: "all 0.15s",
              }}
              onMouseEnter={e => (e.currentTarget.style.backgroundColor = "#007bff", e.currentTarget.style.color = "white")}
              onMouseLeave={e => (e.currentTarget.style.backgroundColor = "white", e.currentTarget.style.color = "#555")}
            >
              {s}
            </button>
          ))}
        </div>
      )}

      {/* ── Results ── */}
      {searched && (
        <div>
          {loading ? (
            <div style={{ textAlign: "center", padding: "30px", color: "#888" }}>
              <div style={{ fontSize: "2rem", marginBottom: "8px" }}>🔍</div>
              Searching your contacts...
            </div>
          ) : results.length === 0 ? (
            <div style={{
              textAlign: "center", padding: "30px",
              backgroundColor: "white", borderRadius: "12px",
              border: "2px dashed #ddd", color: "#888",
            }}>
              <div style={{ fontSize: "2rem", marginBottom: "8px" }}>😕</div>
              <strong>No contacts found for "{query}"</strong>
              <p style={{ fontSize: "13px", marginTop: "8px" }}>
                Try different keywords or scan more visiting cards
              </p>
            </div>
          ) : (
            <>
              <div style={{ fontSize: "13px", color: "#888", marginBottom: "12px" }}>
                Found <strong style={{ color: "#007bff" }}>{totalCount}</strong> match{totalCount !== 1 ? "es" : ""} for "{query}"
              </div>
              {results.map((c, i) => (
                <ResultCard key={c.id} contact={c} rank={i + 1} />
              ))}
            </>
          )}
        </div>
      )}

      <style>{`
        @keyframes pulse {
          0%, 100% { transform: scale(1); }
          50% { transform: scale(1.1); }
        }
      `}</style>
    </div>
  );
}

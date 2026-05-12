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
  stars?: number;
  distance_km?: number | null;
  extraction_confidence?: number;
}

interface ChatMessage {
  role: "user" | "bot";
  text: string;
  contacts?: Contact[];
  time: string;
}

const QUICK_SUGGESTIONS = [
  "Electrician", "Plumber", "Doctor", "Lawyer", "CA",
  "Engineer", "Solar", "IT", "Marketing", "Architect",
  "Mechanic", "Logistics", "Real Estate", "Insurance", "Consultant",
];

// ── Star rating display ───────────────────────────────────────────────────────
function Stars({ value }: { value: number }) {
  const full  = Math.floor(value);
  const half  = value - full >= 0.5;
  const empty = 5 - full - (half ? 1 : 0);
  return (
    <span style={{ fontSize: "12px", color: "#fd7e14" }}>
      {"★".repeat(full)}
      {half ? "½" : ""}
      {"☆".repeat(empty)}
      <span style={{ color: "#888", marginLeft: "3px" }}>{value.toFixed(1)}</span>
    </span>
  );
}

// ── Result Card ───────────────────────────────────────────────────────────────
function ResultCard({ contact, rank }: { contact: Contact; rank: number }) {
  const score = contact.match_score ?? 0;
  const scoreColor = score > 0.6 ? "#28a745" : score > 0.3 ? "#fd7e14" : "#6c757d";

  const call = () => {
    const n = contact.phone?.split("/")[0]?.trim().replace(/[\s\-]/g, "");
    if (n) window.location.href = `tel:${n}`;
  };
  const email = () => { if (contact.email) window.location.href = `mailto:${contact.email}`; };
  const web   = () => {
    if (contact.website) {
      const u = contact.website.startsWith("http") ? contact.website : `https://${contact.website}`;
      window.open(u, "_blank");
    }
  };
  const map = () => {
    if (contact.address) {
      window.open(`https://www.google.com/maps/search/${encodeURIComponent(contact.address)}`, "_blank");
    }
  };

  return (
    <div style={{
      backgroundColor: "white", borderRadius: "12px", padding: "14px",
      marginBottom: "10px",
      boxShadow: rank === 1 ? "0 3px 16px rgba(0,123,255,0.18)" : "0 1px 4px rgba(0,0,0,0.08)",
      border: rank === 1 ? "2px solid #007bff" : "1px solid #eee",
      position: "relative",
    }}>
      {rank === 1 && (
        <div style={{
          position: "absolute", top: "-10px", left: "14px",
          backgroundColor: "#007bff", color: "white",
          fontSize: "11px", fontWeight: 700, padding: "2px 10px", borderRadius: "10px",
        }}>🏆 Best Match</div>
      )}

      <div style={{ display: "flex", gap: "10px", alignItems: "flex-start" }}>
        {/* Avatar */}
        <div style={{
          width: "42px", height: "42px", borderRadius: "50%", flexShrink: 0,
          backgroundColor: rank === 1 ? "#007bff" : "#6c757d",
          display: "flex", alignItems: "center", justifyContent: "center",
          color: "white", fontWeight: 700, fontSize: "16px",
        }}>
          {(contact.name || "?")[0].toUpperCase()}
        </div>

        {/* Info */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: "flex", alignItems: "center", gap: "6px", flexWrap: "wrap" }}>
            <span style={{ fontWeight: 700, fontSize: "0.95rem", color: "#1a1a2e" }}>
              {contact.name}
            </span>
            {score > 0 && (
              <span style={{
                backgroundColor: scoreColor, color: "white",
                fontSize: "10px", padding: "1px 6px", borderRadius: "8px", fontWeight: 600,
              }}>{Math.round(score * 100)}%</span>
            )}
          </div>
          {contact.designation && <div style={{ fontSize: "12px", color: "#555" }}>💼 {contact.designation}</div>}
          {contact.company    && <div style={{ fontSize: "12px", color: "#555" }}>🏢 {contact.company}</div>}
          {contact.services   && <div style={{ fontSize: "12px", color: "#007bff" }}>🛠️ {contact.services}</div>}
          {/* Stars + distance */}
          <div style={{ display: "flex", gap: "10px", alignItems: "center", marginTop: "3px", flexWrap: "wrap" }}>
            {contact.stars !== undefined && contact.stars > 0 && (
              <Stars value={contact.stars} />
            )}
            {contact.distance_km !== undefined && contact.distance_km !== null && (
              <span style={{ fontSize: "11px", color: "#28a745", fontWeight: 600 }}>
                📍 {contact.distance_km} km away
              </span>
            )}
          </div>
          {contact.address    && (
            <div style={{ fontSize: "11px", color: "#888", cursor: "pointer" }} onClick={map}>
              📍 {contact.address.split(",").slice(-2).join(",").trim()} ↗
            </div>
          )}
        </div>
      </div>

      {/* Action buttons */}
      <div style={{ display: "flex", gap: "6px", marginTop: "10px", flexWrap: "wrap" }}>
        {contact.phone && (
          <button onClick={call} style={{
            flex: 1, minWidth: "70px", padding: "7px 0",
            backgroundColor: "#28a745", color: "white",
            border: "none", borderRadius: "8px", cursor: "pointer",
            fontSize: "13px", fontWeight: 600,
          }}>📞 Call</button>
        )}
        {contact.email && (
          <button onClick={email} style={{
            flex: 1, minWidth: "70px", padding: "7px 0",
            backgroundColor: "#007bff", color: "white",
            border: "none", borderRadius: "8px", cursor: "pointer",
            fontSize: "13px", fontWeight: 600,
          }}>📧 Email</button>
        )}
        {contact.address && (
          <button onClick={map} style={{
            flex: 1, minWidth: "70px", padding: "7px 0",
            backgroundColor: "#fd7e14", color: "white",
            border: "none", borderRadius: "8px", cursor: "pointer",
            fontSize: "13px", fontWeight: 600,
          }}>🗺️ Map</button>
        )}
        {contact.website && (
          <button onClick={web} style={{
            flex: 1, minWidth: "70px", padding: "7px 0",
            backgroundColor: "#6c757d", color: "white",
            border: "none", borderRadius: "8px", cursor: "pointer",
            fontSize: "13px", fontWeight: 600,
          }}>🌐 Web</button>
        )}
        <button onClick={() => {
          const q = `${contact.name} ${contact.company || contact.designation || ""} ${contact.address?.split(",").slice(-1)[0] || ""}`.trim();
          window.open(`https://www.google.com/search?q=${encodeURIComponent(q)}`, "_blank");
        }} style={{
          flex: 1, minWidth: "70px", padding: "7px 0",
          backgroundColor: "#4285f4", color: "white",
          border: "none", borderRadius: "8px", cursor: "pointer",
          fontSize: "13px", fontWeight: 600,
        }}>🔍 Google</button>
      </div>
    </div>
  );
}

// ── Chatbot ───────────────────────────────────────────────────────────────────
function Chatbot({ onSearch }: { onSearch: (q: string) => void }) {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: "bot",
      text: "Hi! 👋 I'm your AI assistant. Ask me anything like:\n• \"Who can fix my AC?\"\n• \"I need a lawyer in Pune\"\n• \"Find me a solar energy expert\"",
      time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      contacts: [],
    }
  ]);
  const [input,   setInput]   = useState("");
  const [loading, setLoading] = useState(false);
  const [listening, setListening] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const recognRef = useRef<SpeechRecognition | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const send = async (text: string) => {
    if (!text.trim()) return;
    const userMsg: ChatMessage = {
      role: "user", text,
      time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };
    setMessages(prev => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const res  = await fetch("http://127.0.0.1:8000/chatbot/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text }),
      });
      const data = await res.json();
      const botMsg: ChatMessage = {
        role: "bot",
        text: data.reply || "I couldn't find an answer.",
        contacts: data.contacts || [],
        time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };
      setMessages(prev => [...prev, botMsg]);
    } catch {
      setMessages(prev => [...prev, {
        role: "bot", text: "⚠️ Could not connect to server. Make sure backend is running.",
        time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      }]);
    } finally {
      setLoading(false);
    }
  };

  const startVoice = () => {
    const SR = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SR) return;
    const r = new SR();
    r.lang = "en-IN";
    r.onstart  = () => setListening(true);
    r.onend    = () => setListening(false);
    r.onresult = (e: any) => {
      const t = Array.from(e.results).map((x: any) => x[0].transcript).join("");
      setInput(t);
      if (e.results[e.results.length - 1].isFinal) send(t);
    };
    r.start();
    recognRef.current = r;
  };

  return (
    <div style={{
      backgroundColor: "white", borderRadius: "16px",
      boxShadow: "0 2px 16px rgba(0,0,0,0.1)",
      display: "flex", flexDirection: "column", height: "420px",
    }}>
      {/* Header */}
      <div style={{
        padding: "12px 16px", borderBottom: "1px solid #eee",
        display: "flex", alignItems: "center", gap: "10px",
        backgroundColor: "#007bff", borderRadius: "16px 16px 0 0",
      }}>
        <div style={{
          width: "36px", height: "36px", borderRadius: "50%",
          backgroundColor: "rgba(255,255,255,0.2)",
          display: "flex", alignItems: "center", justifyContent: "center",
          fontSize: "20px",
        }}>🤖</div>
        <div>
          <div style={{ color: "white", fontWeight: 700, fontSize: "14px" }}>AI Assistant</div>
          <div style={{ color: "rgba(255,255,255,0.8)", fontSize: "11px" }}>Ask about your contacts</div>
        </div>
        <div style={{
          marginLeft: "auto", width: "8px", height: "8px",
          borderRadius: "50%", backgroundColor: "#28a745",
        }} />
      </div>

      {/* Messages */}
      <div style={{ flex: 1, overflowY: "auto", padding: "12px", display: "flex", flexDirection: "column", gap: "10px" }}>
        {messages.map((msg, i) => (
          <div key={i} style={{ display: "flex", flexDirection: "column", alignItems: msg.role === "user" ? "flex-end" : "flex-start" }}>
            <div style={{
              maxWidth: "85%", padding: "10px 14px", borderRadius: msg.role === "user" ? "16px 16px 4px 16px" : "16px 16px 16px 4px",
              backgroundColor: msg.role === "user" ? "#007bff" : "#f0f4ff",
              color: msg.role === "user" ? "white" : "#1a1a2e",
              fontSize: "13px", lineHeight: "1.5", whiteSpace: "pre-wrap",
            }}>
              {msg.text}
            </div>
            {/* Suggested contacts from bot */}
            {msg.contacts && msg.contacts.length > 0 && (
              <div style={{ maxWidth: "85%", marginTop: "6px", display: "flex", flexDirection: "column", gap: "6px" }}>
                {msg.contacts.map(c => (
                  <div key={c.id} style={{
                    backgroundColor: "white", border: "1px solid #e0e8ff",
                    borderRadius: "10px", padding: "8px 12px", fontSize: "12px",
                  }}>
                    <div style={{ fontWeight: 700 }}>👤 {c.name}</div>
                    {c.designation && <div style={{ color: "#555" }}>💼 {c.designation}</div>}
                    {c.phone && (
                      <button onClick={() => window.location.href = `tel:${c.phone.split("/")[0].trim().replace(/\s/g,"")}`}
                        style={{ marginTop: "4px", padding: "4px 10px", backgroundColor: "#28a745", color: "white", border: "none", borderRadius: "6px", cursor: "pointer", fontSize: "11px" }}>
                        📞 Call
                      </button>
                    )}
                  </div>
                ))}
              </div>
            )}
            <div style={{ fontSize: "10px", color: "#aaa", marginTop: "2px" }}>{msg.time}</div>
          </div>
        ))}
        {loading && (
          <div style={{ display: "flex", alignItems: "flex-start" }}>
            <div style={{ backgroundColor: "#f0f4ff", borderRadius: "16px 16px 16px 4px", padding: "10px 14px", fontSize: "13px", color: "#888" }}>
              🤖 Thinking...
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div style={{ padding: "10px 12px", borderTop: "1px solid #eee", display: "flex", gap: "8px" }}>
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === "Enter" && send(input)}
          placeholder="Ask anything about your contacts..."
          style={{
            flex: 1, padding: "8px 12px", borderRadius: "20px",
            border: "1px solid #ddd", fontSize: "13px", outline: "none",
          }}
        />
        <button onClick={startVoice} style={{
          width: "36px", height: "36px", borderRadius: "50%", border: "none",
          backgroundColor: listening ? "#dc3545" : "#e8f0fe",
          color: listening ? "white" : "#007bff",
          cursor: "pointer", fontSize: "16px",
          display: "flex", alignItems: "center", justifyContent: "center",
        }}>🎤</button>
        <button onClick={() => send(input)} disabled={!input.trim() || loading} style={{
          width: "36px", height: "36px", borderRadius: "50%", border: "none",
          backgroundColor: input.trim() ? "#007bff" : "#e8e8e8",
          color: input.trim() ? "white" : "#aaa",
          cursor: input.trim() ? "pointer" : "not-allowed",
          fontSize: "16px", display: "flex", alignItems: "center", justifyContent: "center",
        }}>➤</button>
      </div>
    </div>
  );
}

// ── Main SmartSearch ──────────────────────────────────────────────────────────
export default function SmartSearch() {
  const [query,     setQuery]     = useState("");
  const [results,   setResults]   = useState<Contact[]>([]);
  const [loading,   setLoading]   = useState(false);
  const [searched,  setSearched]  = useState(false);
  const [listening, setListening] = useState(false);
  const [voiceErr,  setVoiceErr]  = useState("");
  const [total,     setTotal]     = useState(0);
  const [mode,      setMode]      = useState<"search" | "chat">("search");
  const [gps,       setGps]       = useState<{ lat: number; lng: number } | null>(null);
  const [gpsStatus, setGpsStatus] = useState("");
  // Ambient keyword listener
  const [ambient,       setAmbient]       = useState(false);
  const [detectedWord,  setDetectedWord]  = useState("");
  const [ambientStatus, setAmbientStatus] = useState("");

  const recognRef   = useRef<SpeechRecognition | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const ambientRef  = useRef<SpeechRecognition | null>(null);

  // Get GPS location
  const getLocation = () => {
    if (!navigator.geolocation) { setGpsStatus("GPS not supported"); return; }
    setGpsStatus("Getting location...");
    navigator.geolocation.getCurrentPosition(
      pos => {
        setGps({ lat: pos.coords.latitude, lng: pos.coords.longitude });
        setGpsStatus(`📍 Location: ${pos.coords.latitude.toFixed(3)}, ${pos.coords.longitude.toFixed(3)}`);
      },
      () => setGpsStatus("Location denied"),
      { timeout: 8000 }
    );
  };

  const doSearch = useCallback(async (q: string) => {
    if (!q.trim()) { setResults([]); setSearched(false); return; }
    setLoading(true); setSearched(true);
    try {
      let url = `http://127.0.0.1:8000/smart-search/?q=${encodeURIComponent(q)}&limit=15`;
      if (gps) url += `&lat=${gps.lat}&lng=${gps.lng}`;
      const res  = await fetch(url);
      const data = await res.json();
      setResults(data.results || []);
      setTotal(data.total || 0);
    } catch { setResults([]); }
    finally { setLoading(false); }
  }, [gps]);

  // ── Ambient keyword listener ────────────────────────────────────────────────
  // Listens continuously, extracts service keywords, auto-searches
  const startAmbient = () => {
    const SR = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SR) { setVoiceErr("Use Chrome for voice features"); return; }

    setAmbient(true);
    setAmbientStatus("🎤 Listening for keywords...");
    setVoiceErr("");

    const r = new SR();
    r.lang = "en-IN";
    r.continuous = true;       // keep listening
    r.interimResults = true;

    r.onresult = async (e: any) => {
      // Get latest transcript
      const transcript = Array.from(e.results)
        .map((x: any) => x[0].transcript)
        .join(" ");

      // Only process final results to avoid too many API calls
      if (!e.results[e.results.length - 1].isFinal) return;

      // Send to backend to extract keywords
      try {
        const res = await fetch("http://127.0.0.1:8000/extract-keywords/", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text: transcript }),
        });
        const data = await res.json();

        if (data.keywords && data.keywords.length > 0) {
          const kw = data.search || data.keywords[0];
          setDetectedWord(kw);
          setAmbientStatus(`🔑 Detected: "${kw}" — searching...`);
          setQuery(kw);
          doSearch(kw);
          setMode("search");
        }
      } catch {
        // silently ignore
      }
    };

    r.onerror = (e: any) => {
      if (e.error !== "no-speech") {
        setAmbient(false);
        setAmbientStatus("");
        setVoiceErr(`Mic error: ${e.error}`);
      }
    };

    r.onend = () => {
      // Restart if still in ambient mode
      if (ambientRef.current) {
        try { ambientRef.current.start(); } catch { /* ignore */ }
      }
    };

    r.start();
    ambientRef.current = r;
  };

  const stopAmbient = () => {
    ambientRef.current?.stop();
    ambientRef.current = null;
    setAmbient(false);
    setAmbientStatus("");
    setDetectedWord("");
  };

  const handleInput = (val: string) => {
    setQuery(val);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => doSearch(val), 350);
  };

  const startVoice = () => {
    const SR = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SR) { setVoiceErr("Use Chrome for voice search"); return; }
    setVoiceErr("");
    const r = new SR();
    r.lang = "en-IN"; r.continuous = false; r.interimResults = true;
    r.onstart  = () => setListening(true);
    r.onend    = () => setListening(false);
    r.onerror  = (e: any) => { setListening(false); setVoiceErr(e.error); };
    r.onresult = (e: any) => {
      const t = Array.from(e.results).map((x: any) => x[0].transcript).join("");
      setQuery(t);
      if (e.results[e.results.length - 1].isFinal) doSearch(t);
    };
    r.start(); recognRef.current = r;
  };

  useEffect(() => () => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    recognRef.current?.stop();
    ambientRef.current?.stop();
    ambientRef.current = null;
  }, []);

  return (
    <div style={{ maxWidth: "700px", margin: "0 auto" }}>

      {/* Mode toggle */}
      <div style={{ display: "flex", gap: "8px", marginBottom: "16px", justifyContent: "center" }}>
        {(["search", "chat"] as const).map(m => (
          <button key={m} onClick={() => setMode(m)} style={{
            padding: "8px 20px", borderRadius: "20px", border: "none",
            backgroundColor: mode === m ? "#007bff" : "#e8e8e8",
            color: mode === m ? "white" : "#555",
            cursor: "pointer", fontWeight: mode === m ? 700 : 400, fontSize: "14px",
          }}>
            {m === "search" ? "🔍 Search" : "🤖 AI Chat"}
          </button>
        ))}
      </div>

      {/* ── SEARCH MODE ── */}
      {mode === "search" && (
        <>
          {/* Search bar */}
          <div style={{
            display: "flex", gap: "8px", alignItems: "center",
            backgroundColor: "white", borderRadius: "50px",
            padding: "6px 6px 6px 18px",
            boxShadow: "0 2px 20px rgba(0,0,0,0.12)",
            border: "2px solid #e8e8e8", marginBottom: "10px",
          }}>
            <span style={{ fontSize: "18px", color: "#888" }}>🔍</span>
            <input
              type="text" value={query}
              onChange={e => handleInput(e.target.value)}
              onKeyDown={e => e.key === "Enter" && doSearch(query)}
              placeholder="Search electrician, doctor, solar, CA..."
              style={{ flex: 1, border: "none", outline: "none", fontSize: "15px", backgroundColor: "transparent" }}
            />
            {query && (
              <button onClick={() => { setQuery(""); setResults([]); setSearched(false); }}
                style={{ background: "none", border: "none", cursor: "pointer", fontSize: "18px", color: "#aaa" }}>✕</button>
            )}
            <button onClick={listening ? () => { recognRef.current?.stop(); setListening(false); } : startVoice}
              style={{
                width: "38px", height: "38px", borderRadius: "50%", border: "none",
                backgroundColor: listening ? "#dc3545" : "#007bff",
                color: "white", cursor: "pointer", fontSize: "16px",
                display: "flex", alignItems: "center", justifyContent: "center",
                animation: listening ? "pulse 1s infinite" : "none",
              }}>
              {listening ? "⏹" : "🎤"}
            </button>
            <button onClick={() => doSearch(query)} disabled={loading} style={{
              padding: "8px 16px", borderRadius: "50px", border: "none",
              backgroundColor: loading ? "#ccc" : "#007bff",
              color: "white", cursor: loading ? "not-allowed" : "pointer",
              fontSize: "14px", fontWeight: 700,
            }}>{loading ? "..." : "Search"}</button>
          </div>

          {/* GPS + voice status */}
          <div style={{ display: "flex", gap: "8px", marginBottom: "10px", flexWrap: "wrap", alignItems: "center" }}>
            <button onClick={getLocation} style={{
              padding: "5px 12px", borderRadius: "16px", border: "1px solid #ddd",
              backgroundColor: gps ? "#d4edda" : "white", cursor: "pointer", fontSize: "12px",
              color: gps ? "#155724" : "#555",
            }}>
              {gps ? "📍 Location ON" : "📍 Use My Location"}
            </button>

            {/* Ambient keyword listener toggle */}
            <button
              onClick={ambient ? stopAmbient : startAmbient}
              style={{
                padding: "5px 14px", borderRadius: "16px", border: "none",
                backgroundColor: ambient ? "#dc3545" : "#6f42c1",
                color: "white", cursor: "pointer", fontSize: "12px", fontWeight: 600,
                animation: ambient ? "pulse 1.5s infinite" : "none",
              }}>
              {ambient ? "⏹ Stop Listening" : "👂 Smart Listen"}
            </button>

            {gpsStatus && <span style={{ fontSize: "11px", color: "#888" }}>{gpsStatus}</span>}
            {listening && <span style={{ fontSize: "12px", color: "#dc3545", fontWeight: 600 }}>🎤 Listening...</span>}
            {voiceErr && <span style={{ fontSize: "11px", color: "#dc3545" }}>{voiceErr}</span>}
          </div>

          {/* Ambient status banner */}
          {ambient && (
            <div style={{
              padding: "10px 14px", marginBottom: "10px",
              backgroundColor: "#f3e8ff", borderRadius: "10px",
              border: "1px solid #d8b4fe", fontSize: "13px",
              display: "flex", alignItems: "center", gap: "10px",
            }}>
              <span style={{ fontSize: "20px", animation: "pulse 1s infinite" }}>👂</span>
              <div>
                <div style={{ fontWeight: 600, color: "#6f42c1" }}>{ambientStatus}</div>
                {detectedWord && (
                  <div style={{ fontSize: "12px", color: "#555" }}>
                    Last keyword: <strong style={{ color: "#007bff" }}>"{detectedWord}"</strong>
                    {" "}→ showing matching contacts below
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Quick chips */}
          {!searched && (
            <div style={{ display: "flex", flexWrap: "wrap", gap: "8px", marginBottom: "20px" }}>
              {QUICK_SUGGESTIONS.map(s => (
                <button key={s} onClick={() => { setQuery(s); doSearch(s); }} style={{
                  padding: "6px 14px", borderRadius: "20px", border: "1px solid #ddd",
                  backgroundColor: "white", cursor: "pointer", fontSize: "13px", color: "#555",
                }}>{s}</button>
              ))}
            </div>
          )}

          {/* Results */}
          {searched && (
            loading ? (
              <div style={{ textAlign: "center", padding: "30px", color: "#888" }}>
                <div style={{ fontSize: "2rem" }}>🔍</div>Searching...
              </div>
            ) : results.length === 0 ? (
              <div style={{ textAlign: "center", padding: "30px", backgroundColor: "white", borderRadius: "12px", border: "2px dashed #ddd", color: "#888" }}>
                <div style={{ fontSize: "2rem" }}>😕</div>
                <strong>No contacts found for "{query}"</strong>
                <p style={{ fontSize: "13px" }}>Try the AI Chat for smarter suggestions 👆</p>
              </div>
            ) : (
              <>
                <div style={{ fontSize: "13px", color: "#888", marginBottom: "10px" }}>
                  Found <strong style={{ color: "#007bff" }}>{total}</strong> match{total !== 1 ? "es" : ""} for "{query}"
                </div>
                {results.map((c, i) => <ResultCard key={c.id} contact={c} rank={i + 1} />)}
              </>
            )
          )}
        </>
      )}

      {/* ── CHAT MODE ── */}
      {mode === "chat" && <Chatbot onSearch={q => { setMode("search"); setQuery(q); doSearch(q); }} />}

      <style>{`
        @keyframes pulse { 0%,100%{transform:scale(1)} 50%{transform:scale(1.1)} }
        button:hover { opacity: 0.9; }
      `}</style>
    </div>
  );
}

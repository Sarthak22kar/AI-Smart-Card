import { useState, useEffect } from "react";

interface Props {
  onGetStarted: () => void;
  contactCount: number | null;
}

export default function LandingPage({ onGetStarted, contactCount }: Props) {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 40);
    window.addEventListener("scroll", onScroll);
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <div style={{ fontFamily: "system-ui, -apple-system, sans-serif", overflowX: "hidden" }}>

      {/* ── NAVBAR ── */}
      <nav style={{
        position: "fixed", top: 0, left: 0, right: 0, zIndex: 200,
        backgroundColor: scrolled ? "rgba(255,255,255,0.97)" : "transparent",
        boxShadow: scrolled ? "0 2px 16px rgba(0,0,0,0.10)" : "none",
        transition: "all 0.3s ease",
        padding: "14px 40px",
        display: "flex", alignItems: "center", justifyContent: "space-between",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <div style={{
            width: 36, height: 36, borderRadius: "10px",
            background: "linear-gradient(135deg,#007bff,#6610f2)",
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: 18,
          }}>🤖</div>
          <span style={{ fontWeight: 800, fontSize: "1.1rem", color: scrolled ? "#1a1a2e" : "white" }}>
            AI Smart Card
          </span>
        </div>
        <div style={{ display: "flex", gap: "8px" }}>
          <button onClick={onGetStarted} style={{
            padding: "9px 22px", borderRadius: "50px", border: "none",
            background: "linear-gradient(135deg,#007bff,#6610f2)",
            color: "white", fontWeight: 700, fontSize: "14px", cursor: "pointer",
            boxShadow: "0 4px 14px rgba(0,123,255,0.35)",
          }}>
            Launch App →
          </button>
        </div>
      </nav>

      {/* ── HERO ── */}
      <section style={{
        minHeight: "100vh",
        background: "linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%)",
        display: "flex", flexDirection: "column",
        alignItems: "center", justifyContent: "center",
        textAlign: "center", padding: "100px 24px 60px",
        position: "relative", overflow: "hidden",
      }}>
        {/* Animated background blobs */}
        {[
          { top:"10%", left:"5%",  size:300, color:"rgba(0,123,255,0.15)" },
          { top:"60%", right:"5%", size:250, color:"rgba(102,16,242,0.15)" },
          { top:"30%", left:"50%", size:200, color:"rgba(40,167,69,0.10)" },
        ].map((b, i) => (
          <div key={i} style={{
            position: "absolute", borderRadius: "50%",
            width: b.size, height: b.size,
            background: b.color,
            top: b.top, left: (b as any).left, right: (b as any).right,
            filter: "blur(60px)", pointerEvents: "none",
          }} />
        ))}

        {/* Badge */}
        <div style={{
          display: "inline-flex", alignItems: "center", gap: "8px",
          backgroundColor: "rgba(255,255,255,0.1)",
          border: "1px solid rgba(255,255,255,0.2)",
          borderRadius: "50px", padding: "6px 16px",
          color: "rgba(255,255,255,0.85)", fontSize: "13px",
          marginBottom: "28px", backdropFilter: "blur(10px)",
        }}>
          <span style={{ width: 8, height: 8, borderRadius: "50%", backgroundColor: "#28a745", display: "inline-block" }} />
          Powered by Google Gemini AI · {contactCount ?? "250"}+ Contacts
        </div>

        {/* Headline */}
        <h1 style={{
          fontSize: "clamp(2.2rem, 6vw, 4rem)",
          fontWeight: 900, color: "white", margin: "0 0 20px",
          lineHeight: 1.15, maxWidth: 800,
        }}>
          Turn Visiting Cards Into<br />
          <span style={{
            background: "linear-gradient(90deg,#4facfe,#00f2fe)",
            WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent",
          }}>
            Smart Digital Contacts
          </span>
        </h1>

        {/* Subheadline */}
        <p style={{
          fontSize: "clamp(1rem, 2.5vw, 1.25rem)",
          color: "rgba(255,255,255,0.72)", maxWidth: 600,
          margin: "0 0 40px", lineHeight: 1.7,
        }}>
          Scan any visiting card in 3 seconds. AI extracts name, phone, email,
          address and more. Search by profession, find the nearest expert using GPS.
        </p>

        {/* CTA Buttons */}
        <div style={{ display: "flex", gap: "14px", flexWrap: "wrap", justifyContent: "center" }}>
          <button onClick={onGetStarted} style={{
            padding: "16px 36px", borderRadius: "50px", border: "none",
            background: "linear-gradient(135deg,#007bff,#6610f2)",
            color: "white", fontWeight: 800, fontSize: "16px", cursor: "pointer",
            boxShadow: "0 8px 30px rgba(0,123,255,0.45)",
            transition: "transform 0.2s",
          }}
            onMouseEnter={e => (e.currentTarget.style.transform = "scale(1.05)")}
            onMouseLeave={e => (e.currentTarget.style.transform = "scale(1)")}
          >
            🚀 Get Started Free
          </button>
          <button onClick={onGetStarted} style={{
            padding: "16px 36px", borderRadius: "50px",
            border: "2px solid rgba(255,255,255,0.3)",
            backgroundColor: "transparent",
            color: "white", fontWeight: 700, fontSize: "16px", cursor: "pointer",
            backdropFilter: "blur(10px)",
          }}>
            📷 Scan a Card
          </button>
        </div>

        {/* Stats row */}
        <div style={{
          display: "flex", gap: "40px", marginTop: "60px",
          flexWrap: "wrap", justifyContent: "center",
        }}>
          {[
            { value: "3 sec", label: "Card scan time" },
            { value: "90%+", label: "OCR accuracy" },
            { value: contactCount ? `${contactCount}+` : "250+", label: "Contacts stored" },
            { value: "80+", label: "Indian cities" },
          ].map((s, i) => (
            <div key={i} style={{ textAlign: "center" }}>
              <div style={{ fontSize: "2rem", fontWeight: 900, color: "white" }}>{s.value}</div>
              <div style={{ fontSize: "13px", color: "rgba(255,255,255,0.55)", marginTop: 4 }}>{s.label}</div>
            </div>
          ))}
        </div>

        {/* Scroll indicator */}
        <div style={{
          position: "absolute", bottom: 30, left: "50%", transform: "translateX(-50%)",
          color: "rgba(255,255,255,0.4)", fontSize: "12px", textAlign: "center",
        }}>
          <div style={{ marginBottom: 6 }}>Scroll to explore</div>
          <div style={{ fontSize: 20 }}>↓</div>
        </div>
      </section>

      {/* ── HOW IT WORKS ── */}
      <section style={{
        padding: "80px 24px",
        background: "#f8f9ff",
        textAlign: "center",
      }}>
        <div style={{ maxWidth: 900, margin: "0 auto" }}>
          <p style={{ color: "#007bff", fontWeight: 700, fontSize: "13px", letterSpacing: 2, textTransform: "uppercase", marginBottom: 12 }}>
            How It Works
          </p>
          <h2 style={{ fontSize: "clamp(1.6rem,4vw,2.4rem)", fontWeight: 800, color: "#1a1a2e", margin: "0 0 16px" }}>
            From Physical Card to Smart Contact in 3 Steps
          </h2>
          <p style={{ color: "#666", fontSize: "1.05rem", maxWidth: 560, margin: "0 auto 56px" }}>
            No manual typing. No lost cards. Just scan, extract, and search.
          </p>

          <div style={{ display: "flex", gap: "24px", flexWrap: "wrap", justifyContent: "center" }}>
            {[
              {
                step: "01", icon: "📷", color: "#007bff", bg: "#E3F2FD",
                title: "Scan the Card",
                desc: "Upload front and back photos of any visiting card. Supports JPG, PNG, HEIC from any phone camera.",
              },
              {
                step: "02", icon: "🧠", color: "#6610f2", bg: "#EDE7F6",
                title: "AI Extracts Data",
                desc: "Google Gemini Vision AI reads name, phone, email, company, address, website and GSTIN in one API call.",
              },
              {
                step: "03", icon: "🔍", color: "#28a745", bg: "#E8F5E9",
                title: "Search & Connect",
                desc: "Find any contact by profession, company or service. GPS ranks nearest professionals first.",
              },
            ].map((item, i) => (
              <div key={i} style={{
                flex: "1 1 240px", maxWidth: 280,
                backgroundColor: "white", borderRadius: "20px",
                padding: "32px 24px", textAlign: "left",
                boxShadow: "0 4px 24px rgba(0,0,0,0.07)",
                border: "1px solid #eee",
                position: "relative",
              }}>
                <div style={{
                  position: "absolute", top: -16, left: 24,
                  backgroundColor: item.color, color: "white",
                  fontWeight: 900, fontSize: "12px",
                  padding: "4px 12px", borderRadius: "50px",
                }}>
                  STEP {item.step}
                </div>
                <div style={{
                  width: 56, height: 56, borderRadius: "16px",
                  backgroundColor: item.bg, fontSize: "28px",
                  display: "flex", alignItems: "center", justifyContent: "center",
                  marginBottom: 16,
                }}>
                  {item.icon}
                </div>
                <h3 style={{ fontWeight: 800, fontSize: "1.1rem", color: "#1a1a2e", margin: "0 0 10px" }}>
                  {item.title}
                </h3>
                <p style={{ color: "#666", fontSize: "14px", lineHeight: 1.7, margin: 0 }}>
                  {item.desc}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── FEATURES ── */}
      <section style={{ padding: "80px 24px", background: "white" }}>
        <div style={{ maxWidth: 1000, margin: "0 auto" }}>
          <div style={{ textAlign: "center", marginBottom: 56 }}>
            <p style={{ color: "#007bff", fontWeight: 700, fontSize: "13px", letterSpacing: 2, textTransform: "uppercase", marginBottom: 12 }}>
              Features
            </p>
            <h2 style={{ fontSize: "clamp(1.6rem,4vw,2.4rem)", fontWeight: 800, color: "#1a1a2e", margin: 0 }}>
              Everything You Need to Manage Contacts
            </h2>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "20px" }}>
            {[
              { icon: "🤖", color: "#007bff", title: "Gemini Vision OCR", desc: "Google's most advanced AI reads any card layout — rotated, dark, colored, or sideways. 90%+ accuracy." },
              { icon: "📍", color: "#28a745", title: "GPS Distance Ranking", desc: "Haversine formula calculates real distance from your location. Nearest professionals shown first." },
              { icon: "💬", color: "#6610f2", title: "AI Chatbot Assistant", desc: "Ask in plain English: 'Find me an eye surgeon near Pune'. AI picks the best matching contacts." },
              { icon: "🎤", color: "#fd7e14", title: "Voice Search", desc: "Speak your query. Smart Listen mode detects keywords from ambient conversation automatically." },
              { icon: "✏️", color: "#dc3545", title: "Editable Extraction", desc: "All extracted fields are editable before saving. Orange badge shows what was changed." },
              { icon: "📊", color: "#20c997", title: "Stats Dashboard", desc: "Confidence scores, profession breakdown, OCR engine stats, and recent contact activity." },
            ].map((f, i) => (
              <div key={i} style={{
                padding: "24px", borderRadius: "16px",
                border: "1.5px solid #eee", backgroundColor: "#fafafa",
                transition: "box-shadow 0.2s, transform 0.2s",
              }}
                onMouseEnter={e => {
                  (e.currentTarget as HTMLDivElement).style.boxShadow = "0 8px 32px rgba(0,0,0,0.10)";
                  (e.currentTarget as HTMLDivElement).style.transform = "translateY(-4px)";
                }}
                onMouseLeave={e => {
                  (e.currentTarget as HTMLDivElement).style.boxShadow = "none";
                  (e.currentTarget as HTMLDivElement).style.transform = "translateY(0)";
                }}
              >
                <div style={{
                  width: 48, height: 48, borderRadius: "14px",
                  backgroundColor: f.color + "18",
                  display: "flex", alignItems: "center", justifyContent: "center",
                  fontSize: "24px", marginBottom: 14,
                }}>
                  {f.icon}
                </div>
                <h3 style={{ fontWeight: 700, fontSize: "1rem", color: "#1a1a2e", margin: "0 0 8px" }}>
                  {f.title}
                </h3>
                <p style={{ color: "#666", fontSize: "13.5px", lineHeight: 1.65, margin: 0 }}>
                  {f.desc}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── TECH STACK ── */}
      <section style={{ padding: "60px 24px", background: "#f8f9ff" }}>
        <div style={{ maxWidth: 800, margin: "0 auto", textAlign: "center" }}>
          <p style={{ color: "#888", fontSize: "13px", marginBottom: 24, textTransform: "uppercase", letterSpacing: 2 }}>
            Built With
          </p>
          <div style={{ display: "flex", flexWrap: "wrap", gap: "12px", justifyContent: "center" }}>
            {[
              { label: "Google Gemini AI", color: "#4285F4" },
              { label: "FastAPI", color: "#009688" },
              { label: "React 19", color: "#61DAFB" },
              { label: "TypeScript", color: "#3178C6" },
              { label: "MySQL 8", color: "#F29111" },
              { label: "OpenCV", color: "#5C3EE8" },
              { label: "spaCy NLP", color: "#09A3D5" },
              { label: "EasyOCR", color: "#E91E63" },
              { label: "Haversine GPS", color: "#28a745" },
              { label: "Vite", color: "#646CFF" },
            ].map((t, i) => (
              <span key={i} style={{
                padding: "8px 18px", borderRadius: "50px",
                backgroundColor: "white",
                border: `2px solid ${t.color}22`,
                color: t.color, fontWeight: 700, fontSize: "13px",
                boxShadow: "0 2px 8px rgba(0,0,0,0.06)",
              }}>
                {t.label}
              </span>
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA BANNER ── */}
      <section style={{
        padding: "80px 24px",
        background: "linear-gradient(135deg,#007bff,#6610f2)",
        textAlign: "center",
      }}>
        <h2 style={{ fontSize: "clamp(1.6rem,4vw,2.4rem)", fontWeight: 900, color: "white", margin: "0 0 16px" }}>
          Ready to Digitize Your Contacts?
        </h2>
        <p style={{ color: "rgba(255,255,255,0.8)", fontSize: "1.05rem", margin: "0 0 36px" }}>
          Scan your first visiting card in under 5 seconds.
        </p>
        <button onClick={onGetStarted} style={{
          padding: "16px 44px", borderRadius: "50px", border: "none",
          backgroundColor: "white", color: "#007bff",
          fontWeight: 800, fontSize: "16px", cursor: "pointer",
          boxShadow: "0 8px 30px rgba(0,0,0,0.2)",
          transition: "transform 0.2s",
        }}
          onMouseEnter={e => (e.currentTarget.style.transform = "scale(1.05)")}
          onMouseLeave={e => (e.currentTarget.style.transform = "scale(1)")}
        >
          🚀 Launch App Now
        </button>
      </section>

      {/* ── FOOTER ── */}
      <footer style={{
        padding: "32px 24px", backgroundColor: "#1a1a2e",
        textAlign: "center", color: "rgba(255,255,255,0.45)", fontSize: "13px",
      }}>
        <div style={{ marginBottom: 8, fontWeight: 700, color: "rgba(255,255,255,0.7)", fontSize: "15px" }}>
          🤖 AI Smart Card Network
        </div>
        AI Smart Card Network · Gemini OCR · MySQL · FastAPI · React
        <br />
        <span style={{ fontSize: "11px", marginTop: 6, display: "block" }}>
          Built for professionals who network smarter
        </span>
      </footer>
    </div>
  );
}

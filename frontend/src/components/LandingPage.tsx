import { useState, useEffect, useRef } from "react";

interface Props {
  onGetStarted: () => void;
  contactCount: number | null;
}

// ── Animated counter ──────────────────────────────────────────────────────────
function Counter({ target, suffix = "" }: { target: number; suffix?: string }) {
  const [count, setCount] = useState(0);
  const ref = useRef<HTMLSpanElement>(null);
  useEffect(() => {
    const observer = new IntersectionObserver(([e]) => {
      if (e.isIntersecting) {
        let start = 0;
        const step = Math.ceil(target / 60);
        const timer = setInterval(() => {
          start += step;
          if (start >= target) { setCount(target); clearInterval(timer); }
          else setCount(start);
        }, 20);
        observer.disconnect();
      }
    });
    if (ref.current) observer.observe(ref.current);
    return () => observer.disconnect();
  }, [target]);
  return <span ref={ref}>{count}{suffix}</span>;
}

export default function LandingPage({ onGetStarted, contactCount }: Props) {
  const [scrollY, setScrollY] = useState(0);

  useEffect(() => {
    const fn = () => setScrollY(window.scrollY);
    window.addEventListener("scroll", fn);
    return () => window.removeEventListener("scroll", fn);
  }, []);

  const navScrolled = scrollY > 60;

  const scrollTo = (id: string) => {
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth" });
  };

  return (
    <div style={{ fontFamily: "'Segoe UI', system-ui, -apple-system, sans-serif", overflowX: "hidden", color: "#1a1a2e" }}>

      {/* ════════════════════════════════════════════════════════════════════
          NAVBAR
      ════════════════════════════════════════════════════════════════════ */}
      <nav style={{
        position: "fixed", top: 0, left: 0, right: 0, zIndex: 999,
        backgroundColor: navScrolled ? "rgba(255,255,255,0.97)" : "transparent",
        backdropFilter: navScrolled ? "blur(12px)" : "none",
        boxShadow: navScrolled ? "0 2px 20px rgba(0,0,0,0.10)" : "none",
        transition: "all 0.35s ease",
        padding: "0 5%",
      }}>
        <div style={{
          maxWidth: 1200, margin: "0 auto",
          display: "flex", alignItems: "center", justifyContent: "space-between",
          height: 68,
        }}>
          {/* Logo */}
          <div style={{ display: "flex", alignItems: "center", gap: 10, cursor: "pointer" }}
            onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}>
            <div style={{
              width: 40, height: 40, borderRadius: 12,
              background: "linear-gradient(135deg,#007bff,#6610f2)",
              display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: 20, boxShadow: "0 4px 12px rgba(0,123,255,0.35)",
            }}>🤖</div>
            <div>
              <div style={{ fontWeight: 800, fontSize: "1rem", color: navScrolled ? "#1a1a2e" : "white", lineHeight: 1.1 }}>
                AI Smart Card
              </div>
              <div style={{ fontSize: "10px", color: navScrolled ? "#888" : "rgba(255,255,255,0.6)", lineHeight: 1 }}>
                Network
              </div>
            </div>
          </div>

          {/* Desktop nav links */}
          <div style={{ display: "flex", gap: 32, alignItems: "center" }}>
            {[["Features","features"],["How It Works","howitworks"],["Technology","tech"],["Contact","contact"]].map(([label, id]) => (
              <button key={id} onClick={() => scrollTo(id)} style={{
                background: "none", border: "none", cursor: "pointer",
                fontSize: "14px", fontWeight: 600,
                color: navScrolled ? "#444" : "rgba(255,255,255,0.85)",
                transition: "color 0.2s",
              }}
                onMouseEnter={e => (e.currentTarget.style.color = "#007bff")}
                onMouseLeave={e => (e.currentTarget.style.color = navScrolled ? "#444" : "rgba(255,255,255,0.85)")}
              >{label}</button>
            ))}
            <button onClick={onGetStarted} style={{
              padding: "10px 24px", borderRadius: 50, border: "none",
              background: "linear-gradient(135deg,#007bff,#6610f2)",
              color: "white", fontWeight: 700, fontSize: "14px", cursor: "pointer",
              boxShadow: "0 4px 16px rgba(0,123,255,0.4)",
              transition: "transform 0.2s, box-shadow 0.2s",
            }}
              onMouseEnter={e => { e.currentTarget.style.transform = "scale(1.05)"; e.currentTarget.style.boxShadow = "0 6px 20px rgba(0,123,255,0.5)"; }}
              onMouseLeave={e => { e.currentTarget.style.transform = "scale(1)"; e.currentTarget.style.boxShadow = "0 4px 16px rgba(0,123,255,0.4)"; }}
            >
              Launch App →
            </button>
          </div>
        </div>
      </nav>

      {/* ════════════════════════════════════════════════════════════════════
          HERO
      ════════════════════════════════════════════════════════════════════ */}
      <section style={{
        minHeight: "100vh",
        background: "linear-gradient(135deg,#0f0c29 0%,#302b63 55%,#24243e 100%)",
        display: "flex", flexDirection: "column",
        alignItems: "center", justifyContent: "center",
        textAlign: "center", padding: "120px 24px 80px",
        position: "relative", overflow: "hidden",
      }}>
        {/* Decorative blobs */}
        {[
          { top:"8%",  left:"3%",  size:380, c:"rgba(0,123,255,0.18)" },
          { top:"55%", right:"3%", size:300, c:"rgba(102,16,242,0.18)" },
          { top:"35%", left:"45%", size:220, c:"rgba(40,167,69,0.12)" },
        ].map((b,i) => (
          <div key={i} style={{
            position:"absolute", borderRadius:"50%",
            width:b.size, height:b.size, background:b.c,
            top:b.top, left:(b as any).left, right:(b as any).right,
            filter:"blur(70px)", pointerEvents:"none",
          }}/>
        ))}

        {/* Live badge */}
        <div style={{
          display:"inline-flex", alignItems:"center", gap:8,
          background:"rgba(255,255,255,0.08)",
          border:"1px solid rgba(255,255,255,0.18)",
          borderRadius:50, padding:"7px 18px",
          color:"rgba(255,255,255,0.88)", fontSize:13,
          marginBottom:28, backdropFilter:"blur(10px)",
        }}>
          <span style={{ width:8, height:8, borderRadius:"50%", background:"#28a745", display:"inline-block", boxShadow:"0 0 6px #28a745" }}/>
          Live · {contactCount ?? 250}+ Contacts · Powered by Google Gemini AI
        </div>

        {/* Headline */}
        <h1 style={{
          fontSize:"clamp(2.4rem,6vw,4.2rem)",
          fontWeight:900, color:"white",
          margin:"0 0 22px", lineHeight:1.12, maxWidth:820,
        }}>
          Turn Visiting Cards Into<br/>
          <span style={{
            background:"linear-gradient(90deg,#4facfe 0%,#00f2fe 100%)",
            WebkitBackgroundClip:"text", WebkitTextFillColor:"transparent",
          }}>
            Smart Digital Contacts
          </span>
        </h1>

        {/* Sub */}
        <p style={{
          fontSize:"clamp(1rem,2.5vw,1.2rem)",
          color:"rgba(255,255,255,0.70)", maxWidth:620,
          margin:"0 0 44px", lineHeight:1.75,
        }}>
          AI-powered visiting card scanner that extracts name, phone, email, company
          and address in under 5 seconds. Search by profession, find the nearest
          expert using real GPS distance.
        </p>

        {/* CTA */}
        <div style={{ display:"flex", gap:14, flexWrap:"wrap", justifyContent:"center", marginBottom:64 }}>
          <button onClick={onGetStarted} style={{
            padding:"16px 40px", borderRadius:50, border:"none",
            background:"linear-gradient(135deg,#007bff,#6610f2)",
            color:"white", fontWeight:800, fontSize:"16px", cursor:"pointer",
            boxShadow:"0 8px 32px rgba(0,123,255,0.45)",
            transition:"transform 0.2s",
          }}
            onMouseEnter={e => (e.currentTarget.style.transform="scale(1.05)")}
            onMouseLeave={e => (e.currentTarget.style.transform="scale(1)")}
          >🚀 Get Started Free</button>
          <button onClick={() => scrollTo("howitworks")} style={{
            padding:"16px 40px", borderRadius:50,
            border:"2px solid rgba(255,255,255,0.28)",
            background:"transparent", color:"white",
            fontWeight:700, fontSize:"16px", cursor:"pointer",
            backdropFilter:"blur(8px)",
            transition:"background 0.2s",
          }}
            onMouseEnter={e => (e.currentTarget.style.background="rgba(255,255,255,0.08)")}
            onMouseLeave={e => (e.currentTarget.style.background="transparent")}
          >See How It Works ↓</button>
        </div>

        {/* Stats */}
        <div style={{
          display:"flex", gap:"48px", flexWrap:"wrap", justifyContent:"center",
          borderTop:"1px solid rgba(255,255,255,0.12)", paddingTop:40,
        }}>
          {[
            { val:3,   suf:"s",  label:"Card scan time" },
            { val:90,  suf:"%+", label:"OCR accuracy" },
            { val:contactCount??250, suf:"+", label:"Contacts stored" },
            { val:80,  suf:"+",  label:"Indian cities mapped" },
          ].map((s,i) => (
            <div key={i} style={{ textAlign:"center" }}>
              <div style={{ fontSize:"2.2rem", fontWeight:900, color:"white" }}>
                <Counter target={s.val} suffix={s.suf}/>
              </div>
              <div style={{ fontSize:"13px", color:"rgba(255,255,255,0.50)", marginTop:4 }}>{s.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* ════════════════════════════════════════════════════════════════════
          HOW IT WORKS
      ════════════════════════════════════════════════════════════════════ */}
      <section id="howitworks" style={{ padding:"90px 24px", background:"#f8f9ff" }}>
        <div style={{ maxWidth:960, margin:"0 auto", textAlign:"center" }}>
          <span style={{ color:"#007bff", fontWeight:700, fontSize:12, letterSpacing:3, textTransform:"uppercase" }}>
            Simple Process
          </span>
          <h2 style={{ fontSize:"clamp(1.8rem,4vw,2.6rem)", fontWeight:900, color:"#1a1a2e", margin:"12px 0 16px" }}>
            From Physical Card to Smart Contact
          </h2>
          <p style={{ color:"#666", fontSize:"1.05rem", maxWidth:540, margin:"0 auto 60px", lineHeight:1.7 }}>
            No manual typing. No lost cards. Scan once, search forever.
          </p>

          <div style={{ display:"flex", gap:24, flexWrap:"wrap", justifyContent:"center" }}>
            {[
              { n:"01", icon:"📷", color:"#007bff", bg:"#E3F2FD",
                title:"Upload Card Photo",
                desc:"Take a photo of the front and back of any visiting card. Supports JPG, PNG, HEIC from any mobile camera. Client-side compression ensures fast upload." },
              { n:"02", icon:"🧠", color:"#6610f2", bg:"#EDE7F6",
                title:"Gemini AI Extracts Data",
                desc:"Google Gemini Vision AI reads both card sides in a single API call. Extracts name, phone, email, company, designation, address, website and GSTIN with 90%+ accuracy." },
              { n:"03", icon:"✅", color:"#28a745", bg:"#E8F5E9",
                title:"Review & Edit Fields",
                desc:"All extracted fields are shown as editable inputs. Orange badge highlights any changes. Save corrections instantly — your data, your control." },
              { n:"04", icon:"🔍", color:"#fd7e14", bg:"#FFF3E0",
                title:"Search & Connect",
                desc:"Find any contact by profession, company or service. GPS ranks nearest professionals first using real Haversine distance. Call, email or map in one tap." },
            ].map((item,i) => (
              <div key={i} style={{
                flex:"1 1 200px", maxWidth:220,
                background:"white", borderRadius:20,
                padding:"36px 22px 28px", textAlign:"left",
                boxShadow:"0 4px 24px rgba(0,0,0,0.07)",
                border:"1px solid #eee", position:"relative",
              }}>
                <div style={{
                  position:"absolute", top:-14, left:20,
                  background:item.color, color:"white",
                  fontWeight:900, fontSize:11, padding:"4px 14px", borderRadius:50,
                }}>STEP {item.n}</div>
                <div style={{
                  width:54, height:54, borderRadius:16,
                  background:item.bg, fontSize:26,
                  display:"flex", alignItems:"center", justifyContent:"center",
                  marginBottom:16,
                }}>{item.icon}</div>
                <h3 style={{ fontWeight:800, fontSize:"1rem", color:"#1a1a2e", margin:"0 0 10px" }}>{item.title}</h3>
                <p style={{ color:"#666", fontSize:"13.5px", lineHeight:1.7, margin:0 }}>{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ════════════════════════════════════════════════════════════════════
          FEATURES
      ════════════════════════════════════════════════════════════════════ */}
      <section id="features" style={{ padding:"90px 24px", background:"white" }}>
        <div style={{ maxWidth:1100, margin:"0 auto" }}>
          <div style={{ textAlign:"center", marginBottom:60 }}>
            <span style={{ color:"#007bff", fontWeight:700, fontSize:12, letterSpacing:3, textTransform:"uppercase" }}>
              Core Features
            </span>
            <h2 style={{ fontSize:"clamp(1.8rem,4vw,2.6rem)", fontWeight:900, color:"#1a1a2e", margin:"12px 0 0" }}>
              Everything You Need to Manage Contacts
            </h2>
          </div>

          <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fit,minmax(300px,1fr))", gap:22 }}>
            {[
              { icon:"🤖", color:"#007bff",
                title:"Gemini Vision AI OCR",
                desc:"Google's multimodal AI reads any card layout — rotated, dark background, colored, sideways. Both card sides processed in a single API call. Returns structured JSON directly.",
                tags:["90%+ accuracy","Single API call","Any card layout"] },
              { icon:"📍", color:"#28a745",
                title:"Real GPS Distance Ranking",
                desc:"Haversine formula calculates actual distance from your GPS location to each contact's city. 80+ Indian cities mapped. Nearest professionals always shown first.",
                tags:["Haversine formula","80+ cities","Nearest first"] },
              { icon:"💬", color:"#6610f2",
                title:"AI Chatbot Assistant",
                desc:"Ask in plain English: 'Find me an eye surgeon near Pune'. Gemini picks the best 3 contacts by index — no name-matching errors. Natural language reply with contact cards.",
                tags:["Natural language","Index-based","Strict filtering"] },
              { icon:"🎤", color:"#fd7e14",
                title:"Voice & Ambient Search",
                desc:"Tap the mic to speak your query. Smart Listen mode continuously detects service keywords from ambient conversation and auto-searches — like Google Ads but for your contacts.",
                tags:["en-IN locale","Continuous listen","Auto-search"] },
              { icon:"✏️", color:"#dc3545",
                title:"Editable Extraction Results",
                desc:"Every extracted field is an editable input. Orange border and 'edited' badge show changes. Save corrections with one click. Reset to original anytime.",
                tags:["Inline editing","Change tracking","Instant save"] },
              { icon:"🔒", color:"#20c997",
                title:"Smart Duplicate Detection",
                desc:"Automatically detects duplicate contacts by email, phone (last 10 digits), or name before saving. Prevents clutter and keeps your database clean.",
                tags:["Email match","Phone match","Name match"] },
            ].map((f,i) => (
              <div key={i} style={{
                padding:"28px", borderRadius:18,
                border:"1.5px solid #eee", background:"#fafafa",
                transition:"all 0.25s",
              }}
                onMouseEnter={e => {
                  const d = e.currentTarget as HTMLDivElement;
                  d.style.boxShadow = `0 12px 40px ${f.color}22`;
                  d.style.borderColor = f.color + "44";
                  d.style.transform = "translateY(-5px)";
                  d.style.background = "white";
                }}
                onMouseLeave={e => {
                  const d = e.currentTarget as HTMLDivElement;
                  d.style.boxShadow = "none";
                  d.style.borderColor = "#eee";
                  d.style.transform = "translateY(0)";
                  d.style.background = "#fafafa";
                }}
              >
                <div style={{
                  width:52, height:52, borderRadius:14,
                  background:f.color+"18",
                  display:"flex", alignItems:"center", justifyContent:"center",
                  fontSize:26, marginBottom:16,
                }}>{f.icon}</div>
                <h3 style={{ fontWeight:800, fontSize:"1.05rem", color:"#1a1a2e", margin:"0 0 10px" }}>{f.title}</h3>
                <p style={{ color:"#666", fontSize:"13.5px", lineHeight:1.7, margin:"0 0 16px" }}>{f.desc}</p>
                <div style={{ display:"flex", gap:6, flexWrap:"wrap" }}>
                  {f.tags.map(t => (
                    <span key={t} style={{
                      padding:"3px 10px", borderRadius:50,
                      background:f.color+"12", color:f.color,
                      fontSize:11, fontWeight:700,
                    }}>{t}</span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ════════════════════════════════════════════════════════════════════
          SERVICES / USE CASES
      ════════════════════════════════════════════════════════════════════ */}
      <section style={{ padding:"90px 24px", background:"#f8f9ff" }}>
        <div style={{ maxWidth:1000, margin:"0 auto", textAlign:"center" }}>
          <span style={{ color:"#007bff", fontWeight:700, fontSize:12, letterSpacing:3, textTransform:"uppercase" }}>
            Use Cases
          </span>
          <h2 style={{ fontSize:"clamp(1.8rem,4vw,2.6rem)", fontWeight:900, color:"#1a1a2e", margin:"12px 0 16px" }}>
            Who Is This For?
          </h2>
          <p style={{ color:"#666", fontSize:"1.05rem", maxWidth:540, margin:"0 auto 56px", lineHeight:1.7 }}>
            Anyone who collects visiting cards and wants to find the right contact fast.
          </p>
          <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fit,minmax(180px,1fr))", gap:18 }}>
            {[
              { icon:"💼", title:"Sales Professionals", desc:"Scan 50+ cards from an expo in minutes. Search by company or service instantly." },
              { icon:"🏥", title:"Healthcare Seekers", desc:"Find the nearest doctor, dentist or specialist from your contact network." },
              { icon:"⚖️", title:"Legal & Finance", desc:"Locate your advocate, CA or financial advisor with one voice query." },
              { icon:"🏗️", title:"Real Estate & Construction", desc:"Find architects, contractors and builders sorted by proximity." },
              { icon:"⚡", title:"Home Services", desc:"Search electrician, plumber, AC repair — nearest professional first." },
              { icon:"🌱", title:"Solar & Energy", desc:"Connect with renewable energy experts and solar installers near you." },
            ].map((u,i) => (
              <div key={i} style={{
                background:"white", borderRadius:16, padding:"28px 20px",
                boxShadow:"0 2px 16px rgba(0,0,0,0.06)", border:"1px solid #eee",
                textAlign:"center",
              }}>
                <div style={{ fontSize:36, marginBottom:12 }}>{u.icon}</div>
                <h4 style={{ fontWeight:800, fontSize:"0.95rem", color:"#1a1a2e", margin:"0 0 8px" }}>{u.title}</h4>
                <p style={{ color:"#777", fontSize:"13px", lineHeight:1.6, margin:0 }}>{u.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ════════════════════════════════════════════════════════════════════
          TECHNOLOGY STACK
      ════════════════════════════════════════════════════════════════════ */}
      <section id="tech" style={{ padding:"80px 24px", background:"white" }}>
        <div style={{ maxWidth:900, margin:"0 auto", textAlign:"center" }}>
          <span style={{ color:"#007bff", fontWeight:700, fontSize:12, letterSpacing:3, textTransform:"uppercase" }}>
            Technology
          </span>
          <h2 style={{ fontSize:"clamp(1.8rem,4vw,2.6rem)", fontWeight:900, color:"#1a1a2e", margin:"12px 0 16px" }}>
            Built on Enterprise-Grade Stack
          </h2>
          <p style={{ color:"#666", fontSize:"1.05rem", maxWidth:540, margin:"0 auto 48px", lineHeight:1.7 }}>
            Every component chosen for accuracy, speed and reliability.
          </p>

          <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fit,minmax(200px,1fr))", gap:16, marginBottom:40 }}>
            {[
              { icon:"🧠", name:"Google Gemini AI", role:"Vision OCR + Chatbot", color:"#4285F4" },
              { icon:"⚡", name:"FastAPI + Python", role:"REST API Backend", color:"#009688" },
              { icon:"⚛️", name:"React 19 + TypeScript", role:"Frontend UI", color:"#61DAFB" },
              { icon:"🗄️", name:"MySQL 8.0", role:"Relational Database", color:"#F29111" },
              { icon:"👁️", name:"OpenCV 4.8", role:"Image Preprocessing", color:"#5C3EE8" },
              { icon:"🔤", name:"spaCy + EasyOCR", role:"NLP + Fallback OCR", color:"#09A3D5" },
            ].map((t,i) => (
              <div key={i} style={{
                padding:"22px 18px", borderRadius:14,
                border:`2px solid ${t.color}22`,
                background:`${t.color}08`,
                textAlign:"center",
              }}>
                <div style={{ fontSize:28, marginBottom:8 }}>{t.icon}</div>
                <div style={{ fontWeight:800, fontSize:"0.9rem", color:"#1a1a2e", marginBottom:4 }}>{t.name}</div>
                <div style={{ fontSize:"12px", color:t.color, fontWeight:600 }}>{t.role}</div>
              </div>
            ))}
          </div>

          {/* Pipeline diagram */}
          <div style={{
            background:"#f8f9ff", borderRadius:16, padding:"28px 24px",
            border:"1px solid #e0e8ff",
          }}>
            <div style={{ fontSize:"13px", color:"#888", marginBottom:16, fontWeight:600 }}>
              OCR PIPELINE
            </div>
            <div style={{
              display:"flex", alignItems:"center", justifyContent:"center",
              gap:8, flexWrap:"wrap",
            }}>
              {[
                { label:"Card Image", color:"#1565C0" },
                { label:"→" },
                { label:"CLAHE + Sharpen", color:"#E65100" },
                { label:"→" },
                { label:"Gemini Vision AI", color:"#B71C1C" },
                { label:"→" },
                { label:"Field Validator", color:"#2E7D32" },
                { label:"→" },
                { label:"MySQL Storage", color:"#4A148C" },
              ].map((item,i) => (
                item.label === "→"
                  ? <span key={i} style={{ color:"#aaa", fontSize:18, fontWeight:700 }}>→</span>
                  : <span key={i} style={{
                      padding:"6px 14px", borderRadius:50,
                      background:item.color+"15", color:item.color,
                      fontSize:12, fontWeight:700, border:`1px solid ${item.color}30`,
                    }}>{item.label}</span>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ════════════════════════════════════════════════════════════════════
          CTA BANNER
      ════════════════════════════════════════════════════════════════════ */}
      <section style={{
        padding:"90px 24px",
        background:"linear-gradient(135deg,#007bff 0%,#6610f2 100%)",
        textAlign:"center", position:"relative", overflow:"hidden",
      }}>
        <div style={{
          position:"absolute", top:-80, right:-80,
          width:300, height:300, borderRadius:"50%",
          background:"rgba(255,255,255,0.06)",
        }}/>
        <div style={{
          position:"absolute", bottom:-60, left:-60,
          width:250, height:250, borderRadius:"50%",
          background:"rgba(255,255,255,0.06)",
        }}/>
        <div style={{ position:"relative", zIndex:1 }}>
          <h2 style={{ fontSize:"clamp(1.8rem,4vw,2.8rem)", fontWeight:900, color:"white", margin:"0 0 16px" }}>
            Ready to Digitize Your Network?
          </h2>
          <p style={{ color:"rgba(255,255,255,0.80)", fontSize:"1.1rem", margin:"0 0 40px", maxWidth:500, marginLeft:"auto", marginRight:"auto" }}>
            Scan your first visiting card in under 5 seconds. No signup required.
          </p>
          <div style={{ display:"flex", gap:14, justifyContent:"center", flexWrap:"wrap" }}>
            <button onClick={onGetStarted} style={{
              padding:"16px 44px", borderRadius:50, border:"none",
              background:"white", color:"#007bff",
              fontWeight:800, fontSize:"16px", cursor:"pointer",
              boxShadow:"0 8px 32px rgba(0,0,0,0.20)",
              transition:"transform 0.2s",
            }}
              onMouseEnter={e => (e.currentTarget.style.transform="scale(1.05)")}
              onMouseLeave={e => (e.currentTarget.style.transform="scale(1)")}
            >🚀 Launch App Now</button>
            <button onClick={() => scrollTo("features")} style={{
              padding:"16px 44px", borderRadius:50,
              border:"2px solid rgba(255,255,255,0.5)",
              background:"transparent", color:"white",
              fontWeight:700, fontSize:"16px", cursor:"pointer",
            }}>View Features</button>
          </div>
        </div>
      </section>

      {/* ════════════════════════════════════════════════════════════════════
          CONTACT / SUPPORT
      ════════════════════════════════════════════════════════════════════ */}
      <section id="contact" style={{ padding:"80px 24px", background:"#f8f9ff" }}>
        <div style={{ maxWidth:700, margin:"0 auto", textAlign:"center" }}>
          <span style={{ color:"#007bff", fontWeight:700, fontSize:12, letterSpacing:3, textTransform:"uppercase" }}>
            Support
          </span>
          <h2 style={{ fontSize:"clamp(1.6rem,4vw,2.2rem)", fontWeight:900, color:"#1a1a2e", margin:"12px 0 16px" }}>
            Need Help?
          </h2>
          <p style={{ color:"#666", fontSize:"1.05rem", margin:"0 0 40px", lineHeight:1.7 }}>
            Have questions about the system or want to contribute? Reach out.
          </p>
          <div style={{ display:"flex", gap:16, justifyContent:"center", flexWrap:"wrap" }}>
            {[
              { icon:"📧", label:"Email Support", value:"sarthak22kar@gmail.com", href:"mailto:sarthak22kar@gmail.com", color:"#007bff" },
              { icon:"💻", label:"GitHub Repository", value:"Sarthak22kar/AI-Smart-Card", href:"https://github.com/Sarthak22kar/AI-Smart-Card", color:"#1a1a2e" },
              { icon:"📖", label:"API Documentation", value:"localhost:8000/docs", href:"http://127.0.0.1:8000/docs", color:"#28a745" },
            ].map((c,i) => (
              <a key={i} href={c.href} target="_blank" rel="noreferrer" style={{
                display:"flex", flexDirection:"column", alignItems:"center",
                padding:"24px 28px", borderRadius:16,
                background:"white", border:`2px solid ${c.color}22`,
                textDecoration:"none", minWidth:180,
                boxShadow:"0 2px 16px rgba(0,0,0,0.06)",
                transition:"transform 0.2s, box-shadow 0.2s",
              }}
                onMouseEnter={e => { (e.currentTarget as HTMLAnchorElement).style.transform="translateY(-4px)"; (e.currentTarget as HTMLAnchorElement).style.boxShadow=`0 8px 24px ${c.color}22`; }}
                onMouseLeave={e => { (e.currentTarget as HTMLAnchorElement).style.transform="translateY(0)"; (e.currentTarget as HTMLAnchorElement).style.boxShadow="0 2px 16px rgba(0,0,0,0.06)"; }}
              >
                <span style={{ fontSize:28, marginBottom:8 }}>{c.icon}</span>
                <span style={{ fontWeight:700, fontSize:"13px", color:"#1a1a2e", marginBottom:4 }}>{c.label}</span>
                <span style={{ fontSize:"12px", color:c.color }}>{c.value}</span>
              </a>
            ))}
          </div>
        </div>
      </section>

      {/* ════════════════════════════════════════════════════════════════════
          FOOTER
      ════════════════════════════════════════════════════════════════════ */}
      <footer style={{
        background:"#0f0c29",
        color:"rgba(255,255,255,0.6)",
        padding:"60px 24px 32px",
      }}>
        <div style={{ maxWidth:1100, margin:"0 auto" }}>
          {/* Top row */}
          <div style={{
            display:"grid",
            gridTemplateColumns:"repeat(auto-fit,minmax(200px,1fr))",
            gap:40, marginBottom:48,
          }}>
            {/* Brand */}
            <div>
              <div style={{ display:"flex", alignItems:"center", gap:10, marginBottom:14 }}>
                <div style={{
                  width:38, height:38, borderRadius:10,
                  background:"linear-gradient(135deg,#007bff,#6610f2)",
                  display:"flex", alignItems:"center", justifyContent:"center", fontSize:18,
                }}>🤖</div>
                <span style={{ fontWeight:800, fontSize:"1.05rem", color:"white" }}>AI Smart Card Network</span>
              </div>
              <p style={{ fontSize:"13.5px", lineHeight:1.7, margin:"0 0 16px", maxWidth:240 }}>
                AI-powered visiting card digitization and intelligent contact management system.
              </p>
              <div style={{ display:"flex", gap:10 }}>
                {[
                  { label:"GitHub", href:"https://github.com/Sarthak22kar/AI-Smart-Card" },
                ].map((l,i) => (
                  <a key={i} href={l.href} target="_blank" rel="noreferrer" style={{
                    padding:"6px 14px", borderRadius:50,
                    border:"1px solid rgba(255,255,255,0.2)",
                    color:"rgba(255,255,255,0.7)", fontSize:12,
                    textDecoration:"none", fontWeight:600,
                    transition:"border-color 0.2s",
                  }}>{l.label}</a>
                ))}
              </div>
            </div>

            {/* Product */}
            <div>
              <h4 style={{ color:"white", fontWeight:700, fontSize:"14px", marginBottom:16, textTransform:"uppercase", letterSpacing:1 }}>Product</h4>
              {["Scan Card","Smart Search","AI Chatbot","Contact Manager","Stats Dashboard"].map(l => (
                <div key={l} style={{ marginBottom:10 }}>
                  <button onClick={onGetStarted} style={{
                    background:"none", border:"none", cursor:"pointer",
                    color:"rgba(255,255,255,0.6)", fontSize:"13.5px", padding:0,
                    transition:"color 0.2s",
                  }}
                    onMouseEnter={e => (e.currentTarget.style.color="white")}
                    onMouseLeave={e => (e.currentTarget.style.color="rgba(255,255,255,0.6)")}
                  >{l}</button>
                </div>
              ))}
            </div>

            {/* Technology */}
            <div>
              <h4 style={{ color:"white", fontWeight:700, fontSize:"14px", marginBottom:16, textTransform:"uppercase", letterSpacing:1 }}>Technology</h4>
              {["Google Gemini AI","FastAPI Backend","React Frontend","MySQL Database","OpenCV Processing","spaCy NLP"].map(l => (
                <div key={l} style={{ marginBottom:10, fontSize:"13.5px" }}>{l}</div>
              ))}
            </div>

            {/* Support */}
            <div>
              <h4 style={{ color:"white", fontWeight:700, fontSize:"14px", marginBottom:16, textTransform:"uppercase", letterSpacing:1 }}>Support</h4>
              {[
                { label:"GitHub Issues", href:"https://github.com/Sarthak22kar/AI-Smart-Card/issues" },
                { label:"API Docs (Swagger)", href:"http://127.0.0.1:8000/docs" },
                { label:"Email: sarthak22kar@gmail.com", href:"mailto:sarthak22kar@gmail.com" },
              ].map(l => (
                <div key={l.label} style={{ marginBottom:10 }}>
                  <a href={l.href} target="_blank" rel="noreferrer" style={{
                    color:"rgba(255,255,255,0.6)", fontSize:"13.5px",
                    textDecoration:"none", transition:"color 0.2s",
                  }}
                    onMouseEnter={e => ((e.target as HTMLAnchorElement).style.color="white")}
                    onMouseLeave={e => ((e.target as HTMLAnchorElement).style.color="rgba(255,255,255,0.6)")}
                  >{l.label}</a>
                </div>
              ))}
            </div>
          </div>

          {/* Divider */}
          <div style={{ borderTop:"1px solid rgba(255,255,255,0.10)", paddingTop:28 }}>
            <div style={{
              display:"flex", justifyContent:"space-between", alignItems:"center",
              flexWrap:"wrap", gap:12,
            }}>
              <div style={{ fontSize:"13px" }}>
                © {new Date().getFullYear()} AI Smart Card Network. All rights reserved.
                <span style={{ margin:"0 8px", opacity:0.4 }}>·</span>
                Built by <span style={{ color:"#4facfe", fontWeight:600 }}>Sarthak Karkar</span>
              </div>
              <div style={{ display:"flex", gap:20, fontSize:"12px" }}>
                <span>Version 6.0.0</span>
                <span style={{ opacity:0.4 }}>·</span>
                <span>Gemini OCR · MySQL · FastAPI · React</span>
                <span style={{ opacity:0.4 }}>·</span>
                <span>Made in India 🇮🇳</span>
              </div>
            </div>
          </div>
        </div>
      </footer>

    </div>
  );
}

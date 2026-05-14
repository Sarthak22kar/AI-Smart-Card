import { useState, useEffect } from "react";
import SmartSearch from "./components/SmartSearch";
import UploadCard from "./components/UploadCard";
import ContactList from "./components/ContactList";
import DatabaseStats from "./components/DatabaseStats";

function App() {
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const [activeTab, setActiveTab] = useState<"search" | "scan" | "contacts" | "stats">("search");
  const [contactCount, setContactCount] = useState<number | null>(null);

  // Fetch real contact count from backend
  const fetchCount = () => {
    fetch("http://127.0.0.1:8000/stats/")
      .then(r => r.json())
      .then(d => setContactCount(d?.statistics?.total_contacts ?? null))
      .catch(() => {});
  };

  useEffect(() => {
    fetchCount();
  }, [refreshTrigger]); // re-fetch after every scan too

  const handleScanSuccess = () => {
    setRefreshTrigger(prev => prev + 1); // triggers fetchCount via useEffect
    setActiveTab("contacts");
  };

  const tabStyle = (tab: typeof activeTab) => ({
    padding: "10px 20px",
    border: "none",
    borderBottom: activeTab === tab ? "3px solid #007bff" : "3px solid transparent",
    backgroundColor: "transparent",
    color: activeTab === tab ? "#007bff" : "#666",
    fontWeight: activeTab === tab ? 700 : 400,
    cursor: "pointer",
    fontSize: "14px",
    whiteSpace: "nowrap" as const,
  });

  return (
    <div style={{
      minHeight: "100vh",
      backgroundColor: "#f4f6fb",
      fontFamily: "system-ui, -apple-system, sans-serif",
    }}>
      {/* ── Header ── */}
      <div style={{
        backgroundColor: "white",
        boxShadow: "0 2px 8px rgba(0,0,0,0.08)",
        position: "sticky", top: 0, zIndex: 100,
      }}>
        <div style={{ maxWidth: "800px", margin: "0 auto", padding: "0 16px" }}>
          <div style={{ padding: "14px 0 0", textAlign: "center" }}>
            <h1 style={{ margin: "0 0 2px", fontSize: "1.4rem", color: "#1a1a2e" }}>
              🤖 AI Smart Card Network
            </h1>
            <p style={{ margin: "0 0 10px", fontSize: "12px", color: "#888" }}>
              {contactCount !== null ? contactCount : "..."} contacts · Powered by Gemini AI
            </p>
          </div>
          {/* Tabs */}
          <div style={{ display: "flex", overflowX: "auto", borderTop: "1px solid #eee" }}>
            <button style={tabStyle("search")} onClick={() => setActiveTab("search")}>🔍 Search</button>
            <button style={tabStyle("scan")}   onClick={() => setActiveTab("scan")}>📷 Scan Card</button>
            <button style={tabStyle("contacts")} onClick={() => setActiveTab("contacts")}>
              📇 Contacts
            </button>
            <button style={tabStyle("stats")}  onClick={() => setActiveTab("stats")}>📊 Stats</button>
          </div>
        </div>
      </div>

      {/* ── Content ── */}
      <div style={{ maxWidth: "800px", margin: "0 auto", padding: "24px 16px" }}>

        {activeTab === "search" && (
          <SmartSearch />
        )}

        {activeTab === "scan" && (
          <UploadCard onScanSuccess={handleScanSuccess} />
        )}

        {activeTab === "contacts" && (
          <ContactList refreshTrigger={refreshTrigger} />
        )}

        {activeTab === "stats" && (
          <DatabaseStats />
        )}
      </div>

      <footer style={{
        textAlign: "center", padding: "20px",
        color: "#aaa", fontSize: "12px",
        borderTop: "1px solid #eee", marginTop: "20px",
      }}>
        AI Smart Card Network · Gemini OCR · MySQL
      </footer>
    </div>
  );
}

export default App;

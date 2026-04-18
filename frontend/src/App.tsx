import { useState } from "react";
import UploadCard from "./components/UploadCard";
import Recommendation from "./components/Recommendation";
import ContactList from "./components/ContactList";
import DatabaseStats from "./components/DatabaseStats";

function App() {
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const [output, setOutput] = useState("");

  const handleScanSuccess = () => {
    setRefreshTrigger(prev => prev + 1);
  };

  return (
    <div style={{ 
      minHeight: "100vh",
      backgroundColor: "#f8f9fa",
      padding: "20px",
      fontFamily: "system-ui, -apple-system, sans-serif"
    }}>
      <div style={{ maxWidth: "1200px", margin: "0 auto" }}>
        <header style={{ textAlign: "center", marginBottom: "40px" }}>
          <h1 style={{ 
            fontSize: "2.5rem", 
            color: "#007bff", 
            marginBottom: "10px",
            textShadow: "2px 2px 4px rgba(0,0,0,0.1)"
          }}>
            🤖 AI Smart Visiting Card Network
          </h1>
          <p style={{ 
            fontSize: "1.2rem", 
            color: "#6c757d",
            maxWidth: "600px",
            margin: "0 auto"
          }}>
            Scan visiting cards, build your professional network, and get AI-powered service recommendations
          </p>
        </header>

        <div style={{ 
          display: "grid", 
          gridTemplateColumns: "1fr", 
          gap: "30px",
          alignItems: "start"
        }}>
          {/* Upload Section */}
          <section>
            <UploadCard onScanSuccess={handleScanSuccess} />
          </section>

          {/* Recommendation Section */}
          <section>
            <Recommendation setOutput={setOutput} />
          </section>

          {/* Contact List Section */}
          <section style={{ display: "flex", justifyContent: "center" }}>
            <ContactList refreshTrigger={refreshTrigger} />
          </section>

          {/* Database Statistics Section */}
          <section>
            <DatabaseStats />
          </section>
        </div>

        {/* Footer */}
        <footer style={{ 
          textAlign: "center", 
          marginTop: "50px", 
          padding: "20px",
          color: "#6c757d",
          borderTop: "1px solid #dee2e6"
        }}>
          <p>🚀 Powered by AI • OCR Technology • Smart Recommendations</p>
        </footer>
      </div>
    </div>
  );
}

export default App;
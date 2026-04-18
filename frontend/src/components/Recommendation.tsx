import { useState } from "react";

interface RecommendedContact {
  id: number;
  name: string;
  phone: string;
  email: string;
  profession: string;
  company: string;
  location: string;
  calculated_score: number;
}

interface RecommendationResult {
  service_requested: string;
  recommended_contact: RecommendedContact;
  alternatives: RecommendedContact[];
  total_matches: number;
  error?: string;
  suggestion?: string;
}

interface Props {
  setOutput: (data: string) => void;
}

function Recommendation({ setOutput }: Props) {
  const [service, setService] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<RecommendationResult | null>(null);

  const getRecommendation = async () => {
    if (!service.trim()) {
      alert("Please enter a service type");
      return;
    }

    setLoading(true);
    try {
      const res = await fetch(`http://127.0.0.1:8000/recommend/${encodeURIComponent(service)}`);
      const data = await res.json();
      
      setResult(data);
      setOutput(JSON.stringify(data, null, 2));
    } catch (error) {
      console.error("Error getting recommendation:", error);
      alert("Failed to get recommendation");
    } finally {
      setLoading(false);
    }
  };

  const ContactRecommendationCard = ({ contact, isMain = false }: { contact: RecommendedContact, isMain?: boolean }) => (
    <div style={{ 
      padding: "15px", 
      border: isMain ? "2px solid #28a745" : "1px solid #ddd",
      borderRadius: "10px",
      marginBottom: "10px",
      backgroundColor: isMain ? "#f8fff9" : "#f9f9f9",
      position: "relative"
    }}>
      {isMain && (
        <div style={{ 
          position: "absolute", 
          top: "-10px", 
          left: "15px", 
          backgroundColor: "#28a745", 
          color: "white", 
          padding: "5px 10px", 
          borderRadius: "15px", 
          fontSize: "12px",
          fontWeight: "bold"
        }}>
          🏆 BEST MATCH
        </div>
      )}
      
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div style={{ flex: 1 }}>
          <h3 style={{ margin: "0 0 10px 0", color: "#333" }}>
            {contact.name}
          </h3>
          
          <div style={{ display: "flex", flexWrap: "wrap", gap: "10px", marginBottom: "10px" }}>
            <span style={{ 
              backgroundColor: "#007bff", 
              color: "white", 
              padding: "3px 8px", 
              borderRadius: "12px", 
              fontSize: "12px" 
            }}>
              {contact.profession}
            </span>
            
            <span style={{ 
              backgroundColor: "#6c757d", 
              color: "white", 
              padding: "3px 8px", 
              borderRadius: "12px", 
              fontSize: "12px" 
            }}>
              Score: {(contact.calculated_score * 100).toFixed(1)}%
            </span>
          </div>

          <div style={{ fontSize: "14px", color: "#666" }}>
            {contact.phone && <p style={{ margin: "3px 0" }}>📞 {contact.phone}</p>}
            {contact.email && <p style={{ margin: "3px 0" }}>📧 {contact.email}</p>}
            {contact.company && <p style={{ margin: "3px 0" }}>🏢 {contact.company}</p>}
            {contact.location && <p style={{ margin: "3px 0" }}>📍 {contact.location}</p>}
          </div>
        </div>
      </div>
    </div>
  );

  return (
    <div style={{ maxWidth: "600px", margin: "0 auto" }}>
      <h2>🤖 AI Service Recommendation</h2>
      
      <div style={{ 
        display: "flex", 
        gap: "10px", 
        marginBottom: "20px",
        alignItems: "center"
      }}>
        <input
          type="text"
          placeholder="e.g. plumber, electrician, doctor, lawyer..."
          value={service}
          onChange={(e) => setService(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && getRecommendation()}
          style={{ 
            flex: 1,
            padding: "12px", 
            fontSize: "16px", 
            border: "2px solid #ddd", 
            borderRadius: "8px",
            outline: "none"
          }}
        />
        <button 
          onClick={getRecommendation}
          disabled={loading}
          style={{ 
            padding: "12px 20px", 
            fontSize: "16px", 
            backgroundColor: "#007bff",
            color: "white",
            border: "none",
            borderRadius: "8px",
            cursor: loading ? "not-allowed" : "pointer",
            opacity: loading ? 0.6 : 1
          }}
        >
          {loading ? "🔍 Searching..." : "🔍 Find Expert"}
        </button>
      </div>

      {result && (
        <div style={{ textAlign: "left" }}>
          {result.error ? (
            <div style={{ 
              padding: "20px", 
              backgroundColor: "#fff3cd", 
              border: "1px solid #ffeaa7", 
              borderRadius: "8px",
              color: "#856404"
            }}>
              <h3>⚠️ {result.error}</h3>
              {result.suggestion && <p>{result.suggestion}</p>}
            </div>
          ) : (
            <div>
              <div style={{ marginBottom: "20px", textAlign: "center" }}>
                <h3>🎯 Results for "{result.service_requested}"</h3>
                <p style={{ color: "#666" }}>Found {result.total_matches} matching professional{result.total_matches !== 1 ? 's' : ''}</p>
              </div>

              {result.recommended_contact && (
                <div style={{ marginBottom: "20px" }}>
                  <ContactRecommendationCard contact={result.recommended_contact} isMain={true} />
                </div>
              )}

              {result.alternatives && result.alternatives.length > 0 && (
                <div>
                  <h4 style={{ color: "#666", marginBottom: "10px" }}>Alternative Options:</h4>
                  {result.alternatives.map((contact, index) => (
                    <ContactRecommendationCard key={contact.id || index} contact={contact} />
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default Recommendation;
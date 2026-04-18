import { useEffect, useState } from "react";

interface DatabaseStats {
  total_contacts: number;
  by_profession: Record<string, number>;
  average_confidence: number;
  field_completion: {
    phone: number;
    email: number;
    profession: number;
    company: number;
    location: number;
  };
}

interface StatsResponse {
  status: string;
  statistics: DatabaseStats;
  database_health: string;
}

function DatabaseStats() {
  const [stats, setStats] = useState<DatabaseStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [showStats, setShowStats] = useState(false);

  const fetchStats = async () => {
    setLoading(true);
    try {
      console.log("Fetching stats from backend...");
      const res = await fetch("http://127.0.0.1:8000/stats/");
      console.log("Response status:", res.status);
      const data: StatsResponse = await res.json();
      console.log("Response data:", data);
      if (data.status === "success") {
        setStats(data.statistics);
        console.log("Stats set successfully:", data.statistics);
      } else {
        console.error("Backend returned error status:", data.status);
      }
    } catch (error) {
      console.error("Failed to fetch stats", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (showStats) {
      fetchStats();
    }
  }, [showStats]);

  if (!showStats) {
    return (
      <div style={{ textAlign: "center", marginTop: "20px" }}>
        <button
          onClick={() => setShowStats(true)}
          style={{
            padding: "10px 20px",
            backgroundColor: "#6c757d",
            color: "white",
            border: "none",
            borderRadius: "8px",
            cursor: "pointer",
            fontSize: "14px"
          }}
        >
          📊 Show Database Statistics
        </button>
      </div>
    );
  }

  console.log("Rendering stats component. Loading:", loading, "Stats:", stats);

  return (
    <div style={{
      marginTop: "30px",
      padding: "20px",
      backgroundColor: "#f8f9fa",
      borderRadius: "10px",
      border: "1px solid #dee2e6",
      minHeight: "200px" // Add minimum height to prevent collapse
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "15px" }}>
        <h3 style={{ margin: 0, color: "#495057" }}>📊 Database Statistics</h3>
        <div>
          <button
            onClick={fetchStats}
            disabled={loading}
            style={{
              padding: "5px 10px",
              backgroundColor: "#007bff",
              color: "white",
              border: "none",
              borderRadius: "5px",
              cursor: loading ? "not-allowed" : "pointer",
              fontSize: "12px",
              marginRight: "10px"
            }}
          >
            {loading ? "🔄" : "🔄 Refresh"}
          </button>
          <button
            onClick={() => setShowStats(false)}
            style={{
              padding: "5px 10px",
              backgroundColor: "#6c757d",
              color: "white",
              border: "none",
              borderRadius: "5px",
              cursor: "pointer",
              fontSize: "12px"
            }}
          >
            ✕ Hide
          </button>
        </div>
      </div>

      {loading ? (
        <div style={{ textAlign: "center", padding: "20px" }}>
          <p>Loading statistics...</p>
        </div>
      ) : stats ? (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "20px" }}>
          {/* Overview */}
          <div>
            <h4 style={{ color: "#495057", marginBottom: "10px" }}>📈 Overview</h4>
            <div style={{ fontSize: "14px" }}>
              <p><strong>Total Contacts:</strong> {stats.total_contacts}</p>
              <p><strong>Avg. Confidence:</strong> {Math.round(stats.average_confidence * 100)}%</p>
            </div>
          </div>

          {/* Field Completion */}
          <div>
            <h4 style={{ color: "#495057", marginBottom: "10px" }}>📋 Field Completion</h4>
            <div style={{ fontSize: "12px" }}>
              {Object.entries(stats.field_completion).map(([field, count]) => (
                <div key={field} style={{ display: "flex", justifyContent: "space-between", marginBottom: "3px" }}>
                  <span>{field.charAt(0).toUpperCase() + field.slice(1)}:</span>
                  <span>{count}/{stats.total_contacts}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Professions */}
          {Object.keys(stats.by_profession).length > 0 && (
            <div style={{ gridColumn: "1 / -1" }}>
              <h4 style={{ color: "#495057", marginBottom: "10px" }}>💼 By Profession</h4>
              <div style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
                {Object.entries(stats.by_profession).map(([profession, count]) => (
                  <span
                    key={profession}
                    style={{
                      backgroundColor: "#007bff",
                      color: "white",
                      padding: "4px 8px",
                      borderRadius: "12px",
                      fontSize: "12px"
                    }}
                  >
                    {profession}: {count}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      ) : (
        <div style={{ textAlign: "center", padding: "20px" }}>
          <p style={{ color: "#dc3545" }}>Failed to load statistics. Please try refreshing.</p>
        </div>
      )}
    </div>
  );
}

export default DatabaseStats;
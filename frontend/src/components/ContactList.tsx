import { useEffect, useState } from "react";

interface Contact {
  id: number;
  name: string;
  phone: string;
  email: string;
  designation: string;
  company: string;
  address: string;
  website: string;
  gstin: string;
  extraction_confidence?: number;
  created_at?: string;
}

interface Props {
  refreshTrigger: number;
}

function ContactList({ refreshTrigger }: Props) {
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [loading, setLoading] = useState(false);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [showAll, setShowAll] = useState(false);

  useEffect(() => {
    fetchContacts();
  }, [refreshTrigger]);

  const fetchContacts = async () => {
    setLoading(true);
    try {
      const res = await fetch("http://127.0.0.1:8000/contacts/");
      const data = await res.json();
      setContacts(data.contacts || []);
    } catch (error) {
      console.error("Failed to fetch contacts", error);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id: number, name: string) => {
    if (!confirm(`Delete contact "${name}"?`)) return;
    await fetch(`http://127.0.0.1:8000/contacts/${id}`, { method: "DELETE" });
    fetchContacts();
  };

  // Filter out invalid entries
  const validContacts = contacts.filter(c =>
    c.name && c.name.trim() !== "" &&
    c.name.toLowerCase() !== "unknown" &&
    !c.name.toLowerCase().startsWith("error")
  );

  const displayed = showAll ? validContacts : validContacts.slice(0, 6);

  const confidenceColor = (v?: number) => {
    if (!v) return "#dc3545";
    if (v > 0.7) return "#28a745";
    if (v > 0.4) return "#ffc107";
    return "#dc3545";
  };

  return (
    <div style={{ marginTop: "30px", width: "100%", maxWidth: "640px", margin: "30px auto 0" }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
        <h2 style={{ margin: 0, fontSize: "1.3rem", color: "#1a1a2e" }}>
          📇 My Contacts <span style={{ fontSize: "0.9rem", color: "#888", fontWeight: 400 }}>({validContacts.length})</span>
        </h2>
        {validContacts.length > 6 && (
          <button onClick={() => setShowAll(!showAll)} style={{
            padding: "6px 14px", backgroundColor: "#007bff", color: "white",
            border: "none", borderRadius: "6px", cursor: "pointer", fontSize: "13px"
          }}>
            {showAll ? "Show Less" : `View All (${validContacts.length})`}
          </button>
        )}
      </div>

      {loading ? (
        <p style={{ color: "#888", textAlign: "center" }}>Loading contacts...</p>
      ) : validContacts.length === 0 ? (
        <div style={{
          padding: "30px", textAlign: "center", border: "2px dashed #ddd",
          borderRadius: "12px", color: "#aaa"
        }}>
          <p style={{ fontSize: "2rem", margin: "0 0 8px" }}>📭</p>
          <p>No contacts yet. Scan a visiting card to get started!</p>
        </div>
      ) : (
        <div>
          {displayed.map(contact => (
            <div key={contact.id} style={{
              border: "1px solid #e0e0e0", borderRadius: "10px",
              marginBottom: "10px", overflow: "hidden",
              backgroundColor: "white", boxShadow: "0 1px 4px rgba(0,0,0,0.06)"
            }}>
              {/* ── Main row: name + phone only ── */}
              <div
                onClick={() => setExpandedId(expandedId === contact.id ? null : contact.id)}
                style={{
                  display: "flex", justifyContent: "space-between", alignItems: "center",
                  padding: "14px 16px", cursor: "pointer",
                  backgroundColor: expandedId === contact.id ? "#f0f7ff" : "white"
                }}
              >
                <div>
                  <div style={{ fontWeight: 600, fontSize: "1rem", color: "#1a1a2e" }}>
                    👤 {contact.name}
                  </div>
                  <div style={{ fontSize: "0.9rem", color: "#555", marginTop: "3px" }}>
                    {contact.phone ? `📞 ${contact.phone}` : "📞 No phone"}
                  </div>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  {contact.extraction_confidence !== undefined && (
                    <span style={{
                      backgroundColor: confidenceColor(contact.extraction_confidence),
                      color: "white", padding: "2px 7px", borderRadius: "10px", fontSize: "11px"
                    }}>
                      {Math.round((contact.extraction_confidence || 0) * 100)}%
                    </span>
                  )}
                  <span style={{ color: "#aaa", fontSize: "13px" }}>
                    {expandedId === contact.id ? "▲" : "▼"}
                  </span>
                </div>
              </div>

              {/* ── Expanded: full details ── */}
              {expandedId === contact.id && (
                <div style={{
                  padding: "14px 16px", borderTop: "1px solid #eee",
                  backgroundColor: "#fafafa", fontSize: "14px"
                }}>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px" }}>
                    {contact.email && (
                      <div><span style={{ color: "#888" }}>📧 Email</span><br />
                        <a href={`mailto:${contact.email}`} style={{ color: "#007bff" }}>{contact.email}</a>
                      </div>
                    )}
                    {contact.designation && (
                      <div><span style={{ color: "#888" }}>💼 Designation</span><br />
                        <strong>{contact.designation}</strong>
                      </div>
                    )}
                    {contact.company && (
                      <div><span style={{ color: "#888" }}>🏢 Company</span><br />
                        {contact.company}
                      </div>
                    )}
                    {contact.website && (
                      <div><span style={{ color: "#888" }}>🌐 Website</span><br />
                        <a href={`https://${contact.website.replace(/^https?:\/\//, '')}`}
                          target="_blank" rel="noreferrer" style={{ color: "#007bff" }}>
                          {contact.website}
                        </a>
                      </div>
                    )}
                    {contact.gstin && (
                      <div><span style={{ color: "#888" }}>🧾 GSTIN</span><br />
                        <code style={{ fontSize: "12px" }}>{contact.gstin}</code>
                      </div>
                    )}
                    {contact.address && (
                      <div style={{ gridColumn: "1 / -1" }}>
                        <span style={{ color: "#888" }}>📍 Address</span><br />
                        {contact.address}
                      </div>
                    )}
                  </div>

                  <div style={{ marginTop: "12px", display: "flex", justifyContent: "flex-end" }}>
                    <button
                      onClick={() => handleDelete(contact.id, contact.name)}
                      style={{
                        padding: "5px 12px", backgroundColor: "#dc3545", color: "white",
                        border: "none", borderRadius: "6px", cursor: "pointer", fontSize: "12px"
                      }}
                    >
                      🗑 Delete
                    </button>
                  </div>
                </div>
              )}
            </div>
          ))}

          {!showAll && validContacts.length > 6 && (
            <p style={{ textAlign: "center", color: "#aaa", fontSize: "13px" }}>
              +{validContacts.length - 6} more — click "View All"
            </p>
          )}
        </div>
      )}
    </div>
  );
}

export default ContactList;

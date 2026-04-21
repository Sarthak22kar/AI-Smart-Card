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
  services: string;
  extraction_confidence?: number;
  created_at?: string;
}

const FIELDS: { key: keyof Contact; label: string; icon: string; multiline?: boolean }[] = [
  { key: "name",        label: "Name",        icon: "👤" },
  { key: "phone",       label: "Phone",       icon: "📞" },
  { key: "email",       label: "Email",       icon: "📧" },
  { key: "designation", label: "Designation", icon: "💼" },
  { key: "company",     label: "Company",     icon: "🏢" },
  { key: "website",     label: "Website",     icon: "🌐" },
  { key: "gstin",       label: "GSTIN",       icon: "🧾" },
  { key: "services",    label: "Services / Domain", icon: "🛠️" },
  { key: "address",     label: "Address",     icon: "📍", multiline: true },
];

interface Props {
  refreshTrigger: number;
}

// ── Edit Modal ────────────────────────────────────────────────────────────────
function EditModal({
  contact,
  onClose,
  onSaved,
}: {
  contact: Contact;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [form, setForm]     = useState<Contact>({ ...contact });
  const [saving, setSaving] = useState(false);
  const [error,  setError]  = useState("");

  const handleSave = async () => {
    setSaving(true);
    setError("");
    try {
      const res = await fetch(`http://127.0.0.1:8000/contacts/${contact.id}`, {
        method:  "PUT",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify(form),
      });
      if (res.ok) {
        onSaved();
        onClose();
      } else {
        const d = await res.json();
        setError(d.detail || "Save failed");
      }
    } catch {
      setError("Network error");
    } finally {
      setSaving(false);
    }
  };

  return (
    /* Backdrop */
    <div
      onClick={onClose}
      style={{
        position: "fixed", inset: 0, backgroundColor: "rgba(0,0,0,0.5)",
        zIndex: 1000, display: "flex", alignItems: "center", justifyContent: "center",
        padding: "16px",
      }}
    >
      {/* Modal box */}
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          backgroundColor: "white", borderRadius: "14px", width: "100%",
          maxWidth: "560px", maxHeight: "90vh", overflow: "auto",
          boxShadow: "0 20px 60px rgba(0,0,0,0.3)",
        }}
      >
        {/* Header */}
        <div style={{
          padding: "18px 20px", borderBottom: "1px solid #eee",
          display: "flex", justifyContent: "space-between", alignItems: "center",
          position: "sticky", top: 0, backgroundColor: "white", zIndex: 1,
        }}>
          <h3 style={{ margin: 0, color: "#007bff", fontSize: "1.1rem" }}>
            ✏️ Edit Contact
          </h3>
          <button onClick={onClose} style={{
            background: "none", border: "none", fontSize: "20px",
            cursor: "pointer", color: "#888", lineHeight: 1,
          }}>✕</button>
        </div>

        {/* Fields */}
        <div style={{ padding: "20px", display: "flex", flexDirection: "column", gap: "14px" }}>
          {FIELDS.map(({ key, label, icon, multiline }) => (
            <div key={key}>
              <label style={{ fontSize: "12px", color: "#888", textTransform: "uppercase", display: "block", marginBottom: "4px" }}>
                {icon} {label}
              </label>
              {multiline ? (
                <textarea
                  value={(form[key] as string) || ""}
                  onChange={(e) => setForm({ ...form, [key]: e.target.value })}
                  rows={3}
                  style={{
                    width: "100%", padding: "8px 10px", borderRadius: "6px",
                    border: "1px solid #ddd", fontSize: "14px", fontFamily: "inherit",
                    resize: "vertical", boxSizing: "border-box",
                  }}
                />
              ) : (
                <input
                  type="text"
                  value={(form[key] as string) || ""}
                  onChange={(e) => setForm({ ...form, [key]: e.target.value })}
                  placeholder={`Enter ${label.toLowerCase()}...`}
                  style={{
                    width: "100%", padding: "8px 10px", borderRadius: "6px",
                    border: "1px solid #ddd", fontSize: "14px",
                    boxSizing: "border-box",
                  }}
                />
              )}
            </div>
          ))}

          {error && (
            <div style={{ color: "#dc3545", fontSize: "13px", padding: "8px", backgroundColor: "#f8d7da", borderRadius: "6px" }}>
              ❌ {error}
            </div>
          )}
        </div>

        {/* Footer */}
        <div style={{
          padding: "14px 20px", borderTop: "1px solid #eee",
          display: "flex", gap: "10px", justifyContent: "flex-end",
          position: "sticky", bottom: 0, backgroundColor: "white",
        }}>
          <button onClick={onClose} style={{
            padding: "8px 18px", borderRadius: "8px", border: "1px solid #ddd",
            backgroundColor: "white", cursor: "pointer", fontSize: "14px",
          }}>
            Cancel
          </button>
          <button onClick={handleSave} disabled={saving} style={{
            padding: "8px 20px", borderRadius: "8px", border: "none",
            backgroundColor: saving ? "#ccc" : "#007bff",
            color: "white", cursor: saving ? "not-allowed" : "pointer",
            fontSize: "14px", fontWeight: 700,
          }}>
            {saving ? "Saving..." : "💾 Save Changes"}
          </button>
        </div>
      </div>
    </div>
  );
}


// ── Main ContactList ──────────────────────────────────────────────────────────
function ContactList({ refreshTrigger }: Props) {
  const [contacts,   setContacts]   = useState<Contact[]>([]);
  const [loading,    setLoading]    = useState(false);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [showAll,    setShowAll]    = useState(false);
  const [editContact, setEditContact] = useState<Contact | null>(null);
  const [search,     setSearch]     = useState("");

  useEffect(() => { fetchContacts(); }, [refreshTrigger]);

  const fetchContacts = async () => {
    setLoading(true);
    try {
      const res  = await fetch("http://127.0.0.1:8000/contacts/");
      const data = await res.json();
      setContacts(data.contacts || []);
    } catch (e) {
      console.error("Failed to fetch contacts", e);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id: number, name: string) => {
    if (!confirm(`Delete "${name}"? This cannot be undone.`)) return;
    await fetch(`http://127.0.0.1:8000/contacts/${id}`, { method: "DELETE" });
    fetchContacts();
    if (expandedId === id) setExpandedId(null);
  };

  const confidenceColor = (v?: number) => {
    if (!v) return "#dc3545";
    if (v > 0.7) return "#28a745";
    if (v > 0.4) return "#ffc107";
    return "#dc3545";
  };

  // Filter
  const valid = contacts.filter(c =>
    c.name && c.name.trim() !== "" &&
    c.name.toLowerCase() !== "unknown" &&
    !c.name.toLowerCase().startsWith("error")
  );

  const filtered = search.trim()
    ? valid.filter(c =>
        [c.name, c.phone, c.email, c.company, c.designation, c.services]
          .some(f => f?.toLowerCase().includes(search.toLowerCase()))
      )
    : valid;

  const displayed = showAll ? filtered : filtered.slice(0, 6);

  return (
    <div style={{ marginTop: "30px", width: "100%", maxWidth: "680px", margin: "30px auto 0" }}>

      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
        <h2 style={{ margin: 0, fontSize: "1.3rem", color: "#1a1a2e" }}>
          📇 My Contacts
          <span style={{ fontSize: "0.9rem", color: "#888", fontWeight: 400, marginLeft: "6px" }}>
            ({filtered.length})
          </span>
        </h2>
        {valid.length > 6 && (
          <button onClick={() => setShowAll(!showAll)} style={{
            padding: "6px 14px", backgroundColor: "#007bff", color: "white",
            border: "none", borderRadius: "6px", cursor: "pointer", fontSize: "13px",
          }}>
            {showAll ? "Show Less" : `View All (${valid.length})`}
          </button>
        )}
      </div>

      {/* Search */}
      <input
        type="text"
        placeholder="🔍 Search by name, company, phone, services..."
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        style={{
          width: "100%", padding: "10px 14px", borderRadius: "8px",
          border: "1px solid #ddd", fontSize: "14px", marginBottom: "14px",
          boxSizing: "border-box",
        }}
      />

      {loading ? (
        <p style={{ color: "#888", textAlign: "center" }}>Loading contacts...</p>
      ) : filtered.length === 0 ? (
        <div style={{ padding: "30px", textAlign: "center", border: "2px dashed #ddd", borderRadius: "12px", color: "#aaa" }}>
          <p style={{ fontSize: "2rem", margin: "0 0 8px" }}>📭</p>
          <p>{search ? "No contacts match your search." : "No contacts yet. Scan a visiting card to get started!"}</p>
        </div>
      ) : (
        <div>
          {displayed.map(contact => (
            <div key={contact.id} style={{
              border: "1px solid #e0e0e0", borderRadius: "10px",
              marginBottom: "10px", overflow: "hidden",
              backgroundColor: "white", boxShadow: "0 1px 4px rgba(0,0,0,0.06)",
            }}>
              {/* ── Collapsed row ── */}
              <div
                onClick={() => setExpandedId(expandedId === contact.id ? null : contact.id)}
                style={{
                  display: "flex", justifyContent: "space-between", alignItems: "center",
                  padding: "14px 16px", cursor: "pointer",
                  backgroundColor: expandedId === contact.id ? "#f0f7ff" : "white",
                }}
              >
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontWeight: 600, fontSize: "1rem", color: "#1a1a2e" }}>
                    👤 {contact.name}
                  </div>
                  <div style={{ fontSize: "0.85rem", color: "#555", marginTop: "2px" }}>
                    {contact.company && <span>🏢 {contact.company}</span>}
                    {contact.company && contact.phone && <span style={{ margin: "0 6px", color: "#ccc" }}>|</span>}
                    {contact.phone && <span>📞 {contact.phone}</span>}
                  </div>
                  {contact.services && (
                    <div style={{ fontSize: "0.8rem", color: "#007bff", marginTop: "2px" }}>
                      🛠️ {contact.services}
                    </div>
                  )}
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: "8px", flexShrink: 0 }}>
                  {contact.extraction_confidence !== undefined && (
                    <span style={{
                      backgroundColor: confidenceColor(contact.extraction_confidence),
                      color: "white", padding: "2px 7px", borderRadius: "10px", fontSize: "11px",
                    }}>
                      {Math.round((contact.extraction_confidence || 0) * 100)}%
                    </span>
                  )}
                  <span style={{ color: "#aaa", fontSize: "13px" }}>
                    {expandedId === contact.id ? "▲" : "▼"}
                  </span>
                </div>
              </div>

              {/* ── Expanded details ── */}
              {expandedId === contact.id && (
                <div style={{ padding: "14px 16px", borderTop: "1px solid #eee", backgroundColor: "#fafafa", fontSize: "14px" }}>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}>
                    {contact.email && (
                      <div>
                        <div style={{ color: "#888", fontSize: "11px", marginBottom: "2px" }}>📧 EMAIL</div>
                        <a href={`mailto:${contact.email}`} style={{ color: "#007bff", wordBreak: "break-all" }}>{contact.email}</a>
                      </div>
                    )}
                    {contact.designation && (
                      <div>
                        <div style={{ color: "#888", fontSize: "11px", marginBottom: "2px" }}>💼 DESIGNATION</div>
                        <strong>{contact.designation}</strong>
                      </div>
                    )}
                    {contact.website && (
                      <div>
                        <div style={{ color: "#888", fontSize: "11px", marginBottom: "2px" }}>🌐 WEBSITE</div>
                        <a href={contact.website.startsWith('http') ? contact.website : `https://${contact.website}`}
                          target="_blank" rel="noreferrer" style={{ color: "#007bff", wordBreak: "break-all" }}>
                          {contact.website}
                        </a>
                      </div>
                    )}
                    {contact.gstin && (
                      <div>
                        <div style={{ color: "#888", fontSize: "11px", marginBottom: "2px" }}>🧾 GSTIN</div>
                        <code style={{ fontSize: "12px" }}>{contact.gstin}</code>
                      </div>
                    )}
                    {contact.services && (
                      <div style={{ gridColumn: "1 / -1" }}>
                        <div style={{ color: "#888", fontSize: "11px", marginBottom: "2px" }}>🛠️ SERVICES / DOMAIN</div>
                        <div style={{ color: "#1a1a2e" }}>{contact.services}</div>
                      </div>
                    )}
                    {contact.address && (
                      <div style={{ gridColumn: "1 / -1" }}>
                        <div style={{ color: "#888", fontSize: "11px", marginBottom: "2px" }}>📍 ADDRESS</div>
                        <div>{contact.address}</div>
                      </div>
                    )}
                  </div>

                  {/* Action buttons */}
                  <div style={{ marginTop: "14px", display: "flex", gap: "8px", justifyContent: "flex-end" }}>
                    <button
                      onClick={() => setEditContact(contact)}
                      style={{
                        padding: "6px 14px", backgroundColor: "#007bff", color: "white",
                        border: "none", borderRadius: "6px", cursor: "pointer", fontSize: "13px",
                      }}
                    >
                      ✏️ Edit
                    </button>
                    <button
                      onClick={() => handleDelete(contact.id, contact.name)}
                      style={{
                        padding: "6px 14px", backgroundColor: "#dc3545", color: "white",
                        border: "none", borderRadius: "6px", cursor: "pointer", fontSize: "13px",
                      }}
                    >
                      🗑 Delete
                    </button>
                  </div>
                </div>
              )}
            </div>
          ))}

          {!showAll && filtered.length > 6 && (
            <p style={{ textAlign: "center", color: "#aaa", fontSize: "13px" }}>
              +{filtered.length - 6} more — click "View All"
            </p>
          )}
        </div>
      )}

      {/* Edit Modal */}
      {editContact && (
        <EditModal
          contact={editContact}
          onClose={() => setEditContact(null)}
          onSaved={() => { fetchContacts(); setEditContact(null); }}
        />
      )}
    </div>
  );
}

export default ContactList;

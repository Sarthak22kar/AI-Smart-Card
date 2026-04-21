import { useState } from "react";

interface ExtractedContact {
  name: string;
  phone: string;
  email: string;
  designation: string;
  company: string;
  address: string;
  website: string;
  gstin: string;
}

interface ScanImages {
  before_front: string;
  before_back:  string;
  after_front:  string;
  after_back:   string;
}

interface ScanResult {
  status: string;
  message: string;
  contact_id?: number;
  contact_info?: ExtractedContact;
  images?: ScanImages;
  ocr_engine?: string;
  processing_time?: { ocr: number; validation: number; database: number; total: number };
  raw_front?: string;
  raw_back?: string;
  existing_contact?: { id: number; name: string; phone: string; email: string };
  extracted_contact?: ExtractedContact;
  validation?: { is_valid: boolean; errors: Record<string, string>; warnings: Record<string, string> };
}

interface Props {
  onScanSuccess: () => void;
}

const FIELD_ICONS: Record<string, string> = {
  name: "👤", phone: "📞", email: "📧", designation: "💼",
  company: "🏢", address: "📍", website: "🌐", gstin: "🧾",
};

const FIELD_LABELS: Record<string, string> = {
  name: "Name", phone: "Phone", email: "Email", designation: "Designation",
  company: "Company", address: "Address", website: "Website", gstin: "GSTIN",
};

// ── Image comparison panel ────────────────────────────────────────────────────
function ImageComparison({ images, side }: { images: ScanImages; side: "front" | "back" }) {
  const [showAfter, setShowAfter] = useState(true);
  const before  = side === "front" ? images.before_front : images.before_back;
  const after   = side === "front" ? images.after_front  : images.after_back;
  const label   = side === "front" ? "Front" : "Back";
  const hasAfter = !!after;

  return (
    <div style={{ flex: 1, minWidth: 0 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "8px" }}>
        <span style={{ fontWeight: 700, fontSize: "13px", color: "#444" }}>📄 {label} Side</span>
        {hasAfter && (
          <div style={{ display: "flex", borderRadius: "6px", overflow: "hidden", border: "1px solid #007bff" }}>
            {["Before", "After"].map((label) => (
              <button key={label}
                onClick={() => setShowAfter(label === "After")}
                style={{
                  padding: "3px 10px", fontSize: "11px", border: "none",
                  backgroundColor: (label === "After") === showAfter ? "#007bff" : "white",
                  color: (label === "After") === showAfter ? "white" : "#007bff",
                  cursor: "pointer", fontWeight: 600,
                }}
              >{label}</button>
            ))}
          </div>
        )}
      </div>
      <div style={{ position: "relative" }}>
        <img
          src={showAfter && hasAfter ? after : before}
          alt={`${label} ${showAfter ? "preprocessed" : "original"}`}
          style={{
            width: "100%", borderRadius: "8px",
            border: `2px solid ${showAfter ? "#28a745" : "#6c757d"}`,
            display: "block", objectFit: "contain",
            maxHeight: "220px", backgroundColor: "#f0f0f0",
          }}
        />
        <span style={{
          position: "absolute", top: "6px", left: "6px",
          backgroundColor: showAfter ? "#28a745" : "#6c757d",
          color: "white", fontSize: "10px", fontWeight: 700,
          padding: "2px 7px", borderRadius: "10px",
        }}>
          {showAfter ? "✨ Preprocessed" : "📷 Original"}
        </span>
      </div>
      <p style={{ fontSize: "11px", color: "#888", textAlign: "center", margin: "5px 0 0" }}>
        {showAfter ? "CLAHE contrast + sharpened for OCR" : "Original uploaded image"}
      </p>
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────
function UploadCard({ onScanSuccess }: Props) {
  const [frontFile,   setFrontFile]   = useState<File | null>(null);
  const [backFile,    setBackFile]    = useState<File | null>(null);
  const [loading,     setLoading]     = useState(false);
  const [result,      setResult]      = useState<ScanResult | null>(null);
  const [activeTab,   setActiveTab]   = useState<"upload" | "extraction">("upload");

  // Editable fields state
  const [editedFields, setEditedFields] = useState<ExtractedContact | null>(null);
  const [saving,        setSaving]       = useState(false);
  const [saveMsg,       setSaveMsg]      = useState<{ type: "success" | "error"; text: string } | null>(null);
  const [hasEdits,      setHasEdits]     = useState(false);

  // ── When scan succeeds, initialise editable fields ──────────────────────────
  const initEdits = (info: ExtractedContact) => {
    setEditedFields({ ...info });
    setHasEdits(false);
    setSaveMsg(null);
  };

  const handleFieldChange = (key: string, value: string) => {
    setEditedFields(prev => prev ? { ...prev, [key]: value } : prev);
    setHasEdits(true);
    setSaveMsg(null);
  };

  // ── Save edited fields to database ─────────────────────────────────────────
  const saveEdits = async () => {
    if (!result?.contact_id || !editedFields) return;
    setSaving(true);
    setSaveMsg(null);
    try {
      const res = await fetch(`http://127.0.0.1:8000/contacts/${result.contact_id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(editedFields),
      });
      if (res.ok) {
        setSaveMsg({ type: "success", text: "✅ Changes saved successfully!" });
        setHasEdits(false);
        // Update the result so status bar reflects new name
        setResult(prev => prev ? { ...prev, contact_info: { ...editedFields } } : prev);
        onScanSuccess(); // refresh contact list
      } else {
        const err = await res.json();
        setSaveMsg({ type: "error", text: `❌ Save failed: ${err.detail || "Unknown error"}` });
      }
    } catch (e) {
      setSaveMsg({ type: "error", text: "❌ Network error — could not save" });
    } finally {
      setSaving(false);
    }
  };

  const resetEdits = () => {
    if (result?.contact_info) {
      setEditedFields({ ...result.contact_info });
      setHasEdits(false);
      setSaveMsg(null);
    }
  };

  // ── Upload handler ──────────────────────────────────────────────────────────
  const uploadCard = async () => {
    if (!frontFile || !backFile) {
      alert("Please select both front and back card images");
      return;
    }
    setLoading(true);
    setResult(null);
    setEditedFields(null);
    setHasEdits(false);
    setSaveMsg(null);

    try {
      const [frontCompressed, backCompressed] = await Promise.all([
        compressImage(frontFile),
        compressImage(backFile),
      ]);
      const formData = new FormData();
      formData.append("front_file", frontCompressed);
      formData.append("back_file",  backCompressed);

      const res  = await fetch("http://127.0.0.1:8000/scan-card/", { method: "POST", body: formData });
      const data: ScanResult = await res.json();
      setResult(data);

      if (data.status === "success" && data.contact_info) {
        setActiveTab("extraction");
        initEdits(data.contact_info);
        onScanSuccess();
      }
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      setResult({ status: "error", message: `Network error: ${msg}. Make sure backend is running on http://127.0.0.1:8000` });
    } finally {
      setLoading(false);
      setFrontFile(null);
      setBackFile(null);
      document.querySelectorAll<HTMLInputElement>('input[type="file"]').forEach(i => (i.value = ""));
    }
  };

  // ── Image compression ───────────────────────────────────────────────────────
  const compressImage = async (file: File): Promise<File> => {
    return new Promise((resolve) => {
      if (file.type === "image/heic" || file.type === "image/heif" ||
          file.name.toLowerCase().endsWith(".heic") || file.name.toLowerCase().endsWith(".heif")) {
        resolve(file); return;
      }
      const reader = new FileReader();
      reader.onload = (e) => {
        const img = new window.Image();
        img.onload = () => {
          const canvas = document.createElement("canvas");
          let w = img.width, h = img.height;
          if (w > 800) { h = (h * 800) / w; w = 800; }
          canvas.width = w; canvas.height = h;
          canvas.getContext("2d")?.drawImage(img, 0, 0, w, h);
          canvas.toBlob(
            (blob) => resolve(blob ? new File([blob], file.name.replace(/\.\w+$/, ".jpg"), { type: "image/jpeg" }) : file),
            "image/jpeg", 0.85
          );
        };
        img.onerror = () => resolve(file);
        img.src = e.target?.result as string;
      };
      reader.onerror = () => resolve(file);
      reader.readAsDataURL(file);
    });
  };

  const tabStyle = (tab: "upload" | "extraction") => ({
    padding: "10px 24px", border: "none",
    borderBottom: activeTab === tab ? "3px solid #007bff" : "3px solid transparent",
    backgroundColor: "transparent",
    color: activeTab === tab ? "#007bff" : "#666",
    fontWeight: activeTab === tab ? 700 : 400,
    cursor: "pointer", fontSize: "15px",
  });

  return (
    <div style={{ border: "2px solid #007bff", borderRadius: "14px", backgroundColor: "#f8f9ff", overflow: "hidden" }}>

      {/* Tabs */}
      <div style={{ display: "flex", borderBottom: "1px solid #ddd", backgroundColor: "white" }}>
        <button style={tabStyle("upload")} onClick={() => setActiveTab("upload")}>📷 Scan Card</button>
        <button style={tabStyle("extraction")} onClick={() => setActiveTab("extraction")}>
          🔍 Extraction Details
          {result?.status === "success" && (
            <span style={{ marginLeft: "6px", backgroundColor: "#28a745", color: "white", borderRadius: "10px", padding: "1px 6px", fontSize: "11px" }}>✓</span>
          )}
          {hasEdits && (
            <span style={{ marginLeft: "6px", backgroundColor: "#fd7e14", color: "white", borderRadius: "10px", padding: "1px 6px", fontSize: "11px" }}>edited</span>
          )}
        </button>
      </div>

      {/* ══ UPLOAD TAB ══ */}
      {activeTab === "upload" && (
        <div style={{ padding: "24px" }}>
          <h2 style={{ color: "#007bff", marginTop: 0 }}>📷 Scan Visiting Card</h2>

          <div style={{ display: "flex", gap: "30px", justifyContent: "center", flexWrap: "wrap", marginBottom: "20px" }}>
            {(["Front", "Back"] as const).map((side) => {
              const file    = side === "Front" ? frontFile : backFile;
              const setFile = side === "Front" ? setFrontFile : setBackFile;
              return (
                <div key={side} style={{ textAlign: "center" }}>
                  <h3 style={{ color: "#333", marginBottom: "8px" }}>📄 {side} Side</h3>
                  <input type="file" accept="image/*,.heic,.heif,.webp,.tiff,.tif,.bmp"
                    onChange={(e) => setFile(e.target.files?.[0] || null)}
                    style={{ padding: "8px", border: "1px solid #ddd", borderRadius: "5px", backgroundColor: "white" }}
                  />
                  {file && <p style={{ fontSize: "12px", color: "#28a745", marginTop: "5px" }}>✅ {file.name}</p>}
                </div>
              );
            })}
          </div>

          <div style={{ textAlign: "center", marginBottom: "18px", padding: "10px", backgroundColor: "#e3f2fd", borderRadius: "8px", fontSize: "12px", color: "#1565c0" }}>
            <strong>📸 Supported:</strong> JPG, PNG, HEIC, HEIF, WebP, TIFF, BMP &nbsp;|&nbsp;
            <strong>⚡ Tip:</strong> Clear, well-lit images give best results
          </div>

          <div style={{ textAlign: "center" }}>
            <button onClick={uploadCard} disabled={loading || !frontFile || !backFile}
              style={{
                padding: "14px 32px", fontSize: "17px", fontWeight: "bold",
                backgroundColor: loading || !frontFile || !backFile ? "#ccc" : "#28a745",
                color: "white", border: "none", borderRadius: "10px",
                cursor: loading || !frontFile || !backFile ? "not-allowed" : "pointer",
              }}>
              {loading ? "🔄 Scanning..." : "🚀 Scan Card"}
            </button>
            {loading && (
              <div style={{ marginTop: "12px", fontSize: "13px", color: "#666" }}>
                <div style={{ width: "200px", height: "4px", backgroundColor: "#e0e0e0", borderRadius: "2px", margin: "8px auto", overflow: "hidden" }}>
                  <div style={{ width: "60%", height: "100%", backgroundColor: "#007bff", borderRadius: "2px" }} />
                </div>
                Processing images with AI...
              </div>
            )}
          </div>

          {result && result.status !== "success" && (
            <div style={{
              marginTop: "18px", padding: "14px", borderRadius: "8px",
              backgroundColor: result.status === "duplicate" ? "#fff3cd" : "#f8d7da",
              border: `1px solid ${result.status === "duplicate" ? "#ffc107" : "#f5c6cb"}`,
              color: result.status === "duplicate" ? "#856404" : "#721c24",
            }}>
              <strong>{result.status === "duplicate" ? "⚠️ Duplicate" : "❌ Error"}:</strong> {result.message}
              {result.status === "duplicate" && result.existing_contact && (
                <p style={{ margin: "6px 0 0" }}>Existing: <strong>{result.existing_contact.name}</strong> — {result.existing_contact.phone}</p>
              )}
            </div>
          )}
          {result?.status === "success" && (
            <div style={{ marginTop: "18px", padding: "14px", borderRadius: "8px", backgroundColor: "#d4edda", border: "1px solid #c3e6cb", color: "#155724" }}>
              ✅ <strong>{result.contact_info?.name}</strong> saved! (Total: {result.processing_time?.total}s)
              &nbsp;→&nbsp;
              <button onClick={() => setActiveTab("extraction")} style={{ background: "none", border: "none", color: "#007bff", cursor: "pointer", textDecoration: "underline", fontSize: "14px" }}>
                View &amp; edit extraction details
              </button>
            </div>
          )}
        </div>
      )}

      {/* ══ EXTRACTION DETAILS TAB ══ */}
      {activeTab === "extraction" && (
        <div style={{ padding: "24px" }}>
          <h2 style={{ color: "#007bff", marginTop: 0 }}>🔍 Extraction Details</h2>

          {!result ? (
            <div style={{ textAlign: "center", color: "#aaa", padding: "30px" }}>
              <p style={{ fontSize: "2rem" }}>📋</p>
              <p>Scan a card first to see extraction results here.</p>
            </div>

          ) : result.status === "success" && result.contact_info && editedFields ? (
            <>
              {/* Status bar */}
              <div style={{
                display: "flex", gap: "12px", marginBottom: "20px",
                padding: "10px 14px", backgroundColor: "#d4edda",
                borderRadius: "8px", fontSize: "13px", color: "#155724",
                flexWrap: "wrap", alignItems: "center",
              }}>
                <span>✅ Saved as ID #{result.contact_id}</span>
                <span>⏱ OCR: {result.processing_time?.ocr}s</span>
                <span>⚡ Total: {result.processing_time?.total}s</span>
                {result.ocr_engine && (
                  <span style={{ marginLeft: "auto", backgroundColor: "#007bff", color: "white", padding: "2px 8px", borderRadius: "10px", fontSize: "11px" }}>
                    🤖 {result.ocr_engine}
                  </span>
                )}
              </div>

              {/* Image preview */}
              {result.images && (result.images.before_front || result.images.before_back) && (
                <div style={{ marginBottom: "24px" }}>
                  <h3 style={{ fontSize: "14px", color: "#555", marginBottom: "12px", display: "flex", alignItems: "center", gap: "8px" }}>
                    🖼️ Image Preview
                    <span style={{ fontSize: "11px", color: "#888", fontWeight: 400 }}>— toggle Before / After</span>
                  </h3>
                  <div style={{ display: "flex", gap: "16px", flexWrap: "wrap" }}>
                    {result.images.before_front && <ImageComparison images={result.images} side="front" />}
                    {result.images.before_back  && <ImageComparison images={result.images} side="back" />}
                  </div>
                </div>
              )}

              {/* ── Editable fields ── */}
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "12px", flexWrap: "wrap", gap: "8px" }}>
                <h3 style={{ fontSize: "14px", color: "#555", margin: 0 }}>
                  📋 Extracted Fields
                  <span style={{ fontSize: "11px", color: "#888", fontWeight: 400, marginLeft: "8px" }}>
                    — click any field to edit
                  </span>
                </h3>
                {hasEdits && (
                  <div style={{ display: "flex", gap: "8px" }}>
                    <button onClick={resetEdits}
                      style={{
                        padding: "6px 14px", fontSize: "13px", borderRadius: "6px",
                        border: "1px solid #6c757d", backgroundColor: "white",
                        color: "#6c757d", cursor: "pointer",
                      }}>
                      ↩ Reset
                    </button>
                    <button onClick={saveEdits} disabled={saving}
                      style={{
                        padding: "6px 16px", fontSize: "13px", fontWeight: 700,
                        borderRadius: "6px", border: "none",
                        backgroundColor: saving ? "#ccc" : "#007bff",
                        color: "white", cursor: saving ? "not-allowed" : "pointer",
                      }}>
                      {saving ? "Saving..." : "💾 Save Changes"}
                    </button>
                  </div>
                )}
              </div>

              {/* Save message */}
              {saveMsg && (
                <div style={{
                  marginBottom: "12px", padding: "10px 14px", borderRadius: "8px", fontSize: "13px",
                  backgroundColor: saveMsg.type === "success" ? "#d4edda" : "#f8d7da",
                  color: saveMsg.type === "success" ? "#155724" : "#721c24",
                  border: `1px solid ${saveMsg.type === "success" ? "#c3e6cb" : "#f5c6cb"}`,
                }}>
                  {saveMsg.text}
                </div>
              )}

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                {(Object.keys(editedFields) as (keyof ExtractedContact)[]).map((key) => {
                  const value    = editedFields[key];
                  const original = result.contact_info![key];
                  const changed  = value !== original;
                  const isLong   = ["address", "gstin"].includes(key);

                  return (
                    <div key={key} style={{
                      padding: "12px", backgroundColor: "white", borderRadius: "8px",
                      border: `1.5px solid ${changed ? "#fd7e14" : value ? "#c3e6cb" : "#f5c6cb"}`,
                      gridColumn: isLong ? "1 / -1" : "auto",
                      transition: "border-color 0.2s",
                    }}>
                      {/* Field label */}
                      <div style={{
                        fontSize: "11px", color: changed ? "#fd7e14" : "#888",
                        marginBottom: "6px", textTransform: "uppercase",
                        display: "flex", justifyContent: "space-between", alignItems: "center",
                      }}>
                        <span>{FIELD_ICONS[key] || "•"} {FIELD_LABELS[key]}</span>
                        {changed && (
                          <span style={{ fontSize: "10px", color: "#fd7e14", fontWeight: 600 }}>
                            ✏️ edited
                          </span>
                        )}
                      </div>

                      {/* Editable input */}
                      {isLong ? (
                        <textarea
                          value={value}
                          onChange={(e) => handleFieldChange(key, e.target.value)}
                          rows={2}
                          placeholder={`Enter ${FIELD_LABELS[key].toLowerCase()}...`}
                          style={{
                            width: "100%", border: "none", outline: "none",
                            fontSize: "0.95rem", fontWeight: 600,
                            color: value ? "#1a1a2e" : "#999",
                            backgroundColor: "transparent", resize: "vertical",
                            fontFamily: "inherit", padding: 0,
                            boxSizing: "border-box",
                          }}
                        />
                      ) : (
                        <input
                          type="text"
                          value={value}
                          onChange={(e) => handleFieldChange(key, e.target.value)}
                          placeholder={`Enter ${FIELD_LABELS[key].toLowerCase()}...`}
                          style={{
                            width: "100%", border: "none", outline: "none",
                            fontSize: key === "name" ? "1.1rem" : "0.95rem",
                            fontWeight: 600,
                            color: value ? "#1a1a2e" : "#999",
                            backgroundColor: "transparent",
                            fontFamily: "inherit", padding: 0,
                            boxSizing: "border-box",
                          }}
                        />
                      )}
                    </div>
                  );
                })}
              </div>

              {/* Save button at bottom when edits exist */}
              {hasEdits && (
                <div style={{ marginTop: "16px", display: "flex", gap: "8px", justifyContent: "flex-end" }}>
                  <button onClick={resetEdits}
                    style={{ padding: "8px 18px", fontSize: "14px", borderRadius: "8px", border: "1px solid #6c757d", backgroundColor: "white", color: "#6c757d", cursor: "pointer" }}>
                    ↩ Reset
                  </button>
                  <button onClick={saveEdits} disabled={saving}
                    style={{
                      padding: "8px 20px", fontSize: "14px", fontWeight: 700,
                      borderRadius: "8px", border: "none",
                      backgroundColor: saving ? "#ccc" : "#007bff",
                      color: "white", cursor: saving ? "not-allowed" : "pointer",
                    }}>
                    {saving ? "Saving..." : "💾 Save Changes"}
                  </button>
                </div>
              )}

              {/* Validation warnings */}
              {result.validation?.warnings && Object.keys(result.validation.warnings).length > 0 && (
                <details style={{ marginTop: "16px" }}>
                  <summary style={{ cursor: "pointer", color: "#856404", fontSize: "13px" }}>
                    ⚠️ {Object.keys(result.validation.warnings).length} auto-corrections applied
                  </summary>
                  <div style={{ marginTop: "8px", padding: "10px", backgroundColor: "#fff3cd", borderRadius: "6px", fontSize: "12px" }}>
                    {Object.entries(result.validation.warnings).map(([field, msg]) => (
                      <div key={field} style={{ marginBottom: "4px" }}><strong>{field}:</strong> {msg}</div>
                    ))}
                  </div>
                </details>
              )}
            </>

          ) : (
            <div style={{
              padding: "16px", borderRadius: "8px",
              backgroundColor: result.status === "duplicate" ? "#fff3cd" : "#f8d7da",
              color: result.status === "duplicate" ? "#856404" : "#721c24",
            }}>
              <strong>{result.status === "duplicate" ? "⚠️ Duplicate detected" : "❌ Extraction failed"}</strong>
              <p>{result.message}</p>
              {result.extracted_contact && (
                <>
                  <p style={{ fontWeight: 600 }}>What was extracted:</p>
                  {(Object.entries(result.extracted_contact) as [string, string][]).map(([k, v]) =>
                    v ? <p key={k} style={{ margin: "3px 0" }}>{FIELD_ICONS[k] || "•"} <strong>{k}:</strong> {v}</p> : null
                  )}
                </>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default UploadCard;

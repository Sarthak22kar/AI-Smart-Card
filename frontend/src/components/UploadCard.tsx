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

// ── Image comparison panel ────────────────────────────────────────────────────
function ImageComparison({ images, side }: { images: ScanImages; side: "front" | "back" }) {
  const [showAfter, setShowAfter] = useState(true);
  const before = side === "front" ? images.before_front : images.before_back;
  const after  = side === "front" ? images.after_front  : images.after_back;
  const label  = side === "front" ? "Front" : "Back";

  // If no after image (shouldn't happen but guard anyway)
  const hasAfter = !!after;

  return (
    <div style={{ flex: 1, minWidth: 0 }}>
      {/* Header with toggle */}
      <div style={{
        display: "flex", alignItems: "center", justifyContent: "space-between",
        marginBottom: "8px",
      }}>
        <span style={{ fontWeight: 700, fontSize: "13px", color: "#444" }}>
          📄 {label} Side
        </span>
        {hasAfter && (
          <div style={{
            display: "flex", gap: "0", borderRadius: "6px",
            overflow: "hidden", border: "1px solid #007bff",
          }}>
            <button
              onClick={() => setShowAfter(false)}
              style={{
                padding: "3px 10px", fontSize: "11px", border: "none",
                backgroundColor: !showAfter ? "#007bff" : "white",
                color: !showAfter ? "white" : "#007bff",
                cursor: "pointer", fontWeight: 600,
              }}
            >
              Before
            </button>
            <button
              onClick={() => setShowAfter(true)}
              style={{
                padding: "3px 10px", fontSize: "11px", border: "none",
                backgroundColor: showAfter ? "#007bff" : "white",
                color: showAfter ? "white" : "#007bff",
                cursor: "pointer", fontWeight: 600,
              }}
            >
              After
            </button>
          </div>
        )}
      </div>

      {/* Image */}
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
        {/* Badge */}
        <span style={{
          position: "absolute", top: "6px", left: "6px",
          backgroundColor: showAfter ? "#28a745" : "#6c757d",
          color: "white", fontSize: "10px", fontWeight: 700,
          padding: "2px 7px", borderRadius: "10px",
        }}>
          {showAfter ? "✨ Preprocessed" : "📷 Original"}
        </span>
      </div>

      {/* Caption */}
      <p style={{
        fontSize: "11px", color: "#888", textAlign: "center",
        margin: "5px 0 0",
      }}>
        {showAfter
          ? "CLAHE contrast + sharpened for OCR"
          : "Original uploaded image"}
      </p>
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────
function UploadCard({ onScanSuccess }: Props) {
  const [frontFile, setFrontFile] = useState<File | null>(null);
  const [backFile,  setBackFile]  = useState<File | null>(null);
  const [loading,   setLoading]   = useState(false);
  const [result,    setResult]    = useState<ScanResult | null>(null);
  const [activeTab, setActiveTab] = useState<"upload" | "extraction">("upload");

  // ── Upload handler ──────────────────────────────────────────────────────────
  const uploadCard = async () => {
    if (!frontFile || !backFile) {
      alert("Please select both front and back card images");
      return;
    }
    setLoading(true);
    setResult(null);

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

      if (data.status === "success") {
        setActiveTab("extraction");
        onScanSuccess();
      }
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      setResult({ status: "error", message: `Network error: ${msg}. Make sure backend is running on http://127.0.0.1:8000` });
    } finally {
      setLoading(false);
      setFrontFile(null);
      setBackFile(null);
      document.querySelectorAll<HTMLInputElement>('input[type="file"]')
        .forEach(i => (i.value = ""));
    }
  };

  // ── Image compression ───────────────────────────────────────────────────────
  const compressImage = async (file: File): Promise<File> => {
    return new Promise((resolve) => {
      if (
        file.type === "image/heic" || file.type === "image/heif" ||
        file.name.toLowerCase().endsWith(".heic") ||
        file.name.toLowerCase().endsWith(".heif")
      ) {
        resolve(file);
        return;
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
            (blob) => resolve(blob
              ? new File([blob], file.name.replace(/\.\w+$/, ".jpg"), { type: "image/jpeg" })
              : file),
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

  // ── Tab style ───────────────────────────────────────────────────────────────
  const tabStyle = (tab: "upload" | "extraction") => ({
    padding: "10px 24px", border: "none",
    borderBottom: activeTab === tab ? "3px solid #007bff" : "3px solid transparent",
    backgroundColor: "transparent",
    color: activeTab === tab ? "#007bff" : "#666",
    fontWeight: activeTab === tab ? 700 : 400,
    cursor: "pointer", fontSize: "15px",
  });

  // ── Render ──────────────────────────────────────────────────────────────────
  return (
    <div style={{
      border: "2px solid #007bff", borderRadius: "14px",
      backgroundColor: "#f8f9ff", overflow: "hidden",
    }}>
      {/* Tabs */}
      <div style={{ display: "flex", borderBottom: "1px solid #ddd", backgroundColor: "white" }}>
        <button style={tabStyle("upload")} onClick={() => setActiveTab("upload")}>
          📷 Scan Card
        </button>
        <button style={tabStyle("extraction")} onClick={() => setActiveTab("extraction")}>
          🔍 Extraction Details
          {result?.status === "success" && (
            <span style={{
              marginLeft: "6px", backgroundColor: "#28a745", color: "white",
              borderRadius: "10px", padding: "1px 6px", fontSize: "11px",
            }}>✓</span>
          )}
        </button>
      </div>

      {/* ══════════════════════════════════════════════════════════════════════
          UPLOAD TAB
      ══════════════════════════════════════════════════════════════════════ */}
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
                  <input
                    type="file"
                    accept="image/*,.heic,.heif,.webp,.tiff,.tif,.bmp"
                    onChange={(e) => setFile(e.target.files?.[0] || null)}
                    style={{ padding: "8px", border: "1px solid #ddd", borderRadius: "5px", backgroundColor: "white" }}
                  />
                  {file && <p style={{ fontSize: "12px", color: "#28a745", marginTop: "5px" }}>✅ {file.name}</p>}
                </div>
              );
            })}
          </div>

          <div style={{
            textAlign: "center", marginBottom: "18px", padding: "10px",
            backgroundColor: "#e3f2fd", borderRadius: "8px", fontSize: "12px", color: "#1565c0",
          }}>
            <strong>📸 Supported:</strong> JPG, PNG, HEIC, HEIF, WebP, TIFF, BMP &nbsp;|&nbsp;
            <strong>⚡ Tip:</strong> Clear, well-lit images give best results
          </div>

          <div style={{ textAlign: "center" }}>
            <button
              onClick={uploadCard}
              disabled={loading || !frontFile || !backFile}
              style={{
                padding: "14px 32px", fontSize: "17px", fontWeight: "bold",
                backgroundColor: loading || !frontFile || !backFile ? "#ccc" : "#28a745",
                color: "white", border: "none", borderRadius: "10px",
                cursor: loading || !frontFile || !backFile ? "not-allowed" : "pointer",
              }}
            >
              {loading ? "🔄 Scanning..." : "🚀 Scan Card"}
            </button>

            {loading && (
              <div style={{ marginTop: "12px", fontSize: "13px", color: "#666" }}>
                <div style={{
                  width: "200px", height: "4px", backgroundColor: "#e0e0e0",
                  borderRadius: "2px", margin: "8px auto", overflow: "hidden",
                }}>
                  <div style={{
                    width: "60%", height: "100%", backgroundColor: "#007bff",
                    borderRadius: "2px", animation: "slide 1.2s ease-in-out infinite",
                  }} />
                </div>
                Processing images with AI...
              </div>
            )}
          </div>

          {/* Inline status */}
          {result && result.status !== "success" && (
            <div style={{
              marginTop: "18px", padding: "14px", borderRadius: "8px",
              backgroundColor: result.status === "duplicate" ? "#fff3cd" : "#f8d7da",
              border: `1px solid ${result.status === "duplicate" ? "#ffc107" : "#f5c6cb"}`,
              color: result.status === "duplicate" ? "#856404" : "#721c24",
            }}>
              <strong>{result.status === "duplicate" ? "⚠️ Duplicate" : "❌ Error"}:</strong> {result.message}
              {result.status === "duplicate" && result.existing_contact && (
                <p style={{ margin: "6px 0 0" }}>
                  Existing: <strong>{result.existing_contact.name}</strong> — {result.existing_contact.phone}
                </p>
              )}
            </div>
          )}
          {result?.status === "success" && (
            <div style={{
              marginTop: "18px", padding: "14px", borderRadius: "8px",
              backgroundColor: "#d4edda", border: "1px solid #c3e6cb", color: "#155724",
            }}>
              ✅ <strong>{result.contact_info?.name}</strong> saved! (Total: {result.processing_time?.total}s)
              &nbsp;→&nbsp;
              <button onClick={() => setActiveTab("extraction")} style={{
                background: "none", border: "none", color: "#007bff",
                cursor: "pointer", textDecoration: "underline", fontSize: "14px",
              }}>
                View extraction details
              </button>
            </div>
          )}
        </div>
      )}

      {/* ══════════════════════════════════════════════════════════════════════
          EXTRACTION DETAILS TAB
      ══════════════════════════════════════════════════════════════════════ */}
      {activeTab === "extraction" && (
        <div style={{ padding: "24px" }}>
          <h2 style={{ color: "#007bff", marginTop: 0 }}>🔍 Extraction Details</h2>

          {!result ? (
            <div style={{ textAlign: "center", color: "#aaa", padding: "30px" }}>
              <p style={{ fontSize: "2rem" }}>📋</p>
              <p>Scan a card first to see extraction results here.</p>
            </div>

          ) : result.status === "success" && result.contact_info ? (
            <>
              {/* ── Status bar ── */}
              <div style={{
                display: "flex", gap: "12px", marginBottom: "20px",
                padding: "10px 14px", backgroundColor: "#d4edda",
                borderRadius: "8px", fontSize: "13px", color: "#155724",
                flexWrap: "wrap", alignItems: "center",
              }}>
                <span>✅ Saved as ID #{result.contact_id}</span>
                <span>⏱ OCR: {result.processing_time?.ocr}s</span>
                <span>💾 DB: {result.processing_time?.database}s</span>
                <span>⚡ Total: {result.processing_time?.total}s</span>
                {result.ocr_engine && (
                  <span style={{
                    marginLeft: "auto", backgroundColor: "#007bff", color: "white",
                    padding: "2px 8px", borderRadius: "10px", fontSize: "11px",
                  }}>
                    🤖 {result.ocr_engine}
                  </span>
                )}
              </div>

              {/* ── Before / After image comparison ── */}
              {result.images && (result.images.before_front || result.images.before_back) && (
                <div style={{ marginBottom: "24px" }}>
                  <h3 style={{
                    fontSize: "14px", color: "#555", marginBottom: "12px",
                    display: "flex", alignItems: "center", gap: "8px",
                  }}>
                    🖼️ Image Preview
                    <span style={{
                      fontSize: "11px", color: "#888", fontWeight: 400,
                    }}>
                      — toggle Before / After to see preprocessing effect
                    </span>
                  </h3>

                  <div style={{ display: "flex", gap: "16px", flexWrap: "wrap" }}>
                    {result.images.before_front && (
                      <ImageComparison images={result.images} side="front" />
                    )}
                    {result.images.before_back && (
                      <ImageComparison images={result.images} side="back" />
                    )}
                  </div>
                </div>
              )}

              {/* ── Extracted fields ── */}
              <h3 style={{ fontSize: "14px", color: "#555", marginBottom: "12px" }}>
                📋 Extracted Fields
              </h3>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                {(Object.entries(result.contact_info) as [string, string][]).map(([key, value]) => (
                  <div key={key} style={{
                    padding: "12px", backgroundColor: "white",
                    borderRadius: "8px",
                    border: `1px solid ${value ? "#c3e6cb" : "#f5c6cb"}`,
                    gridColumn: ["address", "gstin"].includes(key) ? "1 / -1" : "auto",
                  }}>
                    <div style={{
                      fontSize: "11px", color: "#888", marginBottom: "4px",
                      textTransform: "uppercase",
                    }}>
                      {FIELD_ICONS[key] || "•"} {key}
                    </div>
                    <div style={{
                      fontWeight: 600, color: value ? "#1a1a2e" : "#ccc",
                      fontSize: key === "name" ? "1.1rem" : "0.95rem",
                      wordBreak: "break-word",
                    }}>
                      {value || "— not found —"}
                    </div>
                  </div>
                ))}
              </div>

              {/* ── Validation warnings ── */}
              {result.validation?.warnings && Object.keys(result.validation.warnings).length > 0 && (
                <details style={{ marginTop: "16px" }}>
                  <summary style={{ cursor: "pointer", color: "#856404", fontSize: "13px" }}>
                    ⚠️ {Object.keys(result.validation.warnings).length} auto-corrections applied
                  </summary>
                  <div style={{
                    marginTop: "8px", padding: "10px", backgroundColor: "#fff3cd",
                    borderRadius: "6px", fontSize: "12px",
                  }}>
                    {Object.entries(result.validation.warnings).map(([field, msg]) => (
                      <div key={field} style={{ marginBottom: "4px" }}>
                        <strong>{field}:</strong> {msg}
                      </div>
                    ))}
                  </div>
                </details>
              )}
            </>

          ) : (
            /* Error / duplicate state */
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

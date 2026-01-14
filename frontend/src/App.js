import { useState } from "react";

function App() {
  const [policyText, setPolicyText] = useState("");
  const [permissions, setPermissions] = useState([]);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const togglePermission = (perm) => {
    setPermissions((prev) =>
      prev.includes(perm)
        ? prev.filter((p) => p !== perm)
        : [...prev, perm]
    );
  };

  const analyzeConsent = async () => {
    setLoading(true);
    setResult(null);

    const response = await fetch("http://127.0.0.1:8000/analyze-consent", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        app_name: "User Submitted App",
        permissions: permissions,
        policy_text: policyText
      })
    });

    const data = await response.json();
    setResult(data);
    setLoading(false);
  };

  const riskColor = (level) => {
    if (level === "High") return "red";
    if (level === "Medium") return "orange";
    return "green";
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        backgroundColor: "#f7f9fc",
        padding: "40px 20px",
        fontFamily: "Inter, Arial, sans-serif",
        display: "flex",
        justifyContent: "center"
      }}
    >
      <div
        style={{
          width: "100%",
          maxWidth: 900,
          backgroundColor: "#ffffff",
          padding: 32,
          borderRadius: 8,
          boxShadow: "0 4px 12px rgba(0,0,0,0.05)"
        }}
      >
        {/* Header */}
        <h2 style={{ marginBottom: 8 }}>Consent Transparency Engine</h2>
        <p style={{ color: "#555", marginBottom: 24 }}>
          Paste a consent or privacy agreement to understand what you are actually agreeing to.
        </p>

        {/* Input */}
        <label style={{ fontWeight: 600 }}>
          Privacy Policy / Consent Agreement
        </label>
        <textarea
          rows="10"
          style={{
            width: "100%",
            marginTop: 8,
            padding: 12,
            fontSize: 14,
            borderRadius: 6,
            border: "1px solid #ccc",
            resize: "vertical"
          }}
          placeholder="Paste the full agreement text here..."
          value={policyText}
          onChange={(e) => setPolicyText(e.target.value)}
        />

        {/* Button */}
        <button
          onClick={analyzeConsent}
          disabled={!policyText || loading}
          style={{
            marginTop: 16,
            padding: "10px 20px",
            backgroundColor: loading ? "#999" : "#2563eb",
            color: "#fff",
            border: "none",
            borderRadius: 6,
            cursor: loading ? "not-allowed" : "pointer",
            fontSize: 14
          }}
        >
          {loading ? "Analyzing Agreement..." : "Analyze Agreement"}
        </button>

        {/* Result */}
        {result && (
          <div
            style={{
              marginTop: 32,
              padding: 24,
              borderRadius: 8,
              border: "1px solid #e5e7eb",
              backgroundColor: "#fafafa"
            }}
          >
            <h3 style={{ marginBottom: 12 }}>{result.app}</h3>

            <div style={{ marginBottom: 16 }}>
              <strong>Plain-English Summary</strong>
              <p style={{ marginTop: 6 }}>
                {result.plain_english_summary}
              </p>
            </div>

            <div style={{ marginBottom: 16 }}>
              <strong>Risk Assessment</strong>
              <p style={{ marginTop: 6 }}>
                <span
                  style={{
                    color: riskColor(result.risk_level),
                    fontWeight: 600
                  }}
                >
                  {result.risk_level}
                </span>{" "}
                risk ({result.risk_score})
              </p>
            </div>

            <div>
              <strong>Why this matters</strong>
              <ul style={{ marginTop: 6 }}>
                {result.why_it_matters.map((r, i) => (
                  <li key={i}>{r.replaceAll("_", " ")}</li>
                ))}
              </ul>
            </div>
          </div>
        )}
      </div>
    </div>
  );

}

export default App;

function setEmpty(element, message) {
  element.className = "result empty";
  element.textContent = message;
}

function setError(element, message) {
  element.className = "result error";
  element.textContent = message;
}

function setHtml(element, html) {
  element.className = "result";
  element.innerHTML = html;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll("\"", "&quot;")
    .replaceAll("'", "&#39;");
}

async function apiRequest(url, options = {}) {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    const message = data.error || data.message || `Request failed with ${response.status}`;
    throw new Error(message);
  }

  return data;
}

function formatPairs(pairs) {
  return `<div class="result-grid">${pairs.map(([label, value]) => {
    const isObjectValue =
      value !== null &&
      typeof value === "object" &&
      !Array.isArray(value);

    const renderedValue = isObjectValue
      ? `<pre class="result-json">${escapeHtml(JSON.stringify(value, null, 2))}</pre>`
      : `<div class="result-value">${escapeHtml(value)}</div>`;

    return `
      <div class="result-row">
        <div class="result-key">${escapeHtml(label)}</div>
        ${renderedValue}
      </div>
    `;
  }).join("")}</div>`;
}

function formatJson(value) {
  return `<pre class="result-json">${escapeHtml(JSON.stringify(value, null, 2))}</pre>`;
}

document.addEventListener("DOMContentLoaded", () => {
  const submitResult = document.getElementById("submit-result");
  const appealResult = document.getElementById("appeal-result");
  const verifyResult = document.getElementById("verify-result");
  const metadataResult = document.getElementById("metadata-result");
  const logResult = document.getElementById("log-result");
  const analyticsResult = document.getElementById("analytics-result");

  setEmpty(submitResult, "Submission results will appear here.");
  setEmpty(appealResult, "Appeal responses will appear here.");
  setEmpty(verifyResult, "Verification details will appear here.");
  setEmpty(metadataResult, "Metadata analysis will appear here.");
  setEmpty(logResult, "Click Fetch Log to load recent audit entries.");
  setEmpty(analyticsResult, "Click Fetch Analytics to load dashboard metrics.");

  document.getElementById("submit-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);

    try {
      setEmpty(submitResult, "Submitting text...");
      const data = await apiRequest("/submit", {
        method: "POST",
        body: JSON.stringify({
          creator_id: formData.get("creator_id"),
          text: formData.get("text"),
        }),
      });

      setHtml(submitResult, formatPairs([
        ["content_id", data.content_id],
        ["attribution", data.attribution],
        ["confidence", data.confidence],
        ["label", data.label],
        ["signal_scores.llm", data.signal_scores.llm],
        ["signal_scores.stylometric", data.signal_scores.stylometric],
        ["signal_scores.predictability", data.signal_scores.predictability],
      ]));
    } catch (error) {
      setError(submitResult, error.message);
    }
  });

  document.getElementById("appeal-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);

    try {
      setEmpty(appealResult, "Submitting appeal...");
      const data = await apiRequest("/appeal", {
        method: "POST",
        body: JSON.stringify({
          content_id: formData.get("content_id"),
          creator_reasoning: formData.get("creator_reasoning"),
        }),
      });

      setHtml(appealResult, formatPairs([
        ["content_id", data.content_id],
        ["status", data.status],
        ["message", data.message],
      ]));
    } catch (error) {
      setError(appealResult, error.message);
    }
  });

  document.getElementById("verify-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);

    try {
      setEmpty(verifyResult, "Saving verification...");
      const data = await apiRequest("/verify-creator", {
        method: "POST",
        body: JSON.stringify({
          creator_id: formData.get("creator_id"),
          verification_method: formData.get("verification_method"),
        }),
      });

      setHtml(verifyResult, formatPairs([
        ["creator_id", data.creator_id],
        ["verified", data.verified],
        ["verification_method", data.verification_method],
        ["timestamp", data.timestamp],
        ["certificate_label", data.certificate_label],
      ]));
    } catch (error) {
      setError(verifyResult, error.message);
    }
  });

  document.getElementById("metadata-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);

    try {
      setEmpty(metadataResult, "Analyzing metadata...");
      const data = await apiRequest("/submit-metadata", {
        method: "POST",
        body: JSON.stringify({
          creator_id: formData.get("creator_id"),
          content_type: formData.get("content_type"),
          metadata: {
            tool_used: formData.get("tool_used"),
            declared_ai_assistance: formData.get("declared_ai_assistance") === "on",
            has_process_notes: formData.get("has_process_notes") === "on",
            edit_history_available: formData.get("edit_history_available") === "on",
            human_reviewed: formData.get("human_reviewed") === "on",
          },
        }),
      });

      setHtml(metadataResult, formatPairs([
        ["content_id", data.content_id],
        ["creator_id", data.creator_id],
        ["content_type", data.content_type],
        ["provenance_score", data.provenance_score],
        ["metadata_attribution", data.metadata_attribution],
        ["reason", data.reason],
        ["metadata_checks", data.metadata_checks],
      ]));
    } catch (error) {
      setError(metadataResult, error.message);
    }
  });

  document.getElementById("load-log").addEventListener("click", async () => {
    try {
      setEmpty(logResult, "Loading audit log...");
      const data = await apiRequest("/log");
      setHtml(logResult, formatJson(data.entries));
      logResult.classList.add("preformatted");
    } catch (error) {
      setError(logResult, error.message);
    }
  });

  document.getElementById("load-analytics").addEventListener("click", async () => {
    try {
      setEmpty(analyticsResult, "Loading analytics...");
      const data = await apiRequest("/analytics");
      setHtml(analyticsResult, formatPairs([
        ["total_submissions", data.total_submissions],
        ["likely_ai_count", data.likely_ai_count],
        ["likely_human_count", data.likely_human_count],
        ["uncertain_count", data.uncertain_count],
        ["appeal_count", data.appeal_count],
        ["appeal_rate", data.appeal_rate],
        ["average_confidence", data.average_confidence],
      ]));
    } catch (error) {
      setError(analyticsResult, error.message);
    }
  });
});

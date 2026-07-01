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
      : renderResultValue(value);

    return `
      <div class="result-row">
        <div class="result-label result-key">${escapeHtml(label)}</div>
        ${renderedValue}
      </div>
    `;
  }).join("")}</div>`;
}

function formatJson(value) {
  return `<pre class="result-json">${escapeHtml(JSON.stringify(value, null, 2))}</pre>`;
}

function providerLabel(provider) {
  if (provider === "ollama") {
    return "Local Ollama/Qwen";
  }
  return "Groq cloud";
}

function formatLatency(value) {
  if (typeof value === "number" && Number.isFinite(value)) {
    return `${value} ms`;
  }
  return "Unavailable";
}

function formatScore(value) {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value.toFixed(4);
  }
  return "Unavailable";
}

function formatBoolean(value) {
  if (value === true) {
    return "true";
  }
  if (value === false) {
    return "false";
  }
  return "Unavailable";
}

function renderResultValue(value, options = {}) {
  const { long = false } = options;

  return `<div class="result-value${long ? " result-long-value" : ""}">${escapeHtml(value)}</div>`;
}

function renderResultRow(label, value, options = {}) {
  return `
    <div class="result-row">
      <div class="result-label result-key">${escapeHtml(label)}</div>
      ${renderResultValue(value, options)}
    </div>
  `;
}

function buildSubmitResult(data) {
  const thresholds = data.classification_thresholds || {};
  const scores = data.signal_scores || {};
  const contributions = data.signal_contributions || {};
  const calibration = data.calibration_summary || {};

  return `
    <section class="submit-report">
      <div class="summary-band">
        <div class="summary-chip">
          <span class="summary-label">Attribution</span>
          <strong>${escapeHtml(data.attribution)}</strong>
        </div>
        <div class="summary-chip">
          <span class="summary-label">Combined confidence</span>
          <strong>${escapeHtml(formatScore(data.confidence))}</strong>
        </div>
        <div class="summary-chip">
          <span class="summary-label">Likely AI at</span>
          <strong>${escapeHtml(formatScore(thresholds.likely_ai_min))}+</strong>
        </div>
      </div>

      <div class="result-grid">
        ${renderResultRow("content_id", data.content_id, { long: true })}
        ${renderResultRow("label", data.label)}
        ${renderResultRow("Used LLM Provider", providerLabel(data.llm_provider), { long: true })}
        ${renderResultRow("LLM latency", formatLatency(data.llm_latency_ms))}
      </div>

      <section class="calibration-block calibration-card">
        <h3>Calibration details</h3>
        <div class="result-grid">
          ${renderResultRow("likely_human_max", formatScore(thresholds.likely_human_max))}
          ${renderResultRow("likely_ai_min", formatScore(thresholds.likely_ai_min))}
          ${renderResultRow("Distance to likely_ai", formatScore(calibration.distance_to_likely_ai))}
          ${renderResultRow("Calibration rule applied", formatBoolean(calibration.calibration_rule_applied))}
          ${renderResultRow("Calibration rule", calibration.calibration_rule || "none", { long: true })}
        </div>
        <div class="result-row calibration-explanation-row">
          <div class="result-label result-key">Explanation</div>
          <p class="result-value result-long-value calibration-explanation">${escapeHtml(calibration.explanation || "")}</p>
        </div>
      </section>

      <section class="calibration-block">
        <h3>Signal breakdown</h3>
        <div class="signal-breakdown">
          <article class="signal-card">
            <span class="signal-name">LLM</span>
            <strong>${escapeHtml(formatScore(scores.llm))}</strong>
            <span class="signal-meta">weighted contribution ${escapeHtml(formatScore(contributions.llm))}</span>
          </article>
          <article class="signal-card">
            <span class="signal-name">Stylometric</span>
            <strong>${escapeHtml(formatScore(scores.stylometric))}</strong>
            <span class="signal-meta">weighted contribution ${escapeHtml(formatScore(contributions.stylometric))}</span>
          </article>
          <article class="signal-card">
            <span class="signal-name">Predictability</span>
            <strong>${escapeHtml(formatScore(scores.predictability))}</strong>
            <span class="signal-meta">weighted contribution ${escapeHtml(formatScore(contributions.predictability))}</span>
          </article>
        </div>
      </section>
    </section>
  `;
}

document.addEventListener("DOMContentLoaded", () => {
  const submitResult = document.getElementById("submit-result");
  const appealResult = document.getElementById("appeal-result");
  const verifyResult = document.getElementById("verify-result");
  const metadataResult = document.getElementById("metadata-result");
  const logResult = document.getElementById("log-result");
  const analyticsResult = document.getElementById("analytics-result");
  const providerSelect = document.getElementById("llm-provider-select");
  const providerDefault = document.getElementById("llm-provider-default");

  setEmpty(submitResult, "Submission results will appear here.");
  setEmpty(appealResult, "Appeal responses will appear here.");
  setEmpty(verifyResult, "Verification details will appear here.");
  setEmpty(metadataResult, "Metadata analysis will appear here.");
  setEmpty(logResult, "Click Fetch Log to load recent audit entries.");
  setEmpty(analyticsResult, "Click Fetch Analytics to load dashboard metrics.");
  providerDefault.textContent = "Default provider from .env: Loading...";

  apiRequest("/llm-provider")
    .then((data) => {
      providerDefault.textContent = `Default provider from .env: ${data.default_provider_label || providerLabel(data.default_provider)}`;
    })
    .catch(() => {
      providerDefault.textContent = "Default provider from .env: Groq cloud";
    });

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
          llm_provider: providerSelect.value,
        }),
      });

      setHtml(submitResult, buildSubmitResult(data));
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
        ["Average LLM latency", formatLatency(data.average_llm_latency_ms)],
        ["Average Groq latency", formatLatency(data.average_llm_latency_by_provider?.groq)],
        ["Average Ollama latency", formatLatency(data.average_llm_latency_by_provider?.ollama)],
      ]));
    } catch (error) {
      setError(analyticsResult, error.message);
    }
  });
});

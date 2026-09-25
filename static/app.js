/**
 * VaraVaakku — The Newsroom Verification Desk
 * Frontend Controller & API Integration
 * Pure Vanilla JS · Zero Dependencies · Fully Offline
 */

document.addEventListener("DOMContentLoaded", () => {
  // DOM Elements
  const inputText = document.getElementById("inputText");
  const classifyBtn = document.getElementById("classifyBtn");
  const clearBtn = document.getElementById("clearBtn");
  const bufferStatus = document.getElementById("bufferStatus");
  const loadingState = document.getElementById("loadingState");
  const errorState = document.getElementById("errorState");
  const errorMessage = document.getElementById("errorMessage");
  const resultsSection = document.getElementById("resultsSection");
  
  // Results Elements
  const dossierId = document.getElementById("dossierId");
  const detectedLanguage = document.getElementById("detectedLanguage");
  const verdictStamp = document.getElementById("verdictStamp");
  const stampTitle = document.getElementById("stampTitle");
  const stampVerdictText = document.getElementById("stampVerdictText");
  const stampCode = document.getElementById("stampCode");
  const confidenceValue = document.getElementById("confidenceValue");
  const polygraphNeedle = document.getElementById("polygraphNeedle");
  const needleTag = document.getElementById("needleTag");
  const redactedDocument = document.getElementById("redactedDocument");
  const flaggedList = document.getElementById("flaggedList");

  // Corroboration Elements
  const corroborationLoading = document.getElementById("corroborationLoading");
  const corroborationResult = document.getElementById("corroborationResult");
  const corroborationStatus = document.getElementById("corroborationStatus");
  const corroborationSourcesList = document.getElementById("corroborationSourcesList");

  // Archive & Tabs
  const samplesContainer = document.getElementById("samplesContainer");
  const langTabs = document.getElementById("langTabs");
  const showAllToggle = document.getElementById("showAllToggle");
  const modeBadge = document.getElementById("modeBadge");

  let allSamples = [];
  let currentFilter = "all";
  let dispatchCounter = 1042;

  // 1. Textarea Input Buffer Counter
  function updateBufferStatus() {
    const len = inputText.value.trim().length;
    bufferStatus.textContent = `BUFFER: ${len > 0 ? 'ACTIVE' : 'READY'} (${len} CHARS)`;
  }
  inputText.addEventListener("input", updateBufferStatus);

  // 2. Keyboard shortcut: Ctrl + Enter
  inputText.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
      e.preventDefault();
      handleClassify();
    }
  });

  // 3. Clear Button
  clearBtn.addEventListener("click", () => {
    inputText.value = "";
    updateBufferStatus();
    resultsSection.classList.add("hidden");
    errorState.classList.add("hidden");
    document.querySelectorAll(".sample-card").forEach(c => c.classList.remove("active-card"));
    inputText.focus();
  });

  // 4. Fetch & Render Wire Archive Samples
  async function loadSamples(loadAll = false) {
    try {
      const url = loadAll ? "/samples?all=true" : "/samples";
      const res = await fetch(url);
      if (!res.ok) throw new Error("Failed to load wire samples");
      allSamples = await res.json();
      
      // Update tab counts
      updateTabLabels();
      renderSampleCards();

      if (modeBadge) {
        modeBadge.textContent = loadAll ? "FULL 15-ITEM ARCHIVE" : "★ CURATED DEMO SET";
      }
    } catch (err) {
      console.warn("Could not load samples:", err);
      samplesContainer.innerHTML = `<div class="sample-error-note">Archive offline. You can still paste dispatches manually.</div>`;
    }
  }

  function updateTabLabels() {
    const totalCount = allSamples.length;
    const enCount = allSamples.filter(s => s.lang_code === "en").length;
    const hiCount = allSamples.filter(s => s.lang_code === "hi").length;
    const taCount = allSamples.filter(s => s.lang_code === "ta").length;

    const allBtn = langTabs.querySelector('[data-filter="all"]');
    const enBtn = langTabs.querySelector('[data-filter="en"]');
    const hiBtn = langTabs.querySelector('[data-filter="hi"]');
    const taBtn = langTabs.querySelector('[data-filter="ta"]');

    if (allBtn) allBtn.textContent = `ALL (${totalCount})`;
    if (enBtn) enBtn.textContent = `ENGLISH (${enCount})`;
    if (hiBtn) hiBtn.textContent = `HINDI (${hiCount})`;
    if (taBtn) taBtn.textContent = `TAMIL (${taCount})`;
  }

  // Toggle handler for curated vs all
  if (showAllToggle) {
    showAllToggle.addEventListener("change", () => {
      loadSamples(showAllToggle.checked);
    });
  }

  function renderSampleCards() {
    if (!allSamples || allSamples.length === 0) return;

    const filtered = allSamples.filter(s => {
      if (currentFilter === "all") return true;
      return s.lang_code === currentFilter;
    });

    samplesContainer.innerHTML = "";
    filtered.forEach((sample) => {
      const card = document.createElement("div");
      card.className = "sample-card";
      card.dataset.id = sample.id;

      const isReal = sample.expected && sample.expected.toLowerCase().includes("reliable");
      const truthClass = isReal ? "expected-real" : "expected-fake";
      const truthLabel = isReal ? "★ RELIABLE" : "✕ HOAX / FAKE";

      card.innerHTML = `
        <div class="card-top-meta">
          <span class="card-category">[${sample.category || sample.language}]</span>
          <span class="card-ground-truth ${truthClass}">${truthLabel}</span>
        </div>
        <div class="card-body-headline">${escapeHtml(sample.text)}</div>
        <div class="card-footer-action">PRESS TO SCRUTINIZE ›</div>
      `;

      card.addEventListener("click", () => {
        document.querySelectorAll(".sample-card").forEach(c => c.classList.remove("active-card"));
        card.classList.add("active-card");
        inputText.value = sample.text;
        updateBufferStatus();
        handleClassify();
      });

      samplesContainer.appendChild(card);
    });
  }

  // Filter Tabs Event
  langTabs.addEventListener("click", (e) => {
    const btn = e.target.closest(".tab-btn");
    if (!btn) return;
    document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    currentFilter = btn.dataset.filter;
    renderSampleCards();
  });

  // 5. Submit Classification Action
  classifyBtn.addEventListener("click", handleClassify);

  async function handleClassify() {
    const text = inputText.value.trim();
    if (!text) {
      showError("Please paste or select a news dispatch to verify.");
      inputText.focus();
      return;
    }

    // UI Loading State
    setLoading(true);
    hideError();
    resultsSection.classList.add("hidden");

    try {
      const response = await fetch("/classify", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: text })
      });

      const data = await response.json();

      if (!response.ok || data.error) {
        throw new Error(data.error || "Verification server returned an error.");
      }

      displayResults(data, text);
    } catch (err) {
      console.error("Classification error:", err);
      showError(err.message || "Failed to communicate with classification model.");
    } finally {
      setLoading(false);
    }
  }

  // 6. Display Results Dossier
  function displayResults(data, originalText) {
    dispatchCounter++;
    dossierId.textContent = `DISPATCH RECORD #VV-${dispatchCounter} · FORENSIC MEMO`;
    
    // Detected Language
    detectedLanguage.textContent = data.language || "Unknown";

    // Verdict Stamp
    const isReliable = data.verdict && data.verdict.toLowerCase().includes("reliable");
    verdictStamp.className = "rubber-stamp";
    
    if (isReliable) {
      verdictStamp.classList.add("stamp-verified");
      stampTitle.textContent = "VERIFIED";
      stampVerdictText.textContent = "RELIABLE NEWS";
      stampCode.textContent = "DESK APPROVAL · PASS";
    } else {
      verdictStamp.classList.add("stamp-flagged");
      stampTitle.textContent = "FLAGGED";
      stampVerdictText.textContent = "MISLEADING / FAKE";
      stampCode.textContent = "ANOMALY REJECT · HOAX";
    }

    // Polygraph Confidence Scale
    const conf = Math.max(0, Math.min(100, parseFloat(data.confidence) || 0));
    confidenceValue.textContent = `${conf.toFixed(1)}%`;
    needleTag.textContent = `${conf.toFixed(1)}%`;
    
    // Animate Needle
    polygraphNeedle.style.left = `${conf}%`;
    polygraphNeedle.className = "polygraph-needle";
    polygraphNeedle.classList.add(isReliable ? "state-reliable" : "state-misleading");

    // Redaction Dossier with Interactive Black Bars
    buildRedactedDocument(originalText, data.flagged_phrases || []);

    // Flagged Notes List
    buildFlaggedNotes(data.flagged_phrases || [], isReliable);

    // Reveal Results
    resultsSection.classList.remove("hidden");
    resultsSection.scrollIntoView({ behavior: "smooth", block: "nearest" });

    // Asynchronously trigger corroboration check (non-blocking)
    fetchCorroboration(originalText);
  }

  // 7. Forensic Text Inspection: Solid Black Redaction Bars
  function buildRedactedDocument(text, flaggedPhrases) {
    if (!flaggedPhrases || flaggedPhrases.length === 0) {
      redactedDocument.innerHTML = `<div>${escapeHtml(text)}</div>`;
      return;
    }

    let annotatedHtml = escapeHtml(text);

    // Replace flagged phrases with redaction spans
    flaggedPhrases.forEach(phrase => {
      const cleanPhrase = phrase.trim();
      if (!cleanPhrase || cleanPhrase.length < 3) return;

      // Extract phrase words for flexible matching if full sentence was truncated
      const escapedPhrase = escapeRegex(cleanPhrase);
      const regex = new RegExp(`(${escapedPhrase})`, "gi");

      annotatedHtml = annotatedHtml.replace(regex, (match) => {
        return `<span class="redaction-bar" title="Click or hover to reveal classified text" tabindex="0">${match}</span>`;
      });
    });

    redactedDocument.innerHTML = annotatedHtml;

    // Toggle reveal on click for mobile/touch
    redactedDocument.querySelectorAll(".redaction-bar").forEach(span => {
      span.addEventListener("click", () => {
        span.classList.toggle("revealed");
      });
    });
  }

  // 8. Flagged Notes Breakdown
  function buildFlaggedNotes(flaggedPhrases, isReliable) {
    flaggedList.innerHTML = "";

    if (!flaggedPhrases || flaggedPhrases.length === 0) {
      const li = document.createElement("li");
      li.className = "clean-note-item";
      li.innerHTML = `✓ No sensational trigger words, excessive punctuation, or abnormal capitalization detected in this wire.`;
      flaggedList.appendChild(li);
      return;
    }

    flaggedPhrases.forEach((phrase, idx) => {
      const li = document.createElement("li");
      li.className = "flagged-note-item";
      
      let reason = "Sensational or Rhetorical Anomaly";
      if (phrase.includes("!!")) reason = "Excessive Punctuation ('!!')";
      else if (/[A-Z]{3,}/.test(phrase)) reason = "ALL-CAPS Urgency / Hyperbole";
      else if (/shocking|secret|miracle|banned|exposed|सावधान|அதிர்ச்சி/i.test(phrase)) reason = "Viral Misinformation Trigger Keyword";

      li.innerHTML = `
        <span class="badge-flag">[FLAG #${idx + 1}: ${reason}]</span>
        <span class="note-quote">"${escapeHtml(phrase)}"</span>
      `;
      flaggedList.appendChild(li);
    });
  }

  // 9. Real-Time Corroboration Layer (Optional, Non-blocking, Graceful Degradation)
  async function fetchCorroboration(text) {
    if (!corroborationLoading || !corroborationResult) return;

    corroborationLoading.classList.remove("hidden");
    corroborationResult.classList.add("hidden");
    corroborationSourcesList.innerHTML = "";

    try {
      const response = await fetch("/corroborate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: text })
      });

      const data = await response.json();

      if (data && data.found && data.sources && data.sources.length > 0) {
        corroborationStatus.className = "corroboration-status-bar found";
        corroborationStatus.textContent = `✓ MATCHING COVERAGE FOUND IN LIVE NEWS ARCHIVES (${data.sources.length} SOURCES)`;

        corroborationSourcesList.innerHTML = "";
        data.sources.forEach(src => {
          const div = document.createElement("div");
          div.className = "corroboration-source-card";
          div.innerHTML = `
            <span class="source-name-badge">${escapeHtml(src.name)}</span>
            <span class="source-title-text">${escapeHtml(src.title)}</span>
            <a href="${escapeHtml(src.link)}" target="_blank" rel="noopener noreferrer" class="source-link-anchor">VIEW SOURCE ↗</a>
          `;
          corroborationSourcesList.appendChild(div);
        });
      } else if (data && data.status && data.status.toLowerCase().includes("offline")) {
        corroborationStatus.className = "corroboration-status-bar offline";
        corroborationStatus.textContent = "⚡ Corroboration check unavailable — offline mode.";
      } else {
        corroborationStatus.className = "corroboration-status-bar not-found";
        corroborationStatus.textContent = "○ No matching coverage found in live news archives for these terms.";
      }
    } catch (err) {
      corroborationStatus.className = "corroboration-status-bar offline";
      corroborationStatus.textContent = "⚡ Corroboration check unavailable — offline mode.";
    } finally {
      corroborationLoading.classList.add("hidden");
      corroborationResult.classList.remove("hidden");
    }
  }

  // Utilities
  function setLoading(isLoading) {
    if (isLoading) {
      loadingState.classList.remove("hidden");
      classifyBtn.disabled = true;
      classifyBtn.style.opacity = "0.6";
    } else {
      loadingState.classList.add("hidden");
      classifyBtn.disabled = false;
      classifyBtn.style.opacity = "1";
    }
  }

  function showError(msg) {
    errorMessage.textContent = msg;
    errorState.classList.remove("hidden");
  }

  function hideError() {
    errorState.classList.add("hidden");
  }

  function escapeHtml(str) {
    if (!str) return "";
    return str
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function escapeRegex(str) {
    return str.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  }

  // Initial Boot
  loadSamples();
});

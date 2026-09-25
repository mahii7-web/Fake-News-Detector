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

  // Reconciled Verdict & Evidence Dossier Elements
  const finalVerdictHeadline = document.getElementById("finalVerdictHeadline");
  const reconciliationCaveatBadge = document.getElementById("reconciliationCaveatBadge");
  const signalOfflineBadge = document.getElementById("signalOfflineBadge");
  const signalCorroborationBadge = document.getElementById("signalCorroborationBadge");

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

  // Backend API URL: uses relative path when hosted on Flask localhost,
  // and points to Render backend URL when deployed as split architecture on Vercel.
  const API_BASE_URL = window.API_BASE_URL ||
    localStorage.getItem("varavaakku_api_url") ||
    ((window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1")
      ? ""
      : "https://varavaakku-backend.onrender.com");

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
      const endpoint = loadAll ? "/samples?all=true" : "/samples";
      const url = `${API_BASE_URL}${endpoint}`;
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
      const response = await fetch(`${API_BASE_URL}/classify`, {
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

  // Helper: Set Rubber Stamp Visual State
  function setStampState(state, verdictText, conf, customCode) {
    verdictStamp.className = "rubber-stamp";
    
    if (state === "corroborated") {
      verdictStamp.classList.add("stamp-corroborated");
      stampTitle.textContent = "CORROBORATED";
      stampVerdictText.textContent = "RELIABLE — CORROBORATED";
      stampCode.textContent = customCode || "LIVE WIRE MATCH · 2+ SOURCES";
    } else if (state === "review") {
      verdictStamp.classList.add("stamp-review");
      stampTitle.textContent = "MANUAL REVIEW";
      stampVerdictText.textContent = "FLAGGED PATTERN · WIRE MATCH";
      stampCode.textContent = customCode || "DUAL SIGNAL · MANUAL AUDIT REQUIRED";
    } else if (state === "verified") {
      verdictStamp.classList.add("stamp-verified");
      stampTitle.textContent = "VERIFIED";
      stampVerdictText.textContent = "RELIABLE NEWS";
      stampCode.textContent = customCode || "DESK APPROVAL · PASS";
    } else {
      verdictStamp.classList.add("stamp-flagged");
      stampTitle.textContent = "FLAGGED";
      stampVerdictText.textContent = "MISLEADING / FAKE";
      stampCode.textContent = customCode || "ANOMALY REJECT · HOAX";
    }
  }

  // 6. Display Results Dossier
  function displayResults(data, originalText) {
    dispatchCounter++;
    dossierId.textContent = `DISPATCH RECORD #VV-${dispatchCounter} · FORENSIC MEMO`;
    
    // Detected Language
    detectedLanguage.textContent = data.language || "Unknown";

    const isReliable = data.verdict && data.verdict.toLowerCase().includes("reliable");
    const conf = Math.max(0, Math.min(100, parseFloat(data.confidence) || 0));

    // Initial Rubber Stamp (from offline classification)
    setStampState(isReliable ? "verified" : "flagged", data.verdict, conf);

    // Initial Top Final Combined Verdict
    if (finalVerdictHeadline) {
      finalVerdictHeadline.textContent = data.verdict ? data.verdict.toUpperCase() : "ANALYZED";
    }
    if (reconciliationCaveatBadge) {
      reconciliationCaveatBadge.className = "reconciliation-caveat-badge";
      reconciliationCaveatBadge.textContent = "⚡ Running 100% offline — querying live press wire for corroboration...";
    }

    // Signal 1 Card Badge
    if (signalOfflineBadge) {
      signalOfflineBadge.className = `evidence-badge ${isReliable ? 'badge-reliable' : 'badge-misleading'}`;
      signalOfflineBadge.textContent = `Offline: ${data.verdict} (${conf.toFixed(1)}%)`;
    }

    // Signal 2 Card Badge (Initial)
    if (signalCorroborationBadge) {
      signalCorroborationBadge.className = "evidence-badge";
      signalCorroborationBadge.textContent = "Live Wire: Querying...";
    }

    // Polygraph Confidence Scale
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

    // Asynchronously trigger corroboration check (non-blocking, passing offline signals)
    fetchCorroboration(originalText, data);
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

  // 9. Real-Time Corroboration Layer with Verdict Reconciliation
  async function fetchCorroboration(text, offlineData) {
    if (!corroborationLoading || !corroborationResult) return;

    corroborationLoading.classList.remove("hidden");
    corroborationResult.classList.add("hidden");
    corroborationSourcesList.innerHTML = "";

    const offlineVerdict = offlineData ? offlineData.verdict : "";
    const offlineConfidence = offlineData ? (parseFloat(offlineData.confidence) || 0) : 0;
    const isOfflineMisleading = (offlineVerdict || "").toLowerCase().includes("misleading");

    try {
      const response = await fetch(`${API_BASE_URL}/corroborate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text: text,
          offline_verdict: offlineVerdict,
          offline_confidence: offlineConfidence
        })
      });

      const data = await response.json();
      const sources = (data && data.sources) ? data.sources : [];
      const found = !!(data && data.found && sources.length > 0);
      const isOfflineStatus = !!(data && data.status && data.status.toLowerCase().includes("offline"));

      // 1. Render Signal 2 (Corroboration Card Content)
      if (found) {
        corroborationStatus.className = "corroboration-status-bar found";
        corroborationStatus.textContent = `✓ MATCHING COVERAGE FOUND IN LIVE NEWS ARCHIVES (${sources.length} SOURCES)`;

        corroborationSourcesList.innerHTML = "";
        sources.forEach(src => {
          const div = document.createElement("div");
          div.className = "corroboration-source-card";
          div.innerHTML = `
            <span class="source-name-badge">${escapeHtml(src.name)}</span>
            <span class="source-title-text">${escapeHtml(src.title)}</span>
            <a href="${escapeHtml(src.link)}" target="_blank" rel="noopener noreferrer" class="source-link-anchor">VIEW SOURCE ↗</a>
          `;
          corroborationSourcesList.appendChild(div);
        });
      } else if (isOfflineStatus) {
        corroborationStatus.className = "corroboration-status-bar offline";
        corroborationStatus.textContent = "⚡ Corroboration check unavailable — offline mode.";
      } else {
        corroborationStatus.className = "corroboration-status-bar not-found";
        corroborationStatus.textContent = "○ No matching coverage found in live news archives for these terms.";
      }

      // 2. Verdict Reconciliation: Roll up into ONE coherent final verdict at top
      if (found && sources.length >= 2) {
        // Case 1: Corroboration finds matching coverage from 2+ sources
        if (isOfflineMisleading && offlineConfidence >= 90.0) {
          // Exception: Offline confidence for "Misleading" was very high (90%+)
          setStampState("review", "FLAGGED PATTERN · WIRE MATCH", offlineConfidence, "DUAL SIGNAL · MANUAL AUDIT REQUIRED");
          if (finalVerdictHeadline) finalVerdictHeadline.textContent = "MANUAL REVIEW RECOMMENDED";
          if (reconciliationCaveatBadge) {
            reconciliationCaveatBadge.className = "reconciliation-caveat-badge review";
            reconciliationCaveatBadge.textContent = "⚠ Content pattern flagged, but matching coverage found — recommend manual review";
          }
          if (signalOfflineBadge) {
            signalOfflineBadge.className = "evidence-badge badge-review";
            signalOfflineBadge.textContent = `Offline: Pattern Flagged (${offlineConfidence.toFixed(1)}%)`;
          }
          if (signalCorroborationBadge) {
            signalCorroborationBadge.className = "evidence-badge badge-corroborated";
            signalCorroborationBadge.textContent = `Live: ${sources.length} Sources Found`;
          }
        } else {
          // Override to "RELIABLE — CORROBORATED"
          setStampState("corroborated", "RELIABLE — CORROBORATED", offlineConfidence, `LIVE WIRE MATCH · ${sources.length} SOURCES`);
          if (finalVerdictHeadline) finalVerdictHeadline.textContent = "RELIABLE — CORROBORATED";
          if (reconciliationCaveatBadge) {
            reconciliationCaveatBadge.className = "reconciliation-caveat-badge reconciled";
            if (isOfflineMisleading) {
              reconciliationCaveatBadge.textContent = `✓ Reconciled: External news coverage verified across ${sources.length} sources (overrode offline pattern flag)`;
            } else {
              reconciliationCaveatBadge.textContent = `✓ Corroborated: Real-time news coverage confirmed across ${sources.length} verified sources`;
            }
          }
          if (signalOfflineBadge) {
            signalOfflineBadge.className = `evidence-badge ${isOfflineMisleading ? 'badge-misleading' : 'badge-reliable'}`;
            signalOfflineBadge.textContent = isOfflineMisleading 
              ? `Offline: Flagged (${offlineConfidence.toFixed(1)}%) [OVERRIDDEN]`
              : `Offline: Reliable (${offlineConfidence.toFixed(1)}%)`;
          }
          if (signalCorroborationBadge) {
            signalCorroborationBadge.className = "evidence-badge badge-corroborated";
            signalCorroborationBadge.textContent = `Live: ${sources.length} Sources Confirmed`;
          }
        }
      } else if (!found || sources.length < 2) {
        // Case 2: No matching coverage found
        const isReliable = !isOfflineMisleading;
        setStampState(isReliable ? "verified" : "flagged", offlineVerdict, offlineConfidence);
        if (finalVerdictHeadline) finalVerdictHeadline.textContent = offlineVerdict ? offlineVerdict.toUpperCase() : "ANALYZED";
        if (reconciliationCaveatBadge) {
          reconciliationCaveatBadge.className = "reconciliation-caveat-badge caveat";
          reconciliationCaveatBadge.textContent = "○ No corroborating source found — verdict based on content pattern only";
        }
        if (signalCorroborationBadge) {
          signalCorroborationBadge.className = "evidence-badge";
          signalCorroborationBadge.textContent = "Live Wire: No Match";
        }
      } else if (isOfflineStatus) {
        // Case 3: Offline mode fallback
        const isReliable = !isOfflineMisleading;
        setStampState(isReliable ? "verified" : "flagged", offlineVerdict, offlineConfidence);
        if (finalVerdictHeadline) finalVerdictHeadline.textContent = offlineVerdict ? offlineVerdict.toUpperCase() : "ANALYZED";
        if (reconciliationCaveatBadge) {
          reconciliationCaveatBadge.className = "reconciliation-caveat-badge offline";
          reconciliationCaveatBadge.textContent = "⚡ Corroboration check unavailable — offline mode.";
        }
        if (signalCorroborationBadge) {
          signalCorroborationBadge.className = "evidence-badge";
          signalCorroborationBadge.textContent = "Live Wire: Offline Mode";
        }
      }

    } catch (err) {
      console.warn("Corroboration request error:", err);
      corroborationStatus.className = "corroboration-status-bar offline";
      corroborationStatus.textContent = "⚡ Corroboration check unavailable — offline mode.";

      if (reconciliationCaveatBadge) {
        reconciliationCaveatBadge.className = "reconciliation-caveat-badge offline";
        reconciliationCaveatBadge.textContent = "⚡ Corroboration check unavailable — offline mode.";
      }
      if (signalCorroborationBadge) {
        signalCorroborationBadge.className = "evidence-badge";
        signalCorroborationBadge.textContent = "Live Wire: Offline Mode";
      }
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

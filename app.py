import json
import os
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import psutil
import torch
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS

app = Flask(__name__)
# Enable CORS for cross-origin requests from Vercel frontend or any origin
CORS(app, resources={r"/*": {"origins": "*"}})

def log_system_memory(checkpoint: str):
    """Logs available system memory and current process RSS for deployment diagnostics."""
    try:
        vm = psutil.virtual_memory()
        proc = psutil.Process()
        proc_rss_mb = proc.memory_info().rss / (1024 * 1024)
        avail_mb = vm.available / (1024 * 1024)
        total_mb = vm.total / (1024 * 1024)
        print(f"[Memory - {checkpoint}] Process RSS: {proc_rss_mb:.1f} MB | System Avail: {avail_mb:.1f} MB / {total_mb:.1f} MB Total")
        if total_mb <= 600:
            print(f"[Memory Alert - {checkpoint}] Low memory host detected ({total_mb:.0f} MB total, matching Render 512MB free tier).")
            print(f"[Memory Alert - {checkpoint}] Note: Combined model footprint (~2.5 GB) will exceed 512MB RAM and risk SIGKILL (OOM).")
    except Exception as _me:
        print(f"[Memory Check Note]: {_me}")

# Verify compute device and log initial memory state
print("[Init] Starting Multilingual Fake News Detector Backend...")
log_system_memory("Startup")

# Determine compute device
device = 0 if torch.cuda.is_available() else -1
print(f"[Device] Using {'CUDA (GPU)' if device == 0 else 'CPU'}")

LANG_MODEL_NAME = "papluca/xlm-roberta-base-language-detection"
NLI_MODEL_NAME = "MoritzLaurer/mDeBERTa-v3-base-mnli-xnli"

# Load models ONCE at module level to eliminate reload lag in live demo
print(f"[Model 1/2] Loading language identification model: {LANG_MODEL_NAME}...")
from transformers import pipeline
try:
    lang_pipe = pipeline("text-classification", model=LANG_MODEL_NAME, device=device)
    print("[Model 1/2] Language identification model loaded successfully.")
    log_system_memory("Post-Model 1")
except Exception as e:
    print(f"[CRITICAL ERROR] Failed to load Model 1 ({LANG_MODEL_NAME}): {e}", file=sys.stderr)
    log_system_memory("Model 1 Failure")
    raise

print(f"[Model 2/2] Loading multilingual zero-shot classifier: {NLI_MODEL_NAME}...")
try:
    classifier_pipe = pipeline("zero-shot-classification", model=NLI_MODEL_NAME, device=device)
    print("[Model 2/2] Multilingual classifier loaded successfully.")
    log_system_memory("Post-Model 2")
except Exception as e:
    print(f"[CRITICAL ERROR] Failed to load Model 2 ({NLI_MODEL_NAME}): {e}", file=sys.stderr)
    log_system_memory("Model 2 Failure")
    raise

# Warm-up pass to eliminate cold-start inference lag during live evaluation
print("[Warm-up] Executing startup warm-up inference pass...")
try:
    _dummy_text = "Headline test: Breaking scientific discovery."
    _ = lang_pipe(_dummy_text[:512])
    _ = classifier_pipe(_dummy_text[:512], candidate_labels=["reliable news", "misleading/fake news"])
    print("Models warmed up and ready")
    log_system_memory("Post-Warmup Ready")
except Exception as _we:
    print(f"[Warm-up Note]: {_we}")

# Human-readable language map
LANG_MAP = {
    "en": "English",
    "hi": "Hindi",
    "ta": "Tamil",
    "ur": "Urdu",
    "fr": "French",
    "es": "Spanish",
    "de": "German",
    "it": "Italian",
    "pt": "Portuguese",
    "ru": "Russian",
    "zh": "Chinese",
    "ja": "Japanese",
    "ar": "Arabic"
}

TRIGGER_WORDS = [
    "shocking",
    "miracle",
    "you won't believe",
    "secret",
    "banned",
    "doctors hate",
    "exposed",
    # Additional regional sensational triggers
    "सावधान",
    "चमत्कार",
    "खुलासा",
    "அதிர்ச்சி",
    "ரகசியம்",
    "உடனே பகிருங்கள்"
]

def detect_language(text: str) -> str:
    """Detect language with native Tamil script support and XLM-RoBERTa pipeline."""
    # Fast Unicode check for Tamil script (U+0B80 - U+0BFF)
    tamil_chars = sum(1 for c in text if '\u0B80' <= c <= '\u0BFF')
    if tamil_chars > 3:
        return "Tamil (ta)"
    
    # Devanagari script (U+0900 - U+097F) check for Hindi
    devanagari_chars = sum(1 for c in text if '\u0900' <= c <= '\u097F')
    
    try:
        res = lang_pipe(text[:512])[0]
        code = res.get("label", "unknown")
        if devanagari_chars > 5 and code not in ["hi", "ur", "mr", "ne"]:
            code = "hi"
        name = LANG_MAP.get(code, code.upper())
        return f"{name} ({code})"
    except Exception:
        if devanagari_chars > 3:
            return "Hindi (hi)"
        return "English (en)"

def extract_flagged_phrases(text: str) -> list[str]:
    """
    Simple heuristic function (no extra model call) to extract flagged suspicious phrases:
    - Sentences containing ALL-CAPS words (len >= 3)
    - 2+ consecutive exclamation marks ('!!')
    - Any word from the trigger list
    """
    if not text:
        return []

    # Split text into sentences using common punctuation marks including Hindi purna viram (।)
    sentences = re.split(r'[.!?।\n]+', text)
    flagged = []

    for raw_s in sentences:
        s = raw_s.strip()
        if not s:
            continue
        
        is_suspicious = False
        lower_s = s.lower()

        # Check for 2+ consecutive exclamation marks in the sentence or original text
        if "!!" in text or "!!" in raw_s:
            if "!" in raw_s or len(sentences) == 1:
                is_suspicious = True

        # Check for trigger words
        for trigger in TRIGGER_WORDS:
            if trigger in lower_s:
                is_suspicious = True
                break

        # Check for ALL-CAPS words (length >= 3, alphabetic)
        words = re.findall(r'\b[A-Za-z]+\b', s)
        for w in words:
            if len(w) >= 3 and w.isupper() and w not in ["THE", "AND", "FOR"]:
                is_suspicious = True
                break

        if is_suspicious and s not in flagged:
            flagged.append(s)
            if len(flagged) >= 3:
                break

    # If no sentence boundary captured the exclamation or trigger, capture the specific match
    if not flagged:
        for trigger in TRIGGER_WORDS:
            if trigger in text.lower():
                flagged.append(f"Trigger matched: '{trigger}'")
                break

    return flagged[:3]

@app.route("/", methods=["GET"])
def index():
    """Serves the newsroom verification desk editorial dashboard."""
    return render_template("index.html")

@app.route("/samples", methods=["GET"])
def get_samples():
    """
    Returns curated demo samples by default (demo_curated.json).
    Returns the full 15 samples if query parameter ?all=true is passed.
    """
    show_all = request.args.get("all", "false").lower() in ["true", "1", "yes"]
    filename = "demo_samples.json" if show_all else "demo_curated.json"
    samples_path = os.path.join(os.path.dirname(__file__), filename)
    if not os.path.exists(samples_path):
        samples_path = os.path.join(os.path.dirname(__file__), "demo_samples.json")
    try:
        with open(samples_path, "r", encoding="utf-8") as f:
            samples = json.load(f)
        return jsonify(samples), 200
    except Exception as e:
        return jsonify({"error": f"Failed to load samples: {str(e)}"}), 500

@app.route("/classify", methods=["POST"])
def classify():
    """
    POST route: accepts JSON {"text": "..."}, returns JSON with:
    {"language": ..., "verdict": ..., "confidence": ..., "flagged_phrases": [...]}
    Wrapped in try/except returning clean JSON errors.
    """
    try:
        data = request.get_json(force=True, silent=True)
        if not data or "text" not in data or not str(data["text"]).strip():
            return jsonify({
                "language": "N/A",
                "verdict": "Invalid Input",
                "confidence": 0.0,
                "flagged_phrases": [],
                "error": "Missing or empty 'text' parameter in JSON payload."
            }), 400

        text = str(data["text"]).strip()

        # Step 1: Detect Language
        language = detect_language(text)

        # Step 2: Zero-shot classification
        candidate_labels = ["reliable news", "misleading/fake news"]
        classification_res = classifier_pipe(text[:512], candidate_labels=candidate_labels)
        
        raw_verdict = classification_res["labels"][0]
        confidence = float(classification_res["scores"][0] * 100.0)

        # Map to display verdict
        if "reliable" in raw_verdict.lower():
            verdict = "Reliable News"
        else:
            verdict = "Misleading / Fake News"

        # Step 3: Heuristic flagged phrases
        flagged_phrases = extract_flagged_phrases(text)

        return jsonify({
            "language": language,
            "verdict": verdict,
            "confidence": round(confidence, 2),
            "flagged_phrases": flagged_phrases
        }), 200

    except Exception as e:
        # Never crash with raw 500 trace in demo
        print(f"[Inference Error]: {e}", file=sys.stderr)
        return jsonify({
            "language": "Unknown",
            "verdict": "Classification Error",
            "confidence": 0.0,
            "flagged_phrases": [],
            "error": f"Inference failed safely: {str(e)}"
        }), 200

# ==============================================================================
# OPTIONAL Real-Time Corroboration Layer (Non-blocking, Graceful Degradation)
# ==============================================================================
STOPWORDS = {
    # English
    "the", "a", "an", "in", "on", "at", "to", "for", "of", "with", "by", "from",
    "is", "are", "was", "were", "be", "been", "being", "have", "has", "had",
    "do", "does", "did", "will", "would", "shall", "should", "may", "might", "can", "could",
    "and", "but", "or", "nor", "so", "yet", "both", "neither", "either",
    "this", "that", "these", "those", "it", "its", "they", "them", "their",
    "shocking", "urgent", "warning", "secret", "miracle", "alert", "breaking",
    "completely", "without", "starting", "next", "after", "before", "about",
    # Hindi
    "का", "के", "की", "को", "में", "से", "पर", "है", "हैं", "था", "थी", "थे",
    "और", "या", "यह", "वह", "इस", "उस", "ने", "भी", "तक", "लिए", "रहे", "रहा",
    "सावधान", "तुरंत", "शेयर", "करें", "पूरी", "तरह", "सभी",
    # Tamil
    "இந்த", "அந்த", "ஒரு", "மற்றும்", "உடன்", "இல்", "க்கு", "இருந்து", "ஆகிய",
    "அதிர்ச்சி", "தகவல்", "உடனே", "பகிருங்கள்", "அனைத்தும்"
}

def extract_search_terms(text: str) -> str:
    cleaned = re.sub(r'[!?,.:;\'"()\[\]/\\॥|।]+', ' ', text)
    tokens = cleaned.split()
    meaningful = [w for w in tokens if w.lower() not in STOPWORDS and len(w) > 2]
    if meaningful:
        return " ".join(meaningful[:5])
    return text[:60].strip()

def search_news_corroboration(text: str, timeout: float = 3.5) -> dict:
    query = extract_search_terms(text)
    if not query:
        return {"found": False, "query": "", "sources": [], "status": "No search terms extracted"}

    # Detect language script for search localization
    tamil_chars = sum(1 for c in text if '\u0B80' <= c <= '\u0BFF')
    devanagari_chars = sum(1 for c in text if '\u0900' <= c <= '\u097F')
    
    hl, gl, ceid = "en-IN", "IN", "IN:en"
    if tamil_chars > 3:
        hl, gl, ceid = "ta", "IN", "IN:ta"
    elif devanagari_chars > 3:
        hl, gl, ceid = "hi", "IN", "IN:hi"

    url = f"https://news.google.com/rss/search?q={urllib.parse.quote(query)}&hl={hl}&gl={gl}&ceid={ceid}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    req = urllib.request.Request(url, headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            root = ET.fromstring(resp.read())
            items = root.findall(".//item")
            if not items:
                return {
                    "found": False,
                    "query": query,
                    "sources": [],
                    "status": "No matching coverage found in live news"
                }

            sources = []
            seen_sources = set()
            for item in items:
                source_name = item.find("source").text if item.find("source") is not None else ""
                title = item.find("title").text if item.find("title") is not None else ""
                link = item.find("link").text if item.find("link") is not None else ""
                
                clean_title = re.sub(r'\s*-\s*[^-\n]+$', '', title).strip()
                source_label = source_name or "Verified News Outlet"

                if source_label not in seen_sources:
                    seen_sources.add(source_label)
                    sources.append({
                        "name": source_label,
                        "title": clean_title,
                        "link": link
                    })
                if len(sources) >= 2:
                    break

            return {
                "found": len(sources) > 0,
                "query": query,
                "sources": sources,
                "status": f"Matching coverage found across {len(sources)} source(s)" if sources else "No matching coverage found"
            }
    except Exception:
        # Graceful degradation on timeout or offline mode
        return {
            "found": False,
            "query": query,
            "sources": [],
            "status": "Corroboration check unavailable — offline mode."
        }

def reconcile_verdict(offline_verdict: str, offline_confidence: float, search_result: dict) -> dict:
    """
    Reconciles offline zero-shot classification with real-time news corroboration.
    
    1. If corroboration finds matching coverage from 2+ sources:
       - Override displayed verdict to 'RELIABLE — CORROBORATED' regardless of offline output,
         UNLESS offline confidence for 'Misleading' was very high (90%+), in which case show:
         'Content pattern flagged, but matching coverage found — recommend manual review'
       - Visually change stamp badge to 'CORROBORATED' (neutral/blue) or 'MANUAL REVIEW' (amber).
    2. If corroboration finds NO matching coverage:
       - Keep offline verdict as-is, with caveat:
         'No corroborating source found — verdict based on content pattern only'
    3. If corroboration is unavailable (offline mode / timeout):
       - Keep offline verdict with fallback message:
         'Corroboration check unavailable — offline mode.'
    """
    sources = search_result.get("sources", [])
    found = search_result.get("found", False)
    status = search_result.get("status", "")
    is_offline = "offline mode" in status.lower()

    is_reliable_offline = "reliable" in (offline_verdict or "").lower()
    default_stamp_state = "verified" if is_reliable_offline else "flagged"
    default_stamp_title = "VERIFIED" if is_reliable_offline else "FLAGGED"
    default_stamp_subtitle = "RELIABLE NEWS" if is_reliable_offline else "MISLEADING / FAKE"
    default_stamp_code = "DESK APPROVAL · PASS" if is_reliable_offline else "ANOMALY REJECT · HOAX"

    if is_offline or not search_result.get("query"):
        return {
            "final_verdict": offline_verdict or "Unverified",
            "stamp_state": default_stamp_state,
            "stamp_title": default_stamp_title,
            "stamp_subtitle": default_stamp_subtitle,
            "stamp_code": default_stamp_code,
            "reconciliation_action": "offline_fallback",
            "reconciliation_note": "Corroboration check unavailable — offline mode.",
            "is_corroborated": False
        }

    # 1. Matching coverage found across 2+ sources
    if found and len(sources) >= 2:
        is_misleading = "misleading" in (offline_verdict or "").lower()
        if is_misleading and offline_confidence >= 90.0:
            return {
                "final_verdict": "Manual Review Recommended",
                "stamp_state": "review",
                "stamp_title": "MANUAL REVIEW",
                "stamp_subtitle": "FLAGGED PATTERN · WIRE MATCH",
                "stamp_code": "DUAL SIGNAL · MANUAL AUDIT REQUIRED",
                "reconciliation_action": "manual_review",
                "reconciliation_note": "Content pattern flagged, but matching coverage found — recommend manual review",
                "is_corroborated": True
            }
        else:
            return {
                "final_verdict": "RELIABLE — CORROBORATED",
                "stamp_state": "corroborated",
                "stamp_title": "CORROBORATED",
                "stamp_subtitle": "RELIABLE — CORROBORATED",
                "stamp_code": f"LIVE WIRE MATCH · {len(sources)} SOURCES",
                "reconciliation_action": "override_reliable",
                "reconciliation_note": f"Matching coverage found across {len(sources)} source(s) — external news confirmation",
                "is_corroborated": True
            }

    # 2. No matching coverage found
    return {
        "final_verdict": offline_verdict or "Unverified",
        "stamp_state": default_stamp_state,
        "stamp_title": default_stamp_title,
        "stamp_subtitle": default_stamp_subtitle,
        "stamp_code": default_stamp_code,
        "reconciliation_action": "keep_offline",
        "reconciliation_note": "No corroborating source found — verdict based on content pattern only",
        "is_corroborated": False
    }

@app.route("/corroborate", methods=["POST"])
def corroborate():
    """
    OPTIONAL real-time corroboration endpoint.
    Accepts JSON {"text": "...", "offline_verdict": "...", "offline_confidence": ...}.
    Performs live news query with 3.5s timeout.
    Reconciles with offline signals into a single coherent result.
    Degrades gracefully on timeout or offline mode.
    """
    try:
        data = request.get_json(force=True, silent=True)
        if not data or "text" not in data or not str(data["text"]).strip():
            return jsonify({
                "found": False,
                "query": "",
                "sources": [],
                "status": "Missing or empty 'text' parameter."
            }), 400

        text = str(data["text"]).strip()
        offline_verdict = data.get("offline_verdict")
        offline_confidence = float(data.get("offline_confidence", 0.0))

        result = search_news_corroboration(text, timeout=3.5)

        if offline_verdict:
            result["reconciliation"] = reconcile_verdict(offline_verdict, offline_confidence, result)

        return jsonify(result), 200

    except Exception as e:
        fallback_result = {
            "found": False,
            "query": "",
            "sources": [],
            "status": "Corroboration check unavailable — offline mode."
        }
        if data and data.get("offline_verdict"):
            fallback_result["reconciliation"] = reconcile_verdict(
                data.get("offline_verdict"),
                float(data.get("offline_confidence", 0.0)),
                fallback_result
            )
        return jsonify(fallback_result), 200

@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint with system memory telemetry."""
    try:
        vm = psutil.virtual_memory()
        proc = psutil.Process()
        return jsonify({
            "status": "healthy",
            "service": "varavaakku-backend",
            "device": "cuda" if device == 0 else "cpu",
            "process_rss_mb": round(proc.memory_info().rss / (1024 * 1024), 2),
            "system_available_mb": round(vm.available / (1024 * 1024), 2),
            "system_total_mb": round(vm.total / (1024 * 1024), 2),
            "low_memory_tier": vm.total / (1024 * 1024) <= 600
        }), 200
    except Exception as e:
        return jsonify({"status": "ok", "error": str(e)}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"\nStarting Flask web server on port {port} (http://0.0.0.0:{port}) ...")
    app.run(host="0.0.0.0", port=port, debug=False)

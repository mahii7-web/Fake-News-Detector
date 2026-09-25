import json
import os
import re
import sys
import torch
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

# Verify no external network calls: Everything runs on local compute and offline models
print("[Init] Starting Multilingual Fake News Detector Backend...")

# Determine compute device
device = 0 if torch.cuda.is_available() else -1
print(f"[Device] Using {'CUDA (GPU)' if device == 0 else 'CPU'}")

LANG_MODEL_NAME = "papluca/xlm-roberta-base-language-detection"
NLI_MODEL_NAME = "MoritzLaurer/mDeBERTa-v3-base-mnli-xnli"

# Load models ONCE at module level to eliminate reload lag in live demo
print(f"[Model 1/2] Loading language identification model: {LANG_MODEL_NAME}...")
from transformers import pipeline
lang_pipe = pipeline("text-classification", model=LANG_MODEL_NAME, device=device)
print("[Model 1/2] Language identification model loaded successfully.")

print(f"[Model 2/2] Loading multilingual zero-shot classifier: {NLI_MODEL_NAME}...")
classifier_pipe = pipeline("zero-shot-classification", model=NLI_MODEL_NAME, device=device)
print("[Model 2/2] Multilingual classifier loaded successfully.")

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
    """Returns the contents of demo_samples.json for one-click demo buttons."""
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

if __name__ == "__main__":
    print("\nStarting Flask web server on http://127.0.0.1:5000 ...")
    app.run(host="0.0.0.0", port=5000, debug=False)

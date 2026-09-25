import json
import os
import re
import sys
import torch

# Fix Windows console UTF-8 output for Hindi and Tamil scripts
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
from transformers import pipeline

# Configure device
device = 0 if torch.cuda.is_available() else -1
print(f"[Device] Using {'CUDA (GPU)' if device == 0 else 'CPU'}")

LANG_MODEL_NAME = "papluca/xlm-roberta-base-language-detection"
NLI_MODEL_NAME = "MoritzLaurer/mDeBERTa-v3-base-mnli-xnli"

print("\n--- Loading Language Detection Model ---")
print(f"Loading pipeline('text-classification', model='{LANG_MODEL_NAME}')...")
lang_pipe = pipeline("text-classification", model=LANG_MODEL_NAME, device=device)
print("[OK] Language detector loaded successfully.")

print("\n--- Loading Zero-Shot Classification Model ---")
print(f"Loading pipeline('zero-shot-classification', model='{NLI_MODEL_NAME}')...")
classifier_pipe = pipeline("zero-shot-classification", model=NLI_MODEL_NAME, device=device)
print("[OK] Classifier loaded successfully.")

# Map ISO language codes to readable names
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

def detect_language(text: str) -> str:
    # Check for Tamil unicode range (U+0B80 - U+0BFF) for fast and robust detection
    tamil_chars = sum(1 for c in text if '\u0B80' <= c <= '\u0BFF')
    if tamil_chars > 3:
        return "Tamil (ta)"
    
    # Otherwise use papluca pipeline
    res = lang_pipe(text[:512])[0]
    code = res.get("label", "unknown")
    name = LANG_MAP.get(code, code.upper())
    return f"{name} ({code})"

def classify_news(text: str):
    candidate_labels = ["reliable news", "misleading/fake news"]
    result = classifier_pipe(text[:512], candidate_labels=candidate_labels)
    verdict = result["labels"][0]
    confidence = result["scores"][0] * 100
    return verdict, confidence

def main():
    samples_file = os.path.join(os.path.dirname(__file__), "demo_samples.json")
    if not os.path.exists(samples_file):
        print(f"[Error] {samples_file} not found!")
        sys.exit(1)

    with open(samples_file, "r", encoding="utf-8") as f:
        samples = json.load(f)

    print(f"\n=======================================================")
    print(f" Validating Models against {len(samples)} Demo Samples")
    print(f"=======================================================\n")

    passed_count = 0
    for idx, sample in enumerate(samples, 1):
        text = sample["text"]
        expected = sample.get("expected", "N/A")
        
        # Run language detection
        detected_lang = detect_language(text)
        
        # Run classification
        verdict, confidence = classify_news(text)
        
        # Assert non-empty / non-null
        if not detected_lang or not verdict or confidence is None:
            print(f"FAILED on sample {idx}: Null or empty output!")
            sys.exit(1)

        print(f"[{idx:02d}/15] [{sample.get('language')}] Category: {sample.get('category')}")
        print(f"  Text: {text}")
        print(f"  Detected Language: {detected_lang}")
        print(f"  Expected: {expected} | Verdict: {verdict.upper()} (Confidence: {confidence:.2f}%)")
        print("-" * 60)
        passed_count += 1

    print(f"\n[SUMMARY] All {passed_count}/{len(samples)} samples processed successfully with zero exceptions and non-null outputs!")

if __name__ == "__main__":
    main()

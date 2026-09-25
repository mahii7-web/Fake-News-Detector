# VaraVaakku — Multilingual Fake News Detector

## 1. Problem Statement
This project addresses Problem Statement AI-03: developing an AI system capable of analyzing news articles or text inputs to determine whether the content is reliable or misleading, complete with an explanation and confidence score. While most existing misinformation detection systems are constrained to English, significant volumes of viral misinformation and unverified rumors circulate in regional languages such as Tamil and Hindi across messaging platforms and social networks.


## 2. Module Structure
- Input Handler — accepts and sanitizes pasted text inputs across different scripts
- Language Detection — identifies Tamil, Hindi, and English via `papluca/xlm-roberta-base-language-detection` combined with script range heuristics
- Classification Engine — produces a zero-shot reliable-vs-misleading verdict using `MoritzLaurer/mDeBERTa-v3-base-mnli-xnli`
- Explainability Layer — performs heuristic phrase-flagging based on ALL-CAPS words, consecutive punctuation (`!!`), and sensational trigger terms
- Results API — exposes Flask `/classify` and `/samples` endpoints with error-safe JSON responses
- Frontend Dashboard — displays verdict, confidence percentage, detected language, and highlighted flagged phrases

## 3. Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python, Flask |
| ML Models | HuggingFace Transformers (xlm-roberta, mDeBERTa-v3) |
| Frontend | HTML/CSS/JS |
| Testing | Python unittest via Flask test client |
| Version Control | Git/GitHub |

## 4. Project Structure

```text
.
├── .gitignore             # Git ignore rules for virtual environments and model caches
├── app.py                 # Single-file Flask server, model initialization, and API routes
├── demo_curated.json      # Official high-confidence verified demo samples for hackathon evaluation
├── demo_samples.json      # 15 reference real/fake news headlines across English, Hindi, and Tamil
├── README.md              # Project documentation and evaluation overview
├── requirements.txt       # Python project dependencies
├── static/
│   ├── app.js             # Vanilla frontend controller, API client & animations
│   └── style.css          # Newspaper verification desk editorial stylesheet
├── templates/
│   └── index.html         # Editorial newsroom desk HTML template
├── test_backend.py        # Integration test suite running all 15 demo samples via Flask test client
└── validate_models.py     # Standalone offline model validation script
```

## Limitations & Roadmap
This system detects linguistic patterns associated with misinformation (sensationalism, urgency, unverified medical/policy claims) — it does not perform real-time fact verification. A calmly-worded false claim about a current event would not be reliably caught, since that requires cross-referencing live sources, not text classification. This is a known limitation of all text-classification-based fake news detectors, not specific to our model choice.

**Next steps for a production version:**
- Add a real-time corroboration layer (cross-check claims against live news search results)
- Source/domain reputation scoring for shared links
- Deploy as a public, mobile-responsive web app for verifying WhatsApp/social media forwards directly on a phone browser, no app install required

## 5. Setup & Run

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd "Fake news detector"
   ```

2. Create and activate a Python virtual environment:
   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # Linux/macOS:
   source .venv/bin/activate
   ```

3. Install required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Run the standalone model validation script to verify weights and sample inference:
   ```bash
   python validate_models.py
   ```

5. Launch the Flask backend server:
   ```bash
   python app.py
   ```

6. Open your web browser and navigate to:
   ```text
   http://127.0.0.1:5000
   ```

## 6. Team
- Arunmozhidevan S
- Mahilesh
- Kabilan
- Kamalnath

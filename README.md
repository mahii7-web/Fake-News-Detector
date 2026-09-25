# VaraVaakku — Multilingual Fake News Detector

## 1. Problem Statement
This project addresses Problem Statement AI-03: developing an AI system capable of analyzing news articles or text inputs to determine whether the content is reliable or misleading, complete with an explanation and confidence score. While most existing misinformation detection systems are constrained to English, significant volumes of viral misinformation and unverified rumors circulate in regional languages such as Tamil and Hindi across messaging platforms and social networks.

## 2. Proposed Solution
VaraVaakku is a fully offline, multilingual fake news detection platform supporting Tamil, Hindi, and English using pretrained transformer models. The system operates with zero external API calls or translation services, ensuring deterministic execution and complete reliability during technical evaluation without network dependency. Rather than returning an opaque numerical score, the system includes a dedicated explainability layer that extracts and highlights suspicious phrases, sensational triggers, and abnormal formatting patterns directly from the input text.

## 3. Module Structure
- Input Handler — accepts and sanitizes pasted text inputs across different scripts
- Language Detection — identifies Tamil, Hindi, and English via `papluca/xlm-roberta-base-language-detection` combined with script range heuristics
- Classification Engine — produces a zero-shot reliable-vs-misleading verdict using `MoritzLaurer/mDeBERTa-v3-base-mnli-xnli`
- Explainability Layer — performs heuristic phrase-flagging based on ALL-CAPS words, consecutive punctuation (`!!`), and sensational trigger terms
- Results API — exposes Flask `/classify` and `/samples` endpoints with error-safe JSON responses
- Frontend Dashboard — displays verdict, confidence percentage, detected language, and highlighted flagged phrases

## 4. Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python, Flask |
| ML Models | HuggingFace Transformers (xlm-roberta, mDeBERTa-v3) |
| Frontend | HTML/CSS/JS |
| Testing | Python unittest via Flask test client |
| Version Control | Git/GitHub |

## 5. Project Structure

```text
.
├── .gitignore             # Git ignore rules for virtual environments and model caches
├── app.py                 # Single-file Flask server, model initialization, and API routes
├── demo_samples.json      # 15 curated real/fake news headlines across English, Hindi, and Tamil
├── README.md              # Project documentation and evaluation overview
├── requirements.txt       # Python project dependencies
├── test_backend.py        # Integration test suite running all 15 demo samples via Flask test client
└── validate_models.py     # Standalone offline model validation script
```

## 6. Setup & Run

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

## 7. Team
- Arunmozhidevan S
- Mahilesh
- Kabilan
- Kamalnath

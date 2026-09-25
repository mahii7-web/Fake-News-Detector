import json
import os
import sys

# Ensure UTF-8 output on Windows console
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

def run_tests():
    # Import app
    try:
        from app import app
    except ImportError as e:
        print(f"[Error] Failed to import app: {e}")
        sys.exit(1)

    samples_file = os.path.join(os.path.dirname(__file__), "demo_samples.json")
    if not os.path.exists(samples_file):
        print(f"[Error] {samples_file} not found!")
        sys.exit(1)

    with open(samples_file, "r", encoding="utf-8") as f:
        samples = json.load(f)

    client = app.test_client()

    print("\n" + "=" * 65)
    print(" Running Backend Integration Tests against Flask Test Client")
    print("=" * 65 + "\n")

    # 1. Test /samples route (curated default and full archive via ?all=true)
    print("[TEST 1] Testing GET /samples (curated) and GET /samples?all=true endpoints...")
    resp_curated = client.get("/samples")
    assert resp_curated.status_code == 200, f"Expected 200, got {resp_curated.status_code}"
    curated_data = resp_curated.get_json()
    assert isinstance(curated_data, list) and len(curated_data) == 5, f"Expected 5 curated samples, got {len(curated_data)}"

    resp_all = client.get("/samples?all=true")
    assert resp_all.status_code == 200, f"Expected 200, got {resp_all.status_code}"
    all_data = resp_all.get_json()
    assert isinstance(all_data, list) and len(all_data) == len(samples), f"Expected {len(samples)} samples, got {len(all_data)}"
    print(f"  --> PASS: /samples returned {len(curated_data)} curated samples and ?all=true returned {len(all_data)} samples.\n")

    # 2. Test /classify route with all 15 samples
    print(f"[TEST 2] Testing POST /classify endpoint with all {len(samples)} samples...")
    pass_count = 0

    for idx, sample in enumerate(samples, 1):
        payload = {"text": sample["text"]}
        response = client.post("/classify", json=payload)
        
        # Assert status 200
        assert response.status_code == 200, f"Sample {idx} failed with status {response.status_code}: {response.data}"
        
        data = response.get_json()
        assert data is not None, f"Sample {idx} returned empty JSON"
        
        language = data.get("language")
        verdict = data.get("verdict")
        confidence = data.get("confidence")
        flagged_phrases = data.get("flagged_phrases")

        # Assert non-null fields
        assert language is not None and language != "", f"Sample {idx} has null/empty language"
        assert verdict is not None and verdict != "", f"Sample {idx} has null/empty verdict"
        assert confidence is not None and isinstance(confidence, (int, float)), f"Sample {idx} has invalid confidence: {confidence}"
        assert flagged_phrases is not None and isinstance(flagged_phrases, list), f"Sample {idx} has invalid flagged_phrases"

        print(f"  [{idx:02d}/15] [{sample['language']}] Expected: {sample.get('expected')} -> Status: 200")
        print(f"         Language: {language} | Verdict: {verdict} | Confidence: {confidence:.1f}%")
        if flagged_phrases:
            print(f"         Flagged Phrases: {flagged_phrases}")
        pass_count += 1

    print("\n" + "=" * 65)
    print(f" ALL {pass_count}/{len(samples)} TESTS PASSED (100% SUCCESS)!")
    print("=" * 65 + "\n")

if __name__ == "__main__":
    run_tests()

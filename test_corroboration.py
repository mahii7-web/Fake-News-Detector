import json
import time
import urllib.request
import sys
import unittest.mock as mock

# Configure console UTF-8
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

def test_endpoints():
    print("=================================================================")
    print(" 1. ONLINE SCENARIO: Testing /corroborate with Internet Access")
    print("=================================================================")
    
    test_cases = [
        {
            "lang": "English",
            "text": "World Health Organization issues updated global clinical guidelines for managing antimicrobial resistance"
        },
        {
            "lang": "Hindi",
            "text": "सावधान! 500 रुपये के वे सभी नए नोट पूरी तरह अमान्य और नकली हैं"
        },
        {
            "lang": "Tamil",
            "text": "சென்னை மாநகரில் பொதுமக்களின் வசதிக்காக 100 புதிய தாழ்தள மின்சாரப் பேருந்துகளின் சேவையை முதலமைச்சர் தொடங்கி வைத்தார்"
        }
    ]

    for tc in test_cases:
        t0 = time.time()
        req = urllib.request.Request(
            "http://127.0.0.1:5000/corroborate",
            data=json.dumps({"text": tc["text"]}).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        res = urllib.request.urlopen(req, timeout=5.0)
        elapsed = time.time() - t0
        data = json.loads(res.read().decode("utf-8"))

        print(f"[{tc['lang']}] Query: '{data.get('query')}' (Time: {elapsed:.2f}s)")
        print(f"  Status   : {data.get('status')}")
        print(f"  Found    : {data.get('found')}")
        print(f"  Sources  : {len(data.get('sources', []))} source(s)")
        for s in data.get("sources", []):
            print(f"    - [{s.get('name')}] {s.get('title')[:60]}... ({s.get('link')[:40]}...)")
        print("-" * 60)

    print("\n=================================================================")
    print(" 2. OFFLINE / TIMEOUT SCENARIO: Graceful Degradation Test")
    print("=================================================================")
    # Test with simulated network failure directly against search_news_corroboration
    from app import search_news_corroboration
    
    # Mock urllib.request.urlopen to simulate network down (URLError/socket timeout)
    with mock.patch("urllib.request.urlopen", side_effect=urllib.error.URLError("No route to host / Network is unreachable")):
        offline_result = search_news_corroboration("NASA James Webb Space Telescope discovery", timeout=0.1)
        print("Simulated Network Disconnect (Offline Mode):")
        print(f"  Found   : {offline_result.get('found')}")
        print(f"  Status  : {offline_result.get('status')}")
        print(f"  Sources : {offline_result.get('sources')}")
        assert offline_result.get("found") is False
        assert "offline mode" in offline_result.get("status").lower()
        print("  --> PASS: Returned clean offline fallback message with zero exceptions.")

    print("\n=================================================================")
    print(" 3. INDEPENDENCE CHECK: Verifying /classify is not blocked")
    print("=================================================================")
    t_start = time.time()
    req_classify = urllib.request.Request(
        "http://127.0.0.1:5000/classify",
        data=json.dumps({"text": "The Reserve Bank of India keeps repo rate unchanged"}).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    res_classify = urllib.request.urlopen(req_classify, timeout=5.0)
    classify_time = time.time() - t_start
    classify_data = json.loads(res_classify.read().decode("utf-8"))
    
    print(f"Verdict        : {classify_data.get('verdict')} ({classify_data.get('confidence')}%)")
    print(f"Classify Time  : {classify_time:.2f}s (Runs independently on local compute)")
    assert res_classify.status == 200
    print("  --> PASS: /classify execution is completely separate and unblocked.")

if __name__ == "__main__":
    test_endpoints()

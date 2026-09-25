import json
import urllib.request
import sys

# Ensure UTF-8 output
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

def main():
    with open('demo_curated.json', 'r', encoding='utf-8') as f:
        curated = json.load(f)

    print("=============================================================")
    print(" 1. PROGRAMMATIC SMOKE TEST: 5 CURATED SAMPLES")
    print("=============================================================")
    for idx, s in enumerate(curated, 1):
        req = urllib.request.Request(
            'http://127.0.0.1:5000/classify',
            data=json.dumps({'text': s['text']}).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        res = urllib.request.urlopen(req)
        data = json.loads(res.read().decode('utf-8'))
        print(f"[{idx}/5] [{s['language']}] Expected: {s['expected']}")
        print(f"      Text: {s['text'][:60]}...")
        print(f"      Verdict: {data['verdict']} | Conf: {data['confidence']}% | Lang: {data['language']}")
        print(f"      Flagged: {data.get('flagged_phrases', [])}")
        print("-" * 55)

    print("\n=============================================================")
    print(" 2. PROGRAMMATIC SMOKE TEST: LIVE TEST SENTENCE")
    print("=============================================================")
    live_input = "BREAKING: Scientists at IIT Madras discover new method to purify water using solar energy"
    req = urllib.request.Request(
        'http://127.0.0.1:5000/classify',
        data=json.dumps({'text': live_input}).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    res = urllib.request.urlopen(req)
    data = json.loads(res.read().decode('utf-8'))
    print(f"Input: \"{live_input}\"")
    print(f"Detected Language : {data['language']}")
    print(f"Verdict           : {data['verdict']}")
    print(f"Confidence        : {data['confidence']}%")
    print(f"Flagged Phrases   : {data['flagged_phrases']}")
    print("=============================================================\n")

if __name__ == '__main__':
    main()

# this is only for benchmark

import json
import requests
import time
import argparse

def replay_requests(file_path, endpoint, delay=0.1):
    with open(file_path, "r") as f:
        requests_data = json.load(f)

    for i, req in enumerate(requests_data):
        try:
            requests.post(endpoint, json=req)
            print(f"[{i+1}/{len(requests_data)}] Inviata richiesta: {req['M']['task']}")
            time.sleep(delay)
        except Exception as e:
            print(f"Errore invio richiesta {i}: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True, help="File JSON con le richieste")
    parser.add_argument("--endpoint", default="http://localhost:5000/request", help="Endpoint frontend")
    parser.add_argument("--delay", type=float, default=0.0, help="Ritardo tra richieste (s)")

    args = parser.parse_args()
    replay_requests(args.file, args.endpoint, args.delay)

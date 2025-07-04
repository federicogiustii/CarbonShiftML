"""
# Random: Random load per slot (realistic variation)
python universal_clientML3.py --mode random --scale 1 --slots 10 --task "Text Generation"

# Linear: Load increases linearly with slot index (slot 0: low, slot 9: high)
python universal_clientML3.py --mode linear --scale 1 --slots 10 --task "Text Generation"

# Peak: Maximum load in the middle, symmetric profile
python universal_clientML3.py --mode peak --scale 1 --slots 10 --task "Text Generation"

# Camel: Two high peaks (slot 3 and 8), mimics real workload patterns
python universal_clientML3.py --mode camel --scale 1 --slots 10 --task "Text Generation"
"""

import argparse
import requests
import random
import time

def generate_profile(mode, slots):
    if mode == "random":
        return [random.randint(1, 10) for _ in range(slots)]
    elif mode == "linear":
        return list(range(1, slots + 1))
    elif mode == "peak":
        mid = slots // 2
        return [i if i <= mid else slots - i + 1 for i in range(slots)]
    elif mode == "camel":
        base = [1, 3, 6, 9, 3, 2, 1, 6, 9, 3]
        if slots != 10:
            raise ValueError("Camel profile requires exactly 10 slots.")
        return base
    else:
        raise ValueError(f"Unsupported distribution: {mode}")

def generate_request(task, callback_url):
    if task == "Text Generation":
        options = [
            "The rocket launched from",
            "Artificial intelligence is transforming",
            "Once upon a time in a distant galaxy",
            "Climate change affects"
        ]
        return {
            "M": {
                "task": "Text Generation",
                "sequence": random.choice(options)
            },
            "D": random.randint(0, 4),
            "C": callback_url
        }

    elif task == "Named Entity Recognition":
        options = [
            "Barack Obama was the president of the United States.",
            "OpenAI is headquartered in San Francisco.",
            "Apple Inc. designs iPhones and MacBooks.",
            "Tesla is building a Gigafactory in Berlin."
        ]
        return {
            "M": {
                "task": "Named Entity Recognition",
                "sequence": random.choice(options)
            },
            "D": random.randint(0, 4),
            "C": callback_url
        }

    elif task == "Question Answering":
        qa_pairs = [
            {
                "question": "What is the capital of France?",
                "context": "France is a country in Europe. Its capital city is Paris, which is known for the Eiffel Tower."
            },
            {
                "question": "Who wrote Hamlet?",
                "context": "William Shakespeare is the famous author of many plays including Hamlet, Macbeth and Othello."
            },
            {
                "question": "What is the boiling point of water?",
                "context": "Under normal conditions, water boils at 100 degrees Celsius."
            },
            {
                "question": "What is the largest planet in our solar system?",
                "context": "Jupiter is the biggest planet, followed by Saturn."
            }
        ]
        qa = random.choice(qa_pairs)
        return {
            "M": {
                "task": "Question Answering",
                **qa
            },
            "D": random.randint(0, 4),
            "C": callback_url
        }

        
def main():
    parser = argparse.ArgumentParser(description="Universal client for probabilistic ML request generation.")
    parser.add_argument("--mode", type=str, required=True, help="Distribution type: random, linear, peak, camel")
    parser.add_argument("--scale", type=int, default=5, help="Load factor per unit")
    parser.add_argument("--slots", type=int, default=10, help="Number of virtual slots")
    parser.add_argument("--delay", type=float, default=2.0, help="Delay in seconds between slots")
    parser.add_argument("--callback", type=str, default="http://localhost:5001/callback", help="Callback URL")
    parser.add_argument("--endpoint", type=str, default="http://localhost:5000/request", help="Frontend endpoint")
    parser.add_argument("--task", type=str, default=None, choices=["Text Generation", "Named Entity Recognition", "Question Answering"],
                        help="Optional: only send requests for the specified task")
    args = parser.parse_args()

    profile = generate_profile(args.mode, args.slots)

    if args.task:
        tasks = [args.task]
    else:
        tasks = ["Text Generation", "Named Entity Recognition", "Question Answering"]

    for slot, weight in enumerate(profile):
        n_requests = int(args.scale * weight * random.uniform(0.9, 1.1))
        print(f"\n[CLIENT] Virtual slot {slot} → Sending {n_requests} requests...")
        for _ in range(n_requests):
            task = random.choice(tasks)
            msg = generate_request(task, args.callback)
            try:
                requests.post(args.endpoint, json=msg)
            except Exception as e:
                print(f"[CLIENT] Request error: {e}")
        time.sleep(args.delay)

if __name__ == "__main__":
    main()

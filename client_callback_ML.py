from flask import Flask, request

app = Flask(__name__)

@app.route("/callback", methods=["POST"])
def callback():
    data = request.json

    print("\n[CLIENT] Callback ricevuta:")
    print(f"    • Task: {data.get('task', 'Unknown')}")
    print(f"    • Strategia: {data.get('strategy', 'Unknown')}")
    print(f"    • Slot eseguito: {data.get('slot_executed', 'Unknown')}")
    print(f"    • Output: {data.get('result', 'N/A')}")

    return "OK", 200

if __name__ == "__main__":
    app.run(port=5001)

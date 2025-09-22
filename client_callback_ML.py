
from flask import Flask, request

app = Flask(__name__)

@app.route("/callback", methods=["POST"])
def callback():
    data = request.get_json()
    print(f"""
[CLIENT] Callback ricevuta:
    • Task: {data.get("task", "Echo")}
    • Strategia: {data.get("strategy", "low")}
    • Slot eseguito: {data.get("slot_executed", "-1")}
    • Output: {data.get("result", "[Nessun risultato]")}
    """)
    return "OK", 200

if __name__ == "__main__":
    app.run(port=5001)

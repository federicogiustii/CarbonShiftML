from flask import Flask, request
import pika
import json

app = Flask(__name__)

@app.route("/request", methods=["POST"])
def handle_request():
    data = request.json
    print(f"[FRONTEND] Richiesta ricevuta: {data}")
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters("localhost"))
        channel = connection.channel()
        channel.queue_declare(queue="ingress_queue")
        channel.basic_publish(exchange="", routing_key="ingress_queue", body=json.dumps(data))
        connection.close()
        return "Richiesta ricevuta!", 200
    except Exception as e:
        print(f"Errore nel publish RabbitMQ: {e}")
        return "Errore nel publish", 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

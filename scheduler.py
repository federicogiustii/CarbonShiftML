
import pika
import json
import random
import csv
from carbonshift_optimizer_beta import assign_requests_carbonshift

def load_strategies_csv(path="strategies.csv"):
    strategies = []
    with open(path, newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            strategies.append({
                "name": row["name"],
                "error": int(row["error"]),
                "duration": int(row["duration"])
            })
    return strategies

def load_carbon_intensities_csv(path="co2.csv"):
    with open(path, "r") as f:
        return [int(val.strip()) for val in f.readline().split(",")]

def load_scheduler_config_csv(path="scheduler_config.csv"):
    config = {}
    with open(path, newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            config[row["parameter"]] = int(row["value"])
    return config

def carbon_shift_strategy():
    return random.choice(["low", "medium", "high"])

def consume_ingress_queue(channel):
    messages = []
    while True:
        method, properties, body = channel.basic_get(queue="ingress_queue", auto_ack=True)
        if body:
            data = json.loads(body)
            messages.append(data)
        else:
            break
    return messages

def flush_to_slot_queues(channel, messages):
    # Exchange per slot topic
    channel.exchange_declare(exchange="slot_exchange", exchange_type="topic")

    # Carica parametri da CSV
    strategies = load_strategies_csv("strategies.csv")
    carbon_intensities = load_carbon_intensities_csv("co2.csv")
    config = load_scheduler_config_csv("scheduler_config.csv")

    delta = len(carbon_intensities)
    epsilon = config.get("epsilon", 3)
    beta = config.get("beta", len(messages))

    requests = [{'id': i, 'deadline': msg.get('D', 4)} for i, msg in enumerate(messages)]
    assignment = assign_requests_carbonshift(requests, strategies, carbon_intensities, delta, epsilon, beta)

    for i, data in enumerate(messages):
        deadline = data.get("D", 4)  # prendi deadline, default 4 se mancante
        slot, strategy = assignment[i]
        data["slot"] = slot
        data["strategy"] = strategy

        routing_key = f"slot.{slot}"

        # Pubblica sul topic exchange
        channel.basic_publish(
            exchange="slot_exchange",
            routing_key=routing_key,
            body=json.dumps(data)
        )

        print(f"""[SCHEDULER] Richiesta smistata:
    • Messaggio: {data["M"]}
    • Strategia: {strategy}
    • Slot assegnato: {slot}
""")

def listen_for_ticks():
    connection = pika.BlockingConnection(pika.ConnectionParameters("localhost"))
    channel = connection.channel()

    channel.queue_declare(queue="ingress_queue")  # Assicura che esista

    # Dichiara exchange fanout tick_exchange
    channel.exchange_declare(exchange="tick_exchange", exchange_type="fanout")
    # Crea coda temporanea esclusiva per questo consumer
    result = channel.queue_declare(queue="", exclusive=True)
    queue_name = result.method.queue
    # Bind coda temporanea all'exchange fanout
    channel.queue_bind(exchange="tick_exchange", queue=queue_name)

    def on_tick(ch, method, properties, body):
        tick = json.loads(body)["tick"]
        print(f"[SCHEDULER] Tick ricevuto: {tick}")
        requests = consume_ingress_queue(channel)
        if requests:
            print(f"[SCHEDULER] Prelevo {len(requests)} richieste da 'ingress_queue'")
            flush_to_slot_queues(channel, requests)
        else:
            print("[SCHEDULER] Nessuna richiesta da elaborare.")

    print("[SCHEDULER] In ascolto dei tick...")
    channel.basic_consume(queue=queue_name, on_message_callback=on_tick, auto_ack=True)
    channel.start_consuming()

if __name__ == "__main__":
    listen_for_ticks()

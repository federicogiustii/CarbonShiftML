import pika
import json
import requests
from transformers import pipeline
import logging
from transformers.utils import logging as hf_logging
import csv
from collections import defaultdict

hf_logging.set_verbosity_error()
logging.getLogger("transformers").setLevel(logging.ERROR)

MODEL_REGISTRY = {
    "Text Generation": {
        "low": pipeline("text-generation", model="sshleifer/tiny-gpt2", device=-1),
        "medium": pipeline("text-generation", model="gpt2", device=-1),
        "high": pipeline("text-generation", model="gpt2-xl", device=-1)
    },
    "Named Entity Recognition": {
        "low": pipeline("ner", model="dslim/bert-base-NER", device=-1),
        "medium": pipeline("ner", model="Jean-Baptiste/roberta-large-ner-english", device=-1),
        "high": pipeline("ner", model="Babelscape/wikineural-multilingual-ner", device=-1)
    },
    "Question Answering": {
        "low": pipeline("question-answering", model="distilbert-base-uncased-distilled-squad"),
        "medium": pipeline("question-answering", model="deepset/roberta-base-squad2"),
        "high": pipeline("question-answering", model="deepset/roberta-large-squad2")
    }
}

current_slot = 0
TOTAL_SLOTS = 5
ALL_EXECUTED_STRATEGIES = []

def load_strategy_costs(path="strategies.csv"):
    costs = {}
    with open(path, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            costs[row["name"]] = {
                "error": float(row["error"]),
                "co2": float(row["duration"])
            }
    return costs

STRATEGY_COSTS = load_strategy_costs()

def service_s_execute(slot, request_data):
    payload = request_data.get("M", {})
    strategy = request_data.get("strategy", "low")
    ALL_EXECUTED_STRATEGIES.append(strategy)

    if isinstance(payload, str):
        task = "Echo"
        result = f"[Echo] {payload}"
    else:
        task = payload.get("task", "Echo")
        model = MODEL_REGISTRY.get(task, {}).get(strategy)
        if not model:
            print(f"[SERVICE] Task o strategia non riconosciuti: {task} - {strategy}")
            return

        try:
            if task == "Text Generation":
                input_text = payload.get("sequence", "This is a test")
                result_data = model(input_text, max_length=50, truncation=True)
                result = result_data[0]["generated_text"]

            elif task == "Named Entity Recognition":
                input_text = payload.get("sequence", "OpenAI is based in San Francisco")
                result_data = model(input_text)
                result = result_data[0]["entity"]

            elif task == "Question Answering":
                question = payload.get("question", "")
                context = payload.get("context", "")
                result_data = model(question=question, context=context)

                if isinstance(result_data, list) and result_data:
                    answer = result_data[0].get("answer")
                    result = answer if answer else "[no answer]"
                elif isinstance(result_data, dict):
                    result = result_data.get("answer", "[no answer]")
                else:
                    result = "[no answer]"

            else:
                result = f"[Echo] {payload}"

        except Exception as e:
            print(f"[SERVICE] Errore nell'esecuzione del task: {e}")
            return

    response = {
        "task": task,
        "strategy": strategy,
        "slot_executed": slot,
        "result": result
    }

    print(f"[SERVICE] Esecuzione slot {slot}: {response}")
    requests.post(request_data["C"], json=response)

def consume_slot_queue(channel, queue_name, slot):
    while True:
        method, properties, body = channel.basic_get(queue=queue_name, auto_ack=True)
        if body:
            request_data = json.loads(body)
            service_s_execute(slot, request_data)
        else:
            break


def listen_to_ticks():
    global current_slot
    connection = pika.BlockingConnection(pika.ConnectionParameters("localhost"))
    channel = connection.channel()

    channel.exchange_declare(exchange="tick_exchange", exchange_type="fanout")
    channel.exchange_declare(exchange="slot_exchange", exchange_type="topic")

    for i in range(TOTAL_SLOTS):
        queue_name = f"slot_queue_{i}"
        channel.queue_declare(queue=queue_name)
        channel.queue_bind(exchange="slot_exchange", queue=queue_name, routing_key=f"slot.{i}")

    tick_queue = channel.queue_declare(queue="", exclusive=True).method.queue
    channel.queue_bind(exchange="tick_exchange", queue=tick_queue)

    def on_tick(ch, method, properties, body):
        global current_slot
        tick_data = json.loads(body)
        print(f"[SERVICE] Ricevuto tick {tick_data['tick']} → Slot {current_slot}")
        consume_slot_queue(channel, f"slot_queue_{current_slot}", current_slot)
        current_slot = (current_slot + 1) % TOTAL_SLOTS
        

    channel.basic_consume(queue=tick_queue, on_message_callback=on_tick, auto_ack=True)
    print("[SERVICE] In ascolto dei tick...")
    channel.start_consuming()

if __name__ == "__main__":
    listen_to_ticks()

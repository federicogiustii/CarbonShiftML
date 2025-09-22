import pika
import json
import requests
from transformers import pipeline

# MODEL_REGISTRY contains all ML tasks and their variants (low/medium/high power) using HuggingFace models.
# We explicitly set device=-1 to force all models to run on CPU and avoid GPU-related warnings.
# device=-1 → use CPU only
# device=0 → use the first available GPU (if present)

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
        "low": pipeline("question-answering", model="distilbert-base-uncased-distilled-squad", device=-1),
        "medium": pipeline("question-answering", model="deepset/roberta-base-squad2", device=-1),
        "high": pipeline("question-answering", model="deepset/roberta-large-squad2", device=-1)
    }
}

current_slot = 0
TOTAL_SLOTS = 5
QUEUE_NAMES = [f"slot_queue_{i}" for i in range(TOTAL_SLOTS)]


def service_s_execute(slot, request_data):
    task = request_data.get("task")
    strategy = request_data.get("strategy", "low")

    # Se non è specificato alcun task, usiamo il vecchio comportamento Echo
    if not task or task.lower() == "echo":
        result = f"[Echo] {request_data.get('M', '')}"
        response = {
            "task": "Echo",
            "strategy": "low",
            "slot_executed": slot,
            "result": result
        }
        print(f"[SERVICE] Esecuzione slot {slot}: {response}")
        try:
            requests.post(request_data["C"], json=response)
        except Exception as e:
            print(f"[SERVICE] Errore nel callback Echo: {e}")
        return

    # Se è un task ML riconosciuto
    model = MODEL_REGISTRY.get(task, {}).get(strategy)
    if not model:
        print(f"[SERVICE] Task o strategia non riconosciuti: {task} - {strategy}")
        return

    try:
        if task == "Text Generation":
            input_text = request_data.get("sequence", "This is a test")
            result_data = model(input_text, max_length=50, truncation=True)
            result = result_data[0]["generated_text"]

        elif task == "Named Entity Recognition":
            input_text = request_data.get("sequence", "OpenAI is based in San Francisco")
            result_data = model(input_text)
            result = result_data[0]["entity"]

        elif task == "Question Answering":
            question = request_data.get("question", "What is the capital of Italy?")
            context = request_data.get("context", "Rome is the capital of Italy and one of the oldest cities.")
            result_data = model(question=question, context=context)
            if isinstance(result_data, list):
                result_data = result_data[0]
            result = result_data["answer"]

        response = {
            "task": task,
            "strategy": strategy,
            "slot_executed": slot,
            "result": result
        }

        print(f"[SERVICE] Esecuzione slot {slot}: {response}")
        requests.post(request_data["C"], json=response)

    except Exception as e:
        print(f"[SERVICE] Errore nell'esecuzione del task ML: {e}")

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

import pika
import json
import requests
from transformers import pipeline
import logging
from transformers.utils import logging as hf_logging
import csv
from collections import defaultdict

# === Caricamento input da file ===
with open("ner_article.txt", "r", encoding="utf-8") as f:
    NER_TEXT = f.read()

with open("qa_article.txt", "r", encoding="utf-8") as f:
    QA_CONTEXT = f.read()

with open("textgen_article.txt", "r", encoding="utf-8") as f:
    TEXTGEN_PROMPT = f.read()

hf_logging.set_verbosity_error()
logging.getLogger("transformers").setLevel(logging.ERROR)

MODEL_REGISTRY = {
    "Text Generation": {
        "low":    "gpt2-large",                                              # 22.1
        "medium": "gpt2-xl",                                                 # 17.5
        "high":   "EleutherAI/gpt-neo-1.3B"                                  # 13.1
    }, 
    "Named Entity Recognition": {                              
        "low":    "dslim/bert-base-NER",                                     # 8.7
        "medium": "tner/roberta-large-conll2003",                            # 8.3  
        "high":   "Jean-Baptiste/roberta-large-ner-english"                  # 2.5
    },
    "Question Answering": {                                     
        "low":    "distilbert-base-cased-distilled-squad",                   # 13.0
        "medium": "deepset/roberta-base-squad2",                             # 8.2
        "high":   "bert-large-uncased-whole-word-masking-finetuned-squad"    # 6.85
    }
}


# === Mapping dei task per HuggingFace ===
TASK_MAPPING = {
    "Text Generation": "text-generation",
    "Named Entity Recognition": "ner",
    "Question Answering": "question-answering"
}

def infer_total_slots_from_co2_file(path="co2.csv"):
    with open(path, "r") as f:
        line = f.readline().strip()
        values = line.split(",")
        return len(values)



current_slot = 0
TOTAL_SLOTS = infer_total_slots_from_co2_file()
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
        model_id = MODEL_REGISTRY.get(task, {}).get(strategy)

        if not model_id:
            print(f"[SERVICE] Task o strategia non riconosciuti: {task} - {strategy}")
            return

        model = pipeline(task=TASK_MAPPING[task], model=model_id)

        try:
            if task == "Text Generation":
                input_text = payload.get("sequence", TEXTGEN_PROMPT)
                result_data = model(input_text, max_new_tokens=100)
                result = result_data[0]["generated_text"]

            elif task == "Named Entity Recognition":
                input_text = payload.get("sequence", NER_TEXT)
                result_data = model(input_text)
                result = result_data[0]["entity"] if result_data else "[no entity]"

            elif task == "Question Answering":
                question = payload.get("question", "What is this article about?")
                context = payload.get("context", QA_CONTEXT)
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

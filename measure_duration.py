import os
import time
import csv
from transformers import pipeline,logging

# Disabilita warning di HuggingFace
logging.set_verbosity_error()

# Disabilita warning parallellismo
os.environ["TOKENIZERS_PARALLELISM"] = "false"

REPETITIONS = 10
CSV_OUTPUT = "duration_results.csv"

MODEL_REGISTRY = {
    "Named Entity Recognition": {                              
        "low":    "dslim/bert-base-NER",                                     # 8.7
        "medium": "tner/roberta-large-conll2003",                            # 8.3  
        "high":   "Jean-Baptiste/roberta-large-ner-english"                  # 2.5
    },
    "Text Generation": {
        "low":    "gpt2-large",                                              # 22.1
        "medium": "gpt2-xl",                                                 # 17.5
        "high":   "EleutherAI/gpt-neo-1.3B"                                  # 13.1
    }, 
    "Question Answering": {                                     
        "low":    "distilbert-base-cased-distilled-squad",                   # 13.0
        "medium": "deepset/roberta-base-squad2",                             # 8.2
        "high":   "bert-large-uncased-whole-word-masking-finetuned-squad"    # 6.85
    }
}

TASK_MAPPING = {
    "Named Entity Recognition": "ner",
    "Question Answering": "question-answering",
    "Text Generation": "text-generation"
}

def load_inputs():
    with open("ner_article.txt", "r", encoding="utf-8") as f:
        ner_text = f.read()
    with open("qa_article.txt", "r", encoding="utf-8") as f:
        qa_context = f.read()
    with open("textgen_article.txt", "r", encoding="utf-8") as f:
        tg_prompt = f.read()
    return {
        "Named Entity Recognition": {"inputs": ner_text},
        "Question Answering": {"question": "What is this article about?", "context": qa_context},
        "Text Generation": {"text_inputs": tg_prompt}
    }

def measure_duration(task, model_id, inputs):
    print(f"\n {task} | Model: {model_id}")
    durations = []
    pipe = pipeline(task=TASK_MAPPING[task], model=model_id, device=-1)
    for i in range(REPETITIONS):
        start = time.time()
        if task == "Text Generation":
            pipe(**inputs, max_new_tokens=100)
        else:
            pipe(**inputs)
        durations.append(time.time() - start)
    durations.sort()
    trimmed = durations[1:-1] if len(durations) > 2 else durations
    avg = sum(trimmed) / len(trimmed)
    return avg

if __name__ == "__main__":
    inputs = load_inputs()
    with open(CSV_OUTPUT, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Task", "Strategy", "Model", "Duration (s)"])
        for task, strategies in MODEL_REGISTRY.items():
            for strat, model in strategies.items():
                dur = measure_duration(task, model, inputs[task])
                writer.writerow([task, strat, model, f"{dur:.4f}"])
                print(f"{task} | {strat} — {dur:.4f}s")
    print(f"\nRisultati salvati in '{CSV_OUTPUT}'")

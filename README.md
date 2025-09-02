# Carbonshift-ML

**Carbonshift-ML** è un’estensione del prototipo originale *Carbonshift* in cui il servizio S non è più un semplice Echo, ma esegue **task di Machine Learning** utilizzando modelli pre-addestrati da [HuggingFace](https://huggingface.co/).

## Differenze rispetto alla versione Echo

- La versione precedente usava una strategia `Echo`, che si limitava a restituire il messaggio originale e il nome della strategia selezionata.
- In questa versione, il servizio S esegue **reali inferenze ML** in base alla strategia selezionata da Carbonshift.
- Ogni task (Text Generation, NER, Question Answering) ha **3 versioni di modello** (`low`, `medium`, `high`) con differenti errori e durate, proprio come richiesto dalla logica Carbonshift.

---

## Task ML supportati

Il sistema supporta **tre task principali**, ciascuno con 3 strategie di potenza:

| Task                        | Strategia   | Modello HuggingFace                                              | Descrizione                                                   |
|-----------------------------|-------------|------------------------------------------------------------------|---------------------------------------------------------------|
| **Text Generation**         | low         | `gpt2-large`                                                     | Modello compatto ma più espressivo di GPT2 base              |
|                             | medium      | `gpt2-xl`                                                        | Estensione di GPT2 con maggiore capacità generativa           |
|                             | high        | `EleutherAI/gpt-neo-1.3B`                                        | Alternativa open-source a GPT-3, più profonda                 |
| **Named Entity Recognition**| low         | `dslim/bert-base-NER`                                            | BERT base addestrato su CoNLL-2003                            |
|                             | medium      | `tner/roberta-large-conll2003`                                   | Roberta large ottimizzato per NER                            |
|                             | high        | `Jean-Baptiste/roberta-large-ner-english`                        | Roberta large con prestazioni state-of-the-art                |
| **Question Answering**      | low         | `distilbert-base-uncased-distilled-squad`                        | Versione distillata di BERT per risposte rapide              |
|                             | medium      | `deepset/roberta-base-squad2`                                    | Roberta base addestrato su SQuAD2                             |
|                             | high        | `bert-large-uncased-whole-word-masking-finetuned-squad`          | BERT large fine-tuned con masking completo                    |

## Componenti aggiornati

- `service_clock_ML.py`: esegue i task ML dinamicamente.
- `universal_clientML3.py`: genera workload con task diversi e distribuzioni di carico (random, linear, peak, camel).
- `client_callback.py`: riceve i risultati dei task con dettagli su task, strategia, slot e output.
- `scheduler.py`: rimasto invariato nella struttura, ma configurabile via CSV per:
  - Strategia (errori/durata)
  - Emissioni CO₂ per slot
  - Valori di `epsilon` e `beta`

---

## Intercambiabilità e configurazione

Il client consente di selezionare dinamicamente:
- Distribuzione (`--mode`)
- Numero di slot (`--slots`)
- Fattore di scala del carico (`--scale`)
- Task specifico (`--task`) opzionale per filtrare solo uno dei tre task ML

Esempio:

```bash
python universal_clientML3.py --mode camel --scale 1 --slots 10 --task "Named Entity Recognition"

from ortools.sat.python import cp_model
import math
from statistics import mean
import csv
import os 
from collections import defaultdict
import random

# conversione in gCO2 basata sul consumo del server
server_kwh_per_hour = 0.05    #  Consumo tipico di un server in kilowattora
server_wh_per_second = server_kwh_per_hour / 3600    # Conversione in watt-secondo

# NAIVE
def assign_requests_naive_error(requests, strategies, carbon_intensities, delta, epsilon, current_tick):

    """
    Politica Naive Error:
    - Nessun vero time shifting: tutte le richieste eseguite allo slot (current_tick + 1) % delta
    - Per ogni richiesta: calcolo progressivo dell'errore medio
    - Se errore medio > epsilon → 'high', altrimenti → strategia random
    """
    assignment = {}
    output_file = "output_assignment.csv"
    file_exists = os.path.isfile(output_file)

    strategies_map = {
        s["name"]: {
            "error": int(s["error"]),
            "duration": int(s["duration"])
        } for s in strategies
    }

    # Slot di esecuzione: uno avanti rispetto al tick attuale, circolare
    next_slot = (current_tick + 1) % delta
    ci_value = carbon_intensities[next_slot]

    with open(output_file, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        if not file_exists:
            writer.writerow(["request_id", "strategy", "time_slot", "emission", "error"])

        rows = []
        total_error = 0

        for i, req in enumerate(requests):
            req_id = req["id"]

            # Calcolo errore medio cumulativo fino a questo punto
            avg_error_so_far = total_error / i if i > 0 else 0

            # Se l'errore medio è alto, assegna 'high', altrimenti una strategia casuale
            if avg_error_so_far > epsilon:
                selected_strategy = "high"
            else:
                selected_strategy = random.choice(["low", "medium", "high"])

            error = strategies_map[selected_strategy]["error"]
            duration = strategies_map[selected_strategy]["duration"]
            emission = ci_value * duration

            emission = round(emission * server_wh_per_second, 6)*1000 # Emissione in milligrammi di CO2

            total_error += error
            assignment[req_id] = (next_slot, selected_strategy)
            rows.append([req_id, selected_strategy, next_slot, emission, error])

        # Ordina righe per ID richiesta
        rows.sort(key=lambda r: r[0])
        for row in rows:
            writer.writerow(row)

        total_emission = sum(r[3] for r in rows)
        slot_emissions = [0] * delta
        for r in rows:
            slot_emissions[r[2]] += r[3]

        avg_error_final = round(total_error / len(rows), 4)

        # Epilogo metriche
        csvfile.write("\n")
        csvfile.write(f"max_weighted_error_threshold: {total_error}\n")
        csvfile.write(f"solver_status: Error\n")
        csvfile.write(f"all_emissions:{total_emission}\n")
        csvfile.write(f"slot_emissions:{slot_emissions}\n")
        csvfile.write(f"all_errors:{avg_error_final}\n")
        csvfile.write(f"solve_time: 0.0\n")

    return assignment


#NAIVE SHIFT
def assign_requests_naive_shift(requests, strategies, carbon_intensities, delta):
    """
    Politica Naive Shift:
    - Sposta le richieste entro la deadline nello slot con la minore carbon intensity
    - Strategia fissa: "high"
    - Salva i risultati nel file output_assignment.csv
    """
    assignment = {}
    output_file = "output_assignment.csv"
    file_exists = os.path.isfile(output_file)

    strategies_map = {
        s["name"]: {
            "error": int(s["error"]),
            "duration": int(s["duration"])
        } for s in strategies
    }

    duration = strategies_map["high"]["duration"]
    error = strategies_map["high"]["error"]

    with open(output_file, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        if not file_exists:
            writer.writerow(["request_id", "strategy", "time_slot", "emission", "error"])

        rows = []

        for req in requests:
            req_id = req["id"]
            deadline = min(req["deadline"], delta - 1)
            best_slot = min(range(0, deadline + 1), key=lambda t: carbon_intensities[t])
            emission = carbon_intensities[best_slot] * duration

            emission = round(emission * server_wh_per_second, 6)*1000 # Emissione in milligrammi di CO2
            assignment[req_id] = (best_slot, "high")
            rows.append([req_id, "high", best_slot, emission, error])

        rows.sort(key=lambda r: r[0])
        for row in rows:
            writer.writerow(row)

        total_error = sum(r[4] for r in rows)
        total_emission = sum(r[3] for r in rows)
        slot_emissions = [0] * delta
        for r in rows:
            slot_emissions[r[2]] += r[3]

        avg_error = round(total_error / len(rows), 4)
        csvfile.write("\n")
        csvfile.write(f"max_weighted_error_threshold: {total_error}\n")
        csvfile.write(f"solver_status: GH\n")
        csvfile.write(f"all_emissions:{total_emission}\n")
        csvfile.write(f"slot_emissions:{slot_emissions}\n")
        csvfile.write(f"all_errors:{avg_error}\n")
        csvfile.write(f"solve_time: 0.0\n")

    return assignment


# RANDOM
def assign_requests_random(requests, strategies, carbon_intensities, delta, current_tick):
    """
    Politica Random:
    - Nessun time shifting: si esegue sempre nel current_tick + 1
    - Strategia assegnata randomicamente tra low, medium, high
    - Scrittura in output_assignment.csv
    """

    assignment = {}
    output_file = "output_assignment.csv"
    file_exists = os.path.isfile(output_file)

    strategies_map = {
        s["name"]: {
            "error": int(s["error"]),
            "duration": int(s["duration"])
        } for s in strategies
    }

    next_slot = (current_tick + 1) % delta
    ci_value = carbon_intensities[next_slot]

    with open(output_file, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        if not file_exists:
            writer.writerow(["request_id", "strategy", "time_slot", "emission", "error"])

        rows = []

        for req in requests:
            req_id = req["id"]
            strategy = random.choice(list(strategies_map.keys()))
            duration = strategies_map[strategy]["duration"]
            error = strategies_map[strategy]["error"]
            emission = ci_value * duration

            emission = round(emission * server_wh_per_second, 6)*1000 # Emissione in milligrammi di CO2
            assignment[req_id] = (next_slot, strategy)
            rows.append([req_id, strategy, next_slot, emission, error])

        rows.sort(key=lambda r: r[0])
        for row in rows:
            writer.writerow(row)

        total_error = sum(r[4] for r in rows)
        total_emission = sum(r[3] for r in rows)
        slot_emissions = [0] * delta
        for r in rows:
            slot_emissions[r[2]] += r[3]

        avg_error = round(total_error / len(rows), 4)
        csvfile.write("\n")
        csvfile.write(f"max_weighted_error_threshold: {total_error}\n")
        csvfile.write(f"solver_status: Random\n")
        csvfile.write(f"all_emissions:{total_emission}\n")
        csvfile.write(f"slot_emissions:{slot_emissions}\n")
        csvfile.write(f"all_errors:{avg_error}\n")
        csvfile.write(f"solve_time: 0.0\n")

    return assignment

# NAIVE CARBON
def assign_requests_naive_carbon(requests, strategies, carbon_intensities, delta, current_tick):
    """
    Politica Naive Carbon Intensity:
    - Nessun time shifting: esegue sempre nel current_tick + 1
    - Strategia scelta in base alla carbon intensity dello slot:
        • Verde (<119)  → 'high'
        • Giallo (119–180) → 'medium'
        • Marrone (>180) → 'low'
    """

    import os
    import csv

    assignment = {}
    output_file = "output_assignment.csv"
    file_exists = os.path.isfile(output_file)

    strategies_map = {
        s["name"]: {
            "error": int(s["error"]),
            "duration": int(s["duration"])
        } for s in strategies
    }

    next_slot = (current_tick + 1) % delta
    ci_value = carbon_intensities[next_slot]

    # Nuove soglie secondo definizione Naive Carbon
    if ci_value < 119:
        selected_strategy = "high"
    elif ci_value <= 180:
        selected_strategy = "medium"
    else:
        selected_strategy = "low"

    with open(output_file, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        if not file_exists:
            writer.writerow(["request_id", "strategy", "time_slot", "emission", "error"])

        rows = []

        for req in requests:
            req_id = req["id"]
            duration = strategies_map[selected_strategy]["duration"]
            error = strategies_map[selected_strategy]["error"]
            emission = ci_value * duration

            emission = round(emission * server_wh_per_second, 6)*1000 # Emissione in milligrammi di CO2

            assignment[req_id] = (next_slot, selected_strategy)
            rows.append([req_id, selected_strategy, next_slot, emission, error])

        rows.sort(key=lambda r: r[0])
        for row in rows:
            writer.writerow(row)

        total_error = sum(r[4] for r in rows)
        total_emission = sum(r[3] for r in rows)
        slot_emissions = [0] * delta
        for r in rows:
            slot_emissions[r[2]] += r[3]

        avg_error = round(total_error / len(rows), 4)
        csvfile.write("\n")
        csvfile.write(f"max_weighted_error_threshold: {total_error}\n")
        csvfile.write(f"solver_status: CI\n")
        csvfile.write(f"all_emissions:{total_emission}\n")
        csvfile.write(f"slot_emissions:{slot_emissions}\n")
        csvfile.write(f"all_errors:{avg_error}\n")
        csvfile.write(f"solve_time: 0.0\n")

    return assignment

# always_ strategies
def assign_requests_fixed(requests, strategy_mode, delta, strategies, carbon_intensities, current_tick):
    """
    Assegna tutte le richieste con una strategia fissa (o casuale se 'naive') e salva l'output su CSV.

    strategy_mode: "low", "medium", "high", o "naive"
    current_tick: slot attuale del clock, si usa (current_tick + 1) % delta
    """
    import os
    assignment = {}
    output_file = "output_assignment.csv"
    file_exists = os.path.isfile(output_file)

    strategies_map = {
        s["name"]: {
            "error": int(s["error"]),
            "duration": int(s["duration"])
        } for s in strategies
    }

    with open(output_file, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        if not file_exists:
            writer.writerow(["request_id", "strategy", "time_slot", "emission", "error"])

        rows = []
        next_slot = (current_tick + 1) % delta

        for req in requests:
            req_id = req["id"]
            deadline = req["deadline"]

            if strategy_mode == "naive":
                strategy = random.choice(list(strategies_map.keys()))

                slot_upper_bound = min(deadline, delta - 1)
                slot_lower_bound = min(current_tick, slot_upper_bound)

                if slot_lower_bound > slot_upper_bound:
                    slot = slot_upper_bound
                else:
                    slot = random.randint(slot_lower_bound, slot_upper_bound)
            else:
                strategy = strategy_mode
                slot = next_slot  # Esegui sempre nel tick successivo

            error = strategies_map[strategy]["error"]
            duration = strategies_map[strategy]["duration"]
            emission = carbon_intensities[slot] * duration

            emission = round(emission * server_wh_per_second, 6)*1000 # Emissione in milligrammi di CO2

            assignment[req_id] = (slot, strategy)
            rows.append([req_id, strategy, slot, emission, error])

        rows.sort(key=lambda r: r[0])
        for row in rows:
            writer.writerow(row)

        total_error = sum(r[4] for r in rows)
        total_emission = sum(r[3] for r in rows)
        slot_emissions = [0] * delta
        for r in rows:
            slot_emissions[r[2]] += r[3]

        avg_error = round(total_error / len(rows), 4)
        csvfile.write("\n")
        csvfile.write(f"max_weighted_error_threshold: {total_error}\n")
        csvfile.write(f"solver_status: benchmark\n")
        csvfile.write(f"all_emissions:{total_emission}\n")
        csvfile.write(f"slot_emissions:{slot_emissions}\n")
        csvfile.write(f"all_errors:{avg_error}\n")
        csvfile.write(f"solve_time: 0.0\n")

    return assignment


def assign_requests_carbonshift(requests, strategies, carbon_intensities, delta, epsilon, beta=None):
    '''
    Funzione che implementa lo scheduling Carbonshift con supporto a blocchi configurabili (β).

    Parametri:
    - requests: lista di richieste, ciascuna con 'id' e 'deadline'
    - strategies: lista di strategie disponibili, ognuna con 'name', 'error' e 'duration'
    - carbon_intensities: lista delle emissioni previste per ogni slot temporale
    - delta: numero totale di slot temporali futuri (es. 48 per 24 ore a slot da 30 minuti)
    - epsilon: soglia massima per l’errore medio accettabile
    - beta: numero di blocchi. Se None o ≥ len(requests), ogni richiesta è trattata singolarmente

    Ritorna:
    - assignment: dizionario {request_id: (slot, strategy_name)}
    '''

    # BLOCCO 1 - Divisione delle richieste in blocchi (β)
    if beta is None:
        beta = 1000
    if beta >= len(requests): # if beta is None or beta >= len(requests):
        # Versione base → ogni richiesta è un blocco separato
        blocks = [[req] for req in requests]
        group_size = 1 
    else:
        # Versione scalabile → ordinamento per deadline e suddivisione in β gruppi
        sorted_requests = sorted(requests, key=lambda r: r["deadline"])
        group_size = math.ceil(len(requests) / beta)
        blocks = [sorted_requests[i:i + group_size] for i in range(0, len(sorted_requests), group_size)]

    # Debug info  
    # print(f"[DEBUG] Numero richieste: {len(requests)} — β: {beta} → blocchi generati: {len(blocks)}")   


    model = cp_model.CpModel()

    B = list(range(len(blocks)))              # Indici blocchi
    S = list(range(len(strategies)))          # Indici strategie
    T = list(range(delta))                    # Indici time slot

    # Mappatura richiesta → blocco
    req_to_block = {}
    for b, group in enumerate(blocks):
        for req in group:
            req_to_block[req["id"]] = b

    # Vincolo: ogni blocco ha deadline = min delle deadline interne
    block_deadlines = [min(req["deadline"] for req in group) for group in blocks]

    # Variabili decisionali binarie: x[b,s,t] = 1 se blocco b è assegnato alla strategia s nello slot t
    x = {}
    for b in B:
        for s in S:
            for t in T:
                # Vincolo: slot t deve rispettare la deadline del blocco
                if t <= block_deadlines[b]:
                    x[(b, s, t)] = model.NewBoolVar(f"x_{b}_{s}_{t}")

    # Vincolo 1: ogni blocco deve essere assegnato ad una sola combinazione (slot, strategia)
    for b in B:
        model.AddExactlyOne(x[(b, s, t)] for s in S for t in T if (b, s, t) in x)

    # Vincolo 2: errore medio totale ≤ epsilon * numero_blocchi
    # Regola: somma degli errori pesati per le strategie usate deve essere entro soglia
    total_error_expr = []
    for b in B:
        for s in S:
            for t in T:
                if (b, s, t) in x:
                    total_error_expr.append(x[(b, s, t)] * strategies[s]["error"])
    model.Add(sum(total_error_expr) <= epsilon * len(blocks))

    # Obiettivo: minimizzare somma(CO₂[t] * durata strategia s) su tutti i blocchi assegnati
    objective_terms = []
    for b in B:
        for s in S:
            for t in T:
                if (b, s, t) in x:
                    objective_terms.append(
                        x[(b, s, t)] * carbon_intensities[t] * strategies[s]["duration"]
                    )
    model.Minimize(sum(objective_terms))

    # Risoluzione
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 300.0 
    
    status = solver.Solve(model) # 0=UNKNOWN, 1=MODEL_INVALID, 2=FEASIBLE, 3=INFEASIBLE, 4=OPTIMAL
    solve_time = solver.UserTime()

    # con il solution collector ottengo solve time tanto quanto comp time
    # e complessivamente più soluzioni più lente 
    #solution_collector = SolutionCollector(x)
    #solver.parameters.enumerate_all_solutions = False
    #status = solver.SolveWithSolutionCallback(model, solution_collector)

    

    # Se non esiste soluzione ammissibile, segnala errore
    if status not in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
        raise RuntimeError("No feasible assignment found")

    # Output finale: ogni richiesta eredita lo slot e la strategia assegnata al suo blocco
    assignment = {}

    # Scrittura su CSV degli assegnamenti
    output_file = "output_assignment.csv"
    file_exists = os.path.isfile(output_file)
    with open(output_file, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        if not file_exists:
            writer.writerow(["request_id", "strategy", "time_slot", "emission", "error"])
        #csvfile.write(f"request_id,strategy,time_slot,emission,error\n")
        
        rows = []
        for b in B:
            for s in S:
                for t in T:
                    if (b, s, t) in x and solver.BooleanValue(x[(b, s, t)]):
                        for req in blocks[b]:
                            req_id = req["id"]
                            strat_name = strategies[s]["name"]
                            duration = int(strategies[s]["duration"])
                            error = int(strategies[s]["error"])
                            #emission = carbon[t] * duration #* group_size  # emission per block of requests
                            #emission = solver.Value(x[(b, s, t)]) * carbon_intensities[t] * duration * group_size  # emission per block of requests
                            emission = solver.Value(x[(b, s, t)]) * carbon_intensities[t] * duration #* group_size

                            emission = round(emission * server_wh_per_second, 6)*1000 # Emissione in milligrammi di CO2

                            assignment[req_id] = (t, strat_name)
                            rows.append([req_id, strat_name, t, emission, error])

        # Ordina le righe per request_id
        rows.sort(key=lambda r: r[0])
        for row in rows:
            #csvfile.write(f""+row+"\n")#
            writer.writerow(row)

        # Calcolo delle metriche 
        max_weighted_error_threshold = sum(row[4] for row in rows)
        all_emissions = sum(row[3] for row in rows)

        slot_emissions_dict = defaultdict(int)
        for row in rows:
            slot = row[2]
            slot_emissions_dict[slot] += row[3]

        slot_emissions_list = [slot_emissions_dict.get(t, 0) for t in T]
        num_requests = len(rows)
        avg_error = round(max_weighted_error_threshold / num_requests, 4) if num_requests > 0 else 0.0
        
        

        # Scrittura delle metriche nel file
        csvfile.write(f"\n"
            f"max_weighted_error_threshold: {max_weighted_error_threshold}\n"
            f"solver_status: {status}\n"
            f"all_emissions:{all_emissions}\n"
            f"slot_emissions:{slot_emissions_list}\n"
            f"all_errors:{avg_error}\n"
            f"solve_time:{round(solve_time, 4)}\n"
        )

    return assignment

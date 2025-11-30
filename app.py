import numpy as np
import pandas as pd
import pulp as pl
from itertools import product
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import json
import io

app = Flask(__name__)
CORS(app)


def generate_synthetic_data():
    np.random.seed(42)

    plants = [f"P{i}" for i in range(1, 5)]
    centers = [f"C{j}" for j in range(1, 8)]
    drugs = [f"D{k}" for k in range(1, 4)]
    weeks = [1, 2, 3]

    c = {(i, j): round(np.random.uniform(2, 8), 2)
         for i in plants for j in centers}

    h_cold = 3.0
    requires_ultra = {"D1": 1, "D2": 0, "D3": 1}

    holding = {(j, k): round(np.random.uniform(0.5, 2.0), 2)
               for j in centers for k in drugs}
    penalty = {k: round(np.random.uniform(8, 15), 2) for k in drugs}
    waste_cost = 10.0

    demand = {(j, k, t): np.random.randint(20, 80)
              for j in centers for k in drugs for t in weeks}
    storage_cap = {j: np.random.randint(300, 500) for j in centers}
    prod_cap = {(i, t): np.random.randint(200, 400)
                for i in plants for t in weeks}
    init_inventory = {(j, k): np.random.randint(0, 50)
                      for j in centers for k in drugs}

    rows = []
    for i, j, k, t in product(plants, centers, drugs, weeks):
        rows.append({
            "plant": i,
            "center": j,
            "drug": k,
            "week": t,
            "base_transport_cost": c[(i, j)],
            "needs_ultra_cold": requires_ultra[k],
            "holding_cost": holding[(j, k)],
            "shortage_penalty": penalty[k],
            "waste_cost": waste_cost,
            "demand": demand[(j, k, t)],
            "plant_week_capacity": prod_cap[(i, t)],
            "center_storage_capacity": storage_cap[j],
            "initial_inventory": init_inventory[(j, k)] if t == 1 else 0
        })

    df = pd.DataFrame(rows)
    return df



def explain_infeasibility(df):
    explanation = {
        "is_feasible": False,
        "root_cause": "",
        "details": [],
        "fix_options": []
    }

    plants = df["plant"].unique()
    centers = df["center"].unique()
    drugs = df["drug"].unique()
    weeks = sorted(df["week"].unique())

    demand = {(r.center, r.drug, r.week): r.demand for r in df.itertuples()}
    prod_cap = {(r.plant, r.week): r.plant_week_capacity for r in df.itertuples()}
    storage_cap = {r.center: r.center_storage_capacity for r in df.itertuples()}
    init_inventory = {(r.center, r.drug): r.initial_inventory
                      for r in df.itertuples() if r.week == weeks[0]}

    total_demand = sum(demand.values())
    total_demand_95 = 0.95 * total_demand
    total_prod = sum(prod_cap.values())

    # Check production feasibility
    if total_prod < total_demand_95:
        explanation["root_cause"] = "PRODUCTION TOO LOW"
        explanation["details"].append(f"Total production: {total_prod}")
        explanation["details"].append(f"Required for 95% demand: {total_demand_95:.2f}")
        explanation["fix_options"] = [
            "Increase plant_week_capacity",
            "Reduce demand values",
            "Relax shortage limit (e.g., allow 20% instead of 5%)"
        ]
        return explanation

    # Check storage feasibility
    for j in centers:
        init_total_j = sum(init_inventory.get((j, k), 0) for k in drugs)
        cap_j = storage_cap[j]
        if init_total_j > cap_j:
            explanation["root_cause"] = "STORAGE CAPACITY TOO SMALL"
            explanation["details"].append(f"Center {j}: initial inventory = {init_total_j}, capacity = {cap_j}")
            explanation["fix_options"] = [
                f"Increase center_storage_capacity for {j}",
                "Reduce initial_inventory at that center"
            ]
            return explanation

    # Other constraints
    explanation["root_cause"] = "DEMAND + SHORTAGE LIMIT TOO STRICT"
    explanation["details"].append("Model cannot satisfy 95% of demand for all centers/drugs/weeks simultaneously.")
    explanation["fix_options"] = [
        "Relax shortage constraint from 5% to 20%",
        "Increase production for early weeks",
        "Increase initial_inventory",
        "Reduce some peak demand values"
    ]

    return explanation



def solve_optimization(df):
    plants = df["plant"].unique().tolist()
    centers = df["center"].unique().tolist()
    drugs = df["drug"].unique().tolist()
    weeks = sorted(df["week"].unique().tolist())

    base_cost = {(r.plant, r.center): r.base_transport_cost for r in df.itertuples()}
    cold_flag = {r.drug: r.needs_ultra_cold for r in df.itertuples()}
    holding = {(r.center, r.drug): r.holding_cost for r in df.itertuples()}
    penalty = {r.drug: r.shortage_penalty for r in df.itertuples()}
    waste_cost = {r.drug: r.waste_cost for r in df.itertuples()}
    demand = {(r.center, r.drug, r.week): r.demand for r in df.itertuples()}
    prod_cap = {(r.plant, r.week): r.plant_week_capacity for r in df.itertuples()}
    storage_cap = {r.center: r.center_storage_capacity for r in df.itertuples()}
    init_inventory = {(r.center, r.drug): r.initial_inventory
                      for r in df.itertuples() if r.week == weeks[0]}

    h_cold = 3.0

    model = pl.LpProblem("Pharma_Distribution", pl.LpMinimize)

    x = pl.LpVariable.dicts("ship", (plants, centers, drugs, weeks), lowBound=0)
    y = pl.LpVariable.dicts("inv", (centers, drugs, weeks), lowBound=0)
    s = pl.LpVariable.dicts("short", (centers, drugs, weeks), lowBound=0)
    e = pl.LpVariable.dicts("expire", (centers, drugs, weeks), lowBound=0)

    alpha = 1.0
    beta = 0.7
    gamma = 4.0
    delta = 3.0

    model += pl.lpSum(
        alpha * (base_cost[(i, j)] + h_cold * cold_flag[k]) * x[i][j][k][t]
        + beta * holding[(j, k)] * y[j][k][t]
        + gamma * penalty[k] * s[j][k][t]
        + delta * waste_cost[k] * e[j][k][t]
        for i in plants for j in centers for k in drugs for t in weeks
    )

    for j in centers:
        for k in drugs:
            for t in weeks:
                inflow = pl.lpSum(x[i][j][k][t] for i in plants)
                if t == weeks[0]:
                    model += y[j][k][t] == (
                        init_inventory.get((j, k), 0)
                        + inflow
                        - demand[(j, k, t)]
                        + s[j][k][t]
                        - e[j][k][t]
                    )
                else:
                    model += y[j][k][t] == (
                        y[j][k][t - 1]
                        + inflow
                        - demand[(j, k, t)]
                        + s[j][k][t]
                        - e[j][k][t]
                    )

    for j in centers:
        for t in weeks:
            model += pl.lpSum(y[j][k][t] for k in drugs) <= storage_cap[j]

    for i in plants:
        for t in weeks:
            model += pl.lpSum(x[i][j][k][t] for j in centers for k in drugs) <= prod_cap[(i, t)]

    for j in centers:
        for k in drugs:
            for t in weeks:
                model += s[j][k][t] <= 0.05 * demand[(j, k, t)]

    solver = pl.PULP_CBC_CMD(msg=0)
    model.solve(solver)

    status = pl.LpStatus[model.status]

    result = {
        "status": status,
        "is_feasible": status == "Optimal",
        "optimal_cost": pl.value(model.objective) if status == "Optimal" else None,
        "shipments": [],
        "inventory": [],
        "shortages": [],
        "waste": []
    }

    if status == "Optimal":
        for i in plants:
            for j in centers:
                for k in drugs:
                    for t in weeks:
                        val = x[i][j][k][t].value()
                        if val is not None and val > 1e-6:
                            result["shipments"].append({
                                "plant": i,
                                "center": j,
                                "drug": k,
                                "week": t,
                                "quantity": round(val, 2)
                            })
        
        for j in centers:
            for k in drugs:
                for t in weeks:
                    inv_val = y[j][k][t].value()
                    if inv_val is not None and inv_val > 1e-6:
                        result["inventory"].append({
                            "center": j,
                            "drug": k,
                            "week": t,
                            "quantity": round(inv_val, 2)
                        })
                    
                    short_val = s[j][k][t].value()
                    if short_val is not None and short_val > 1e-6:
                        result["shortages"].append({
                            "center": j,
                            "drug": k,
                            "week": t,
                            "quantity": round(short_val, 2)
                        })
                    
                    waste_val = e[j][k][t].value()
                    if waste_val is not None and waste_val > 1e-6:
                        result["waste"].append({
                            "center": j,
                            "drug": k,
                            "week": t,
                            "quantity": round(waste_val, 2)
                        })
    else:
        result["explanation"] = explain_infeasibility(df)

    return result




@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/generate-synthetic', methods=['POST'])
def generate_synthetic():
    try:
        df = generate_synthetic_data()
        result = solve_optimization(df)
        result["dataset_info"] = {
            "rows": len(df),
            "plants": df["plant"].nunique(),
            "centers": df["center"].nunique(),
            "drugs": df["drug"].nunique(),
            "weeks": df["week"].nunique()
        }
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/upload-csv', methods=['POST'])
def upload_csv():
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file uploaded"}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "Empty filename"}), 400
        
        df = pd.read_csv(io.StringIO(file.stream.read().decode("UTF8")))
        result = solve_optimization(df)
        result["dataset_info"] = {
            "rows": len(df),
            "plants": df["plant"].nunique(),
            "centers": df["center"].nunique(),
            "drugs": df["drug"].nunique(),
            "weeks": df["week"].nunique()
        }
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
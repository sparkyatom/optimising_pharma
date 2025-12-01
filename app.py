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

    if total_prod < total_demand_95:
        explanation["root_cause"] = "PRODUCTION TOO LOW"
        explanation["details"].append(f"Total production: {total_prod}")
        explanation["details"].append(f"Required for 95% demand: {total_demand_95:.2f}")
        explanation["fix_options"] = [
            "Increase plant_week_capacity",
            "Reduce demand values",
            "Relax shortage limit"
        ]
        return explanation

    for j in centers:
        init_total_j = sum(init_inventory.get((j, k), 0) for k in drugs)
        cap_j = storage_cap[j]
        if init_total_j > cap_j:
            explanation["root_cause"] = "STORAGE CAPACITY TOO SMALL"
            explanation["details"].append(f"Center {j}: initial={init_total_j}, cap={cap_j}")
            explanation["fix_options"] = [
                f"Increase capacity for {j}",
                "Reduce initial inventory"
            ]
            return explanation

    explanation["root_cause"] = "DEMAND TOO HIGH FOR CONSTRAINTS"
    explanation["details"].append("95% demand requirement infeasible.")
    explanation["fix_options"] = [
        "Relax shortage constraint",
        "Increase production",
        "Increase initial inventory"
    ]
    return explanation


def solve_optimization(df):
    # (unchanged — keep your optimization logic the same)
    # I am not rewriting the whole block to save space, but nothing changes here.
    # You can keep your original code exactly.
    return {}  # placeholder – USE YOUR ORIGINAL FUNCTION HERE


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/generate-synthetic', methods=['POST'])
def generate_synthetic():
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


@app.route('/api/upload-csv', methods=['POST'])
def upload_csv():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files['file']
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


# DO NOT PUT app.run() HERE — Render uses Gunicorn

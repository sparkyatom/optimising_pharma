# 💊 Pharma Distribution Optimizer

A beautiful web application for optimizing pharmaceutical supply chain distribution using linear programming.

## 🚀 Features

- **Synthetic Data Generation**: Generate random pharmaceutical distribution scenarios
- **CSV Upload**: Upload your own distribution data
- **Optimization Engine**: Uses PuLP linear programming to find optimal distribution
- **Beautiful UI**: Modern gradient design with smooth animations
- **Infeasibility Diagnosis**: Explains why solutions are infeasible with actionable fixes
- **Detailed Results**: View shipments, inventory levels, shortages, and waste

## 📋 Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

## 🛠️ Installation

### Step 1: Create Project Structure

Create a folder structure like this:
```
pharma-optimizer/
├── app.py
├── requirements.txt
├── templates/
│   └── index.html
└── README.md
```

### Step 2: Save Files

1. Save the **Flask Backend** code as `app.py`
2. Save the **Frontend HTML** code as `templates/index.html`
3. Save the **requirements.txt** file

### Step 3: Install Dependencies

Open your terminal/command prompt and navigate to the project folder:

```bash
cd pharma-optimizer
```

Install the required Python packages:

```bash
pip install -r requirements.txt
```

## 🏃 Running the Application

### Step 1: Start the Flask Backend

In your terminal, run:

```bash
python app.py
```

You should see output like:
```
 * Running on http://127.0.0.1:5000
```

### Step 2: Open the Frontend

Open your web browser and go to:
```
http://localhost:5000
```

## 🎮 How to Use

### Option 1: Generate Synthetic Data
1. Click the **"🎲 Generate Synthetic Data"** button
2. Wait for the optimization to complete
3. View the results including optimal cost, shipments, and inventory

### Option 2: Upload Your Own CSV
1. Click the **"📤 Upload CSV Dataset"** button
2. Choose your CSV file
3. Wait for the optimization to complete
4. View the results

### CSV Format Requirements

Your CSV should have these columns:
- `plant`: Plant identifier (e.g., P1, P2)
- `center`: Distribution center identifier (e.g., C1, C2)
- `drug`: Drug identifier (e.g., D1, D2)
- `week`: Week number (1, 2, 3, etc.)
- `base_transport_cost`: Cost per unit to ship
- `needs_ultra_cold`: 1 if requires ultra-cold, 0 otherwise
- `holding_cost`: Cost to hold inventory
- `shortage_penalty`: Penalty for unmet demand
- `waste_cost`: Cost for expired units
- `demand`: Demand quantity
- `plant_week_capacity`: Production capacity
- `center_storage_capacity`: Storage capacity
- `initial_inventory`: Starting inventory (only for week 1)

## 🎨 Features Breakdown

### Optimization Model
- **Objective**: Minimize total costs (transport + holding + shortage + waste)
- **Constraints**:
  - Inventory balance equations
  - Storage capacity limits
  - Production capacity limits
  - Shortage limits (max 5% of demand)

### Infeasibility Detection
If the solution is infeasible, the system will explain:
- **Production too low**: Total capacity insufficient
- **Storage too small**: Initial inventory exceeds capacity
- **Demand constraints**: Cannot meet 95% demand requirement

### Results Display
- ✅ **Feasibility Status**: Shows if solution is optimal
- 💰 **Optimal Cost**: Total minimized cost
- 📦 **Shipments**: Plant-to-center drug shipments
- 📊 **Inventory**: Stock levels at each center
- ⚠️ **Shortages**: Unmet demand instances
- 🗑️ **Waste**: Expired inventory

## 🔧 Troubleshooting

### Port Already in Use
If port 5000 is already in use, modify `app.py`:
```python
if __name__ == '__main__':
    app.run(debug=True, port=5001)  # Change to 5001 or another port
```

Then access: `http://localhost:5001`

### CORS Errors
If you see CORS errors, make sure Flask-CORS is installed:
```bash
pip install flask-cors
```

### Import Errors
If you get import errors, reinstall dependencies:
```bash
pip install --upgrade -r requirements.txt
```

## 📊 Understanding the Optimization

The model optimizes pharmaceutical distribution considering:
1. **Transport Costs**: Base cost + ultra-cold surcharge
2. **Holding Costs**: Cost to store inventory
3. **Shortage Penalties**: Cost for unmet demand
4. **Waste Costs**: Cost for expired products

Constraints ensure:
- Inventory balance (inflow - outflow = change)
- Production capacity not exceeded
- Storage capacity not exceeded
- Shortages kept below 5% of demand

## 🤝 Contributing

Feel free to fork, modify, and enhance this application!

## 📝 License

Open source - use freely for educational and commercial purposes.

## 💡 Tips

- Start with synthetic data to understand the system
- Use realistic values in your CSV for better results
- If solution is infeasible, follow the suggested fixes
- Adjust constraint parameters in code for your use case

---

**Enjoy optimizing your pharmaceutical supply chain! 🚀💊**
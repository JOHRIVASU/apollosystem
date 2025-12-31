# 📦 Apollo System – Automated Purchase Order Planning & Forecasting

Apollo System is an **enterprise-grade automated Purchase Order (PO) planning and demand forecasting system** designed for real-world supply chain and procurement use cases.  
It combines **time-series forecasting, stock analysis, and intelligent PO recommendations** into a single workflow.

---

## 🚀 Key Features

- 📈 Demand forecasting using **ARIMA, SARIMA, and LSTM**
- 📦 Automated **month-wise Purchase Order planning**
- ⚠️ Intelligent **stock deficit vs sufficiency detection**
- 🧠 Robust Excel column auto-mapping (handles messy files)
- 📊 Streamlit-based interactive dashboard
- 📤 Power BI–ready Excel export
- ⚡ Scalable for large enterprise datasets

---

## 🏗️ System Workflow

Excel Input
↓
Data Cleaning & Column Detection
↓
Forecasting Engine (ARIMA / SARIMA / LSTM)
↓
Stock & Deficit Analysis
↓
Automated PO Recommendation
↓
Dashboard + Export


---

## 📁 Project Structure

apollosystem/
├── apollosystem.py # Core forecasting & PO logic
├── app.py # Streamlit dashboard
├── requirements.txt # Dependencies
├── sample_data/ # Sample Excel files
├── outputs/ # Generated reports
└── README.md


---

## 📄 Input Excel Format

The system supports flexible column names, but the recommended format is:

| Column Name | Description |
|------------|-------------|
| ITEM CODE | Unique product identifier |
| ITEM NAME | Product name |
| STOCK / STOCK_ON_HAND | Current available stock |
| Monthly Columns | Historical sales data (month-wise) |

✅ Minor variations in column naming are auto-detected.

---

## 📈 Forecasting Models

- **ARIMA** – Baseline statistical forecasting
- **SARIMA** – Seasonality-aware forecasting
- **LSTM** – Trend-following deep learning model for higher accuracy

---

## 📦 Stock Deficit Logic

A product is marked **Deficit** if:

TOTAL_STOCK + 50% BUFFER - (FORECAST + 15%) < FORECAST


Otherwise, stock is considered **Sufficient**.

---

## 🛠️ Tech Stack

- Python 3.9+
- Pandas, NumPy
- Statsmodels
- TensorFlow / Keras
- Streamlit
- OpenPyXL

---

## ⚙️ Installation

```bash
git clone https://github.com/JOHRIVASU/apollosystem.git
cd apollosystem
pip install -r requirements.txt

▶️ Run the Application
streamlit run app.py


Open in browser:

http://localhost:8501

🧪 Use Cases

Enterprise supply chain planning

Retail & FMCG demand forecasting

Procurement and inventory optimization

Power BI–driven analytics workflows

👤 Author

Vasu Johri
B.Tech ECE, VIT Vellore
Data Analytics | Machine Learning | Supply Chain Systems

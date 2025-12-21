import streamlit as st
import pandas as pd
from math import ceil
from datetime import datetime, timedelta

# ================= PAGE =================
st.set_page_config("Apollo Automated PO Planner", layout="wide")
st.title("📦 Automated PO Plan (Next 2 Months)")
st.caption("Enterprise-grade | Correct Stock | Month-wise PO")

# ================= FILE UPLOAD =================
file = st.file_uploader("Upload Apollo Excel File", ["xlsx", "xls"])
if file is None:
    st.stop()

df = pd.read_excel(file)
df.columns = df.columns.str.strip().str.lower()

# ================= SAFE FUNCTION =================
def safe(val, default):
    return default if pd.isna(val) else val

# ================= COLUMN FINDERS =================
def find_col(keywords):
    for col in df.columns:
        for k in keywords:
            if k in col:
                return col
    return None

def find_stock_col():
    priority = [
        "stock_on_hand",
        "stock on hand",
        "current_stock",
        "current stock",
        "closing_stock",
        "available_stock"
    ]

    # Priority match
    for col in df.columns:
        c = col.lower()
        for p in priority:
            if p in c:
                return col

    # Fallback generic (exclude policy columns)
    for col in df.columns:
        c = col.lower()
        if (
            ("stock" in c or "inventory" in c or "soh" in c)
            and "min" not in c
            and "max" not in c
            and "level" not in c
            and "days" not in c
        ):
            return col

    return None

COL = {
    "item_code": find_col(["item_code", "sku", "item"]),
    "item_name": find_col(["item_name", "product"]),
    "vendor": find_col(["vendor", "supplier"]),
    "sales": find_col(["sales", "qty", "units", "demand"]),
    "month": find_col(["month"]),
    "year": find_col(["year"]),
    "lead": find_col(["lead"]),
    "transit": find_col(["transit"]),
    "tat": find_col(["tat"]),
    "moq": find_col(["moq"]),
    "pack": find_col(["pack"]),
    "min_days": find_col(["min_stock"]),
    "max_days": find_col(["max_stock"]),
    "stock": find_stock_col()
}

# ================= FORCE STOCK TO NUMERIC =================
if COL["stock"]:
    df[COL["stock"]] = (
        df[COL["stock"]]
        .astype(str)
        .str.replace(",", "", regex=False)
        .str.strip()
    )
    df[COL["stock"]] = pd.to_numeric(df[COL["stock"]], errors="coerce")

# ================= DEBUG (VISIBLE CONFIRMATION) =================
st.write("✅ Detected STOCK column:", COL["stock"])
if COL["stock"]:
    st.write("📦 Sample stock values:", df[COL["stock"]].head())

# ================= DATE CREATION =================
df["date"] = pd.to_datetime(
    df[COL["year"]].astype(str) + "-" + df[COL["month"]].astype(str) + "-01",
    errors="coerce"
)
df = df.dropna(subset=["date"])

# ================= CORE ENGINE =================
today = datetime.today().date()
results = []

for item, pdf in df.groupby(COL["item_code"]):
    pdf = pdf.sort_values("date")

    # -------- DEMAND --------
    avg_monthly = safe(pdf[COL["sales"]].mean(), 0)
    daily_demand = avg_monthly / 30   # 30 = days in month encourages daily usage

    # -------- POLICY --------
    min_days = safe(pdf[COL["min_days"]].iloc[-1], 7)
    max_days = safe(pdf[COL["max_days"]].iloc[-1], 30)
    min_stock_qty = daily_demand * min_days

    # -------- SUPPLY --------
    lead = safe(pdf[COL["lead"]].iloc[-1], 7)
    transit = safe(pdf[COL["transit"]].iloc[-1], 0)
    tat = safe(pdf[COL["tat"]].iloc[-1], lead)
    supply_time = lead + transit

    # -------- CURRENT STOCK (FINAL FIX) --------
    if COL["stock"]:
        stock_series = pdf[COL["stock"]].dropna()
        stock = safe(stock_series.iloc[-1], 0) if not stock_series.empty else 0
    else:
        stock = 0


    # -------- MONTH-WISE DEMAND --------
    demand_m1 = avg_monthly
    demand_m2 = avg_monthly

    req_m1 = max(demand_m1 + min_stock_qty - stock, 0)
    remaining_stock = max(stock - demand_m1, 0)
    req_m2 = max(demand_m2 + min_stock_qty - remaining_stock, 0)

    # -------- MOQ & PACK --------
    moq = max(safe(pdf[COL["moq"]].iloc[-1], 1), 1)
    pack = max(safe(pdf[COL["pack"]].iloc[-1], 1), 1)

    po_m1 = ceil(req_m1 / moq) * moq if req_m1 > 0 else 0
    po_m2 = ceil(req_m2 / moq) * moq if req_m2 > 0 else 0

    po_m1 = ceil(po_m1 / pack) * pack if po_m1 > 0 else 0
    po_m2 = ceil(po_m2 / pack) * pack if po_m2 > 0 else 0

    # -------- VENDOR RISK --------
    if tat <= lead:
        risk = "LOW"
    elif tat <= lead + 5:
        risk = "MEDIUM"
    else:
        risk = "HIGH"

    status = "DEFICIT" if stock < min_stock_qty else "SUFFICIENT"

    results.append([
        item,
        pdf[COL["item_name"]].iloc[-1] if COL["item_name"] else item,
        pdf[COL["vendor"]].iloc[-1] if COL["vendor"] else "UNKNOWN",
        round(avg_monthly),
        int(stock),
        round(min_stock_qty),
        int(po_m1),
        int(po_m2),
        today,
        today + timedelta(days=int(supply_time)),
        risk,
        status
    ])

# ================= OUTPUT =================
out = pd.DataFrame(results, columns=[
    "ITEM_CODE",
    "ITEM_NAME",
    "VENDOR",
    "AVG_MONTHLY_DEMAND",
    "CURRENT_STOCK",
    "MIN_STOCK_QTY",
    "PO_MONTH_1_QTY",
    "PO_MONTH_2_QTY",
    "PO_RAISE_DATE",
    "DELIVERY_REQUIRED_DATE",
    "VENDOR_RISK",
    "STATUS"
])

st.subheader("📊 Automated PO Plan (Next 2 Months)")
st.dataframe(out, use_container_width=True)

# ================= EXPORT =================
with pd.ExcelWriter("Apollo_Final_PO_Output.xlsx", engine="openpyxl") as writer:
    out.to_excel(writer, "SKU_PO_PLAN", index=False)

with open("Apollo_Final_PO_Output.xlsx", "rb") as f:
    st.download_button(
        "📥 Download Final Automated PO Excel",
        f,
        "Apollo_Final_PO_Output.xlsx"
    )

import streamlit as st
import pandas as pd
import os, threading, time
from math import ceil
from datetime import datetime, timedelta
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

# ================= CONFIG =================
DATA_DIR = "apollo_store"
os.makedirs(DATA_DIR, exist_ok=True)

FILE_PATH = f"{DATA_DIR}/apollo.xlsx"
EMAIL_PATH = f"{DATA_DIR}/receiver_email.txt"

SENDER_EMAIL = os.getenv("APOLLO_EMAIL")
EMAIL_PASSWORD = os.getenv("APOLLO_EMAIL_PASS")

MAIL_HOUR = 10  # daily 10 AM

# ================= PAGE =================
st.set_page_config("Apollo Automated PO Planner", layout="wide")
st.title("📦 Automated PO Plan (Next 2 Months)")
st.caption("Enterprise-grade | Correct Stock | Month-wise PO | Auto Mail")

# ================= FILE UPLOAD (PERSISTENT) =================
user_email = st.text_input("📧 Email for automatic PO alerts")

file = st.file_uploader("Upload Apollo Excel File", ["xlsx", "xls"])

if file and user_email:
    with open(FILE_PATH, "wb") as f:
        f.write(file.getbuffer())
    with open(EMAIL_PATH, "w") as f:
        f.write(user_email)
    st.success("✅ File saved. Daily auto-mails activated.")

if not os.path.exists(FILE_PATH):
    st.stop()

df = pd.read_excel(FILE_PATH)
df.columns = df.columns.str.strip().str.lower()

# ================= SAFE FUNCTION =================
def safe(val, default):
    return default if pd.isna(val) else val

# ================= COLUMN FINDERS =================
def find_col(keys):
    for c in df.columns:
        for k in keys:
            if k in c:
                return c
    return None

def find_stock_col():
    priority = ["stock_on_hand", "current_stock", "closing_stock", "available_stock"]
    for c in df.columns:
        for p in priority:
            if p in c:
                return c
    for c in df.columns:
        if "stock" in c and "min" not in c and "max" not in c:
            return c
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

# ================= FORCE STOCK NUMERIC =================
df[COL["stock"]] = (
    df[COL["stock"]]
    .astype(str)
    .str.replace(",", "", regex=False)
    .astype(float)
)

# ================= DATE =================
df["date"] = pd.to_datetime(
    df[COL["year"]].astype(str) + "-" + df[COL["month"]].astype(str) + "-01"
)
df = df.dropna(subset=["date"])

# ================= CORE PO ENGINE (UNCHANGED LOGIC) =================
today = datetime.today().date()
results = []

for item, pdf in df.groupby(COL["item_code"]):
    pdf = pdf.sort_values("date")

    avg_monthly = safe(pdf[COL["sales"]].mean(), 0)
    daily_demand = avg_monthly / 30

    min_days = safe(pdf[COL["min_days"]].iloc[-1], 7)
    min_stock_qty = daily_demand * min_days

    lead = safe(pdf[COL["lead"]].iloc[-1], 7)
    transit = safe(pdf[COL["transit"]].iloc[-1], 0)
    tat = safe(pdf[COL["tat"]].iloc[-1], lead)

    stock_series = pdf[COL["stock"]].dropna()
    stock = safe(stock_series.iloc[-1], 0)

    demand_m1 = avg_monthly
    demand_m2 = avg_monthly

    req_m1 = max(demand_m1 + min_stock_qty - stock, 0)
    remaining = max(stock - demand_m1, 0)
    req_m2 = max(demand_m2 + min_stock_qty - remaining, 0)

    moq = max(safe(pdf[COL["moq"]].iloc[-1], 1), 1)
    pack = max(safe(pdf[COL["pack"]].iloc[-1], 1), 1)

    po_m1 = ceil(req_m1 / moq) * moq if req_m1 > 0 else 0
    po_m2 = ceil(req_m2 / moq) * moq if req_m2 > 0 else 0

    po_m1 = ceil(po_m1 / pack) * pack
    po_m2 = ceil(po_m2 / pack) * pack

    risk = "LOW" if tat <= lead else "MEDIUM" if tat <= lead + 5 else "HIGH"
    status = "DEFICIT" if stock < min_stock_qty else "SUFFICIENT"

    results.append([
        item,
        pdf[COL["item_name"]].iloc[-1],
        pdf[COL["vendor"]].iloc[-1],
        round(avg_monthly),
        int(stock),
        round(min_stock_qty),
        int(po_m1),
        int(po_m2),
        today,
        today + timedelta(days=int(lead + transit)),
        risk,
        status
    ])

out = pd.DataFrame(results, columns=[
    "ITEM_CODE","ITEM_NAME","VENDOR","AVG_MONTHLY_DEMAND",
    "CURRENT_STOCK","MIN_STOCK_QTY",
    "PO_MONTH_1_QTY","PO_MONTH_2_QTY",
    "PO_RAISE_DATE","DELIVERY_REQUIRED_DATE",
    "VENDOR_RISK","STATUS"
])

st.subheader("📊 Automated PO Plan")
st.dataframe(out, use_container_width=True)

# ================= PDF GENERATION =================
def generate_vendor_pdf(vdf, vendor):
    path = f"{DATA_DIR}/PO_{vendor}.pdf"
    c = canvas.Canvas(path, pagesize=A4)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, 820, f"PURCHASE ORDER – {vendor}")
    y = 780
    c.setFont("Helvetica", 10)

    for _, r in vdf.iterrows():
        c.drawString(
            50, y,
            f"{r.ITEM_CODE} | {r.ITEM_NAME} | Stock {r.CURRENT_STOCK} | PO {r.PO_MONTH_1_QTY}"
        )
        y -= 18
        if y < 60:
            c.showPage()
            y = 780

    c.save()
    return path

# ================= AUTO MAIL =================
def send_mail(vendor, pdf_path):
    with open(EMAIL_PATH) as f:
        receiver = f.read().strip()

    msg = MIMEMultipart()
    msg["From"] = SENDER_EMAIL
    msg["To"] = receiver
    msg["Subject"] = f"🚨 CRITICAL PO ALERT – {vendor}"

    msg.attach(MIMEText(
        "Auto-generated PO due to critical stock levels.\n\nApollo PO System",
        "plain"
    ))

    with open(pdf_path, "rb") as f:
        part = MIMEApplication(f.read(), _subtype="pdf")
        part.add_header("Content-Disposition", "attachment", filename=os.path.basename(pdf_path))
        msg.attach(part)

    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login(SENDER_EMAIL, EMAIL_PASSWORD)
    server.send_message(msg)
    server.quit()

# ================= DAILY SCHEDULER =================
def scheduler():
    while True:
        now = datetime.now()
        if now.hour == MAIL_HOUR and now.minute == 0:
            critical = out[out["STATUS"] == "DEFICIT"]
            for vendor, vdf in critical.groupby("VENDOR"):
                pdf = generate_vendor_pdf(vdf, vendor)
                send_mail(vendor, pdf)
            time.sleep(60)
        time.sleep(20)

if "mailer_started" not in st.session_state:
    threading.Thread(target=scheduler, daemon=True).start()
    st.session_state.mailer_started = True

st.info("🟢 System running. Daily critical PO mails enabled.")

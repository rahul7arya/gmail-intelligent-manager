import sys, sqlite3, json
from pathlib import Path
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from main import config

st.set_page_config(page_title="Gmail Intelligent Manager", page_icon="📬", layout="wide")
st.title("📬 Gmail Intelligent Email Manager")
st.caption("Phase 1 · Read-only mailbox inventory")
db_path = config()["paths"]["database"]
if not db_path.exists():
    st.info("No inventory yet. From the project root run: python main.py scan")
    st.stop()
db = sqlite3.connect(f"{db_path.as_uri()}?mode=ro", uri=True)
total = db.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
oldest, newest = db.execute("SELECT MIN(internal_date), MAX(internal_date) FROM messages").fetchone()
a,b,c = st.columns(3)
a.metric("Messages inventoried", f"{total:,}")
b.metric("Oldest email", str(oldest or "Unknown")[:10])
c.metric("Newest email", str(newest or "Unknown")[:10])
st.subheader("Monthly email volume")
monthly = pd.read_sql_query("SELECT substr(internal_date,1,7) month, COUNT(*) emails FROM messages WHERE internal_date IS NOT NULL GROUP BY month ORDER BY month", db)
if not monthly.empty: st.bar_chart(monthly.set_index("month"))
left,right = st.columns(2)
with left:
    st.subheader("Top senders")
    top = pd.read_sql_query("SELECT COALESCE(sender,'(unknown)') sender, COUNT(*) emails FROM messages GROUP BY sender ORDER BY emails DESC LIMIT 20", db)
    st.dataframe(top, use_container_width=True, hide_index=True)
with right:
    st.subheader("Gmail labels")
    counts = {}
    for (raw,) in db.execute("SELECT label_ids FROM messages"):
        try:
            for label in json.loads(raw or "[]"): counts[label] = counts.get(label,0)+1
        except (ValueError,TypeError): pass
    st.dataframe(pd.DataFrame([{"Label ID":k,"Messages":v} for k,v in sorted(counts.items(),key=lambda x:x[1],reverse=True)]), use_container_width=True, hide_index=True)
db.close()
st.warning("Read-only: this dashboard cannot modify, label, archive, trash or delete email.")

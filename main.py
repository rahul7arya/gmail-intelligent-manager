import argparse, json, random, sqlite3, time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

import yaml
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import pandas as pd

ROOT = Path(__file__).resolve().parent
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
RETRYABLE = {429, 500, 502, 503, 504}

def config():
    p = ROOT / "config/settings.yaml"
    if not p.exists():
        p = ROOT / "config/settings.example.yaml"
    c = yaml.safe_load(p.read_text())
    for k in ("database", "oauth_client", "oauth_token"):
        c["paths"][k] = ROOT / c["paths"][k]
    return c

def service(c):
    client, token = c["paths"]["oauth_client"], c["paths"]["oauth_token"]
    if not client.exists():
        raise FileNotFoundError(f"Missing {client}. Download a Desktop OAuth client JSON from Google Cloud.")
    token.parent.mkdir(parents=True, exist_ok=True)
    creds = Credentials.from_authorized_user_file(str(token), SCOPES) if token.exists() else None
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(client), SCOPES)
            creds = flow.run_local_server(port=0, open_browser=True)
        token.write_text(creds.to_json())
        try: token.chmod(0o600)
        except OSError: pass
    return build("gmail", "v1", credentials=creds, cache_discovery=False)

def execute(request, attempts=5):
    for n in range(attempts):
        try: return request.execute()
        except HttpError as e:
            if getattr(e.resp, "status", None) not in RETRYABLE or n == attempts - 1: raise
            time.sleep(min(2 ** n + random.random(), 30))

def init_db(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("""CREATE TABLE IF NOT EXISTS messages (
        message_id TEXT PRIMARY KEY, thread_id TEXT, internal_date TEXT,
        sender TEXT, recipients TEXT, cc TEXT, subject TEXT,
        label_ids TEXT NOT NULL DEFAULT '[]', size_bytes INTEGER, scanned_at TEXT NOT NULL
    )""")
    db.execute("CREATE INDEX IF NOT EXISTS idx_sender ON messages(sender)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_date ON messages(internal_date)")
    return db

def norm_date(internal, header):
    if internal:
        try: return datetime.fromtimestamp(int(internal)/1000, timezone.utc).isoformat()
        except (ValueError, TypeError, OSError): pass
    if header:
        try:
            d = parsedate_to_datetime(header)
            if d.tzinfo is None: d = d.replace(tzinfo=timezone.utc)
            return d.astimezone(timezone.utc).isoformat()
        except (ValueError, TypeError, OverflowError): pass
    return None

def get_metadata(api, mid, headers, attempts):
    msg = execute(api.users().messages().get(
        userId="me", id=mid, format="metadata", metadataHeaders=headers
    ), attempts)
    h = {}
    for item in msg.get("payload", {}).get("headers", []):
        h.setdefault(item.get("name", "").lower(), item.get("value", ""))
    return (
        msg.get("id", mid), msg.get("threadId"),
        norm_date(msg.get("internalDate"), h.get("date")),
        h.get("from"), h.get("to"), h.get("cc"), h.get("subject"),
        json.dumps(msg.get("labelIds", [])), msg.get("sizeEstimate"),
        datetime.now(timezone.utc).isoformat()
    )

def scan(api, c, limit=None, exclude_spam_trash=False):
    db = init_db(c["paths"]["database"])
    g, s = c.get("gmail", {}), c.get("scan", {})
    include = bool(g.get("include_spam_trash", True)) and not exclude_spam_trash
    page_token, seen, errors = None, 0, 0
    profile = execute(api.users().getProfile(userId="me"))
    print("Authenticated account:", profile.get("emailAddress"))
    print("Including Spam and Trash:", include)
    try:
        while True:
            args = {"userId":"me", "maxResults":min(max(int(g.get("page_size",500)),1),500),
                    "includeSpamTrash":include}
            if page_token: args["pageToken"] = page_token
            page = execute(api.users().messages().list(**args))
            for item in page.get("messages", []):
                try:
                    row = get_metadata(api, item["id"], g.get("metadata_headers",["From","To","Cc","Subject","Date"]),
                                       int(s.get("retry_attempts",5)))
                    db.execute("""INSERT INTO messages VALUES (?,?,?,?,?,?,?,?,?,?)
                        ON CONFLICT(message_id) DO UPDATE SET
                        thread_id=excluded.thread_id, internal_date=excluded.internal_date,
                        sender=excluded.sender, recipients=excluded.recipients, cc=excluded.cc,
                        subject=excluded.subject, label_ids=excluded.label_ids,
                        size_bytes=excluded.size_bytes, scanned_at=excluded.scanned_at""", row)
                    seen += 1
                except Exception as e:
                    errors += 1
                    print(f"[WARN] {item.get('id')}: {e}")
                if seen and seen % int(s.get("progress_every",100)) == 0:
                    db.commit()
                    print(f"Processed {seen}; errors {errors}")
                if limit is not None and seen >= limit: break
            if limit is not None and seen >= limit: break
            page_token = page.get("nextPageToken")
            if not page_token: break
        db.commit()
        total = db.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
        print(f"Scan complete. This run: {seen}; failures: {errors}; inventory total: {total}")
        print("Database:", c["paths"]["database"])
    finally: db.close()

def report(path):
    db = sqlite3.connect(path)
    try:
        total = db.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
        dates = db.execute("SELECT MIN(internal_date), MAX(internal_date) FROM messages").fetchone()
        senders = pd.read_sql_query("SELECT COALESCE(sender,'(unknown)') sender, COUNT(*) emails FROM messages GROUP BY sender ORDER BY emails DESC LIMIT 20", db)
        monthly = pd.read_sql_query("SELECT substr(internal_date,1,7) month, COUNT(*) emails FROM messages WHERE internal_date IS NOT NULL GROUP BY month ORDER BY month", db)
        labels = {}
        for (raw,) in db.execute("SELECT label_ids FROM messages"):
            try:
                for label in json.loads(raw or "[]"): labels[label] = labels.get(label,0)+1
            except (ValueError, TypeError): pass
        print(f"Messages: {total:,}\nOldest: {dates[0]}\nNewest: {dates[1]}")
        print("\nTop senders:\n", senders.to_string(index=False))
        print("\nMost common label IDs:")
        for k,v in sorted(labels.items(), key=lambda x:x[1], reverse=True)[:20]: print(f"{k:24} {v:,}")
        print("\nMonthly counts:\n", monthly.to_string(index=False))
    finally: db.close()

def cli():
    p = argparse.ArgumentParser(description="Read-only Gmail inventory")
    sub = p.add_subparsers(dest="cmd", required=True)
    sp = sub.add_parser("scan"); sp.add_argument("--max-messages", type=int); sp.add_argument("--exclude-spam-trash", action="store_true")
    sub.add_parser("report")
    a = p.parse_args(); c = config()
    if a.cmd == "scan": scan(service(c), c, a.max_messages, a.exclude_spam_trash)
    else: report(c["paths"]["database"])

if __name__ == "__main__": cli()

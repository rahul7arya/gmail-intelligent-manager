# Gmail Intelligent Email Manager — Phase 1

Read-only Gmail metadata inventory with Gmail API, OAuth 2.0, SQLite, CLI and Streamlit.

## Safety
- Requests only `gmail.readonly`.
- Retrieves headers, labels, dates and estimated message sizes; does not fetch message bodies or attachments.
- Does not modify, label, archive, trash or delete messages.
- Includes Spam and Trash by default. Use `--exclude-spam-trash` to omit them.
- OAuth credentials and the SQLite database are excluded from Git.

## Google Cloud setup
1. Create/select a project at https://console.cloud.google.com/
2. Enable Gmail API.
3. Configure Google Auth Platform / OAuth consent screen. Add your account as a test user if required.
4. Create an OAuth Client ID with application type **Desktop app**.
5. Download its JSON as `credentials/client_secret.json`.

Official guide: https://developers.google.com/workspace/gmail/api/quickstart/python

`gmail.readonly` is a restricted scope. Additional verification/security requirements can apply if the app is distributed or used beyond personal development.

## WSL2 installation

```bash
unzip gmail-intelligent-manager-phase1.zip
cd gmail-intelligent-manager
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
mkdir -p credentials data
cp config/settings.example.yaml config/settings.yaml
```

Place the downloaded OAuth JSON at `credentials/client_secret.json`.

## First test

```bash
python main.py scan --max-messages 100
python main.py report
```

Complete Google's sign-in/consent flow in the browser. Verify the account shown in the terminal is the intended Gmail account.

## Full inventory

```bash
python main.py scan
```

The API lists IDs in pages of up to 500, then retrieves metadata for each message. Large mailboxes may take time. Re-running is safe: message IDs are primary keys and records are upserted.

## Dashboard

```bash
streamlit run dashboard/app.py
```

## Data
- `credentials/client_secret.json`: downloaded OAuth client config
- `credentials/token.json`: generated OAuth token
- `data/gmail_inventory.sqlite3`: local metadata inventory

The database includes sender, recipients, CC, subject, date, Gmail label IDs and size estimate. Keep it private because email metadata is personal information.

## Troubleshooting
- Missing client JSON: confirm exact path and filename.
- OAuth access blocked: check consent-screen audience, test-user list and scope.
- `invalid_grant`: remove `credentials/token.json` and repeat authorization.
- WSL browser callback issue: ensure the browser can reach the local callback port.
- API quota/transient errors: retry logic handles common rate limits and server errors; rerun to refresh inventory.

## Phase 1 acceptance criteria
- 100-message test scan completes.
- CLI report displays count, date range, top senders and labels.
- Streamlit dashboard displays the same local inventory.
- Gmail remains unchanged.

Phase 2 will add categorization and cleanup recommendations. Any future deletion will require explicit approval.

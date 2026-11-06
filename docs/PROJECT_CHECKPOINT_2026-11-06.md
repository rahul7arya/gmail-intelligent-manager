# Gmail Intelligent Email Manager
## Project Checkpoint — 6 November 2026

**Status:** V2.3 validated against a 500-message sample
**Current phase:** Classification rule expansion and precision improvement
**Environment:** Windows 11 + WSL2 Ubuntu 24.04
**Repository:** gmail-intelligent-manager
**GitHub:** https://github.com/rahul7arya/gmail-intelligent-manager

---

## 1. Project Overview

Build an intelligent email management system that analyses Gmail messages, identifies their purpose, categorises them, detects required actions, and eventually helps organise the inbox through intelligent recommendations.

### Core objectives
- Accurate email classification.
- Reliable action-required detection.
- Explainable classification evidence.
- Safe, read-only analysis before Gmail modifications.
- Incremental development with synthetic and real-data validation.
- A maintainable architecture that evolves beyond basic keyword-based filtering.

The long-term goal is an intelligent email manager, not simply a collection of Gmail filters.

## 2. Development Environment

| Component | Setup |
|---|---|
| OS | Windows 11 |
| Development | WSL2 |
| Linux | Ubuntu 24.04 |
| Python | 3.12.3 |
| Virtual environment | `.venv` |
| Project directory | `~/projects/gmail-intelligent-manager` |
| Database | SQLite |
| Database path | `data/gmail_inventory.sqlite3` |
| Dashboard | Streamlit |
| Repository | Private GitHub repository |

Activate the environment:

```bash
cd ~/projects/gmail-intelligent-manager
source .venv/bin/activate

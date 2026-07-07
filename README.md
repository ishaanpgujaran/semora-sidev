<div align="center">

# Semora

### An autonomous quality gate for the vibe-coding era

*Catches what fast, AI-generated code skips — before it ever reaches a commit.*

[![Track](https://img.shields.io/badge/Kaggle-Freestyle%20Track-blue)]()
[![License](https://img.shields.io/badge/license-MIT-green)]()
[![Built with](https://img.shields.io/badge/built%20with-Antigravity%20%2B%20ADK%202.0-purple)]()

[Live Dashboard](https://semora-sidev.web.app/) · [Demo Video](#) · [Architecture](#architecture) · [Quickstart](#quickstart)

</div>

---

> **Note on the live dashboard:** [semora-sidev.web.app](https://semora-sidev.web.app/) is a real, deployed Firebase-hosted application — you're welcome to create a free account and explore it. Its authenticated views (Project Portfolio, Audit Timeline, Spec Matrix) require login by design, since they show a user's own private compliance history. Per the submission guidelines, this repository — with the setup instructions below — is the public project link for judging.

---

## The Problem

Ask an AI coding assistant to "add a password reset endpoint," and it will — often without input validation, without a cryptographically sound token, and without a single test. The code runs. It is not the same thing as code that's safe to ship. Semora closes that gap autonomously, on every commit.

## What Semora Does

Semora intercepts a `git commit`, mounts the full repository through a Model Context Protocol filesystem server, and runs three specialized agents in a graph built on Google's ADK 2.0:

| Agent | Job |
|---|---|
| **Spec Agent** | Turns the diff into Gherkin behavioral test scenarios — happy path plus adversarial edge cases |
| **Execution Agent** | Runs those scenarios in a fast, persistent sandbox and reports pass/fail |
| **Threat Agent** | Scans changed files with Semgrep, mapped onto the STRIDE security framework |

An **Aggregator** merges both signals into one compliance score. A score below 60 blocks the commit; the developer sees exactly why, with a suggested fix, in under two seconds:

```
SEMORA COMPLIANCE REPORT — auth.py (branch: feature/email-verify)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Compliance Score: 42/100  ❌ COMMIT BLOCKED

✔ Specs generated: 5 scenarios → tests/features/email_verify.feature
✘ Execution: 3/5 passed — empty-string input crashes with unhandled 500

STRIDE Findings:
  🔴 CRITICAL   [Information Disclosure]  verify_token() uses random.random()
                 for token generation — predictable, not cryptographically secure
  🟠 HIGH       [Tampering]  No length/format validation on the token parameter

Suggested patch:
  - token = str(random.random())
  + token = secrets.token_urlsafe(32)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

Every run also syncs live to the deployed dashboard — no custom backend involved, just Firestore's real-time listeners.

## Architecture

```
                    LOCAL MACHINE (your repo)
  ┌─────────────────────────────────────────────────────────┐
  │ git commit ──▶ MCP Filesystem Server (mounts your repo) │
  │                          │                              │
  │              ┌───────────▼────────────┐                 │
  │              │      ADK 2.0 Graph      │                │
  │              │  Spec ─┬─▶ Execution     │               │
  │              │        └─▶ Threat(STRIDE)│               │
  │              │            │             │               │
  │              │       Aggregator         │               │
  │              └───────────┬────────────┘                 │
  │                          ▼                              │
  │        Markdown report → your terminal                  │
  │        RunReport → written directly to Firestore        │
  └──────────────────────────┼──────────────────────────────┘
                              ▼
                    FIREBASE (free tier, no card required)
  ┌─────────────────────────────────────────────────────────┐
  │  Firestore (history + live updates) ◀── security rules ──▶│
  │  Firebase Hosting: React dashboard                        │
  │  Firebase Auth: login                                     │
  └─────────────────────────────────────────────────────────┘
```

The agent graph runs entirely on your machine — nothing about your code leaves it except the compliance summary. There is no custom backend server: the CLI writes directly to Firestore, and the dashboard reads directly from it, both governed by a single `firestore.rules` file rather than server-side authorization code.

## Tech Stack

| Layer | Tools |
|---|---|
| Agent orchestration | Google ADK 2.0, `agents-cli` |
| Context/tooling | Model Context Protocol (MCP) |
| Testing | Gherkin, `pytest-bdd` |
| Security | Semgrep, custom STRIDE rule mapping |
| LLM (spec generation) | Gemini API (free tier via Google AI Studio) |
| Dashboard | React (Vite), Tailwind CSS |
| Cloud | Firebase (Auth, Firestore, Hosting) — free Spark plan, no billing account required |

## Quickstart

### Prerequisites

- Python 3.11+
- Git
- A free [Google AI Studio](https://aistudio.google.com/) API key (for the Spec Agent's Gemini calls)

### Install

```bash
pip install semora
```

### Set up your API key

```bash
echo "GEMINI_API_KEY=your_key_here" > .env
```

### Wire up the commit gate

```bash
semora init
```
This installs a git pre-commit hook in your current repository. From now on, every `git commit` in this repo runs Semora automatically before the commit is allowed through.

### (Optional) Connect to the live dashboard

```bash
semora login
```
Prompts for an email and password (creates an account on first use). Once logged in, every `semora run` also syncs its report to your dashboard account in real time.

### Try it manually, any time

```bash
semora run
```
Runs a full check against your currently staged changes without needing to commit.

## Repository Structure

```
semora/
├── backend/semora/       # CLI, ADK agent graph, MCP server, sandbox, security, reporting, Firebase sync
├── dashboard/             # React dashboard (Firebase Hosting)
├── hooks/                 # Git pre-commit hook
├── sample_target_repo/    # Minimal demo app used to showcase Semora catching a real vulnerability
├── docs/                  # Architecture notes, demo script
├── firestore.rules        # Per-user Firestore authorization — the entire access-control layer
└── CONTEXT.md              # Coding standards followed throughout the build
```

## Testing

```bash
pip install -e .
pytest backend/tests/
```

## Demo Video

[Watch the 5-minute demo on YouTube](#) — covers the problem, the agent architecture, a live Antigravity build session, a blocked-then-fixed commit, and the deployed dashboard updating in real time.

## Built For

Google's **5-Day AI Agents Intensive — Vibe Coding Capstone**, Freestyle Track. Demonstrates all six of the course's key concepts: a multi-agent ADK 2.0 system, an MCP server, live Antigravity development, STRIDE-based security features, real deployability via Firebase, and direct use of Google's Agent Skills tooling (`agents-cli`).

## Authors

Built by **Ishaan Gujaran** and **Shivani Singh**.

## License

MIT

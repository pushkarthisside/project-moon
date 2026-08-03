# AGENTS.md — Project Moon

Context for any AI coding assistant (Codex CLI, GitHub Copilot) working in this repo.

## What this project is
A private, single-user Telegram bot — a personal AI companion named **Luna**. Publicly described as a life-navigation/companion assistant. It is built for exactly one user (the repo owner) and is never meant to support multiple users or a public audience.

**Hard constraint: this is single-user, single-persona by design.** Do not suggest, scaffold, or add multi-tenant support, user registration, multi-persona switching, or anything implying more than one person will ever use this bot. If asked to build something that would require reversing this, flag it instead of silently generalizing the code.

## Tech stack
- **Language:** Python
- **Bot interface:** `python-telegram-bot` (polling mode, not webhooks, for now)
- **LLM:** currently **Groq** (`llama-3.3-70b-versatile`), via the `groq` Python SDK. Originally planned for Gemini API (`google-genai` SDK) — abandoned temporarily due to an unresolved Google-side API key rollout bug (Gemini AI Studio issuing `AQ.` auth-key-format keys that the Gemini API itself rejects with `ACCESS_TOKEN_TYPE_UNSUPPORTED`, widely reported, unresolved as of build time). **The LLM call is isolated in one place in the code so this is swappable** — do not hardcode Groq-specific assumptions outside that boundary.
- **Database:** SQLite, local file at `data/moon.db`
- **Scheduler (planned, not yet built):** APScheduler, for unprompted/proactive messages
- **Hosting (planned, not yet done):** Oracle Cloud Always Free tier VM (Ubuntu), so the bot runs 24/7 independent of the owner's laptop
- **Env management:** `python-dotenv`, all secrets in `.env`, never hardcoded, never committed

## Repo structure
```
project-moon/
├── bot.py              # Entry point — Telegram handlers, LLM calls
├── db.py               # SQLite setup and table definitions
├── requirements.txt
├── .env                # NOT committed — secrets only
├── .gitignore          # covers .env, venv/, __pycache__, data/
├── data/               # NOT committed — contains moon.db (real personal conversation data)
└── personas/           # (planned, Phase 2) — system prompt / persona definition files
```

## Environment variables (`.env`)
```
TELEGRAM_BOT_TOKEN=   # from @BotFather
GROQ_API_KEY=         # console.groq.com
MY_CHAT_ID=           # the owner's Telegram chat_id — used for the allowlist check
```
(`GEMINI_API_KEY` may reappear later if the Gemini key issue resolves — treat as optional/legacy for now.)

## Non-negotiable security rule
**Every incoming message handler must check `chat_id` against `MY_CHAT_ID` before doing anything else** — including before any LLM call. This bot is publicly discoverable on Telegram (`t.me/ProjectMoonLunaBot`) and without this check, any stranger who messages it gets a response and burns the owner's API quota. Never remove or weaken this check. Never log full message content from a rejected/unauthorized sender beyond the chat_id itself.

## Database schema (current)
- **`messages`**: `id` (PK), `role` ('user'/'luna'), `content`, `timestamp`
- **`facts`**: `id` (PK), `category`, `content`, `importance` (1–5), `last_referenced`, `created_at`

**Planned (Phase 3) — weighted memory system.** This is a deliberate design choice, not a placeholder to "simplify":
- Each fact has an `importance` score (1–5), set either manually or by asking the LLM to rate significance at save-time
- Effective retrieval weight = `importance × recency_decay(time_since_last_referenced)` — importance-5 facts decay much slower than importance-2 ones
- Referencing a fact again in conversation should reinforce/reset part of its decay, not just its timestamp
- Retrieval for context-building should rank by effective weight, not treat all facts as equal — **do not implement a flat "dump all facts into context" approach**, that's the exact pattern this project is deliberately avoiding

## Current status (update this section as phases complete)
- **Phase 1 (platform setup): ~90% done.** Telegram bot working, Groq wired in as the LLM, allowlist verified working, SQLite table schema created. Not yet done: deployment to Oracle Cloud VM.
- **Phase 2 (personality/system prompt design): not started.** Current system prompt is a placeholder (`"you are Luna, a warm companion"`) — do not treat this as final, do not build features that assume a finished persona.
- **Phase 3 (weighted memory + scheduler): not started.**
- **Phase 4 (real-world usage + iteration): not started.**

## Conventions for any AI assistant working here
- Never write real API keys, tokens, or chat IDs into any file other than `.env`
- Never suggest making this bot public, multi-user, or web-facing
- Keep the LLM-calling logic isolated behind a clear boundary (currently in `bot.py`, should probably become its own `llm.py` as complexity grows — flag this refactor when it becomes relevant rather than doing it silently)
- When adding a feature, check whether it belongs to a phase that hasn't started yet (see Current status) — don't jump ahead into Phase 3/4 work while Phase 1 deployment is still incomplete
- `data/` and `.env` must never be committed — if either shows up in `git status` as staged, stop and flag it before committing# AGENTS.md — Project Moon

Context for any AI coding assistant (Codex CLI, GitHub Copilot) working in this repo.

## What this project is
A private, single-user Telegram bot — a personal AI companion named **Luna**. Publicly described as a life-navigation/companion assistant. It is built for exactly one user (the repo owner) and is never meant to support multiple users or a public audience.

**Hard constraint: this is single-user, single-persona by design.** Do not suggest, scaffold, or add multi-tenant support, user registration, multi-persona switching, or anything implying more than one person will ever use this bot. If asked to build something that would require reversing this, flag it instead of silently generalizing the code.

## Tech stack
- **Language:** Python
- **Bot interface:** `python-telegram-bot` (polling mode, not webhooks, for now)
- **LLM:** currently **Groq** (`llama-3.3-70b-versatile`), via the `groq` Python SDK. Originally planned for Gemini API (`google-genai` SDK) — abandoned temporarily due to an unresolved Google-side API key rollout bug (Gemini AI Studio issuing `AQ.` auth-key-format keys that the Gemini API itself rejects with `ACCESS_TOKEN_TYPE_UNSUPPORTED`, widely reported, unresolved as of build time). **The LLM call is isolated in one place in the code so this is swappable** — do not hardcode Groq-specific assumptions outside that boundary.
- **Database:** SQLite, local file at `data/moon.db`
- **Scheduler (planned, not yet built):** APScheduler, for unprompted/proactive messages
- **Hosting (planned, not yet done):** Oracle Cloud Always Free tier VM (Ubuntu), so the bot runs 24/7 independent of the owner's laptop
- **Env management:** `python-dotenv`, all secrets in `.env`, never hardcoded, never committed

## Repo structure
```
project-moon/
├── bot.py              # Entry point — Telegram handlers, LLM calls
├── db.py               # SQLite setup and table definitions
├── requirements.txt
├── .env                # NOT committed — secrets only
├── .gitignore          # covers .env, venv/, __pycache__, data/
├── data/               # NOT committed — contains moon.db (real personal conversation data)
└── personas/           # (planned, Phase 2) — system prompt / persona definition files
```

## Environment variables (`.env`)
```
TELEGRAM_BOT_TOKEN=   # from @BotFather
GROQ_API_KEY=         # console.groq.com
MY_CHAT_ID=           # the owner's Telegram chat_id — used for the allowlist check
```
(`GEMINI_API_KEY` may reappear later if the Gemini key issue resolves — treat as optional/legacy for now.)

## Non-negotiable security rule
**Every incoming message handler must check `chat_id` against `MY_CHAT_ID` before doing anything else** — including before any LLM call. This bot is publicly discoverable on Telegram (`t.me/ProjectMoonLunaBot`) and without this check, any stranger who messages it gets a response and burns the owner's API quota. Never remove or weaken this check. Never log full message content from a rejected/unauthorized sender beyond the chat_id itself.

## Database schema (current)
- **`messages`**: `id` (PK), `role` ('user'/'luna'), `content`, `timestamp`
- **`facts`**: `id` (PK), `category`, `content`, `importance` (1–5), `last_referenced`, `created_at`

**Planned (Phase 3) — weighted memory system.** This is a deliberate design choice, not a placeholder to "simplify":
- Each fact has an `importance` score (1–5), set either manually or by asking the LLM to rate significance at save-time
- Effective retrieval weight = `importance × recency_decay(time_since_last_referenced)` — importance-5 facts decay much slower than importance-2 ones
- Referencing a fact again in conversation should reinforce/reset part of its decay, not just its timestamp
- Retrieval for context-building should rank by effective weight, not treat all facts as equal — **do not implement a flat "dump all facts into context" approach**, that's the exact pattern this project is deliberately avoiding

## Current status (update this section as phases complete)
- **Phase 1 (platform setup): ~90% done.** Telegram bot working, Groq wired in as the LLM, allowlist verified working, SQLite table schema created. Not yet done: deployment to Oracle Cloud VM.
- **Phase 2 (personality/system prompt design): not started.** Current system prompt is a placeholder (`"you are Luna, a warm companion"`) — do not treat this as final, do not build features that assume a finished persona.
- **Phase 3 (weighted memory + scheduler): not started.**
- **Phase 4 (real-world usage + iteration): not started.**

## Conventions for any AI assistant working here
- Never write real API keys, tokens, or chat IDs into any file other than `.env`
- Never suggest making this bot public, multi-user, or web-facing
- Keep the LLM-calling logic isolated behind a clear boundary (currently in `bot.py`, should probably become its own `llm.py` as complexity grows — flag this refactor when it becomes relevant rather than doing it silently)
- When adding a feature, check whether it belongs to a phase that hasn't started yet (see Current status) — don't jump ahead into Phase 3/4 work while Phase 1 deployment is still incomplete
- `data/` and `.env` must never be committed — if either shows up in `git status` as staged, stop and flag it before committing
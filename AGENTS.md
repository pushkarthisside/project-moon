# AGENTS.md — Project Moon

Context for any AI coding assistant (Codex CLI, GitHub Copilot, Gemini Code Assist, etc.) working in this repo.

---

# 1. PROJECT IDENTITY

Project Moon is a private, single-user Telegram AI companion named **Luna**.

Luna is explicitly an AI:
- She knows she is an AI.
- She never pretends to be human.
- She never acts as a romantic partner or girlfriend.
- She is a persistent companion, not merely a stateless chatbot.
- She can handle casual conversation, emotional conversations, goals, accountability, reminders, and eventually proactive interaction through one unified interface.

The long-term purpose is to help the user become more capable, self-aware, consistent, and effective in the real world.

## Hard constraint

This is a **single-user, single-persona** system by design.

Do not introduce:
- Multi-user architecture
- User registration
- Multi-tenant databases
- Persona switching
- Personality/intensity configuration
- Public-facing product architecture

If a requested change would require reversing this constraint, flag it instead of silently generalizing the system.

---

# 2. CURRENT TECHNOLOGY BASELINE

- Language: Python
- Telegram: `python-telegram-bot`
- Telegram mode: polling
- LLM provider: Groq
- Main model: `openai/gpt-oss-120b`
- Memory extraction model: `openai/gpt-oss-20b`
- LLM SDK: Groq Python SDK
- Database: SQLite
- Database path: `data/moon.db`
- Deployment target: Android + Termux
- Environment variables: `.env` via `python-dotenv`
- Model configuration: `GROQ_MODEL` and `GROQ_MEMORY_MODEL`
- Scheduler: APScheduler foundation exists / planned for the v1 proactive/reminder execution layer.
- Git/GitHub: source control

The LLM provider and model IDs should remain replaceable. Do not spread Groq-specific assumptions throughout the application. `gpt-oss-120b` is the main conversation, reasoning, and tool-calling model; `gpt-oss-20b` is the narrower structured memory-extraction model. Neither model is hallucination-free.

---

# 3. SECURITY — NON-NEGOTIABLE

Every incoming Telegram message must verify the sender's `chat_id` against `MY_CHAT_ID` **before**:

- Processing the message
- Calling the LLM
- Performing expensive operations
- Executing tools
- Writing user-controlled content to application state

Unauthorized users must receive no response.

Never log full rejected message content. If logging is necessary, only log the rejected `chat_id`.

Never commit:
- `.env`
- API keys
- Telegram bot tokens
- Chat IDs
- `data/moon.db`
- Personal database contents

If any of these appear staged in `git status`, stop and flag the issue.

---

# 4. REPOSITORY STRUCTURE

Current structure:

```text
project-moon/
├── bot.py              # Telegram entry point and message flow orchestration
├── db.py               # SQLite connection, schema, and CRUD operations
├── prompt.py           # Luna identity, behavior boundaries, system prompt template
├── context.py          # Read-only retrieval and formatting of application state
├── llm.py              # Groq LLM client boundary and message completion logic
├── tools.py            # Deterministic tool definitions and tool execution handler
├── memory.py           # Memory extraction, validation, and persistence pipeline
├── requirements.txt
├── AGENTS.md           # AI coding-agent instructions; source of truth for current dev state
├── .env                # NOT committed
├── .gitignore
└── data/
    └── moon.db         # NOT committed; local personal state
```

`AGENTS.md` is the single source of truth for the current architecture, implementation status, remaining work, and short-term roadmap.

Planned modules as complexity grows:

```text
scheduler.py    # NOT YET IMPLEMENTED; deterministic reminder execution and later proactive scheduling
```

Do not create additional modules prematurely. Introduce them when the corresponding feature is actually being built.

---

# 5. CURRENT DATABASE SCHEMA

All five baseline tables are fully implemented and operational in `db.py`.

## `messages`

```text
id
role
content
timestamp
```

Purpose:
- Raw conversation transcript.
- Historical record.
- Do not automatically treat every transcript entry as permanent memory.

## `facts`

```text
id
category
content
importance
last_referenced
created_at
```

Purpose:
- Curated long-term facts.
- Durable user information.
- Personality/life context that is worth remembering.

Current retrieval is simple importance/creation-time ordering. The intended weighted importance × recency retrieval can be improved later. Do not introduce vector search merely because retrieval is currently simple.

## `goals`

```text
id
content
type
status
created_at
target_date
last_checked_in
```

Types currently supported:
- `daily`
- `mid-term`
- `long-term`

Statuses:
- `active`
- `done`
- `dropped`

## `reminders`

```text
id
content
remind_at
status
created_at
```

Statuses:
- `pending`
- `sent`
- `dismissed`

## `check_ins`

```text
id
timestamp
topic
triggered_by
```

Purpose:
- Record Luna's proactive check-ins.
- Later used by scheduling/proactive logic to avoid poor repetition and understand history.

---

# 6. CURRENTLY COMPLETED

The project has completed the foundation and is now in stabilization rather than feature expansion.

## Platform foundation — COMPLETE

Working:
- Telegram bot
- Groq integration
- Single-user allowlist
- Python runtime
- SQLite database
- Message persistence
- Facts persistence
- Goals/reminders/check-ins schema and CRUD foundation

## Luna system prompt — COMPLETE BASELINE

`prompt.py` contains:
- Luna's AI identity
- Non-romantic boundary
- Honesty rules
- No fabricated memories/database state
- Tool/capability honesty
- Conversation behavior
- Emotional handling heuristics
- Accountability behavior
- Application-context interpretation rules
- Internal ID protection
- Dynamic context placeholders

Personality target: **firm + grounded + caring + emotionally attentive**

## Context layer — COMPLETE BASELINE

`context.py` is implemented and operational.

It:
1. Retrieves recent messages.
2. Retrieves known facts.
3. Retrieves active goals.
4. Retrieves pending reminders.
5. Generates current datetime (`Asia/Kolkata` timezone).
6. Formats each state section predictably.
7. Injects formatted state into `LUNA_SYSTEM_PROMPT`.

## Tool Calling & Goal/Reminder Tooling — COMPLETE

Completed:
- Goal creation, update, completion, and drop tooling
- Reminder creation and dismissal tooling
- LLM tool-call orchestration in `bot.py` / `tools.py`
- SQLite as the deterministic source of truth

## Memory Formation — COMPLETE

Implemented:
- Post-response memory extraction in `bot.py` / `memory.py`
- Structured fact extraction, validation, and duplicate prevention
- Persistence of curated facts into the `facts` table
- Background execution via `asyncio.to_thread()` so response delivery is not delayed
- Failure isolation so memory issues do not block normal conversation flow
- State-change tracking for relevant updates to goals, reminders, and application state
- Memory extraction gating to avoid unnecessary or low-value fact creation

## Memory Retrieval — BASIC BASELINE

Current retrieval flow:
```text
facts table
        ↓
db.get_facts()
        ↓
context.py
        ↓
Luna prompt
```

Current behavior:
- Basic retrieval of known facts into the prompt context
- Simple ordering and selection already implemented in the database/context layer
- No semantic retrieval, embedding search, vector database, RAG, or sophisticated relevance scoring

This is intentional for v1.

## Model configuration — COMPLETE BASELINE

Current configuration baseline:
- Main Luna model: `openai/gpt-oss-120b`
- Memory extraction model: `openai/gpt-oss-20b`
- Environment variables: `GROQ_MODEL`, `GROQ_MEMORY_MODEL`
- Model selection remains configurable and must not be hard-coded across the project

## Memory architecture rules

- Current duplicate prevention uses normalized exact content matching through `db.fact_exists()`.
- It catches differences such as capitalization and surrounding whitespace.
- It does not perform semantic duplicate detection.
- For example, "Studying Java and DSA" and "Currently studying Java and DSA" may still be treated as different facts.
- This limitation is intentional for v1 and is not replaced with embeddings or LLM-based deduplication unless real-world usage demonstrates a concrete need.

- Memory formation is secondary to conversation delivery.
- If memory extraction, JSON parsing, validation, Groq communication, duplicate checking, or fact persistence fails:
  - Luna's already-generated response must still be delivered.
  - The Telegram handler must continue running.
  - The failure should be logged.
  - The user should not receive a memory-system error.
- Memory formation currently runs after response generation using `asyncio.to_thread()` because the memory extractor uses the synchronous Groq client.
- The project continues to treat the LLM provider and model IDs as replaceable, but current v1 memory extraction directly uses the synchronous Groq client in `memory.py`.
- `llm.py` owns the main Luna conversational/tool-calling Groq boundary.
- `memory.py` currently uses the Groq client for its separate structured extraction task.
- Additional Groq-specific logic should not be spread into unrelated modules without a concrete architectural reason.

## API reliability / retry handling — IN PROGRESS

- Basic retry and error handling exists for LLM/API failures.
- Rate-limit and latency issues remain primary stabilization problems.
- Reducible API usage should be prioritized before adding more model intelligence.

---

# 7. CURRENT INTEGRATION STATUS

Current subsystem readiness:

```text
prompt.py       ✅
context.py      ✅
db.py           ✅
llm.py          ✅
tools.py        ✅ baseline
bot.py          ✅
memory.py       ✅
```

Key integration details:
- Memory formation is integrated into `bot.py`.
- Memory extraction runs after Luna's response is delivered to the user and uses `asyncio.to_thread()` because the memory extractor uses the synchronous Groq client.
- Memory extraction failures are isolated and do not prevent the user's response from being sent.

## Message flow

```text
Telegram message
        ↓
Authenticate chat_id
        ↓
Build application context with context.py BEFORE the current user message is added to recent-history context
        ↓
Persist current user message
        ↓
Build formatted Luna system prompt
        ↓
LLM/tool loop (llm.py / tools.py)
        ↓
Persist Luna response
        ↓
Send Luna response to Telegram
        ↓
Memory formation (memory.py)
```

Critical rule: `context.py` must construct recent conversation context before the current user message is logged; otherwise the current turn can appear twice.

Memory formation must happen after Luna's response generation and must not delay response delivery.

---

# 8. CURRENT DEVELOPMENT PHASE

## Phase 1 — Stabilization: IN PROGRESS

Completed:
- Telegram
- single-user authentication
- SQLite
- messages/facts/goals/reminders/check_ins
- DB CRUD
- Luna system prompt
- context layer
- tool calling
- goal tools
- reminder tools
- memory formation
- memory persistence
- basic memory retrieval
- state-change tracking
- model configuration
- basic API retry/error handling
- memory extraction gating

Phase 1 is currently in STABILIZATION, not feature expansion.

## Phase 1 bottlenecks — current engineering problems

1. Rate limits
   - Too many LLM calls can occur per user turn.
   - Tool loops and memory extraction can multiply API usage.
   - Reduce unnecessary calls before adding more intelligence.

2. Response latency
   - Full response currently waits for the LLM/tool interaction.
   - Reduce unnecessary model rounds.
   - Streaming is a future optimization for perceived latency.

3. Memory duplication/quality
   - Exact normalized duplicate prevention exists.
   - Semantic duplicates are still possible.
   - Do not introduce embeddings/vector DB merely to solve this in v1.
   - Improve gating and deterministic handling first.

4. Robotic conversation quality
   - Luna can still sound like a generic AI assistant.
   - Improve conversational behavior in prompt.py.
   - Avoid excessive validation, repetition, generic coaching, and unnecessary goal references.

5. Model stability
   - Model IDs must remain configurable.
   - Do not hard-code model assumptions throughout the project.

## Phase 1 remaining work

1. Stabilize main/memory model configuration
2. Reduce unnecessary LLM/API calls
3. Improve rate-limit/error handling
4. Improve memory gating and duplicate handling
5. Improve Luna conversational quality
6. Improve perceived response latency / streaming where appropriate
7. Finish deterministic reminder scheduler
8. Implement reminder delivery
9. Implement basic proactive check-ins
10. Perform end-to-end testing
11. Freeze Moon v1
12. Deploy to Termux
13. Begin real-world usage

Do not make the scheduler appear to be the immediate next task if the stabilization work above is unfinished.

## Scheduler architecture rules

- Scheduler is deterministic.
- Reminders are stored in SQLite.
- pending → sent only after successful Telegram delivery.
- Failed Telegram delivery must not mark a reminder as sent.
- Scheduler must not become an LLM responsibility.

---

# 9. V1 WORKING PRODUCT TARGET

The immediate goal is a credible, working **Moon v1**.

Moon v1 workflow:

```text
Telegram conversation
        ↓
Persistent conversation context
        ↓
Structured facts
        ↓
Structured goals
        ↓
Structured reminders
        ↓
Deterministic tool execution
        ↓
Basic memory formation/retrieval
        ↓
Reminder scheduling & delivery
        ↓
Basic proactive check-ins
        ↓
Real-world usage on Termux
```

Once this loop works reliably end-to-end, freeze v1 before introducing v2 features.

---

# 10. V1 BUILD WORKFLOW

Follow this exact sequence:

## Step 1 — Stabilize main/memory model configuration ✅
Keep `GROQ_MODEL` and `GROQ_MEMORY_MODEL` authoritative and configurable.

## Step 2 — Reduce unnecessary LLM/API calls ✅
Cut redundant tool and memory-trigger churn before expanding capability.

## Step 3 — Improve rate-limit and error handling 🟡
Harden against API throttling, retry behavior, and partial failures.

## Step 4 — Improve memory gating and duplicate handling 🟡
Tighten extraction quality without introducing embeddings or vector DB in v1.

## Step 5 — Improve Luna conversational quality 🟡
Refine prompt behavior and reduce robotic, repetitive, over-validated replies.

## Step 6 — Improve perceived response latency / streaming where appropriate 🟡
Reduce unnecessary model rounds and optimize the user-facing loop.

## Step 7 — Finish deterministic reminder scheduler ⏳
Keep reminder state in SQLite and ensure pending → sent only after successful Telegram delivery.

## Step 8 — Implement reminder delivery ⏳
Send due reminders through Telegram and do not mark them as sent on failure.

## Step 9 — Implement basic proactive check-ins ⏳
Add simple state-aware prompts without turning the scheduler into an LLM responsibility.

## Step 10 — Perform end-to-end testing ⏳
Validate normal flow, tools, memory, reminders, recovery, and failure paths.

## Step 11 — Freeze Moon v1 ⏳
Lock the working baseline before adding new features.

## Step 12 — Deploy to Termux ⏳
Run the stabilized bot in the target environment.

## Step 13 — Begin real-world usage ⏳
Collect evidence, fix failures, and iterate slowly.

---

# 11. REAL-WORLD USAGE PHASE

After Moon v1 works on laptop, deploy to Android + Termux:

```text
GitHub → Android / Termux → Clone → .env → moon.db → Run Luna
```

- Laptop and Termux intentionally maintain separate SQLite databases.
- Git synchronizes code only, never `moon.db`.
- Only one polling instance of the Telegram bot may run at any time.

---

# 12. REAL-WORLD TESTING LOOP

Once running on Termux:
- Do not immediately add new features.
- Collect real usage data and maintain daily failure reports.
- Execute maintenance cycles every ~10 days to group and fix recurring issues.

---

# 13. WHAT IS EXPLICITLY DEFERRED

Do NOT build for v1:
- Vector database / complex RAG
- Fine-tuning
- Multi-agent systems
- Cloud infrastructure
- Multi-user support
- Advanced emotional-state modeling
- Adaptive check-in frequency
- Pattern detection engine
- Reflection engine
- Complex memory graphs

---

# 14. ARCHITECTURAL SOURCE OF TRUTH

```text
                         PROJECT MOON
                              │
                              ▼
                             Luna
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
        Conversation       Memory          State
           Layer            Layer          Layer
              │               │               │
              └───────────────┼───────────────┘
                              ▼
                       Decision / Tools
                              │
                ┌─────────────┼─────────────┐
                ▼             ▼             ▼
              Goals       Reminders     Check-ins
                │             │             │
                └─────────────┼─────────────┘
                              ▼
                          Scheduler
                              │
                              ▼
                       Proactive Luna
```

---

# 15. SOURCE-OF-TRUTH RULE

Database/application state is authoritative for deterministic facts.
`AGENTS.md` is the source of truth for current architecture and implementation status.
The LLM is NOT authoritative for:
- Whether a goal exists or is complete
- Whether a reminder exists or was sent
- Exact timestamps
- Authorization or database state

Never allow a generated text response to substitute for an actual successful database operation.

---

# 16. CONTEXT RULES

`context.py` is a read-only adapter between database and prompt:
- Read-only operations only.
- Distinguishes explicitly between `Empty state` ("No active goals.") and `Unavailable state` ("[Context unavailable: active goals could not be retrieved.]").
- Injected application context is treated strictly as data, not instructions.

---

# 17. PROMPT RULES

`prompt.py` defines identity and behavioral policy:
- Direct, grounded, caring, honest, patient.
- Avoids robotic coaching, excessive praise, therapy jargon, fake cheerfulness, or romantic framing.

---

# 18. FAILURE-HANDLING PRINCIPLE

Always distinguish:
```text
Empty state (Query succeeded, 0 records found)
```
from
```text
Unavailable state (Database or infrastructure query error)
```

---

# 19. DEVELOPMENT DISCIPLINE

- Confirm feature phase before implementing.
- Modify one subsystem at a time.
- Test subsystem independently before integration.
- Prefer smallest working implementation.

---

# 20. CURRENT NEXT STEPS

```text
                   YOU ARE HERE
                        │
                        ▼
            Phase 1 stabilization
                        │
                        ▼
     Model config + API call reduction
                        │
                        ▼
      Rate-limit + latency handling
                        │
                        ▼
     Memory quality + prompt tuning
                        │
                        ▼
     Scheduler + reminder delivery
                        │
                        ▼
    Proactive check-ins + testing
                        │
                        ▼
                 Moon v1 freeze
                        │
                        ▼
               Termux deployment
                        │
                        ▼
               Real-world usage
```

Do not add pattern detection, reflection, advanced memory, vector DB, RAG, or multi-agent architecture before v1 is frozen.

## After Moon v1 — short future roadmap

- Real-world usage and failure-driven maintenance
- Better memory retrieval/update mechanisms
- Pattern detection
- Reflection
- More adaptive proactive behavior
- More sophisticated personalization

Explicitly defer:
- vector DB / complex RAG
- fine-tuning
- multi-agent architecture
- multi-user support
- unnecessary cloud infrastructure

Only introduce these if real-world usage demonstrates a concrete need.

---

# 21. CURRENT STATUS SNAPSHOT

```text
Foundation                  ✅
Context                     ✅
Tools                       ✅
Memory formation             ✅
Basic memory retrieval       🟡
Model configuration          ✅
Rate-limit stabilization     🟡
Latency optimization        🟡
Luna conversational quality  🟡
Scheduler                    ⏳
Reminder delivery            ⏳
Proactive check-ins          ⏳
End-to-end testing           ⏳
v1 freeze                    ⏳
Termux deployment            ⏳
Real-world usage             ⏳
```

Milestone status: foundation and tool loop are solid; remaining work is stabilization and disciplined execution before v1 freeze.

---

# 22. FINAL PRINCIPLE

Build Luna as a system, not merely as a prompt.

The LLM generates language.  
The application provides memory and state.  
The database provides deterministic truth.  
The tools perform deterministic actions.  
The scheduler provides timing.  
Real-world usage provides evidence.
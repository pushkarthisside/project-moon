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
- Current model: `llama-3.3-70b-versatile`
- LLM SDK: Groq Python SDK
- Database: SQLite
- Database path: `data/moon.db`
- Deployment target: Android + Termux
- Environment variables: `.env` via `python-dotenv`
- Scheduler: APScheduler foundation exists / planned for the v1 proactive/reminder execution layer.
- Git/GitHub: source control

The LLM provider should remain replaceable. Do not spread Groq-specific assumptions throughout the application.

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
├── AGENTS.md           # AI coding-agent instructions (Source of truth for dev state)
├── GOALS.md            # Master project specification / roadmap
├── .env                # NOT committed
├── .gitignore
└── data/
    └── moon.db         # NOT committed; local personal state
```

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

The project has completed its foundation, tool calling, and memory formation pipelines.

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

Not yet complete:
- Reminder scheduling
- Detecting due reminders
- Telegram reminder delivery
- Marking reminders as sent after successful delivery

## Memory Formation — COMPLETE

Implemented:
- Post-response memory extraction in `bot.py` / `memory.py`
- Structured fact extraction, validation, and duplicate prevention
- Persistence of curated facts into the `facts` table
- Background execution via `asyncio.to_thread()` so response delivery is not delayed
- Failure isolation so memory issues do not block normal conversation flow

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
- The project continues to treat the LLM provider as replaceable, but current v1 memory extraction directly uses the synchronous Groq client in `memory.py`.
- `llm.py` owns the main Luna conversational/tool-calling Groq boundary.
- `memory.py` currently uses the Groq client for its separate structured extraction task.
- Additional Groq-specific logic should not be spread into unrelated modules without a concrete architectural reason.

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

## Phase A — Foundation: COMPLETE

Completed:
- Telegram, Groq, Auth allowlist, SQLite
- Schema and CRUD operations
- System prompt baseline and context layer

---

## Phase B — Core Intelligence & State: IN PROGRESS

Completed:
- Context integration
- LLM tool calling
- Goal execution
- Reminder CRUD and tooling
- Memory formation
- Memory persistence
- Baseline memory retrieval

Remaining:
1. Deterministic reminder scheduler
2. Reminder delivery via Telegram
3. Basic proactive check-ins
4. End-to-end testing
5. Moon v1 freeze

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

## Step 1 — Bot & context integration ✅
Pipeline established and tested.

## Step 2 — Tool calling ✅
Goal and reminder execution wired deterministically.

## Step 3 — Basic memory ✅
Post-response memory extraction, validation, and retrieval operational.

## Step 4 — Reminder scheduler ⏳ (NEXT)
Implement deterministic reminder execution via APScheduler:
```text
Reminder stored (pending)
        ↓
Scheduler checks due reminders
        ↓
Telegram sends reminder message
        ↓
Update status to 'sent'
```
*Note: If Telegram send fails, DO NOT mark as sent.*

## Step 5 — Basic proactive check-ins ⏳
Simple daily trigger inspecting active state/check-ins to initiate conversation.

## Step 6 — End-to-end testing ⏳
Validate normal flow, tools, memory, reminders, recovery, and failure paths.

## Step 7 — Freeze v1 ⏳
Freeze code and deploy to Android/Termux for real-world usage.

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
             ┌────────────────────┐
             │ Reminder scheduler │  ⏳ NEXT
             └──────────┬─────────┘
                        │
                        ▼
                Reminder delivery
                        │
                        ▼
               Basic proactive check-ins
                        │
                        ▼
               End-to-end testing
                        │
                        ▼
                Moon v1 freeze
                        │
                        ▼
               Termux deployment
                        │
                        ▼
               Real-world usage
                        │
                        ▼
         Failure-driven maintenance
```

Do not add pattern detection, reflection, advanced memory, vector DB, RAG, or multi-agent architecture before v1 is frozen.

---

# 21. CURRENT STATUS SNAPSHOT

```text
Telegram                         ✅
Groq                             ✅
Single-user security             ✅
SQLite                           ✅
messages table                   ✅
facts table                      ✅
goals table                      ✅
reminders table                  ✅
check_ins table                  ✅
Database CRUD foundation         ✅
Luna system prompt               ✅ baseline
Context retrieval                ✅
Context formatting               ✅
Timezone handling                ✅
Bot ↔ context integration        ✅
Tool calling                     ✅
Goal execution                   ✅
Reminder tooling                 ✅
Memory formation                 ✅
Memory retrieval                 🟡 basic baseline
Scheduler                        ⏳ NEXT
Reminder execution               ⏳
Reminder delivery                ⏳
Proactive check-ins              ⏳
End-to-end testing               ⏳
Termux deployment                ⏳
Real-world usage                 ⏳
```

Estimated completion toward Moon v1 freeze: **~75% planning estimate**

This is not an engineering metric.

---

# 22. FINAL PRINCIPLE

Build Luna as a system, not merely as a prompt.

The LLM generates language.  
The application provides memory and state.  
The database provides deterministic truth.  
The tools perform deterministic actions.  
The scheduler provides timing.  
Real-world usage provides evidence.
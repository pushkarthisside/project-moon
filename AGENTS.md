# AGENTS.md — Project Moon

Context for any AI coding assistant working in this repo.

---

# 1. PROJECT VISION

Project Moon is a private, single-user Telegram AI companion named Luna.

Luna is primarily a persistent conversational AI companion. Goals, facts, reminders, tools, and scheduler logic are internal capabilities she uses when useful, not the user-facing purpose of the system.

The user should not have to think:
- "Should I create a goal?"
- "Should I save this as a memory?"
- "Should I create a reminder?"

Luna should behave naturally and use structured state when appropriate.

This is a single-user, single-persona system by design.

Do not introduce:
- multi-user architecture
- user registration
- multi-tenant databases
- persona switching
- personality/intensity configuration
- public-facing product architecture

Goals remain available for explicit requests and clearly appropriate state-management situations.

Reminders remain explicit-action only.

Do not add autonomous goal creation as a Phase-1 requirement.

Do not make Luna turn ordinary conversation into goals.

---

# 2. CURRENT ARCHITECTURE

Repository structure:

```text
project-moon/
├── bot.py
├── db.py
├── prompt.py
├── context.py
├── llm.py
├── tools.py
├── memory.py
├── scheduler.py
├── requirements.txt
├── AGENTS.md
├── .env                # not committed
├── .gitignore
└── data/
    └── moon.db         # not committed
```

`AGENTS.md` is the source of truth for architecture and current implementation status.

Current baseline:
- Python
- Telegram polling
- Groq LLM provider
- SQLite database at `data/moon.db`
- `.env` via `python-dotenv`
- main model configurable via `GROQ_MODEL` (default `openai/gpt-oss-120b`)
- memory model configurable via `GROQ_MEMORY_MODEL` (default `openai/gpt-oss-20b`)
- `llama-3.1-8b-instant` and `llama-3.3-70b-versatile` were shut down by Groq on 2026-08-16; both main and memory models have been migrated to env-configurable defaults so future provider deprecations don't require a code change
- `scheduler.py` is implemented: `check_due_reminders` runs on a 60s job-queue interval, is timezone-aware (`Asia/Kolkata`), and only marks a reminder `sent` after Telegram delivery succeeds; real Telegram delivery validation is still pending
- proactive check-ins are implemented in `scheduler.py` and registered in `bot.py`; they use deterministic scheduler-side triggers and templates (see §10)

`llm.py`, `tools.py`, and `memory.py` are implemented modules, not planned placeholders.

---

# 3. SECURITY AND STATE RULES

Every incoming Telegram message must verify the sender `chat_id` against `MY_CHAT_ID` before:
- processing the message
- calling the LLM
- executing tools
- performing expensive operations
- writing user-controlled content to app state

Unauthorized users receive no response.

Never log full rejected message content. If logging is necessary, only log the rejected `chat_id`.

Never commit:
- `.env`
- API keys
- Telegram bot tokens
- chat IDs
- `data/moon.db`
- personal database contents

If these appear in `git status`, stop and flag the issue.

---

# 4. CURRENT LLM / TOOL STABILIZATION

The following are completed in the current codebase:

- configurable `GROQ_MODEL` and `GROQ_MEMORY_MODEL`
- bounded Groq retry handling
- Groq SDK `max_retries=0`
- small retry budget intentionally kept short
- `max_tool_rounds` remains 2
- `parallel_tool_calls=True`
- multiple independent tool calls can execute in one model response
- duplicate tool-call protection
- `state_change_attempted` tracking
- deterministic fallback when tool execution succeeds but the final LLM synthesis cannot complete
- batch goal-status tool
- partial batch result reporting
- tool-schema gating so ordinary messages do not receive unnecessary tool definitions

This does not mean rate limits are solved. Groq TPM/rate limits remain an external constraint and a stabilization concern.

---

# 5. CURRENT TOKEN / CONTEXT OPTIMIZATION

Phase-1 token reduction is implemented.

Current strategy:
- ordinary messages do not receive unnecessary tool schemas
- goal/reminder-related requests retain tool support
- system prompt was condensed while preserving critical behavior
- context selection was reduced

Observed approximate input-token estimates after optimization:
- ordinary casual messages: ~1.3K
- goal/reminder operations: ~2.4K
- durable statements: ~1.4K

These are estimates, not guaranteed provider-reported counts.

The database is not the prompt. Store long-term state in SQLite and inject only the context relevant to the current turn.

Context optimization is not considered finished forever. The remaining goal is to keep context bounded and relevant as state grows, without building vector RAG or complex retrieval in Phase 1.

---

# 6. CURRENT PROMPT / PERSONALITY STATE

`prompt.py` has been intentionally refined.

Current personality target:
- natural
- direct
- grounded
- conversational
- not robotic
- not excessively motivational
- not constantly asking questions
- does not force goals/productivity into unrelated conversation
- does not use unnecessary Markdown emphasis
- remains explicitly an AI
- never pretends to be human
- never acts as a romantic partner

This is currently good enough for Phase 1; it is not treated as a perfect or endlessly tuneable state.

---

# 7. CURRENT MEMORY STATE

The following memory features are completed baseline:
- post-response memory extraction
- deterministic/trivial-message gating
- durable-statement filtering
- duplicate prevention
- failure isolation
- configurable memory model
- basic fact retrieval

Known limitation:
- semantic duplicate facts can still exist

Memory extraction runs as a secondary post-response pass and must remain isolated from the user-facing response path. Memory failure must never cause the main response to fail.

Do not introduce embeddings or vector DB merely to solve this in Phase 1.

---

# 8. CURRENT TOOL STATE

Goal and reminder tools are operational.

Goal tools include:
- `create_goal`
- `get_active_goals`
- `update_goal_status`
- `update_multiple_goal_statuses`
- `update_goal_target_date` (updates only `target_date`; leaves status/content untouched)

Reminder tools include:
- `create_reminder`
- `get_pending_reminders`
- `update_reminder_status`

Batch goal operations are intended for explicit group requests such as:
- "remove all my Java goals"

Do not expose internal database IDs to the user.

SQLite remains the deterministic source of truth.

---

# 9. CURRENT FAILURE HANDLING

Deterministic fallback exists when tool execution succeeds but the LLM cannot complete the final synthesis.

Important principle:
- a successful database/tool operation must never be represented as failed merely because the final LLM response failed
- the system must never claim a state change that the database did not confirm

Do not add another LLM call just to make fallback text sound more natural.

---

# 10. PHASE 1 STATUS

## Completed

- Telegram foundation
- authentication
- SQLite/schema/CRUD
- context layer
- prompt baseline/refinement
- main LLM integration
- configurable models
- tool calling
- parallel tool execution
- batch goal operations
- reminder CRUD/tooling
- reminder scheduler (`scheduler.py`, `check_due_reminders`) — implemented with send-then-mark ordering; real delivery validation is still incomplete
- proactive check-ins — implemented with deterministic scheduler-side triggers and templates
- memory formation
- memory persistence
- baseline memory retrieval
- memory gating
- retry/error handling
- tool-loop stabilization
- deterministic fallback
- token/context reduction
- bounded dynamic context retrieval and per-item truncation
- model deprecation migration (env-configurable `GROQ_MODEL` / `GROQ_MEMORY_MODEL`, retry logic for rate/connection errors)

## Still incomplete

1. End-to-end reliability testing
   - test conversation, tools, memory, reminders, scheduler, proactive check-ins, failures, restarts, and rate-limit recovery together
   - includes a real (non-mocked) delivery test for `check_due_reminders`: due reminder → send fires → status transitions to `sent`

2. Phase-1 freeze
   - once the above works reliably, freeze the v1 architecture instead of adding more features

3. Termux deployment
   - deploy only after laptop end-to-end testing is stable

4. Real-world usage
   - run Luna for real usage and use observed failures to guide later improvements

---

# 11. IMPORTANT PHASE-1 BOTTLENECKS

1. Groq TPM / rate limits
   - external provider constraint
   - minimize unnecessary calls
   - do not solve by blindly adding retries

2. Context size
   - requests must remain bounded
   - avoid dumping all state into every prompt

3. Final-response reliability after tool execution
   - deterministic fallback exists
   - continue monitoring how often it is triggered

4. Memory API usage
   - avoid unnecessary memory extraction calls
   - memory remains secondary to response delivery

5. Perceived latency
   - latency has improved
   - streaming is optional future optimization, not a prerequisite for v1
   - stated evaluation order: latency measurement → streaming evaluation → scheduler duplicate-delivery hardening (send-then-mark race; see §10, Still incomplete item 1 for delivery validation), independent of the proactive check-ins work

Do not add new architecture just because these bottlenecks exist.

---

# 12. PHASE-1 PRIORITY ORDER

1. End-to-end reliability testing
2. Fix only concrete failures found during testing
3. Freeze Moon v1
4. Deploy to Termux
5. Begin real-world usage

Do not reopen stable LLM/tool architecture without evidence of a real failure.

---

# 13. AFTER PHASE 1

Future roadmap stays intentionally short:
- real-world failure-driven iteration
- better memory retrieval/update
- more adaptive proactive behavior
- pattern detection
- reflection
- deeper personalization

Explicitly defer:
- vector DB / complex RAG
- fine-tuning
- multi-agent systems
- multi-user architecture
- unnecessary cloud infrastructure

Only introduce these when real-world usage demonstrates a concrete need.

---

# 14. DEVELOPMENT DISCIPLINE

- confirm feature phase before implementing
- modify one subsystem at a time
- test subsystem independently before integration
- prefer the smallest working implementation
- keep the database and tool results authoritative
- do not let the LLM rewrite state that the database did not confirm

---

# 15. FINAL PRINCIPLE

Build Luna as a system, not merely as a prompt.

The LLM generates language. The application provides memory and state. The database provides deterministic truth. The tools perform deterministic actions. The scheduler provides timing. Real-world usage provides evidence.

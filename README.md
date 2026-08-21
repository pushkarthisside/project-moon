# 🌙 Project Moon — Luna

> A persistent AI companion that remembers you, tracks what matters, and can reach out on its own instead of always waiting for you to message first.

Project Moon is a personal AI companion system built around **Luna** — an AI designed to have normal conversations, remember important information, track goals, manage reminders, and eventually develop a better understanding of the person using it.

One of Moon's defining ideas is that **Luna is not only reactive**. The long-term system is designed so Luna can also initiate conversations herself — for example, by checking on a goal, following up on something important, noticing an approaching deadline, or simply deciding that a check-in makes sense.

The goal is not to build another chatbot that forgets everything between conversations. It is to build a system that can **know you over time**, maintain useful structured state, and eventually be able to reach out when there is a meaningful reason to do so.

> **Phase 1 note:** The reactive conversation, memory, goals, reminders, tools, context, and scheduler foundations are being built and tested first. Autonomous proactive messaging is part of the Phase 1 direction, but is not yet considered complete.

---

## Table of Contents

- [What is Luna?](#what-is-luna)
- [What Makes Moon Different?](#what-makes-moon-different)
- [Current Features](#-current-features)
- [How It Works](#-how-it-works)
- [The Bigger Idea](#-the-bigger-idea)
- [Tech Stack](#️-tech-stack)
- [Getting Started](#-getting-started)
- [Running Luna: Testing vs. Long-Term Use](#️-running-luna-testing-vs-long-term-use)
- [Android / Termux Deployment](#-android--termux-deployment)
- [Project Structure](#-project-structure)
- [Data & Privacy](#️-data--privacy)
- [Security](#-security)
- [Testing](#-testing)
- [Current Phase 1 Status](#-current-phase-1-status)
- [Roadmap](#️-roadmap)
- [Design Principles](#-design-principles)
- [License](#-license)

---

## What is Luna?

Luna is designed to sit somewhere between a normal AI assistant and a long-term personal companion.

You can talk to her normally:

> "I had a terrible day."

> "I just watched this insane movie."

> "What do you think about this?"

Or you can use her for more structured things:

> "My goal is to learn Spring Boot this month."

> "Remind me tomorrow at 8 PM to revise DBMS."

> "Mark my Java goal as completed."

The application provides Luna with relevant context from its own state instead of expecting the language model to magically remember everything.

That context can include:

- Recent conversation
- Persistent facts
- Active goals
- Pending reminders
- Current date and time

The result is intended to be more persistent and context-aware than a normal stateless chatbot.

---

## What Makes Moon Different?

A normal chatbot waits for you to open it and send a message.

Project Moon is being built toward something different:

```text
Normal chatbot:

You
 │
 ▼
Message
 │
 ▼
AI
 │
 ▼
Response


Project Moon:

You ───────────────► Luna
 │                     │
 │                     │
 └─────────────────────┘
                       │
                       ▼
                  Luna can also
                  initiate a
                  conversation
```

The eventual idea is simple:

> **Luna should sometimes be the one who texts first.**

For example:

> "You mentioned yesterday that your interview went badly. How are you feeling about it today?"

Or:

> "Your exam is getting close. How's the preparation going?"

Or:

> "You haven't checked in about that goal for a while. What's the situation?"

Or, when there is no urgent issue but a check-in makes sense:

> "How's your day going?"

This should **not** become a spam system or a rigid "send exactly three messages every day" scheduler.

The intended behavior is closer to:

```text
Is there a meaningful reason to check in?
            │
       ┌────┴────┐
      Yes        No
       │          │
       ▼          ▼
    Message    Stay quiet
```

Possible reasons can eventually include goals, deadlines, reminders, recent conversations, important events, previous check-ins, time of day, and observed user patterns.

The autonomous proactive layer is still being completed and tested. It is a core part of Moon's intended behavior, not a claim that the current Phase 1 build already handles every proactive scenario.

---

## ✨ Current Features

### 💬 Normal conversation

Luna can have ordinary conversations without forcing everything into a productivity or goal-tracking workflow.

### 🧠 Persistent facts

Important information can be stored as long-term facts instead of treating the entire conversation history as permanent memory.

A separate memory-extraction pass can run after the main response. It is isolated from the primary reply path so a memory-extraction failure does not break the conversation.

### 🎯 Goal tracking

Luna can create and manage structured goals, including:

- Daily, mid-term, and long-term goals
- Target dates
- Target-date changes/rescheduling
- Completion and dropped/cancelled status
- Clearly scoped batch updates

Goal IDs are application/database values. Luna can receive existing goal information as structured context and use those IDs when a tool operation requires them.

### ⏰ Reminders

Explicit reminders are stored in SQLite and delivered through the scheduler.

For example:

> "Remind me tomorrow at 8 PM to study DBMS."

The application creates the reminder, the scheduler checks for due reminders, and Telegram is used for delivery.

A reminder should only be treated as sent after the delivery operation succeeds.

### 🔔 Proactive messaging

Proactive messaging is one of the core ideas behind Project Moon.

The intended system allows Luna to initiate a Telegram message without the user first sending a message in that moment.

The eventual proactive layer can use application state such as:

- Active goals
- Goal deadlines
- Pending reminders
- Recent conversation
- Important events
- Previous check-ins
- Time of day
- User activity patterns

The system should have sensible limits and timing rules so that "Luna texts first" does not become "Luna spams you."

**Phase 1 status:** the database contains `check_ins` infrastructure and the scheduler foundation is being developed, but autonomous proactive message selection and delivery are not yet considered complete.

### 🛡️ Tool safety

Important state-changing actions are handled through deterministic tools rather than allowing the model to simply claim that something happened.

```text
User request
     ↓
Luna understands the request
     ↓
Structured tool call
     ↓
Application validates it
     ↓
SQLite operation
     ↓
Confirmed result
     ↓
Luna responds
```

For example, Luna should not say:

> "Done, I created the reminder."

unless the application actually confirmed that the reminder was created.

The LLM also cannot directly decide that a database operation succeeded.

### 🧩 Structured context

Before generating a response, the application can assemble structured context containing:

- Current date/time
- Recent messages
- Known facts
- Active goals
- Pending reminders

The application supplies this context; the model does not invent it.

---

## 🏗️ How It Works

At a high level, Moon has both a **reactive path** and an eventual **proactive path**.

```text
                         PROJECT MOON
                              │
                ┌─────────────┴─────────────┐
                │                           │
          User message                  Scheduler
                │                           │
                ▼                     ┌─────┴─────┐
             bot.py               Reminders   Proactive
                │                              │
                └─────────────┐                │
                              ▼                │
                           Context ◄───────────┘
                              │
                 ┌────────────┼────────────┐
                 │            │            │
              Messages      Facts        Goals
                                           │
                                       Reminders
                              │
                              ▼
                             Luna
                              │
                              ▼
                             Groq
                              │
                              ▼
                           Telegram
```

The important architectural distinction is:

**The LLM handles language. The application handles state.**

The application is responsible for things that need to be deterministic and verifiable, including:

- Database state
- Goal status
- Reminder state
- Tool execution
- Scheduling
- Time handling
- Telegram authorization

The LLM is responsible primarily for:

- Understanding natural language
- Interpreting context
- Generating conversational responses
- Requesting supported tools when an action is needed

---

## 🧠 The Bigger Idea

Project Moon is intentionally being built in layers.

The long-term vision is for Luna to eventually be able to:

- Remember important experiences
- Understand long-term goals
- Track commitments
- Notice behavioral patterns
- Recognize improvement
- Understand time and context
- Follow up on important events
- Initiate conversations on her own
- Decide when it is useful to listen, advise, push, or simply check in
- Build an increasingly useful model of the user over time

The goal is not to make Luna "self-aware" in the literal human sense.

The goal is to build a reliable artificial system that can **maintain context, learn useful information about the user, observe changes over time, and act at appropriate moments.**

---

## ⚙️ Tech Stack

| Component | Technology |
|---|---|
| Language | Python |
| Interface | Telegram |
| Bot framework | python-telegram-bot |
| LLM provider | Groq |
| Database | SQLite |
| Scheduling | python-telegram-bot `JobQueue` / scheduler layer |
| Environment variables | python-dotenv |
| Deployment target | Android / Termux, or another always-on environment |

The main LLM model and memory-extraction model are configurable through environment variables.

---

## 🚀 Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/pushkarthisside/project-moon
cd project-moon
```

### 2. Create a virtual environment

**Windows**

```bash
python -m venv .venv
.venv\Scripts\activate
```

**Linux / macOS / Termux**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the project root:

```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
GROQ_API_KEY=your_groq_api_key
MY_CHAT_ID=your_telegram_chat_id
GROQ_MODEL=openai/gpt-oss-120b
GROQ_MEMORY_MODEL=openai/gpt-oss-20b
```

Use the model values appropriate for the current project configuration.

**Do not commit `.env` to Git.**

### 5. Start Luna

```bash
python bot.py
```

If the configuration is correct, Luna will start polling Telegram.

---

## ⚠️ Running Luna: Testing vs. Long-Term Use

There is an important difference between **running Luna** and **hosting Luna**.

### Running locally

You can simply run:

```bash
python bot.py
```

This is enough for:

- Development
- Testing
- Short-term use
- End-to-end testing on your laptop

However, Luna only runs while that Python process is running.

If you:

- Close the terminal
- Shut down the computer
- Stop the Python process
- Put the hosting environment to sleep

then the bot stops running.

Your SQLite database is not automatically deleted. The application simply is no longer running.

### Long-term / 24×7 use

If you want Luna to remain available and eventually be able to **text you on her own even when you are not actively using the bot**, the process needs to run continuously on an always-on environment.

Examples include:

- Android + Termux
- A VPS / virtual machine
- A home server
- Another computer that stays running

A virtual machine is **not required**. The actual requirement is an environment that stays online and allows the Python process and scheduler to keep running.

For Project Moon, **Android + Termux is the intended personal deployment environment**. 

---

## 📱 Android / Termux Deployment

The intended personal always-on setup is:

```text
Android Phone
      │
    Termux
      │
    Python
      │
 Project Moon
      │
    SQLite
      │
   Telegram
```

For reliable long-term operation, Android may require additional configuration such as:

- Termux startup/persistence configuration
- Battery optimization changes
- Automatic restart after reboot
- Keeping the Python process alive

These are deployment concerns rather than requirements for local development.

Deployment should happen after laptop end-to-end testing is stable.

---

## 📁 Project Structure

The project is intentionally kept relatively simple.

```text
project-moon/
│
├── bot.py
├── context.py
├── prompt.py
├── llm.py
├── memory.py
├── tools.py
├── scheduler.py
├── db.py
│
├── tests/
│   ├── test_bot_formatting.py
│   ├── test_goal_date_validation.py
│   ├── test_memory_extraction.py
│   ├── test_llm_safety.py
│   ├── test_llm_tool_fallback.py
│   └── ...
│
├── data/
│   └── moon.db
│
├── .env
├── .gitignore
├── requirements.txt
└── README.md
```

### Main components

| File | Responsibility |
|---|---|
| `bot.py` | Telegram handling and application orchestration |
| `context.py` | Retrieves and formats application context |
| `prompt.py` | Luna's identity, behavior, and system prompt |
| `llm.py` | Groq interaction and tool-call handling |
| `memory.py` | Memory extraction and memory-related logic |
| `tools.py` | Deterministic goal/reminder operations |
| `scheduler.py` | Runs scheduled operations such as reminder delivery and proactive check-in logic |
| `db.py` | SQLite database, schema, and CRUD operations |

Together, these components form the core application loop: `bot.py` receives the Telegram event, `context.py` gathers the relevant state, `prompt.py` defines how Luna should behave, `llm.py` communicates with Groq, and `tools.py` handles actions that must be verified by the application. `memory.py` handles durable-information extraction, while `scheduler.py` handles work that needs to happen because of time rather than because the user just sent a message.

---

## 🗃️ Data & Privacy

Project Moon stores its local application data in:

```text
data/moon.db
```

This database may contain:

- Conversation history
- Persistent facts
- Goals
- Reminders
- Check-in state
- Other personal application data

For that reason, `data/` should not be committed to Git.

The `.env` file also contains secrets and must not be committed.

Git synchronizes the **code**, not the personal SQLite database.

---

## 🔐 Security

Keep these values private:

- `TELEGRAM_BOT_TOKEN`
- `GROQ_API_KEY`
- `MY_CHAT_ID`

Never commit them to GitHub.

The bot uses a Telegram chat ID allowlist so unauthorized users cannot use the bot or consume the owner's API quota.

Authorization is checked before expensive processing such as LLM calls or tool execution.

---

## 🧪 Testing

Tests are located in:

```text
tests/
```

Run the full test suite with:

```bash
python -m unittest discover
```

Current tests cover areas such as:

- Telegram message formatting
- Goal date validation
- Memory extraction and memory gating
- LLM safety behavior
- Tool fallback behavior
- Scheduler-related behavior
- Other application regressions

The test suite is used to catch regressions as Moon becomes more complex.

---

## 🧭 Current Phase 1 Status

Project Moon is actively under development.

### Working foundation

- Telegram bot
- Telegram chat ID allowlisting
- Groq integration
- Configurable LLM models
- SQLite persistence
- Conversation history
- Structured facts
- Goal management
- Reminder management
- Context assembly
- Tool/function calling
- Tool validation
- Duplicate tool-call protection
- Deterministic tool fallbacks
- Memory extraction safeguards
- Automated tests

### In progress / not yet complete

- Full reminder scheduler validation
- Autonomous proactive check-ins
- Proactive message selection
- Proactive message delivery
- End-to-end reliability testing across restarts and transient API failures
- Termux deployment

### Intentionally not part of Phase 1

- Vector databases
- Complex RAG
- Fine-tuning
- Multi-agent architecture
- Multi-user architecture
- Cloud infrastructure
- Complex emotional-state modeling
- Advanced pattern detection

The project is deliberately being built incrementally. Real usage should determine when additional complexity is justified.

---

## 🗺️ Roadmap

### Phase 1 — Foundation

- ✓ Telegram
- ✓ Groq
- ✓ SQLite
- ✓ Structured context
- ✓ Facts
- ✓ Goals
- ✓ Reminders
- ✓ Tool calling
- ✓ Basic memory extraction
- ✓ Safety and fallback handling
- ✓ Automated tests
- ✓ Finish scheduler validation
- ✓ Build autonomous proactive check-ins



### Later phases

- Improve memory retrieval
- Improve long-term user modeling
- Better time awareness
- Pattern detection
- Evidence-based behavioral insights
- More sophisticated proactive behavior
- Reflection

The roadmap is intentionally flexible. Real-world usage should determine what gets built next instead of adding speculative architecture ahead of need.

---

## 🧱 Design Principles

### The database is the source of truth

The LLM should not decide whether a goal exists, whether a reminder was created, or whether a state-changing operation succeeded.

### The LLM is not the entire application

Luna is powered by an LLM, but deterministic responsibilities belong to normal software.

### Proactive does not mean spam

Luna should not message simply because a timer says she must.

The intended question is:

> **"Is there a good reason to initiate a conversation right now?"**

### Memory is not the same as conversation history

Not everything the user says should become permanent memory.

### Don't overengineer

Moon starts with:

```text
Python
+
SQLite
+
Structured Context
+
LLM
+
Deterministic Tools
+
Scheduler
```

More complicated systems should only be introduced when real usage demonstrates a real limitation.

### Luna should help the user become more capable

The purpose of the system is not to make the user dependent on it.

---

## 🔧 How the Main Pieces Work

The main files are intentionally separated by responsibility.

### `bot.py` — the entry point

Receives Telegram updates and coordinates the application flow. It is the layer that connects the Telegram interface to the rest of Moon.

### `context.py` — current state for Luna

Reads the relevant application state from SQLite and turns it into predictable context for the model. It does not call the LLM or modify goals, reminders, or memories.

### `prompt.py` — Luna's behavior

Defines Luna's identity, boundaries, response style, and rules for interpreting the application-provided context.

### `llm.py` — model boundary

Handles communication with Groq and the LLM/tool-call loop. The rest of the application should not need to know the provider-specific details of the model API.

### `tools.py` — actions that must actually happen

Handles deterministic operations such as creating or updating goals and reminders. The model can request an action, but the application performs and verifies it.

### `memory.py` — turning useful information into memory

Runs the memory-extraction logic after conversation handling and applies safeguards before information is stored as a persistent fact.

### `scheduler.py` — work that happens because of time

Handles scheduled operations such as checking for due reminders and, as the proactive system is completed, checking whether Luna has a reason to initiate a conversation.

### `db.py` — source of truth

Owns the SQLite schema and database operations. Persistent state lives here rather than inside the LLM.

The overall flow is therefore:

```text
Telegram
   ↓
bot.py
   ↓
context.py ───────► SQLite
   ↓
prompt.py
   ↓
llm.py ───────────► Groq
   ↓
tools.py ─────────► SQLite
   ↓
Telegram

scheduler.py ─────► time-based work
                       │
                       ├── reminders
                       └── proactive checks
```

This separation keeps language generation, persistent state, deterministic actions, and time-based automation from becoming one large piece of code.

---

## 📜 License

This project is licensed under the MIT License.

See [LICENSE](LICENSE) for details.

```text
Copyright (c) 2026 Pushkar Nakkina
```

---

🌙 **Project Moon** — a persistent AI companion built one reliable system at a time.

> **A note about this project:** Project Moon is my first AI project, built mainly for my own use and to learn along the way — not as a polished multi-user product or hosted service. It's a single-user, personal system by design, but feel free to use it, fork it, or build on top of it if it's useful to you 🫱🏽‍🫲🏽.

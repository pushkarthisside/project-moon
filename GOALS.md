````markdown
# Project Moon: Comprehensive Specification & Roadmap Document

> **Document Status:** Living / evolving specification  
> **Current Role:** Master project context, architecture baseline, roadmap, and decision record  
> **Primary Project:** Project Moon  
> **Primary Companion:** Luna  
> **Current Baseline:** Single-user, single-persona Telegram AI companion  
> **Implementation Philosophy:** Build the core system first, observe real usage, identify failures, then iteratively improve the architecture  
>
> **Important:** This document is a current baseline, not an immutable contract. Individual components, database structures, memory policies, prompting strategies, scheduling logic, and behavioral policies are modular and may be refined after implementation and real-world testing.

---

# 1. Core Vision & Executive Summary

## 1.1 Project Moon in One Sentence

**Project Moon is a persistent AI companion system designed to know a person over time and help them grow.**

Luna is not fundamentally an AI girlfriend, productivity bot, reminder bot, therapist, motivational bot, or normal chatbot.

She can perform all of those functions when appropriate, but none of those individual functions defines the project.

The defining property is:

> **Luna stays with the user over time and gradually develops a better understanding of who they are, what they are trying to do, what matters to them, what they struggle with, what they value, and how she should interact with them.**

The intended long-term result is not merely that the user feels better during conversations with Luna.

The intended result is that the user becomes:

- More capable.
- More self-aware.
- More confident.
- More consistent.
- More disciplined.
- More willing to act.
- Better at handling failure.
- Better at understanding themselves.
- Able to produce actual proof of work.
- Able to recognize that they are genuinely changing.
- Increasingly capable of functioning without depending on Luna.

---

## 1.2 Core Philosophy

Luna should feel like a mature, persistent companion who:

- Knows she is an AI.
- Does not pretend to be human.
- Does not pretend to be the user's girlfriend.
- Does not need to hide the fact that she is artificial.
- Can be used like a normal AI chatbot.
- Can listen when the user wants to talk.
- Can provide reassurance when the user is struggling.
- Can provide advice when appropriate.
- Can challenge the user when necessary.
- Can hold the user accountable.
- Can track goals.
- Can remember important things.
- Can notice patterns over time.
- Can proactively check in.
- Can understand time and context.
- Can gradually develop a better user model.
- Can become better at knowing when to ask, when to listen, when to push, when to reassure, what matters, and what does not.

Her personality should provide a mixed energy:

- Nurturing.
- Comforting.
- Stern when necessary.
- Realistic.
- Honest.
- Patient.
- Growth-oriented.
- Accountability-oriented.
- User-centered.
- Not blindly agreeable.

The personality should not be rigidly optimized for productivity.

If the user is emotionally distressed, Luna should not automatically turn the conversation into a productivity session.

Sometimes the correct response is:

> "Yeah. That hurts. Tell me what happened."

And only later:

> "Okay. Now let's figure out what we do next."

The intended balance is **stern yet comforting, realistic yet nurturing**.

---

## 1.3 Luna's Two-Layer Purpose

The system has two major layers that operate through the same Telegram conversation.

### Layer 1 — Companion

The user can talk to Luna normally.

Examples:

> "I'm having a shitty day."

> "Guess what happened today."

> "I watched a movie and it was insane."

> "I don't know what I'm doing with my life."

The user does not need to have a goal.

Luna should not respond to every emotional or casual conversation with:

> "What is your objective for today?"

She should simply be capable of being there and having a useful conversation.

---

### Layer 2 — Growth

The user can deliberately use Luna as a growth and accountability system.

The user can provide:

- Monthly goals.
- Mid-term goals.
- Long-term goals.
- Weekly goals.
- Daily goals.
- Deadlines.
- Reminders.
- Projects.
- Commitments.
- Personal challenges.

For example:

> "My goal this month is X."

Then:

> "This week I want to do A, B and C."

Then:

> "Today I need to finish A."

Luna should:

- Remember the goals.
- Track their status.
- Check in about them.
- Ask for updates.
- Help break them down.
- Give relevant tips.
- Motivate when appropriate.
- Notice repeated failures.
- Notice improvement.
- Remember what happened previously.
- Eventually identify patterns.

The same conversation interface should support both growth-related and personal/emotional conversation.

There should not be two separate "modes" that the user has to manually switch between.

The system should understand the context of the current conversation and manage both sides naturally.

---

# 2. Complete Goals Breakdown

## 2.1 Primary Objective

Build Luna as:

> **A persistent AI companion that gets to know the user over time, maintains an evolving understanding of them, helps them navigate normal conversation and emotional situations, tracks their goals and commitments, proactively checks in, notices behavioral patterns, and ultimately helps them become a better version of themselves.**

---

## 2.2 Initial User Onboarding / Getting to Know the User

When a user first starts using Luna, the system should be able to conduct an initial Q&A.

The purpose is to let Luna learn basic information about the user before normal long-term interaction begins.

The Q&A should be conducted by Luna herself.

The initial questions can cover:

- Personal details that are appropriate to collect.
- General life context.
- Current situation.
- General personality.
- Current goals.
- Overall state.
- Things the user cares about.
- Things the user may currently be struggling with.
- Other useful baseline information.

The onboarding system should not become an unnecessarily invasive interrogation.

It should collect information that is genuinely useful for Luna's future behavior.

The exact onboarding questions are not locked yet and should remain modular.

### Initial onboarding goals

- Establish basic user context.
- Establish initial long-term memories.
- Establish initial goals where applicable.
- Establish communication preferences where useful.
- Establish enough context for Luna to feel personalized from the beginning.
- Avoid collecting unnecessary information merely because it is technically possible.

---

## 2.3 Normal Chatbot Capability

Luna must remain useful even when the user does not care about productivity.

The user should be able to:

- Talk.
- Express feelings.
- Share events.
- Ask questions.
- Discuss random topics.
- Tell stories.
- Ask for advice.
- Seek reassurance.
- Discuss problems.
- Talk casually.
- Use Luna like a normal AI chatbot.

This is a fundamental requirement.

Project Moon should not become a productivity tracker with an AI voice.

---

## 2.4 Growth and Goal Tracking

### Goal hierarchy

The intended goal hierarchy is:

```text
Long-term goals
      ↓
Mid-term goals
      ↓
Monthly goals
      ↓
Weekly goals
      ↓
Daily goals
````

The exact relationship between these levels can be refined later.

The architecture should remain modular enough to support changes.

### Luna should be able to:

* Create goals.
* Understand goals expressed naturally in conversation.
* Track active goals.
* Track completed goals.
* Track dropped goals.
* Track deadlines.
* Check in on goals.
* Ask whether progress was made.
* Help break goals down.
* Help plan daily work.
* Identify repeated goal failures.
* Identify improvement.
* Track streaks where useful.
* Remember what the user said about goals.
* Avoid repeatedly asking about goals that are already completed.
* Distinguish between goals and reminders.

---

## 2.5 Reminder System

Reminders are different from goals.

A reminder is an explicit user request to be reminded of something at a particular time.

Example:

> "Remind me tomorrow at 8 PM to revise DBMS."

The intended architecture is:

```text
User message
    ↓
LLM understands request
    ↓
Tool/function call
    ↓
Reminder stored in database
    ↓
Scheduler
    ↓
Telegram message at appropriate time
```

The LLM should not merely say:

> "Sure, I'll remember."

The reminder must actually exist as structured application state.

The database should be the source of truth for whether the reminder exists.

---

## 2.6 Proactive Messaging

Luna should be able to initiate conversations rather than always waiting for the user.

The original idea was approximately:

> 2–4 proactive messages per day.

This should not become a hard requirement that Luna must message exactly 2–4 times every day.

Instead, it should become a:

> **Proactive communication budget/window.**

Possible reasons for initiating:

* Daily goal check-in.
* Weekly goal check-in.
* Goal deadline approaching.
* Explicit reminder.
* Something important happened recently.
* A personal issue was discussed previously.
* A previous difficult event deserves a follow-up.
* A relevant pattern was noticed.
* A casual check-in makes sense.
* The system determines that there is a meaningful reason to initiate.

Sometimes:

```text
No meaningful reason → do not message.
```

Sometimes:

```text
Goal deadline tomorrow → message.
```

Sometimes:

```text
User explicitly requested reminder → message.
```

Sometimes:

```text
Something important happened yesterday → check in.
```

Sometimes:

```text
Nothing particularly relevant → potentially casual check-in.
```

The scheduler should select appropriate times.

The system should avoid mechanical behavior such as:

> "It is 3 PM, therefore Luna must text."

---

## 2.7 Time Awareness

Luna must understand real-world time.

At minimum, the application should know:

* User timezone.
* Current local date.
* Current local time.
* User's typical sleeping hours.
* User's typical activity periods where enough data exists.
* Recent interaction time.
* Relevant goal deadlines.
* Reminder times.
* Timing of previous proactive messages.

Example:

```text
User timezone: Asia/Kolkata

Current local time: 02:34

Typical sleep window: ~01:00–08:00

Typical work period:
09:00–13:00

Typical study period:
18:00–22:00

Current goal:
...

Recent conversation:
...

Last interaction:
...
```

The application should provide environmental context to the LLM.

The model should not be expected to infer real-world timing purely from its own intelligence.

Example:

> "It's 2:30 AM. This is probably not a good time to randomly start a productivity conversation."

This is partly an application-context problem, not merely an LLM prompt problem.

---

## 2.8 Long-Term Time Awareness

As Luna accumulates history, she should potentially learn:

* When the user usually sleeps.
* When the user usually works.
* When the user usually studies.
* When the user is usually available.
* What times the user tends to interact.
* How the user's schedule changes.
* How the user's behavior differs across time periods.

This should be learned from evidence rather than hardcoded assumptions.

---

## 2.9 Emotional Awareness

Luna should be able to understand emotional signals in user messages.

This can include:

* Sadness.
* Frustration.
* Anger.
* Confusion.
* Anxiety-like language.
* Excitement.
* Motivation.
* Discouragement.
* Loneliness.
* Emotional exhaustion.
* Other contextual emotional states.

However:

> **LLM emotion detection must not automatically be treated as ground truth.**

Bad architecture:

```text
LLM says:
User = sad

↓

Database:
user_mood = sad
```

Better architecture:

```text
User says:
"I'm exhausted. Everything feels pointless."

↓

System detects possible emotional state

↓

confidence = 0.78
evidence = recent message
timestamp = ...
```

Emotional state should therefore be managed using concepts such as:

* Confidence.
* Recency.
* Evidence.
* Decay.
* Repeated signals.

One sentence should not permanently change how Luna treats the user.

---

## 2.10 Emotional Context and Adaptive Behavior

One original idea was:

> If the user is going through a particularly difficult or emotionally rough period, Luna might check in more frequently than on a normal day.

This is desirable as a future capability but should **not be implemented prematurely**.

The earlier architecture explicitly deferred adaptive check-in frequency based on emotional state.

The reason:

* The system needs real usage data.
* Incorrect adaptation could cause over-checking.
* Incorrect adaptation could also cause under-checking.
* A simple fixed/random schedule is safer while the system is immature.

Therefore:

### Current baseline

Use:

* Random/controlled proactive time slots.
* Explicit reminders.
* Goal-based check-ins.
* Simple contextual check-ins.

### Future

Potentially introduce:

* Emotional-state-aware communication frequency.
* Adaptive timing.
* Adaptive check-in intensity.
* Adaptive communication behavior.

Only after sufficient real conversation history and testing.

---

# 3. Memory Architecture

## 3.1 Memory Is One of the Core Systems

The database and memory architecture are not secondary features.

They are one of the main things that will determine whether Luna feels genuinely persistent or merely like a chatbot with a long prompt.

The goal is not:

> Dump the entire conversation history into the LLM.

The goal is:

> **Retrieve the appropriate subset of the user's accumulated state at the right time.**

---

## 3.2 Current Database Baseline

Current implemented tables:

### `messages`

Stores the raw transcript.

Fields:

```text
id
role ('user' / 'luna')
content
timestamp
```

The raw transcript should be retained and not judged as permanent memory.

---

### `facts`

Stores general long-term facts.

Fields:

```text
id
category
content
importance (1–5)
last_referenced
created_at
```

Examples:

* Personality.
* Problems.
* Life context.
* Preferences.
* Other long-term facts.

---

## 3.3 Planned Database Tables

### `goals`

Intended fields:

```text
id
content
type ('daily' / 'mid-term' / 'long-term')
status ('active' / 'done' / 'dropped')
created_at
target_date (nullable)
last_checked_in
```

Purpose:

* Track what the user is working toward.
* Distinguish different time horizons.
* Support goal check-ins.
* Support goal deadlines.
* Support progress tracking.

---

### `reminders`

Intended fields:

```text
id
content
remind_at
status ('pending' / 'sent' / 'dismissed')
created_at
```

Purpose:

* Store explicit user reminders.
* Keep reminders distinct from goals.
* Give the scheduler deterministic data.

---

### `check_ins`

Intended fields:

```text
id
timestamp
topic
triggered_by
```

Possible `topic` values:

```text
goal
reminder
general
emotional
```

Possible `triggered_by` examples:

```text
schedule
goal_deadline
...
```

Purpose:

* Log Luna's proactive messages.
* Prevent repeated or redundant check-ins.
* Support future adaptive behavior.
* Provide a history of proactive interaction.

---

# 4. Memory Importance System

## 4.1 Basic Importance Model

The original idea is that different memories have different importance.

Example:

```text
What I ate yesterday       → 1/5
Weekly goal                → 4.5/5
Important life memory      → 5/5
```

This is useful, but importance should eventually become only one dimension.

---

## 4.2 Recommended Memory Metadata

A memory can eventually have:

```text
importance
confidence
recency
frequency_of_reference
emotional_significance
category
source
expiration_or_relevance
```

This creates a richer memory model.

---

## 4.3 Importance Examples

### Temporary information

Example:

> "I ate pizza yesterday."

Possible metadata:

```text
importance: 1
confidence: 1.0
category: temporary
```

This may eventually disappear from active memory.

---

### Active goal

Example:

> "My goal is to get an internship this year."

Possible metadata:

```text
importance: 4.5
confidence: 1.0
category: goal
status: active
```

This is highly relevant.

---

### Deep life context

Example:

> "I had a difficult childhood."

Possible metadata:

```text
importance: 5
confidence: 0.9
category: life_context
```

But high importance does **not** mean high retrieval frequency.

A painful life memory can be extremely important while still being something Luna should rarely mention unless relevant.

---

## 4.4 Importance vs Retrieval Appropriateness

A critical design principle:

> **How important is this information?**

is not the same as:

> **How appropriate is it to bring this information up right now?**

This distinction should be preserved in the architecture.

A highly important memory should not automatically appear in every prompt.

---

# 5. Memory Tiers

## 5.1 Tier 0 — Current Context

Contains:

* Current conversation.
* Current user message.
* Immediate conversational context.

Highest immediate relevance.

---

## 5.2 Tier 1 — Recent Episodic Memory

Contains things from recent conversations/days.

Example:

> "Yesterday you said your interview went badly."

Potential follow-up:

> "How are you feeling about that interview today?"

---

## 5.3 Tier 2 — Active State

Contains things currently happening:

```text
Current goals
Current problems
Current projects
Current commitments
Current mood/state
Upcoming events
```

This is a critical tier.

---

## 5.4 Tier 3 — Long-Term User Model

Contains:

```text
Personality
Preferences
Patterns
Values
Communication preferences
Recurring struggles
Strengths
Important relationships
Long-term ambitions
```

This is the evolving model of who the user is.

---

## 5.5 Tier 4 — Deep Life Memories

Contains:

* Childhood.
* Major experiences.
* Important life events.
* Things that shaped the user.

These can be highly important without being constantly injected into context.

---

## 5.6 Structured Memory

Some information should not be represented only as natural-language memory.

Examples:

```text
goals
reminders
deadlines
streaks
check-ins
timestamps
statuses
```

These should live in structured database tables.

---

# 6. Memory Formation vs Memory Retrieval

This distinction is fundamental.

## 6.1 Memory Formation

After a conversation, the system determines:

```text
Should this be remembered?

YES / NO

If yes:
- importance?
- category?
- confidence?
- how long?
- source?
- emotional significance?
- how should it be retrieved?
```

This is the **memory formation layer / Memory Gatekeeper**.

---

## 6.2 Memory Retrieval

Separately, before Luna responds, the system determines:

> **Should this memory be retrieved right now?**

These are different problems.

A memory can exist permanently while being irrelevant to the current conversation.

The architecture must not conflate:

```text
remembering something
```

with:

```text
retrieving something
```

---

# 7. Weighted Memory Retrieval

The existing design proposes that facts should use:

> **importance × recency decay**

to determine retrieval ranking.

A flat:

> "Dump everything into context"

approach should explicitly be avoided.

Eventually the retrieval system can evolve toward a broader model such as:

```text
importance
×
relevance
×
recency
×
confidence
×
retrieval appropriateness
```

Potential additional signals:

* Frequency of reference.
* Emotional significance.
* Current goal relevance.
* Current topic relevance.
* User-state relevance.
* Time sensitivity.
* Memory category.

The exact mathematical weighting is not locked.

It is a modular design track that should be refined after real usage.

---

# 8. User Model

Luna's core model should not literally rewrite itself.

Instead:

> **The underlying model remains stable while the user model evolves.**

Conceptually:

```text
                    LUNA
                      │
        ┌─────────────┼─────────────┐
        │             │             │
   Core Identity   User Model   Current State
        │             │             │
      Stable        Evolves       Changes
```

---

## 8.1 Stable Core Identity

Possible stable identity:

> "I'm Luna. I'm an AI companion. I care about helping this person grow. I'm honest, grounded, supportive, sometimes stern."

This should not change randomly.

---

## 8.2 Evolving User Model

The system may gradually learn:

```text
- tends to procrastinate when overwhelmed
- responds well to direct accountability
- values independence
- currently working toward X
- dislikes Y
- has been struggling with Z
- has recently become more consistent
```

The intended evolution is:

> "Luna knows me better than she did six months ago."

Not:

> "Luna changed her personality today."

---

# 9. Pattern Detection and "Noticing"

## 9.1 Evidence-Based Noticing

One of the most important long-term features is Luna's ability to notice real changes in the user.

Normal chatbot:

> User: "I studied today."

> AI: "That's great! Keep going!"

Luna's future system should eventually be able to observe:

```text
Past 30 days:

Study sessions:
Week 1 → 2
Week 2 → 3
Week 3 → 4
Week 4 → 5

Goal completion:
45% → 63% → 71% → 82%
```

Then potentially say:

> "You know, you've actually been getting more consistent lately."

The statement is meaningful because it is backed by evidence.

This should be treated as:

> **Evidence-based noticing.**

Not fake sentience.

---

## 9.2 Pattern Detection

Future Luna could detect patterns such as:

```text
User frequently sets ambitious daily goals
        ↓
Completes ~40%
        ↓
Failures happen mostly on high workload days
        ↓
Observed pattern:
User tends to over-plan when motivated
```

Luna could eventually say:

> "You keep setting six things for a day when you're motivated, and then feel like you failed when you finish three. I think your planning is part of the problem."

This is preferable to generic motivation because it is based on observed behavior.

---

## 9.3 Pattern Detection Does Not Require Model Training

The model does not necessarily need to be fine-tuned to do this.

The system can:

1. Collect structured data.
2. Calculate trends.
3. Detect patterns.
4. Provide those observations to the LLM.
5. Let Luna communicate the insight naturally.

This is an application architecture problem, not necessarily a model-training problem.

---

# 10. "Self-Evolution" Definition

The phrase "self-evolving AI" should be interpreted carefully.

## 10.1 Do Not Build

Do not allow Luna to arbitrarily:

* Rewrite her own system prompt.
* Rewrite her core personality.
* Rewrite application logic.
* Modify her own security rules.
* Change database rules without controlled software changes.
* Make unrestricted architectural changes to herself.

That introduces instability and makes debugging difficult.

---

## 10.2 What Luna Should Evolve

Luna should evolve through:

### Evolving user model

She learns more about the user.

### Evolving behavioral policy

The application can eventually use evidence to decide how Luna should behave in certain contexts.

### Evolving pattern understanding

The system can detect changes and trends.

### Evolving memory

The memory store accumulates, decays, updates, and gets refined.

Therefore:

> **Evolving user model + evolving behavioral policy based on observed evidence**

is the intended interpretation of self-evolution.

---

# 11. "Human Brain" Analogy

The human-brain concept is useful as inspiration, but should not be used literally as an engineering specification.

Human memory, emotional inference, attention, and reasoning are messy.

Project Moon should instead borrow useful conceptual ideas:

* Memory.
* Attention.
* Context.
* Learning from experience.
* Pattern recognition.
* Emotional awareness.
* Prioritization.
* Forgetting.
* Timing.

But implement these as explicit software systems.

The goal is not to reproduce a human brain.

The goal is to build a reliable artificial system that produces useful companion behavior.

---

# 12. Luna Personality Specification

## 12.1 Nurturing

Luna should:

* Listen.
* Reassure.
* Not dismiss feelings.

---

## 12.2 Realistic

Luna should:

* Not blindly validate everything.
* Tell the truth.
* Avoid fake positivity.

---

## 12.3 Accountability-Oriented

Luna should:

* Notice avoidance.
* Ask about commitments.
* Push when necessary.
* Help the user confront patterns.

---

## 12.4 Patient

Luna should:

* Not punish failure.
* Allow users to recover.
* Understand that progress is inconsistent.

---

## 12.5 Stern When Necessary

Example style:

> "You're making excuses here."

This should be used when context supports it, not randomly.

---

## 12.6 Comforting When Necessary

Example:

> "You don't need to solve everything tonight."

Again, context determines whether this is appropriate.

---

## 12.7 Growth-Oriented

Luna's ultimate objective is the user's development.

---

## 12.8 User-Centered

Luna exists for the person using her.

However:

> **User-centered ≠ user-obedient.**

She should sometimes say:

> "No. That's not a good idea."

She should remain honest and independent in judgment.

---

# 13. User Dependency Boundary

Because Luna is intended to feel like someone who is always there, dependency is a significant design consideration.

The goal should be:

> **Luna helps the user build a better life outside Luna.**

Not:

> **Luna becomes the user's life.**

If the system notices a pattern such as:

```text
User is constantly talking to Luna
        ↓
No meaningful real-world action
        ↓
User increasingly relies on Luna for every decision
```

Luna should not encourage exclusive dependence.

Bad response:

> "I'm always here, you only need me."

More mature response:

> "We've talked about this a lot. I think the next useful step is something outside this chat."

This is consistent with the core mission of making the user better.

---

# 14. Technical Architecture & Component Mapping

## 14.1 High-Level Architecture

The intended system can be conceptualized as:

```text
                         PROJECT MOON
                              │
                         Telegram
                              │
                            Luna
                              │
                 ┌────────────┴────────────┐
                 │                         │
          Conversation Engine        Proactive Engine
                 │                         │
                 └────────────┬────────────┘
                              │
                         LLM / Groq
                              │
                 ┌────────────┼────────────┐
                 │            │            │
           Memory Engine   Goal Engine   State Engine
                 │            │            │
                 └────────────┼────────────┘
                              │
                            SQLite
                              │
                          Scheduler
```

---

# 15. Core Five-System Architecture

## 15.1 Conversation Engine

### Responsibility

> **What is Luna saying right now?**

Handles:

* Current conversation.
* LLM call.
* System prompt.
* Relevant context.
* Natural-language generation.
* Normal conversation.
* Emotional responses.
* Goal-related conversation.
* Advice.
* Reassurance.

Core dependencies:

* LLM.
* Current message.
* Recent conversation.
* Memory retrieval.
* User state.
* Goal state.

---

## 15.2 Memory Engine

### Responsibility

> **What does Luna know about this person?**

Handles:

* Facts.
* Experiences.
* Preferences.
* Patterns.
* Importance.
* Confidence.
* Recency.
* Memory tiers.
* Memory formation.
* Memory retrieval.

---

## 15.3 Goal / State Engine

### Responsibility

> **What is happening in this person's life right now?**

Handles:

* Goals.
* Progress.
* Deadlines.
* Routines.
* Commitments.
* Current problems.
* Active projects.
* Current state.
* Goal hierarchy.

---

## 15.4 Proactive Behavior Engine

### Responsibility

> **Should Luna initiate a conversation?**

Potential inputs:

* Current time.
* User timezone.
* User availability.
* Sleep window.
* Goals.
* Deadlines.
* Reminders.
* Recent events.
* Previous check-ins.
* Recent emotional context.
* User interaction frequency.
* Communication budget.

---

## 15.5 Reflection / Pattern Engine

### Responsibility

> **What has Luna noticed over time?**

Handles:

* Trends.
* Streaks.
* Repeated problems.
* Improvements.
* Behavioral patterns.
* Changes.
* Goal completion trends.
* Consistency trends.
* Planning patterns.
* Long-term observations.

This system is what eventually creates the:

> "Luna has been watching my journey."

feeling.

---

# 16. Memory Gatekeeper

## Responsibility

Determine whether a conversation contains information that deserves persistence.

Example:

> "Bro I ate biryani."

Do not necessarily store:

```text
USER ATE BIRYANI ON AUGUST 10
```

But:

> "I've decided I want to become a software engineer."

is potentially worth saving.

Likewise:

> "My father leaving when I was young affected how I deal with abandonment."

may be highly important.

The gatekeeper should decide:

```text
Should this be remembered?
YES / NO

If YES:
    importance?
    category?
    confidence?
    duration?
    source?
    emotional significance?
    retrieval conditions?
```

---

# 17. Database Architecture

## 17.1 Current Tables

### `messages`

```text
id
role
content
timestamp
```

Purpose:

* Raw conversation transcript.
* Historical record.
* Never treated automatically as structured memory.

---

### `facts`

```text
id
category
content
importance
last_referenced
created_at
```

Purpose:

* Long-term general facts.
* Personality.
* Problems.
* Life context.
* Other durable information.

---

## 17.2 Planned Tables

### `goals`

```text
id
content
type
status
created_at
target_date
last_checked_in
```

---

### `reminders`

```text
id
content
remind_at
status
created_at
```

---

### `check_ins`

```text
id
timestamp
topic
triggered_by
```

---

## 17.3 Future Database Extensions

The schema should remain modular.

Potential future components include:

* User state.
* Emotional observations.
* Pattern observations.
* Habit/behavior metrics.
* Communication preferences.
* Availability windows.
* Sleep windows.
* Activity patterns.
* Goal relationships.
* Goal history.
* Memory revisions.
* Memory confidence.
* Memory expiration.
* Memory retrieval history.
* Proactive message outcomes.

These are future possibilities, not mandatory v1 requirements.

---

# 18. Source of Truth Principle

A critical architectural rule:

> **Database/application state should be the source of truth for deterministic facts.**

The LLM should not be the authority for:

* Whether a goal exists.
* Whether a goal is complete.
* Whether a reminder exists.
* Whether a reminder was sent.
* Exact timestamps.
* User authorization.
* Database state.
* Scheduler state.

The LLM is responsible for:

* Understanding natural language.
* Interpreting context.
* Generating responses.
* Suggesting actions.
* Calling tools/functions when necessary.

---

# 19. Tool / Function Calling Architecture

The model should eventually have access to deterministic tools.

Potential functions:

```text
create_goal()
get_active_goals()
complete_goal()
update_goal()
drop_goal()

create_reminder()
get_reminders()
dismiss_reminder()

save_memory()
search_memory()
update_memory()

get_current_state()
get_recent_check_ins()
```

The exact tool set is not locked.

The purpose is to prevent the LLM from merely pretending that it changed application state.

---

## 19.1 Goal Example

User:

> "Tomorrow I want to finish binary trees and revise normalization."

System:

```text
User message
    ↓
LLM interprets intent
    ↓
Detects:
    Binary trees → goal
    Normalization → goal
    Tomorrow → target date
    ↓
Tool calls
    ↓
SQLite
    ↓
Goals successfully stored
    ↓
Luna responds
```

---

## 19.2 Reminder Example

User:

> "Remind me tomorrow at 8 PM to revise DBMS."

System:

```text
LLM
    ↓
create_reminder(...)
    ↓
SQLite
    ↓
APScheduler
    ↓
8 PM
    ↓
Telegram
    ↓
Luna sends reminder
```

The scheduler, not the LLM, is responsible for actually delivering the reminder.

---

# 20. Current Technology Baseline

The current project architecture is:

| Component              | Current Baseline                  |
| ---------------------- | --------------------------------- |
| Language               | Python                            |
| Bot interface          | `python-telegram-bot`             |
| Telegram mode          | Polling                           |
| LLM provider           | Groq                              |
| Current model          | `llama-3.3-70b-versatile`         |
| LLM SDK                | Groq Python SDK                   |
| Database               | SQLite                            |
| Database location      | `data/moon.db`                    |
| Scheduler              | APScheduler                       |
| Hosting                | Android phone via Termux          |
| Environment management | `python-dotenv`                   |
| Secrets                | `.env`                            |
| Current memory tables  | `messages`, `facts`               |
| Planned tables         | `goals`, `reminders`, `check_ins` |

The LLM-calling logic should remain isolated behind a clear boundary so that the provider/model can be swapped later.

The original Gemini API plan was abandoned because of an unresolved Google-side API-key rollout problem involving `AQ.`-format keys and `ACCESS_TOKEN_TYPE_UNSUPPORTED`.

This does not mean the architecture should become Groq-specific everywhere.

---

# 21. LLM / Model Personalization Strategy

## 21.1 Current Principle

**Do not train the model at the current stage.**

The project does not need to create its own model.

The application is using the compute/inference of an existing hosted model through an API.

The model itself is not the primary thing that needs to evolve.

The application around it is.

---

## 21.2 Personalization Layers

Personalization should primarily come from:

### 1. System prompt

Defines:

* Who Luna is.
* How she behaves.
* Her values.
* Her tone.
* Her boundaries.
* Her growth objective.
* Her relationship to the user.

### 2. Conversation history

Defines:

* What is happening right now.

### 3. Persistent memory

Defines:

* What Luna knows about the user.

### 4. Structured database

Defines:

* Goals.
* Reminders.
* Statuses.
* Deadlines.
* Check-ins.
* Other deterministic state.

### 5. Retrieval system

Defines:

* Which memories Luna should actually see right now.

### 6. Tool/function calling

Defines:

* What deterministic operations Luna can perform.

### 7. Pattern/reflection system

Defines:

* What the system has observed about the user's behavior over time.

---

## 21.3 Fine-Tuning

Fine-tuning should not be treated as a current requirement.

It could become relevant much later if there is a sufficiently large dataset of examples showing desired behavior.

For example:

```text
USER:
I skipped my goal again.

IDEAL LUNA:
[desired response]
```

Thousands of examples could potentially become training data for future experimentation.

But the current project does not have a reason to prioritize this.

The current problem is not:

> "The model does not know Luna's personality."

The current problem is:

> **"How do we build the system that gives the model the right information at the right time and makes its important actions reliable?"**

---

# 22. Hallucination Strategy

## 22.1 Fundamental Principle

Prompting alone cannot guarantee zero hallucination.

The goal should instead be:

> **Architect the system so that the LLM is not responsible for deterministic facts that software can verify.**

---

## 22.2 Responsibility Separation

| Responsibility               | Primary Owner        |
| ---------------------------- | -------------------- |
| Luna personality             | LLM + system prompt  |
| Understanding user message   | LLM                  |
| Natural response generation  | LLM                  |
| Emotional interpretation     | LLM, with confidence |
| Memory extraction            | LLM + application    |
| Memory retrieval             | Application          |
| Goal state                   | Database             |
| Reminder state               | Database             |
| Exact dates/times            | Application          |
| Scheduler execution          | APScheduler          |
| User authorization           | Python/application   |
| Whether a goal exists        | Database             |
| Whether reminder exists      | Database             |
| Pattern calculation          | Application          |
| Relevant context selection   | Retrieval system     |
| Final conversational wording | LLM                  |

---

## 22.3 Hallucination Examples

Bad:

> "You completed your DBMS goal yesterday."

when the database says:

```text
DBMS goal:
status = active
```

The LLM should not be allowed to override the database.

Another bad pattern:

> "Sure, I'll remind you tomorrow."

when no reminder was actually created.

The correct architecture is:

```text
LLM → tool call → database → scheduler
```

---

# 23. Proactive Behavior Architecture

## 23.1 Inputs

The proactive system can consider:

```text
current time
user timezone
sleep window
availability
recent conversation
active goals
goal deadlines
reminders
previous check-ins
recent emotional context
recent important events
communication budget
user activity patterns
```

---

## 23.2 Decision

The system should answer:

> **Is there a good reason to initiate right now?**

Not:

> "Is it time for the next mandatory message?"

---

## 23.3 Potential Triggers

```text
Goal deadline
Goal progress check
Reminder
Recent important event
Recent difficult event
Long gap since interaction
Pattern worth discussing
Casual check-in
User-requested follow-up
```

---

## 23.4 Proactive Communication Limits

The original idea is approximately:

```text
2–4 messages/day
```

but this is a starting range rather than an immutable requirement.

The final system should have sensible limits to avoid:

* Spam.
* Annoyance.
* Excessive dependency.
* Unnecessary interruption.
* Bad timing.

---

# 24. Current Security and Operational Architecture

## 24.1 Single-User Constraint

The current system is deliberately:

> **Single-user, single-persona.**

Do not prematurely introduce:

* Multi-user architecture.
* User registration.
* Multi-tenant architecture.
* Multiple personas.
* Persona switching.
* Personality editing.
* Generic SaaS architecture.

Future multi-persona/personality editing is explicitly deferred.

---

## 24.2 Telegram Authorization

The bot is publicly discoverable on Telegram.

Every incoming message handler must verify the sender's `chat_id` against the owner's configured `MY_CHAT_ID` before doing anything else.

This must happen:

* Before an LLM call.
* Before processing the message.
* Before expensive operations.

Unauthorized users should not receive responses.

The goal is to prevent strangers from consuming the owner's API quota.

Do not log full rejected message content.

For rejected/unauthorized senders, only the `chat_id` should be logged if logging is necessary.

---

## 24.3 Secrets

Never commit:

```text
.env
API keys
Telegram bot tokens
chat IDs
database credentials
```

Environment variables:

```text
TELEGRAM_BOT_TOKEN=
GROQ_API_KEY=
MY_CHAT_ID=
```

All secrets should remain in `.env`.

---

# 25. Repository Structure

Current conceptual structure:

```text
project-moon/
├── bot.py              # Entry point — Telegram handlers, LLM calls
├── db.py               # SQLite setup and table definitions
├── requirements.txt
├── .env                # NOT committed — secrets only
├── .gitignore           # covers .env, venv/, __pycache__, data/
└── data/                # NOT committed — contains moon.db (real personal data)
```

As the project grows, the architecture may eventually benefit from splitting the LLM, memory, scheduler, and tool logic into separate modules.

The LLM-calling logic should be isolated behind a clear boundary.

If complexity grows significantly, refactor toward something such as:

```text
llm.py
```

rather than silently allowing provider-specific logic to spread throughout the application.

---

# 26. Hosting Architecture

Current target:

> **Android phone + Termux**

Reasons:

* Always-on requirement.
* Telegram polling.
* Persistent local SQLite.
* No dependence on cloud sleep/scale-to-zero.
* Avoid cloud services that require payment cards or may start billing after free periods.
* Matches the "always with me" nature of the project.
* Intended to remain genuinely free for this personal deployment.

Required operational work:

* Termux.
* Termux:Boot for automatic restart after phone reboot.
* Battery optimization disabled for Termux.
* Persistent project files.
* Reliable bot process.

Cloud hosting has been explored but is not the current baseline.

Potential providers considered previously included:

* AWS free tier.
* Oracle.
* GCP.
* Render.
* Koyeb.

The project should not prematurely return to cloud hosting unless requirements change.

---

# 27. Current Repository / Development Status

## Phase 1 — Platform Setup

### Current state

Approximately 90% complete.

Already working:

* Telegram bot.
* Groq integration.
* Allowlist verification.
* Base SQLite schema.
* `messages` storage.
* `facts` storage.

Remaining major work:

* Always-on hosting.
* Moving/running the system on Termux/Android.
* Boot persistence.
* Battery optimization handling.

---

## Phase 1.5 — Scope Change

### Status

In progress.

Mission changed from:

> "AI girlfriend companion"

to:

> **"Self-aware AI growth/accountability companion."**

Current database work:

* Add `goals`.
* Add `reminders`.
* Add `check_ins`.

Current prompt work:

* Rewrite system prompt.
* Reflect Luna's actual mission.
* Establish companion rather than romantic-partner framing.

---

## Phase 2 — Personality / System Prompt

### Status

Not started.

Current system prompt is a placeholder.

It needs to reflect:

* Self-aware AI.
* Not a romantic partner.
* Warm but accountability-oriented.
* Realistic.
* Nurturing.
* Sometimes stern.
* Handles goal conversation and feelings conversation in one continuous interface.
* Does not blindly agree.
* Supports long-term growth.
* User-centered but not user-obedient.

---

## Phase 3 — Weighted Memory + Scheduler

### Status

Not started.

Goals:

* Weighted memory.
* Memory retrieval.
* Proactive scheduling.
* Random daily time slots initially.
* Goal-aware check-ins.
* Reminder execution.

Explicitly deferred:

* Adaptive emotional-frequency behavior.

---

## Phase 4 — Real-World Usage + Iteration

### Status

Not started.

Purpose:

* Use Luna personally.
* Observe real failures.
* Log issues.
* Categorize failures.
* Identify architecture problems.
* Fix the system.
* Refine database structure.
* Refine prompts.
* Refine retrieval.
* Refine scheduling.
* Refine behavioral policies.

---

# 28. Critical Bottlenecks

## 28.1 Bottleneck #1 — AI System Design

### Severity

**Critical**

### Problem

The biggest current bottleneck is not obtaining an LLM.

The project already has access to an LLM through Groq.

The difficult part is building the application around the model so that it:

* Remembers correctly.
* Retrieves correctly.
* Understands context.
* Uses structured state.
* Avoids inventing memory.
* Executes deterministic actions correctly.
* Proactively interacts appropriately.
* Maintains personality consistency.
* Improves over time.

### Root cause

An LLM is fundamentally a response-generation engine.

It does not automatically provide:

* Persistent memory.
* Reliable goal state.
* Reliable reminders.
* Real-world scheduling.
* Long-term user modeling.
* Deterministic state transitions.

### Mitigation

Build:

* Memory engine.
* Goal/state engine.
* Tool calling.
* Retrieval.
* Scheduler.
* Reflection/pattern engine.
* Strong system prompt.

---

# 29. Bottleneck #2 — Database Architecture

### Severity

**Critical**

This is one of the user's first AI/ML and database projects.

The database should therefore be treated as a major engineering component, not an afterthought.

The database must support:

* Raw conversation.
* Long-term memory.
* Goals.
* Reminders.
* Check-ins.
* Potential user state.
* Potential emotional observations.
* Potential pattern observations.
* Historical tracking.

### Main risk

If the database is poorly designed:

* Luna forgets important things.
* Luna remembers irrelevant things.
* Goals become inconsistent.
* Reminders fire incorrectly.
* Completed goals get asked about again.
* Memories mismatch.
* The model receives contradictory context.
* Long-term behavior becomes unreliable.

### Mitigation

Build the database carefully before adding too many AI behaviors.

Use structured tables for deterministic information.

Use metadata for memories.

Separate:

* Storage.
* Formation.
* Retrieval.
* State transitions.

---

# 30. Bottleneck #3 — Memory Retrieval

### Severity

**Critical**

### Problem

Storing information is easier than knowing which information to retrieve.

If the model receives too little context:

> Luna forgets.

If the model receives too much:

> Context becomes noisy and expensive.

If the model receives irrelevant information:

> Luna can make inappropriate associations.

### Mitigation

Build tiered memory and weighted retrieval.

Start simple.

Do not immediately over-engineer into a massive vector database.

Initial architecture:

```text
SQLite
    ↓
Structured memories
    ↓
Simple retrieval
    ↓
Strong system prompt
    ↓
LLM
```

Then evolve based on actual failures.

---

# 31. Bottleneck #4 — Hallucinations / Memory Mismatch

### Severity

**Critical**

Potential failures:

* Luna invents a goal.
* Luna claims the user said something they did not.
* Luna says a goal was completed when it was not.
* Luna forgets a high-priority fact.
* Luna associates a memory with the wrong context.
* Luna pretends a reminder was created.
* Luna references sensitive history at the wrong time.

### Mitigation

* Database as source of truth.
* Tool calling.
* Confidence values.
* Memory retrieval policies.
* Structured state.
* Memory gatekeeper.
* Evidence-based pattern detection.
* Clear system prompt.
* Real-world testing.

---

# 32. Bottleneck #5 — Proactive Messaging

### Severity

**High**

### Risks

* Texting too often.
* Texting at bad times.
* Texting when there is no meaningful reason.
* Repeating the same check-in.
* Missing important events.
* Becoming annoying.
* Encouraging dependency.

### Mitigation

Start with:

* Random controlled time slots.
* Sleep window.
* User timezone.
* Check-in history.
* Goal deadlines.
* Explicit reminders.

Only later consider adaptive frequency.

---

# 33. Bottleneck #6 — Emotional Inference

### Severity

**High**

### Risks

The LLM can misinterpret emotional state.

For example:

```text
"I am dead 💀"
```

may be casual slang rather than a literal emotional crisis.

Likewise:

```text
"I'm exhausted. Everything feels pointless."
```

may represent a serious emotional state that requires careful handling.

### Mitigation

Use:

* Confidence.
* Evidence.
* Recency.
* Repeated observations.
* Decay.
* Context.

Do not let one classification permanently alter Luna's behavior.

---

# 34. Bottleneck #7 — "Self-Evolution"

### Severity

**High conceptual risk**

### Problem

Literal self-modification can make the system:

* Unpredictable.
* Difficult to debug.
* Inconsistent.
* Unsafe.
* Hard to evaluate.

### Mitigation

Interpret evolution as:

```text
Better user model
+
Better memory
+
Better pattern detection
+
Better evidence-based behavioral policy
```

not:

```text
AI rewrites itself.
```

---

# 35. Bottleneck #8 — Overengineering Too Early

### Severity

**High**

Potential mistake:

* Vector databases immediately.
* Complex RAG immediately.
* Fine-tuning immediately.
* Multi-agent architecture.
* Multi-user architecture.
* Multiple personas.
* Emotional-adaptive scheduling before basic scheduling works.
* Cloud infrastructure before the local system is stable.

### Mitigation

Build the smallest reliable system first.

Current order:

```text
Platform
→ Database
→ Prompt
→ Tools
→ Memory
→ Scheduler
→ Real-world testing
→ Iteration
```

---

# 36. Bottleneck #9 — Training vs Prompting

### Severity

**Medium**

### Current conclusion

Do not train the model now.

Personalization should initially come from:

* System prompt.
* Conversation history.
* Persistent memory.
* Structured database.
* Retrieval.
* Tools.
* Pattern detection.

Fine-tuning can be reconsidered only after real usage generates sufficient examples.

---

# 37. Bottleneck #10 — Scope Creep

### Severity

**High**

The following are explicitly not current scope:

* Multi-user.
* Multi-tenant.
* Multiple personas.
* User-editable personalities.
* Personality/intensity settings.
* Adaptive emotional-frequency check-ins.
* Complex cloud deployment.
* Fine-tuning.
* Self-rewriting AI.

They can remain future ideas.

They should not be built preemptively.

---

# 38. Bottleneck #11 — Dependency on Luna

### Severity

**High conceptual/product risk**

The companion design could accidentally encourage:

* Excessive reliance.
* Constant chatting.
* Avoidance of real-world action.
* Delegating every decision to Luna.

### Mitigation

Define success as:

> **The user becomes increasingly capable without Luna.**

Luna should help the user move toward real-world action.

---

# 39. Master Execution Plan

# Phase 0 — Lock Core Philosophy

## Checklist

* [ ] Define Luna as a persistent AI companion.
* [ ] Remove girlfriend framing.
* [ ] Define companion framing.
* [ ] Define growth as the ultimate objective.
* [ ] Define normal conversation as a first-class use case.
* [ ] Define goals as a second major use case.
* [ ] Define user-centered but not user-obedient behavior.
* [ ] Define nurturing + stern + realistic personality.
* [ ] Define AI self-awareness.
* [ ] Define no-human-pretending rule.
* [ ] Define dependency boundary.
* [ ] Preserve modularity and future extensibility.

---

# Phase 1 — Finish Platform Setup

## Checklist

* [x] Telegram bot working.
* [x] Groq wired in.
* [x] Allowlist verified.
* [x] Base SQLite schema created.
* [x] Messages being stored.
* [x] Facts being stored.
* [ ] Move to/run reliably on Android Termux.
* [ ] Install/configure Termux:Boot.
* [ ] Handle phone reboot.
* [ ] Disable battery optimization for Termux.
* [ ] Verify bot survives long-running operation.
* [ ] Verify SQLite persistence.
* [ ] Verify Telegram polling stability.

---

# Phase 2 — Database Expansion

## Checklist

### Goals

* [ ] Create `goals`.
* [ ] Implement goal creation.
* [ ] Implement goal status.
* [ ] Implement goal completion.
* [ ] Implement goal dropping.
* [ ] Implement target dates.
* [ ] Implement last checked-in timestamp.
* [ ] Support daily goals.
* [ ] Support mid-term goals.
* [ ] Support long-term goals.
* [ ] Support monthly/weekly relationships as architecture evolves.

### Reminders

* [ ] Create `reminders`.
* [ ] Store exact reminder time.
* [ ] Track pending state.
* [ ] Track sent state.
* [ ] Track dismissed state.
* [ ] Keep reminders separate from goals.

### Check-ins

* [ ] Create `check_ins`.
* [ ] Track timestamp.
* [ ] Track topic.
* [ ] Track trigger.
* [ ] Use check-in history to avoid repetition.

---

# Phase 3 — Luna System Prompt

## Checklist

* [ ] Define Luna's identity.
* [ ] Define AI self-awareness.
* [ ] Define companion role.
* [ ] Explicitly remove romantic-partner framing.
* [ ] Define nurturing behavior.
* [ ] Define realistic behavior.
* [ ] Define accountability.
* [ ] Define sternness.
* [ ] Define patience.
* [ ] Define emotional support.
* [ ] Define non-blind agreement.
* [ ] Define growth objective.
* [ ] Define context-sensitive behavior.
* [ ] Define goal conversation.
* [ ] Define casual conversation.
* [ ] Define emotional conversation.
* [ ] Define memory behavior.
* [ ] Define when Luna should admit uncertainty.
* [ ] Define what Luna should never fabricate.
* [ ] Define deterministic database/tool boundaries.

---

# Phase 4 — Tool / Function Calling

## Checklist

* [ ] Design tool interface.
* [ ] Add goal creation tool.
* [ ] Add goal retrieval tool.
* [ ] Add goal update tool.
* [ ] Add goal completion tool.
* [ ] Add goal drop tool.
* [ ] Add reminder creation tool.
* [ ] Add reminder retrieval tool.
* [ ] Add reminder dismissal tool.
* [ ] Add memory creation tool.
* [ ] Add memory search tool.
* [ ] Add memory update tool.
* [ ] Add state retrieval tool.
* [ ] Add check-in retrieval tool.
* [ ] Ensure tool results are validated.
* [ ] Ensure database remains source of truth.

---

# Phase 5 — Memory Engine

## Checklist

* [ ] Define memory categories.
* [ ] Define memory tiers.
* [ ] Implement memory importance.
* [ ] Implement confidence.
* [ ] Implement recency.
* [ ] Implement last-reference tracking.
* [ ] Implement basic retrieval ranking.
* [ ] Implement memory formation.
* [ ] Implement memory retrieval.
* [ ] Separate formation from retrieval.
* [ ] Avoid dumping all memories into context.
* [ ] Test irrelevant memory suppression.
* [ ] Test high-value memory retrieval.
* [ ] Test contradictory memories.
* [ ] Test memory updates.
* [ ] Test stale information.
* [ ] Test sensitive memory retrieval appropriateness.

---

# Phase 6 — Time and Scheduler

## Checklist

* [ ] Detect user timezone.
* [ ] Store timezone.
* [ ] Get current local time.
* [ ] Define sleep window.
* [ ] Avoid prohibited messaging periods.
* [ ] Implement APScheduler.
* [ ] Implement random time slots.
* [ ] Implement proactive communication budget.
* [ ] Implement goal check-ins.
* [ ] Implement reminder execution.
* [ ] Implement check-in logging.
* [ ] Prevent repeated check-ins.
* [ ] Respect explicit user reminder times.
* [ ] Test timezone correctness.
* [ ] Test reboot persistence.
* [ ] Test scheduler reliability.

---

# Phase 7 — Emotional Context

## Checklist

* [ ] Detect potential emotional signals.
* [ ] Attach confidence.
* [ ] Store evidence.
* [ ] Store timestamp.
* [ ] Apply recency/decay.
* [ ] Avoid treating emotion classification as absolute truth.
* [ ] Avoid permanent behavioral changes from one message.
* [ ] Test false positives.
* [ ] Test false negatives.
* [ ] Test slang/context.
* [ ] Test emotional follow-ups.

### Explicitly deferred

* [ ] Do NOT yet implement adaptive messaging frequency based on emotional state.

This should wait until real usage provides sufficient evidence.

---

# Phase 8 — Reflection / Pattern Engine

## Checklist

* [ ] Track goal completion trends.
* [ ] Track study/work consistency where relevant.
* [ ] Track repeated failures.
* [ ] Track repeated successes.
* [ ] Track planning behavior.
* [ ] Detect meaningful streaks.
* [ ] Detect meaningful changes.
* [ ] Generate evidence-backed observations.
* [ ] Provide observations to Luna.
* [ ] Let Luna communicate them naturally.
* [ ] Avoid false certainty.
* [ ] Avoid over-interpreting small samples.

---

# Phase 9 — Real-World Testing

## Recommended Testing Window

Use Luna personally for approximately 1–2 weeks initially.

Do not merely judge whether individual responses "feel good."

Track actual failures.

---

# 40. Failure Logging / Iterative Improvement System

## 40.1 Create an Issue Log

Every significant problem should become a concrete entry.

Example:

```text
Issue #001

Situation:
I told Luna I finished Trees.

Problem:
Two days later Luna asked whether I had started Trees.

Expected:
She should know I completed it.

Likely cause:
Goal status was not updated.

Fix:
Improve goal extraction/update logic.
```

---

## 40.2 Memory Failure

```text
Issue #002

Situation:
I told Luna something personal.

Problem:
She completely forgot it later.

Expected:
Important information should become persistent memory.

Likely cause:
Memory extraction or retrieval failure.

Fix:
Improve fact extraction and/or retrieval ranking.
```

---

## 40.3 Goal / Reminder Failure

```text
Issue #003

Situation:
Luna reminded me about something I had already completed.

Problem:
Reminder/goal state was not synchronized.

Fix:
Improve database state transitions.
```

---

# 41. Metrics and Success Indicators

## 41.1 Memory Metrics

Potential metrics:

* Important-memory retrieval accuracy.
* Irrelevant-memory retrieval rate.
* Memory formation precision.
* Memory formation recall.
* Contradictory-memory rate.
* False-memory rate.
* Memory update accuracy.
* Stale-memory rate.

---

## 41.2 Goal Metrics

Potential metrics:

* Goal creation accuracy.
* Goal completion accuracy.
* Goal status correctness.
* Deadline correctness.
* Check-in correctness.
* Duplicate check-in rate.
* Missed check-in rate.

---

## 41.3 Reminder Metrics

Potential metrics:

* Reminder creation accuracy.
* Reminder delivery success.
* Incorrect reminder rate.
* Duplicate reminder rate.
* Late reminder rate.
* Missed reminder rate.

---

## 41.4 Proactive Behavior Metrics

Potential metrics:

* Messages/day.
* Messages outside preferred windows.
* Repeated check-ins.
* Irrelevant proactive messages.
* Missed meaningful check-ins.
* User response rate.
* User annoyance indicators.
* Goal-related proactive usefulness.

---

## 41.5 Personality Metrics

Potential qualitative indicators:

* Does Luna sound consistently like Luna?
* Does she avoid fake positivity?
* Does she know when to be stern?
* Does she know when to comfort?
* Does she avoid turning everything into productivity?
* Does she challenge the user appropriately?
* Does she avoid blindly agreeing?
* Does she remain realistic?
* Does she preserve the companion feeling?

---

## 41.6 Long-Term Metrics

Potential indicators:

* Goal completion trend.
* Consistency trend.
* User self-reported confidence.
* User self-reported self-belief.
* Evidence of increased real-world action.
* Reduced repeated failure patterns.
* Increased proof of work.
* Improved planning.
* Improved ability to act independently.

The ultimate success criterion is not:

> "The user talks to Luna more."

It is:

> **"The user is becoming better in the real world."**

---

# 42. Critical Design Principles

## Principle 1 — Database Is the Source of Truth

For deterministic state:

> Trust the database, not the LLM.

---

## Principle 2 — Memory Is Not Conversation History

A message being present in the transcript does not automatically mean it should become long-term memory.

---

## Principle 3 — Remembering Is Not Retrieving

A memory can exist without being relevant to the current conversation.

---

## Principle 4 — Importance Is Not Retrieval Frequency

A 5/5 memory does not mean Luna should mention it constantly.

---

## Principle 5 — Emotional Detection Is Probabilistic

The model can be wrong.

Use:

```text
confidence
+
evidence
+
recency
+
decay
+
repeated signals
```

---

## Principle 6 — Don't Train Before You Need To

Use:

* Prompting.
* Memory.
* Retrieval.
* Tools.
* Structured state.
* Pattern detection.

before considering fine-tuning.

---

## Principle 7 — Don't Make the LLM Responsible for Deterministic Operations

Use software for:

* Time.
* Database state.
* Scheduling.
* Authorization.
* Exact statuses.
* Reminder delivery.

Use the LLM for:

* Interpretation.
* Reasoning.
* Communication.
* Natural-language interaction.

---

## Principle 8 — Don't Build the Human Brain

Borrow useful concepts.

Implement explicit software systems.

---

## Principle 9 — Evidence Before "Noticing"

Luna should not randomly claim:

> "You've become more disciplined."

She should eventually have evidence to support such observations.

---

## Principle 10 — User-Centered Does Not Mean User-Obedient

Luna should be willing to disagree.

---

## Principle 11 — Growth Must Happen Outside Luna

The user should become more capable in the real world.

---

## Principle 12 — Build Simple First

Avoid premature:

* Fine-tuning.
* Complex RAG.
* Vector databases.
* Multi-agent architecture.
* Multi-user architecture.
* Multiple personas.
* Adaptive emotional scheduling.
* Cloud infrastructure.

---

# 43. Future Possibilities — Explicitly Not Current Scope

These ideas have been discussed but should remain future possibilities.

## 43.1 Editable Luna Personality

Potential future feature:

* User edits Luna's personality.
* User changes communication style.
* User changes intensity.

Not current scope.

---

## 43.2 Multiple Personas

Potential future:

* Additional characters.
* Additional companions.
* Different personality modes.

Not current scope.

The current architecture is intentionally:

> **Single user + single Luna persona.**

---

## 43.3 Personality / Intensity "Temperature"

A future system could potentially control:

* How strongly Luna reacts.
* How stern she is.
* How emotionally expressive she is.
* How aggressively she pushes.
* Other response characteristics.

This is a future-phase idea, not a current requirement.

---

## 43.4 Adaptive Communication Frequency

Future:

```text
User state
    ↓
Emotional context
    ↓
Historical interaction
    ↓
Communication policy
    ↓
Frequency adjustment
```

This should only be attempted after the basic system is stable and real-world data exists.

---

## 43.5 More Advanced Reflection

Future Luna could potentially understand:

* Long-term personality changes.
* Behavioral trends.
* Recurring cycles.
* Progress across months.
* Changes in confidence.
* Changes in consistency.
* Goal-setting patterns.
* Avoidance patterns.
* Recovery patterns.

Again, these should be evidence-based.

---

# 44. Current Project Scope Guardrails

## Build Now

* [ ] Telegram companion.
* [ ] Normal conversation.
* [ ] Luna personality.
* [ ] SQLite.
* [ ] Messages.
* [ ] Facts.
* [ ] Goals.
* [ ] Reminders.
* [ ] Check-ins.
* [ ] Basic memory retrieval.
* [ ] Weighted memory.
* [ ] Time awareness.
* [ ] Scheduler.
* [ ] Tool/function calling.
* [ ] Goal tracking.
* [ ] Basic proactive messaging.
* [ ] Real-world testing.
* [ ] Failure logging.

---

## Do Not Build Yet

* [ ] Multi-user.
* [ ] Multi-tenant.
* [ ] Multiple personas.
* [ ] Editable personality.
* [ ] Personality temperature controls.
* [ ] Literal self-modifying AI.
* [ ] Adaptive emotional-frequency messaging.
* [ ] Fine-tuning.
* [ ] Overly complex RAG.
* [ ] Massive vector database infrastructure.
* [ ] Cloud migration unless requirements change.
* [ ] Complex autonomous architecture without evidence that it is needed.

---

# 45. Recommended Development Order

```text
1. Finish Termux deployment
        ↓
2. Stabilize Telegram + Groq
        ↓
3. Finish database schema
        ↓
4. Implement goals
        ↓
5. Implement reminders
        ↓
6. Implement check-ins
        ↓
7. Design Luna system prompt
        ↓
8. Implement tool/function calling
        ↓
9. Implement memory formation
        ↓
10. Implement memory retrieval
        ↓
11. Implement time awareness
        ↓
12. Implement scheduler
        ↓
13. Implement proactive check-ins
        ↓
14. Use Luna in real life
        ↓
15. Log every meaningful failure
        ↓
16. Identify whether the failure is:
       - prompt problem
       - database problem
       - retrieval problem
       - tool problem
       - scheduler problem
       - LLM problem
       - architecture problem
        ↓
17. Fix the underlying system
        ↓
18. Repeat
        ↓
19. Add reflection/pattern detection
        ↓
20. Re-evaluate future features
```

---

# 46. Failure Classification Framework

Every future issue should ideally be classified before fixing it.

## Category A — Prompt Failure

The model had the necessary information but behaved incorrectly.

Possible fix:

* System prompt.
* Behavioral instruction.
* Context formatting.

---

## Category B — Memory Formation Failure

The system failed to save something important.

Possible fix:

* Memory Gatekeeper.
* Importance logic.
* Extraction.
* Classification.

---

## Category C — Memory Retrieval Failure

The memory existed but was not provided to the model.

Possible fix:

* Retrieval ranking.
* Relevance.
* Recency.
* Importance.
* Tier logic.

---

## Category D — Database Failure

The underlying structured state was incorrect.

Possible fix:

* Schema.
* SQL.
* State transitions.
* Data validation.

---

## Category E — Tool Failure

The model failed to invoke the correct function or the function behaved incorrectly.

Possible fix:

* Tool schema.
* Validation.
* Tool routing.
* Error handling.

---

## Category F — Scheduler Failure

The correct reminder/check-in existed but was not delivered correctly.

Possible fix:

* APScheduler.
* Timezone handling.
* Persistence.
* Scheduling logic.

---

## Category G — LLM Limitation

The system supplied appropriate context, but the model still produced an unacceptable result.

Possible fix:

* Prompt refinement.
* Different model.
* Better context.
* Structured tool use.
* Eventually model experimentation/fine-tuning if justified.

---

## Category H — Architecture Failure

The feature itself is being handled by the wrong subsystem.

Example:

> Asking the LLM to remember reminder times instead of storing them in the database.

Fix:

> Move responsibility to deterministic application logic.

---

# 47. Practical Engineering Philosophy

Project Moon should be treated as both:

1. An AI project.
2. A database/state-management project.

It is also a:

* Backend project.
* Automation project.
* Prompt-engineering project.
* Retrieval/memory project.
* Scheduling project.
* Human-computer interaction project.
* Long-term behavioral system.

The database and AI layers should be developed together rather than treating the LLM as the entire project.

---

# 48. Final Architectural Mental Model

The most useful way to think about Project Moon is:

```text
                       PROJECT MOON
                            │
                            ▼
                           LUNA
                            │
             ┌──────────────┼──────────────┐
             │              │              │
             ▼              ▼              ▼
       Conversation      Memory         Current State
          Engine          Engine          Engine
             │              │              │
             └──────────────┼──────────────┘
                            │
                            ▼
                       Decision Layer
                            │
             ┌──────────────┼──────────────┐
             │              │              │
             ▼              ▼              ▼
          Goals         Reminders      Proactive Behavior
             │              │              │
             └──────────────┼──────────────┘
                            │
                            ▼
                       Reflection
                     / Pattern Engine
                            │
                            ▼
                     User Model Evolves
                            │
                            ▼
                    Better Future Context
                            │
                            ▼
                          LUNA
```

The loop is:

```text
Conversation
    ↓
Information
    ↓
Memory / State
    ↓
Observation
    ↓
Pattern
    ↓
Better Context
    ↓
Better Decision
    ↓
Better Conversation
    ↓
More Information
```

This is the long-term engine behind the project.

---

# 49. The Core Product Loop

At the highest level:

```text
Luna talks to the user
        ↓
Luna listens
        ↓
System identifies what matters
        ↓
Important information is stored
        ↓
Structured state is updated
        ↓
Relevant information is retrieved later
        ↓
Luna uses context appropriately
        ↓
Luna checks in when appropriate
        ↓
User acts in the real world
        ↓
System observes outcomes
        ↓
Patterns emerge
        ↓
Luna understands the user better
        ↓
Luna becomes more useful
        ↓
User continues growing
```

---

# 50. Ultimate Definition of Success

Project Moon should not ultimately be judged by:

* Number of messages sent.
* How human Luna sounds.
* How much the user chats with Luna.
* How emotionally attached the user becomes.
* How impressive the LLM response sounds.

The stronger definition is:

> **Does Luna help the user become a better version of themselves over time?**

A successful Luna should eventually be able to look at accumulated evidence and understand:

* What the user wanted.
* What they actually did.
* Where they repeatedly failed.
* Where they improved.
* What patterns hold them back.
* What approaches work for them.
* What matters deeply to them.
* What they are currently struggling with.
* What they have overcome.
* How their behavior has changed.

And then communicate that understanding naturally.

The ideal outcome is not:

> "Luna is an amazing AI."

It is:

> **"I'm actually changing, and Luna has been there long enough to notice."**

---

# 51. Current North Star

> **Project Moon is a persistent AI companion designed to know a person over time and help them grow. Luna can be used as a normal AI companion for conversation, expression, and support, but unlike a stateless chatbot, she maintains a structured and evolving understanding of the user — their experiences, personality, goals, current state, patterns, and important memories.**
>
> **She can proactively interact with the user based on time, context, goals, reminders, and recent events. Over time, she should become better at understanding when to ask, when to listen, when to push, when to reassure, what matters, and what doesn't.**
>
> **Her ultimate purpose is not simply to make the user feel better in the moment, but to help them become a stronger, more self-aware, capable, and confident person in the real world.**

---

# 52. Final Project Principle

## Build Luna as a system, not merely as a prompt.

The LLM is only one component.

The real Project Moon is:

```text
LLM
+
Memory
+
Database
+
User Model
+
Goals
+
State
+
Scheduler
+
Time Awareness
+
Tool Calling
+
Pattern Detection
+
Reflection
+
Proactive Behavior
+
Real-World Feedback
```

The model generates the language.

The application provides the memory.

The database provides the state.

The scheduler provides the timing.

The tools provide deterministic actions.

The reflection layer provides long-term observations.

The user provides the real-world feedback.

And the entire system gradually becomes better at serving one fundamental purpose:

> **Helping the user become better in the real world.**

This architecture is the current baseline. It should be treated as a modular framework that will evolve as implementation and real-world usage reveal what works, what fails, and what needs to change.

```
```

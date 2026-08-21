"""Behavioral contract for implemented Phase-1 proactive goal check-ins.

Implementation source: scheduler.py
- Triggers: goal_deadline_approaching, stale_active_goal
- Quiet hours: 23:00–08:00 Asia/Kolkata (08:00 is the first active minute)
- Rolling 24h budget: 2 check-ins (counted from check_ins.timestamp, UTC)
- Global cooldown: 3 hours since the most recent check_in
- Per-goal cooldowns: 48h (deadline) / 5d (stale), keyed off goals.last_checked_in
- Only active goals are scanned
- At most one check-in per scheduler invocation
- Deterministic templates; no LLM call in V1

Timezone contract:
- goals.target_date uses Asia/Kolkata wall-clock strings (same as reminders)
- check_ins.timestamp, goals.created_at, goals.last_checked_in use UTC strings
  from SQLite CURRENT_TIMESTAMP semantics

Delivery / bookkeeping contract (resolves the send-then-book duplicate risk):
- Book first: atomically create_check_in + update_goal_last_checked_in
- Then deliver via Telegram
- If Telegram delivery fails, roll back both DB mutations
- Therefore Telegram must NOT be called when pre-send bookkeeping fails
- A successful Telegram delivery must always find bookkeeping already committed
"""

import os
import tempfile
import unittest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch
from zoneinfo import ZoneInfo

import db
from scheduler import TIMEZONE, check_proactive_triggers

# --- V1 contract constants (implementation must match) ---
TRIGGER_GOAL_DEADLINE = "goal_deadline_approaching"
TRIGGER_STALE_GOAL = "stale_active_goal"
CHECK_IN_TOPIC = "goal"
DAILY_BUDGET = 2
GLOBAL_COOLDOWN_HOURS = 3
DEADLINE_WINDOW_HOURS = 24
DEADLINE_COOLDOWN_HOURS = 48
STALE_THRESHOLD_DAYS = 5
STALE_COOLDOWN_DAYS = 5

# Mid-afternoon on a weekday — outside quiet hours and easy to reason about.
FIXED_NOW = datetime(2026, 8, 20, 14, 0, tzinfo=TIMEZONE)
FIXED_NOW_UTC = FIXED_NOW.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)


class ProactiveCheckInContractTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self._tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self._tmp.close()
        self._db_path_patch = patch.object(db, "DB_PATH", self._tmp.name)
        self._db_path_patch.start()
        self.addCleanup(self._db_path_patch.stop)
        self.addCleanup(lambda: os.path.exists(self._tmp.name) and os.remove(self._tmp.name))
        db.init_db()
        self._chat_patch = patch("scheduler.MY_CHAT_ID", "12345")
        self._chat_patch.start()
        self.addCleanup(self._chat_patch.stop)

    # --- helpers ---

    @staticmethod
    def _utc_str(when: datetime) -> str:
        return when.strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def _local_str(when: datetime) -> str:
        return when.replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S")

    def _hours_ago_utc(self, hours: float) -> str:
        return self._utc_str(FIXED_NOW_UTC - timedelta(hours=hours))

    def _days_ago_utc(self, days: float) -> str:
        return self._utc_str(FIXED_NOW_UTC - timedelta(days=days))

    def _hours_from_now_local(self, hours: float) -> str:
        return self._local_str(FIXED_NOW + timedelta(hours=hours))

    def _insert_goal(
        self,
        content: str,
        *,
        status: str = "active",
        target_date: str | None = None,
        last_checked_in: str | None = None,
        created_at: str | None = None,
    ) -> int:
        conn = db.get_connection()
        try:
            cursor = conn.execute(
                """
                INSERT INTO goals (content, type, status, target_date, last_checked_in, created_at)
                VALUES (?, 'mid-term', ?, ?, ?, ?)
                """,
                (
                    content,
                    status,
                    target_date,
                    last_checked_in,
                    created_at or self._utc_str(FIXED_NOW_UTC),
                ),
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def _insert_check_in(self, triggered_by: str, *, timestamp: str | None = None) -> int:
        conn = db.get_connection()
        try:
            cursor = conn.execute(
                "INSERT INTO check_ins (topic, triggered_by, timestamp) VALUES (?, ?, ?)",
                (CHECK_IN_TOPIC, triggered_by, timestamp or self._utc_str(FIXED_NOW_UTC)),
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def _insert_message(self, role: str, content: str, *, timestamp: str | None = None) -> None:
        conn = db.get_connection()
        try:
            conn.execute(
                "INSERT INTO messages (role, content, timestamp) VALUES (?, ?, ?)",
                (role, content, timestamp or self._utc_str(FIXED_NOW_UTC)),
            )
            conn.commit()
        finally:
            conn.close()

    def _count_check_ins(self) -> int:
        conn = db.get_connection()
        try:
            return conn.execute("SELECT COUNT(*) FROM check_ins").fetchone()[0]
        finally:
            conn.close()

    def _latest_check_in(self) -> dict | None:
        conn = db.get_connection()
        try:
            row = conn.execute(
                "SELECT topic, triggered_by, timestamp FROM check_ins ORDER BY id DESC LIMIT 1"
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def _goal_last_checked_in(self, goal_id: int) -> str | None:
        conn = db.get_connection()
        try:
            row = conn.execute(
                "SELECT last_checked_in FROM goals WHERE id = ?",
                (goal_id,),
            ).fetchone()
            return row["last_checked_in"] if row else None
        finally:
            conn.close()

    def _make_context(self) -> AsyncMock:
        context = AsyncMock()
        context.bot.send_message = AsyncMock()
        return context

    async def _run(self, *, now: datetime = FIXED_NOW, context: AsyncMock | None = None):
        context = context or self._make_context()
        with patch("scheduler.datetime") as mock_datetime:
            mock_datetime.now.return_value = now
            mock_datetime.strptime = datetime.strptime
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
            await check_proactive_triggers(context)
        return context

    def _seed_eligible_deadline_goal(self, content: str = "Finish DBMS revision") -> int:
        return self._insert_goal(
            content,
            target_date=self._hours_from_now_local(12),
            last_checked_in=self._hours_ago_utc(DEADLINE_COOLDOWN_HOURS + 1),
        )

    def _seed_eligible_stale_goal(self, content: str = "Practice DSA daily") -> int:
        return self._insert_goal(
            content,
            target_date=None,
            created_at=self._days_ago_utc(STALE_THRESHOLD_DAYS + 1),
            last_checked_in=None,
        )

    # --- guard rails ---

    async def test_quiet_hours_suppress_check_in(self):
        original_last_checked_in = self._hours_ago_utc(DEADLINE_COOLDOWN_HOURS + 1)
        goal_id = self._insert_goal(
            "Finish DBMS revision",
            target_date=self._hours_from_now_local(12),
            last_checked_in=original_last_checked_in,
        )
        for quiet_time in (
            datetime(2026, 8, 20, 23, 30, tzinfo=TIMEZONE),
            datetime(2026, 8, 21, 7, 45, tzinfo=TIMEZONE),
        ):
            with self.subTest(quiet_time=quiet_time.isoformat()):
                context = await self._run(now=quiet_time)
                context.bot.send_message.assert_not_called()
                self.assertEqual(self._goal_last_checked_in(goal_id), original_last_checked_in)

    async def test_active_hours_allow_check_in(self):
        run_at = datetime(2026, 8, 20, 8, 0, tzinfo=TIMEZONE)
        run_at_utc = run_at.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)
        self._insert_goal(
            "Finish DBMS revision",
            target_date=self._local_str(run_at + timedelta(hours=12)),
            last_checked_in=self._utc_str(run_at_utc - timedelta(hours=DEADLINE_COOLDOWN_HOURS + 2)),
        )
        context = await self._run(now=run_at)
        context.bot.send_message.assert_called_once()

    async def test_daily_budget_reached_suppresses_check_in(self):
        self._seed_eligible_deadline_goal()
        self._insert_check_in(TRIGGER_STALE_GOAL, timestamp=self._hours_ago_utc(20))
        self._insert_check_in(TRIGGER_GOAL_DEADLINE, timestamp=self._hours_ago_utc(10))
        context = await self._run()
        context.bot.send_message.assert_not_called()
        self.assertEqual(self._count_check_ins(), 2)

    async def test_global_cooldown_suppresses_check_in(self):
        self._seed_eligible_deadline_goal()
        self._insert_check_in(TRIGGER_GOAL_DEADLINE, timestamp=self._hours_ago_utc(2))
        context = await self._run()
        context.bot.send_message.assert_not_called()

    async def test_global_cooldown_expired_allows_check_in(self):
        self._seed_eligible_deadline_goal()
        self._insert_check_in(TRIGGER_GOAL_DEADLINE, timestamp=self._hours_ago_utc(4))
        context = await self._run()
        context.bot.send_message.assert_called_once()

    # --- triggers ---

    async def test_deadline_trigger_fires_within_24_hours(self):
        goal_id = self._insert_goal(
            "Submit internship application",
            target_date=self._hours_from_now_local(18),
            last_checked_in=self._hours_ago_utc(DEADLINE_COOLDOWN_HOURS + 1),
        )
        context = await self._run()
        context.bot.send_message.assert_called_once()
        recorded = self._latest_check_in()
        self.assertEqual(recorded["triggered_by"], TRIGGER_GOAL_DEADLINE)
        self.assertEqual(recorded["topic"], CHECK_IN_TOPIC)
        self.assertIsNotNone(self._goal_last_checked_in(goal_id))
        sent_text = context.bot.send_message.call_args.kwargs["text"]
        self.assertIn("Submit internship application", sent_text)

    async def test_deadline_trigger_does_not_fire_beyond_24_hours(self):
        self._insert_goal(
            "Build portfolio site",
            target_date=self._hours_from_now_local(30),
            last_checked_in=self._days_ago_utc(STALE_THRESHOLD_DAYS + 1),
        )
        context = await self._run()
        context.bot.send_message.assert_not_called()

    async def test_deadline_trigger_respects_48h_per_goal_cooldown(self):
        self._insert_goal(
            "Revise OS notes",
            target_date=self._hours_from_now_local(6),
            last_checked_in=self._hours_ago_utc(24),
        )
        context = await self._run()
        context.bot.send_message.assert_not_called()

    async def test_stale_goal_trigger_fires_after_5_days(self):
        goal_id = self._seed_eligible_stale_goal()
        context = await self._run()
        context.bot.send_message.assert_called_once()
        recorded = self._latest_check_in()
        self.assertEqual(recorded["triggered_by"], TRIGGER_STALE_GOAL)
        self.assertIsNotNone(self._goal_last_checked_in(goal_id))

    async def test_stale_goal_respects_5d_per_goal_cooldown(self):
        self._insert_goal(
            "Read one systems paper",
            target_date=None,
            created_at=self._days_ago_utc(STALE_THRESHOLD_DAYS + 2),
            last_checked_in=self._days_ago_utc(3),
        )
        context = await self._run()
        context.bot.send_message.assert_not_called()

    async def test_goal_without_target_date_uses_stale_logic(self):
        goal_id = self._insert_goal(
            "Maintain workout habit",
            target_date=None,
            created_at=self._days_ago_utc(STALE_THRESHOLD_DAYS + 1),
            last_checked_in=None,
        )
        context = await self._run()
        context.bot.send_message.assert_called_once()
        self.assertEqual(self._latest_check_in()["triggered_by"], TRIGGER_STALE_GOAL)
        self.assertIsNotNone(self._goal_last_checked_in(goal_id))

    async def test_far_off_target_date_uses_stale_logic(self):
        goal_id = self._insert_goal(
            "Prepare for placements",
            target_date=self._hours_from_now_local(24 * 14),
            created_at=self._days_ago_utc(STALE_THRESHOLD_DAYS + 2),
            last_checked_in=self._days_ago_utc(STALE_THRESHOLD_DAYS + 1),
        )
        context = await self._run()
        context.bot.send_message.assert_called_once()
        self.assertEqual(self._latest_check_in()["triggered_by"], TRIGGER_STALE_GOAL)
        self.assertIsNotNone(self._goal_last_checked_in(goal_id))

    async def test_deadline_trigger_has_priority_over_stale(self):
        deadline_goal_id = self._insert_goal(
            "Due soon goal",
            target_date=self._hours_from_now_local(8),
            last_checked_in=self._hours_ago_utc(DEADLINE_COOLDOWN_HOURS + 1),
        )
        self._insert_goal(
            "Stale goal",
            target_date=None,
            created_at=self._days_ago_utc(STALE_THRESHOLD_DAYS + 3),
            last_checked_in=None,
        )
        context = await self._run()
        context.bot.send_message.assert_called_once()
        self.assertEqual(self._latest_check_in()["triggered_by"], TRIGGER_GOAL_DEADLINE)
        sent_text = context.bot.send_message.call_args.kwargs["text"]
        self.assertIn("Due soon goal", sent_text)
        self.assertIsNotNone(self._goal_last_checked_in(deadline_goal_id))

    async def test_only_one_check_in_per_scheduler_run(self):
        self._insert_goal(
            "First deadline goal",
            target_date=self._hours_from_now_local(4),
            last_checked_in=self._hours_ago_utc(DEADLINE_COOLDOWN_HOURS + 2),
        )
        self._insert_goal(
            "Second deadline goal",
            target_date=self._hours_from_now_local(6),
            last_checked_in=self._hours_ago_utc(DEADLINE_COOLDOWN_HOURS + 3),
        )
        context = await self._run()
        context.bot.send_message.assert_called_once()
        self.assertEqual(self._count_check_ins(), 1)

    async def test_completed_and_dropped_goals_are_ignored(self):
        self._insert_goal(
            "Done goal",
            status="done",
            target_date=self._hours_from_now_local(4),
            last_checked_in=self._hours_ago_utc(DEADLINE_COOLDOWN_HOURS + 1),
        )
        self._insert_goal(
            "Dropped goal",
            status="dropped",
            target_date=None,
            created_at=self._days_ago_utc(STALE_THRESHOLD_DAYS + 2),
            last_checked_in=None,
        )
        context = await self._run()
        context.bot.send_message.assert_not_called()

    # --- delivery / bookkeeping ---

    async def test_successful_delivery_creates_check_in_and_updates_last_checked_in(self):
        goal_id = self._seed_eligible_deadline_goal()
        before = self._count_check_ins()
        context = await self._run()
        context.bot.send_message.assert_called_once()
        self.assertEqual(self._count_check_ins(), before + 1)
        self.assertIsNotNone(self._goal_last_checked_in(goal_id))

    async def test_delivery_failure_performs_no_database_mutations(self):
        original_last_checked_in = self._hours_ago_utc(DEADLINE_COOLDOWN_HOURS + 1)
        goal_id = self._insert_goal(
            "Finish DBMS revision",
            target_date=self._hours_from_now_local(12),
            last_checked_in=original_last_checked_in,
        )
        context = self._make_context()
        context.bot.send_message.side_effect = RuntimeError("telegram unavailable")
        before = self._count_check_ins()
        await self._run(context=context)
        self.assertEqual(self._count_check_ins(), before)
        self.assertEqual(self._goal_last_checked_in(goal_id), original_last_checked_in)

    async def test_bookkeeping_failure_prevents_telegram_delivery(self):
        """Book-then-send contract: failed pre-send DB work must not deliver."""
        self._seed_eligible_deadline_goal()
        context = self._make_context()
        with patch("db.create_check_in", side_effect=RuntimeError("database unavailable")):
            await self._run(context=context)
        context.bot.send_message.assert_not_called()

    async def test_delivery_failure_rolls_back_precheck_bookkeeping(self):
        original_last_checked_in = self._hours_ago_utc(DEADLINE_COOLDOWN_HOURS + 1)
        goal_id = self._insert_goal(
            "Finish DBMS revision",
            target_date=self._hours_from_now_local(12),
            last_checked_in=original_last_checked_in,
        )
        context = self._make_context()
        context.bot.send_message.side_effect = RuntimeError("telegram unavailable")
        await self._run(context=context)
        self.assertEqual(self._count_check_ins(), 0)
        self.assertEqual(self._goal_last_checked_in(goal_id), original_last_checked_in)

    async def test_successful_delivery_never_leaves_unrecorded_check_in(self):
        """Guards against send-then-book duplicates: bookkeeping precedes delivery."""
        self._seed_eligible_deadline_goal()
        call_order: list[str] = []

        original_create = db.create_check_in
        original_update = db.update_goal_last_checked_in

        def tracking_create(*args, **kwargs):
            call_order.append("create_check_in")
            return original_create(*args, **kwargs)

        def tracking_update(*args, **kwargs):
            call_order.append("update_goal_last_checked_in")
            return original_update(*args, **kwargs)

        context = self._make_context()

        async def tracking_send(**kwargs):
            call_order.append("send_message")
            return None

        context.bot.send_message.side_effect = tracking_send

        with patch("db.create_check_in", side_effect=tracking_create), patch(
            "db.update_goal_last_checked_in", side_effect=tracking_update
        ):
            await self._run(context=context)

        self.assertIn("create_check_in", call_order)
        self.assertIn("update_goal_last_checked_in", call_order)
        self.assertIn("send_message", call_order)
        self.assertLess(
            call_order.index("send_message"),
            len(call_order),
            "send_message should happen after bookkeeping starts",
        )
        self.assertLess(
            call_order.index("create_check_in"),
            call_order.index("send_message"),
        )
        self.assertLess(
            call_order.index("update_goal_last_checked_in"),
            call_order.index("send_message"),
        )

    # --- budget source ---

    async def test_rolling_budget_uses_check_ins_not_messages(self):
        self._seed_eligible_deadline_goal()
        for index in range(DAILY_BUDGET + 3):
            self._insert_message(
                "luna",
                f"Proactive-style message {index}",
                timestamp=self._hours_ago_utc(1 + index),
            )
        context = await self._run()
        context.bot.send_message.assert_called_once()
        self.assertEqual(self._count_check_ins(), 1)


if __name__ == "__main__":
    unittest.main()

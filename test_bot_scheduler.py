import unittest

from bot import register_job_queue_jobs
from scheduler import check_due_reminders, check_proactive_triggers


class SlotsJobQueue:
    def __init__(self):
        self.calls = []

    def run_repeating(self, callback, *, interval, first):
        self.calls.append((callback, interval, first))


class SlotsApplication:
    __slots__ = ("job_queue",)

    def __init__(self, job_queue):
        self.job_queue = job_queue


class BotSchedulerIntegrationTests(unittest.TestCase):
    def test_register_job_queue_jobs_handles_slots_application_and_is_per_instance(self):
        first_app = SlotsApplication(SlotsJobQueue())
        second_app = SlotsApplication(SlotsJobQueue())

        self.assertFalse(hasattr(first_app, "__dict__"))

        register_job_queue_jobs(first_app)
        register_job_queue_jobs(first_app)
        register_job_queue_jobs(second_app)

        self.assertEqual(len(first_app.job_queue.calls), 2)
        self.assertEqual(len(second_app.job_queue.calls), 2)
        reminder_call, proactive_call = first_app.job_queue.calls

        self.assertIs(reminder_call[0], check_due_reminders)
        self.assertEqual(reminder_call[1:], (60, 10))

        self.assertIs(proactive_call[0], check_proactive_triggers)
        self.assertEqual(proactive_call[1:], (900, 60))

    def test_register_job_queue_jobs_skips_registration_when_job_queue_missing(self):
        app = SlotsApplication(None)

        register_job_queue_jobs(app)

        self.assertIsNone(app.job_queue)


if __name__ == "__main__":
    unittest.main()

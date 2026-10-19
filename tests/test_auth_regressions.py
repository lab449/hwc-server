import concurrent.futures
from datetime import datetime, timezone
import os
import unittest
import uuid
from pymongo import MongoClient
from auth import AuthHandler


class AttemptQuotaRegressions(unittest.TestCase):
    def setUp(self):
        self.name = 'hwc_e2e_quota_' + uuid.uuid4().hex
        self.client = MongoClient(os.environ['MONGODB_HOSTNAME'], int(os.environ['MONGODB_PORT']))
        self.db = self.client[self.name]
        self.auth = AuthHandler({'host': os.environ['MONGODB_HOSTNAME'],
                                 'port': os.environ['MONGODB_PORT'], 'db': self.name})

    def tearDown(self):
        self.auth.db_client.close()
        assert self.name.startswith('hwc_e2e_')
        self.client.drop_database(self.name)
        self.client.close()

    def submit(self, number=4, answers=None):
        return self.auth.set_task(1, {}, {'number': number, 'answers': answers or {}},
                                  {'total_score': 0}, datetime.now(timezone.utc), 40)

    def seed_legacy(self, count):
        values = [4, '4', '04', '+4', ' 4 ']
        self.db.StudentsAttempts.insert_many([
            {'id_student': 1, 'task_out': {'number': values[i % len(values)]},
             'score': {'total_score': 0}} for i in range(count)])

    def test_parallel_last_slot_preserves_legacy_rows(self):
        self.seed_legacy(39)
        before = list(self.db.StudentsAttempts.find())
        with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
            result = list(pool.map(lambda _: self.submit(), range(24)))
        self.assertEqual(sum(x is not None for x in result), 1)
        self.assertEqual(self.auth.get_count_attemps(1, 4), 40)
        for row in before:
            self.assertEqual(self.db.StudentsAttempts.find_one({'_id': row['_id']}), row)

    def test_parallel_empty_history_admits_exactly_40(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
            result = list(pool.map(lambda _: self.submit(), range(60)))
        self.assertEqual(sum(x is not None for x in result), 40)
        slots = [r['attempt_slot'] for r in self.db.StudentsAttempts.find()]
        self.assertEqual(sorted(slots), list(range(40)))

    def test_failed_insert_leaves_capacity_available(self):
        with self.assertRaises(OverflowError):
            self.submit(answers={'invalid': 10**100})
        self.assertEqual(self.db.StudentsAttempts.count_documents({}), 0)
        self.assertEqual(self.submit(), 39)

    def test_deleted_slot_can_be_reused(self):
        self.submit(); self.submit()
        self.db.StudentsAttempts.delete_one({'attempt_slot': 0})
        self.assertEqual(self.submit(), 38)
        self.assertEqual(sorted(r['attempt_slot'] for r in self.db.StudentsAttempts.find()), [0, 1])

    def test_full_legacy_history_is_unchanged(self):
        self.seed_legacy(40)
        self.assertIsNone(self.submit())
        self.assertEqual(self.db.StudentsAttempts.count_documents({}), 40)
        self.assertEqual(self.db.StudentsAttempts.count_documents({'attempt_slot': {'$exists': True}}), 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)

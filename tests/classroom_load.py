"""Bounded 30-student benchmark against production uWSGI in a disposable DB."""
import concurrent.futures
import json
import os
import threading
import time
from api_e2e import ApiE2E


def main():
    os.environ['HWC_E2E_SERVER'] = 'uwsgi'
    ApiE2E.setUpClass()
    report = {'students': 30, 'source_ip': '127.0.0.1', 'server': 'uwsgi',
              'client_timeout_seconds': 30, 'stages': {}}
    users = [{'id': 26322001 + i, 'name': 'Classroom test',
              'email': 'classroom@example.invalid', 'password': 'test-classroom-only'} for i in range(30)]
    try:
        for stage, endpoint in [('register', '/api/register'), ('login', '/api/login'),
                                ('gettask', '/api/gettask'), ('send_task', '/api/send_task')]:
            barrier = threading.Barrier(30)
            def one(user):
                body = {'auth': user, 'number': 1, 'task': {'number': 1, 'answers': {}}}
                barrier.wait(timeout=10)
                started = time.monotonic()
                status, obj, _ = ApiE2E.request('POST', endpoint, body)
                elapsed = time.monotonic() - started
                assert status == 200 and isinstance(obj, dict), (stage, status)
                assert (obj.get('statusCode'), obj.get('isError')) == (200, False), (stage, obj)
                assert elapsed < 30, (stage, elapsed)
                return elapsed
            with concurrent.futures.ThreadPoolExecutor(max_workers=30) as pool:
                timings = list(pool.map(one, users))
            ordered = sorted(timings)
            report['stages'][stage] = {'requests': len(timings), 'http_200': len(timings),
                'max_seconds': round(max(timings), 3), 'p95_seconds': round(ordered[28], 3),
                'over_legacy_5s': sum(t > 5 for t in timings)}
        assert ApiE2E.db.StudentsAttempts.count_documents({}) == 30
        assert ApiE2E.db.StudentsAttempts.count_documents({'submitted_at': {'$exists': True}}) == 30
        report['success'] = True
        print(json.dumps(report, indent=2))
    finally:
        ApiE2E.tearDownClass()


if __name__ == '__main__':
    main()

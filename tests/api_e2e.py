"""Real HTTP + MongoDB checks; only a disposable hwc_e2e_* database is written."""
import concurrent.futures
from datetime import datetime, timedelta, timezone
import http.client
import json
import os
from pathlib import Path
import socket
import signal
import subprocess
import sys
import tempfile
import time
import unittest
import uuid
from pymongo import MongoClient


class ApiE2E(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db_name = 'hwc_e2e_' + uuid.uuid4().hex
        cls.mongo = MongoClient(os.environ['MONGODB_HOSTNAME'], int(os.environ['MONGODB_PORT']), tz_aware=True)
        cls.db = cls.mongo[cls.db_name]
        cls.config = json.loads(Path('server_task_data/tasks_info.json').read_text())
        cls.tasks = [json.loads(Path(t['filepath']).read_text()) for t in cls.config['course_tasks']]
        cls.serial = 20000000
        cls.log = tempfile.TemporaryFile(mode='w+b')
        with socket.socket() as s:
            s.bind(('127.0.0.1', 0))
            cls.port = s.getsockname()[1]
        env = dict(os.environ, MONGODB_DATABASE=cls.db_name, FLASK_DEBUG='0')
        cls.ini = None
        if os.environ.get('HWC_E2E_SERVER') == 'uwsgi':
            cls.ini = tempfile.NamedTemporaryFile(mode='w', suffix='.ini')
            cls.ini.write(Path('hwc_server.ini').read_text().replace(
                'http-socket = 0.0.0.0:5050', 'http-socket = 127.0.0.1:' + str(cls.port)))
            cls.ini.flush()
            command = ['uwsgi', '--ini', cls.ini.name]
        else:
            command = [sys.executable, '-m', 'flask', '--app', 'hwc_server', 'run', '--host',
                       '127.0.0.1', '--port', str(cls.port), '--no-debugger']
        cls.server = None
        try:
            cls.server = subprocess.Popen(command, env=env, stdout=cls.log, stderr=cls.log, start_new_session=True)
            for _ in range(100):
                try:
                    if cls.request('GET', '/api/ok')[1]['statusCode'] == 200:
                        return
                except (OSError, ValueError, KeyError):
                    pass
                if cls.server.poll() is not None:
                    raise RuntimeError('Disposable API process exited')
                time.sleep(.1)
            raise RuntimeError('Disposable API did not become ready')
        except Exception:
            cls.tearDownClass()
            raise

    @classmethod
    def tearDownClass(cls):
        try:
            if cls.server is not None:
                try:
                    os.killpg(cls.server.pid, signal.SIGINT)
                except ProcessLookupError:
                    pass
                try:
                    cls.server.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    try:
                        os.killpg(cls.server.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    cls.server.wait()
        finally:
            try:
                assert cls.db_name.startswith('hwc_e2e_')
                cls.mongo.drop_database(cls.db_name)
            finally:
                cls.mongo.close()
                cls.log.close()
                if cls.ini is not None:
                    cls.ini.close()

    @classmethod
    def request(cls, method, path, data=None, raw=None, content_type='application/json'):
        body = json.dumps(data).encode() if raw is None and data is not None else raw
        headers = {'Content-Type': content_type} if content_type else {}
        conn = http.client.HTTPConnection('127.0.0.1', cls.port, timeout=30)
        try:
            conn.request(method, path, body=body, headers=headers)
            r = conn.getresponse()
            body = r.read()
            try:
                parsed = json.loads(body)
            except (ValueError, UnicodeDecodeError):
                parsed = None
            return r.status, parsed, body
        finally:
            conn.close()

    def setUp(self):
        type(self).serial += 1
        self.user = {'id': self.serial, 'name': 'API test', 'email': 'api-test@example.invalid', 'password': 'test-only-password'}
        status, obj, _ = self.request('POST', '/api/register', {'auth': self.user})
        self.assertEqual((status, obj.get('statusCode'), obj.get('isError')), (200, 200, False))

    def good(self, endpoint, body):
        status, obj, _ = self.request('POST', endpoint, body)
        self.assertEqual(status, 200)
        self.assertIsInstance(obj, dict)
        self.assertEqual((obj.get('statusCode'), obj.get('isError')), (200, False))
        return obj

    def assign(self, number, case=0):
        self.db.StudentsCases.update_one({'_id': self.user['id']}, {'$set': {'task'+str(number): case}}, upsert=True)

    def test_login_and_repeated_registration(self):
        self.good('/api/login', {'auth': self.user})
        self.good('/api/register', {'auth': self.user})
        wrong = dict(self.user, password='wrong-password')
        _, obj, _ = self.request('POST', '/api/login', {'auth': wrong})
        self.assertTrue(obj['isError'])
        self.assertEqual(obj['statusCode'], 403)

    def test_positive_student_ids_and_invalid_ids(self):
        for student_id in [1, 202622001, 9223372036854775807]:
            user = dict(self.user, id=student_id)
            self.good('/api/register', {'auth': user})
            self.good('/api/login', {'auth': user})
        for student_id in [0, -1, True, 1.5, '202622001', None, 9223372036854775808]:
            for endpoint in ['/api/register', '/api/login']:
                _, obj, _ = self.request('POST', endpoint, {'auth': dict(self.user, id=student_id)})
                self.assertEqual((obj['isError'], obj['statusCode']), (True, 400))

    def test_password_hashes_and_legacy_account_compatibility(self):
        row = self.db.InfoStudent.find_one({'_id': self.user['id']})
        self.assertNotIn('password', row)
        self.assertNotEqual(row['password_hash'], self.user['password'])
        self.good('/api/login', {'auth': self.user})
        legacy = dict(self.user, id=self.user['id'] + 100000)
        stored = dict(legacy)
        stored['_id'] = stored.pop('id')
        self.db.InfoStudent.insert_one(stored)
        self.good('/api/login', {'auth': legacy})
        self.good('/api/register', {'auth': legacy})
        self.assertEqual(self.db.InfoStudent.find_one({'_id': legacy['id']}), stored)

    def test_historic_string_attempts_count_towards_limit(self):
        self.assign(4, 0)
        self.db.StudentsAttempts.insert_many([
            {'id_student': self.user['id'], 'task_out': {'number': '4'}, 'score': {'total_score': 3}}
            for _ in range(40)])
        obj = self.good('/api/send_task', {'auth': self.user, 'task': {'number': 4, 'answers': {}}})
        self.assertEqual(obj['data']['total_score'], 3)
        self.assertEqual(self.db.StudentsAttempts.count_documents({'id_student': self.user['id']}), 40)

    def test_invalid_saved_variant_is_not_reassigned(self):
        self.assign(1, -1)
        for endpoint, body in [('/api/gettask', {'auth': self.user, 'number': 1}),
                               ('/api/send_task', {'auth': self.user, 'task': {'number': 1, 'answers': {}}})]:
            _, obj, _ = self.request('POST', endpoint, body)
            self.assertEqual((obj['isError'], obj['statusCode']), (True, 409))
        self.assertEqual(self.db.StudentsCases.find_one({'_id': self.user['id']})['task1'], -1)

    def test_invalid_unicode_credentials_are_json_errors(self):
        legacy = dict(self.user, id=self.user['id'] + 500000)
        stored = dict(legacy)
        stored['_id'] = stored.pop('id')
        self.db.InfoStudent.insert_one(stored)
        for user in [self.user, legacy]:
            for field in ['password', 'name', 'email']:
                for endpoint in ['/api/register', '/api/login', '/api/gettask', '/api/send_task']:
                    status, obj, _ = self.request('POST', endpoint, {
                        'auth': dict(user, **{field: '\ud800'}), 'number': 1,
                        'task': {'number': 1, 'answers': {}}})
                    self.assertEqual(status, 200)
                    self.assertIsInstance(obj, dict)
                    self.assertEqual((obj['statusCode'], obj['isError']), (400, True))
        unicode_user = dict(self.user, id=self.user['id'] + 600000,
                            name='学生测试', password='пароль-密码-100%')
        self.good('/api/register', {'auth': unicode_user})
        self.good('/api/login', {'auth': unicode_user})

    def test_concurrent_last_attempt_and_legacy_numbers(self):
        self.assign(4, 0)
        numbers = [4, '4', '04', '+4', ' 4 ']
        self.db.StudentsAttempts.insert_many([
            {'id_student': self.user['id'], 'task_out': {'number': numbers[i % len(numbers)]},
             'score': {'total_score': 0}} for i in range(39)])
        case = self.tasks[3]['cases'][0]
        answers = {k: v['true_value'] for k, v in case['answers'].items()}
        def submit(_):
            return self.good('/api/send_task', {'auth': self.user, 'task': {'number': 4, 'answers': answers}})
        with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
            results = list(pool.map(submit, range(24)))
        self.assertEqual(self.db.StudentsAttempts.count_documents({'id_student': self.user['id']}), 40)
        self.assertEqual(self.db.StudentsAttempts.count_documents(
            {'id_student': self.user['id'], 'attempt_slot': {'$exists': True}}), 1)
        self.assertTrue(all(x['data']['total_score'] == sum(v['score'] for v in case['answers'].values())
                            for x in results))

    def test_client_archive_matches_published_versions(self):
        from io import BytesIO
        from zipfile import ZipFile
        import hashlib
        status, _, body = self.request('GET', '/clients/hwc-matlab-client.zip')
        self.assertEqual(status, 200)
        with ZipFile(BytesIO(body)) as archive:
            self.assertEqual(set(archive.namelist()), {'HWC.m', 'hwc_connect.m', 'hwc_reset.m', 'README.md'})
            for name, endpoint in [('HWC.m', 'client_version'), ('hwc_connect.m', 'launcher_version')]:
                _, version, _ = self.request('GET', '/api/matlab/' + endpoint)
                self.assertEqual(hashlib.md5(archive.read(name)).hexdigest(), version['data']['md5'])
                status, _, downloaded = self.request('GET', '/clients/hwc-matlab-client/' + name)
                self.assertEqual(status, 200)
                self.assertEqual(downloaded, archive.read(name))
        _, _, page = self.request('GET', '/')
        self.assertIn(b'/clients/hwc-matlab-client.zip', page)
        self.assertNotIn(b"chdu_connect('http')", page)

    def test_bad_payloads_are_json_errors(self):
        failures = []
        samples = [('no-content-type', b'', None), ('broken-json', b'{', 'application/json'), ('missing-auth', b'{}', 'application/json'), ('null', b'null', 'application/json'), ('array', b'[]', 'application/json'), ('null-auth', b'{"auth":null}', 'application/json'), ('missing-password', json.dumps({'auth': {k:v for k,v in self.user.items() if k!='password'}}).encode(), 'application/json'), ('fractional-id', json.dumps({'auth': dict(self.user, id=20000000.5)}).encode(), 'application/json')]
        for endpoint in ['/api/register', '/api/login', '/api/gettask', '/api/send_task']:
            for label, raw, ct in samples:
                status, obj, _ = self.request('POST', endpoint, raw=raw, content_type=ct)
                if status >= 500 or not isinstance(obj, dict) or obj.get('isError') is not True or obj.get('statusCode') != 400:
                    failures.append((endpoint, label, status, obj.get('statusCode') if isinstance(obj, dict) else 'non-json'))
        self.assertEqual(failures, [])

    def test_invalid_task_numbers(self):
        failures=[]
        for n in [0, -1, 7, 1.5, True, 'invalid', None]:
            for endpoint, body in [('/api/gettask', {'auth': self.user, 'number': n}), ('/api/send_task', {'auth': self.user, 'task': {'number': n, 'answers': {}}})]:
                status, obj, _ = self.request('POST', endpoint, body)
                if status >= 500 or not isinstance(obj, dict) or obj.get('statusCode')!=400 or obj.get('isError') is not True:
                    failures.append((endpoint, repr(n), status, obj.get('statusCode') if isinstance(obj,dict) else 'non-json'))
        self.assertEqual(failures, [])

    def test_all_six_labs_and_case_zero(self):
        for n in range(1,7):
            self.assign(n,0)
            obj=self.good('/api/gettask', {'auth':self.user,'number':n})
            self.assertTrue(all(v=='?' for v in obj['data']['answers'].values()))
            self.assertEqual(obj['data']['parameters'],self.tasks[n-1]['cases'][0]['parameters'])
            self.assertEqual(self.good('/api/gettask',{'auth':self.user,'number':n})['data'],obj['data'])
            case = self.tasks[n-1]['cases'][0]
            answers = {k: v['true_value'] for k, v in case['answers'].items()}
            graded = self.good('/api/send_task', {'auth': self.user, 'task': {'number': n, 'answers': answers}})
            self.assertEqual(graded['data']['total_score'], sum(v['score'] for v in case['answers'].values()))

    def test_lab4_grading_and_attempt_limit_with_numeric_strings(self):
        self.assign(4,0)
        case=self.tasks[3]['cases'][0]
        answers={k:v['true_value'] for k,v in case['answers'].items()}
        score=sum(v['score'] for v in case['answers'].values())
        for i in range(40):
            number='4' if i%2 else 4.0
            obj=self.good('/api/send_task',{'auth':self.user,'task':{'number':number,'answers':answers if i==0 else {}}})
            self.assertEqual(obj['data']['total_score'],score if i==0 else 0)
        last=self.good('/api/send_task',{'auth':self.user,'task':{'number':4,'answers':{}}})
        self.assertEqual(last['data']['total_score'],score)
        self.assertEqual(self.db.StudentsAttempts.count_documents({'id_student':self.user['id']}),40)
        self.assertTrue(all(type(x['task_out']['number']) is int for x in self.db.StudentsAttempts.find({'id_student':self.user['id']})))

    def test_submission_timestamp_is_server_utc(self):
        self.assign(1, 0)
        before = datetime.now(timezone.utc) - timedelta(milliseconds=1)
        self.good('/api/send_task', {
            'auth': self.user,
            'submitted_at': '1900-01-01T00:00:00Z',
            'task': {'number': 1, 'answers': {}, 'submitted_at': '1900-01-01T00:00:00Z'},
        })
        after = datetime.now(timezone.utc)
        row = self.db.StudentsAttempts.find_one({'id_student': self.user['id']})
        submitted_at = row['submitted_at']
        self.assertIsInstance(submitted_at, datetime)
        self.assertEqual(submitted_at.utcoffset(), timedelta(0))
        self.assertGreaterEqual(submitted_at, before)
        self.assertLessEqual(submitted_at, after)

    def test_classroom_students_share_one_ip(self):
        def submit(student_number):
            user = dict(self.user, id=202600000 + student_number)
            self.good('/api/register', {'auth': user})
            # Every connection uses the same 127.0.0.1 source IP, without X-Forwarded-For.
            self.good('/api/gettask', {'auth': user, 'number': 1})
            # Grade that student's actual assigned variant.
            assignment = self.db.StudentsCases.find_one({'_id': user['id']})['task1']
            assigned = self.tasks[0]['cases'][assignment]
            student_answers = {k: v['true_value'] for k, v in assigned['answers'].items()}
            result = self.good('/api/send_task', {
                'auth': user, 'task': {'number': 1, 'answers': student_answers}})
            self.assertEqual(result['data']['total_score'],
                             sum(v['score'] for v in assigned['answers'].values()))
            self.assertEqual(self.db.StudentsAttempts.count_documents({'id_student': user['id']}), 1)

        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
            list(pool.map(submit, range(30)))

    def test_submit_before_assignment(self):
        _,obj,_=self.request('POST','/api/send_task',{'auth':self.user,'task':{'number':1,'answers':{}}})
        self.assertEqual((obj['isError'],obj['statusCode']),(True,400))
        self.assertEqual(self.db.StudentsAttempts.count_documents({'id_student':self.user['id']}),0)

    def test_invalid_answer_shapes_and_types_do_not_crash(self):
        self.assign(1,1)
        failures=[]
        for a in [None,[], 'bad']:
            status,obj,_=self.request('POST','/api/send_task',{'auth':self.user,'task':{'number':1,'answers':a}})
            if status>=500 or not isinstance(obj,dict) or obj.get('statusCode')!=400:failures.append(('container',type(a).__name__,status))
        case=self.tasks[0]['cases'][1]
        for bad in [['bad'], {'bad':1}, [None], [[1],[2,3]], True, 10**100]:
            answers={k:bad for k in case['answers']}
            status,obj,_=self.request('POST','/api/send_task',{'auth':self.user,'task':{'number':1,'answers':answers}})
            if status>=500 or not isinstance(obj,dict) or obj.get('statusCode') not in (200, 400):failures.append(('value',repr(bad),status))
        self.assertEqual(failures,[])

    def test_parallel_gettask_keeps_one_assigned_variant(self):
        def get(_):return self.request('POST','/api/gettask',{'auth':self.user,'number':1})
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:out=list(pool.map(get,range(20)))
        for status,obj,_ in out:self.assertEqual((status,obj.get('statusCode')),(200,200))
        self.assertEqual(len({json.dumps(obj['data'],sort_keys=True) for _,obj,_ in out}),1)

    def test_auth_errors_do_not_log_passwords(self):
        marker='DO-NOT-LOG-'+uuid.uuid4().hex
        self.request('POST','/api/gettask',{'auth':dict(self.user,password=marker),'number':1})
        time.sleep(.05)
        self.log.flush();self.log.seek(0);logged=self.log.read().decode(errors='replace')
        self.assertFalse(marker in logged,'Authentication failure exposed password in server log')

    def test_files_and_main_page(self):
        status,_,body=self.request('GET','/')
        self.assertEqual(status,200)
        self.assertEqual(body.count(b'alt="available"'),6)
        status,_,body=self.request('GET','/files/l4.pdf')
        self.assertEqual(status,200);self.assertTrue(body.startswith(b'%PDF-'))
        status,_,_=self.request('GET','/files/../tasks_info.json')
        self.assertEqual(status,404)


if __name__=='__main__':
    unittest.main(verbosity=2)

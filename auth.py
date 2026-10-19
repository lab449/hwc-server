from typing import Optional, Tuple
import hmac
from datetime import datetime
from pymongo import MongoClient, ReturnDocument
from pymongo.errors import DuplicateKeyError
from jsonschema import validate, ValidationError
from werkzeug.security import generate_password_hash, check_password_hash

LOGIN_SCHEME = {
    '$schema': 'http://json-schema.org/draft-04/schema#',
    'type': 'object',
    'properties': {
        'id': {'type': 'integer', 'minimum': 1, 'maximum': 9223372036854775807},
        'name': {'type': 'string'},
        'email': {'type': 'string'},
        'password': {'type': 'string'},
    },
    'required': ['id', 'name', 'email', 'password'],
}
REGISTER_SCHEME = LOGIN_SCHEME


class AuthHandler:
    def __init__(self, db_config: dict):
        self.__host = db_config['host']
        self.__port = int(db_config['port'])
        self.db_client = MongoClient(self.__host, self.__port)
        db = self.db_client[db_config['db']]
        self.__user_db = db['InfoStudent']
        self.__user_case_assoc = db['StudentsCases']
        self.__task_db = db['StudentsAttempts']
        self.__slot_key = [('id_student', 1), ('task_out.number', 1), ('attempt_slot', 1)]
        self.__task_db.create_index(self.__slot_key, name='student_lab_attempt_slot', unique=True,
                                    partialFilterExpression={'attempt_slot': {'$exists': True}})

    @staticmethod
    def __valid_user_data(user_data) -> bool:
        try:
            validate(instance=user_data, schema=LOGIN_SCHEME)
            for field in ('name', 'email', 'password'):
                user_data[field].encode('utf-8')
        except (ValidationError, UnicodeError):
            return False
        return True

    @staticmethod
    def __password_matches(user: dict, password: str) -> bool:
        if 'password_hash' in user:
            try:
                return check_password_hash(user['password_hash'], password)
            except (ValueError, TypeError):
                return False
        # Keep existing accounts usable without rewriting production records.
        legacy = user.get('password')
        return isinstance(legacy, str) and hmac.compare_digest(legacy.encode(), password.encode())

    def register(self, user_data: dict) -> Tuple[int, str]:
        if not self.__valid_user_data(user_data):
            return 400, 'Invalid user data'
        user_id = user_data['id']
        user = self.__user_db.find_one({'_id': user_id})
        if user is not None:
            return self.__check_existing_registration(user, user_data)
        record = {'_id': user_id, 'name': user_data['name'], 'email': user_data['email'],
                  'password_hash': generate_password_hash(user_data['password'])}
        try:
            self.__user_db.insert_one(record)
        except DuplicateKeyError:
            user = self.__user_db.find_one({'_id': user_id})
            return self.__check_existing_registration(user, user_data)
        return 200, 'Registration complete'

    def __check_existing_registration(self, user, user_data):
        if user is None or user.get('email') != user_data['email']:
            return 401, 'Given wrong registration email'
        if not self.__password_matches(user, user_data['password']):
            return 403, 'Given wrong registration password'
        return 200, 'Authentification complete'

    def auth(self, user_data: dict) -> Tuple[int, str]:
        if not self.__valid_user_data(user_data):
            return 400, 'Invalid user data'
        user = self.__user_db.find_one({'_id': user_data['id']})
        if user is None:
            return 404, 'Unknown user. Please reset chdu connection and register'
        if not self.__password_matches(user, user_data['password']):
            return 403, 'Invalid password'
        return 200, 'Authentification complete'

    def set_case_number(self, user_id: int, task_number: int, case_number: int) -> int:
        field = 'task' + str(task_number)
        update = [{'$set': {field: {'$ifNull': ['$' + field, case_number]}}}]
        try:
            row = self.__user_case_assoc.find_one_and_update(
                {'_id': user_id}, update, upsert=True, return_document=ReturnDocument.AFTER)
        except DuplicateKeyError:
            row = self.__user_case_assoc.find_one_and_update(
                {'_id': user_id}, update, return_document=ReturnDocument.AFTER)
        return row[field]

    @staticmethod
    def __attempt_query(user_id: int, task_number: int):
        # Also count historic submissions that stored a JSON string as the number.
        return {'id_student': user_id, '$or': [
            {'task_out.number': task_number},
            {'task_out.number': {'$regex': r'^\s*\+?0*' + str(task_number) + r'\s*$'}}]}

    def get_best_score(self, user_id: int, task_number: int):
        row = self.__task_db.find_one(self.__attempt_query(user_id, task_number), sort=[('score.total_score', -1)])
        return row['score'] if row else {'total_score': 0}

    def get_count_attemps(self, user_id: int, task_number: int):
        return self.__task_db.count_documents(self.__attempt_query(user_id, task_number))

    def set_task(self, user_id: int, task_in: dict, task_out: dict, score: dict,
                 submitted_at: datetime, attempt_limit: int) -> Optional[int]:
        query = self.__attempt_query(user_id, task_out['number'])
        # Legacy rows are kept unchanged and reduce the number of available slots.
        legacy = self.__task_db.count_documents(dict(query, attempt_slot={'$exists': False}))
        capacity = max(0, attempt_limit - legacy)
        occupied = {row['attempt_slot'] for row in self.__task_db.find(
            dict(query, attempt_slot={'$exists': True}), {'attempt_slot': 1, '_id': 0})}
        for slot in range(capacity):
            if slot in occupied:
                continue
            record = {'id_student': user_id, 'task_in': task_in, 'task_out': task_out,
                      'score': score, 'submitted_at': submitted_at, 'attempt_slot': slot}
            try:
                # The unique index admits one request per slot; no separate counter
                # reservation can be stranded if encoding or insertion fails.
                self.__task_db.insert_one(record)
            except DuplicateKeyError as exc:
                if (exc.details or {}).get('keyPattern') != dict(self.__slot_key):
                    raise
                continue
            return max(0, attempt_limit - self.get_count_attemps(user_id, task_out['number']))
        return None

    def get_case_number(self, user_id: int, task_number: int):
        row = self.__user_case_assoc.find_one({'_id': user_id})
        return row.get('task' + str(task_number)) if row else None

    @property
    def host(self) -> str:
        return self.__host

    @property
    def port(self) -> int:
        return self.__port

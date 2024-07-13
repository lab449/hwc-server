from typing import Tuple
from pymongo import MongoClient
import json
import smtplib
import copy
import os
import logging
import secrets

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from jsonschema import validate, ValidationError

LOGIN_SCHEME = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "$id": "https://example.com/employee.schema.json",
    "description": "Scheme for verification auth_data message form",
    "type": "object",
    "properties": {
        "password": {
            "type": "string"
        },
        "id": {
            "type": "number",
            "minimum": 19322000,
            "maximum": 21322500
        },
        "name": {
            "type": "string"
        },
        "email": {
            "type": "string"
        }
    },
    "required": ["id", "name", "email", "password"]  
}

REGISTER_SCHEME = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "$id": "https://example.com/employee.schema.json",
    "description": "Scheme for verification auth_data message form",
    "type": "object",
    "properties": {
        "id": {
            "type": "number",
            "minimum": 19322000,
            "maximum": 21322500
        },
        "name": {
            "type": "string"
        },
        "email": {
            "type": "string"
        }
    },
    "required": ["id", "name", "email"]  
}

class AuthHandler:
    def __init__(self, db_config: str):
        self.db_client = MongoClient('mongodb://{:s}:{:s}'.format(
            db_config['host'],
            db_config['port']
        ))
        self.__user_db = self.db_client[db_config['db']]['InfoStudent']
        self.__user_case_assoc = self.db_client[db_config['db']]['StudentsCases']
        self.__task_db = self.db_client[db_config['db']]['StudentsAttempts']
        
    def register(self, user_data: dict) -> Tuple[int, str]:
        if not self.__prepare_user_data(user_data):
            return False, "Given invalid information for registration"
        try:
            users = list(self.__user_db.find({"_id": user_data['_id']}))
        except Exception as e:
            logging.exception('Invalid user id')
            return 400, 'Invalid user id'
        if len(users) == 1:
            user_info = copy.deepcopy(users[0])
            if user_info['email'] != user_data['email']:
                return 401, "Given wrong registration email"
            elif user_info['password'] != user_data['password']:
                return 403, "Given wrong registration password"
            return 200, 'Authentification complete'
        try:
            self.__user_db.insert_one(user_data)
        except Exception as e:
            logging.exception('Wrong registration data. Password must be at least 6 characters')
            return 400, 'Wrong registration data. Please check Email. Password must be at least 6 characters'
        return 200, 'Registration complete'

    def auth(self, user_data: dict) -> Tuple[int, str]:
        if not self.__prepare_user_data(user_data):
            return 401, "Given invalid information for authentification"
        try:
            users = list(self.__user_db.find({"_id": user_data['_id']}))
        except Exception as e:
            logging.exception('Invalid user id')
            return 400, 'Invalid user id'
        if len(users) != 1:
            logging.error('User with id %s not found', str(user_data['_id']))
            return 404, 'Unknown user. Please reset chdu connection and register'
        if users[0]['password'] != user_data['password']:
            logging.error('Invalid password')
            return 403, 'Invalid password'
        return 200, 'Authentification complete'
    
    def set_case_number(self, user_id: int, task_number: int, case_number: int) -> bool:
        out = self.__user_case_assoc.find_one_and_update({"_id": user_id}, {"$set":{"task"+str(task_number): case_number} })
        if out is None:
            self.__user_case_assoc.insert_one({"_id": user_id, "task"+str(task_number): case_number})
        return True
    
    def get_best_score(self,user_id: int, task_number: int):
        max_score_attemp = self.__task_db.find({"id_student": user_id, "task_out.number": task_number}).sort("score.total_score", -1).limit(1)
        out_d = list(max_score_attemp)
        return out_d[0]["score"]

    def get_count_attemps(self,user_id: int, task_number: int):
        attemps = list(self.__task_db.find({"id_student": user_id, "task_out.number": task_number}))
        # print(attemps)
        return len(attemps)
    
    def set_task(self, user_id: int, task_in: dict, task_out: dict, score: dict) -> bool:
        self.__task_db.insert_one({"id_student": user_id,"task_in": task_in, "task_out": task_out, "score": score})
        return True
    
    def get_case_number(self, user_id: int, task_number: int) -> int:
        out = self.__user_case_assoc.find_one({"_id": user_id})
        if out is None:
            return None
        if not 'task' + str(task_number) in out:
            return None
        return out['task' + str(task_number)]
    
    def __prepare_user_data(self, user_data: dict) -> bool:
        try:
            validate(instance=user_data, schema=REGISTER_SCHEME)
        except ValidationError:
            return False, "Invalid user data"
        try:
            user_data['_id'] = int(user_data.pop('id'))
        except ValueError:
            return False

        return True


    @property
    def host(self) -> str:
        return self.__host

    @property
    def port(self) -> int:
        return self.__port

from typing import Tuple
from pymongo import MongoClient
import json
import smtplib
import copy
import os
import logging
import secrets

from jsonschema import validate, ValidationError

LOGIN_SCHEME = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "$id": "https://example.com/employee.schema.json",
    "description": "Scheme for verification auth_data message form",
    "type": "object",
    "properties": {
        "token": {
            "type": "string"
        },
        "id": {
            "type": "string"
        },
        "name": {
            "type": "string"
        },
        "email": {
            "type": "string"
        }
    },
    "required": ["id", "name", "email", "token"]  
}

REGISTER_SCHEME = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "$id": "https://example.com/employee.schema.json",
    "description": "Scheme for verification auth_data message form",
    "type": "object",
    "properties": {
        "id": {
            "type": "string"
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
    def __init__(self, auth_manager_config: str):
        with open(auth_manager_config, 'r') as conf:
            config_dict = json.load(conf)
            self.__db_server = config_dict['db_connect']['host']
            self.__db_port = config_dict['db_connect']['port']
            self.__smtp_login = config_dict['smtp_connect']['login']
            self.__smtp_pass = config_dict['smtp_connect']['pass']
        
        self.__host = config_dict['host']
        self.__port = config_dict['port']

        self.__server_email = smtplib.SMTP('smtp.yandex.ru', 587)
        self.__server_email.ehlo() 
        self.__server_email.starttls()
        self.__server_email.login(self.__smtp_login, self.__smtp_pass)

        self.db_client = MongoClient('mongodb://{:s}:{:s}'.format(self.__db_server, str(self.__db_port)))
        self.__user_db = self.db_client['local-hdu']['InfoStudent']
        self.__user_case_assoc = self.db_client['local-hdu']['StudentsCases']
        self.__task_db = self.db_client['local-hdu']['StudentsAttempts']
        
    def register(self, user_data: dict) -> Tuple[bool, str]:
        ok = True
        error_msg = ""
        try:
            validate(instance=user_data, schema=REGISTER_SCHEME)
        except ValidationError:
            ok = False
            error_msg = "Invalid user data"
        
        if ok:
            gen_token = 0
            users = list(self.__user_db.find({"_id": user_data['id']}))
            print(users)
            reg = False
            if len(users) == 1:
                user_info = copy.deepcopy(users[0])
                if user_info['email'] != user_data['email']:
                    return False, "Given wrong registration email"
                gen_token = user_info['token']
                email_text = 'Key recovery complete.\n Your HDU Key: ' + gen_token
                dest_email = user_info['email']
            else:
                gen_token = secrets.token_hex(16)
                dest_email = user_data['email']
                reg = True
            try:
                subject = 'HDULab'
                email_text = 'Registration complete.\n Your HDU Key: ' + gen_token
                message = 'From: %s\nTo: %s\nSubject: %s\n\n%s' % (self.__smtp_login, dest_email, subject, email_text)
                print(message)
                # self.__server_email.set_debuglevel(1) # Необязательно; так будут отображаться данные с сервера в консоли
                self.__server_email.sendmail(self.__smtp_login, dest_email, message)
            except:
                ok = False
                error_msg = "Something went wrong"
            if reg:
                self.__user_db.insert_one({'_id': user_data['id'], 'name': user_data['name'], 'email': user_data['email'], 'token': gen_token})
        return ok, error_msg

    def auth(self, user_data: dict) -> Tuple[bool, str]:
        try:
            validate(instance=user_data, schema=LOGIN_SCHEME)
            users = list(self.__user_db.find({"_id": user_data['id']}))
            print(user_data)
            if len(users) != 1:
                logging.error('Logging error. User with id {:s} not found'.format(user_data['_id']))
                return False, 'Unknown login. Please reset chdu connection and register'
            if users[0]['token'] != user_data['token']:
                logging.error('Logging error. Invalid token')
                return False, 'Invalid token'
            return True, ''
        except ValidationError:
            return False, 'Invalid user data'
    
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

    @property
    def host(self) -> str:
        return self.__host

    @property
    def port(self) -> int:
        return self.__port
    

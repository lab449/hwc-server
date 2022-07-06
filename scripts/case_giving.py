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
from jsonschema import validate

class AuthHandler:
    def __init__(self, auth_manager_config: str):
        with open(auth_manager_config, 'r') as conf:
            config_dict = json.load(conf)
            self.__db_server = config_dict['db_connect']['host']
            self.__db_port = config_dict['db_connect']['port']

        self.db_client = MongoClient('mongodb://{:s}:{:s}'.format(self.__db_server, str(self.__db_port)))
        self.__user_db = self.db_client['local-hdu']['InfoStudent']
        self.__user_case_assoc = self.db_client['local-hdu']['StudentsCases']
        self.__task_db = self.db_client['local-hdu']['StudentsAttempts']
        
    def set_case_number(self, user_id: int, task_number: int, case_number: int) -> bool:
            out = self.__user_case_assoc.find_one_and_update({"_id": user_id}, {"$set":{"task"+str(task_number): case_number} })
            # if out is None:
            #     self.__user_case_assoc.insert_one({"_id": user_id, "task"+str(task_number): case_number})
            return True 
    
    def get_case_number(self, user_id: int, task_number: int) -> int:
        out = self.__user_case_assoc.find_one({"_id": user_id})
        if out is None:
            return None
        if not 'task' + str(task_number) in out:
            return None
        return out['task' + str(task_number)]

    def get_users(self) -> list:
        users = list(self.__user_db.find())
        return users

if __name__ == '__main__':
    auth = AuthHandler('auth_manager_config.json')

    users = auth.get_users()

    for u in users:
        cn = auth.get_case_number(u['_id'], 1)
        auth.set_case_number(u['_id'], 2, cn)
from typing import Tuple
from pymongo import MongoClient
import json
import smtplib
import copy
import os
import logging
import secrets
import numpy as np


import pandas as pd

scores_factor = [10.0/3, 10.0/3, 10.0/3, 10.0/4, 10.0/3, 10.0/22]


class AuthHandler:
    def __init__(self, auth_manager_config: str):
        with open(auth_manager_config, 'r') as conf:
            config_dict = json.load(conf)
            self.__db_server = config_dict['db_connect']['host']
            self.__db_port = config_dict['db_connect']['port']

        self.db_client = MongoClient('mongodb://{:s}:{:s}'.format(self.__db_server, str(self.__db_port)))
        self.__user_db = self.db_client['hwc-db']['InfoStudent']
        self.__user_case_assoc = self.db_client['hwc-db']['StudentsCases']
        self.__task_db = self.db_client['hwc-db']['StudentsAttempts']
    
    def get_attems(self, user_id: int, task_number: int) -> int:
        out = self.__user_case_assoc.find_one({"_id": user_id})
        if out is None:
            return None
        if not 'task' + str(task_number) in out:
            return None
        return out['task' + str(task_number)]

    def get_users(self) -> list:
        users = list(self.__user_db.find())
        return users

    def get_best_score(self, user_id: int, task_number: int):
        max_score_attemp = self.__task_db.find({"id_student": user_id, "task_out.number": task_number}).sort("score.total_score", -1).limit(1)
        out_d = list(max_score_attemp)
        if len(out_d) ==0:
            return None
        return out_d[0]["score"]

if __name__ == '__main__':
    auth = AuthHandler('auth_manager_config.json')
    df = pd.DataFrame(columns=('id', 'lab1', 'lab2', 'lab3', 'lab4', 'lab5', 'lab6'))
    users = auth.get_users()
    counter = 0
    for u in users:
        lab_scores = [int(u['_id'])]
        for i in range(6):
            max_score = auth.get_best_score(u['_id'], i+1)
            if max_score is None:
                max_score = 0
            else:
                max_score = max_score['total_score']
            if i==0:
                 max_score = min(3, max_score)
            lab_scores.append(np.ceil(max_score*scores_factor[i]))
        df.loc[counter] = lab_scores
        counter+=1

    for i in df.columns:
        try:
            df[[i]] = df[[i]].astype(float).astype(int)
        except:
            pass
    print(df)
    df.to_csv('labs_scores.csv', index=False)
        

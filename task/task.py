from __future__ import annotations
from typing import Tuple
import io, os, sys
import json
import jsonschema
import logging
import numpy as np
from jsonschema import validate, ValidationError

from abc import ABC, abstractmethod

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
# print(sys.path)

class TaskChecker():
    def __init__(self, task_config: dict):
        pass

    def check(self, answers: dict):
        pass

class Answer(ABC):
    def __init__(self, answer_config: dict):
        self._answer_config = answer_config


    @abstractmethod
    def check(self, value: dict) -> float:
        pass

class Task():
    def __init__(self, task_config_filename: str):
        with open(task_config_filename) as json_config:
            task_config = json.load(json_config) 
        with open('server_task_data/task_config_schema.json') as json_file:
            task_schema = json.load(json_file)
        validate(instance=task_config, schema=task_schema)

        self.__task_config = task_config
        # print(self.__task_config)
        self.__count_cases = len(task_config['cases'])
    
    def generate_case(self) -> Tuple[dict, int]:
        case_number = int(np.random.uniform(0, self.__count_cases-1))
        case = dict(self.__task_config['cases'][case_number])
        for a in case['answers'].keys():
            case['answers'][a] = []
        return case, case_number
        
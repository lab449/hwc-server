from __future__ import annotations
import copy
from math import ceil
from typing import Tuple
import os, sys
import json
import logging
import numpy as np
from jsonschema import validate, ValidationError

from abc import ABC, abstractmethod

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class CaseScore:
    def __init__(self, case_config: dict):
        self.__score = {}
        for a in case_config['answers'].keys():
            self.__score[a] = 0
    
    def __getitem__(self, key):
        return self.__score[key]
    
    def __setitem__(self, key, item):
        if isinstance(item, (int, float, type(None))):
            self.__score[key] = item
    
    @property
    def total(self):
        return  sum(filter(None, self.__score.values()))

    def jsonify(self) -> dict:
        case_score = copy.deepcopy(self.__score)
        case_score['total_score'] = self.total
        return case_score
    
    def __str__(self) -> str:
        return str(self.jsonify())
    
    def __repr__(self) -> str:
        return str(self.jsonify())

class Answer(ABC):
    def __init__(self, ans_config:dict): 
        with open('task/answer_config_schema.json') as json_file:
            ans_schema = json.load(json_file)
        validate(instance=ans_config, schema=ans_schema)
        self._ans_config = ans_config
        self._ans_value = ans_config['true_value']
    
    @abstractmethod
    def check(value) -> int:
        pass

class NumberAnswer(Answer):
    def __init__(self, ans_config: dict):
        super().__init__(ans_config)
        self._ans_value = float(self._ans_config['true_value'])
    
    def check(self, value) -> int:
        if not isinstance(value, (int, float)):
            return None
        score = self._ans_config['score'] if np.abs((self._ans_value - value)) <= self._ans_config['valid_range'] else 0.0
        return score

class IntegerAnswer(Answer):
    def __init__(self, ans_config: dict):
        super().__init__(ans_config)
        self._ans_value = int(self._ans_config['true_value'])

    def check(self, value) -> int:
        if not isinstance(value, int):
            return None
        score = self._ans_config['score'] if value==self._ans_value else 0.0
        return score

class ArrayAnswer(Answer):
    def __init__(self, ans_config: dict):
        super().__init__(ans_config)
        self._ans_value = np.array(self._ans_config['true_value'])
    
    def check(self, value) -> int:
        if not isinstance(value, list):
            return None
        value = np.array(value)
        if value.shape != self._ans_value.shape:
            return None
        score = self._ans_config['score'] if np.allclose(value, self._ans_value, rtol=0, atol=self._ans_config['valid_range']) else 0.0
        return score

class AnswerCreator:
    factory = {
        'list': ArrayAnswer,
        'float': NumberAnswer,
        'double': NumberAnswer,
        'int': IntegerAnswer
    }
    def create_answer(answer_config: dict) -> Answer:
        return AnswerCreator.factory[answer_config['inst']](answer_config)

class Case:
    def __init__(self, case_config: dict):
        with open('task/case_config_schema.json') as json_file:
            case_schema = json.load(json_file)
        validate(instance=case_config, schema=case_schema)
        self.__case_config = case_config
        self.__answers_dict = {}
        for c in case_config['answers'].keys():
            self.__answers_dict[c] = AnswerCreator.create_answer(case_config['answers'][c])
    
    def __str__(self) -> str:
        return str(self.jsonify(True))
    
    def __repr__(self) -> str:
        return str(self.jsonify(True))
    
    def jsonify(self, include_answers: bool = False) -> dict:
        case_info = copy.deepcopy(self.__case_config)
        for a in case_info['answers'].keys():
            if not include_answers:
                case_info['answers'][a] = '?'
            else:
                case_info['answers'][a] = case_info['answers'][a]['true_value']
        return case_info
    
    def check(self, answers: dict) -> CaseScore:
        cs = CaseScore(self.__case_config)
        for a in self.__answers_dict.keys():
            if a in answers:
                cs[a] = self.__answers_dict[a].check(answers[a])
            else:
                cs[a] = None
        return cs


class Task:
    def __init__(self, task_config_filename: str):
        with open(task_config_filename) as json_config:
            task_config = json.load(json_config) 
        with open('task/task_config_schema.json') as json_file:
            task_schema = json.load(json_file)
        validate(instance=task_config, schema=task_schema)
        self.__task_config = task_config
        self.__count_cases = len(self.__task_config['cases'])
    
    def generate_case_number(self) -> int:
        case_number = int(np.random.uniform(0, self.__count_cases))
        return case_number
    
    def get_case(self, case_number: int) -> Case:
        assert (case_number>0 and case_number< self.__count_cases), 'Invalid casenumber'
        return Case(self.__task_config['cases'][case_number])

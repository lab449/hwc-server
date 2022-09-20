import sys
import os
import json
from jsonschema import validate, ValidationError
from task.task import Task
from pathlib import Path

import pypandoc

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TaskManager():
    def __init__(self, task_manager_config_filename: str):
        with open(task_manager_config_filename) as json_config:
            task_manager_config = json.load(json_config) 
        with open('task/task_manager_config_schema.json') as json_file:
            task_schema = json.load(json_file)
        validate(instance=task_manager_config, schema=task_schema)
        self.__task_manager_config = task_manager_config
        self.__tasks_list = [Task(t['filepath']) for t in self.__task_manager_config['course_tasks']]
        self.__course_description = '<!DOCTYPE html><html><head><title>Test</title></head>\
                                        <body><h1>Getting started</h1></body></html>'

        # TODO: Add page decription multiformat generation
        if self.__task_manager_config['common_description'] !="":
            assert os.path.exists(self.__task_manager_config['common_description']), 'Description file not found'
            assert Path(self.__task_manager_config['common_description']).suffix=='.html', 'Given unsupported file extension for page description file, now expected only .html'
            with open(self.__task_manager_config['common_description'], 'r') as file:
                self.__course_description = file.read()
        
    
    def __getitem__(self, key: int):
        assert (key>=0 and key< len(self.__tasks_list)), "Unknown key"
        if not self.__task_manager_config['course_tasks'][key]['available']:
            return None
        else:
            return self.__tasks_list[key]

    def generate_description_page(self):
        return self.__course_description
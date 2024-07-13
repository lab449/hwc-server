from flask import Flask, jsonify
from flask import request, send_from_directory
from flask import render_template_string
import logging
import os,sys
import hashlib, pathlib

from auth import AuthHandler

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from task import task, task_manager

task_manager = task_manager.TaskManager('server_task_data/tasks_info.json')
mongodb_config = {
    'host': os.environ['MONGODB_HOSTNAME'],
    'port': os.environ['MONGODB_PORT'],
    'db': os.environ['MONGODB_DATABASE']
}
auth = AuthHandler(mongodb_config)
app = Flask(__name__)


def get_file_version(filename: str) -> dict:
    with open(filename,'rb') as f:
        client_bytes = f.read()
        f.close()
        return {'md5': hashlib.md5(client_bytes).hexdigest()}

def matlab_version():
    return get_file_version('/home/hwc/apps/hwc-server/clients/hwc-matlab-client/HWC.m'), get_file_version('/home/hwc/apps/hwc-server/clients/hwc-matlab-client/hwc_connect.m')

ATTEMPS_LIMIT = 40
MATLAB_CLIENT_VERSION, MATLAB_LAUNCHER_VERSION = matlab_version()

@app.route('/', methods=['GET'])
def root():
    return render_template_string(task_manager.generate_description_page())

@app.route('/api/ok', methods=['GET'])
def ok():
    return jsonify(isError= False, message= "OK", statusCode=200, data='')

@app.route('/api/register', methods=['POST'])
def register():
    content_type = request.headers.get('Content-Type')
    if 'application/json' in content_type:
        user_data = request.json['auth']
        code, msg = auth.register(user_data)
        return jsonify(isError=(code!=200), message=msg, statusCode=code, data=msg)
    return jsonify(isError= True,  message='Comething went wrong', statusCode=400)


@app.route('/api/login', methods=['POST'])
def login():
    content_type = request.headers.get('Content-Type')
    if 'application/json' in content_type:
        user_data = request.json['auth']
        code, msg = auth.auth(user_data)
        return jsonify(isError=(code!=200), message=msg, statusCode=code, data=msg)
    return jsonify(isError=True, statusCode=400, message="Something went wrong")

@app.route('/api/gettask', methods=['POST'])
def get_task():
    content_type = request.headers.get('Content-Type')
    if 'application/json' in content_type:
        try:
            user_data = request.json['auth']
            code, msg = auth.auth(user_data)
            if code!=200:
                logging.error('Authentification errors: %s',  user_data)
                return jsonify(isError=True, message=msg, statusCode=code)
            task_number = int(request.json['number'])
            case_number = auth.get_case_number(user_data['_id'], task_number)
            task = task_manager[task_number-1]
            if not task:
                return jsonify(isError=True, message='This task is unvailable right now', statusCode=400)
            if case_number is None:
                case_number = task.generate_case_number()
                auth.set_case_number(user_data['_id'], task_number, case_number)
            case = task.get_case(case_number)
            return jsonify(isError=True, message='', statusCode=code, data=case.jsonify())
        except Exception as e: 
            logging.error('Failed to get task. Error code: %s', str(e))
            return jsonify(isError= True, message= 'Task not found', statusCode=404)

    return jsonify(isError= True, message= 'Something went wrong', statusCode=400)

@app.route('/api/send_task', methods=['POST'])
def set_task():
    content_type = request.headers.get('Content-Type')
    if 'application/json' in content_type:
        user_data = request.json['auth']
        code, msg = auth.auth(user_data)
        if code!=200:
            return jsonify(isError=True, message=msg, statusCode=code)
        task_json= request.json['task']
        try:
            task_number = int(task_json['number'])
        except Exception as e: 
            logging.error('Failed to send task: %s', str(e))
            return jsonify(isError=True, message='Unknown task number', statusCode=400)
        
        count_attemps = auth.get_count_attemps(user_data['_id'], task_number)
        if count_attemps >= ATTEMPS_LIMIT:
            best_score = auth.get_best_score(user_data['_id'], task_number)
            return jsonify(isError=False, message= 'You\'ve run out of tries!(max={:d})\nYour max score:'.format(ATTEMPS_LIMIT), statusCode=200, data=best_score)

        case_number = auth.get_case_number(user_data['_id'], task_number)
        if case_number is None:
            return jsonify(isError= True, message= 'First you must get this task. You may have entered the wrong task number', statusCode=400)

        task = task_manager[task_number-1]
        if not task:
            return jsonify(isError=True, message='This task is unvailable right now', statusCode=400)
        case = task.get_case(case_number)
        score = case.check(task_json['answers'])
        auth.set_task(user_data['_id'], case.jsonify(True), task_json, score.jsonify())
        return jsonify(isError= False, message='You have {:d} attempts left'.format(ATTEMPS_LIMIT-count_attemps-1), statusCode=code, data=score.jsonify())
        
    return jsonify(isError= True, message= 'Something went wrong', statusCode=400)

@app.route('/files/<path:filename>', methods=['GET', 'POST'])
def download(filename):
    uploads = os.path.join('server_task_data', 'files')
    return send_from_directory(directory=uploads, path=filename)

@app.route('/clients/<path:filename>', methods=['GET', 'POST'])
def get_client(filename):
    uploads = os.path.join('clients')
    print(filename)
    return send_from_directory(directory=uploads, path=filename)

@app.route('/api/matlab/client_version', methods=['GET'])
def client_version():
    return jsonify(isError= False, message= 'Succes', statusCode=200, data=MATLAB_CLIENT_VERSION)

@app.route('/api/matlab/launcher_version', methods=['GET'])
def launcher_version():
    return jsonify(isError= False, message= 'Succes', statusCode=200, data=MATLAB_LAUNCHER_VERSION)
    

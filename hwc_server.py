from flask import Flask, jsonify
from flask import request, send_from_directory
from flask import render_template_string
import logging
import os,sys
import hashlib, pathlib
import math
from functools import wraps
from pymongo.errors import PyMongoError
from bson.errors import InvalidDocument

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

def api_response(code=200, message='', data=None):
    # MATLAB webwrite expects the legacy HTTP-200 envelope and checks these fields.
    return jsonify(isError=(code != 200), statusCode=code, message=message, data=data)


def json_endpoint(handler):
    @wraps(handler)
    def wrapped():
        payload = request.get_json(silent=True) if request.is_json else None
        if not isinstance(payload, dict) or not isinstance(payload.get('auth'), dict):
            return api_response(400, 'Expected a JSON object with auth data')
        try:
            return handler(payload)
        except (InvalidDocument, OverflowError):
            return api_response(400, 'Request contains a value that cannot be stored')
        except PyMongoError:
            logging.exception('Database operation failed')
            return api_response(503, 'Database temporarily unavailable')
    return wrapped


def select_task(value):
    if isinstance(value, bool):
        raise ValueError('Unknown task number')
    if isinstance(value, str):
        if not value.strip().isdigit():
            raise ValueError('Unknown task number')
    elif not isinstance(value, (int, float)):
        raise ValueError('Unknown task number')
    if isinstance(value, float) and (not math.isfinite(value) or not value.is_integer()):
        raise ValueError('Unknown task number')
    number = int(value)
    if not 1 <= number <= len(task_manager):
        raise ValueError('Unknown task number')
    return number, task_manager[number - 1]


@app.route('/api/register', methods=['POST'])
@json_endpoint
def register(payload):
    code, message = auth.register(payload['auth'])
    return api_response(code, message, message)


@app.route('/api/login', methods=['POST'])
@json_endpoint
def login(payload):
    code, message = auth.auth(payload['auth'])
    return api_response(code, message)


@app.route('/api/gettask', methods=['POST'])
@json_endpoint
def get_task(payload):
    user_data = payload['auth']
    code, message = auth.auth(user_data)
    if code != 200:
        return api_response(code, message)
    try:
        task_number, selected = select_task(payload.get('number'))
    except ValueError as exc:
        return api_response(400, str(exc))
    if selected is None:
        return api_response(400, 'This task is unavailable right now')
    user_id = user_data['id']
    case_number = auth.get_case_number(user_id, task_number)
    if case_number is None:
        case_number = auth.set_case_number(user_id, task_number, selected.generate_case_number())
    try:
        case = selected.get_case(case_number)
    except ValueError:
        return api_response(409, 'Assigned task variant is invalid; contact the instructor')
    return api_response(data=case.jsonify())


@app.route('/api/send_task', methods=['POST'])
@json_endpoint
def set_task(payload):
    user_data = payload['auth']
    code, message = auth.auth(user_data)
    if code != 200:
        return api_response(code, message)
    submission = payload.get('task')
    if not isinstance(submission, dict) or not isinstance(submission.get('answers'), dict):
        return api_response(400, 'Expected a task object with an answers object')
    try:
        task_number, selected = select_task(submission.get('number'))
    except ValueError as exc:
        return api_response(400, str(exc))
    if selected is None:
        return api_response(400, 'This task is unavailable right now')
    user_id = user_data['id']
    case_number = auth.get_case_number(user_id, task_number)
    if case_number is None:
        return api_response(400, 'First you must get this task')
    count = auth.get_count_attemps(user_id, task_number)
    if count >= ATTEMPS_LIMIT:
        return api_response(message="You've run out of tries!(max={:d})\nYour max score:".format(ATTEMPS_LIMIT),
                            data=auth.get_best_score(user_id, task_number))
    try:
        case = selected.get_case(case_number)
    except ValueError:
        return api_response(409, 'Assigned task variant is invalid; contact the instructor')
    score = case.check(submission['answers'])
    submission = dict(submission, number=task_number)
    auth.set_task(user_id, case.jsonify(True), submission, score.jsonify())
    return api_response(message='You have {:d} attempts left'.format(ATTEMPS_LIMIT - count - 1), data=score.jsonify())


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
    

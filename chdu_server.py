from flask import Flask, jsonify
from flask import request, send_from_directory
import logging
import os,sys
import hashlib, pathlib

from auth import AuthHandler

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from task import task
ATTEMPS_LIMIT = 20

auth = AuthHandler('auth_manager_config.json')
task_list = (task.Task('server_task_data/test_task.json'),)

app = Flask(__name__)

@app.route('/ok', methods=['GET'])
def ok():
    return jsonify(isError= False, message= "OK", statusCode=200, data=''), 200

@app.route('/register', methods=['POST'])
def register():
    content_type = request.headers.get('Content-Type')
    if 'application/json' in content_type:
        user_data = request.json['auth']
        ok, msg = auth.register(user_data)
        if ok:
            # print('Register complete')
            return jsonify(isError= False, message= msg, statusCode=200, data=msg), 200
    out = jsonify(isError= True,  message=msg, statusCode=404, data=msg), 404
    return out 

@app.route('/login', methods=['POST'])
def login():
    content_type = request.headers.get('Content-Type')
    if 'application/json' in content_type:
        user_data = request.json['auth']
        ok, msg = auth.auth(user_data)
        if ok:
            return jsonify(isError= False, message=msg, statusCode=200, data=msg), 200
        return jsonify(isError= True, message=msg, statusCode=401, data=msg), 401
    return jsonify(isError= True,  message="Something went wrong", statusCode=404, data="Something went wrong"), 404

@app.route('/gettask', methods=['POST'])
def get_task():
    content_type = request.headers.get('Content-Type')
    if 'application/json' in content_type:
        try:
            user_data = request.json['auth']
            ok = auth.auth(user_data)
            if ok:
                print(request.json)
                task_number = int(request.json['number'])
                case_number = auth.get_case_number(user_data['id'], task_number)
                print(case_number)
                if case_number is None:
                    case_number = task_list[task_number-1].generate_case_number()
                    auth.set_case_number(user_data['id'], task_number, case_number)
                case = task_list[task_number-1].get_case(case_number)
                return jsonify(isError= False, message= '', statusCode=200, data=case.jsonify()), 200
        except Exception as e: 
            logging.error('Failed to get task. Error code: '+ str(e))
            return jsonify(isError= True, message= 'Unknown task number', statusCode=404, data=''), 404
    return jsonify(isError= True, message= 'Something went wrong', statusCode=400, data=''), 404

@app.route('/send_task', methods=['POST'])
def set_task():
    content_type = request.headers.get('Content-Type')
    if 'application/json' in content_type:
        try:
            user_data = request.json['auth']
            ok = auth.auth(user_data)
            if ok:
                task_json= request.json['task']
                task_number = int(task_json['number'])
                count_attemps = auth.get_count_attemps(user_data['id'], task_number)
                print(count_attemps)
                if count_attemps >= ATTEMPS_LIMIT:
                    best_score = auth.get_best_score(user_data['id'], task_number)
                    return jsonify(isError= False, message= 'You\'ve run out of tries!(max={:d})\nYour max score:'.format(ATTEMPS_LIMIT), statusCode=200, data=best_score), 200
                case_number = auth.get_case_number(user_data['id'], task_number)
                if case_number is None:
                    return jsonify(isError= True, message= 'First you must get this task. You may have entered the wrong task number', statusCode=400, data=''), 200
                case = task_list[task_number-1].get_case(case_number)
                score = case.check(task_json['answers'])
                auth.set_task(user_data['id'], case.jsonify(True), task_json, score.jsonify())
                return jsonify(isError= False, message= 'You have {:d} attempts left'.format(ATTEMPS_LIMIT-count_attemps-1), statusCode=200, data=score.jsonify()), 200
        except Exception as e: 
            logging.error('Failed to send task: '+ str(e))
            return jsonify(isError= True, message= 'Unknown task number', statusCode=404, data=''), 404
    return jsonify(isError= True, message= 'Something went wrong', statusCode=400, data=''), 404


@app.route('/matlab_client_version', methods=['GET'])
def client_update():
    try:
        with open('../hwc-matlab-client/CHDU.m','rb') as f:
            client_bytes = f.read()
            f.close()
        client_hash = {'md5': hashlib.md5(client_bytes).hexdigest()}
        # print(client_hash)
        return jsonify(isError= False, message= 'Succes', statusCode=200, data=client_hash), 200
    except Exception as e: 
        logging.error('Failed to get task: '+ str(e))
        return jsonify(isError= True, message= 'Unknown task number', statusCode=404, data=''), 404

@app.route('/files/<path:filename>')
def download_file(filename):
    return send_from_directory("../files", filename, as_attachment=True)

@app.route('/hwc-matlab-client/<path:filename>')
def update_client(filename):
    return send_from_directory("../hwc-matlab-client", filename, as_attachment=True)


if __name__ == '__main__':
    # context = ('hdu2--cacert503.pem', 'localhost.pem')#certificate and key files
    port = int(os.environ.get('PORT', 5000))
    # app.run(debug=True, ssl_context=context, host='127.0.0.1', port=port)
    app.run(debug=True, host='127.0.0.1', port=port)

    
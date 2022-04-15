from flask import Flask, jsonify
from flask import request
import logging
import os,sys
import hashlib, pathlib

from auth import AuthHandler

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from task import task

auth = AuthHandler(('127.0.0.1',27017), ('hdulab.check@yandex.ru', 'xlfxrfnibsoeufnt'))
task_list = [task.Task('server_task_data/task1.json')]

app = Flask(__name__)

@app.route('/ok', methods=['GET'])
def ok():
    return jsonify(isError= False, message= "OK", statusCode= 200, data=''), 200

@app.route('/register', methods=['POST'])
def register():
    content_type = request.headers.get('Content-Type')
    if 'application/json' in content_type:
        json_data = request.json['auth']
        ok = auth.register(json_data)
        if ok:
            # print('Register complete')
            return jsonify(isError= False, message= "Success", statusCode= 200, data=''), 200
    out = jsonify(isError= True,  message= 'Failed', statusCode= 404, data=''), 404
    return out 

@app.route('/login', methods=['POST'])
def login():
    content_type = request.headers.get('Content-Type')
    if 'application/json' in content_type:
        json_data = request.json['auth']
        ok = auth.auth(json_data)
        if ok:
            return jsonify(isError= False, message= "Success", statusCode= 200, data=''), 200
    return jsonify(isError= True,  message= 'Failed', statusCode= 404, data=''), 404

@app.route('/gettask', methods=['POST'])
def get_task():
    content_type = request.headers.get('Content-Type')
    if 'application/json' in content_type:
        json_data = request.json['auth']
        ok = auth.auth(json_data)
        try:
            if ok:
                print(json_data)
                task_number = int(request.json['number'])
                gen_task, case_number = task_list[task_number-1].generate_case()
                print(gen_task)
                return jsonify(isError= False, message= 'Succes', statusCode= 200, data=gen_task), 200
        except Exception as e: 
            logging.error('Failed to get task: '+ str(e))
            return jsonify(isError= True, message= 'Unknown task number', statusCode= 404, data=''), 404
    return jsonify(isError= True, message= 'Failed', statusCode= 404, data=''), 404


@app.route('/client_version', methods=['GET'])
def client_update():
    try:
        with open('../client/CHDU.m','rb') as f:
            client_bytes = f.read()
            f.close()
        client_hash = {'md5': hashlib.md5(client_bytes).hexdigest()}
        # print(client_hash)
        return jsonify(isError= False, message= 'Succes', statusCode= 200, data=client_hash), 200
    except Exception as e: 
        logging.error('Failed to get task: '+ str(e))
        return jsonify(isError= True, message= 'Unknown task number', statusCode= 404, data=''), 404
    # return jsonify(isError= True, message= 'Failed', statusCode= 404, data=''), 404




if __name__ == '__main__':
    # context = ('hdu2--cacert503.pem', 'localhost.pem')#certificate and key files
    port = int(os.environ.get('PORT', 5000))
    # app.run(debug=True, ssl_context=context, host='127.0.0.1', port=port)
    app.run(debug=True, host='127.0.0.1', port=port)

    
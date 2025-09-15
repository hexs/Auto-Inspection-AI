import os
import logging
import time
from hexss import check_packages

check_packages(
    'numpy', 'opencv-python', 'Flask', 'requests', 'pygame-gui',
    'tensorflow', 'keras', 'pyzbar',
    auto_install=True, verbose=False
)

from hexss import json_load, json_update, close_port, get_hostname
from hexss.network import get_all_ipv4
from flask import Flask, render_template, request, jsonify

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)


@app.route('/api/get_model', methods=['GET'])
def api_get_model():
    data = app.config['data']
    return jsonify({
        "model_names": data.get("model_names", []),
        "model_name": data.get("model_name")
    })


@app.route('/api/change_model', methods=['GET'])
def api_change_model():
    data = app.config['data']
    model_name = request.args.get('model_name', type=str)
    if not model_name:
        return jsonify({"status": "error", "message": "missing model_name"}), 400

    allowed = set(data.get("model_names", []))
    if model_name not in allowed:
        return jsonify({"status": "error", "message": f"invalid model_name: {model_name}"}), 400

    data['model_name'] = model_name
    data['events'].append('change_model')

    print("Change model", model_name)

    return jsonify({"status": "ok", "model_name": model_name}), 200


@app.route('/change_model', methods=['GET'])
def change_model():
    return render_template('change_model.html')


@app.route('/status_robot', methods=['GET'])
def status_robot():
    data = app.config['data']
    return data['robot capture']


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        button_name = request.form.get('button')
        if button_name:
            data = app.config['data']
            data['events'].append(button_name)
            logger.info(f"Button clicked: {button_name}")
    return render_template('index.html')


@app.route('/data', methods=['GET'])
def data():
    def filter_list(d: list):
        filtered = []
        for v in d:
            if isinstance(v, (int, float, bool, str)):
                filtered.append(v)
            if isinstance(v, (list, tuple)):
                filtered.append(filter_list(v))
            if isinstance(v, dict):
                filtered.append(filter_dict(v))
        return filtered

    def filter_dict(d):
        filtered = {}
        for k, v in d.items():
            if isinstance(v, (int, float, bool, str)):
                filtered[k] = v
            if isinstance(v, (list, tuple)):
                filtered[k] = filter_list(v)
            if isinstance(v, dict):
                filtered[k] = filter_dict(v)
        return filtered

    data: dict = app.config['data']
    filtered_data = filter_dict(data)

    return jsonify(filtered_data), 200


def run_server(data):
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)

    app.config['data'] = data

    ipv4 = data['config']['ipv4']
    port = data['config']['port']

    if ipv4 == '0.0.0.0':
        for ipv4_ in {'127.0.0.1', *get_all_ipv4(), get_hostname()}:
            logging.info(f"Running on http://{ipv4_}:{port}")
    else:
        logging.info(f"Running on http://{ipv4}:{port}")

    app.run(host=ipv4, port=port, debug=False, use_reloader=False)

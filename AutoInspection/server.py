import os
import logging
import time
from pathlib import Path

import hexss

hexss.check_packages(
    'numpy', 'opencv-python', 'Flask', 'requests', 'pygame-gui',
    'tensorflow', 'keras', 'pyzbar',
    auto_install=True, verbose=False
)

from hexss import json_load, json_update, close_port, get_hostname
from hexss.network import get_all_ipv4
from hexss.download import download
from flask import Flask, render_template, request, jsonify
import cv2
import numpy as np

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


@app.route('/api/change_image', methods=['POST'])
def api_change_image():
    data = app.config['data']
    if 'image' not in request.files:
        return jsonify({"status": "error", "message": "No image provided"}), 400

    file = request.files['image']
    file_bytes = np.frombuffer(file.read(), np.uint8)
    img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
    if img is None:
        return jsonify({"status": "error", "message": "Invalid image"}), 400

    data['img'] = img
    data['events'].append('change_image')

    return jsonify({"status": "ok"}), 200


@app.route('/change_image', methods=['GET'])
def change_image():
    return render_template('change_image.html')


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


def download_static_files():
    download(
        'https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/css/bootstrap.min.css',
        dest_dir=Path(__file__).parent / 'static'
    )


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

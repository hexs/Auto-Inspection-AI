import os
import logging
import time
from hexss import check_packages

check_packages(
    'numpy', 'opencv-python', 'Flask', 'requests', 'pygame-gui',
    'tensorflow', 'keras', 'pyzbar',
    install=True
)

from hexss import json_load, json_update, close_port, get_hostname
from hexss.network import get_all_ipv4
from hexss.path import get_script_directory, move_up
from hexss.image import get_image_from_url
import numpy as np
import cv2
from flask import Flask, render_template, request, jsonify
import requests

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)


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
    data = app.config['data']
    print(data)
    return jsonify(data), 200


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


def send_request(robot_url, endpoint, method='post', **kwargs):
    try:
        response = getattr(requests, method)(f"{robot_url}/api/{endpoint}", **kwargs)
        response.raise_for_status()
        logger.info(f"{endpoint.capitalize()} request sent successfully")
        return response.json() if method == 'get' else None
    except requests.RequestException as e:
        logger.error(f"Error sending {endpoint} request: {e}")
        return None


def robot_capture(data: dict):
    '''
    for auto inspection x robot only

    :param data: dict data
    :return: None
    '''

    # if data.get('xfunction') != "robot":
    # return

    def move_and_capture(row):
        send_request(data['config']['robot_url'], "move_to", json={"row": row})
        old_res = ["1", "2", "3", "4", "5"]
        while True:
            res = send_request(data['config']['robot_url'], "current_position", method="get")
            old_res.append(res)
            old_res.remove(old_res[0])
            if old_res[0] == old_res[1] == old_res[2] == old_res[3] == old_res[4]:
                break

        time.sleep(1.7)
        return get_image_from_url(data['config']['url_image'])

    while data['play']:
        time.sleep(0.1)
        if data['robot capture'] == 'capture':
            # send_request(data['config']['robot_url'], "home")
            # time.sleep(5)

            images = [move_and_capture(i) for i in range(1, 10)]
            send_request(data['config']['robot_url'], "move_to", json={"row": 0})

            # if not all(images):
            # logger.error("Failed to capture all images")
            # data['robot capture'] = 'capture error'
            # continue

            wh = images[0].shape[1::-1]
            y = lambda p: int(wh[1] * p)
            x = lambda p: int(wh[0] * p)

            image = np.concatenate((
                np.concatenate((images[0][y(0):y(.5), x(.2):x(.7)], images[1][y(.5):y(1), x(.2):x(.7)]), axis=0),
                np.concatenate((images[2][y(0):y(.5), x(.4):x(.6)], images[3][y(.5):y(1), x(.4):x(.6)]), axis=0),
                np.concatenate((images[4][y(0):y(.5), x(.2):x(.8)], images[5][y(.5):y(1), x(.2):x(.8)]), axis=0),
                np.concatenate((images[6][y(0):y(.5), x(.0):x(.3)], images[7][y(.5):y(1), x(.0):x(.3)]), axis=0),
                np.concatenate((images[6][y(0):y(.5), x(.7):x(1.)], images[7][y(.5):y(1), x(.7):x(1.)]), axis=0),
            ), axis=1)

            image = np.concatenate((
                np.zeros([500, image.shape[1], 3], dtype=np.uint8),
                image
            ), axis=0)
            image[0:500, 1000:3048] = images[8][500:1000, :]

            data['image'] = image
            data['robot capture'] = 'capture ok'

            for i, image in enumerate(images):
                os.makedirs('log', exist_ok=True)
                cv2.imwrite(f'log/{i}.png', image)


if __name__ == '__main__':
    import auto_inspection
    from hexss.threading import Multithread

    config = json_load('config.json', {
        'ipv4': '0.0.0.0',
        'port': 3000,
        'device_note': 'PC, RP',
        'device': 'RP',
        'resolution_note': '1920x1080, 800x480',
        'resolution': '800x480',
        'model_name': '-',
        'model_names': ["QC7-7990-000", "POWER-SUPPLY-FIXING-UNIT"],
        'fullscreen': True,
        'image_url': 'http://127.0.0.1:2002/image?source=video_capture&id=0',
    }, True)

    close_port(config['ipv4'], config['port'], verbose=False)

    script_directory = get_script_directory()
    projects_directory = move_up(script_directory)

    m = Multithread()
    data = {
        'config': config,
        'script_directory': script_directory,
        'projects_directory': projects_directory,
        'model_name': config['model_name'],
        'model_names': config['model_names'],
        'events': [],
        'play': True,
    }

    m.add_func(auto_inspection.main, args=(data,))
    m.add_func(run_server, args=(data,), join=False)

    m.start()
    try:
        while data['play']:
            # print(m.get_status())
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        data['play'] = False
        m.join()

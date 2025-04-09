import time
from hexss import check_packages

check_packages(
    'numpy', 'opencv-python', 'Flask', 'requests', 'pygame', 'pygame-gui',
    'tensorflow', 'keras', 'pyzbar', 'AutoInspection', 'matplotlib', 'pyserial',
    auto_install=True
)

from hexss import json_load, close_port
from hexss.serial import Arduino
from AutoInspection import AutoInspection
from AutoInspection.server import run_server


def handle_arduino_events(data):
    ar = Arduino('Arduino', 'USB-SERIAL CH340')
    ar.pinMode(3,2)
    ar.waiting_for_reply(5)

    while data['play']:
        if ar.is_falling_edge(3):
            # data['events'].append('Capture&Predict')
            data['events'].append('Predict')
        time.sleep(0.02)


def main(data):
    app = AutoInspection(data)
    app.run()


if __name__ == '__main__':
    from hexss.threading import Multithread

    config = json_load('config.json', {
        "projects_directory": r"C:\PythonProjects",
        'ipv4': '0.0.0.0',
        'port': 3000,
        'resolution_note': '1920x1080, 800x480',
        'resolution': '1920x1080',
        'model_name': '-',
        'model_names': ["QC7-7990-000-Example", ],
        'fullscreen': True,
        'image_url': 'http://127.0.0.1:2002/image?source=video_capture&id=0',
    }, True)

    close_port(config['ipv4'], config['port'], verbose=False)

    m = Multithread()
    data = {
        'config': config,
        'model_name': config['model_name'],
        'model_names': config['model_names'],
        'events': [],
        'play': True,
    }

    m.add_func(main, args=(data,))
    m.add_func(run_server, args=(data,), join=False)
    m.add_func(handle_arduino_events, args=(data,))

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

import time
from hexss import check_packages

check_packages(
    'numpy', 'opencv-python', 'Flask', 'requests', 'pygame-gui',
    'tensorflow', 'keras', 'pyzbar',
    auto_install=True, verbose=False
)

from hexss import json_load, close_port
from AutoInspection import AutoInspection
from AutoInspection.server import run_server


def main(data):
    app = AutoInspection(data)
    app.run()


if __name__ == '__main__':
    from hexss.threading import Multithread

    config = json_load('config.json', {
        "projects_directory": r"C:\PythonProjects",
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

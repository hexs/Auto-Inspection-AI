import time
from pathlib import Path
from datetime import datetime, timedelta
from hexss import check_packages

check_packages(
    'numpy', 'opencv-python', 'Flask', 'requests', 'pygame', 'pygame-gui',
    'tensorflow', 'keras', 'pyzbar', 'AutoInspection', 'matplotlib',
    'gpiozero', 'lgpio', 'pigpio',
    'flatbuffers==23.5.26',
    auto_install=True
)

from hexss import json_load, close_port, system, username
from AutoInspection import AutoInspection, training
from AutoInspection.server import run_server


def handle_raspberrypi_io(data, ui):
    from gpiozero import LED, Button

    g_button = Button(5)
    y_button = Button(6)
    g_led = LED(17)
    y_led = LED(27)

    last_now = datetime.now()
    g_button_status = [0, 0]
    y_button_status = [0, 0]
    while True:
        now = datetime.now()
        g_button_status[0] = g_button_status[1]
        g_button_status[1] = g_button.is_pressed
        y_button_status[0] = y_button_status[1]
        y_button_status[1] = y_button.is_pressed

        if g_button_status[1] and not g_button_status[0]:
            data['events'].append('Capture&Predict')

        if y_button_status[1] and not y_button_status[0]:
            data['events'].append('Capture&Predict')

        if now - last_now > timedelta(seconds=0.5):
            last_now = now

            res = ui.res_textbox.texts.get('res')

            if res and res.text == 'Wait':
                y_led.off()
                g_led.toggle()

            elif res and res.text == 'NG':
                g_led.off()
                y_led.toggle()

            else:
                y_led.off()
                g_led.off()

        time.sleep(0.02)


if __name__ == '__main__':
    from hexss.threading import Multithread

    config = json_load('config.json', {
        'projects_directory': r'C:\PythonProjects' if system == 'Windows' else f'/home/{username}/PythonProjects',
        'ipv4': '0.0.0.0',
        'port': 3000,
        'resolution_note': '1920x1080, 800x480',
        'resolution': '1920x1080' if system == 'Windows' else '800x480',
        'model_name': '-',
        'model_names': ["QC7-7990-000-Example", ],
        'fullscreen': True,
        'image_url': 'http://127.0.0.1:2002/image?source=video_capture&id=0',
    }, True)

    close_port(config['ipv4'], config['port'], verbose=False)

    # download example
    if 'auto_inspection_data__QC7-7990-000-Example' not in \
            list(p.name for p in Path(config['projects_directory']).iterdir()):
        from hexss.github import download

        download(
            'hexs', 'auto_inspection_data__QC7-7990-000-Example',
            dest_folder=Path(config['projects_directory']) / 'auto_inspection_data__QC7-7990-000-Example'
        )

    # training
    try:
        training(
            *config['model_names'],
            config={
                'projects_directory': config['projects_directory'],
                'batch_size': 32,
                'img_height': 180,
                'img_width': 180,
                'epochs': 5,
                'shift_values': [-4, -2, 0, 2, 4],
                'brightness_values': [-24, -12, 0, 12, 24],
                'contrast_values': [-12, -6, 0, 6, 12],
                'max_file': 20000,
            }
        )
    except Exception as e:
        print(e)
    data = {
        'config': config,
        'model_name': config['model_name'],
        'model_names': config['model_names'],
        'events': [],
        'play': True,
    }

    ui = AutoInspection(data)

    m = Multithread()
    m.add_func(run_server, args=(data,), join=False)
    m.add_func(handle_raspberrypi_io, args=(data, ui))

    m.start()

    ui.run()

    m.join()

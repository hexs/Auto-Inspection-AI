import time
from datetime import datetime, timedelta
from hexss import check_packages

check_packages(
    'numpy', 'opencv-python', 'Flask', 'requests', 'pygame', 'pygame-gui',
    'tensorflow', 'keras', 'pyzbar', 'AutoInspection', 'matplotlib',
    'gpiozero',
    auto_install=True
)

from hexss import json_load, close_port
from AutoInspection import AutoInspection
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

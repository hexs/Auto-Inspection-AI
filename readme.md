# Auto-Inspection-AI

---

## setup

### 1. Create Virtual Environment

- Linux
    ```bash
    python3 -m venv .venv
    ```
- Windows
    ```bash
    python -m venv .venv
    ```

### 2. Activate Virtual Environment

- Linux
    ```bash
    source .venv/bin/activate
    ```
- Windows
   ```bash
   .venv/Scripts/activate
   ```

### 3. Install `hexss`

```bash
pip install hexss
```

> if use Pip with a Proxy Server.<br>
> `pip install --proxy http://<proxyserver_name>:<port> hexss`<br>
> or<br>
> `pip install --proxy http://<usr_name>:<password>@<proxyserver_name>:<port> hexss`<br>
>
>- **such as**
   >   ```bash
   >   pip install --proxy http://150.61.8.70:10086 hexss
   >   ```
>- **Set Proxy** (if using Pip with a Proxy Server) for auto install packages
   >   ```bash
   >   hexss config proxies.http http://150.61.8.70:10086
   >   hexss config proxies.https http://150.61.8.70:10086
   >   ```

---

## example for use

```python
import time
from pathlib import Path
from hexss import check_packages

check_packages(
    'numpy', 'opencv-python', 'Flask', 'requests', 'pygame', 'pygame-gui',
    'tensorflow', 'keras', 'pyzbar', 'AutoInspection', 'matplotlib',
    auto_install=True
)

from hexss import json_load, close_port
from hexss.github import download
from AutoInspection import AutoInspection, training
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
        'resolution_note': '1920x1080, 800x480',
        'resolution': '1920x1080',
        'model_name': '-',
        'model_names': ["QC7-7990-000-Example", ],
        'fullscreen': True,
        'image_url': 'http://127.0.0.1:2002/image?source=video_capture&id=0',
    }, True)

    close_port(config['ipv4'], config['port'], verbose=False)

    # download example
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


```
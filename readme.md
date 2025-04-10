# Auto-Inspection-AI

---

## Setup Instructions

### Linux Setup

1. **Create Project Folder**
   ```
   mkdir -p /home/pi/PythonProjects/auto_inspection
   ```

2. **Change Directory to Project Folder**
   ```
   cd /home/pi/PythonProjects/auto_inspection
   ```

3. **Create Virtual Environment**
   ```
   python3 -m venv .venv
   ```

4. **Activate Virtual Environment**
   ```
   source .venv/bin/activate
   ```

---

### Windows Setup

1. **Create Project Folder**
   ```
   mkdir C:\\PythonProjects\auto_inspection
   ```

2. **Change Directory to Project Folder**
   ```
   cd C:\\PythonProjects\auto_inspection
   ```

3. **Create Virtual Environment**
   ```
   python -m venv .venv
   ```

4. **Activate Virtual Environment**
   ```
   .venv/Scripts/activate
   ```

---

## Installing `hexss`

Install the required package using `pip`:

```
pip install hexss
```

> **Note:** If you are using `pip` with a proxy server, you can use the following commands:
>
> ```
> pip install --proxy http://<proxyserver_name>:<port> hexss
> pip install --proxy http://<usr_name>:<password>@<proxyserver_name>:<port> hexss
> ```
>
> Example:
> ```
> pip install --proxy http://150.61.8.70:10086 hexss
> ```
>
> To set up a proxy for automatic package installation:
> ```
> hexss config proxies.http http://150.61.8.70:10086
> hexss config proxies.https http://150.61.8.70:10086
> ```

---

## Example Usage

### General Example

See the [full example code](https://github.com/hexs/Auto-Inspection-AI/blob/main/example/run.py) for basic usage.

---

### Using with Arduino

1. **Handle Arduino Functionality**

```python
def handle_arduino_events():
    from hexss.serial import Arduino
    ar = Arduino('Arduino', 'USB-SERIAL CH340')
    ar.pinMode(3, 2)
    ar.waiting_for_reply(5)

    while data['play']:
        if ar.is_falling_edge(3):
            data['events'].append('Capture&Predict')
        time.sleep(0.02)
```

2. **Add to Multithread**

```python
m.add_func(handle_arduino_events)
```

See the [full example code](https://github.com/hexs/Auto-Inspection-AI/blob/main/example/run_with_arduino.py) for Arduino integration.

---

### Using with Raspberry Pi

1. **Handle Raspberry Pi I/O**

```python
def handle_raspberrypi_io(data, ui):
    from gpiozero import LED, Button
    from datetime import datetime, timedelta

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
```

2. **Add to Multithread**

```python
m.add_func(handle_raspberrypi_io, args=(data, ui))
```

See the [full example code](https://github.com/hexs/Auto-Inspection-AI/blob/main/example/run_with_raspberry_pi.py) for Raspberry Pi integration.

---

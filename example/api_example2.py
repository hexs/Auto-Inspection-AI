from pathlib import Path
from itertools import product
from concurrent.futures import ProcessPoolExecutor, as_completed
import os
import random
import time
import urllib
from pathlib import Path

import requests
import hexss.env

hexss.env.unset_proxy()
IP_ADDRESS = 'http://s-pcs235000:3000/'
# MODEL = 'QD1-1985'
# MODEL = 'QD1-1998'
# MODEL = 'QD1-2001'
# MODEL = 'QD1-2073'
MODEL = 'QC5-9973' #
# MODEL = "QC7-7957"
# MODEL = "QC4-9336" ##
# MODEL = "FE3-8546"
# MODEL = "4A3-5526"
# MODEL = "QC7-2413"

def _process_one(args):
    p, dx, dy, b, c, s = args
    from hexss.image import Image  # Import inside the worker to avoid pickling issues

    out_dir = p.parent / "o"
    out_dir.mkdir(exist_ok=True)

    im = Image(p)

    im = im.shift(dx, dy).brightness(b).contrast(c).sharpness(s)
    out_path = out_dir / f"{'ok' if 'ok' in str(p.stem).lower() else 'ng'}/{p.stem}_x{dx}_y{dy}_b{b:.1f}_c{c:.1f}_s{s:.1f}{p.suffix}"
    im.save(out_path)
    return str(out_path)


def get_image():
    root = Path(rf"C:\PythonProjects\auto_inspection_data__{MODEL}\img_full - Copy")
    files = list(root.glob("*.png"))
    s_factors = [0.9, 1.0, 1.1]
    b_factors = [0.9, 1.0, 1.1]
    c_factors = [0.9, 1.0, 1.1]

    # ignore dark
    # s_factors = [0.8, 1.0, 1.2]
    # b_factors = [1.0, 1.2]
    # c_factors = [0.8, 1.0]
    # ignore light
    # s_factors = [0.8, 1.0, 1.2]
    # b_factors = [0.8, 1.0]
    # c_factors = [1.0, 1.2]

    dxdy = [-5, 0, 5]
    tasks = [(p, dx, dy, b, c, s) for p in files for (dx, dy, b, c, s) in
             product(dxdy, dxdy, b_factors, c_factors, s_factors)]
    total = len(tasks)

    # Tune workers: cpu_count is a good default; lower if you want to keep UI responsive
    max_workers = os.cpu_count() or 4
    print(f"Processing {total} variants across {len(files)} files with {max_workers} workers...")

    done = 0
    errors = 0
    with ProcessPoolExecutor(max_workers=max_workers) as ex:
        futures = [ex.submit(_process_one, t) for t in tasks]
        for fut in as_completed(futures):
            try:
                out_path = fut.result()
                done += 1
                if done % 10 == 0 or done == total:
                    print(end=f"\r[{done}/{total}] write: {out_path}")
            except Exception as e:
                errors += 1
                print(end=f"\rERROR: {e}\n")

    print(f"Finished: {done} succeeded, {errors} failed.")


def f(root):
    files = list(root.glob("*.png"))
    for i, p in enumerate(random.sample(files, k=min(30, len(files)))):
        print(i, p)
        while True:
            try:
                r = requests.post(IP_ADDRESS + 'api/change_image', files={'image': open(p, 'rb')})
                print(r.status_code, r.text)
                if r.status_code == 200:
                    break
            except Exception as e:
                print(e)
            time.sleep(1)
        time.sleep(1)

        while True:
            try:
                r = requests.post(IP_ADDRESS, data={'button': 'Predict'})
                print(r.status_code)
                if r.status_code == 200:
                    break
            except Exception as e:
                print(e)
            time.sleep(1)
        time.sleep(0.5)


if __name__ == '__main__':
    # get_image()

    # change_model
    r = requests.get(IP_ADDRESS + f'api/change_model?model_name={MODEL}')
    print(r.status_code, r.text)
    time.sleep(5)

    f(Path(fr"C:\PythonProjects\auto_inspection_data__{MODEL}\img_full - Copy\o\ng"))
    f(Path(fr"C:\PythonProjects\auto_inspection_data__{MODEL}\img_full - Copy\o\ok"))


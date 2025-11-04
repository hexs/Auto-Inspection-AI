import csv
import json
import os
import math
from typing import Dict, List, Tuple
from itertools import cycle

import matplotlib.pyplot as plt
import numpy as np


def softmax_dict(scores: Dict[str, float], temperature: float = 1.0, base: float = math.e) -> Dict[str, float]:
    if temperature <= 0:
        raise ValueError("temperature must be > 0")
    if not scores:
        return {}
    scaled = {k: (v / temperature) for k, v in scores.items()}
    m = max(scaled.values())
    exps = {k: (base ** (v - m)) for k, v in scaled.items()}
    Z = sum(exps.values())
    return {k: exps[k] / Z for k in scores.keys()}


def load_frames_data(file_path: str) -> dict:
    if not os.path.exists(file_path):
        print(f"[Error] Missing: {file_path}")
        return {}
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"[Error] JSON parse failed: {file_path} ({e})")
        return {}


def read_results(file_path: str) -> List[str]:
    if not os.path.exists(file_path):
        print(f"[Error] Missing: {file_path}")
        return []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.readlines()
    except Exception as e:
        print(f"[Error] reading {file_path}: {e}")
        return []


def process_data(frames_data: dict, results: List[str]) -> Tuple[List[str], List[dict], dict, List[str]]:
    frames_cfg = frames_data.get("frames", {})
    table_rows: List[dict] = []
    plot_series = {comp: [] for comp in frames_cfg.keys()}
    img_names: List[str] = []
    seen_frames = set()

    for raw in results:
        line = raw.strip()
        if not line:
            continue
        try:
            img_name, json_blob = line.split("--", 1)
            img_names.append(img_name)
            row = {"img_name": img_name}

            data = json.loads(json_blob)
            for frame_name, vel_data in data.items():
                seen_frames.add(frame_name)
                if frame_name not in frames_cfg:
                    continue
                ok_case = frames_cfg.get(frame_name, {}).get("res_show", {}).get("OK", [])
                probs = softmax_dict(vel_data, temperature=1.0, base=1.3)
                ok_total = sum(p for case, p in probs.items() if case in ok_case)
                row[frame_name] = ok_total
                plot_series[frame_name].append(ok_total)

            for k in frames_cfg.keys():
                row.setdefault(k, "")
            table_rows.append(row)

        except Exception as e:
            print(f"[Warn] skip line (parse error): {line[:120]}... -> {e}")

    non_empty_keys = [k for k, v in plot_series.items() if any(isinstance(x, (int, float)) and x == x for x in v)]
    non_empty_keys.sort()
    plot_series = {k: plot_series[k] for k in non_empty_keys}
    return non_empty_keys, table_rows, plot_series, img_names


def export_to_csv(file_path: str, frame_names: List[str], table_data: List[dict]) -> None:
    try:
        with open(file_path, "w", newline="", encoding="utf-8") as csvfile:
            fieldnames = ["img_name"] + frame_names
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            for row in table_data:
                out = {}
                for col in fieldnames:
                    v = row.get(col, "")
                    if isinstance(v, float):
                        out[col] = f"{v:.6f}"
                    else:
                        out[col] = v
                writer.writerow(out)
    except Exception as e:
        print(f"[Error] export CSV: {e}")


def _distinct_colors(n: int) -> List[Tuple[float, float, float, float]]:
    """
    - ถ้า n <= 20: ใช้ tab20 ที่แบ่งเป็น n สีชัด ๆ
    - ถ้า n > 20: กระจาย hue เท่า ๆ กันบน HSV -> RGB
    """
    print(n)
    if n <= 20:
        cmap = plt.get_cmap("tab20", n)
        return [cmap(i) for i in range(n)]
    hues = np.linspace(0.0, 1.0, n, endpoint=False)

    def hsv_to_rgb(h, s=0.75, v=0.9):
        i = int(h * 6)
        f = h * 6 - i
        p = v * (1 - s)
        q = v * (1 - f * s)
        t = v * (1 - (1 - f) * s)
        i %= 6
        if i == 0:
            r, g, b = v, t, p
        elif i == 1:
            r, g, b = q, v, p
        elif i == 2:
            r, g, b = p, v, t
        elif i == 3:
            r, g, b = p, q, v
        elif i == 4:
            r, g, b = t, p, v
        else:
            r, g, b = v, p, q
        return (r, g, b, 1.0)

    return [hsv_to_rgb(h) for h in hues]


def _deterministic_color(name: str) -> Tuple[float, float, float, float]:
    h = 0
    for ch in name:
        h = (h * 1315423911 ^ ord(ch)) & 0xFFFFFFFF
    hue = ((h * 0.61803398875) % 1.0)

    def hsv_to_rgb(h, s=0.75, v=0.9):
        i = int(h * 6)
        f = h * 6 - i
        p = v * (1 - s)
        q = v * (1 - f * s)
        t = v * (1 - (1 - f) * s)
        i %= 6
        if i == 0:
            r, g, b = v, t, p
        elif i == 1:
            r, g, b = q, v, p
        elif i == 2:
            r, g, b = p, v, t
        elif i == 3:
            r, g, b = p, q, v
        elif i == 4:
            r, g, b = t, p, v
        else:
            r, g, b = v, p, q
        return (r, g, b, 1.0)

    return hsv_to_rgb(hue)


def load_or_build_color_map(keys: List[str], map_path: str) -> dict:
    cmap = {}
    if os.path.exists(map_path):
        try:
            with open(map_path, "r", encoding="utf-8") as f:
                raw = json.load(f)
                for k, v in raw.items():
                    if isinstance(v, list):
                        cmap[k] = tuple(v)
                    else:
                        cmap[k] = v
        except Exception:
            cmap = {}

    missing = [k for k in keys if k not in cmap]
    if missing:
        print(len(keys))
        if len(keys) <= 50:
            new_colors = _distinct_colors(len(missing))
        else:
            new_colors = [_deterministic_color(k) for k in missing]
        for k, c in zip(missing, new_colors):
            cmap[k] = c
        try:
            with open(map_path, "w", encoding="utf-8") as f:
                json.dump({k: list(v) for k, v in cmap.items()}, f, indent=2)
        except Exception as e:
            print(f"[Warn] cannot save color map: {e}")
    return cmap


def plot_ok_series(series_dict: dict, img_names: List[str], output_plot_file: str, color_map_file: str) -> None:
    plt.figure(figsize=(12, 8))

    keys = list(sorted(series_dict.keys()))
    N = len(keys)
    color_map = load_or_build_color_map(keys, color_map_file)

    marker_cycle = cycle(["o", "s"])
    for k in keys:
        values = series_dict[k]
        if not values:
            continue
        marker = next(marker_cycle)
        try:
            plt.scatter(
                img_names, values,
                label=k,
                color=color_map[k],
                marker=marker,
                s=28,
                linewidths=0.0,
                zorder=2
            )
        except Exception as e:
            print(f"[Warn] plot {k}: {e}")
    plt.axhline(y=0.5, color=(1.0, 0.0, 0.0, 1.0), linestyle="--", zorder=1)

    plt.title("Status Over Time")
    plt.xlabel("Data")
    plt.ylabel("OK value")
    plt.ylim(0, 1)

    max_xticks = 120
    if len(img_names) > max_xticks:
        step = int(np.ceil(len(img_names) / max_xticks))
        plt.xticks(range(0, len(img_names), step), [img_names[i] for i in range(0, len(img_names), step)], rotation=90)
    else:
        plt.xticks(rotation=90)

    plt.legend(
        bbox_to_anchor=(1.02, 1),
        loc="upper left",
        ncol=max(1, int(np.ceil(N / 25))),
        fontsize=8,
        borderaxespad=0.0
    )

    plt.tight_layout()
    plt.savefig(output_plot_file, dpi=150)
    plt.show()


def summary(main_path: str) -> None:
    frames_file = os.path.join(main_path, "frames pos.json")
    results_file = os.path.join(main_path, "img_result", "result.txt")
    output_csv_file = os.path.join(main_path, "img_result.csv")
    output_plot_file = os.path.join(main_path, "img_result_plot.png")
    color_map_file = os.path.join(main_path, "color_map.json")

    frames_data = load_frames_data(frames_file)
    results = read_results(results_file)
    if not frames_data or not results:
        print("[Error] Missing or invalid input files.")
        return

    frame_names, table_rows, series_dict, img_names = process_data(frames_data, results)
    export_to_csv(output_csv_file, frame_names, table_rows)
    plot_ok_series(series_dict, img_names, output_plot_file, color_map_file)


if __name__ == "__main__":
    main_path = r"C:\PythonProjects\auto_inspection_data__QM7-3473"
    summary(main_path)

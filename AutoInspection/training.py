import os
import random
import shutil
import json
import pathlib
from datetime import datetime
from hexss import json_load, json_update
from hexss.constants import *
from hexss.image import controller, crop_img

import cv2
import matplotlib.pyplot as plt
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers, models
from tensorflow.keras.models import Sequential


def save_img(config: dict, model_name: str, frame_dict: dict, paths: dict, resize: tuple = (180, 180)) -> None:
    img_full_path = pathlib.Path(paths['img_full'])
    img_frame_path = pathlib.Path(paths['img_frame'])
    img_frame_log_path = pathlib.Path(paths['img_frame_log'])

    # Remove existing folders for this model, if any
    for base_path in [img_frame_log_path, img_frame_path]:
        folder = base_path / model_name
        if folder.exists():
            shutil.rmtree(folder)

    # Get list of image files
    img_files = sorted({f.stem for f in img_full_path.glob("*") if f.suffix in ['.png', '.json']}, reverse=True)

    for i, file_name in enumerate(img_files):
        print(f'{i + 1}/{len(img_files)} {file_name}')
        json_file = img_full_path / f"{file_name}.json"
        img_file = img_full_path / f"{file_name}.png"
        try:
            frames = json_load(str(json_file))
            img = cv2.imread(str(img_file))
            if img is None:
                print(f"{YELLOW}Warning: Unable to read image {img_file}{END}")
                continue
        except Exception as e:
            print(f"{RED}Error loading {file_name}: {e}{END}")
            continue

        for pos_name, status in frames.items():
            if pos_name not in frame_dict:
                print(f'{pos_name} not in frames')
                continue

            if frame_dict[pos_name]['model_used'] != model_name:
                continue

            print(f'    {model_name} {pos_name} {status}')

            xywh = frame_dict[pos_name]['xywh']

            # Save original cropped image
            img_crop = crop_img(img, xywh, resize=resize)
            log_dir = img_frame_log_path / model_name
            log_dir.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(log_dir / f"{status}_{pos_name}_{file_name}.png"), img_crop)

            # Process and save variations
            variant_dir = img_frame_path / model_name / status
            variant_dir.mkdir(parents=True, exist_ok=True)

            for shift_y in config['shift_values']:
                for shift_x in config['shift_values']:
                    shifted_crop = crop_img(img, xywh, shift=(shift_x, shift_y), resize=resize)
                    for brightness in config['brightness_values']:
                        for contrast in config['contrast_values']:
                            img_variant = controller(shifted_crop, brightness, contrast)
                            output_filename = f"{file_name}_{pos_name}_{status}_{shift_y}_{shift_x}_{brightness}_{contrast}.png"
                            cv2.imwrite(str(variant_dir / output_filename), img_variant)


def create_model(config: dict, model_name: str, img_height: int, img_width: int, batch_size: int, epochs: int,
                 paths: dict) -> None:
    # Use pathlib for cross-platform path handling
    data_dir = pathlib.Path(paths['img_frame']) / model_name

    # delete file if config['max_file']>0
    for class_name in os.listdir(data_dir):
        class_dir = data_dir / class_name
        if len(os.listdir(class_dir)) > config['max_file']:
            files = random.sample(os.listdir(class_dir), len(os.listdir(class_dir)) - config['max_file'])
            for file in files:
                os.remove(class_dir / file)

    # Count images in all subdirectories
    image_count = len(list(data_dir.glob('*/*.png')))
    print(f'image_count = {image_count}')

    train_ds, val_ds = keras.utils.image_dataset_from_directory(
        data_dir,
        validation_split=0.2,
        subset="both",
        seed=123,
        image_size=(img_height, img_width),
        batch_size=batch_size
    )

    class_names = train_ds.class_names
    print('class_names =', class_names)

    # Save class names info to JSON
    model_path = pathlib.Path(paths['model'])
    model_path.mkdir(parents=True, exist_ok=True)
    with open(model_path / f"{model_name}.json", 'w') as file:
        json.dump({"class_names": class_names, "img_size": (img_width, img_height)}, file, indent=4)

    # Visualize a sample of the training data
    plt.figure(figsize=(20, 10))
    for images, labels in train_ds.take(1):
        for i in range(min(32, len(images))):
            ax = plt.subplot(4, 8, i + 1)
            plt.imshow(images[i].numpy().astype("uint8"))
            plt.title(class_names[labels[i]])
            plt.axis("off")
    plt.savefig(str(model_path / f"{model_name}.png"))
    plt.close()

    # Use TensorFlow's AUTOTUNE for data prefetching
    AUTOTUNE = tf.data.AUTOTUNE
    train_ds = train_ds.cache().shuffle(1000).prefetch(buffer_size=AUTOTUNE)
    val_ds = val_ds.cache().prefetch(buffer_size=AUTOTUNE)

    # Build the model
    num_classes = len(class_names)
    data_augmentation = keras.Sequential(
        [
            layers.RandomFlip("horizontal",
                              input_shape=(img_height,
                                           img_width,
                                           3)),
            layers.RandomRotation(0.1),
            layers.RandomZoom(0.1),
        ]
    )

    model = Sequential([
        data_augmentation,
        layers.Rescaling(1. / 255),
        layers.Conv2D(16, 3, padding='same', activation='relu'),
        layers.MaxPooling2D(),
        layers.Conv2D(32, 3, padding='same', activation='relu'),
        layers.MaxPooling2D(),
        layers.Conv2D(64, 3, padding='same', activation='relu'),
        layers.MaxPooling2D(),
        layers.Dropout(0.2),
        layers.Flatten(),
        layers.Dense(128, activation='relu'),
        layers.Dense(num_classes, name="outputs")
    ])

    model.compile(optimizer='adam',
                  loss=tf.keras.losses.SparseCategoricalCrossentropy(from_logits=True),
                  metrics=['accuracy'])
    model.summary()

    history = model.fit(train_ds, validation_data=val_ds, epochs=epochs)

    # Visualize training results
    acc = history.history.get('accuracy', [])
    val_acc = history.history.get('val_accuracy', [])
    loss = history.history.get('loss', [])
    val_loss = history.history.get('val_loss', [])
    epochs_range = range(epochs)
    plt.figure(figsize=(8, 8))
    plt.subplot(1, 2, 1)
    plt.plot(epochs_range, acc, label='Training Accuracy')
    plt.plot(epochs_range, val_acc, label='Validation Accuracy')
    plt.legend(loc='lower right')
    plt.title('Training and Validation Accuracy')
    plt.subplot(1, 2, 2)
    plt.plot(epochs_range, loss, label='Training Loss')
    plt.plot(epochs_range, val_loss, label='Validation Loss')
    plt.legend(loc='upper right')
    plt.title('Training and Validation Loss')
    plt.savefig(str(model_path / f"{model_name}.png"))
    plt.close()

    # Save the trained model
    model.save(str(model_path / f"{model_name}.keras"))
    model.save(str(model_path / f"{model_name}.h5"))

    # Clean up the image frame folder after training
    shutil.rmtree(str(paths['img_frame'] / model_name))


def training_(inspection_name: str, config: dict) -> None:
    projects_directory = pathlib.Path(config['projects_directory'])
    # Create a base directory for the inspection
    inspection_dir = projects_directory / f"auto_inspection_data__{inspection_name}"

    # Define all relevant subdirectories in a dictionary
    paths = {
        'img_full': inspection_dir / "img_full",
        'img_frame': inspection_dir / "img_frame",
        'img_frame_log': inspection_dir / "img_frame_log",
        'model': inspection_dir / "model"
    }
    # Ensure directories exist
    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)

    # List existing trained models (h5 files)
    model_list = [p.stem for p in (paths['model']).glob("*.h5")]
    print(f"\n{CYAN}===========  {inspection_name}  ==========={END}")
    print(f'model.h5 (ที่มี) = {len(model_list)} {model_list}')

    # Load JSON data with frame and model info
    frames_json_path = inspection_dir / 'frames pos.json'
    json_data = json_load(str(frames_json_path))
    frame_dict = json_data['frames']
    model_dict = json_data['models']

    wait_training_path = inspection_dir / 'wait_training.json'
    wait_training_dict = json_load(str(wait_training_path), {})

    for model_name, model in model_dict.items():
        if not wait_training_dict.get(model_name, True):
            print(f'continue {model_name}')
            continue

        print(f"\n{model_name}: {model}")
        t1 = datetime.now()
        print('-------- >>> crop_img <<< ---------')

        save_img(config, model_name, frame_dict, {k: str(v) for k, v in paths.items()})
        t2 = datetime.now()
        print(f'{t2 - t1} เวลาที่ใช้ในการเปลียน img_full เป็น shift_img')
        print('------- >>> training... <<< ---------')
        create_model(config, model_name, config['img_height'], config['img_width'],
                     config['batch_size'], config['epochs'],
                     {k: paths[k] for k in ['img_frame', 'model']})
        json_update(str(wait_training_path), {model_name: False})
        t3 = datetime.now()
        print(f'{t2 - t1} เวลาที่ใช้ในการเปลียน img_full เป็น shift_img')
        print(f'{t3 - t2} เวลาที่ใช้ในการ training')
        print(f'{t3 - t1} เวลาที่ใช้ทั้งหมด\n')


def training(*inspection_names: str, config: dict) -> None:
    for inspection_name in inspection_names:
        training_(inspection_name, config)


if __name__ == '__main__':
    training(
        "QC7-7990-000",
        "QD1-1988-000",
        "POWER-SUPPLY-FIXING-UNIT",
        "POWER-SUPPLY-FIXING-UNIT2",
        config={
            'projects_directory': r'C:\PythonProjects',
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

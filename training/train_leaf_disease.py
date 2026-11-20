"""
Train a generalized leaf disease classifier that can cover any number of plants.

Each dataset directory must contain one folder per class named "Plant___Disease"
(PlantVillage convention), e.g. "Tomato___Early_blight", "Rice___Brown_spot", "Wheat___healthy".
Pass several directories to merge datasets; classes with the same folder name are combined.
To support a new crop, add its folders and retrain - no code changes are needed, because the
API reads the class list from models/leaf_disease_labels.json.

Suggested public datasets (all use or easily rename to the Plant___Disease layout):
  - PlantVillage / New Plant Diseases (38 classes, 14 crops)  kaggle: vipoooool/new-plant-diseases-dataset
  - PlantDoc (real field photos, 27 classes)                  github: pratikkayal/PlantDoc-Dataset
  - Rice leaf diseases, Wheat leaf diseases, Cotton, Sugarcane, Mango, Banana datasets on Kaggle

Improvements over the original notebook model (frozen VGG16, 150px, 650 images/class, 5 epochs):
  - EfficientNetV2-B0 backbone, 224px, all images used
  - Strong augmentation so it generalizes from lab images to field photos
  - Two-phase training: train the head, then fine-tune the top of the backbone
  - Class weights for imbalanced classes, label smoothing, early stopping
  - Writes the label file + preprocessing info the Flask API uses

The model is saved to models/candidates/<run-name>/, never over the model the app is using.
Evaluate it with training/evaluate_leaf_disease.py, then copy it into models/ with
training/promote_leaf_model.py.

Usage (dataset built by training/build_leaf_dataset.py):
  python training/train_leaf_disease.py --run-name combined \
      --data-dirs data/combined/train/* --val-dirs data/combined/val/*
  python training/train_leaf_disease.py --run-name plantvillage_only \
      --data-dirs data/combined/train/plantvillage --val-dirs data/combined/val/plantvillage
"""
import os
import json
import argparse
import numpy as np
import tensorflow as tf
import keras
from keras import layers

IMG_EXTS = ('.jpg', '.jpeg', '.png', '.webp', '.bmp')
AUTOTUNE = tf.data.AUTOTUNE


def list_images(dirs):
    paths, labels = [], []
    for d in dirs:
        for cls in sorted(os.listdir(d)):
            cdir = os.path.join(d, cls)
            if not os.path.isdir(cdir) or '___' not in cls:
                continue
            for f in os.listdir(cdir):
                if f.lower().endswith(IMG_EXTS):
                    paths.append(os.path.join(cdir, f))
                    labels.append(cls)
    return paths, labels


def make_dataset(paths, label_ids, img_size, batch, training):
    def load(path, label):
        img = tf.io.decode_image(tf.io.read_file(path), channels=3, expand_animations=False)
        img = tf.image.resize(img, (img_size, img_size))
        return img, label

    ds = tf.data.Dataset.from_tensor_slices((paths, label_ids))
    if training:
        ds = ds.shuffle(len(paths), reshuffle_each_iteration=True)
    return ds.map(load, num_parallel_calls=AUTOTUNE).batch(batch).prefetch(AUTOTUNE)


def build_model(num_classes, img_size):
    augment = keras.Sequential([
        layers.RandomFlip('horizontal_and_vertical'),
        layers.RandomRotation(0.2),
        layers.RandomZoom(0.2),
        layers.RandomTranslation(0.1, 0.1),
        layers.RandomContrast(0.3),
        layers.RandomBrightness(0.3, value_range=(0, 255)),
    ], name='augmentation')

    # EfficientNetV2 has preprocessing built in and expects raw 0-255 pixels
    base = keras.applications.EfficientNetV2B0(include_top=False, weights='imagenet',
                                               input_shape=(img_size, img_size, 3))
    base.trainable = False

    inputs = keras.Input((img_size, img_size, 3))
    x = augment(inputs)
    x = base(x, training=False)
    x = layers.GlobalAveragePooling2D()(x)
    x = layers.BatchNormalization()(x)
    x = layers.Dropout(0.4)(x)
    outputs = layers.Dense(num_classes, activation='softmax', dtype='float32')(x)
    return keras.Model(inputs, outputs), base


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--data-dirs', nargs='+', required=True, help='Training dirs with Plant___Disease folders')
    ap.add_argument('--val-dirs', nargs='*', default=[], help='Validation dirs; if omitted, 15%% of training is held out')
    ap.add_argument('--img-size', type=int, default=224)
    ap.add_argument('--batch', type=int, default=32)
    ap.add_argument('--epochs', type=int, default=10)
    ap.add_argument('--fine-tune-epochs', type=int, default=10)
    ap.add_argument('--fine-tune-layers', type=int, default=60, help='How many top backbone layers to unfreeze')
    ap.add_argument('--run-name', default='latest', help='Saved to models/candidates/<run-name>')
    ap.add_argument('--out-dir', default=None, help='Override the output folder')
    args = ap.parse_args()
    args.out_dir = args.out_dir or os.path.join('models', 'candidates', args.run_name)
    if os.path.abspath(args.out_dir) == os.path.abspath('models'):
        raise SystemExit('Refusing to write into models/ directly; the app loads from there. '
                         'Train into a candidate folder and use training/promote_leaf_model.py.')

    paths, labels = list_images(args.data_dirs)
    if args.val_dirs:
        val_paths, val_labels = list_images(args.val_dirs)
    else:
        rng = np.random.default_rng(42)
        idx = rng.permutation(len(paths))
        n_val = int(0.15 * len(paths))
        val_paths = [paths[i] for i in idx[:n_val]]
        val_labels = [labels[i] for i in idx[:n_val]]
        paths = [paths[i] for i in idx[n_val:]]
        labels = [labels[i] for i in idx[n_val:]]

    classes = sorted(set(labels))
    class_to_id = {c: i for i, c in enumerate(classes)}
    y = np.array([class_to_id[l] for l in labels])
    keep = [i for i, l in enumerate(val_labels) if l in class_to_id]
    val_paths = [val_paths[i] for i in keep]
    val_y = np.array([class_to_id[val_labels[i]] for i in keep])

    plants = sorted({c.split('___')[0] for c in classes})
    print(f'{len(paths)} train / {len(val_paths)} val images, {len(classes)} classes, {len(plants)} plants')

    counts = np.bincount(y, minlength=len(classes))
    class_weight = {i: len(y) / (len(classes) * max(c, 1)) for i, c in enumerate(counts)}

    train_ds = make_dataset(paths, y, args.img_size, args.batch, training=True)
    val_ds = make_dataset(val_paths, val_y, args.img_size, args.batch, training=False)

    model, base = build_model(len(classes), args.img_size)
    loss = keras.losses.CategoricalCrossentropy(label_smoothing=0.1)
    to_onehot = lambda x, t: (x, tf.one_hot(t, len(classes)))
    train_ds, val_ds = train_ds.map(to_onehot), val_ds.map(to_onehot)

    os.makedirs(args.out_dir, exist_ok=True)
    model_path = os.path.join(args.out_dir, 'leaf_disease_model.keras')
    callbacks = [
        keras.callbacks.EarlyStopping(monitor='val_accuracy', patience=3, restore_best_weights=True),
        keras.callbacks.ReduceLROnPlateau(monitor='val_loss', factor=0.3, patience=2),
    ]

    print('Phase 1: training classification head')
    model.compile(optimizer=keras.optimizers.Adam(1e-3), loss=loss, metrics=['accuracy'])
    model.fit(train_ds, validation_data=val_ds, epochs=args.epochs,
              class_weight=class_weight, callbacks=callbacks)

    print('Phase 2: fine-tuning top of backbone')
    base.trainable = True
    for layer in base.layers[:-args.fine_tune_layers]:
        layer.trainable = False
    for layer in base.layers:
        if isinstance(layer, layers.BatchNormalization):
            layer.trainable = False
    model.compile(optimizer=keras.optimizers.Adam(1e-5), loss=loss, metrics=['accuracy'])
    model.fit(train_ds, validation_data=val_ds, epochs=args.fine_tune_epochs,
              class_weight=class_weight, callbacks=callbacks)

    _, acc = model.evaluate(val_ds, verbose=0)
    print(f'Validation accuracy: {acc:.4f}')

    model.save(model_path)
    with open(os.path.join(args.out_dir, 'leaf_disease_labels.json'), 'w') as f:
        json.dump({'classes': classes, 'plants': plants, 'img_size': args.img_size,
                   'scale': 1.0, 'val_accuracy': round(float(acc), 4),
                   'train_dirs': args.data_dirs, 'val_dirs': args.val_dirs,
                   'train_images': len(paths)}, f, indent=2)
    print(f'Saved {model_path} and leaf_disease_labels.json')


if __name__ == '__main__':
    main()

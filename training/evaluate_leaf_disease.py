"""
Cross-domain evaluation: compare leaf disease models on lab images vs real field photos.

Each model is evaluated the way the Flask app runs it (same OpenCV preprocessing), and scored both
  - open:              the model picks from all of its classes
  - plant-conditioned: only the true plant's classes compete, as in the app when the farmer
                       types the plant name
Only test images whose class the model knows are counted; coverage shows how many that is. When
several models are given, a second table scores all of them on the classes they all share, so
the comparison is fair.

Models: "legacy" (models/leaf_disease_model.h5, the original model) or a folder containing
leaf_disease_model.keras + leaf_disease_labels.json (e.g. models/candidates/combined).
Test sets: name=glob, each glob matching folders that contain class folders.

Usage:
  python training/evaluate_leaf_disease.py \
      --models legacy models/candidates/plantvillage_only models/candidates/combined \
      --test "lab=data/combined/test_lab/*" "field=data/combined/test_field/*" \
      --test "own_photos=data/combined/test_field/own_photos"
"""
import os
import sys
import glob
import json
import argparse
from collections import Counter, defaultdict
from datetime import datetime

import cv2
import numpy as np
from sklearn.metrics import f1_score

sys.path.insert(0, os.getcwd())
IMG_EXTS = ('.jpg', '.jpeg', '.png', '.webp', '.bmp')


def display_name(cls):
    """How the app shows a "Plant___Disease" class: "Tomato___Late_blight" -> "Tomato Late blight"."""
    return cls.replace('___', ' ').replace('_', ' ').strip()


def key(name):
    return ' '.join(name.lower().split())


def load_model(spec):
    import keras
    if spec == 'legacy':
        from backend.routes.disease import DISEASE_CLASSES, LEGACY_PLANTS, LEGACY_MODEL_PATH
        plants = [next(p for p in LEGACY_PLANTS if c.startswith(p)) for c in DISEASE_CLASSES]
        return {'name': 'legacy', 'dir': None, 'model': keras.models.load_model(LEGACY_MODEL_PATH),
                'classes': list(DISEASE_CLASSES), 'plants': plants, 'img_size': 150, 'scale': 1 / 255.0}
    with open(os.path.join(spec, 'leaf_disease_labels.json')) as f:
        meta = json.load(f)
    return {'name': os.path.basename(os.path.normpath(spec)), 'dir': spec,
            'model': keras.models.load_model(os.path.join(spec, 'leaf_disease_model.keras')),
            'classes': [display_name(c) for c in meta['classes']],
            'plants': [c.split('___')[0].replace('_', ' ').strip() for c in meta['classes']],
            'img_size': meta.get('img_size', 224), 'scale': meta.get('scale', 1.0)}


def list_test_images(pattern):
    items = []
    for root in sorted(glob.glob(pattern)):
        if not os.path.isdir(root):
            continue
        for cls in sorted(os.listdir(root)):
            cdir = os.path.join(root, cls)
            if os.path.isdir(cdir) and '___' in cls:
                items += [(os.path.join(cdir, f), cls) for f in sorted(os.listdir(cdir))
                          if f.lower().endswith(IMG_EXTS)]
    return items


def predict(m, paths, batch=64):
    """Probabilities for each image, preprocessed exactly like backend/routes/disease.py."""
    size, out, ok = m['img_size'], [], []
    for i in range(0, len(paths), batch):
        imgs = []
        for p in paths[i:i + batch]:
            img = cv2.imread(p)
            ok.append(img is not None)
            if img is not None:
                img = cv2.resize(cv2.cvtColor(img, cv2.COLOR_BGR2RGB), (size, size)).astype('float32')
                imgs.append(img * m['scale'])
        if imgs:
            out.append(m['model'].predict(np.stack(imgs), verbose=0))
    return (np.concatenate(out) if out else np.zeros((0, len(m['classes'])))), np.array(ok, dtype=bool)


def score(m, items, probs, allowed=None):
    """Metrics on the images whose class the model knows (and, if given, is in allowed)."""
    idx = {key(c): i for i, c in enumerate(m['classes'])}
    plants = np.array(m['plants'])
    rows = [(i, idx[key(display_name(c))]) for i, (_, c) in enumerate(items)
            if key(display_name(c)) in idx and (allowed is None or key(display_name(c)) in allowed)]
    if not rows:
        return None
    sel, y = np.array([r[0] for r in rows]), np.array([r[1] for r in rows])
    p = probs[sel]
    pred = p.argmax(1)
    top3 = (np.argsort(-p, 1)[:, :3] == y[:, None]).any(1)
    # Plant-conditioned: zero out other plants' classes, as the app does when the plant is given
    masked = np.where(plants[None, :] == plants[y][:, None], p, 0.0)
    pred_cond = masked.argmax(1)

    per_class, confusions = {}, Counter()
    for c in np.unique(y):
        per_class[m['classes'][c]] = {'n': int((y == c).sum()), 'accuracy': round(float((pred[y == c] == c).mean()), 4)}
    for t, q in zip(y, pred):
        if t != q:
            confusions[(m['classes'][t], m['classes'][q])] += 1
    return {
        'n': len(y),
        'accuracy': round(float((pred == y).mean()), 4),
        'top3_accuracy': round(float(top3.mean()), 4),
        'plant_conditioned_accuracy': round(float((pred_cond == y).mean()), 4),
        'macro_f1': round(float(f1_score(y, pred, average='macro', labels=np.unique(y))), 4),
        'per_class': per_class,
        'top_confusions': [{'true': t, 'predicted': q, 'count': n} for (t, q), n in confusions.most_common(10)],
    }


def table(title, results, test_names, models, n_test):
    lines = [f'### {title}', '',
             '| Model | ' + ' | '.join(f'{t} acc | {t} plant-cond acc | {t} macro-F1 | {t} coverage' for t in test_names) + ' |',
             '|---|' + '---|' * (4 * len(test_names))]
    for m in models:
        cells = []
        for t in test_names:
            r = results.get((m, t))
            cells += ([f'{r["accuracy"]:.1%}', f'{r["plant_conditioned_accuracy"]:.1%}', f'{r["macro_f1"]:.3f}',
                       f'{r["n"]}/{n_test[t]}'] if r else ['-', '-', '-', f'0/{n_test[t]}'])
        lines.append(f'| {m} | ' + ' | '.join(cells) + ' |')
    return lines


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--models', nargs='+', required=True, help='"legacy" and/or candidate model folders')
    ap.add_argument('--test', nargs='+', action='extend', required=True, help='name=glob of test folders')
    ap.add_argument('--out', default='training/results')
    args = ap.parse_args()

    tests = {}
    for spec in args.test:
        name, _, pattern = spec.partition('=')
        tests[name] = list_test_images(pattern)
        print(f'Test set {name}: {len(tests[name])} images')
        if not tests[name]:
            raise SystemExit(f'No images found for {spec}')

    results, raw, summary, all_models = {}, {}, {}, []
    for spec in args.models:
        m = load_model(spec)
        all_models.append(m)
        for t, items in tests.items():
            probs, ok = predict(m, [p for p, _ in items])
            good = [it for it, k in zip(items, ok) if k]
            raw[(m['name'], t)] = (good, probs)
            r = score(m, good, probs)
            results[(m['name'], t)] = r
            if r:
                summary[f'{m["name"]}/{t}'] = {k: r[k] for k in ('n', 'accuracy', 'plant_conditioned_accuracy', 'macro_f1')}
                print(f'{m["name"]:25s} {t:12s} acc {r["accuracy"]:.1%}  plant-cond {r["plant_conditioned_accuracy"]:.1%}  '
                      f'macro-F1 {r["macro_f1"]:.3f}  (n={r["n"]})')

    names = [m['name'] for m in all_models]
    n_test = {t: len(v) for t, v in tests.items()}
    lines = [f'# Leaf disease evaluation ({datetime.now():%Y-%m-%d %H:%M})', '']
    lines += table('Each model on the classes it knows', results, list(tests), names, n_test)

    if len(all_models) > 1:
        common = set.intersection(*[{key(c) for c in m['classes']} for m in all_models])
        fair = {}
        for m in all_models:
            for t in tests:
                good, probs = raw[(m['name'], t)]
                fair[(m['name'], t)] = score(m, good, probs, allowed=common)
        lines += ['', f'{len(common)} classes are shared by all models.', '']
        lines += table('All models on the shared classes (fair comparison)', fair, list(tests), names, n_test)
        summary['shared_classes'] = {f'{m}/{t}': {'n': r['n'], 'accuracy': r['accuracy'],
                                                  'plant_conditioned_accuracy': r['plant_conditioned_accuracy']}
                                     for (m, t), r in fair.items() if r}

    for (m, t), r in results.items():
        if r and r['top_confusions']:
            lines += ['', f'#### {m} on {t}: most common mistakes', '']
            lines += [f'- {c["true"]} -> {c["predicted"]} ({c["count"]})' for c in r['top_confusions'][:5]]

    os.makedirs(args.out, exist_ok=True)
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report = os.path.join(args.out, f'eval_{stamp}.md')
    with open(report, 'w') as f:
        f.write('\n'.join(lines) + '\n')
    with open(os.path.join(args.out, f'eval_{stamp}.json'), 'w') as f:
        json.dump({'summary': summary, 'details': {f'{m}/{t}': r for (m, t), r in results.items()}}, f, indent=2)
    # Each candidate keeps its own results, which promote_leaf_model.py prints before promoting
    for m in all_models:
        if m['dir']:
            with open(os.path.join(m['dir'], 'eval.json'), 'w') as f:
                json.dump({'summary': {t: summary.get(f'{m["name"]}/{t}') for t in tests},
                           'details': {t: results[(m['name'], t)] for t in tests}}, f, indent=2)
    print('\n'.join(lines[:6 + len(names)]))
    print(f'Wrote {report}')


if __name__ == '__main__':
    main()

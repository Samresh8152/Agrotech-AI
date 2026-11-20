"""
Safely put a trained candidate model into models/, where the Flask app loads it from.

Before copying it checks that the candidate loads, that its output size matches its label file, and
that it gives a valid prediction on a test input. The model currently in use is moved to
models/backup/<timestamp>/ first, so it can always be restored.

models/leaf_disease_model.h5 (the original model) is never modified. When no
leaf_disease_model.keras is present the app falls back to it, so --rollback with no backup left
returns the app to exactly how it was before any retraining.

Restart the Flask app after promoting or rolling back; it loads the model once at startup.

Usage:
  python training/promote_leaf_model.py models/candidates/combined
  python training/promote_leaf_model.py --rollback
"""
import os
import sys
import json
import shutil
import argparse
from datetime import datetime

import numpy as np

MODELS_DIR = 'models'
BACKUP_DIR = os.path.join(MODELS_DIR, 'backup')
FILES = ['leaf_disease_model.keras', 'leaf_disease_labels.json']


def check_candidate(cand):
    for f in FILES:
        if not os.path.exists(os.path.join(cand, f)):
            raise SystemExit(f'Missing {f} in {cand}')
    with open(os.path.join(cand, 'leaf_disease_labels.json')) as f:
        meta = json.load(f)
    classes = meta.get('classes') or []
    bad = [c for c in classes if '___' not in c]
    if not classes or bad:
        raise SystemExit(f'Label file must list "Plant___Disease" classes; bad entries: {bad[:5]}')

    import keras
    model = keras.models.load_model(os.path.join(cand, 'leaf_disease_model.keras'))
    size = meta.get('img_size', 224)
    x = np.random.default_rng(0).uniform(0, 255, (1, size, size, 3)).astype('float32') * meta.get('scale', 1.0)
    probs = model.predict(x, verbose=0)[0]
    if probs.shape[0] != len(classes):
        raise SystemExit(f'Model outputs {probs.shape[0]} classes but the label file lists {len(classes)}')
    if not np.isfinite(probs).all() or abs(probs.sum() - 1) > 1e-3:
        raise SystemExit('Model output is not a valid probability distribution')
    print(f'OK: {len(classes)} classes, {len({c.split("___")[0] for c in classes})} plants, '
          f'val accuracy {meta.get("val_accuracy")}')

    # Classes without a description fall back to generic advice in the app; list them
    try:
        sys.path.insert(0, os.getcwd())
        from backend.routes.disease import DISEASE_INFO
        missing = [c for c in classes if 'healthy' not in c.lower()
                   and c.replace('___', ' ').replace('_', ' ').strip() not in DISEASE_INFO]
        if missing:
            print(f'Note: no DISEASE_INFO entry (generic advice shown) for: {", ".join(missing)}')
    except Exception as e:
        print(f'(Skipped DISEASE_INFO check: {e})')

    eval_path = os.path.join(cand, 'eval.json')
    if os.path.exists(eval_path):
        with open(eval_path) as f:
            print('Evaluation:', json.dumps(json.load(f).get('summary', {}), indent=2))
    else:
        print('Warning: no eval.json; run training/evaluate_leaf_disease.py before promoting.')


def backup_current(prefix=''):
    present = [f for f in FILES if os.path.exists(os.path.join(MODELS_DIR, f))]
    if not present:
        return None
    dest = os.path.join(BACKUP_DIR, prefix + datetime.now().strftime('%Y%m%d_%H%M%S'))
    os.makedirs(dest)
    for f in present:
        shutil.move(os.path.join(MODELS_DIR, f), os.path.join(dest, f))
    return dest


def promote(cand, yes):
    check_candidate(cand)
    if not yes and input(f'Replace the model the app uses with {cand}? [y/N] ').strip().lower() != 'y':
        print('Cancelled; nothing changed.')
        return
    backup = backup_current()
    # Copy the label file last: the app only switches when both files exist
    for f in FILES:
        shutil.copy2(os.path.join(cand, f), os.path.join(MODELS_DIR, f))
    print(f'Promoted {cand}.' + (f' Previous model saved in {backup}.' if backup else ''))
    print('Restart the Flask app to load it.')


def rollback():
    # Models that were rolled back are kept but never restored automatically
    backups = sorted(b for b in os.listdir(BACKUP_DIR) if not b.startswith('rolled_back_')) \
        if os.path.isdir(BACKUP_DIR) else []
    # Move the current model aside rather than deleting it
    current = backup_current(prefix='rolled_back_')
    if current:
        print(f'Moved the current model to {current}')
    if backups:
        src = os.path.join(BACKUP_DIR, backups[-1])
        for f in FILES:
            if os.path.exists(os.path.join(src, f)):
                shutil.move(os.path.join(src, f), os.path.join(MODELS_DIR, f))
        if not os.listdir(src):
            os.rmdir(src)
        print(f'Restored the model from {src}')
    else:
        print('No earlier retrained model; the app will use the original leaf_disease_model.h5.')
    print('Restart the Flask app to load it.')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('candidate', nargs='?', help='Folder with leaf_disease_model.keras + leaf_disease_labels.json')
    ap.add_argument('--rollback', action='store_true', help='Restore the previous model')
    ap.add_argument('--check-only', action='store_true', help='Run the checks without copying')
    ap.add_argument('--yes', action='store_true', help='Do not ask for confirmation')
    args = ap.parse_args()
    if args.rollback:
        rollback()
    elif not args.candidate:
        ap.error('give a candidate folder or --rollback')
    elif args.check_only:
        check_candidate(args.candidate)
    else:
        promote(args.candidate, args.yes)


if __name__ == '__main__':
    main()

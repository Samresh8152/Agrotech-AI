"""
Combine several leaf disease datasets into one dataset with harmonized labels.

Steps:
  1. Read each source listed in a JSON config (PlantVillage, PlantDoc, Indian crop sets, own photos)
  2. Map every class folder to one canonical "Plant___Disease" name (training/label_map.py)
  3. Find duplicate images across all sources with a perceptual hash (dHash), so the same photo can
     never end up in both train and test; drop duplicates whose labels disagree
  4. Split per source and class into train / val / test_lab / test_field
  5. Write the dataset (symlinks by default) plus manifest.csv and report.md for the project report

Output layout, one folder per source so experiments can pick sources:
  <out>/train/<source>/<Plant___Disease>/<image>
  <out>/val/<source>/...
  <out>/test_lab/<source>/...     held out from lab sources (PlantVillage)
  <out>/test_field/<source>/...   held out from field sources (PlantDoc, own photos)

Source roles in the config:
  lab         -> train / val / test_lab        (80 / 10 / 10)
  field       -> train / val / test_field      (70 / 10 / 20)
  field_test  -> test_field only               (e.g. PlantDoc's own test split, your own photos)

This script only writes inside --out. It does not touch models/ or the running app.

Usage:
  python training/build_leaf_dataset.py --config training/leaf_sources.json --out data/combined
  python training/build_leaf_dataset.py --config training/leaf_sources.json --out data/combined --dry-run
"""
import os
import csv
import json
import shutil
import argparse
from collections import defaultdict, Counter
from concurrent.futures import ThreadPoolExecutor

import numpy as np
from PIL import Image

from label_map import canonical_class

IMG_EXTS = ('.jpg', '.jpeg', '.png', '.webp', '.bmp')
SPLIT_FRACTIONS = {  # role -> (val, test)
    'lab': (0.10, 0.10),
    'field': (0.10, 0.20),
    'field_test': (0.0, 1.0),
}
TEST_SPLIT = {'lab': 'test_lab', 'field': 'test_field', 'field_test': 'test_field'}
MANIFEST = 'manifest.csv'


def dhash(path, size=8):
    """64-bit difference hash; unchanged by resizing and re-compression. None if unreadable."""
    try:
        with Image.open(path) as im:
            im.draft('L', (64, 64))  # decode large JPEGs at reduced size; much faster, same hash
            g = np.asarray(im.convert('L').resize((size + 1, size), Image.LANCZOS), dtype=np.int16)
        bits = (g[:, 1:] > g[:, :-1]).flatten()
        return f'{int("".join("1" if b else "0" for b in bits), 2):016x}'
    except Exception:
        return None


def scan_sources(cfg, seed=42):
    """Every image in every source with its canonical label; plus folders that could not be mapped.

    A source's optional "max_per_class" randomly samples that many images per folder, to balance
    large lab sets against small field sets and keep training time reasonable.
    """
    items, unmapped = [], defaultdict(list)
    mapping = cfg.get('mapping', {})
    rng = np.random.default_rng(seed)
    for src in cfg['sources']:
        name, root, role = src['name'], src['path'], src.get('role', 'lab')
        if role not in SPLIT_FRACTIONS:
            raise SystemExit(f'Source "{name}": unknown role "{role}" (use lab, field or field_test)')
        if not os.path.isdir(root):
            raise SystemExit(f'Source "{name}": folder not found: {root}')
        for folder in sorted(os.listdir(root)):
            fdir = os.path.join(root, folder)
            if not os.path.isdir(fdir):
                continue
            cls = canonical_class(folder, plant=src.get('plant'), extra_mapping=mapping)
            files = [f for f in sorted(os.listdir(fdir)) if f.lower().endswith(IMG_EXTS)]
            if cls is None:
                unmapped[name].append((folder, len(files)))
                continue
            cap = src.get('max_per_class')
            if cap and len(files) > cap:
                files = sorted(rng.choice(files, cap, replace=False))
            for f in files:
                items.append({'source': name, 'role': role, 'folder': folder, 'class': cls,
                              'path': os.path.abspath(os.path.join(fdir, f))})
    return items, unmapped


def dedupe(items):
    """Group identical images; keep one per group, drop groups with conflicting labels."""
    groups = defaultdict(list)
    for it in items:
        groups[it['hash']].append(it)
    kept, dup_count, conflicts = [], 0, []
    role_rank = {'field_test': 0, 'field': 1, 'lab': 2}
    for h, members in groups.items():
        labels = {m['class'] for m in members}
        if len(labels) > 1:
            conflicts.append({'hash': h, 'labels': sorted(labels),
                              'files': [f"{m['source']}/{m['folder']}/{os.path.basename(m['path'])}" for m in members]})
            continue
        # A copy in a test-only source wins, so the real-world test set never loses an image
        members.sort(key=lambda m: role_rank[m['role']])
        kept.append(members[0])
        dup_count += len(members) - 1
    return kept, dup_count, conflicts


def assign_splits(items, seed):
    rng = np.random.default_rng(seed)
    by_key = defaultdict(list)
    for it in items:
        by_key[(it['source'], it['class'])].append(it)
    for (_, _), group in sorted(by_key.items()):
        role = group[0]['role']
        val_frac, test_frac = SPLIT_FRACTIONS[role]
        order = rng.permutation(len(group))
        n = len(group)
        if role == 'field_test':
            n_test, n_val = n, 0
        else:
            n_test = int(round(n * test_frac))
            n_val = int(round(n * val_frac))
            # Always leave at least one training image
            while n_test + n_val >= n and (n_test or n_val):
                if n_val:
                    n_val -= 1
                else:
                    n_test -= 1
        for rank, i in enumerate(order):
            if rank < n_test:
                group[i]['split'] = TEST_SPLIT[role]
            elif rank < n_test + n_val:
                group[i]['split'] = 'val'
            else:
                group[i]['split'] = 'train'


def prepare_out_dir(out, overwrite):
    if os.path.exists(out) and os.listdir(out):
        if not overwrite:
            raise SystemExit(f'{out} is not empty. Pass --overwrite to rebuild it.')
        # Only delete folders this script created, never an arbitrary directory
        if not os.path.exists(os.path.join(out, MANIFEST)):
            raise SystemExit(f'{out} has no {MANIFEST}; refusing to delete a folder this script did not create.')
        shutil.rmtree(out)
    os.makedirs(out, exist_ok=True)


def write_dataset(items, out, copy):
    for it in items:
        safe_folder = it['folder'].replace(' ', '_').replace('/', '_')
        dest_dir = os.path.join(out, it['split'], it['source'], it['class'])
        os.makedirs(dest_dir, exist_ok=True)
        dest = os.path.join(dest_dir, f"{safe_folder}__{os.path.basename(it['path'])}")
        it['dest'] = os.path.relpath(dest, out)
        if copy:
            shutil.copy2(it['path'], dest)
        else:
            os.symlink(it['path'], dest)


def write_report(out, items, all_count, unreadable, dup_count, conflicts, unmapped, min_train):
    splits = ['train', 'val', 'test_lab', 'test_field']
    per_class = defaultdict(Counter)
    per_source = defaultdict(Counter)
    for it in items:
        per_class[it['class']][it['split']] += 1
        per_source[it['source']][it['split']] += 1

    lines = ['# Combined leaf disease dataset', '',
             f'- Images found: {all_count}',
             f'- Unreadable images skipped: {len(unreadable)}',
             f'- Duplicate images removed: {dup_count}',
             f'- Duplicate groups dropped for conflicting labels: {len(conflicts)}',
             f'- Images in the final dataset: {len(items)}',
             f'- Classes: {len(per_class)}, plants: {len({c.split("___")[0] for c in per_class})}', '',
             '## Images per source', '',
             '| Source | ' + ' | '.join(splits) + ' | Total |',
             '|---|' + '---|' * (len(splits) + 1)]
    for src, c in sorted(per_source.items()):
        lines.append(f'| {src} | ' + ' | '.join(str(c[s]) for s in splits) + f' | {sum(c.values())} |')

    lines += ['', '## Images per class', '',
              '| Class | ' + ' | '.join(splits) + ' |',
              '|---|' + '---|' * len(splits)]
    low = []
    for cls, c in sorted(per_class.items()):
        lines.append(f'| {cls} | ' + ' | '.join(str(c[s]) for s in splits) + ' |')
        if c['train'] < min_train:
            low.append(f'{cls} ({c["train"]})')
    if low:
        lines += ['', f'## Classes with fewer than {min_train} training images', '', ', '.join(low)]
    if unmapped:
        lines += ['', '## Folders skipped (no label mapping)', '',
                  'Add them to "mapping" in the config (value null keeps skipping), see mapping_template.json.', '']
        for src, folders in unmapped.items():
            lines += [f'- **{src}**: ' + ', '.join(f'{f} ({n})' for f, n in folders)]
    with open(os.path.join(out, 'report.md'), 'w') as f:
        f.write('\n'.join(lines) + '\n')

    with open(os.path.join(out, 'report.json'), 'w') as f:
        json.dump({'images_found': all_count, 'unreadable': unreadable, 'duplicates_removed': dup_count,
                   'label_conflicts': conflicts, 'final_images': len(items),
                   'per_class': {k: dict(v) for k, v in per_class.items()},
                   'per_source': {k: dict(v) for k, v in per_source.items()},
                   'unmapped': {k: [f for f, _ in v] for k, v in unmapped.items()}}, f, indent=2)
    if unmapped:
        template = {f: None for folders in unmapped.values() for f, _ in folders}
        with open(os.path.join(out, 'mapping_template.json'), 'w') as f:
            json.dump(template, f, indent=2)
    return '\n'.join(lines[:8])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--config', required=True, help='JSON file listing the sources (see leaf_sources.example.json)')
    ap.add_argument('--out', default='data/combined')
    ap.add_argument('--copy', action='store_true', help='Copy images instead of symlinking them')
    ap.add_argument('--overwrite', action='store_true', help='Rebuild --out if it was made by this script')
    ap.add_argument('--dry-run', action='store_true', help='Only print the label mapping and counts')
    ap.add_argument('--seed', type=int, default=42)
    ap.add_argument('--min-train', type=int, default=30, help='Warn about classes with fewer training images')
    ap.add_argument('--workers', type=int, default=os.cpu_count())
    args = ap.parse_args()

    with open(args.config) as f:
        cfg = json.load(f)
    items, unmapped = scan_sources(cfg, args.seed)
    print(f'Found {len(items)} images in {len(cfg["sources"])} sources')
    if not args.dry_run:
        prepare_out_dir(args.out, args.overwrite)

    if args.dry_run:
        mapping = defaultdict(set)
        for it in items:
            mapping[(it['source'], it['folder'])].add(it['class'])
        for (src, folder), cls in sorted(mapping.items()):
            print(f'  {src:20s} {folder:55s} -> {", ".join(cls)}')
        for src, folders in unmapped.items():
            for folder, n in folders:
                print(f'  {src:20s} {folder:55s} -> SKIPPED (no mapping, {n} images)')
        return

    print('Hashing images to find duplicates...')
    # Threads, not processes: PIL releases the GIL while decoding, and there is no spawn overhead
    hashes = []
    with ThreadPoolExecutor(args.workers) as pool:
        for i, h in enumerate(pool.map(dhash, [it['path'] for it in items]), 1):
            hashes.append(h)
            if i % 5000 == 0:
                print(f'  {i}/{len(items)}', flush=True)
    unreadable = [it['path'] for it, h in zip(items, hashes) if h is None]
    for it, h in zip(items, hashes):
        it['hash'] = h
    all_count = len(items)
    items = [it for it in items if it['hash']]

    items, dup_count, conflicts = dedupe(items)
    assign_splits(items, args.seed)
    write_dataset(items, args.out, args.copy)
    with open(os.path.join(args.out, MANIFEST), 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['dest', 'split', 'source', 'role', 'folder', 'class', 'hash', 'path'])
        w.writeheader()
        for it in sorted(items, key=lambda x: x['dest']):
            w.writerow({k: it[k] for k in w.fieldnames})
    summary = write_report(args.out, items, all_count, unreadable, dup_count, conflicts, unmapped, args.min_train)
    print(summary)
    print(f'Wrote {args.out} (see report.md and manifest.csv)')


if __name__ == '__main__':
    main()

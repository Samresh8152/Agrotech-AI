# Combined leaf disease dataset

The pipeline merges PlantVillage (lab photos), PlantDoc (field photos), Indian-crop datasets and
your own photos into one dataset with harmonized labels. It then measures how well each model
works on real field photos.

The running app is never affected. Training writes to `models/candidates/`, and the app keeps
using its current model until you run `promote_leaf_model.py`.

## 1. Download the datasets into `data/raw/`

| Folder | Source |
|---|---|
| `data/raw/plantvillage` | Already in the repo as `dataset/Plant Diseas` (15 classes), or the full 38-class set from Kaggle |
| `data/raw/PlantDoc-Dataset` | `git clone https://github.com/pratikkayal/PlantDoc-Dataset` (has `train/` and `test/`) |
| `data/raw/rice_leaf_diseases` etc. | Kaggle or Mendeley sets for rice, wheat, cotton, sugarcane, mango (one folder per disease) |
| `data/raw/own_photos/<Plant___Disease>/` | Your own phone photos, sorted by disease |

## 2. Build the dataset

```bash
cp training/leaf_sources.example.json training/leaf_sources.json   # edit paths and roles
python training/build_leaf_dataset.py --config training/leaf_sources.json --dry-run
python training/build_leaf_dataset.py --config training/leaf_sources.json --out data/combined
```

The dry run shows how every folder will be labelled. Folders it can't map are listed as SKIPPED.
Add those to `"mapping"` in the config. Datasets whose folders only name the disease (for example
`Brown spot`) need `"plant": "Rice"` on their source.

`data/combined/report.md` has the numbers for your project report: images per source and class,
duplicates removed, and label conflicts dropped.

## 3. Train a baseline and the combined model

```bash
python training/train_leaf_disease.py --run-name plantvillage_only \
    --data-dirs data/combined/train/plantvillage --val-dirs data/combined/val/plantvillage
python training/train_leaf_disease.py --run-name combined \
    --data-dirs data/combined/train/* --val-dirs data/combined/val/*
```

## 4. Compare on lab vs field photos

```bash
python training/evaluate_leaf_disease.py \
    --models legacy models/candidates/plantvillage_only models/candidates/combined \
    --test "lab=data/combined/test_lab/*" "field=data/combined/test_field/*" \
           "own_photos=data/combined/test_field/own_photos"
```

The results table is written to `training/results/eval_<time>.md`. The second table there
compares all models on the classes they share, so the comparison is fair.

## 5. Use the new model in the app (only if it is better)

```bash
python training/promote_leaf_model.py models/candidates/combined
python training/promote_leaf_model.py --rollback
```

Promoting checks the model first and backs up the current one to `models/backup/`. Rolling back
with no backups left returns the app to the original `leaf_disease_model.h5`, which is never
modified. Restart Flask after either command.

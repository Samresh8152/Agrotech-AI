# Combined leaf disease dataset

- Images found: 22746
- Unreadable images skipped: 0
- Duplicate images removed: 19
- Duplicate groups dropped for conflicting labels: 20
- Images in the final dataset: 22686
- Classes: 33, plants: 9

## Images per source

| Source | train | val | test_lab | test_field | Total |
|---|---|---|---|---|---|
| plantdoc | 1328 | 188 | 0 | 377 | 1893 |
| plantdoc_test | 0 | 0 | 0 | 195 | 195 |
| plantvillage | 16478 | 2060 | 2060 | 0 | 20598 |

## Images per class

| Class | train | val | test_lab | test_field |
|---|---|---|---|---|
| Apple___Black_rot | 497 | 62 | 62 | 0 |
| Apple___Cedar_apple_rust | 273 | 36 | 28 | 26 |
| Apple___healthy | 616 | 78 | 70 | 25 |
| Apple___scab | 562 | 71 | 63 | 26 |
| Cherry___Powdery_mildew | 560 | 70 | 70 | 0 |
| Cherry___healthy | 593 | 75 | 70 | 19 |
| Corn___Cercospora_leaf_spot_Gray_leaf_spot | 455 | 57 | 51 | 15 |
| Corn___Common_rust | 634 | 80 | 70 | 31 |
| Corn___Northern_Leaf_Blight | 682 | 88 | 70 | 45 |
| Corn___healthy | 560 | 70 | 70 | 0 |
| Grape___Black_rot | 599 | 76 | 70 | 19 |
| Grape___Esca | 560 | 70 | 70 | 0 |
| Grape___Leaf_blight | 560 | 70 | 70 | 0 |
| Grape___healthy | 379 | 48 | 42 | 23 |
| Peach___Bacterial_spot | 560 | 70 | 70 | 0 |
| Peach___healthy | 360 | 46 | 36 | 29 |
| Pepper_bell___Bacterial_spot | 602 | 76 | 70 | 21 |
| Pepper_bell___healthy | 597 | 75 | 70 | 19 |
| Potato___Early_blight | 629 | 80 | 70 | 26 |
| Potato___Late_blight | 625 | 79 | 70 | 23 |
| Potato___healthy | 122 | 15 | 15 | 0 |
| Strawberry___Leaf_scorch | 560 | 70 | 70 | 0 |
| Strawberry___healthy | 425 | 55 | 46 | 26 |
| Tomato___Bacterial_spot | 631 | 80 | 70 | 28 |
| Tomato___Early_blight | 612 | 77 | 70 | 24 |
| Tomato___Late_blight | 624 | 79 | 70 | 29 |
| Tomato___Leaf_Mold | 619 | 78 | 70 | 23 |
| Tomato___Septoria_leaf_spot | 653 | 83 | 70 | 38 |
| Tomato___Spider_mites | 562 | 70 | 70 | 0 |
| Tomato___Target_Spot | 560 | 70 | 70 | 0 |
| Tomato___Yellow_Leaf_Curl_Virus | 607 | 77 | 70 | 19 |
| Tomato___healthy | 598 | 76 | 70 | 19 |
| Tomato___mosaic_virus | 330 | 41 | 37 | 19 |

## Folders skipped (no label mapping)

Add them to "mapping" in the config (value null keeps skipping), see mapping_template.json.

- **plantdoc**: Blueberry leaf (104), Raspberry leaf (112), Soyabean leaf (57), Squash Powdery mildew leaf (124)
- **plantdoc_test**: Blueberry leaf (11), Raspberry leaf (7), Soyabean leaf (8), Squash Powdery mildew leaf (6)

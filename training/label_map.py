"""
Label harmonization for combining leaf disease datasets.

Every dataset names its class folders differently (PlantVillage: "Corn_(maize)___Common_rust_",
PlantDoc: "Corn rust leaf", Kaggle rice sets: "Brown spot"). This module maps them all to one
canonical "Plant___Disease" name.

Canonical names are chosen so the Flask API's display name (class with "___" and "_" replaced by
spaces) matches the keys of DISEASE_INFO in backend/routes/disease.py, e.g.
"Tomato___Late_blight" -> "Tomato Late blight". That keeps the descriptions and treatments working
when a model trained on the combined dataset is promoted.
"""
import re

# Normalized folder name -> canonical class. Keys go through normalize() first.
ALIASES = {
    # ---- PlantVillage / "New Plant Diseases" (38 classes) ----
    'apple apple scab': 'Apple___scab',
    'apple black rot': 'Apple___Black_rot',
    'apple cedar apple rust': 'Apple___Cedar_apple_rust',
    'apple healthy': 'Apple___healthy',
    'blueberry healthy': 'Blueberry___healthy',
    'cherry including sour powdery mildew': 'Cherry___Powdery_mildew',
    'cherry including sour healthy': 'Cherry___healthy',
    'corn maize cercospora leaf spot gray leaf spot': 'Corn___Cercospora_leaf_spot_Gray_leaf_spot',
    'corn maize common rust': 'Corn___Common_rust',
    'corn maize northern leaf blight': 'Corn___Northern_Leaf_Blight',
    'corn maize healthy': 'Corn___healthy',
    'grape black rot': 'Grape___Black_rot',
    'grape esca black measles': 'Grape___Esca',
    'grape leaf blight isariopsis leaf spot': 'Grape___Leaf_blight',
    'grape healthy': 'Grape___healthy',
    'orange haunglongbing citrus greening': 'Orange___Huanglongbing',
    'peach bacterial spot': 'Peach___Bacterial_spot',
    'peach healthy': 'Peach___healthy',
    'pepper bell bacterial spot': 'Pepper_bell___Bacterial_spot',
    'pepper bell healthy': 'Pepper_bell___healthy',
    'potato early blight': 'Potato___Early_blight',
    'potato late blight': 'Potato___Late_blight',
    'potato healthy': 'Potato___healthy',
    'raspberry healthy': 'Raspberry___healthy',
    'soybean healthy': 'Soybean___healthy',
    'squash powdery mildew': 'Squash___Powdery_mildew',
    'strawberry leaf scorch': 'Strawberry___Leaf_scorch',
    'strawberry healthy': 'Strawberry___healthy',
    'tomato bacterial spot': 'Tomato___Bacterial_spot',
    'tomato early blight': 'Tomato___Early_blight',
    'tomato late blight': 'Tomato___Late_blight',
    'tomato leaf mold': 'Tomato___Leaf_Mold',
    'tomato septoria leaf spot': 'Tomato___Septoria_leaf_spot',
    'tomato spider mites two spotted spider mite': 'Tomato___Spider_mites',
    'tomato target spot': 'Tomato___Target_Spot',
    'tomato tomato yellow leaf curl virus': 'Tomato___Yellow_Leaf_Curl_Virus',
    'tomato tomato mosaic virus': 'Tomato___mosaic_virus',
    'tomato healthy': 'Tomato___healthy',
    # Kaggle "PlantVillage" copy with single underscores (dataset/Plant Diseas)
    'tomato tomato yellowleaf curl virus': 'Tomato___Yellow_Leaf_Curl_Virus',

    # ---- PlantDoc (real field photos). Healthy classes are just "<Plant> leaf" ----
    'apple scab leaf': 'Apple___scab',
    'apple leaf': 'Apple___healthy',
    'apple rust leaf': 'Apple___Cedar_apple_rust',
    'bell pepper leaf': 'Pepper_bell___healthy',
    'bell pepper leaf spot': 'Pepper_bell___Bacterial_spot',
    'blueberry leaf': 'Blueberry___healthy',
    'cherry leaf': 'Cherry___healthy',
    'corn gray leaf spot': 'Corn___Cercospora_leaf_spot_Gray_leaf_spot',
    'corn leaf blight': 'Corn___Northern_Leaf_Blight',
    'corn rust leaf': 'Corn___Common_rust',
    'peach leaf': 'Peach___healthy',
    'potato leaf': 'Potato___healthy',
    'potato leaf early blight': 'Potato___Early_blight',
    'potato leaf late blight': 'Potato___Late_blight',
    'raspberry leaf': 'Raspberry___healthy',
    'soyabean leaf': 'Soybean___healthy',
    'soybean leaf': 'Soybean___healthy',
    'squash powdery mildew leaf': 'Squash___Powdery_mildew',
    'strawberry leaf': 'Strawberry___healthy',
    'tomato early blight leaf': 'Tomato___Early_blight',
    'tomato septoria leaf spot': 'Tomato___Septoria_leaf_spot',
    'tomato leaf': 'Tomato___healthy',
    'tomato leaf bacterial spot': 'Tomato___Bacterial_spot',
    'tomato leaf late blight': 'Tomato___Late_blight',
    'tomato leaf mosaic virus': 'Tomato___mosaic_virus',
    'tomato leaf yellow virus': 'Tomato___Yellow_Leaf_Curl_Virus',
    'tomato mold leaf': 'Tomato___Leaf_Mold',
    'tomato two spotted spider mites leaf': 'Tomato___Spider_mites',
    'grape leaf': 'Grape___healthy',
    'grape leaf black rot': 'Grape___Black_rot',
}

# Words that only describe the photo, dropped when building a canonical name automatically
_NOISE_WORDS = {'leaf', 'leaves', 'disease', 'diseased', 'images', 'image'}


def normalize(name):
    """Lowercase, turn every non-alphanumeric run into one space: "Corn_(maize)___Common_rust_" -> "corn maize common rust"."""
    return re.sub(r'[^a-z0-9]+', ' ', name.lower()).strip()


def _canonical_from_parts(plant, disease):
    plant = '_'.join(w.capitalize() for w in normalize(plant).split())
    words = [w for w in normalize(disease).split() if w not in _NOISE_WORDS]
    if not words or words == ['healthy'] or 'healthy' in words or 'normal' in words:
        return f'{plant}___healthy'
    disease = '_'.join(words)
    return f'{plant}___{disease[0].upper()}{disease[1:]}'


def canonical_class(folder, plant=None, extra_mapping=None):
    """
    Canonical "Plant___Disease" for a dataset folder name, or None to skip the folder.

    folder:        the class folder name in the source dataset
    plant:         plant name for datasets whose folders only name the disease (e.g. a rice-only set
                   with folders "Brown spot", "Healthy")
    extra_mapping: user mapping {folder name: canonical class or null}; checked first
    """
    extra = {normalize(k): v for k, v in (extra_mapping or {}).items()}
    keys = [normalize(folder)]
    if plant:
        keys.insert(0, normalize(f'{plant} {folder}'))
    for key in keys:
        if key in extra:
            return extra[key]
        if key in ALIASES:
            return ALIASES[key]

    if plant:
        return _canonical_from_parts(plant, folder)
    if '___' in folder:
        # Already in PlantVillage layout but not a known class: clean it up and keep it
        p, d = folder.split('___', 1)
        p = re.sub(r'\(.*?\)', '', p)
        d = re.sub(r'\(.*?\)', '', d)
        return _canonical_from_parts(p, d)
    return None

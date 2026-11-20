import os
import json
import uuid
import numpy as np
import cv2
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from werkzeug.utils import secure_filename

from backend.services import gemini_disease
from backend.services.activity import log_activity

disease_bp = Blueprint('disease', __name__)

UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}
MIME_TYPES = {'png': 'image/png', 'jpg': 'image/jpeg', 'jpeg': 'image/jpeg', 'webp': 'image/webp'}

LEGACY_MODEL_PATH = 'models/leaf_disease_model.h5'
# Written by training/train_leaf_disease.py; used instead of the legacy model when present
NEW_MODEL_PATH = 'models/leaf_disease_model.keras'
LABELS_PATH = 'models/leaf_disease_labels.json'

# Label classes matching the trained leaf_disease_model.h5 (33 classes)
DISEASE_CLASSES = [
    'Apple scab', 'Apple Black rot', 'Apple Cedar apple rust', 'Apple healthy',
    'Cherry Powdery mildew', 'Cherry healthy',
    'Corn Cercospora leaf spot Gray leaf spot', 'Corn Common rust', 'Corn Northern Leaf Blight', 'Corn healthy',
    'Grape Black rot', 'Grape Esca', 'Grape Leaf blight', 'Grape healthy',
    'Peach Bacterial spot', 'Peach healthy',
    'Pepper bell Bacterial spot', 'Pepper bell healthy',
    'Potato Early blight', 'Potato Late blight', 'Potato healthy',
    'Strawberry Leaf scorch', 'Strawberry healthy',
    'Tomato Bacterial spot', 'Tomato Early blight', 'Tomato Late blight',
    'Tomato Leaf Mold', 'Tomato Septoria leaf spot', 'Tomato Spider mites',
    'Tomato Target Spot', 'Tomato Yellow Leaf Curl Virus', 'Tomato mosaic virus', 'Tomato healthy'
]

DISEASE_INFO = {
    'Apple scab': {
        'description': 'Fungal disease causing dark, scabby lesions on leaves and fruit.',
        'treatment': 'Remove infected leaves. Apply fungicides containing captan or myclobutanil. Rake and destroy fallen leaves to reduce spores.',
        'severity': 'Medium'
    },
    'Apple Black rot': {
        'description': 'Fungal disease causing black rotting of fruit and cankers on branches.',
        'treatment': 'Prune out dead or diseased wood. Remove mummified fruit. Apply appropriate fungicides during the growing season.',
        'severity': 'High'
    },
    'Apple Cedar apple rust': {
        'description': 'Fungal disease causing orange-yellow spots on leaves and fruit.',
        'treatment': 'Remove nearby cedar hosts if possible. Apply fungicides early in the season when apple blossoms are in the pink stage.',
        'severity': 'Medium'
    },
    'Cherry Powdery mildew': {
        'description': 'Fungal disease causing white powdery coating on leaves and shoots.',
        'treatment': 'Apply sulfur or potassium bicarbonate based fungicides. Ensure good air circulation by pruning.',
        'severity': 'Medium'
    },
    'Corn Cercospora leaf spot Gray leaf spot': {
        'description': 'Fungal disease causing tan to gray rectangular lesions on leaves.',
        'treatment': 'Plant resistant hybrids, use crop rotation to non-host crops, and apply fungicides if disease pressure is high.',
        'severity': 'Medium'
    },
    'Corn Common rust': {
        'description': 'Fungal disease with orange-brown pustules on both leaf surfaces.',
        'treatment': 'Use resistant hybrids. Foliar fungicides (propiconazole or trifloxystrobin) can be applied if symptoms appear early.',
        'severity': 'Medium'
    },
    'Corn Northern Leaf Blight': {
        'description': 'Fungal disease causing large, cigar-shaped gray-green lesions on leaves.',
        'treatment': 'Use resistant hybrids and crop rotation. Tillage helps bury infected residue. Apply fungicides if warranted.',
        'severity': 'High'
    },
    'Grape Black rot': {
        'description': 'Fungal disease causing brown leaf lesions and black mummified berries.',
        'treatment': 'Remove mummified berries and infected canes. Apply fungicides starting from early shoot growth until veraison.',
        'severity': 'High'
    },
    'Grape Esca': {
        'description': 'Complex fungal disease causing wood decay and leaf scorch symptoms.',
        'treatment': 'Remove and destroy infected wood. Preventive pruning wound protection is essential.',
        'severity': 'High'
    },
    'Grape Leaf blight': {
        'description': 'Fungal disease causing irregular brown lesions with yellow halos on leaves.',
        'treatment': 'Improve air circulation and spray with appropriate fungicides. Avoid overhead irrigation.',
        'severity': 'Medium'
    },
    'Peach Bacterial spot': {
        'description': 'Bacterial disease causing water-soaked lesions on leaves, fruit, and twigs.',
        'treatment': 'Use resistant varieties. Copper-based sprays can help manage the disease during the dormant and early seasons.',
        'severity': 'Medium'
    },
    'Pepper bell Bacterial spot': {
        'description': 'Bacterial disease causing small water-soaked spots on leaves and fruit.',
        'treatment': 'Plant disease-free seed and transplants. Use copper sprays combined with mancozeb to slow the spread.',
        'severity': 'Medium'
    },
    'Potato Early blight': {
        'description': 'Fungal disease with dark brown spots with concentric rings on lower leaves.',
        'treatment': 'Ensure proper nutrition. Apply protective fungicides like chlorothalonil or mancozeb every 7-10 days.',
        'severity': 'Medium'
    },
    'Potato Late blight': {
        'description': 'Oomycete disease causing water-soaked lesions that rapidly turn brown and kill the plant.',
        'treatment': 'Use resistant varieties. Apply metalaxyl fungicides immediately. Destroy cull piles.',
        'severity': 'High'
    },
    'Strawberry Leaf scorch': {
        'description': 'Fungal disease causing small purple-red spots that enlarge and turn brown.',
        'treatment': 'Remove old infected leaves. Practice crop rotation and avoid overhead watering.',
        'severity': 'Medium'
    },
    'Tomato Bacterial spot': {
        'description': 'Bacterial disease causing small water-soaked spots on leaves and fruit.',
        'treatment': 'Use disease-free seed, practice crop rotation, and avoid working in wet fields. Copper sprays can suppress it.',
        'severity': 'Medium'
    },
    'Tomato Early blight': {
        'description': 'Dark concentric ring spots on lower leaves, progressing upward.',
        'treatment': 'Apply mancozeb or chlorothalonil fungicides every 7-10 days. Remove infected lower leaves.',
        'severity': 'Medium'
    },
    'Tomato Late blight': {
        'description': 'Water-soaked lesions that expand rapidly in humid conditions, killing plants fast.',
        'treatment': 'Destroy infected plants immediately. Apply copper-based fungicides preventively.',
        'severity': 'High'
    },
    'Tomato Leaf Mold': {
        'description': 'Fungal disease causing pale green-yellow spots on upper leaf surface, olive-green mold below.',
        'treatment': 'Increase air circulation and reduce humidity. Apply chlorothalonil or copper fungicides.',
        'severity': 'Medium'
    },
    'Tomato Septoria leaf spot': {
        'description': 'Fungal disease causing small circular spots with dark borders and gray centers.',
        'treatment': 'Remove infected leaves, avoid overhead watering, and apply mancozeb or chlorothalonil fungicides.',
        'severity': 'Medium'
    },
    'Tomato Spider mites': {
        'description': 'Pest infestation causing stippled, yellowing leaves with fine webbing underneath.',
        'treatment': 'Use insecticidal soaps, neem oil, or predatory mites to control populations.',
        'severity': 'Medium'
    },
    'Tomato Target Spot': {
        'description': 'Fungal disease causing brown spots with concentric rings resembling a target.',
        'treatment': 'Ensure good air flow, avoid overhead watering, and apply chlorothalonil or mancozeb fungicides.',
        'severity': 'Medium'
    },
    'Tomato Yellow Leaf Curl Virus': {
        'description': 'Viral disease transmitted by whiteflies causing leaf curling and yellowing.',
        'treatment': 'Control whitefly populations using insecticides or reflective mulches. Remove and destroy infected plants.',
        'severity': 'High'
    },
    'Tomato mosaic virus': {
        'description': 'Viral disease causing mosaic patterns of light and dark green on leaves.',
        'treatment': 'Use resistant varieties, disinfect tools, and wash hands after handling infected plants. No chemical control available.',
        'severity': 'High'
    },
}


DEFAULT_INFO = {
    'description': 'Disease identified by AI analysis. Consult a local agricultural extension office for confirmation.',
    'treatment': 'Consult with a local agricultural expert for specific treatment recommendations.',
    'severity': 'Unknown'
}

# Plant names in the legacy class list (longest first so "Pepper bell" wins over "Pepper")
LEGACY_PLANTS = ['Pepper bell', 'Strawberry', 'Cherry', 'Potato', 'Tomato', 'Apple', 'Grape', 'Peach', 'Corn']

# Common names farmers type, mapped to the plant names the local model uses
PLANT_ALIASES = {
    'maize': 'corn', 'makka': 'corn', 'bell pepper': 'pepper bell', 'capsicum': 'pepper bell',
    'shimla mirch': 'pepper bell', 'tamatar': 'tomato', 'aloo': 'potato', 'angoor': 'grape',
    'seb': 'apple', 'aadu': 'peach',
}

# Below this the local model's answer is reported as uncertain
LOCAL_CONFIDENCE_THRESHOLD = 50.0

# Ensemble weights when both Gemini and the CNN cover the plant
GEMINI_WEIGHT = 0.6
CNN_WEIGHT = 0.4

_model = None
_meta = None


def _load_meta():
    """Class names, plant of each class, and preprocessing used by the local model."""
    global _meta
    if _meta is None:
        if os.path.exists(NEW_MODEL_PATH) and os.path.exists(LABELS_PATH):
            with open(LABELS_PATH) as f:
                data = json.load(f)
            classes = data['classes']
            # New-style labels are "Plant___Disease" (PlantVillage folder names)
            plants = [c.split('___')[0].replace('_', ' ').strip() for c in classes]
            names = [c.replace('___', ' ').replace('_', ' ').strip() for c in classes]
            _meta = {'classes': names, 'plants': plants,
                     'img_size': data.get('img_size', 224), 'scale': data.get('scale', 1.0)}
        else:
            plants = [next(p for p in LEGACY_PLANTS if c.startswith(p)) for c in DISEASE_CLASSES]
            # Legacy VGG16 model was trained on images scaled to 0-1
            _meta = {'classes': DISEASE_CLASSES, 'plants': plants, 'img_size': 150, 'scale': 1 / 255.0}
    return _meta


def _load_model():
    global _model
    if _model is None:
        try:
            import keras
            model_path = NEW_MODEL_PATH if os.path.exists(NEW_MODEL_PATH) and os.path.exists(LABELS_PATH) else LEGACY_MODEL_PATH
            if os.path.exists(model_path):
                _model = keras.models.load_model(model_path)
                print("✅ Leaf disease model loaded successfully")
            else:
                print(f"❌ Model file not found at {model_path}")
        except Exception as e:
            print(f"Model load error: {e}")
            _model = None
    return _model


def _allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def _match_local_plant(plant_name):
    """Return the local model's plant name for user input, or None if the model doesn't cover it."""
    if not plant_name:
        return None
    key = plant_name.strip().lower()
    key = PLANT_ALIASES.get(key, key)
    for p in sorted(set(_load_meta()['plants']), key=len, reverse=True):
        pl = p.lower()
        if key == pl or key.startswith(pl) or pl.startswith(key):
            return p
    return None


def _preprocess_image(filepath, meta):
    """Load and preprocess image with OpenCV to match the training pipeline."""
    img = cv2.imread(filepath)
    if img is None:
        raise ValueError("Could not read the image file")
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    size = meta['img_size']
    img_resized = cv2.resize(img_rgb, (size, size)).astype('float32') * meta['scale']
    return np.expand_dims(img_resized, axis=0)


def _local_predict(filepath, local_plant):
    """Run the CNN. When the plant is known, only that plant's classes compete."""
    m = _load_model()
    if m is None:
        return None
    meta = _load_meta()
    probs = m.predict(_preprocess_image(filepath, meta), verbose=0)[0].astype('float64')

    if local_plant:
        mask = np.array([p == local_plant for p in meta['plants']])
        probs = np.where(mask, probs, 0.0)
        total = probs.sum()
        probs = probs / total if total > 0 else mask / mask.sum()

    top3_idx = np.argsort(probs)[::-1][:3]
    top3 = [{'disease': meta['classes'][i], 'confidence': round(float(probs[i]) * 100, 2)}
            for i in top3_idx if probs[i] > 0]
    top = top3[0]
    disease = top['disease']
    is_healthy = 'healthy' in disease.lower()
    info = DISEASE_INFO.get(disease, DEFAULT_INFO)
    return {
        'plant': meta['plants'][top3_idx[0]],
        'disease': disease,
        'confidence': top['confidence'],
        'is_healthy': is_healthy,
        'severity': 'None' if is_healthy else info['severity'],
        'description': 'Plant looks healthy! Continue regular care and monitoring.' if is_healthy else info['description'],
        'treatment': 'Continue regular care and good agricultural practices.' if is_healthy else info['treatment'],
        'uncertain': top['confidence'] < LOCAL_CONFIDENCE_THRESHOLD,
        'plant_conditioned': bool(local_plant),
        'top_predictions': top3,
        # Full distribution over the plant's classes, used for fusion (not sent to the client)
        '_probs': {meta['classes'][i]: float(probs[i]) for i in range(len(probs)) if probs[i] > 0},
    }


def _public_local(local):
    return {k: v for k, v in local.items() if not k.startswith('_')} if local else None


def _from_gemini(g, plant_name, local):
    is_healthy = bool(g.get('is_healthy'))
    treatment = g.get('organic_treatment', []) + g.get('chemical_treatment', [])
    others = [{'disease': o['disease'], 'confidence': round(float(o['confidence']), 2)}
              for o in g.get('other_possibilities', [])]
    return {
        'source': 'gemini',
        'is_plant_image': g.get('is_plant_image', True),
        'plant': plant_name or g.get('plant_identified'),
        'plant_identified': g.get('plant_identified'),
        'plant_matches_input': g.get('plant_matches_input', True),
        'disease': g.get('disease'),
        'scientific_name': g.get('scientific_name', ''),
        'pathogen_type': g.get('pathogen_type', 'Unknown'),
        'confidence': g['confidence'],
        'is_healthy': is_healthy,
        'severity': 'None' if is_healthy else g.get('severity', 'Unknown'),
        'affected_area_percent': g.get('affected_area_percent'),
        'description': g.get('description', ''),
        'symptoms': g.get('symptoms', []),
        'causes': g.get('causes', []),
        'organic_treatment': g.get('organic_treatment', []),
        'chemical_treatment': g.get('chemical_treatment', []),
        'prevention': g.get('prevention', []),
        'treatment': ' '.join(treatment),
        'image_quality_note': g.get('image_quality_note', ''),
        'top_predictions': [{'disease': g.get('disease'), 'confidence': g['confidence']}] + others,
        'local_model': _public_local(local),
    }


def _from_local(local, plant_name):
    return {
        'source': 'local_model',
        'is_plant_image': True,
        'plant': plant_name or local['plant'],
        'plant_identified': local['plant'],
        'plant_matches_input': True,
        'disease': local['disease'],
        'scientific_name': '',
        'pathogen_type': 'None' if local['is_healthy'] else 'Unknown',
        'confidence': local['confidence'],
        'is_healthy': local['is_healthy'],
        'severity': local['severity'],
        'description': local['description'],
        'symptoms': [], 'causes': [], 'organic_treatment': [], 'chemical_treatment': [], 'prevention': [],
        'treatment': local['treatment'],
        'image_quality_note': '',
        'top_predictions': local['top_predictions'],
        'local_model': _public_local(local),
    }


def _fuse(g, local, plant_name, warnings):
    """Weighted vote between Gemini and the plant-conditioned CNN over the CNN's classes."""
    cnn_probs = local['_probs']
    match = g.get('model_class_match', 'none')
    ensemble = {
        'gemini': {'disease': g.get('disease'), 'confidence': g['confidence'], 'model_class_match': match},
        'cnn': {'disease': local['disease'], 'confidence': local['confidence']},
        'weights': {'gemini': GEMINI_WEIGHT, 'cnn': CNN_WEIGHT},
    }

    # Gemini saw something outside the CNN's classes (other plant, pest, deficiency...): trust Gemini
    if match not in cnn_probs or not g.get('plant_matches_input', True) or not g.get('is_plant_image', True):
        result = _from_gemini(g, plant_name, local)
        result['source'] = 'gemini'
        ensemble['agreement'] = 'gemini_only'
        result['ensemble'] = ensemble
        return result

    gconf = g['confidence'] / 100.0
    n = len(cnn_probs)
    gemini_probs = {c: gconf if c == match else (1 - gconf) / (n - 1) if n > 1 else 0.0 for c in cnn_probs}
    scores = {c: GEMINI_WEIGHT * gemini_probs[c] + CNN_WEIGHT * cnn_probs[c] for c in cnn_probs}
    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    best, best_score = ranked[0]

    if best == match:
        result = _from_gemini(g, plant_name, local)
        ensemble['agreement'] = 'agree' if local['disease'] == match else 'gemini_preferred'
        display = {match: g.get('disease')}
    else:
        # CNN was confident enough to outvote an unsure Gemini
        result = _from_local(local, plant_name)
        ensemble['agreement'] = 'cnn_preferred'
        display = {}
        warnings.append(f'The AI models disagree: Gemini suggested "{g.get("disease")}" '
                        f'({g["confidence"]}%). Please confirm with a closer photo or an expert.')

    result['source'] = 'ensemble'
    result['confidence'] = round(best_score * 100, 2)
    result['top_predictions'] = [{'disease': display.get(c, c), 'confidence': round(sc * 100, 2)}
                                 for c, sc in ranked[:3]]
    result['ensemble'] = ensemble
    return result


def _log_scan(result):
    status = 'healthy' if result['is_healthy'] else f"{result['disease']} ({result['severity']} severity)"
    log_activity('disease_scan', f"Disease scan of {result.get('plant_identified') or result['plant']}: {status}", {
        'plant': result['plant'], 'disease': result['disease'], 'confidence': result['confidence'],
        'severity': result['severity'], 'pathogen_type': result.get('pathogen_type'),
        'source': result['source'], 'treatment': result.get('treatment', '')[:400],
    })


@disease_bp.route('/plants', methods=['GET'])
def supported_plants():
    """Plants the offline model covers, and whether Gemini (any plant) is enabled."""
    return jsonify({
        'success': True,
        'gemini_enabled': gemini_disease.is_configured(),
        'local_model_plants': sorted(set(_load_meta()['plants'])),
    })


@disease_bp.route('/predict', methods=['POST'])
@jwt_required()
def predict_disease():
    try:
        if 'image' not in request.files:
            return jsonify({'success': False, 'message': 'No image file uploaded'}), 400

        file = request.files['image']
        if file.filename == '':
            return jsonify({'success': False, 'message': 'No file selected'}), 400

        if not _allowed_file(file.filename):
            return jsonify({'success': False, 'message': 'Invalid file type. Upload JPG, PNG, or WEBP.'}), 400

        plant_name = request.form.get('plant_name', '').strip()[:60]

        # Save file with unique name to avoid collisions
        original_filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4()}_{original_filename}"
        filepath = os.path.join(UPLOAD_FOLDER, unique_filename)
        file.save(filepath)

        warnings = []

        # 1. Local CNN: only meaningful for plants it was trained on
        local_plant = _match_local_plant(plant_name)
        local = None
        if local_plant or not plant_name:
            try:
                local = _local_predict(filepath, local_plant)
            except ValueError as e:
                return jsonify({'success': False, 'message': str(e)}), 400

        # 2. Gemini: works for any plant
        if gemini_disease.is_configured():
            ext = original_filename.rsplit('.', 1)[-1].lower()
            with open(filepath, 'rb') as f:
                image_bytes = f.read()
            # Gemini judges the image independently; it only sees the CNN's class names, not its answer
            use_ensemble = bool(local and local['plant_conditioned'])
            candidates = [c for c, p in zip(_load_meta()['classes'], _load_meta()['plants'])
                          if p == local_plant] if use_ensemble else None
            try:
                g = gemini_disease.diagnose(image_bytes, MIME_TYPES.get(ext, 'image/jpeg'), plant_name, candidates)
                result = _fuse(g, local, plant_name, warnings) if use_ensemble else _from_gemini(g, plant_name, local)
                _log_scan(result)
                return jsonify({'success': True, 'prediction': result, 'warnings': warnings})
            except gemini_disease.GeminiUnavailable as e:
                print(f"Gemini error: {e}")
                warnings.append(f'{e.user_message} Showing the offline model result instead.')
        else:
            warnings.append('GEMINI_API_KEY not configured; using the offline model only.')

        # 3. Fallback: local model
        if local is None:
            reason = warnings[-1].replace(' Showing the offline model result instead.', '') if warnings else ''
            supported = ', '.join(sorted(set(_load_meta()['plants'])))
            return jsonify({
                'success': False,
                'message': f'Offline model only supports: {supported}. '
                           f'Analysis of "{plant_name}" needs Gemini AI. {reason}'
            }), 503
        if local['uncertain']:
            warnings.append('Low confidence: the image may not match the plants this model was trained on.')
        result = _from_local(local, plant_name)
        _log_scan(result)
        return jsonify({'success': True, 'prediction': result, 'warnings': warnings})

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

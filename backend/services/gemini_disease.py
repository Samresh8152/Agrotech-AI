"""Plant disease diagnosis for any plant species using the Gemini vision API."""
import copy
import base64

from backend.services.gemini_client import generate_json, is_configured, GeminiUnavailable  # noqa: F401

# Structured output schema so Gemini always returns parseable JSON
RESPONSE_SCHEMA = {
    'type': 'OBJECT',
    'properties': {
        'is_plant_image': {'type': 'BOOLEAN'},
        'plant_identified': {'type': 'STRING'},
        'plant_matches_input': {'type': 'BOOLEAN'},
        'is_healthy': {'type': 'BOOLEAN'},
        'disease': {'type': 'STRING'},
        'scientific_name': {'type': 'STRING'},
        'pathogen_type': {
            'type': 'STRING',
            'enum': ['Fungal', 'Bacterial', 'Viral', 'Oomycete', 'Pest', 'Nutrient deficiency',
                     'Abiotic stress', 'None', 'Unknown'],
        },
        'confidence': {'type': 'NUMBER'},
        'severity': {'type': 'STRING', 'enum': ['None', 'Low', 'Medium', 'High', 'Unknown']},
        'affected_area_percent': {'type': 'NUMBER'},
        'description': {'type': 'STRING'},
        'symptoms': {'type': 'ARRAY', 'items': {'type': 'STRING'}},
        'causes': {'type': 'ARRAY', 'items': {'type': 'STRING'}},
        'organic_treatment': {'type': 'ARRAY', 'items': {'type': 'STRING'}},
        'chemical_treatment': {'type': 'ARRAY', 'items': {'type': 'STRING'}},
        'prevention': {'type': 'ARRAY', 'items': {'type': 'STRING'}},
        'other_possibilities': {
            'type': 'ARRAY',
            'items': {
                'type': 'OBJECT',
                'properties': {
                    'disease': {'type': 'STRING'},
                    'confidence': {'type': 'NUMBER'},
                },
                'required': ['disease', 'confidence'],
            },
        },
        'image_quality_note': {'type': 'STRING'},
    },
    'required': ['is_plant_image', 'plant_identified', 'plant_matches_input', 'is_healthy', 'disease',
                 'pathogen_type', 'confidence', 'severity', 'description', 'symptoms', 'causes',
                 'organic_treatment', 'chemical_treatment', 'prevention', 'other_possibilities'],
}

PROMPT = """You are an expert plant pathologist and agronomist advising farmers.

The farmer says this plant is: "{plant}".
Examine the uploaded image carefully (leaves, stems, fruit, spots, lesions, discoloration,
mold, pests, webbing, curling, wilting) and diagnose the plant's health.

Rules:
- If the image does not show a plant, set is_plant_image=false and explain in description.
- Identify the plant yourself. If it clearly differs from the farmer's input, set
  plant_matches_input=false and diagnose based on the plant you actually see.
- If the farmer did not give a plant name, set plant_matches_input=true.
- If the plant looks healthy, set is_healthy=true, disease="Healthy", pathogen_type="None", severity="None".
- Use the common disease name in "disease" (e.g. "Early Blight") and the pathogen's Latin name in scientific_name.
- confidence and other_possibilities[].confidence are percentages from 0 to 100. Be honest: lower the
  confidence when symptoms are ambiguous or the image is blurry, dark or too far away.
- Give practical, field-ready advice. For chemical treatments name the active ingredient and typical
  dose or interval. Prefer options commonly available to Indian farmers, and mention safety precautions.
- Keep each list item to one short sentence. Give 2-5 items per list.
- If image quality limits the diagnosis, say how to retake the photo in image_quality_note."""

CANDIDATES_PROMPT = """

Our offline classifier knows these classes for this plant:
{candidates}
Set model_class_match to the class that is the same condition as your diagnosis (use the exact text),
or "none" if your diagnosis is not in the list. Do not change your diagnosis to fit the list."""


def diagnose(image_bytes, mime_type, plant_name='', candidates=None):
    """Return a diagnosis dict for the image. Raises GeminiUnavailable on any failure.

    candidates: class names the local CNN knows for this plant. When given, Gemini also maps its
    diagnosis to one of them (model_class_match) so the two opinions can be fused.
    """
    schema = copy.deepcopy(RESPONSE_SCHEMA)
    prompt = PROMPT.format(plant=plant_name or 'not specified')
    if candidates:
        schema['properties']['model_class_match'] = {'type': 'STRING', 'enum': list(candidates) + ['none']}
        schema['required'].append('model_class_match')
        prompt += CANDIDATES_PROMPT.format(candidates='\n'.join(f'- {c}' for c in candidates))

    contents = [{
        'role': 'user',
        'parts': [
            {'text': prompt},
            {'inline_data': {'mime_type': mime_type, 'data': base64.b64encode(image_bytes).decode()}},
        ]
    }]
    result = generate_json(contents, schema)
    result['confidence'] = _percent(result.get('confidence', 0))
    for o in result.get('other_possibilities', []):
        o['confidence'] = _percent(o.get('confidence', 0))
    return result


def _percent(value):
    """Some models answer 0.95 instead of 95; normalise to a 0-100 percentage."""
    v = float(value or 0)
    if 0 < v <= 1:
        v *= 100
    return round(max(0.0, min(100.0, v)), 2)

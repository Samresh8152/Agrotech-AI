"""Minimal Gemini REST client shared by disease diagnosis and the farmer assistant."""
import os
import json
import time
import requests

GEMINI_URL = 'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent'
DEFAULT_MODEL = 'gemini-3.5-flash'
# Tried in order when the configured model is retired (404), overloaded (503) or rate limited (429)
# Lite models are faster and less busy but less accurate, so they are the last resort
FALLBACK_MODELS = ['gemini-3.5-flash', 'gemini-3.8-flash', 'gemini-3.7-flash', 'gemini-flash-latest',
                   'gemini-3.5-flash-lite', 'gemini-flash-lite-latest']
RETRYABLE_STATUS = {404, 429, 500, 503}
BUSY_STATUS = {503}          # overloaded: worth one more try on the same model after a short pause
TOTAL_BUDGET_SECONDS = 75    # stay under the frontend's 90 s request timeout


class GeminiUnavailable(Exception):
    """Raised when Gemini is not configured or the request fails.

    user_message explains the cause in plain words for the farmer.
    """
    def __init__(self, message, user_message='The AI service is temporarily unavailable. Please try again.'):
        super().__init__(message)
        self.user_message = user_message


def _user_message(statuses):
    if any(s in (400, 401, 403) for s in statuses):
        return 'The Gemini API key was rejected. Check GEMINI_API_KEY in the backend .env file.'
    if 429 in statuses:
        return ('Your Gemini free-tier quota is used up for now. Wait a minute and try again, '
                'or enable billing in Google AI Studio for higher limits.')
    return "Google's Gemini servers are very busy right now. Please try again in a minute."


def is_configured():
    return bool(os.getenv('GEMINI_API_KEY'))


def _post(model, api_key, body, timeout):
    return requests.post(
        GEMINI_URL.format(model=model),
        headers={'x-goog-api-key': api_key, 'Content-Type': 'application/json'},
        json=body,
        timeout=timeout,
    )


def generate_json(contents, schema, system_instruction=None, temperature=0.2):
    """Call Gemini with structured output and return the parsed JSON object.

    contents: list of {'role': 'user'|'model', 'parts': [...]} turns.
    """
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        raise GeminiUnavailable('GEMINI_API_KEY is not set',
                                'Gemini is not set up. Add GEMINI_API_KEY to the backend .env file.')

    body = {
        'contents': contents,
        'generationConfig': {
            'temperature': temperature,
            'responseMimeType': 'application/json',
            'responseSchema': schema,
        },
    }
    if system_instruction:
        body['systemInstruction'] = {'parts': [{'text': system_instruction}]}

    configured = os.getenv('GEMINI_MODEL') or DEFAULT_MODEL
    models = [configured] + [m for m in FALLBACK_MODELS if m != configured]
    errors = []
    statuses = []
    resp = None
    deadline = time.monotonic() + TOTAL_BUDGET_SECONDS
    attempts = [(m, n) for m in models for n in range(2)]
    for model, attempt in attempts:
        remaining = deadline - time.monotonic()
        if remaining < 3:
            break
        if attempt == 1:
            # Only retry the same model when it said it was busy
            if resp is None or resp.status_code not in BUSY_STATUS or errors[-1].split(':')[0] != model:
                continue
            time.sleep(1.5)
        try:
            resp = _post(model, api_key, body, timeout=min(30, remaining))
        except requests.RequestException as e:
            resp = None
            errors.append(f'{model}: {type(e).__name__}')
            continue
        if resp.status_code == 200:
            break
        try:
            msg = resp.json().get('error', {}).get('message', resp.text)
        except ValueError:
            msg = resp.text
        errors.append(f'{model}: {resp.status_code} {msg[:120]}')
        statuses.append(resp.status_code)
        # Bad key, bad request etc. won't be fixed by another model
        if resp.status_code not in RETRYABLE_STATUS:
            break
    if resp is None or resp.status_code != 200:
        raise GeminiUnavailable('Gemini API failed: ' + ' | '.join(errors), _user_message(statuses))

    try:
        parts = resp.json()['candidates'][0]['content']['parts']
        # Thinking models may put "thought" parts before the answer
        text = next(p['text'] for p in reversed(parts) if 'text' in p and not p.get('thought'))
        return json.loads(text)
    except (KeyError, IndexError, ValueError, StopIteration) as e:
        raise GeminiUnavailable(f'Unexpected Gemini response: {e}')

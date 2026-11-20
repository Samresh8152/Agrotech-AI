from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from backend.database import db
from backend.models.user import User
from backend.models.assistant import ActivityLog, ChatMessage, UserMemory
from backend.models.farm import FarmCrop
from backend.services.activity import log_activity
from backend.services.gemini_client import generate_json, is_configured, GeminiUnavailable

assistant_bp = Blueprint('assistant', __name__)

HISTORY_TURNS = 20      # past chat messages sent to Gemini
ACTIVITY_ITEMS = 15     # recent tool results sent to Gemini
MAX_MEMORIES = 40
MAX_MESSAGE_LEN = 2000

RESPONSE_SCHEMA = {
    'type': 'OBJECT',
    'properties': {
        'reply': {'type': 'STRING'},
        'new_facts': {'type': 'ARRAY', 'items': {'type': 'STRING'}},
        'crops_sown': {'type': 'ARRAY', 'items': {'type': 'OBJECT', 'properties': {
            'crop': {'type': 'STRING'},
            'variety': {'type': 'STRING'},
            'area': {'type': 'NUMBER'},
            'area_unit': {'type': 'STRING', 'enum': ['acre', 'hectare', 'guntha', 'bigha']},
            'sown_on': {'type': 'STRING'},
        }, 'required': ['crop']}},
        'farm_city': {'type': 'STRING'},
    },
    'required': ['reply', 'new_facts'],
}

SYSTEM_PROMPT = """You are "Krishi Mitra", the personal farming assistant inside the AgroTech app.
You help one farmer at a time and you remember them.

Today's date: {today}

## Farmer profile
- Name: {name}
- Location: {location}
- Member since: {member_since}

## Crops on the farm (from the app's crop records)
{crops}

## What you remember about this farmer
{memories}

## Their recent activity in the app (newest first)
{activity}

## How to help
- Use the profile, memories and activity above to personalise every answer: refer to their crops,
  location, season and earlier disease scans or soil tests when relevant ("Last week your tomato scan
  showed Early Blight...").
- Never invent history. If you don't know something important (crop, farm size, irrigation), ask.
- Give practical, step-by-step advice suited to small and medium Indian farms: quantities per acre,
  timings, low-cost and organic options first, chemical options with active ingredient, dose and safety.
- Reply in the same language and script the farmer writes in (English, Hindi or Hinglish).
- Keep answers short and clear; use bullet points. Use **bold** for key actions.
- When useful, point them to app tools: Disease Detection (photo diagnosis), Soil Analysis,
  Crop Advisor, Yield Prediction, Fertilizer Guide, Weather. The home screen shows their crops and local weather.
- For severe outbreaks, pesticide poisoning or financial/legal decisions, recommend contacting the
  local Krishi Vigyan Kendra (KVK) or the Kisan Call Centre (1800-180-1551).

## new_facts
Put in new_facts any lasting facts the farmer revealed in THEIR latest message that are not already
remembered: crops grown, farm size, soil, irrigation, livestock, location, problems they are facing,
preferences (e.g. "prefers organic methods"). One short third-person sentence each, e.g.
"Grows wheat and mustard on 3 acres". Return an empty list if there is nothing new.

## crops_sown
If the farmer's latest message says they have sown or planted a crop (any plant, today or earlier) that is
not already in "Crops on the farm", add it to crops_sown with the crop name in English, and area, unit,
variety and sowing date (YYYY-MM-DD, worked out from today's date if they say "last week" etc.) only if
they said them. Do not add crops they only plan to grow. Otherwise return an empty list.

## farm_city
If the farmer tells you where their farm is (village, town or district) and it differs from the profile
location, put it in farm_city. Otherwise return an empty string."""


def _current_user():
    return User.query.get(int(get_jwt_identity()))


def _format_activity(items):
    if not items:
        return '- No activity yet.'
    return '\n'.join(f"- {a.created_at:%Y-%m-%d}: {a.title}" for a in items)


def _build_system_prompt(user):
    memories = UserMemory.query.filter_by(user_id=user.id).order_by(UserMemory.created_at).all()
    activity = (ActivityLog.query.filter_by(user_id=user.id)
                .order_by(ActivityLog.created_at.desc()).limit(ACTIVITY_ITEMS).all())
    return SYSTEM_PROMPT.format(
        today=datetime.now().strftime('%d %B %Y'),
        name=user.name,
        location=user.location or 'unknown',
        member_since=user.created_at.strftime('%B %Y') if user.created_at else 'unknown',
        memories='\n'.join(f'- {m.fact}' for m in memories) or '- Nothing yet.',
        crops='\n'.join(f'- {c.describe()}' for c in FarmCrop.query.filter_by(user_id=user.id).all()) or '- None recorded yet.',
        activity=_format_activity(activity),
    )


def _save_facts(user_id, facts):
    existing = {m.fact.strip().lower() for m in UserMemory.query.filter_by(user_id=user_id).all()}
    added = []
    for fact in facts:
        fact = fact.strip()[:300]
        if fact and fact.lower() not in existing:
            db.session.add(UserMemory(user_id=user_id, fact=fact))
            existing.add(fact.lower())
            added.append(fact)
    db.session.flush()
    # Keep memory bounded: drop the oldest facts
    all_mem = UserMemory.query.filter_by(user_id=user_id).order_by(UserMemory.created_at.desc()).all()
    for m in all_mem[MAX_MEMORIES:]:
        db.session.delete(m)
    return added


def _save_crops(user, crops):
    """Record crops the farmer said they sowed, skipping ones already growing."""
    from datetime import date
    growing = {c.crop.lower() for c in FarmCrop.query.filter_by(user_id=user.id, status='growing').all()}
    added = []
    for item in crops[:5]:
        name = str(item.get('crop', '')).strip()[:80]
        if not name or name.lower() in growing:
            continue
        crop = FarmCrop(user_id=user.id, crop=name[0].upper() + name[1:], status='growing', source='assistant',
                        variety=(str(item.get('variety') or '').strip()[:80] or None),
                        area_unit=item.get('area_unit') or 'acre')
        try:
            crop.area = float(item['area']) if item.get('area') else None
            sown = date.fromisoformat(str(item.get('sown_on'))[:10]) if item.get('sown_on') else None
            crop.sown_on = sown if sown and sown <= date.today() else None
        except (ValueError, TypeError):
            pass
        db.session.add(crop)
        db.session.commit()
        growing.add(name.lower())
        log_activity('sowing', f'Sowed {crop.describe()} (told the assistant)', {'crop_id': crop.id, 'crop': crop.crop})
        added.append(crop.crop)
    return added


def _save_city(user, city):
    city = city.strip()[:100]
    if not city or (user.location or '').strip().lower() == city.lower():
        return None
    if user.location:  # don't silently overwrite a location the farmer set themselves
        return None
    user.location = city
    db.session.commit()
    log_activity('farm', f'Farm location set to {city} (told the assistant)')
    return city


@assistant_bp.route('/history', methods=['GET'])
@jwt_required()
def history():
    user = _current_user()
    if not user:
        return jsonify({'success': False, 'message': 'User not found'}), 404
    messages = (ChatMessage.query.filter_by(user_id=user.id)
                .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc()).limit(100).all())
    memories = UserMemory.query.filter_by(user_id=user.id).order_by(UserMemory.created_at.desc()).all()
    activity = (ActivityLog.query.filter_by(user_id=user.id)
                .order_by(ActivityLog.created_at.desc()).limit(20).all())
    return jsonify({
        'success': True,
        'gemini_enabled': is_configured(),
        'messages': [m.to_dict() for m in reversed(messages)],
        'memories': [m.to_dict() for m in memories],
        'activity': [a.to_dict() for a in activity],
    })


@assistant_bp.route('/chat', methods=['POST'])
@jwt_required()
def chat():
    try:
        user = _current_user()
        if not user:
            return jsonify({'success': False, 'message': 'User not found'}), 404

        message = ((request.get_json(silent=True) or {}).get('message') or '').strip()
        if not message:
            return jsonify({'success': False, 'message': 'Message is empty'}), 400
        message = message[:MAX_MESSAGE_LEN]

        past = (ChatMessage.query.filter_by(user_id=user.id)
                .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc()).limit(HISTORY_TURNS).all())
        past = list(reversed(past))
        # Gemini expects the conversation to start with a user turn
        while past and past[0].role != 'user':
            past.pop(0)
        contents = [{'role': m.role, 'parts': [{'text': m.content}]} for m in past]
        contents.append({'role': 'user', 'parts': [{'text': message}]})

        try:
            out = generate_json(contents, RESPONSE_SCHEMA, system_instruction=_build_system_prompt(user),
                                temperature=0.5)
        except GeminiUnavailable as e:
            print(f"Assistant Gemini error: {e}")
            return jsonify({'success': False, 'message': e.user_message}), 503

        reply = (out.get('reply') or '').strip() or "Sorry, I couldn't answer that. Could you rephrase?"
        user_msg = ChatMessage(user_id=user.id, role='user', content=message)
        model_msg = ChatMessage(user_id=user.id, role='model', content=reply)
        db.session.add(user_msg)
        db.session.add(model_msg)
        db.session.flush()
        new_facts = _save_facts(user.id, out.get('new_facts') or [])
        db.session.commit()
        crops_added = _save_crops(user, out.get('crops_sown') or [])
        city_set = _save_city(user, out.get('farm_city') or '')

        return jsonify({
            'success': True,
            'reply': model_msg.to_dict(),
            'user_message': user_msg.to_dict(),
            'new_facts': new_facts,
            'crops_added': crops_added,
            'city_set': city_set,
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@assistant_bp.route('/history', methods=['DELETE'])
@jwt_required()
def clear_history():
    ChatMessage.query.filter_by(user_id=int(get_jwt_identity())).delete()
    db.session.commit()
    return jsonify({'success': True})


@assistant_bp.route('/memory', methods=['POST'])
@jwt_required()
def add_memory():
    fact = ((request.get_json(silent=True) or {}).get('fact') or '').strip()
    if not fact:
        return jsonify({'success': False, 'message': 'Fact is empty'}), 400
    user_id = int(get_jwt_identity())
    added = _save_facts(user_id, [fact])
    db.session.commit()
    return jsonify({'success': True, 'added': added})


@assistant_bp.route('/memory/<int:memory_id>', methods=['DELETE'])
@jwt_required()
def delete_memory(memory_id):
    m = UserMemory.query.filter_by(id=memory_id, user_id=int(get_jwt_identity())).first()
    if not m:
        return jsonify({'success': False, 'message': 'Not found'}), 404
    db.session.delete(m)
    db.session.commit()
    return jsonify({'success': True})

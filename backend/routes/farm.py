"""The farmer's own farm: saved city, crops sown (any plant), full activity history and a home overview."""
import json
from datetime import date, datetime

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from backend.database import db
from backend.models.user import User
from backend.models.farm import FarmCrop
from backend.models.assistant import ActivityLog
from backend.services.activity import log_activity
from backend.services import farm_weather

farm_bp = Blueprint('farm', __name__)

UNITS = {'acre', 'hectare', 'guntha', 'bigha'}


def _user():
    return User.query.get(int(get_jwt_identity()))


def _parse_date(value):
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        raise ValueError(f'Invalid date "{value}". Use YYYY-MM-DD.')


def _crops(user_id):
    crops = FarmCrop.query.filter_by(user_id=user_id).all()
    # growing first, then most recently sown
    return sorted(crops, key=lambda c: (c.status != 'growing', -(c.sown_on.toordinal() if c.sown_on else 0), -c.id))


def _last_scans(user_id, crops):
    """Latest disease scan per crop name (matched loosely on the plant name)."""
    scans = (ActivityLog.query.filter_by(user_id=user_id, kind='disease_scan')
             .order_by(ActivityLog.created_at.desc()).limit(100).all())
    out = {}
    for c in crops:
        name = c.crop.lower()
        for s in scans:
            d = json.loads(s.details) if s.details else {}
            plant = str(d.get('plant', '')).lower()
            if plant and (name in plant or plant in name):
                out[c.id] = {'disease': d.get('disease'), 'severity': d.get('severity'),
                             'created_at': s.created_at.isoformat() if s.created_at else None}
                break
    return out


def apply_crop_fields(crop, data):
    if 'crop' in data:
        name = str(data['crop']).strip()[:80]
        if not name:
            raise ValueError('Crop name is required')
        crop.crop = name[0].upper() + name[1:]
    if 'variety' in data:
        crop.variety = (str(data['variety']).strip()[:80] or None) if data['variety'] else None
    if 'area' in data:
        crop.area = float(data['area']) if data['area'] not in (None, '') else None
        if crop.area is not None and crop.area < 0:
            raise ValueError('Area cannot be negative')
    if 'area_unit' in data and data['area_unit']:
        if data['area_unit'] not in UNITS:
            raise ValueError(f'Unit must be one of {", ".join(sorted(UNITS))}')
        crop.area_unit = data['area_unit']
    if 'field_name' in data:
        crop.field_name = (str(data['field_name']).strip()[:80] or None) if data['field_name'] else None
    if 'sown_on' in data:
        crop.sown_on = _parse_date(data['sown_on'])
        if crop.sown_on and crop.sown_on > date.today():
            raise ValueError('Sowing date cannot be in the future')
    if 'notes' in data:
        crop.notes = (str(data['notes']).strip()[:300] or None) if data['notes'] else None


@farm_bp.route('', methods=['GET'])
@jwt_required()
def get_farm():
    user = _user()
    crops = _crops(user.id)
    return jsonify({'success': True, 'city': user.location, 'crops': [c.to_dict() for c in crops]})


@farm_bp.route('/city', methods=['PUT'])
@jwt_required()
def set_city():
    user = _user()
    city = str((request.get_json() or {}).get('city', '')).strip()[:100]
    if not city:
        return jsonify({'success': False, 'message': 'Enter your village, town or district'}), 400
    try:
        current, _ = farm_weather.fetch(city)
    except farm_weather.WeatherError as e:
        return jsonify({'success': False, 'message': str(e)}), 400
    user.location = city
    db.session.commit()
    log_activity('farm', f'Farm location set to {city} ({current["city"]}, {current["country"]})')
    return jsonify({'success': True, 'city': city, 'user': user.to_dict()})


@farm_bp.route('/crops', methods=['POST'])
@jwt_required()
def add_crop():
    user = _user()
    data = request.get_json() or {}
    crop = FarmCrop(user_id=user.id, status='growing', source='manual', sown_on=date.today())
    try:
        apply_crop_fields(crop, {'crop': data.get('crop', ''), **{k: v for k, v in data.items() if k != 'crop'}})
    except (ValueError, TypeError) as e:
        return jsonify({'success': False, 'message': str(e)}), 400
    db.session.add(crop)
    db.session.commit()
    log_activity('sowing', f'Sowed {crop.describe()}', {'crop_id': crop.id, 'crop': crop.crop})
    return jsonify({'success': True, 'crop': crop.to_dict()}), 201


@farm_bp.route('/crops/<int:crop_id>', methods=['PATCH'])
@jwt_required()
def update_crop(crop_id):
    user = _user()
    crop = FarmCrop.query.filter_by(id=crop_id, user_id=user.id).first()
    if not crop:
        return jsonify({'success': False, 'message': 'Crop not found'}), 404
    data = request.get_json() or {}
    try:
        apply_crop_fields(crop, data)
        if data.get('status') == 'harvested' and crop.status != 'harvested':
            crop.status = 'harvested'
            crop.harvested_on = _parse_date(data.get('harvested_on')) or date.today()
            db.session.commit()
            log_activity('harvest', f'Harvested {crop.crop}' + (f' ({crop.area:g} {crop.area_unit}{"" if crop.area == 1 else "s"})' if crop.area else '')
                         + (f' after {crop.days_since_sowing()} days' if crop.sown_on else ''), {'crop_id': crop.id})
        elif data.get('status') == 'growing':
            crop.status, crop.harvested_on = 'growing', None
    except (ValueError, TypeError) as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400
    db.session.commit()
    return jsonify({'success': True, 'crop': crop.to_dict()})


@farm_bp.route('/crops/<int:crop_id>', methods=['DELETE'])
@jwt_required()
def delete_crop(crop_id):
    user = _user()
    crop = FarmCrop.query.filter_by(id=crop_id, user_id=user.id).first()
    if not crop:
        return jsonify({'success': False, 'message': 'Crop not found'}), 404
    db.session.delete(crop)
    db.session.commit()
    return jsonify({'success': True})


@farm_bp.route('/history', methods=['GET'])
@jwt_required()
def history():
    user = _user()
    q = ActivityLog.query.filter_by(user_id=user.id)
    kind = request.args.get('kind')
    if kind:
        q = q.filter_by(kind=kind)
    limit = min(int(request.args.get('limit', 200)), 500)
    items = q.order_by(ActivityLog.created_at.desc()).limit(limit).all()
    counts = dict(db.session.query(ActivityLog.kind, db.func.count(ActivityLog.id))
                  .filter_by(user_id=user.id).group_by(ActivityLog.kind).all())
    return jsonify({'success': True, 'history': [a.to_dict() for a in items], 'counts': counts})


@farm_bp.route('/overview', methods=['GET'])
@jwt_required()
def overview():
    """Everything the home screen needs in one call."""
    user = _user()
    crops = _crops(user.id)
    scans = _last_scans(user.id, crops)
    crop_dicts = [{**c.to_dict(), 'last_scan': scans.get(c.id)} for c in crops]
    weather = {'current': None, 'days': [], 'alerts': [], 'error': None}
    if user.location:
        try:
            current, days = farm_weather.fetch(user.location)
            weather.update(current=current, days=days, alerts=farm_weather.field_alerts(current, days, crops))
        except farm_weather.WeatherError as e:
            weather['error'] = str(e)
    recent = (ActivityLog.query.filter_by(user_id=user.id)
              .order_by(ActivityLog.created_at.desc()).limit(8).all())
    return jsonify({
        'success': True,
        'city': user.location,
        'crops': crop_dicts,
        'weather': weather,
        'recent': [a.to_dict() for a in recent],
        'generated_at': datetime.now().isoformat(timespec='seconds'),
    })

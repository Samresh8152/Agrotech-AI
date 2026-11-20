from backend.database import db
from datetime import datetime, timezone, date


class FarmCrop(db.Model):
    """A crop the farmer has sown. Free text, so any plant can be recorded, not only the model's classes."""
    __tablename__ = 'farm_crops'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    crop = db.Column(db.String(80), nullable=False)
    variety = db.Column(db.String(80), nullable=True)
    area = db.Column(db.Float, nullable=True)
    area_unit = db.Column(db.String(10), default='acre')  # acre | hectare | guntha | bigha
    field_name = db.Column(db.String(80), nullable=True)
    sown_on = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(20), default='growing')  # growing | harvested
    harvested_on = db.Column(db.Date, nullable=True)
    notes = db.Column(db.String(300), nullable=True)
    source = db.Column(db.String(20), default='manual')  # manual | assistant
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def days_since_sowing(self):
        if not self.sown_on:
            return None
        end = self.harvested_on if self.status == 'harvested' and self.harvested_on else date.today()
        return max(0, (end - self.sown_on).days)

    def describe(self):
        """One line for the assistant prompt and activity titles."""
        parts = [self.crop + (f' ({self.variety})' if self.variety else '')]
        if self.area:
            parts.append(f'{self.area:g} {self.area_unit}{"" if self.area == 1 else "s"}')
        if self.field_name:
            parts.append(f'field "{self.field_name}"')
        if self.sown_on:
            parts.append(f'sown {self.sown_on:%d %b %Y}')
            d = self.days_since_sowing()
            if self.status == 'growing' and d is not None:
                parts.append(f'day {d}')
        if self.status == 'harvested':
            parts.append('harvested' + (f' {self.harvested_on:%d %b %Y}' if self.harvested_on else ''))
        return ', '.join(parts)

    def to_dict(self):
        return {
            'id': self.id,
            'crop': self.crop,
            'variety': self.variety,
            'area': self.area,
            'area_unit': self.area_unit,
            'field_name': self.field_name,
            'sown_on': self.sown_on.isoformat() if self.sown_on else None,
            'status': self.status,
            'harvested_on': self.harvested_on.isoformat() if self.harvested_on else None,
            'notes': self.notes,
            'source': self.source,
            'days_since_sowing': self.days_since_sowing(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

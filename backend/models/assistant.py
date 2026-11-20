from backend.database import db
from datetime import datetime, timezone
import json


class ActivityLog(db.Model):
    """Everything a farmer does with the AI tools, so the assistant knows their history."""
    __tablename__ = 'activity_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    kind = db.Column(db.String(30), nullable=False)  # disease_scan | soil_test | crop_recommendation | yield_prediction | fertilizer
    title = db.Column(db.String(300), nullable=False)
    details = db.Column(db.Text, nullable=True)  # JSON
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    def to_dict(self):
        return {
            'id': self.id,
            'kind': self.kind,
            'title': self.title,
            'details': json.loads(self.details) if self.details else {},
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class ChatMessage(db.Model):
    __tablename__ = 'chat_messages'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    role = db.Column(db.String(10), nullable=False)  # user | model
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            'id': self.id,
            'role': self.role,
            'content': self.content,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class UserMemory(db.Model):
    """Durable facts the assistant learned about a farmer (crops, farm size, irrigation...)."""
    __tablename__ = 'user_memories'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    fact = db.Column(db.String(300), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            'id': self.id,
            'fact': self.fact,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

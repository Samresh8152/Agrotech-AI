"""Record what each farmer does so the assistant can use it as context."""
import json
from flask_jwt_extended import get_jwt_identity

from backend.database import db


def log_activity(kind, title, details=None):
    """Save an activity for the current JWT user. Never breaks the calling request."""
    from backend.models.assistant import ActivityLog
    try:
        user_id = int(get_jwt_identity())
        db.session.add(ActivityLog(user_id=user_id, kind=kind, title=title[:300],
                                   details=json.dumps(details or {}, default=str)))
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Activity log error: {e}")

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json
from sqlalchemy import Text
from sqlalchemy.types import TypeDecorator

db = SQLAlchemy()

# Custom JSON type that works with SQLite
class JSONType(TypeDecorator):
    impl = Text

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return json.dumps(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        try:
            return json.loads(value)
        except (ValueError, TypeError):
            return {}

class SavedPage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    url = db.Column(db.String(500), nullable=False)
    saved_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    gumloop_data = db.Column(JSONType)  # Use JSONType for SQLite compatibility
    saved_item_id = db.Column(db.String(50), unique=True, nullable=False)  # Store Gumloop saved_item_id

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'url': self.url,
            'saved_at': self.saved_at.strftime('%Y-%m-%d %H:%M:%S'),
            'gumloop_data': self.gumloop_data,
            'saved_item_id': self.saved_item_id
        } 
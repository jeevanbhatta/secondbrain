from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

db = SQLAlchemy()

class SavedPage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    url = db.Column(db.String(500), nullable=False)
    saved_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    gumloop_data = db.Column(db.JSON)  # Store Gumloop API response as JSON
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
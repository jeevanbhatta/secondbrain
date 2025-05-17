from flask import render_template, jsonify
from ..models import SavedPage
from . import main_bp
from datetime import datetime, timedelta


@main_bp.route('/')
def index():
    saved_pages = SavedPage.query.order_by(SavedPage.saved_at.desc()).all()
    today = datetime.now().strftime('%Y-%m-%d')
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    return render_template('home.html', saved_pages=saved_pages, today=today, yesterday=yesterday)


@main_bp.route('/about')
def about():
    return render_template('about.html')


# New API endpoint for recent bookmarks
@main_bp.route('/api/recent-pages')
def api_recent_pages():
    recent = SavedPage.query.order_by(SavedPage.saved_at.desc()).limit(5).all()
    return jsonify([page.to_dict() for page in recent]) 
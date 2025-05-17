from flask import render_template
from ..models import SavedPage
from . import main_bp

@main_bp.route('/')
def index():
    saved_pages = SavedPage.query.order_by(SavedPage.saved_at.desc()).all()
    return render_template('home.html', saved_pages=saved_pages)

@main_bp.route('/about')
def about():
    return render_template('about.html') 
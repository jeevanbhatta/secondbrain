from flask import render_template, current_app
from ..models import SavedPage
from . import main_bp
import json
import logging

# Setup logger without importing from app
logger = logging.getLogger(__name__)

# Helper function to fetch gumloop extraction without importing from app
def fetch_gumloop_extraction(run_id):
    """
    Fetch extraction results from Gumloop using the run_id
    """
    # We'll get the function from current_app.config which will be set in app.py
    if 'fetch_gumloop_extraction' in current_app.config:
        return current_app.config['fetch_gumloop_extraction'](run_id)
    else:
        logger.error("fetch_gumloop_extraction function not available in app config")
        return {"error": "Extraction function not configured"}

@main_bp.route('/')
def index():
    saved_pages = SavedPage.query.order_by(SavedPage.saved_at.desc()).all()
    return render_template('index.html', saved_pages=saved_pages)

@main_bp.route('/page/<int:page_id>')
def page_detail(page_id):
    page = SavedPage.query.get_or_404(page_id)
    
    # Initialize extraction content
    extracted_content = None
    
    # Check if we have Gumloop data
    if page.gumloop_data:
        try:
            # Extract the run_id from the Gumloop response
            if isinstance(page.gumloop_data, str):
                gumloop_data = json.loads(page.gumloop_data)
            else:
                gumloop_data = page.gumloop_data
                
            run_id = gumloop_data.get('run_id')
            
            if run_id:
                logger.info(f"Fetching extraction for run_id: {run_id}")
                # Call the function to get extraction results
                extraction_results = fetch_gumloop_extraction(run_id)
                
                if extraction_results and not extraction_results.get('error'):
                    extracted_content = extraction_results
        except Exception as e:
            logger.error(f"Error getting extraction content: {str(e)}")
            extracted_content = {"error": f"Failed to parse extraction results: {str(e)}"}
    
    return render_template('page_detail.html', page=page, extracted_content=extracted_content)

@main_bp.route('/about')
def about():
    return render_template('about.html')
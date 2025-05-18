from flask import render_template, jsonify, current_app, request, redirect, url_for
from ..models import SavedPage
from . import main_bp

from datetime import datetime, timedelta
import json
import logging
import re

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

# Helper function for extracting URLs from text
def extract_urls(text):
    """Extract URLs from text using regex"""
    url_pattern = r'https?://[^\s<>"\']+|www\.[^\s<>"\']+\.[^\s<>"\']+'
    return re.findall(url_pattern, text)

@main_bp.route('/')
def index():
    saved_pages = SavedPage.query.order_by(SavedPage.saved_at.desc()).all()
    today = datetime.now().strftime('%Y-%m-%d')
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    return render_template('index.html', saved_pages=saved_pages, today=today, yesterday=yesterday)

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
                
            # First check for run_id in the Gumloop response
            run_id = gumloop_data.get('run_id')
            
            # If run_id is not found in Gumloop response, use saved_item_id from our database
            if not run_id and page.saved_item_id:
                logger.info(f"Using saved_item_id as run_id: {page.saved_item_id}")
                run_id = page.saved_item_id
            
            if run_id:
                logger.info(f"Fetching extraction for run_id: {run_id}")
                # Call the function to get extraction results
                extraction_results = fetch_gumloop_extraction(run_id)
                
                if extraction_results and not extraction_results.get('error'):
                    extracted_content = extraction_results
                    # Add detailed debug logging
                    logger.debug(f"Extracted content: {extracted_content}")
        except Exception as e:
            logger.error(f"Error getting extraction content: {str(e)}")
            extracted_content = {"error": f"Failed to parse extraction results: {str(e)}"}
    
    return render_template('page_detail.html', page=page, extracted_content=extracted_content)

@main_bp.route('/search', methods=['GET', 'POST'])
def search():
    """Search endpoint for web UI"""
    query = None
    results = None
    
    if request.method == 'POST':
        query = request.form.get('query', '').strip()
        
        if query:
            # Import the conversational_search function from app.py
            if 'mcp_conversational_search' in current_app.config:
                try:
                    search_function = current_app.config['mcp_conversational_search']
                    # Call the function instead of treating it as a data structure
                    response = search_function(query)
                    
                    # Format the results properly for the template
                    # If it's already a string, wrap it in a structure the template expects
                    if isinstance(response, str):
                        results = {
                            "conversational_response": response,
                            "items": []  # Empty items array
                        }
                    # If it's a dict, ensure it has the right structure
                    elif isinstance(response, dict):
                        # If it has 'conversational_response' field, ensure it has 'items'
                        if 'conversational_response' in response:
                            if 'items' not in response:
                                response['items'] = []
                            results = response
                        # Otherwise, format it appropriately
                        else:
                            results = {
                                "conversational_response": response.get('message', 'No response available'),
                                "items": response.get('items', [])
                            }
                    # Fallback for unknown response format
                    else:
                        results = {
                            "conversational_response": "Received a response in an unexpected format",
                            "items": []
                        }
                        
                    # Log the results structure for debugging
                    logger.debug(f"Search results structure: {results}")
                        
                except Exception as e:
                    logger.error(f"Error in search: {str(e)}")
                    results = {"error": f"Search failed: {str(e)}", "items": []}
            else:
                results = {"error": "Search functionality not available", "items": []}
    
    return render_template('search.html', query=query, results=results)

@main_bp.route('/about')
def about():
    return render_template('about.html')

# API endpoint for recent bookmarks
@main_bp.route('/api/recent-pages')
def api_recent_pages():
    recent = SavedPage.query.order_by(SavedPage.saved_at.desc()).limit(5).all()
    return jsonify([page.to_dict() for page in recent]) 

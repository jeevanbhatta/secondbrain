from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
from App.routes import main_bp
from App.models import db, SavedPage
import os
import logging
import requests
from dotenv import load_dotenv
import uuid
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Get the saved_item_id from environment variable
GUMLOOP_SAVED_ITEM_ID = os.getenv('GUMLOOP_SAVED_ITEM_ID')
if not GUMLOOP_SAVED_ITEM_ID:
    logger.warning("GUMLOOP_SAVED_ITEM_ID not found in environment variables. Please set this to your saved automation flow ID.")

# Configure retry strategy for requests
retry_strategy = Retry(
    total=3,  # number of retries
    backoff_factor=1,  # wait 1, 2, 4 seconds between retries
    status_forcelist=[500, 502, 503, 504]  # HTTP status codes to retry on
)
adapter = HTTPAdapter(max_retries=retry_strategy)
session = requests.Session()
session.mount("https://", adapter)
session.mount("http://", adapter)

app = Flask(__name__, 
    template_folder='App/templates',
    static_folder='App/static'
)

# Configure SQLite database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///saved_pages.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db.init_app(app)

# Simple CORS configuration
CORS(app)

# Register blueprints
app.register_blueprint(main_bp)

# Create database tables
with app.app_context():
    db.create_all()
    logger.info("Database tables created")

# API endpoints for the extension
@app.route('/api/save-page', methods=['POST', 'OPTIONS'])
def save_page():
    logger.debug(f"Received {request.method} request to /api/save-page")
    logger.debug(f"Request headers: {dict(request.headers)}")
    
    # Handle preflight request
    if request.method == 'OPTIONS':
        return '', 200

    try:
        data = request.get_json()
        logger.debug(f"Received data: {data}")
        
        if not data or 'title' not in data or 'url' not in data:
            logger.error("Missing required fields in request data")
            return jsonify({
                "message": "Missing required fields: title and url",
                "status": "error"
            }), 400

        # Get Gumloop API key from environment variable
        gumloop_api_key = os.getenv('GUMLOOP_API_KEY')
        if not gumloop_api_key:
            logger.error("Gumloop API key not found in environment variables")
            return jsonify({
                "message": "Server configuration error: Gumloop API key not found",
                "status": "error"
            }), 500

        # Check if we have a valid saved_item_id
        if not GUMLOOP_SAVED_ITEM_ID:
            logger.error("Gumloop saved_item_id not configured")
            return jsonify({
                "message": "Server configuration error: Gumloop saved_item_id not configured. Please set GUMLOOP_SAVED_ITEM_ID in your environment variables.",
                "status": "error"
            }), 500

        # Generate a unique run ID for this specific execution
        run_id = f"{int(time.time())}-{uuid.uuid4().hex[:8]}"

        # Process URL through Gumloop API first
        payload = {
            "user_id": os.getenv('GUMLOOP_USER_ID', 'P4NeNUZNmKR4t0s5K0K1Gn30EHz1'),
            "saved_item_id": GUMLOOP_SAVED_ITEM_ID,  # Use the configured saved_item_id
            "pipeline_inputs": [{"url": data['url']}]  # Pass the URL as an input
        }

        headers = {
            "Authorization": f"Bearer {gumloop_api_key}",
            "Content-Type": "application/json"
        }

        # Log the exact payload we're sending
        logger.debug(f"Sending payload to Gumloop API: {payload}")

        # Make request to Gumloop API with retry logic
        try:
            gumloop_response = session.post(
                "https://api.gumloop.com/api/v1/start_pipeline",
                json=payload,
                headers=headers,
                timeout=30
            )
            
            # Log the full response for debugging
            logger.debug(f"Gumloop API response status: {gumloop_response.status_code}")
            logger.debug(f"Gumloop API response headers: {dict(gumloop_response.headers)}")
            logger.debug(f"Gumloop API response body: {gumloop_response.text}")

            if gumloop_response.status_code != 200:
                error_msg = f"Error processing URL through Gumloop: {gumloop_response.text}"
                logger.error(error_msg)
                
                # Save to database even if Gumloop API fails
                saved_page = SavedPage(
                    title=data['title'],
                    url=data['url'],
                    gumloop_data={"error": gumloop_response.text},
                    saved_item_id=run_id  # Use run_id as the saved_item_id in our database
                )
                db.session.add(saved_page)
                db.session.commit()
                
                return jsonify({
                    "message": "Page saved but Gumloop processing failed. Please try again later.",
                    "status": "partial_success",
                    "error": error_msg,
                    "run_id": run_id
                }), 202

        except requests.exceptions.RequestException as e:
            logger.error(f"Request to Gumloop API failed: {str(e)}")
            # Save to database even if Gumloop API fails
            saved_page = SavedPage(
                title=data['title'],
                url=data['url'],
                gumloop_data={"error": str(e)},
                saved_item_id=run_id  # Use run_id as the saved_item_id in our database
            )
            db.session.add(saved_page)
            db.session.commit()
            
            return jsonify({
                "message": "Page saved but Gumloop processing failed. Please try again later.",
                "status": "partial_success",
                "error": str(e),
                "run_id": run_id
            }), 202

        # If we get here, Gumloop API call was successful
        saved_page = SavedPage(
            title=data['title'],
            url=data['url'],
            gumloop_data=gumloop_response.json(),
            saved_item_id=run_id  # Use run_id as the saved_item_id in our database
        )
        db.session.add(saved_page)
        db.session.commit()
        
        logger.info(f"Successfully processed and saved page: {saved_page.title}")
        
        return jsonify({
            "message": f"Successfully processed and saved page: {data['title']}",
            "status": "success",
            "gumloop_response": gumloop_response.json(),
            "run_id": run_id
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error saving page: {str(e)}", exc_info=True)
        return jsonify({
            "message": f"Error saving page: {str(e)}",
            "status": "error"
        }), 500

@app.route('/api/process-url', methods=['POST', 'OPTIONS'])
def process_url():
    logger.debug(f"Received {request.method} request to /api/process-url")
    
    # Handle preflight request
    if request.method == 'OPTIONS':
        return '', 200

    try:
        data = request.get_json()
        logger.debug(f"Received data: {data}")
        
        if not data or 'url' not in data:
            logger.error("Missing required url field in request data")
            return jsonify({
                "message": "Missing required field: url",
                "status": "error"
            }), 400

        # Get Gumloop API key from environment variable
        gumloop_api_key = os.getenv('GUMLOOP_API_KEY')
        if not gumloop_api_key:
            logger.error("Gumloop API key not found in environment variables")
            return jsonify({
                "message": "Server configuration error: Gumloop API key not found",
                "status": "error"
            }), 500

        # Prepare payload for Gumloop API
        payload = {
            "user_id": os.getenv('GUMLOOP_USER_ID', 'P4NeNUZNmKR4t0s5K0K1Gn30EHz1'),
            "saved_item_id": data.get('saved_item_id', ''),
            "pipeline_inputs": [{"url": data['url']}]
        }

        headers = {
            "Authorization": f"Bearer {gumloop_api_key}",
            "Content-Type": "application/json"
        }

        # Make request to Gumloop API
        response = requests.post(
            "https://api.gumloop.com/api/v1/start_pipeline",
            json=payload,
            headers=headers
        )

        if response.status_code != 200:
            logger.error(f"Gumloop API error: {response.text}")
            return jsonify({
                "message": f"Error processing URL: {response.text}",
                "status": "error"
            }), response.status_code

        # Save to our database
        saved_page = SavedPage(
            title=data.get('title', 'Untitled'),
            url=data['url']
        )
        db.session.add(saved_page)
        db.session.commit()
        
        logger.info(f"Successfully processed and saved URL: {data['url']}")
        
        return jsonify({
            "message": "Successfully processed URL",
            "status": "success",
            "gumloop_response": response.json()
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error processing URL: {str(e)}", exc_info=True)
        return jsonify({
            "message": f"Error processing URL: {str(e)}",
            "status": "error"
        }), 500

@app.route('/')
def index():
    # Get all saved pages, ordered by most recent first
    saved_pages = SavedPage.query.order_by(SavedPage.id.desc()).all()
    return render_template('index.html', saved_pages=saved_pages)

@app.route('/page/<int:page_id>')
def page_detail(page_id):
    page = SavedPage.query.get_or_404(page_id)
    return render_template('page_detail.html', page=page)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)

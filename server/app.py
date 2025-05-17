from flask import Flask, jsonify, request
from flask_cors import CORS
from App.routes import main_bp
from App.models import db, SavedPage
import os
import logging
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

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

        saved_page = SavedPage(
            title=data['title'],
            url=data['url']
        )
        db.session.add(saved_page)
        db.session.commit()
        
        logger.info(f"Successfully saved page: {saved_page.title}")
        
        return jsonify({
            "message": f"Successfully saved page: {data['title']}",
            "status": "success"
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

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)

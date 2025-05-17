from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
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

# Function to fetch extraction results from Gumloop
def fetch_gumloop_extraction(run_id):
    """
    Fetch extraction results from Gumloop using the run_id
    """
    gumloop_api_key = os.getenv('GUMLOOP_API_KEY')
    if not gumloop_api_key:
        logger.error("Gumloop API key not found in environment variables")
        return {"error": "Gumloop API key not configured"}
        
    try:
        # Set the headers with authorization
        headers = {
            "Authorization": f"Bearer {gumloop_api_key}",
            "Content-Type": "application/json"
        }
        
        # According to documentation, use the get_pl_run endpoint
        url = "https://api.gumloop.com/api/v1/get_pl_run"
        
        # Add query parameters for run_id and user_id
        params = {
            "run_id": run_id,
            "user_id": os.getenv('GUMLOOP_USER_ID', 'P4NeNUZNmKR4t0s5K0K1Gn30EHz1')
        }
        
        logger.debug(f"Fetching run details from: {url} with run_id: {run_id}")
        
        # Add a small delay to ensure the flow has time to complete
        time.sleep(5)
        
        # Get the results
        response = session.get(url, headers=headers, params=params, timeout=30)
        
        if response.status_code != 200:
            logger.error(f"Error fetching run details: {response.status_code} - {response.text}")
            
            # Create a fallback result with the pipeline URL
            workbook_id = os.getenv('GUMLOOP_WORKBOOK_ID', 'rFq6sXjr3aowj4vEJvoWE6')
            pipeline_url = f"https://www.gumloop.com/pipeline?run_id={run_id}&workbook_id={workbook_id}"
            return {
                "run_id": run_id,
                "extraction_url": pipeline_url,
                "message": "Could not fetch extraction results automatically. View the full results by clicking the link above.",
                "error": response.text
            }
            
        # Parse the results
        result_data = response.json()
        logger.debug(f"Successfully fetched run details: {result_data}")
        
        # Build a formatted extraction url with workbook_id
        workbook_id = os.getenv('GUMLOOP_WORKBOOK_ID', 'rFq6sXjr3aowj4vEJvoWE6')
        pipeline_url = f"https://www.gumloop.com/pipeline?run_id={run_id}&workbook_id={workbook_id}"
        
        # Extract website content from outputs if available
        website_content = None
        outputs = result_data.get("outputs", {})
        
        # Log all available output keys to help debug
        logger.debug(f"Available output keys: {list(outputs.keys())}")
        
        # Check for common output field names used by Gumloop for website content
        if "output" in outputs:
            logger.debug("Found 'output' field in outputs")
            website_content = outputs["output"]
        elif "Website Content" in outputs:
            logger.debug("Found 'Website Content' field in outputs")
            website_content = outputs["Website Content"]
        elif "text" in outputs:
            logger.debug("Found 'text' field in outputs")
            website_content = outputs["text"]
        elif "content" in outputs:
            logger.debug("Found 'content' field in outputs")
            website_content = outputs["content"]
        elif "extracted_content" in outputs:
            logger.debug("Found 'extracted_content' field in outputs")
            website_content = outputs["extracted_content"]
        elif "html" in outputs:
            logger.debug("Found 'html' field in outputs")
            website_content = outputs["html"]
        
        if website_content:
            logger.debug(f"Extracted website content (first 100 chars): {website_content[:100]}...")
        else:
            logger.warning("No website content found in outputs")
        
        # Package all the data together for the template
        return {
            "run_id": run_id,
            "extraction_url": pipeline_url,
            "message": "Successfully retrieved extraction results.",
            "run_details": result_data,
            "outputs": outputs,
            "website_content": website_content,  # Explicitly include the website content
            "state": result_data.get("state", "UNKNOWN"),
            "logs": result_data.get("log", [])
        }
            
    except Exception as e:
        logger.error(f"Exception while fetching extraction results: {str(e)}")
        # Create a fallback with the pipeline URL
        workbook_id = os.getenv('GUMLOOP_WORKBOOK_ID', 'rFq6sXjr3aowj4vEJvoWE6')
        pipeline_url = f"https://www.gumloop.com/pipeline?run_id={run_id}&workbook_id={workbook_id}"
        return {
            "run_id": run_id,
            "extraction_url": pipeline_url,
            "error": str(e),
            "message": "Error fetching extraction results. View directly on Gumloop."
        }

def create_app():
    app = Flask(__name__, 
        template_folder='App/templates',
        static_folder='App/static'
    )

    # Configure SQLite database
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///saved_pages.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Add the fetch_gumloop_extraction function to app config so it can be accessed from views
    app.config['fetch_gumloop_extraction'] = fetch_gumloop_extraction

    # Simple CORS configuration
    CORS(app)

    # Import models and initialize db
    from App.models import db
    db.init_app(app)

    # Create database tables
    with app.app_context():
        db.create_all()
        logger.info("Database tables created")

    # Import and register blueprints
    from App.routes import main_bp
    app.register_blueprint(main_bp)

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

            # Process URL through Gumloop API following the specified structure
            payload = {
                "user_id": os.getenv('GUMLOOP_USER_ID', 'P4NeNUZNmKR4t0s5K0K1Gn30EHz1'),
                "saved_item_id": GUMLOOP_SAVED_ITEM_ID,
                "pipeline_inputs": [
                    {"input_name": "url", "value": data['url']}
                ]
            }

            headers = {
                "Authorization": f"Bearer {gumloop_api_key}",
                "Content-Type": "application/json"
            }

            # Log the exact payload we're sending
            logger.debug(f"Sending payload to Gumloop API: {payload}")

            # Import SavedPage here to avoid circular imports
            from App.models import SavedPage

            # Make request to Gumloop API to start the pipeline
            try:
                start_response = session.post(
                    "https://api.gumloop.com/api/v1/start_pipeline",
                    json=payload,
                    headers=headers,
                    timeout=30
                )
                
                # Log the full response for debugging
                logger.debug(f"Gumloop API response status: {start_response.status_code}")
                logger.debug(f"Gumloop API response headers: {dict(start_response.headers)}")
                logger.debug(f"Gumloop API response body: {start_response.text}")

                if start_response.status_code != 200:
                    error_msg = f"Error processing URL through Gumloop: {start_response.text}"
                    logger.error(error_msg)
                    
                    # Generate a fallback ID
                    fallback_id = f"{int(time.time())}-{uuid.uuid4().hex[:8]}"
                    
                    # Save to database even if Gumloop API fails
                    saved_page = SavedPage(
                        title=data['title'],
                        url=data['url'],
                        gumloop_data={"error": start_response.text},
                        saved_item_id=fallback_id
                    )
                    db.session.add(saved_page)
                    db.session.commit()
                    
                    return jsonify({
                        "message": "Page saved but Gumloop processing failed. Please try again later.",
                        "status": "partial_success",
                        "error": error_msg,
                        "run_id": fallback_id
                    }), 202
                
                # Get the run_id from the response
                start_data = start_response.json()
                run_id = start_data.get('run_id')
                
                if not run_id:
                    logger.error("No run_id found in Gumloop response")
                    fallback_id = f"{int(time.time())}-{uuid.uuid4().hex[:8]}"
                    
                    saved_page = SavedPage(
                        title=data['title'],
                        url=data['url'],
                        gumloop_data=start_data,
                        saved_item_id=fallback_id
                    )
                    db.session.add(saved_page)
                    db.session.commit()
                    
                    return jsonify({
                        "message": "Page saved but no run_id found. Please try again later.",
                        "status": "partial_success",
                        "gumloop_response": start_data,
                        "run_id": fallback_id
                    }), 202
                
                # Fetch the results immediately (may need to poll if not ready)
                # Wait a moment for the pipeline to start processing
                time.sleep(2)
                
                # Set up parameters for the GET request
                get_params = {
                    "run_id": run_id,
                    "user_id": os.getenv('GUMLOOP_USER_ID', 'P4NeNUZNmKR4t0s5K0K1Gn30EHz1')
                }
                
                # Maximum number of polling attempts
                max_attempts = 10
                # Delay between polling attempts (in seconds)
                polling_delay = 2
                
                # Initialize variables
                result_data = None
                final_state = "UNKNOWN"
                
                # Poll until the run is completed or max attempts are reached
                for attempt in range(max_attempts):
                    logger.debug(f"Fetching run details, attempt {attempt+1}/{max_attempts}")
                    
                    get_response = session.get(
                        "https://api.gumloop.com/api/v1/get_pl_run",
                        headers=headers,
                        params=get_params,
                        timeout=30
                    )
                    
                    if get_response.status_code != 200:
                        logger.warning(f"Error fetching run details: {get_response.status_code} - {get_response.text}")
                        time.sleep(polling_delay)
                        continue
                    
                    result_data = get_response.json()
                    final_state = result_data.get("state", "UNKNOWN")
                    
                    # If the run is completed or failed, stop polling
                    if final_state in ["DONE", "FAILED", "TERMINATED"]:
                        logger.debug(f"Run complete with state: {final_state}")
                        break
                    
                    # Wait before the next polling attempt
                    time.sleep(polling_delay)
                
                # If we didn't get results or the run didn't complete successfully
                if not result_data or final_state != "DONE":
                    logger.warning(f"Run did not complete successfully. Final state: {final_state}")
                    
                    # Save to database
                    saved_page = SavedPage(
                        title=data['title'],
                        url=data['url'],
                        gumloop_data=start_data,
                        saved_item_id=run_id
                    )
                    db.session.add(saved_page)
                    db.session.commit()
                    
                    return jsonify({
                        "message": f"Page saved but processing not completed. Final state: {final_state}",
                        "status": "partial_success",
                        "gumloop_response": start_data,
                        "run_id": run_id,
                        "state": final_state
                    }), 202
                
                # Extract website content from outputs if available
                website_content = None
                outputs = result_data.get("outputs", {})
                
                # Build a formatted extraction url with workbook_id
                workbook_id = os.getenv('GUMLOOP_WORKBOOK_ID', 'rFq6sXjr3aowj4vEJvoWE6')
                pipeline_url = f"https://www.gumloop.com/pipeline?run_id={run_id}&workbook_id={workbook_id}"
                
                # Check for common output field names used by Gumloop for website content
                if "Website Content" in outputs:
                    website_content = outputs["Website Content"]
                elif "output" in outputs:
                    website_content = outputs["output"]
                elif "text" in outputs:
                    website_content = outputs["text"]
                elif "content" in outputs:
                    website_content = outputs["content"]
                elif "extracted_content" in outputs:
                    website_content = outputs["extracted_content"]
                elif "html" in outputs:
                    website_content = outputs["html"]
                
                # Save to database with the complete data
                saved_page = SavedPage(
                    title=data['title'],
                    url=data['url'],
                    gumloop_data=result_data,
                    saved_item_id=run_id
                )
                db.session.add(saved_page)
                db.session.commit()
                
                logger.info(f"Successfully processed and saved page: {saved_page.title}")
                
                # Return the complete response including the website content
                return jsonify({
                    "message": f"Successfully processed and saved page: {data['title']}",
                    "status": "success",
                    "run_id": run_id,
                    "website_content": website_content,
                    "extraction_url": pipeline_url,
                    "state": final_state,
                    "logs": result_data.get("log", [])
                })

            except requests.exceptions.RequestException as e:
                logger.error(f"Request to Gumloop API failed: {str(e)}")
                
                # Generate a fallback ID
                fallback_id = f"{int(time.time())}-{uuid.uuid4().hex[:8]}"
                
                # Save to database even if Gumloop API fails
                saved_page = SavedPage(
                    title=data['title'],
                    url=data['url'],
                    gumloop_data={"error": str(e)},
                    saved_item_id=fallback_id
                )
                db.session.add(saved_page)
                db.session.commit()
                
                return jsonify({
                    "message": "Page saved but Gumloop processing failed. Please try again later.",
                    "status": "partial_success",
                    "error": str(e),
                    "run_id": fallback_id
                }), 202

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
            saved_item_id = data.get('saved_item_id', GUMLOOP_SAVED_ITEM_ID)
            if not saved_item_id:
                logger.error("No saved_item_id provided or configured")
                return jsonify({
                    "message": "No saved_item_id provided or configured. Please set GUMLOOP_SAVED_ITEM_ID in environment variables or provide it in the request.",
                    "status": "error"
                }), 400
                
            payload = {
                "user_id": os.getenv('GUMLOOP_USER_ID', 'P4NeNUZNmKR4t0s5K0K1Gn30EHz1'),
                "saved_item_id": saved_item_id,
                "pipeline_inputs": [
                    {"input_name": "url", "value": data['url']}
                ]
            }
            
            headers = {
                "Authorization": f"Bearer {gumloop_api_key}",
                "Content-Type": "application/json"
            }
            
            logger.debug(f"Sending payload to Gumloop API: {payload}")

            # Import SavedPage here to avoid circular imports
            from App.models import SavedPage

            # Make request to Gumloop API to start the pipeline
            try:
                start_response = session.post(
                    "https://api.gumloop.com/api/v1/start_pipeline",
                    json=payload,
                    headers=headers,
                    timeout=30
                )
                
                # Log the response
                logger.debug(f"Start pipeline response: {start_response.status_code} - {start_response.text}")
                
                if start_response.status_code != 200:
                    error_msg = f"Error processing URL through Gumloop: {start_response.text}"
                    logger.error(error_msg)
                    return jsonify({
                        "message": error_msg,
                        "status": "error"
                    }), start_response.status_code
                
                # Get the run_id from the response
                start_data = start_response.json()
                run_id = start_data.get('run_id')
                
                if not run_id:
                    logger.error("No run_id found in Gumloop response")
                    return jsonify({
                        "message": "No run_id found in Gumloop response. Please try again later.",
                        "status": "error",
                        "gumloop_response": start_data
                    }), 500
                
                # Fetch the results immediately (may need to poll if not ready)
                # Wait a moment for the pipeline to start processing
                time.sleep(2)
                
                # Set up parameters for the GET request
                get_params = {
                    "run_id": run_id,
                    "user_id": os.getenv('GUMLOOP_USER_ID', 'P4NeNUZNmKR4t0s5K0K1Gn30EHz1')
                }
                
                # Maximum number of polling attempts
                max_attempts = 10
                # Delay between polling attempts (in seconds)
                polling_delay = 2
                
                # Initialize variables
                result_data = None
                final_state = "UNKNOWN"
                
                # Poll until the run is completed or max attempts are reached
                for attempt in range(max_attempts):
                    logger.debug(f"Fetching run details, attempt {attempt+1}/{max_attempts}")
                    
                    get_response = session.get(
                        "https://api.gumloop.com/api/v1/get_pl_run",
                        headers=headers,
                        params=get_params,
                        timeout=30
                    )
                    
                    if get_response.status_code != 200:
                        logger.warning(f"Error fetching run details: {get_response.status_code} - {get_response.text}")
                        time.sleep(polling_delay)
                        continue
                    
                    result_data = get_response.json()
                    final_state = result_data.get("state", "UNKNOWN")
                    
                    # If the run is completed or failed, stop polling
                    if final_state in ["DONE", "FAILED", "TERMINATED"]:
                        logger.debug(f"Run complete with state: {final_state}")
                        break
                    
                    # Wait before the next polling attempt
                    time.sleep(polling_delay)
                
                # If we didn't get results or the run didn't complete successfully
                if not result_data or final_state != "DONE":
                    logger.warning(f"Run did not complete successfully. Final state: {final_state}")
                    
                    # Save to database
                    saved_page = SavedPage(
                        title=data.get('title', 'Untitled'),
                        url=data['url'],
                        gumloop_data=start_data,
                        saved_item_id=run_id
                    )
                    db.session.add(saved_page)
                    db.session.commit()
                    
                    return jsonify({
                        "message": f"Processing not completed. Final state: {final_state}",
                        "status": "partial_success",
                        "gumloop_response": start_data,
                        "run_id": run_id,
                        "state": final_state
                    }), 202
                
                # Extract website content from outputs if available
                website_content = None
                outputs = result_data.get("outputs", {})
                
                # Build a formatted extraction url with workbook_id
                workbook_id = os.getenv('GUMLOOP_WORKBOOK_ID', 'rFq6sXjr3aowj4vEJvoWE6')
                pipeline_url = f"https://www.gumloop.com/pipeline?run_id={run_id}&workbook_id={workbook_id}"
                
                # Check for common output field names used by Gumloop for website content
                if "Website Content" in outputs:
                    website_content = outputs["Website Content"]
                elif "output" in outputs:
                    website_content = outputs["output"]
                elif "text" in outputs:
                    website_content = outputs["text"]
                elif "content" in outputs:
                    website_content = outputs["content"]
                elif "extracted_content" in outputs:
                    website_content = outputs["extracted_content"]
                elif "html" in outputs:
                    website_content = outputs["html"]
                
                # Save to database with the complete data
                saved_page = SavedPage(
                    title=data.get('title', 'Untitled'),
                    url=data['url'],
                    gumloop_data=result_data,
                    saved_item_id=run_id
                )
                db.session.add(saved_page)
                db.session.commit()
                
                logger.info(f"Successfully processed URL: {data['url']}")
                
                # Return the complete response including the website content
                return jsonify({
                    "message": "Successfully processed URL",
                    "status": "success",
                    "run_id": run_id,
                    "website_content": website_content,
                    "extraction_url": pipeline_url,
                    "state": final_state,
                    "logs": result_data.get("log", [])
                })
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Request to Gumloop API failed: {str(e)}")
                return jsonify({
                    "message": f"Error processing URL: {str(e)}",
                    "status": "error"
                }), 500

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error processing URL: {str(e)}", exc_info=True)
            return jsonify({
                "message": f"Error processing URL: {str(e)}",
                "status": "error"
            }), 500

    @app.route('/api/mcp-search', methods=['POST', 'OPTIONS'])
    def mcp_search():
        """
        Endpoint to handle MCP search requests from the extension
        """
        # Handle preflight request
        if request.method == 'OPTIONS':
            return '', 200
        
        try:
            data = request.get_json()
            if not data or 'query' not in data:
                return jsonify({
                    "error": "Missing query parameter"
                }), 400
            
            query = data['query']
            logger.debug(f"Received search query: {query}")
            
            # Check if the request specifies using conversational search
            use_conversational = data.get('conversational', True)  # Default to conversational search
            
            if use_conversational:
                # Import the conversational search function from mcp_server
                from mcp_server import conversational_search, claude_client
                
                # Check if Claude client is available
                if not claude_client:
                    logger.warning("Anthropic Claude client not available. Falling back to basic search.")
                    from mcp_server import search_database
                    results = search_database(query)
                else:
                    # Perform conversational search
                    response = conversational_search(query)
                    return jsonify({
                        "results": {
                            "message": "Conversational search results",
                            "items": [],  # Empty since we're returning direct text response
                            "conversational_response": response
                        },
                        "status": "success"
                    })
            else:
                # Use basic search as fallback
                from mcp_server import search_database
                results = search_database(query)
            
            return jsonify({
                "results": results,
                "status": "success"
            })
        
        except Exception as e:
            logger.error(f"Error during MCP search: {str(e)}")
            return jsonify({
                "error": f"Search failed: {str(e)}",
                "status": "error"
            }), 500

    @app.route('/create-event/<int:page_id>', methods=['GET'])
    def create_event_page(page_id):
        """
        Display a page for creating calendar events from saved content
        """
        try:
            # Get the page from the database
            from App.models import SavedPage
            page = SavedPage.query.get_or_404(page_id)
            
            # Import the date extraction function from mcp_server
            from mcp_server import extract_dates
            
            # Extract potential dates from content
            content_text = ""
            if isinstance(page.gumloop_data, dict):
                for key in ['website_content', 'output', 'content', 'extracted_content', 'text']:
                    if key in page.gumloop_data and page.gumloop_data[key]:
                        content_text = page.gumloop_data[key]
                        break
            else:
                content_text = str(page.gumloop_data) if page.gumloop_data else ""
            
            # If no content, show message
            if not content_text:
                return render_template('create_event.html', 
                                      page=page, 
                                      dates=[], 
                                      error="No content found for this page.")
            
            # Extract dates
            dates = extract_dates(content_text)
            
            # Render the event creation page
            return render_template('create_event.html', 
                                  page=page, 
                                  dates=dates, 
                                  error=None)
        
        except Exception as e:
            logger.error(f"Error displaying event creation page: {str(e)}")
            return render_template('error.html', 
                                  message=f"Failed to load event creation page: {str(e)}")

    @app.route('/api/create-event', methods=['POST', 'OPTIONS'])
    def create_event_api():
        """
        API endpoint to create a calendar event or email invitation
        """
        # Handle preflight request
        if request.method == 'OPTIONS':
            return '', 200
        
        try:
            data = request.get_json()
            
            if not data or 'event_title' not in data or 'event_date' not in data:
                return jsonify({
                    "error": "Missing required parameters: event_title and event_date",
                    "status": "error"
                }), 400
            
            # Get the method (calendar or email)
            method = data.get('method', 'calendar')
            
            # Create event or send email
            if method == 'calendar':
                from mcp_server import create_calendar_event
                event_details = {
                    'title': data['event_title'],
                    'description': data.get('description', ''),
                    'start_time': data['event_date'] + ' ' + data.get('start_time', '09:00'),
                    'end_time': data['event_date'] + ' ' + data.get('end_time', '10:00')
                }
                result = create_calendar_event(event_details)
            else:
                from mcp_server import send_email_invitation
                event_details = {
                    'title': data['event_title'],
                    'description': data.get('description', ''),
                    'start_time': data['event_date'] + ' ' + data.get('start_time', '09:00'),
                    'end_time': data['event_date'] + ' ' + data.get('end_time', '10:00'),
                    'recipient': data.get('recipient', '')
                }
                result = send_email_invitation(event_details)
            
            if result.get('success', False):
                return jsonify({
                    "message": result.get('message', 'Event created successfully'),
                    "status": "success"
                })
            else:
                return jsonify({
                    "error": result.get('error', 'Failed to create event'),
                    "status": "error"
                }), 400
        
        except Exception as e:
            logger.error(f"Error creating event: {str(e)}")
            return jsonify({
                "error": f"Failed to create event: {str(e)}",
                "status": "error"
            }), 500

    return app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)

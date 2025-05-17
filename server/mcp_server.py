#!/usr/bin/env python3
import os
import json
import logging
from datetime import datetime
import re
from modelcontextprotocol import Server, InputSchema, ContentBlock
import googleapiclient.discovery
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle
from dateutil import parser
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database access function
def search_database(query):
    """
    Search the database for saved pages matching the query
    """
    from app import create_app
    from App.models import SavedPage
    
    app = create_app()
    
    with app.app_context():
        # Perform a simple search across title and content
        results = SavedPage.query.filter(
            (SavedPage.title.like(f'%{query}%')) | 
            (SavedPage.gumloop_data.like(f'%{query}%'))
        ).all()
        
        if not results:
            return {"message": "No results found", "items": []}
        
        # Format results
        formatted_results = []
        for page in results:
            formatted_results.append({
                "id": page.id,
                "title": page.title,
                "url": page.url,
                "saved_at": page.saved_at.strftime('%Y-%m-%d %H:%M:%S'),
                "content_snippet": extract_content_snippet(page.gumloop_data, query) if page.gumloop_data else None
            })
        
        return {"message": f"Found {len(results)} results", "items": formatted_results}

def extract_content_snippet(content, query, max_length=200):
    """
    Extract a relevant snippet from content containing the query
    """
    if not content:
        return None
    
    # For JSON content, extract text data
    if isinstance(content, dict):
        # Try to get website_content or similar fields
        text_content = None
        for key in ['website_content', 'output', 'content', 'extracted_content', 'text']:
            if key in content and content[key]:
                text_content = content[key]
                break
        
        if not text_content:
            # If no specific content field, convert dict to string
            text_content = json.dumps(content)
    else:
        text_content = str(content)
    
    # Find query position
    query_pos = text_content.lower().find(query.lower())
    
    if query_pos == -1:
        # Query not found in content, return start of content
        return text_content[:max_length] + "..."
    
    # Calculate snippet start and end positions
    start_pos = max(0, query_pos - (max_length // 2))
    end_pos = min(len(text_content), start_pos + max_length)
    
    # Adjust start position if we're near the end
    if end_pos == len(text_content):
        start_pos = max(0, end_pos - max_length)
    
    # Create snippet
    snippet = text_content[start_pos:end_pos]
    
    # Add ellipsis if needed
    if start_pos > 0:
        snippet = "..." + snippet
    if end_pos < len(text_content):
        snippet = snippet + "..."
    
    return snippet

def extract_dates(text):
    """
    Extract potential event dates from text content
    """
    # Define patterns for date formats
    date_patterns = [
        r'\b\d{1,2}/\d{1,2}/\d{2,4}\b',  # MM/DD/YYYY
        r'\b\d{1,2}-\d{1,2}-\d{2,4}\b',  # MM-DD-YYYY
        r'\b\d{4}-\d{1,2}-\d{1,2}\b',    # YYYY-MM-DD
        r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b',  # Month DD, YYYY
        r'\b\d{1,2}\s+(January|February|March|April|May|June|July|August|September|October|November|December),?\s+\d{4}\b',  # DD Month YYYY
    ]
    
    # Find all dates in text
    dates = []
    for pattern in date_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            for match in matches:
                try:
                    parsed_date = parser.parse(match if isinstance(match, str) else " ".join(match))
                    dates.append({
                        "text": match if isinstance(match, str) else " ".join(match),
                        "date": parsed_date,
                        "context": extract_context(text, match if isinstance(match, str) else " ".join(match))
                    })
                except:
                    pass  # Skip dates that can't be parsed
    
    return dates

def extract_context(text, date_str, context_length=100):
    """
    Extract text context around a date
    """
    date_pos = text.find(date_str)
    if date_pos == -1:
        return ""
    
    start_pos = max(0, date_pos - context_length)
    end_pos = min(len(text), date_pos + len(date_str) + context_length)
    
    context = text[start_pos:end_pos]
    if start_pos > 0:
        context = "..." + context
    if end_pos < len(text):
        context = context + "..."
    
    return context

def create_calendar_event(event_details):
    """
    Create a Google Calendar event
    """
    # Google Calendar API setup
    SCOPES = ['https://www.googleapis.com/auth/calendar']
    creds = None
    token_path = 'token.pickle'
    credentials_path = 'credentials.json'
    
    # Check if token exists
    if os.path.exists(token_path):
        with open(token_path, 'rb') as token:
            creds = pickle.load(token)
            
    # If no credentials or they're invalid, get new ones
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        elif os.path.exists(credentials_path):
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
            creds = flow.run_local_server(port=0)
        else:
            return {"error": "No Google Calendar credentials found. Please set up credentials.json."}
            
        # Save credentials
        with open(token_path, 'wb') as token:
            pickle.dump(creds, token)
    
    # Create calendar service
    service = googleapiclient.discovery.build('calendar', 'v3', credentials=creds)
    
    # Create event
    event = {
        'summary': event_details.get('title', 'Event from SecondBrain'),
        'description': event_details.get('description', ''),
        'start': {
            'dateTime': event_details['start_time'].isoformat(),
            'timeZone': 'America/Los_Angeles',  # Default timezone
        },
        'end': {
            'dateTime': event_details['end_time'].isoformat(),
            'timeZone': 'America/Los_Angeles',
        },
    }
    
    # Add event
    try:
        event = service.events().insert(calendarId='primary', body=event).execute()
        return {
            "success": True,
            "message": f"Event created: {event.get('htmlLink')}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

def send_email_invitation(event_details):
    """
    Send an email invitation for an event
    """
    # Email configuration
    smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
    smtp_port = int(os.getenv('SMTP_PORT', 587))
    smtp_username = os.getenv('SMTP_USERNAME')
    smtp_password = os.getenv('SMTP_PASSWORD')
    
    if not smtp_username or not smtp_password:
        return {"error": "Email credentials not configured. Set SMTP_USERNAME and SMTP_PASSWORD."}
    
    # Create message
    msg = MIMEMultipart()
    msg['Subject'] = event_details.get('title', 'Event Invitation from SecondBrain')
    msg['From'] = smtp_username
    msg['To'] = event_details.get('recipient', smtp_username)
    
    # Format email body
    body = f"""
    <html>
    <body>
        <h2>{event_details.get('title', 'Event Invitation')}</h2>
        <p><strong>Date:</strong> {event_details['start_time'].strftime('%Y-%m-%d')}</p>
        <p><strong>Time:</strong> {event_details['start_time'].strftime('%H:%M')} - {event_details['end_time'].strftime('%H:%M')}</p>
        <p>{event_details.get('description', '')}</p>
    </body>
    </html>
    """
    
    msg.attach(MIMEText(body, 'html'))
    
    # Send email
    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_username, smtp_password)
        server.send_message(msg)
        server.quit()
        
        return {
            "success": True,
            "message": f"Invitation sent to {event_details.get('recipient', smtp_username)}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

# Define MCP server schema
SEARCH_TOOL = {
    "name": "search_secondbrain",
    "description": "Search through saved pages in the SecondBrain database",
    "inputSchema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query to find saved pages"
            }
        },
        "required": ["query"]
    }
}

EVENT_TOOL = {
    "name": "create_event",
    "description": "Create a calendar event or send an email invitation for an event found in content",
    "inputSchema": {
        "type": "object",
        "properties": {
            "content_id": {
                "type": "integer",
                "description": "ID of the saved page containing event information"
            },
            "event_title": {
                "type": "string",
                "description": "Title of the event"
            },
            "event_date": {
                "type": "string",
                "description": "Date of the event in YYYY-MM-DD format"
            },
            "start_time": {
                "type": "string",
                "description": "Start time of the event in HH:MM format"
            },
            "end_time": {
                "type": "string",
                "description": "End time of the event in HH:MM format"
            },
            "description": {
                "type": "string",
                "description": "Description of the event"
            },
            "method": {
                "type": "string",
                "description": "How to create the invitation: 'calendar' for Google Calendar or 'email' for email invitation",
                "enum": ["calendar", "email"]
            },
            "recipient": {
                "type": "string",
                "description": "Email recipient for email invitations"
            }
        },
        "required": ["event_title", "event_date", "method"]
    }
}

def run_mcp_server():
    """
    Start the MCP server
    """
    server = Server("SecondBrain MCP Server")
    
    @server.on_list_tools
    def handle_list_tools():
        return {"tools": [SEARCH_TOOL, EVENT_TOOL]}
    
    @server.on_call_tool
    def handle_call_tool(request):
        if request.tool_name == "search_secondbrain":
            query = request.args.get("query")
            if not query:
                return {
                    "content": [{"type": "text", "text": "Please provide a search query"}],
                    "isError": True
                }
            
            results = search_database(query)
            
            # Format response
            formatted_results = f"Found {len(results['items'])} results for query: {query}\n\n"
            
            for item in results['items']:
                formatted_results += f"Title: {item['title']}\n"
                formatted_results += f"URL: {item['url']}\n"
                formatted_results += f"Saved: {item['saved_at']}\n"
                if item['content_snippet']:
                    formatted_results += f"Content: {item['content_snippet']}\n"
                formatted_results += f"ID: {item['id']}\n\n"
            
            return {
                "content": [{"type": "text", "text": formatted_results}],
                "isError": False
            }
            
        elif request.tool_name == "create_event":
            content_id = request.args.get("content_id")
            if content_id:
                # Fetch the content from the database
                from app import create_app
                from App.models import SavedPage
                
                app = create_app()
                
                with app.app_context():
                    page = SavedPage.query.get(content_id)
                    if not page or not page.gumloop_data:
                        return {
                            "content": [{"type": "text", "text": f"Content with ID {content_id} not found or has no content"}],
                            "isError": True
                        }
                    
                    # Extract text from gumloop_data
                    content_text = ""
                    if isinstance(page.gumloop_data, dict):
                        for key in ['website_content', 'output', 'content', 'extracted_content', 'text']:
                            if key in page.gumloop_data and page.gumloop_data[key]:
                                content_text = page.gumloop_data[key]
                                break
                    else:
                        content_text = str(page.gumloop_data)
                    
                    # Extract dates
                    dates = extract_dates(content_text)
                    if not dates:
                        return {
                            "content": [{"type": "text", "text": "No dates found in the content"}],
                            "isError": True
                        }
                    
                    # Format found dates
                    date_info = "Found potential event dates:\n\n"
                    for i, date_obj in enumerate(dates):
                        date_info += f"{i+1}. {date_obj['text']} - Context: {date_obj['context']}\n"
                    
                    return {
                        "content": [{"type": "text", "text": date_info}],
                        "isError": False
                    }
            
            # Create event from provided details
            event_title = request.args.get("event_title")
            event_date = request.args.get("event_date")
            start_time = request.args.get("start_time", "09:00")
            end_time = request.args.get("end_time", "10:00")
            description = request.args.get("description", "")
            method = request.args.get("method", "calendar")
            recipient = request.args.get("recipient", "")
            
            if not event_title or not event_date:
                return {
                    "content": [{"type": "text", "text": "Please provide an event title and date"}],
                    "isError": True
                }
            
            # Parse date and times
            try:
                start_datetime = parser.parse(f"{event_date} {start_time}")
                end_datetime = parser.parse(f"{event_date} {end_time}")
            except:
                return {
                    "content": [{"type": "text", "text": "Invalid date or time format"}],
                    "isError": True
                }
            
            # Create event details
            event_details = {
                "title": event_title,
                "description": description,
                "start_time": start_datetime,
                "end_time": end_datetime,
                "recipient": recipient
            }
            
            # Create calendar event or send email
            if method == "calendar":
                result = create_calendar_event(event_details)
            else:
                result = send_email_invitation(event_details)
            
            if result.get("success", False):
                return {
                    "content": [{"type": "text", "text": result.get("message", "Event created successfully")}],
                    "isError": False
                }
            else:
                return {
                    "content": [{"type": "text", "text": f"Error: {result.get('error', 'Unknown error')}"}],
                    "isError": True
                }
    
    # Start the server
    server.run()

if __name__ == "__main__":
    run_mcp_server() 
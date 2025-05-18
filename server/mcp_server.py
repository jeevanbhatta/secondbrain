#!/usr/bin/env python3
import os
import json
import logging
from datetime import datetime
import re
from mcp.server.fastmcp import FastMCP
import googleapiclient.discovery
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle
from dateutil import parser
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import anthropic
from typing import List, Dict, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Anthropic client
try:
    # Try to get API key from environment variable
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if api_key:
        claude_client = anthropic.Anthropic(api_key=api_key)
        logger.info("Anthropic client initialized successfully")
    else:
        logger.warning("ANTHROPIC_API_KEY not found in environment variables. LLM search will not be available.")
        claude_client = None
except Exception as e:
    logger.error(f"Error initializing Anthropic client: {e}")
    claude_client = None

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

# Function to get all saved pages
def get_all_saved_pages():
    """
    Get all saved pages from the database
    """
    from app import create_app
    from App.models import SavedPage
    
    app = create_app()
    
    with app.app_context():
        pages = SavedPage.query.all()
        
        # Format results
        formatted_pages = []
        for page in pages:
            # Extract important content for context
            content_text = extract_text_content(page.gumloop_data)
            formatted_pages.append({
                "id": page.id,
                "title": page.title,
                "url": page.url,
                "saved_at": page.saved_at.strftime('%Y-%m-%d %H:%M:%S'),
                "content_text": content_text[:5000] if content_text else None  # Limit content size
            })
        
        return formatted_pages

def extract_text_content(content) -> str:
    """
    Extract text content from a potentially nested JSON structure
    """
    if not content:
        return ""
    
    # If content is already a string, return it
    if isinstance(content, str):
        return content
    
    # If content is a dict, try to extract text from known fields
    if isinstance(content, dict):
        # First try common content fields
        for key in ['website_content', 'output', 'content', 'extracted_content', 'text']:
            if key in content and content[key]:
                # Recursive call in case the value is also a dict
                return extract_text_content(content[key])
        
        # If no specific field found, try to concatenate all string values
        text_parts = []
        for key, value in content.items():
            if isinstance(value, str):
                text_parts.append(value)
            elif isinstance(value, (dict, list)):
                # Recursive call for nested structures
                text_parts.append(extract_text_content(value))
        
        return " ".join(text_parts)
    
    # If content is a list, extract text from each item and join
    if isinstance(content, list):
        text_parts = [extract_text_content(item) for item in content]
        return " ".join(text_parts)
    
    # Fallback: convert to string
    return str(content)

def advanced_search_database(query, use_llm=True):
    """
    Advanced search that extracts content more effectively and optionally uses LLM for relevance
    """
    from app import create_app
    from App.models import SavedPage
    
    app = create_app()
    
    with app.app_context():
        # Get all pages - we'll filter them manually for better content searching
        all_pages = SavedPage.query.all()
        
        if not all_pages:
            return {"message": "No saved pages found", "items": []}
        
        # Process each page to find matches
        results = []
        for page in all_pages:
            # Extract full text content from the gumloop_data
            content_text = extract_text_content(page.gumloop_data)
            
            # Check if query appears in title or content
            if (query.lower() in page.title.lower() or 
                query.lower() in content_text.lower()):
                
                results.append({
                    "id": page.id,
                    "title": page.title,
                    "url": page.url,
                    "saved_at": page.saved_at.strftime('%Y-%m-%d %H:%M:%S'),
                    "content_snippet": extract_content_snippet_advanced(content_text, query),
                    "content_text": content_text,  # Full content for LLM processing
                    "relevance_score": 1.0  # Default score
                })
        
        # Use Claude to rank results by relevance if enabled and available
        if use_llm and claude_client and results:
            results = llm_rank_search_results(query, results)
        
        # Remove the full content text to reduce response size
        for result in results:
            if "content_text" in result:
                del result["content_text"]
        
        return {"message": f"Found {len(results)} results", "items": results}

def conversational_search(query: str) -> str:
    """
    Use LLM to search through saved pages and respond conversationally
    """
    if not claude_client:
        return "Conversational search is not available because the Anthropic API key is not set. Please set the ANTHROPIC_API_KEY environment variable."
    
    try:
        # First, get all saved pages to provide context to the LLM
        saved_pages = get_all_saved_pages()
        
        if not saved_pages:
            return "I don't have any saved pages to search through."
        
        # Prepare context about all saved pages (limit to 15 most relevant pages for context window size)
        # We'll use a simple keyword matching first to identify potential matches
        potential_matches = []
        query_words = query.lower().split()
        
        # Tokenize query into individual words and filter out common words
        stopwords = {'the', 'a', 'an', 'and', 'or', 'but', 'is', 'are', 'was', 'were', 
                     'in', 'on', 'at', 'to', 'for', 'with', 'by', 'about', 'like', 
                     'through', 'over', 'before', 'between', 'after', 'from', 'up', 
                     'down', 'do', 'does', 'did', 'have', 'has', 'had', 'of', 'that', 'this'}
        
        filtered_query_words = [word for word in query_words if word not in stopwords]
        
        # If no significant words remain, use original query
        if not filtered_query_words:
            filtered_query_words = query_words
        
        # Look for keyword matches in titles and content
        for page in saved_pages:
            score = 0
            title_lower = page['title'].lower()
            content_lower = page['content_text'].lower() if page['content_text'] else ""
            
            # Check if any query words appear in title or content
            for word in filtered_query_words:
                if word in title_lower:
                    score += 3  # Title matches are more important
                if word in content_lower:
                    score += 1
            
            if score > 0:
                page['score'] = score
                potential_matches.append(page)
        
        # Sort by score (descending)
        potential_matches.sort(key=lambda x: x['score'], reverse=True)
        
        # Take top matches (up to 15)
        top_matches = potential_matches[:15]
        
        # If no matches found through keywords, include a sampling of pages (up to 10)
        if not top_matches and saved_pages:
            top_matches = saved_pages[:10]
        
        # Create a compact context of the pages
        page_contexts = []
        for i, page in enumerate(top_matches):
            content_snippet = page['content_text'][:1000] if page['content_text'] else "No content available"
            page_contexts.append(
                f"Page {i+1}:\n"
                f"Title: {page['title']}\n"
                f"URL: {page['url']}\n"
                f"Saved: {page['saved_at']}\n"
                f"Content Snippet: {content_snippet}\n"
            )
        
        context_text = "\n\n".join(page_contexts)
        
        # Create prompt for Claude
        system_prompt = f"""You are SecondBrain, an AI assistant with access to the user's saved web pages and bookmarks.
Your goal is to help the user remember and find information from their saved content.
The user's query is: "{query}"

Below is a selection of web pages the user has saved. Use this information to answer their query.
If the query seems to be asking about a specific saved page, mention details about that page (title, when it was saved, and relevant content).
If you find relevant information, provide a helpful summary from the content with the specific URL as a citation.
If you don't find any relevant information, politely say you couldn't find anything related in their saved pages.

SAVED PAGES:
{context_text}"""
        
        # Send to Claude
        response = claude_client.messages.create(
            model="claude-3-opus-20240229",
            max_tokens=2000,
            system=system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": "Answer based on my saved web pages."
                }
            ]
        )
        
        # Return Claude's response
        return response.content[0].text
    
    except Exception as e:
        logger.error(f"Error in conversational search: {e}")
        return f"I encountered an error while searching through your saved pages: {str(e)}"

def llm_rank_search_results(query: str, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Use Claude to rank search results by relevance
    """
    try:
        # Limit to top 5 results for performance reasons
        processing_results = results[:5] if len(results) > 5 else results
        
        # Create a prompt for Claude to rank the results
        prompt = f"""You are a search engine assistant helping to rank search results for the query: "{query}"

Please analyze these search results and assess their relevance to the query on a scale of 0-10, where 10 is extremely relevant.
For each result, provide a relevance score and brief explanation of why it's relevant or not relevant.

Search Results:
"""
        
        for i, result in enumerate(processing_results):
            content_snippet = result.get("content_snippet", "")
            title = result.get("title", "")
            prompt += f"\nResult {i+1}:\nTitle: {title}\nContent: {content_snippet}\n"
        
        # Ask Claude to rank the results
        response = claude_client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )
        
        # Parse Claude's response to extract scores
        response_text = response.content[0].text if response.content else ""
        
        # Extract scores from response using regex
        score_pattern = r"Result (\d+).*?(\d+(?:\.\d+)?)\s*\/\s*10"
        score_matches = re.findall(score_pattern, response_text, re.DOTALL)
        
        # Update scores in the results
        scores_map = {}
        for result_num, score in score_matches:
            try:
                result_idx = int(result_num) - 1
                score_value = float(score) / 10.0  # Normalize to 0-1
                if 0 <= result_idx < len(processing_results):
                    processing_results[result_idx]["relevance_score"] = score_value
                    result_id = processing_results[result_idx]["id"]
                    scores_map[result_id] = score_value
            except (ValueError, IndexError):
                continue
        
        # Update scores for other results not processed by Claude
        for result in results:
            if result["id"] in scores_map:
                result["relevance_score"] = scores_map[result["id"]]
        
        # Sort results by relevance score (highest first)
        sorted_results = sorted(results, key=lambda x: x.get("relevance_score", 0), reverse=True)
        return sorted_results
        
    except Exception as e:
        logger.error(f"Error in LLM ranking: {e}")
        # In case of error, return original results unchanged
        return results

def extract_content_snippet_advanced(content_text, query, max_length=250):
    """
    Extract a more relevant snippet from content containing the query
    """
    if not content_text:
        return None
    
    # Find query position (case-insensitive)
    query_pos = content_text.lower().find(query.lower())
    
    if query_pos == -1:
        # Query not found in content, return start of content
        return content_text[:max_length] + "..."
    
    # Calculate snippet start and end positions
    start_pos = max(0, query_pos - (max_length // 2))
    end_pos = min(len(content_text), start_pos + max_length)
    
    # Adjust start position if we're near the end
    if end_pos == len(content_text):
        start_pos = max(0, end_pos - max_length)
    
    # Adjust to not break words
    if start_pos > 0:
        # Find the first space before or at start_pos
        space_pos = content_text.rfind(" ", 0, start_pos + 20)
        if space_pos >= 0:
            start_pos = space_pos + 1
    
    if end_pos < len(content_text):
        # Find the first space after or at end_pos
        space_pos = content_text.find(" ", end_pos - 20)
        if space_pos >= 0:
            end_pos = space_pos
    
    # Create snippet
    snippet = content_text[start_pos:end_pos]
    
    # Add ellipsis if needed
    if start_pos > 0:
        snippet = "..." + snippet
    if end_pos < len(content_text):
        snippet = snippet + "..."
    
    # Highlight the query in the snippet (using markdown ** for bold)
    highlighted_snippet = re.sub(
        f"({re.escape(query)})",
        r"**\1**",
        snippet,
        flags=re.IGNORECASE
    )
    
    return highlighted_snippet

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

def run_mcp_server():
    """
    Start the MCP server
    """
    # Create a new FastMCP instance
    server = FastMCP("SecondBrain MCP Server")
    
    # Define basic search tool
    @server.tool(name="search_secondbrain", description="Search through saved pages in the SecondBrain database")
    def search_secondbrain(query: str) -> str:
        """
        Search through saved pages in the SecondBrain database
        
        Args:
            query: The search query to find saved pages
        """
        if not query:
            return "Please provide a search query"
        
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
        
        return formatted_results
    
    # Define advanced search tool with LLM
    @server.tool(name="search_secondbrain_advanced", description="Advanced search through saved pages using content extraction and AI ranking")
    def search_secondbrain_advanced(query: str, use_llm: bool = True) -> str:
        """
        Advanced search through saved pages with better content analysis and AI ranking
        
        Args:
            query: The search query to find saved pages
            use_llm: Whether to use AI (Claude) to rank results by relevance
        """
        if not query:
            return "Please provide a search query"
        
        if use_llm and not claude_client:
            return "LLM-based search is not available. Please set the ANTHROPIC_API_KEY environment variable."
        
        results = advanced_search_database(query, use_llm)
        
        # Format response
        formatted_results = f"Found {len(results['items'])} results for query: {query}\n\n"
        
        for item in results['items']:
            relevance = f"Relevance: {item.get('relevance_score', 'N/A') * 10:.1f}/10\n" if use_llm else ""
            formatted_results += f"Title: {item['title']}\n"
            formatted_results += f"URL: {item['url']}\n" 
            formatted_results += f"Saved: {item['saved_at']}\n"
            formatted_results += relevance
            if item['content_snippet']:
                formatted_results += f"Content: {item['content_snippet']}\n"
            formatted_results += f"ID: {item['id']}\n\n"
        
        return formatted_results
    
    # Define conversational search tool
    @server.tool(name="chat_with_secondbrain", description="Have a natural conversation about your saved pages and bookmarks")
    def chat_with_secondbrain(query: str) -> str:
        """
        Have a natural language conversation about your saved content
        
        Args:
            query: Your natural language query or question about saved content
        """
        if not query:
            return "Please ask a question about your saved content"
        
        if not claude_client:
            return "Conversational search requires the Anthropic API. Please set the ANTHROPIC_API_KEY environment variable."
        
        return conversational_search(query)
    
    # Define event tool
    @server.tool(name="create_event", description="Create a calendar event or send an email invitation for an event found in content")
    def create_event(
        content_id: int = None, 
        event_title: str = None, 
        event_date: str = None,
        start_time: str = "09:00",
        end_time: str = "10:00",
        description: str = "",
        method: str = "calendar",
        recipient: str = ""
    ) -> str:
        """
        Create a calendar event or send an email invitation for an event found in content
        
        Args:
            content_id: ID of the saved page containing event information
            event_title: Title of the event
            event_date: Date of the event in YYYY-MM-DD format
            start_time: Start time of the event in HH:MM format
            end_time: End time of the event in HH:MM format
            description: Description of the event
            method: How to create the invitation: 'calendar' for Google Calendar or 'email' for email invitation
            recipient: Email recipient for email invitations
        """
        if content_id:
            # Fetch the content from the database
            from app import create_app
            from App.models import SavedPage
            
            app = create_app()
            
            with app.app_context():
                page = SavedPage.query.get(content_id)
                if not page or not page.gumloop_data:
                    return f"Content with ID {content_id} not found or has no content"
                
                # Extract text from gumloop_data using our new advanced extractor
                content_text = extract_text_content(page.gumloop_data)
                
                # Extract dates
                dates = extract_dates(content_text)
                if not dates:
                    return "No dates found in the content"
                
                # Format found dates
                date_info = "Found potential event dates:\n\n"
                for i, date_obj in enumerate(dates):
                    date_info += f"{i+1}. {date_obj['text']} - Context: {date_obj['context']}\n"
                
                return date_info
        
        # Create event from provided details
        if not event_title or not event_date:
            return "Please provide an event title and date"
        
        # Parse date and times
        try:
            start_datetime = parser.parse(f"{event_date} {start_time}")
            end_datetime = parser.parse(f"{event_date} {end_time}")
        except Exception as e:
            return f"Invalid date or time format: {str(e)}"
        
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
            return result.get("message", "Event created successfully")
        else:
            return f"Error: {result.get('error', 'Unknown error')}"
    
    # Start the server
    server.run()

if __name__ == "__main__":
    run_mcp_server() 
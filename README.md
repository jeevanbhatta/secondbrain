
To implement MCP for searching your database and adding calendar event functionality, I'll need to:

1. Create an MCP server that connects to your database
2. Add a date extraction and calendar integration feature

Let's start by examining your app structure and implementing the necessary code.

Read file: server/app.py

Read file: requirements.txt

Read file: server/requirements.txt
Let's create an MCP implementation for your SecondBrain app. I'll build this in steps:

1. First, I'll create the MCP server that connects to your database
2. Then add the date extraction and calendar integration feature

## Step 1: Create an MCP Server


Now, let's create an MCP server component for your SecondBrain application:


Now, let's create an integration with the browser extension to leverage this MCP server. We need to see the current extension code structure to understand how to implement the integration.

Ran tool
Let's look at the extension's popup.js and popup.html to understand the current UI and functionality:

Read file: extension/popup.js

Read file: extension/popup.html
Now let's implement the MCP integration for the browser extension. We'll modify the existing files to add the search and calendar functionality:


Now, let's update the popup.html file to add the search results section and clear search button:


Now, let's add the necessary API endpoints to the Flask app to handle MCP search and calendar event creation:


Now let's create the template for the event creation page:


Let's also create a simple error template:


Finally, let's create a script to run the MCP server:


Now let's make the script executable:

```bash
chmod +x run_mcp.py
```
Let's summarize what we've implemented to enhance your SecondBrain extension:

1. **MCP (Model Context Protocol) Integration**:
   - Created a dedicated MCP server (`mcp_server.py`) that provides AI models with access to your saved content
   - Implemented search functionality to find relevant content in your database
   - Added date extraction capabilities to identify potential events in saved pages

2. **Calendar Event Creation**:
   - Added the ability to create Google Calendar events from dates found in content
   - Implemented email invitation sending as an alternative
   - Created a user interface for event creation and configuration

3. **UI Enhancements**:
   - Updated the browser extension to display search results
   - Added event creation buttons for each search result
   - Improved the user experience with clear feedback and error handling

To run and test your implementation:

1. Install the new dependencies:
```
pip install modelcontextprotocol dateutil google-api-python-client google-auth-httplib2 google-auth-oauthlib
```

2. Start the Flask application:
```
python app.py
```

3. In a separate terminal, start the MCP server:
```
./run_mcp.py
```

4. Install or reload your browser extension to see the new functionality.

For the Google Calendar integration, you'll need to create credentials by:
1. Go to the Google Cloud Console
2. Create a new project 
3. Enable the Google Calendar API
4. Create OAuth 2.0 credentials
5. Download the JSON file and save it as `credentials.json` in your server directory

For email sending, you'll need to set the following environment variables:
```
SMTP_USERNAME=your-email@example.com
SMTP_PASSWORD=your-password
```

This implementation provides a complete solution for searching your saved pages using MCP and creating calendar events or email invitations when dates are found in the content.

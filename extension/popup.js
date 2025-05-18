document.addEventListener('DOMContentLoaded', function () {
    const saveBtn = document.getElementById('savePage');
    const recentBookmarksDiv = document.getElementById('recentBookmarks');
    const questionBar = document.getElementById('questionBar');
    const searchResultsDiv = document.getElementById('searchResults');

    saveBtn.addEventListener('click', async () => {
        try {
            // Get the current active tab
            const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
            console.log('Current tab:', tab);

            // Make the API request directly
            const response = await fetch('http://localhost:5001/api/save-page', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                    'Origin': chrome.runtime.getURL('')
                },
                body: JSON.stringify({
                    url: tab.url,
                    title: tab.title
                })
            });

            console.log('Response status:', response.status);
            const data = await response.json();
            console.log('Server response:', data);

            if (data.error) {
                // Instead of showing a status bar, update the button text
                const originalText = saveBtn.innerHTML;
                saveBtn.innerHTML = `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" style="display:inline;vertical-align:middle;"><rect x="4" y="4" width="16" height="16" rx="4" stroke="currentColor" stroke-width="2" fill="none"/><path d="M12 8V16" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><path d="M8 12H16" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><path d="M4 18C7 20 17 20 20 18" stroke="currentColor" stroke-width="2" stroke-linecap="round" fill="none"/></svg> Error: ${data.error}`;
                saveBtn.disabled = true;
                setTimeout(() => {
                    saveBtn.innerHTML = originalText;
                    saveBtn.disabled = false;
                }, 1500);
            } else {
                // Instead of showing a status bar, update the button text
                const originalText = saveBtn.innerHTML;
                saveBtn.innerHTML = `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" style="display:inline;vertical-align:middle;"><rect x="4" y="4" width="16" height="16" rx="4" stroke="currentColor" stroke-width="2" fill="none"/><path d="M12 8V16" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><path d="M8 12H16" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><path d="M4 18C7 20 17 20 20 18" stroke="currentColor" stroke-width="2" stroke-linecap="round" fill="none"/></svg> Saved`;
                saveBtn.disabled = true;
                setTimeout(() => {
                    saveBtn.innerHTML = originalText;
                    saveBtn.disabled = false;
                }, 1500);
                // Reload recent bookmarks after saving
                loadRecentBookmarks();
            }
        } catch (error) {
            console.error('Error:', error);
            // Instead of showing a status bar, update the button text
            const originalText = saveBtn.innerHTML;
            saveBtn.innerHTML = `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" style="display:inline;vertical-align:middle;"><rect x="4" y="4" width="16" height="16" rx="4" stroke="currentColor" stroke-width="2" fill="none"/><path d="M12 8V16" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><path d="M8 12H16" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><path d="M4 18C7 20 17 20 20 18" stroke="currentColor" stroke-width="2" stroke-linecap="round" fill="none"/></svg> Error: ${error.message}`;
            saveBtn.disabled = true;
            setTimeout(() => {
                saveBtn.innerHTML = originalText;
                saveBtn.disabled = false;
            }, 1500);
        }
    });

    // MCP search functionality
    questionBar.addEventListener('keydown', async (e) => {
        if (e.key === 'Enter' && questionBar.value.trim()) {
            const query = questionBar.value.trim();
            console.log('Searching for:', query);
            
            try {
                // Show loading indicator
                searchResultsDiv.innerHTML = '<div class="loading">Searching your saved pages...</div>';
                
                // Call the MCP search endpoint
                const response = await fetch('http://localhost:5001/api/mcp-search', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Accept': 'application/json'
                    },
                    body: JSON.stringify({ 
                        query,
                        conversational: true  // Request conversational search
                    })
                });
                
                const data = await response.json();
                
                if (data.error) {
                    searchResultsDiv.innerHTML = `<div class="error-message">${data.error}</div>`;
                    return;
                }
                
                // Check if we have a conversational response
                if (data.results && data.results.conversational_response) {
                    // Display the conversational response
                    searchResultsDiv.innerHTML = '';
                    
                    // Create a container for the conversation
                    const conversationDiv = document.createElement('div');
                    conversationDiv.className = 'conversation-response';
                    
                    // If there are items with URLs in the results, display the first one at the top
                    let displayedUrl = null;
                    if (data.results.items && data.results.items.length > 0 && data.results.items[0].url) {
                        // Add URL at the top with icon
                        const urlContainer = document.createElement('div');
                        urlContainer.className = 'conversation-url-container';
                        
                        // Add favicon
                        const favicon = document.createElement('img');
                        favicon.className = 'conversation-favicon';
                        favicon.src = `https://www.google.com/s2/favicons?domain=${new URL(data.results.items[0].url).hostname}`;
                        favicon.alt = '';
                        
                        // Add URL
                        const urlElement = document.createElement('div');
                        urlElement.className = 'conversation-url';
                        urlElement.textContent = data.results.items[0].url;
                        
                        // Add elements to container
                        urlContainer.appendChild(favicon);
                        urlContainer.appendChild(urlElement);
                        conversationDiv.appendChild(urlContainer);
                        
                        displayedUrl = data.results.items[0].url;
                    }
                    
                    // Add the user query in a chat bubble
                    const userQueryDiv = document.createElement('div');
                    userQueryDiv.className = 'user-query';
                    userQueryDiv.textContent = query;
                    conversationDiv.appendChild(userQueryDiv);
                    
                    // Add the AI response in a chat bubble
                    const aiResponseDiv = document.createElement('div');
                    aiResponseDiv.className = 'ai-response';
                    
                    // Format the response with markdown-like syntax
                    const formattedResponse = data.results.conversational_response
                        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>') // Bold
                        .replace(/\*(.*?)\*/g, '<em>$1</em>') // Italic
                        .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank">$1</a>') // Links
                        .replace(/\n\n/g, '<br><br>') // Paragraphs
                        .replace(/\n/g, '<br>'); // Line breaks
                    
                    aiResponseDiv.innerHTML = formattedResponse;
                    conversationDiv.appendChild(aiResponseDiv);
                    
                    // If the response mentions URLs but none were displayed at the top, try to extract them
                    if (!displayedUrl && data.results.conversational_response.includes('http')) {
                        // Try to extract URLs from the response
                        const urlRegex = /(https?:\/\/[^\s]+)/g;
                        const foundUrls = data.results.conversational_response.match(urlRegex);
                        
                        if (foundUrls && foundUrls.length > 0) {
                            // Create URL container
                            const urlContainer = document.createElement('div');
                            urlContainer.className = 'conversation-extracted-url-container';
                            
                            // Add a label
                            const urlLabel = document.createElement('div');
                            urlLabel.className = 'url-label';
                            urlLabel.textContent = 'Mentioned URL:';
                            urlContainer.appendChild(urlLabel);
                            
                            // Add the first URL
                            const urlElement = document.createElement('a');
                            urlElement.className = 'conversation-extracted-url';
                            urlElement.href = foundUrls[0];
                            urlElement.target = '_blank';
                            urlElement.textContent = foundUrls[0];
                            urlContainer.appendChild(urlElement);
                            
                            // Add to the conversation after the AI response
                            conversationDiv.appendChild(urlContainer);
                        }
                    }
                    
                    searchResultsDiv.appendChild(conversationDiv);
                }
                // Display regular search results if no conversational response
                else if (data.results && data.results.items && data.results.items.length > 0) {
                    searchResultsDiv.innerHTML = '';
                    const resultsHeader = document.createElement('div');
                    resultsHeader.className = 'results-header';
                    resultsHeader.textContent = `Found ${data.results.items.length} results:`;
                    searchResultsDiv.appendChild(resultsHeader);
                    
                    // Display each result
                    data.results.items.forEach(item => {
                        const resultItem = document.createElement('div');
                        resultItem.className = 'search-result-item';
                        
                        // Add URL at the top
                        const urlElement = document.createElement('div');
                        urlElement.className = 'result-url';
                        urlElement.textContent = item.url;
                        resultItem.appendChild(urlElement);
                        
                        const title = document.createElement('a');
                        title.href = item.url;
                        title.target = '_blank';
                        title.className = 'result-title';
                        title.textContent = item.title;
                        
                        const snippet = document.createElement('div');
                        snippet.className = 'result-snippet';
                        snippet.textContent = item.content_snippet || 'No content preview available';
                        
                        // Add create event button if dates were found
                        const eventButton = document.createElement('button');
                        eventButton.className = 'event-button';
                        eventButton.innerHTML = 'Create Event';
                        eventButton.addEventListener('click', () => {
                            window.open(`http://localhost:5001/create-event/${item.id}`, '_blank');
                        });
                        
                        resultItem.appendChild(title);
                        resultItem.appendChild(snippet);
                        resultItem.appendChild(eventButton);
                        
                        searchResultsDiv.appendChild(resultItem);
                    });
                } else {
                    searchResultsDiv.innerHTML = '<div class="no-results">No results found. Try a different search term.</div>';
                }
                
                // Show search results and hide recent bookmarks
                document.getElementById('recentSection').style.display = 'none';
                document.getElementById('searchSection').style.display = 'block';
                
            } catch (error) {
                console.error('Search error:', error);
                searchResultsDiv.innerHTML = `<div class="error-message">Error searching: ${error.message}</div>`;
            }
        }
    });
    
    // Add clear search button functionality
    document.getElementById('clearSearch').addEventListener('click', () => {
        // Clear search results
        questionBar.value = '';
        searchResultsDiv.innerHTML = '';
        
        // Show recent bookmarks and hide search results
        document.getElementById('recentSection').style.display = 'block';
        document.getElementById('searchSection').style.display = 'none';
    });

    // Fetch and display 5 most recent bookmarks from your backend
    async function loadRecentBookmarks() {
        try {
            const response = await fetch('http://localhost:5001/api/recent-pages');
            const bookmarks = await response.json();
            if (bookmarks && bookmarks.length > 0) {
                recentBookmarksDiv.innerHTML = '';
                bookmarks.forEach(bm => {
                    const url = bm.url;
                    const title = bm.title || url;
                    const favicon = `https://www.google.com/s2/favicons?domain=${new URL(url).hostname}`;
                    
                    // Create container for the bookmark item
                    const container = document.createElement('div');
                    container.className = 'bookmark-container';
                    
                    // Add URL at the top
                    const urlElement = document.createElement('div');
                    urlElement.className = 'bookmark-url';
                    urlElement.textContent = url;
                    container.appendChild(urlElement);
                    
                    // Create the bookmark item
                    const item = document.createElement('a');
                    item.className = 'bookmark-item';
                    item.href = url;
                    item.target = '_blank';
                    item.rel = 'noopener noreferrer';
                    item.innerHTML = `<img class="bookmark-favicon" src="${favicon}" alt=""> <span class="bookmark-title">${title}</span>`;
                    
                    container.appendChild(item);
                    recentBookmarksDiv.appendChild(container);
                });
            } else {
                recentBookmarksDiv.innerHTML = '<div style="color: var(--text-secondary); text-align: center;">No recent bookmarks found.</div>';
            }
        } catch (err) {
            recentBookmarksDiv.innerHTML = '<div style="color: var(--text-secondary); text-align: center;">Failed to load bookmarks.</div>';
        }
    }

    loadRecentBookmarks();
}); 
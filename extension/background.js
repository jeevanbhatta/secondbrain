// Handle installation
chrome.runtime.onInstalled.addListener(() => {
    console.log('SecondBrain extension installed');
});

// Handle messages from content script or popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.type === 'API_CALL') {
        fetch('http://localhost:5000/api/example', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(request.data)
        })
            .then(response => response.json())
            .then(data => sendResponse(data))
            .catch(error => sendResponse({ error: error.message }));
        return true; // Required for async sendResponse
    }
}); 
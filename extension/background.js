// Handle installation
chrome.runtime.onInstalled.addListener(() => {
    console.log('SecondBrain extension installed');
});

// Handle messages from content script or popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    console.log('Background script received message:', request);

    if (request.type === 'SAVE_PAGE') {
        console.log('Processing save page request:', request.data);

        fetch('http://localhost:5000/api/save-page', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            mode: 'cors',
            credentials: 'include',
            body: JSON.stringify(request.data)
        })
            .then(response => {
                console.log('Response status:', response.status);
                console.log('Response headers:', response.headers);

                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                console.log('Server response data:', data);
                sendResponse(data);
            })
            .catch(error => {
                console.error('Background script error:', error);
                sendResponse({ error: error.message });
            });
        return true; // Required for async sendResponse
    }
}); 
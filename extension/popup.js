document.addEventListener('DOMContentLoaded', function () {
    const saveButton = document.getElementById('savePage');
    const contentDiv = document.getElementById('content');

    saveButton.addEventListener('click', async () => {
        try {
            // Get the current active tab
            const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

            // Send message to content script to get page data
            const response = await chrome.tabs.sendMessage(tab.id, { action: 'getPageData' });

            // Send data to Flask server
            const serverResponse = await fetch('http://localhost:5000/api/save-page', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    url: tab.url,
                    title: tab.title,
                    content: response.content
                })
            });

            const result = await serverResponse.json();
            contentDiv.textContent = result.message;
        } catch (error) {
            contentDiv.textContent = 'Error: ' + error.message;
        }
    });
}); 
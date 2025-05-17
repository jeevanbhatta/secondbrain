document.addEventListener('DOMContentLoaded', function () {
    const saveButton = document.getElementById('savePage');
    const contentDiv = document.getElementById('content');

    saveButton.addEventListener('click', async () => {
        try {
            contentDiv.textContent = 'Saving page...';

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
                contentDiv.textContent = 'Error: ' + data.error;
            } else {
                contentDiv.textContent = data.message;
            }
        } catch (error) {
            console.error('Error:', error);
            contentDiv.textContent = 'Error: ' + error.message;
        }
    });
}); 
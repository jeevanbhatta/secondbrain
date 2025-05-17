// Listen for messages from the popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === 'getPageData') {
        // Get the main content of the page
        const content = document.body.innerText;

        // Send the content back to the popup
        sendResponse({ content: content });
    }
    return true; // Required for async sendResponse
}); 
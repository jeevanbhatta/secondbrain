document.addEventListener('DOMContentLoaded', function () {
    const saveBtn = document.getElementById('savePage');
    const recentBookmarksDiv = document.getElementById('recentBookmarks');

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
                    const item = document.createElement('a');
                    item.className = 'bookmark-item';
                    item.href = url;
                    item.target = '_blank';
                    item.rel = 'noopener noreferrer';
                    item.innerHTML = `<img class="bookmark-favicon" src="${favicon}" alt=""> <span class="bookmark-title">${title}</span>`;
                    recentBookmarksDiv.appendChild(item);
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
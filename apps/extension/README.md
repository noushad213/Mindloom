## Chrome Extension – Tab Tracking and Content Extraction

### Overview

The Chrome extension tracks open browser tabs and extracts the text content of selected tabs when requested. It sends the collected information to the connected frontend, which can then forward it to the FastAPI backend for further processing.

The extension is responsible for tab tracking and content extraction. It does not directly communicate with the backend or permanently store the extracted content.

### How It Works

```text
Chrome Tabs
     ↓
Chrome Extension (background.js)
     ↓
React Frontend
     ↓
FastAPI Backend
     ↓
Content Processing and Graph Generation
```

### 1. Tab Tracking

* Tracks tabs opened in the browser.
* Updates the tab list when tabs are added, removed, updated, or activated.
* Excludes incognito tabs and specified blocked websites, such as WhatsApp Web and Microsoft Teams.
* Sends updated tab information to the connected frontend.

### 2. Manual Tab Removal

* The frontend provides a Remove option for each tab.
* Removing a tab excludes it from the current research session.
* The actual browser tab remains open.
* Currently, removed tabs are tracked in frontend memory, so the exclusion resets when the page is fully refreshed.

### 3. Content Extraction

* Content extraction starts when the user clicks the **Get Graph** button.
* The extension extracts the available visible text from the selected tabs using Chrome's scripting API.
* Each result contains the tab ID, title, URL, and extracted content.
* Content extraction is limited to 30,000 characters per tab.
* The extracted results are sent to the frontend as `CONTENT_RESULTS`.

The extracted text may not include hidden, dynamically loaded, or restricted page content.

### 4. How Data Reaches the Backend

The extension sends tab information and extracted content to the frontend through Chrome's external messaging connection.

The frontend is responsible for sending the extracted content to the FastAPI backend using an HTTP POST request.

The extension does not directly call the backend.

### 5. Example JSON Data

The extracted content is returned in the following format:

```json
{
  "tabId": 123,
  "title": "Example Page",
  "url": "https://example.com",
  "content": "Extracted text from the webpage...",
  "success": true
}
```

The frontend can convert the data into the format expected by the backend, such as `tab_id`, `title`, `url`, and `content`.

### 6. Using test.html as an Example

`test.html` is a standalone test page used to check the Chrome extension before integrating it with the main React frontend.

It demonstrates how a webpage can connect to the extension and use the data it provides.

It can be used as a reference for implementing the same functionality in React.

The test page demonstrates:

* Connecting to the Chrome extension.
* Receiving the initial list of open tabs.
* Displaying live tab updates.
* Removing tabs from the current research session without closing them.
* Requesting content extraction using the Get Graph button.
* Receiving and displaying the extracted content through `CONTENT_RESULTS`.

**Important:** `test.html` is a testing example, not the final application frontend. Its connection and message-handling logic can be referred to while implementing the corresponding functionality in React. The React frontend will replace the test page in the final application and will also handle sending the extracted content to FastAPI.

### 7. Configuring the Frontend URL and Port

The extension only accepts connections from frontend URLs listed in `manifest.json` under `externally_connectable.matches`.

The current configuration allows the frontend to connect from the listed localhost URLs, for example:

```json
"externally_connectable": {
  "matches": [
    "http://localhost:5173/*",
    "http://127.0.0.1:5173/*",
    "http://localhost:5500/*",
    "http://127.0.0.1:5500/*"
  ]
}
```

Port `5173` is the default Mindloom Vite dashboard. Port `5500` remains available for the standalone test page.

If you run the frontend on a different port, update these entries to match the new URL.

For example, for port `3000`, use:

```json
"externally_connectable": {
  "matches": [
    "http://localhost:3000/*",
    "http://127.0.0.1:3000/*"
  ]
}
```

You can include both localhost and 127.0.0.1 if you use either address. After changing the manifest, reload the extension from `chrome://extensions/` for the changes to take effect.

The URL used by the frontend must also match the URL allowed in the extension manifest.

### 8. Extension ID Configuration

The frontend needs the extension's ID to establish a connection with it.

Each developer should use the ID of the extension installed in their own Chrome browser. To find it:

1. Open `chrome://extensions/`.
2. Enable Developer mode.
3. Find the loaded extension.
4. Copy its ID.
5. Replace the placeholder extension ID in `test.html` with that ID.

The same ID must be configured wherever the frontend connects to the extension.

**Note:** Do not assume that another developer will have the same extension ID. The ID shown in this repository's example is not a universal ID. Avoid committing personal or machine-specific IDs as though they are required for everyone.

### 9. Data Storage

The extension does not permanently store tab information or extracted content. The frontend currently handles the received data in memory.

If the data needs to be saved for a research session, the FastAPI backend will handle storage.

### 10. Privacy and Limitations

* Incognito tabs and specified blocked websites are excluded.
* Content is extracted only when requested by the user.
* The extension does not automatically send extracted content to the backend.
* Some webpages may restrict content extraction.
* The extension requires the relevant Chrome permissions to access tabs and extract webpage text.
* The extension's allowed frontend URLs are controlled through `externally_connectable.matches` in the manifest.

### Current Implementation

The extension currently supports live tab tracking, manual tab exclusion, and on-demand content extraction. The extension-to-frontend communication has been tested using `test.html`.

The next integration step is to implement the same communication flow in the React frontend and forward the extracted content to the FastAPI backend.

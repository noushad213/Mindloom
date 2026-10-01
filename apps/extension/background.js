// Websites that should never appear in the research tab list.
const BLOCKED_DOMAINS = [
  "web.whatsapp.com",
  "teams.microsoft.com",
  "teams.live.com"
];

// Check whether a URL belongs to a blocked website.
function isBlockedWebsite(url) {
  try {
    const hostname = new URL(url).hostname.toLowerCase();

    return BLOCKED_DOMAINS.some(function (domain) {
      return hostname === domain || hostname.endsWith("." + domain);
    });
  } catch (error) {
    // Blocks chrome:// pages and other invalid URLs.
    return true;
  }
}

// Convert Chrome's tab object into the smaller object
// that our website needs.
function formatTab(tab) {
  return {
    id: tab.id,
    title: tab.title || "Untitled tab",
    url: tab.url || "",
    active: tab.active,
    status: tab.status
  };
}

// Check whether a tab is allowed to be tracked.
function isAllowedTab(tab) {
  return (
    tab &&
    !tab.incognito &&
    tab.url &&
    !isBlockedWebsite(tab.url)
  );
}

// Get all tabs, excluding private/restricted tabs and blocked websites.
function getAllowedTabs(callback) {
  chrome.tabs.query({}, function (tabs) {
    const allowedTabs = tabs
      .filter(isAllowedTab)
      .map(formatTab);

    callback(allowedTabs);
  });
}

// Keep track of website connections.
const connectedPages = new Set();

// Send an update to every connected website.
function sendToWebsites(message) {
  connectedPages.forEach(function (port) {
    try {
      port.postMessage(message);
    } catch (error) {
      connectedPages.delete(port);
    }
  });
}

// Extract text from one tab.
async function extractTabContent(tabId) {
  try {
    const tab = await chrome.tabs.get(tabId);

    // Re-check privacy and URL restrictions before extracting.
    if (!isAllowedTab(tab)) {
      return {
        tabId: tabId,
        success: false,
        error: "This tab is restricted or is no longer available."
      };
    }

    const results = await chrome.scripting.executeScript({
      target: {
        tabId: tabId
      },
      func: function () {
        return {
          title: document.title || "Untitled page",
          url: window.location.href,
          content: document.body
            ? document.body.innerText
            : ""
        };
      }
    });

    const pageData = results && results[0]
      ? results[0].result
      : null;

    if (!pageData) {
      return {
        tabId: tabId,
        success: false,
        error: "No content could be read from this page."
      };
    }

    return {
      tabId: tabId,
      success: true,
      title: pageData.title,
      url: pageData.url,

      // Limit the amount of text returned per page for now.
      content: (pageData.content || "").slice(0, 30000)
    };

  } catch (error) {
    return {
      tabId: tabId,
      success: false,
      error: error.message || "Could not extract this page."
    };
  }
}

// Website connects to the extension.
chrome.runtime.onConnectExternal.addListener(function (port) {
  connectedPages.add(port);

  // Send the current list as soon as the website connects.
  getAllowedTabs(function (tabs) {
    try {
      port.postMessage({
        action: "INITIAL_TABS",
        tabs: tabs
      });
    } catch (error) {
      connectedPages.delete(port);
    }
  });

  // Listen for messages from the website.
  port.onMessage.addListener(async function (message) {

    // Heartbeat: website checks whether the connection is alive.
    if (message.action === "PING") {
      port.postMessage({
        action: "PONG"
      });
      return;
    }

    // Website requests content from the tabs still in its list.
    if (message.action === "EXTRACT_TABS") {
      const tabIds = Array.isArray(message.tabIds)
        ? message.tabIds
        : [];

      const results = await Promise.all(
        tabIds.map(function (tabId) {
          return extractTabContent(tabId);
        })
      );

      try {
        port.postMessage({
          action: "CONTENT_RESULTS",
          results: results
        });
      } catch (error) {
        connectedPages.delete(port);
      }
    }
  });

  // Remove the connection when the website disconnects.
  port.onDisconnect.addListener(function () {
    connectedPages.delete(port);
  });
});

// A new tab is opened.
chrome.tabs.onCreated.addListener(function (tab) {
  // Chrome may not have assigned a URL yet.
  if (!isAllowedTab(tab)) {
    return;
  }

  sendToWebsites({
    action: "TAB_ADDED",
    tab: formatTab(tab)
  });
});

// A tab is closed.
chrome.tabs.onRemoved.addListener(function (tabId) {
  sendToWebsites({
    action: "TAB_REMOVED",
    tabId: tabId
  });
});

// A tab's URL or title changes.
chrome.tabs.onUpdated.addListener(function (tabId, changeInfo, tab) {
  if (!tab.url) {
    return;
  }

  // If it is blocked or incognito, remove it from the website.
  if (!isAllowedTab(tab)) {
    sendToWebsites({
      action: "TAB_REMOVED",
      tabId: tabId
    });
    return;
  }

  if (changeInfo.status === "complete") {
    sendToWebsites({
      action: "TAB_READY",
      tab: formatTab(tab)
    });
  } else if (changeInfo.url || changeInfo.title) {
    sendToWebsites({
      action: "TAB_UPDATED",
      tab: formatTab(tab)
    });
  }
});

// Update active status whenever you switch tabs.
chrome.tabs.onActivated.addListener(function () {
  getAllowedTabs(function (tabs) {
    tabs.forEach(function (tab) {
      sendToWebsites({
        action: "TAB_UPDATED",
        tab: tab
      });
    });
  });
});

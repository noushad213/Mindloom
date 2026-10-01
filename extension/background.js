const API_BASE =
  "https://b82wq2xh-8000.inc1.devtunnels.ms/api/v1";

const QUEUE_KEY = "mindloomUploadQueue";
const TRACKING_KEY = "mindloomTracking";
const CAPTURED_KEY = "mindloomCapturedPages";
const RETRY_ALARM = "mindloomUploadRetry";

const MAX_TEXT_LENGTH = 100000;
const MAX_QUEUE_SIZE = 500;

const BLOCKED_DOMAINS = [
  "web.whatsapp.com",
  "teams.microsoft.com"
];

const DASHBOARD_ORIGINS = new Set([
  "http://localhost:5173",
  "http://127.0.0.1:5173"
]);

let activeSession = {
  isTracking: false,
  workspaceId: null
};

let captureInProgress = new Set();

function isValidUuid(value) {
  return (
    typeof value === "string" &&
    /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(
      value
    )
  );
}

function isTrustedDashboard(sender) {
  if (!sender?.url) return false;

  try {
    return DASHBOARD_ORIGINS.has(new URL(sender.url).origin);
  } catch {
    return false;
  }
}

function isBlockedUrl(url) {
  try {
    const hostname = new URL(url).hostname.toLowerCase();

    return BLOCKED_DOMAINS.some(
      (domain) =>
        hostname === domain || hostname.endsWith(`.${domain}`)
    );
  } catch {
    return true;
  }
}

function isAllowedTab(tab) {
  if (!tab?.url || tab.incognito) return false;

  try {
    const parsed = new URL(tab.url);

    if (!["http:", "https:"].includes(parsed.protocol)) return false;

    // Do not capture the local React dashboard.
    if (
      parsed.hostname === "localhost" ||
      parsed.hostname === "127.0.0.1"
    ) {
      return false;
    }

    if (isBlockedUrl(tab.url)) return false;

    return true;
  } catch {
    return false;
  }
}

async function loadTrackingState() {
  const result = await chrome.storage.local.get(TRACKING_KEY);
  const saved = result[TRACKING_KEY];

  activeSession.isTracking = Boolean(saved?.active);
  activeSession.workspaceId = saved?.workspaceId || null;
}

async function saveTrackingState() {
  await chrome.storage.local.set({
    [TRACKING_KEY]: {
      active: activeSession.isTracking,
      workspaceId: activeSession.workspaceId
    }
  });
}

async function getQueue() {
  const result = await chrome.storage.local.get(QUEUE_KEY);
  return Array.isArray(result[QUEUE_KEY]) ? result[QUEUE_KEY] : [];
}

async function saveQueue(queue) {
  await chrome.storage.local.set({
    [QUEUE_KEY]: queue.slice(-MAX_QUEUE_SIZE)
  });
}

async function getCapturedPages() {
  const result = await chrome.storage.local.get(CAPTURED_KEY);
  return result[CAPTURED_KEY] || {};
}

async function markCaptured(key) {
  const captured = await getCapturedPages();

  captured[key] = Date.now();

  // Keep only the newest 1,000 capture keys.
  const entries = Object.entries(captured)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 1000);

  await chrome.storage.local.set({
    [CAPTURED_KEY]: Object.fromEntries(entries)
  });
}

async function wasCaptured(key) {
  const captured = await getCapturedPages();
  return Boolean(captured[key]);
}

async function enqueuePayload(payload, workspaceId) {
  const queue = await getQueue();

  // The event ID stays unchanged when this item is retried.
  if (
    queue.some(
      (item) =>
        item.payload?.client_event_id === payload.client_event_id
    )
  ) {
    return;
  }

  queue.push({
    payload,
    workspaceId,
    attempts: 0,
    createdAt: Date.now(),
    nextAttemptAt: Date.now()
  });

  await saveQueue(queue);
  await processUploadQueue();
}

async function uploadPayload(payload, workspaceId) {
  if (!isValidUuid(workspaceId)) {
    throw new Error("Invalid workspace ID in queued upload.");
  }

  if (!payload?.url || !/^https?:\/\//i.test(payload.url)) {
    throw new Error(`Invalid page URL: ${payload?.url}`);
  }

  const endpoint =
    `${API_BASE}/workspaces/${workspaceId}/pages`;

  console.log("Mindloom: Upload endpoint:", endpoint);
  console.log("Mindloom: Workspace ID:", workspaceId);
  console.log("Mindloom: URL being sent:", payload.url);
  console.log("Mindloom: Full payload:", payload);

  const response = await fetch(endpoint, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });

  const responseText = await response.text();

  console.log("Mindloom: Backend status:", response.status);
  console.log("Mindloom: Backend response:", responseText);

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${responseText}`);
  }

  return responseText;
}

async function processUploadQueue() {
  let queue = await getQueue();

  if (queue.length === 0) return;

  const now = Date.now();
  const remaining = [];

  for (const item of queue) {
    if (item.nextAttemptAt > now) {
      remaining.push(item);
      continue;
    }

    try {
      await uploadPayload(item.payload, item.workspaceId);

      console.log(
        "Mindloom: Upload successful",
        item.payload.url,
        item.payload.client_event_id
      );
    } catch (error) {
      item.attempts += 1;

      // Retry after 5s, 10s, 20s, etc., up to 15 minutes.
      const delay = Math.min(
        5000 * Math.pow(2, item.attempts - 1),
        15 * 60 * 1000
      );

      item.nextAttemptAt = Date.now() + delay;
      item.lastError = String(error);

      console.error(
        "Mindloom: Upload failed; queued for retry",
        item.payload?.url,
        item.lastError
      );

      remaining.push(item);
    }
  }

  await saveQueue(remaining);

  if (remaining.length > 0) {
    chrome.alarms.create(RETRY_ALARM, {
      when: Math.min(
        ...remaining.map((item) => item.nextAttemptAt)
      )
    });
  } else {
    await chrome.alarms.clear(RETRY_ALARM);
  }
}

async function extractPage(tab) {
  const results = await chrome.scripting.executeScript({
    target: { tabId: tab.id },
    func: () => {
      const meta = (selector) =>
        document.querySelector(selector)?.content || null;

      return {
        url: window.location.href,
        title: document.title || null,
        text: document.body?.innerText || null,
        meta: {
          description: meta('meta[name="description"]'),
          og_image: meta('meta[property="og:image"]'),
          favicon:
            document.querySelector('link[rel~="icon"]')?.href || null,
          lang: document.documentElement?.lang || null,
          site_name: meta('meta[property="og:site_name"]'),
          byline: meta('meta[name="author"]')
        }
      };
    }
  });

  return results?.[0]?.result || null;
}

async function captureAndUploadTab(tabId) {
  if (!activeSession.isTracking || !activeSession.workspaceId) return;
  if (captureInProgress.has(tabId)) return;

  captureInProgress.add(tabId);

  try {
    const tab = await chrome.tabs.get(tabId);

    if (!isAllowedTab(tab)) {
      console.log("Mindloom: Skipping unsupported tab:", tab?.url);
      return;
    }

    const workspaceId = activeSession.workspaceId;
    const captureKey = `${workspaceId}:${tab.id}:${tab.url}`;

    if (await wasCaptured(captureKey)) return;

    const page = await extractPage(tab);

    if (!page?.url || !/^https?:\/\//i.test(page.url)) {
      console.log("Mindloom: Skipping unsupported page URL:", page?.url);
      return;
    }

    const payload = {
      client_event_id: crypto.randomUUID(),
      url: page.url,
      title: page.title,
      text: page.text ? page.text.slice(0, MAX_TEXT_LENGTH) : null,
      meta: page.meta || null,
      extraction: {
        status: "ok",
        method: "chrome_scripting",
        error_code: null,
        error_message: null
      },
      tab: {
        browser_tab_id: tab.id,
        window_id: tab.windowId,
        active: Boolean(tab.active)
      },
      captured_at: new Date().toISOString()
    };

    console.log("Mindloom: Page captured:", page.url);
    console.log("Mindloom: Full payload:", payload);

    // Save before trying the network, so a failed upload can be retried.
    await enqueuePayload(payload, workspaceId);

    await markCaptured(captureKey);
  } catch (error) {
    console.error("Mindloom: Capture failed", error);
  } finally {
    captureInProgress.delete(tabId);
  }
}

async function startTracking(workspaceId) {
  activeSession.isTracking = true;
  activeSession.workspaceId = workspaceId;

  await saveTrackingState();

  console.log("Mindloom: Tracking started", workspaceId);

  const tabs = await chrome.tabs.query({});

  for (const tab of tabs) {
    if (tab.id !== undefined) {
      await captureAndUploadTab(tab.id);
    }
  }

  await processUploadQueue();
}

async function stopTracking() {
  activeSession.isTracking = false;
  activeSession.workspaceId = null;

  await saveTrackingState();

  console.log("Mindloom: Tracking stopped");
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (
    message?.type !== "MINDLOOM_START_TRACKING" &&
    message?.type !== "MINDLOOM_STOP_TRACKING"
  ) {
    return;
  }

  if (!isTrustedDashboard(sender)) {
    sendResponse({
      success: false,
      message: "Untrusted dashboard origin."
    });
    return;
  }

  if (message.type === "MINDLOOM_START_TRACKING") {
    if (!isValidUuid(message.workspaceId)) {
      sendResponse({
        success: false,
        message: "Invalid workspace ID."
      });
      return;
    }

    startTracking(message.workspaceId)
      .then(() => {
        sendResponse({
          success: true,
          message: "Tracking started."
        });
      })
      .catch((error) => {
        console.error("Mindloom: Start tracking error:", error);

        sendResponse({
          success: false,
          message: error.message
        });
      });

    return true;
  }

  stopTracking()
    .then(() => {
      sendResponse({
        success: true,
        message: "Tracking stopped."
      });
    })
    .catch((error) => {
      sendResponse({
        success: false,
        message: error.message
      });
    });

  return true;
});

chrome.tabs.onUpdated.addListener((tabId, changeInfo) => {
  if (changeInfo.status === "complete" && activeSession.isTracking) {
    captureAndUploadTab(tabId);
  }
});

chrome.tabs.onCreated.addListener((tab) => {
  if (activeSession.isTracking && tab.id !== undefined) {
    // New tabs may not have a URL yet. onUpdated will capture when loaded.
    console.log("Mindloom: New tab detected", tab.id);
  }
});

chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === RETRY_ALARM) {
    processUploadQueue();
  }
});

// Restore tracking and retry queued uploads when Chrome starts the worker.
(async () => {
  try {
    await loadTrackingState();

    if (activeSession.isTracking) {
      console.log(
        "Mindloom: Tracking restored",
        activeSession.workspaceId
      );
      await processUploadQueue();
    }
  } catch (error) {
    console.error("Mindloom: Startup error", error);
  }
})();

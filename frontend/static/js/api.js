/**
 * PARAKH Unified API Client
 */

export function showToast(message, type = "info") {
  let container = document.getElementById("toast-container");
  if (!container) {
    container = document.createElement("div");
    container.id = "toast-container";
    document.body.appendChild(container);
  }

  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.textContent = message;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateX(100%)";
    toast.style.transition = "all 0.3s ease";
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

export async function apiRequest(endpoint, options = {}) {
  const url = endpoint.startsWith("http") ? endpoint : endpoint;
  const headers = { ...options.headers };

  // Automatically set Content-Type to application/json for JSON payloads
  if (options.body && typeof options.body === "string" && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }

  const config = {
    ...options,
    headers
  };

  try {
    const response = await fetch(url, config);
    const isJson = response.headers.get("content-type")?.includes("application/json");
    const data = isJson ? await response.json() : await response.text();

    if (!response.ok) {
      const errMsg = (isJson && data.error) ? data.error : (typeof data === "string" ? data : `Error ${response.status}`);
      showToast(errMsg, "error");
      throw new Error(errMsg);
    }
    return data;
  } catch (err) {
    console.error(`API Request Failed: ${endpoint}`, err);
    throw err;
  }
}

// Fetch public settings to render system badge
export async function updateSystemBadge() {
  try {
    const settings = await apiRequest("/api/settings/public");
    const badge = document.getElementById("system-mode-badge");
    if (badge) {
      if (settings.gemini_configured && !settings.mock_mode) {
        badge.className = "mode-badge gemini";
        badge.textContent = `Gemini (${settings.gemini_model})`;
        badge.title = "Connected to Google Gemini Free Tier";
      } else {
        badge.className = "mode-badge mock";
        badge.textContent = "Mock Mode (Offline)";
        badge.title = "Operating in deterministic offline mock mode. Set GEMINI_API_KEY in .env for live AI.";
      }
    }
  } catch (e) {
    console.warn("Could not load system settings badge", e);
  }
}

document.addEventListener("DOMContentLoaded", updateSystemBadge);

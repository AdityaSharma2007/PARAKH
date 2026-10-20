import { apiRequest, showToast } from "./api.js";

async function loadDashboard() {
  const container = document.getElementById("sessions-list");
  try {
    const interviews = await apiRequest("/api/interviews");
    const analytics = await apiRequest("/api/analytics/progress");

    // Populate stats
    document.getElementById("stat-total").textContent = analytics.total_interviews || interviews.length;
    document.getElementById("stat-avg").textContent = (analytics.average_score || 0).toFixed(1);
    document.getElementById("stat-high").textContent = (analytics.highest_score || 0).toFixed(1);

    if (interviews.length > 0) {
      document.getElementById("stat-track").textContent = interviews[0].target_role || "Engineering";
    }

    if (interviews.length === 0) {
      container.innerHTML = `
        <div style="text-align: center; color: var(--text-muted); padding: 40px;">
          <p>No previous interviews found.</p>
          <a href="/resume" class="btn btn-primary" style="margin-top: 10px;">Upload Resume & Start</a>
        </div>
      `;
      return;
    }

    let html = "";
    interviews.forEach((it) => {
      const dt = new Date(it.created_at).toLocaleDateString("en-US", {
        month: "short", day: "numeric", year: "numeric", hour: "2-digit", minute: "2-digit"
      });

      const isCompleted = it.state === "COMPLETED";
      const statusBadge = isCompleted
        ? `<span class="badge" style="background: rgba(16, 185, 129, 0.15); color: #34d399;">COMPLETED</span>`
        : `<span class="badge" style="background: rgba(245, 158, 11, 0.15); color: #fbbf24;">${it.state}</span>`;

      html += `
        <div class="session-item">
          <div>
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 4px;">
              <strong style="color: #fff; font-size: 1.05rem;">Interview #${it.id}: ${it.target_role}</strong>
              ${statusBadge}
            </div>
            <div style="font-size: 0.85rem; color: var(--text-muted);">
              Track: <strong>${it.interview_type}</strong> | Difficulty: <span class="badge badge-${it.current_difficulty.toLowerCase()}">${it.current_difficulty}</span> | Date: ${dt}
            </div>
          </div>
          <div style="display: flex; gap: 8px;">
            ${isCompleted
              ? `<a href="/report?id=${it.id}" class="btn btn-primary btn-sm">View Report</a>`
              : `<a href="/interview?id=${it.id}" class="btn btn-secondary btn-sm">Resume Interview</a>`
            }
            <button class="btn btn-danger btn-sm delete-btn" data-id="${it.id}">Delete</button>
          </div>
        </div>
      `;
    });

    container.innerHTML = html;

    // Attach delete listeners
    document.querySelectorAll(".delete-btn").forEach((btn) => {
      btn.addEventListener("click", async (e) => {
        const id = e.target.getAttribute("data-id");
        if (confirm(`Are you sure you want to delete interview #${id}?`)) {
          try {
            await apiRequest(`/api/interviews/${id}`, { method: "DELETE" });
            showToast(`Interview #${id} deleted`, "success");
            loadDashboard();
          } catch (err) {
            showToast("Failed to delete interview", "error");
          }
        }
      });
    });

  } catch (err) {
    container.innerHTML = `<div style="text-align: center; color: var(--danger); padding: 30px;">Error loading dashboard records.</div>`;
  }
}

document.addEventListener("DOMContentLoaded", loadDashboard);

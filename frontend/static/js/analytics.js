import { apiRequest, showToast } from "./api.js";
import { renderTrendChart } from "./charts.js";

document.addEventListener("DOMContentLoaded", async () => {
  try {
    const data = await apiRequest("/api/analytics/progress");

    // Populate KPIs
    document.getElementById("an-total").textContent = data.total_interviews || 0;
    document.getElementById("an-avg").textContent = (data.average_score || 0).toFixed(1);
    document.getElementById("an-peak").textContent = (data.highest_score || 0).toFixed(1);

    // Calculate overall delta
    let netDelta = 0;
    if (data.score_history && data.score_history.length > 1) {
      const first = data.score_history[0].overall_score;
      const latest = data.score_history[data.score_history.length - 1].overall_score;
      netDelta = latest - first;
    }
    const trendElem = document.getElementById("an-trend");
    trendElem.textContent = `${netDelta >= 0 ? "+" : ""}${netDelta.toFixed(1)} pts`;
    trendElem.style.color = netDelta >= 0 ? "var(--success)" : "var(--danger)";

    // Render SVG Trend Chart
    renderTrendChart("trajectory-chart", data.score_history || []);

    // Render Skill Deltas
    const tbody = document.getElementById("deltas-tbody");
    const deltas = data.skill_deltas || [];

    if (deltas.length === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="5" style="text-align: center; color: var(--text-muted); padding: 30px;">
            No skill deltas available yet. Complete multiple interviews to calculate skill mastery shifts.
          </td>
        </tr>
      `;
    } else {
      tbody.innerHTML = deltas.map((d) => {
        let pillClass = "delta-stable";
        let sign = "";
        if (d.delta > 0) {
          pillClass = "delta-improved";
          sign = "+";
        } else if (d.delta < 0) {
          pillClass = "delta-declined";
        }

        return `
          <tr>
            <td><strong style="color: #fff;">${d.skill}</strong></td>
            <td>${Math.round(d.first_score)}/100</td>
            <td><strong>${Math.round(d.latest_score)}/100</strong></td>
            <td><span class="delta-pill ${pillClass}">${sign}${d.delta.toFixed(1)}</span></td>
            <td><span class="badge" style="font-size: 0.75rem;">${d.status}</span></td>
          </tr>
        `;
      }).join("");
    }

    // Render Reinforced Concepts
    const reinforcedList = document.getElementById("reinforced-list");
    const reinforced = data.reinforced_concepts || [];
    if (reinforced.length === 0) {
      reinforcedList.innerHTML = `<li style="color: var(--text-muted); list-style: none;">No reinforced concept transitions yet. Continue practicing targeted topics.</li>`;
    } else {
      reinforcedList.innerHTML = reinforced.map((r) => `
        <li style="margin-bottom: 6px;"><strong style="color: #fff;">${r}</strong> (Substantially improved over initial attempt)</li>
      `).join("");
    }

    // Render Persistent Focus Areas
    const persistentList = document.getElementById("persistent-list");
    const persistent = data.persistent_gaps || [];
    if (persistent.length === 0) {
      persistentList.innerHTML = `<li style="color: var(--text-muted); list-style: none;">No persistent knowledge bottlenecks detected. Solid coverage!</li>`;
    } else {
      persistentList.innerHTML = persistent.map((p) => `
        <li style="margin-bottom: 6px;"><strong style="color: #fff;">${p}</strong> (Scores currently below 65% bar)</li>
      `).join("");
    }

  } catch (err) {
    showToast("Error loading candidate analytics: " + err.message, "error");
  }
});

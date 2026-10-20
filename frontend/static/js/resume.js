import { apiRequest, showToast } from "./api.js";

let currentResumeId = null;
let currentSkills = [];
let currentProjects = [];

document.addEventListener("DOMContentLoaded", () => {
  const dropZone = document.getElementById("drop-zone");
  const fileInput = document.getElementById("file-input");
  const uploadStatus = document.getElementById("upload-status");
  const profileSection = document.getElementById("profile-section");
  const saveBtn = document.getElementById("save-profile-btn");
  const addSkillBtn = document.getElementById("add-skill-btn");
  const newSkillInput = document.getElementById("new-skill-input");

  // Drag and drop events
  dropZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropZone.classList.add("dragover");
  });

  dropZone.addEventListener("dragleave", () => {
    dropZone.classList.remove("dragover");
  });

  dropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropZone.classList.remove("dragover");
    if (e.dataTransfer.files.length > 0) {
      handleFileUpload(e.dataTransfer.files[0]);
    }
  });

  fileInput.addEventListener("change", (e) => {
    if (e.target.files.length > 0) {
      handleFileUpload(e.target.files[0]);
    }
  });

  async function handleFileUpload(file) {
    const ext = file.name.split(".").pop().toLowerCase();
    if (!["pdf", "docx"].includes(ext)) {
      showToast("Only PDF and DOCX files are supported.", "error");
      return;
    }

    uploadStatus.style.display = "block";
    uploadStatus.innerHTML = `<span style="color: var(--accent-primary);">Uploading & parsing resume with AI intelligence...</span>`;

    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await fetch("/api/resumes/upload", {
        method: "POST",
        body: formData
      });

      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.error || "Upload failed");
      }

      const data = await response.json();
      currentResumeId = data.resume_id;
      showToast("Resume parsed successfully!", "success");
      uploadStatus.style.display = "none";
      dropZone.style.display = "none";

      populateProfile(data.profile);
      profileSection.style.display = "block";
      profileSection.scrollIntoView({ behavior: "smooth" });
    } catch (err) {
      uploadStatus.innerHTML = `<span style="color: var(--danger);">${err.message}</span>`;
      showToast(err.message, "error");
    }
  }

  function populateProfile(profile) {
    document.getElementById("prof-name").value = profile.full_name || "";
    document.getElementById("prof-email").value = profile.email || "";
    document.getElementById("prof-phone").value = profile.phone || "";

    // 1. Render ATS Gauge & Breakdown
    renderAtsIntelligence(profile.ats_score || 0, profile.ats_breakdown || {}, profile.cv_improvement_tips || []);

    // 2. Render Contact Links
    renderContactLinks(profile.contact_links || {});

    // 3. Render Categorized Skills Depth Matrix
    currentSkills = [];
    if (profile.skills && typeof profile.skills === "object") {
      Object.values(profile.skills).forEach((items) => {
        if (Array.isArray(items)) {
          currentSkills.push(...items);
        }
      });
    }
    currentSkills = [...new Set(currentSkills)];
    renderSkillsMatrix(profile.skills || {}, profile.skill_depth_matrix || {});

    // 4. Render Deep Projects
    currentProjects = profile.projects || [];
    renderProjects();

    // 5. Render Role Skill Gap Analysis
    renderRoleGaps(profile.skill_gap_analysis || {});
  }

  function renderAtsIntelligence(score, breakdown, tips) {
    const scoreVal = document.getElementById("ats-score-val");
    const gaugeCircle = document.getElementById("ats-gauge-circle");
    const tierLabel = document.getElementById("ats-tier-label");
    const checklist = document.getElementById("ats-checklist");
    const tipsList = document.getElementById("cv-tips-list");

    scoreVal.textContent = Math.round(score);
    let color = "#10b981";
    let tier = "High Parsability (Strong)";
    if (score < 60) {
      color = "#ef4444";
      tier = "Low Parsability (Needs Review)";
    } else if (score < 80) {
      color = "#f59e0b";
      tier = "Moderate Parsability";
    }

    gaugeCircle.style.borderColor = color;
    gaugeCircle.style.color = color;
    tierLabel.textContent = tier;

    // Checklist
    const checks = breakdown.checks || [];
    const issues = breakdown.issues || [];
    let checkHtml = "";
    checks.slice(0, 4).forEach((c) => {
      checkHtml += `<div style="color: #34d399; display: flex; align-items: center; gap: 6px;">✓ <span>${c}</span></div>`;
    });
    issues.slice(0, 3).forEach((iss) => {
      checkHtml += `<div style="color: #fbbf24; display: flex; align-items: center; gap: 6px;">⚠ <span>${iss}</span></div>`;
    });
    checklist.innerHTML = checkHtml || `<div style="color: var(--text-muted);">Standard ATS format verified.</div>`;

    // Tips
    let tipHtml = "";
    (tips || []).slice(0, 4).forEach((t) => {
      tipHtml += `<div style="color: #cbd5e1; display: flex; align-items: flex-start; gap: 6px;">💡 <span>${t}</span></div>`;
    });
    tipsList.innerHTML = tipHtml || `<div style="color: var(--text-muted);">No immediate optimization flags detected.</div>`;
  }

  function renderContactLinks(contacts) {
    const bar = document.getElementById("contact-links-bar");
    let html = "";
    if (contacts.email) {
      html += `<span class="badge" style="background: rgba(99, 102, 241, 0.15); color: #a5b4fc;">✉ ${contacts.email}</span>`;
    }
    if (contacts.phone) {
      html += `<span class="badge" style="background: rgba(99, 102, 241, 0.15); color: #a5b4fc;">☎ ${contacts.phone}</span>`;
    }
    if (contacts.linkedin) {
      html += `<a href="${contacts.linkedin}" target="_blank" class="badge" style="background: rgba(14, 165, 233, 0.15); color: #38bdf8; text-decoration: none;">🔗 LinkedIn</a>`;
    }
    if (contacts.github) {
      html += `<a href="${contacts.github}" target="_blank" class="badge" style="background: rgba(168, 85, 247, 0.15); color: #c084fc; text-decoration: none;">💻 GitHub</a>`;
    }
    if (contacts.portfolio) {
      html += `<a href="${contacts.portfolio}" target="_blank" class="badge" style="background: rgba(245, 158, 11, 0.15); color: #fbbf24; text-decoration: none;">🌐 Portfolio</a>`;
    }
    bar.innerHTML = html;
  }

  function renderSkillsMatrix(skillsObj, depthMatrix) {
    const container = document.getElementById("skills-matrix-container");
    container.innerHTML = "";

    const categories = [
      { key: "languages", label: "Languages" },
      { key: "frameworks", label: "Frameworks & Libraries" },
      { key: "databases_and_tools", label: "Databases & Storage" },
      { key: "cloud_and_devops", label: "Cloud & DevOps" },
      { key: "architecture", label: "Architecture & Systems" }
    ];

    categories.forEach((cat) => {
      const skills = skillsObj[cat.key] || [];
      if (skills.length === 0) return;

      const groupDiv = document.createElement("div");
      groupDiv.style.marginBottom = "var(--space-sm)";
      groupDiv.innerHTML = `
        <div style="font-size: 0.8rem; font-weight: 600; text-transform: uppercase; color: var(--text-muted); margin-bottom: 4px;">
          ${cat.label}
        </div>
        <div class="skills-container" id="skills-cat-${cat.key}"></div>
      `;
      container.appendChild(groupDiv);

      const catContainer = groupDiv.querySelector(`#skills-cat-${cat.key}`);
      skills.forEach((skill) => {
        const chip = document.createElement("div");
        chip.className = "skill-chip";
        chip.innerHTML = `
          <span>${skill}</span>
          <span class="chip-remove" data-skill="${skill}">✕</span>
        `;
        catContainer.appendChild(chip);
      });
    });

    // Remove skill handler
    container.querySelectorAll(".chip-remove").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        const skillName = e.target.getAttribute("data-skill");
        currentSkills = currentSkills.filter((s) => s !== skillName);
        for (const cat in skillsObj) {
          skillsObj[cat] = (skillsObj[cat] || []).filter((s) => s !== skillName);
        }
        renderSkillsMatrix(skillsObj, depthMatrix);
      });
    });
  }

  function renderProjects() {
    const container = document.getElementById("projects-list");
    if (!currentProjects || currentProjects.length === 0) {
      container.innerHTML = `<p style="color: var(--text-muted); font-size: 0.85rem;">No explicit projects detected. You can proceed directly to interview generation.</p>`;
      return;
    }

    container.innerHTML = currentProjects.map((p, idx) => `
      <div style="background: var(--bg-card-alt); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); padding: var(--space-md); margin-bottom: var(--space-sm);">
        <div style="display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 8px; margin-bottom: 6px;">
          <strong style="color: #fff; font-size: 1.05rem;">${p.title || "Project " + (idx + 1)}</strong>
          <div style="display: flex; gap: 6px;">
            ${p.architecture ? `<span class="badge" style="background: rgba(99, 102, 241, 0.15); color: #a5b4fc;">🏛 ${p.architecture}</span>` : ""}
            ${p.metrics ? `<span class="badge" style="background: rgba(16, 185, 129, 0.15); color: #34d399;">⚡ ${p.metrics}</span>` : ""}
          </div>
        </div>
        <p style="font-size: 0.9rem; margin: 4px 0 8px 0; color: #cbd5e1;">${p.description || "Project implementation."}</p>
        <div style="font-size: 0.8rem; color: var(--text-muted); display: flex; flex-wrap: wrap; gap: 6px; align-items: center;">
          <span style="font-weight: 600;">Stack:</span>
          ${(p.technologies || []).map((t) => `<span style="background: var(--bg-card); padding: 2px 8px; border-radius: var(--radius-sm); border: 1px solid var(--border-subtle);">${t}</span>`).join("")}
        </div>
      </div>
    `).join("");
  }

  function renderRoleGaps(gapMap) {
    const container = document.getElementById("role-gap-container");
    const roles = Object.keys(gapMap);
    if (roles.length === 0) {
      container.innerHTML = `<p style="color: var(--text-muted); font-size: 0.85rem;">Role readiness will be calculated upon interview setup.</p>`;
      return;
    }

    container.innerHTML = roles.map((role) => {
      const data = gapMap[role];
      const pct = data.coverage_percentage || 0;
      let badgeColor = "#34d399";
      let badgeBg = "rgba(16, 185, 129, 0.15)";
      if (pct < 50) {
        badgeColor = "#f87171";
        badgeBg = "rgba(239, 68, 68, 0.15)";
      } else if (pct < 75) {
        badgeColor = "#fbbf24";
        badgeBg = "rgba(245, 158, 11, 0.15)";
      }

      return `
        <div class="role-gap-card">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
            <strong style="color: #fff;">${role}</strong>
            <span class="badge" style="background: ${badgeBg}; color: ${badgeColor}; font-weight: 600;">${pct}% Skill Match (${data.readiness_tier || "Ready"})</span>
          </div>
          <div style="font-size: 0.8rem; color: var(--text-muted); line-height: 1.4;">
            <span style="color: #34d399;">✓ Matched:</span> ${data.matched_skills.join(", ") || "None"} &nbsp;|&nbsp; 
            <span style="color: #f87171;">✗ Missing:</span> ${data.missing_skills.join(", ") || "None"}
          </div>
        </div>
      `;
    }).join("");
  }

  addSkillBtn.addEventListener("click", () => {
    const val = newSkillInput.value.trim();
    if (val && !currentSkills.includes(val)) {
      currentSkills.push(val);
      renderSkills();
      newSkillInput.value = "";
    }
  });

  saveBtn.addEventListener("click", async () => {
    if (!currentResumeId) {
      showToast("No active resume session.", "error");
      return;
    }

    saveBtn.disabled = true;
    saveBtn.textContent = "Saving...";

    try {
      await apiRequest(`/api/resumes/${currentResumeId}/profile`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          full_name: document.getElementById("prof-name").value,
          email: document.getElementById("prof-email").value,
          phone: document.getElementById("prof-phone").value,
          skills: { languages: currentSkills }
        })
      });

      showToast("Profile verified! Redirecting to Interview Setup...", "success");
      setTimeout(() => {
        window.location.href = `/setup?resume_id=${currentResumeId}`;
      }, 700);
    } catch (err) {
      saveBtn.disabled = false;
      saveBtn.textContent = "Confirm Profile & Setup Interview →";
    }
  });
});

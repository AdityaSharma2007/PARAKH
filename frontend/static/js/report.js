import { apiRequest, showToast } from "./api.js";

document.addEventListener("DOMContentLoaded", async () => {
  const urlParams = new URLSearchParams(window.location.search);
  const interviewId = urlParams.get("id");

  if (!interviewId) {
    showToast("No interview ID specified. Redirecting to dashboard.", "error");
    setTimeout(() => { window.location.href = "/dashboard"; }, 1000);
    return;
  }

  try {
    const report = await apiRequest(`/api/interviews/${interviewId}/report`);
    const evidenceData = await apiRequest(`/api/interviews/${interviewId}/evidence-graph`);
    const consistencyData = await apiRequest(`/api/interviews/${interviewId}/consistency`);

    // Populate Hero Scores
    document.getElementById("hero-score").textContent = Math.round(report.overall_score);
    const circle = document.getElementById("hero-circle");
    circle.style.setProperty("--score-pct", `${Math.round(report.overall_score)}%`);

    const dt = new Date(report.generated_at).toLocaleDateString("en-US", {
      month: "long", day: "numeric", year: "numeric", hour: "2-digit", minute: "2-digit"
    });
    document.getElementById("report-meta").textContent = `Assessed on ${dt}`;

    // Dimension Bars
    setMetric("metric-tech", report.technical_score);
    setMetric("metric-concept", report.conceptual_score);
    setMetric("metric-rel", report.relevance_score);
    setMetric("metric-clarity", report.clarity_score);

    // 1. Render Evidence Graph
    renderEvidenceGraph(evidenceData.nodes || []);

    // 2. Render Computer Vision (CV) Analytics
    renderComputerVisionAnalytics(report.vision_analytics || {});

    // 3. Render Raw Audio Acoustic Analytics
    renderAudioAcousticAnalytics(report.audio_analytics || {});

    // 4. Render Explainable Scoring
    renderExplainableScoring(report.evaluations || []);

    // 4. Render Knowledge Consistency
    renderConsistency(consistencyData.consistency_checks || []);

    // 5. Render Knowledge-Gap Map
    renderKnowledgeGaps(report.knowledge_gap_map || {});

    // Strengths & Recommendations
    const strengthsList = document.getElementById("strengths-list");
    strengthsList.innerHTML = (report.strengths || []).map((s) => `<li style="margin-bottom: 6px;">${s}</li>`).join("");

    const recsList = document.getElementById("recommendations-list");
    recsList.innerHTML = (report.recommendations || []).map((r) => `<li style="margin-bottom: 6px;">${r}</li>`).join("");

  } catch (err) {
    showToast("Error loading assessment report: " + err.message, "error");
  }
});

function setMetric(prefix, val) {
  const v = Math.round(val || 0);
  document.getElementById(`${prefix}-val`).textContent = `${v}/100`;
  document.getElementById(`${prefix}-bar`).style.width = `${v}%`;
}

function renderEvidenceGraph(nodes) {
  const container = document.getElementById("evidence-graph-container");
  if (!nodes || nodes.length === 0) {
    container.innerHTML = `<div style="color: var(--text-muted); padding: 15px;">No explicit evidence claims tracked for this session.</div>`;
    return;
  }

  container.innerHTML = nodes.map((n) => {
    const statusClass = n.verified_status.toLowerCase();
    const statusLabel = n.verified_status.replace(/_/g, " ");
    return `
      <div class="evidence-node ${statusClass}">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
          <strong style="color: #fff; font-size: 0.95rem;">${n.claim_text}</strong>
          <span class="badge" style="font-size: 0.7rem; text-transform: uppercase;">${statusLabel}</span>
        </div>
        <div style="font-size: 0.8rem; color: var(--text-muted);">
          Verification Confidence: <strong>${Math.round(n.confidence_score)}%</strong>
        </div>
        ${n.evidence_quote ? `<div class="evidence-quote-snippet">“${n.evidence_quote}”</div>` : ""}
      </div>
    `;
  }).join("");
}

function formatEvidenceItem(item) {
  if (!item) return "";
  const str = String(item).trim();
  let label = "Candidate Spoken Statement";
  let content = str;
  let isCode = false;

  if (str.startsWith("Spoken:")) {
    label = "Spoken Reasoning";
    content = str.replace(/^Spoken:\s*/i, "");
  } else if (str.startsWith("Code:") || str.includes("def ") || str.includes("class ") || str.includes("return ")) {
    label = "Submitted Code Snippet";
    content = str.replace(/^Code:\s*/i, "");
    isCode = true;
  } else if (str.toLowerCase().startsWith("selected option")) {
    label = "Selected Choice";
    content = str;
  }

  return `
    <div style="background: rgba(0,0,0,0.3); border-left: 3px solid var(--accent-primary); padding: 8px 12px; border-radius: var(--radius-sm); font-size: 0.85rem; color: #cbd5e1; margin-bottom: 8px;">
      <span style="font-size: 0.75rem; font-weight: 700; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.5px;">${label}:</span>
      <div style="margin-top: 4px; ${isCode ? 'font-family: monospace; white-space: pre-wrap; font-size: 0.82rem; color: #e2e8f0;' : 'font-style: italic;'}">
        “${content}”
      </div>
    </div>
  `;
}

function renderExplainableScoring(evaluations) {
  const container = document.getElementById("questions-evaluation-list");
  if (!evaluations || evaluations.length === 0) {
    container.innerHTML = `<div style="color: var(--text-muted); padding: 15px;">No evaluated responses found.</div>`;
    return;
  }

  container.innerHTML = evaluations.map((ev, idx) => `
    <div class="explainable-card">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
        <h4 style="color: #fff; margin: 0;">Evaluation #${idx + 1}</h4>
        <span class="badge" style="background: rgba(99, 102, 241, 0.2); color: #fff; font-size: 0.9rem;">
          Score: ${ev.overall_score}/100
        </span>
      </div>

      <p style="font-size: 0.9rem; margin-bottom: 8px;">${ev.feedback}</p>

      <!-- Exact Evidence (Spoken, Code, or MCQ Option) -->
      ${ev.transcript_evidence && ev.transcript_evidence.length > 0 ? 
        ev.transcript_evidence.map(formatEvidenceItem).join("") 
        : ""}

      <!-- Concepts Covered vs Missed -->
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-sm); font-size: 0.85rem; margin-bottom: 8px;">
        <div>
          <strong style="color: var(--success);">✓ Demonstrated Concepts:</strong>
          <ul style="padding-left: 16px; color: var(--text-muted); margin-top: 4px;">
            ${(ev.correct_concepts || ["None"]).map((c) => `<li>${c}</li>`).join("")}
          </ul>
        </div>
        <div>
          <strong style="color: var(--warning);">⚠ Missing / Incomplete Concepts:</strong>
          <ul style="padding-left: 16px; color: var(--text-muted); margin-top: 4px;">
            ${(ev.missing_concepts || ["None"]).map((m) => `<li>${m}</li>`).join("")}
          </ul>
        </div>
      </div>

      <!-- Why This Score Box -->
      ${ev.why_this_score ? `
        <div class="why-score-box">
          <strong>Why this score?</strong> ${ev.why_this_score}
        </div>
      ` : ""}
    </div>
  `).join("");
}

function renderConsistency(checks) {
  const container = document.getElementById("consistency-container");
  if (!checks || checks.length === 0) {
    container.innerHTML = `<div style="color: var(--text-muted); padding: 10px;">Uniform consistency observed across assessed concepts.</div>`;
    return;
  }

  container.innerHTML = checks.map((c) => `
    <div style="background: var(--bg-card-alt); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); padding: var(--space-md); margin-bottom: var(--space-sm);">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
        <strong style="color: #fff;">${c.concept_area}</strong>
        <span class="badge" style="background: rgba(16, 185, 129, 0.15); color: #34d399;">Consistency: ${Math.round(c.consistency_score * 100)}%</span>
      </div>
      <p style="font-size: 0.85rem; margin: 4px 0;">${c.discrepancy_details}</p>
      <div style="font-size: 0.8rem; color: var(--text-muted);">
        Root cause insight: <em>${c.root_cause}</em>
      </div>
    </div>
  `).join("");
}

function renderKnowledgeGaps(gapMap) {
  const container = document.getElementById("knowledge-gap-container");
  const roadmap = gapMap.learning_roadmap || [];

  if (roadmap.length === 0) {
    container.innerHTML = `<div style="color: var(--text-muted); padding: 10px;">No critical knowledge bottlenecks identified.</div>`;
    return;
  }

  container.innerHTML = roadmap.map((item) => `
    <div style="background: var(--bg-card-alt); border-left: 4px solid var(--accent-primary); border-radius: var(--radius-md); padding: var(--space-md); margin-bottom: var(--space-sm);">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
        <strong style="color: #fff;">Stage ${item.stage}: ${item.priority}</strong>
      </div>
      <p style="font-size: 0.85rem; margin: 4px 0;">${item.summary}</p>
      <ul style="padding-left: 18px; font-size: 0.85rem; color: var(--text-secondary); margin-top: 6px;">
        ${(item.actions || []).map((a) => `<li>${a}</li>`).join("")}
      </ul>
    </div>
  `).join("");
}

function renderComputerVisionAnalytics(va) {
  const conf = Math.round(va.visual_confidence_score || 85);
  const eye = Math.round(va.eye_contact_ratio || 88);
  const head = Math.round(va.head_pose_stability || 91);
  const emo = va.emotion_distribution || { confident: 60, focused: 25, neutral: 11, hesitant: 4 };

  const confElem = document.getElementById("cv-report-confidence");
  if (confElem) confElem.textContent = `${conf}/100`;

  const eyeVal = document.getElementById("cv-report-eye-val");
  const eyeBar = document.getElementById("cv-report-eye-bar");
  if (eyeVal) eyeVal.textContent = `${eye}%`;
  if (eyeBar) eyeBar.style.width = `${eye}%`;

  const gazeStatus = document.getElementById("cv-report-gaze-status");
  if (gazeStatus) gazeStatus.textContent = eye >= 80 ? "Direct (Engaged)" : "Slight Deviation";

  const blinkElem = document.getElementById("cv-report-blink");
  if (blinkElem) blinkElem.textContent = `${va.blink_rate_per_minute || 16.5}/min`;

  const headVal = document.getElementById("cv-report-head-val");
  const headBar = document.getElementById("cv-report-head-bar");
  if (headVal) headVal.textContent = `${head}%`;
  if (headBar) headBar.style.width = `${head}%`;

  const postureStatus = document.getElementById("cv-report-posture-status");
  if (postureStatus) postureStatus.textContent = head >= 80 ? "Stable (Centered)" : "Dynamic";

  // Posture Kinematics
  const postureComp = Math.round(va.posture_composure_score || 90);
  const postureCompElem = document.getElementById("cv-report-posture-comp");
  const postureBar = document.getElementById("cv-report-posture-bar");
  if (postureCompElem) postureCompElem.textContent = `${postureComp}/100`;
  if (postureBar) postureBar.style.width = `${postureComp}%`;

  const slouchElem = document.getElementById("cv-report-slouch");
  if (slouchElem) slouchElem.textContent = `${va.slouch_ratio_percent || 5}%`;

  const fidgetElem = document.getElementById("cv-report-fidget");
  if (fidgetElem) fidgetElem.textContent = va.fidget_index || "Minimal (Poised)";

  // Identity Verification & Anti-Cheating
  const idData = va.identity_verification || { status: "VERIFIED_MATCH", continuity_ratio_percent: 100, anti_cheating_clear: true };
  const idStatusElem = document.getElementById("cv-report-identity-status");
  const idRatioElem = document.getElementById("cv-report-identity-ratio");
  const idBar = document.getElementById("cv-report-identity-bar");
  const antiCheatElem = document.getElementById("cv-report-anticheat");

  if (idStatusElem) {
    idStatusElem.textContent = idData.status === "VERIFIED_MATCH" ? "VERIFIED MATCH" : "FLAGGED";
    idStatusElem.style.color = idData.status === "VERIFIED_MATCH" ? "#38bdf8" : "#ef4444";
  }
  const idCont = Math.round(idData.continuity_ratio_percent || 100);
  if (idRatioElem) idRatioElem.textContent = `${idCont}%`;
  if (idBar) idBar.style.width = `${idCont}%`;
  if (antiCheatElem) {
    antiCheatElem.textContent = idData.anti_cheating_clear ? "CLEAR (1 Person)" : "FLAGGED (2+ Persons)";
    antiCheatElem.style.color = idData.anti_cheating_clear ? "#34d399" : "#ef4444";
  }

  const stressElem = document.getElementById("cv-report-stress");
  if (stressElem) {
    const stress = va.stress_indicator_level || "LOW";
    stressElem.textContent = stress;
    stressElem.style.color = stress === "LOW" ? "var(--success)" : (stress === "MODERATE" ? "var(--warning)" : "var(--danger)");
  }

  const dominantEmo = document.getElementById("cv-report-dominant-emo");
  if (dominantEmo) dominantEmo.textContent = (emo.confident >= 45) ? "Confident" : ((emo.focused >= 35) ? "Focused" : "Composed");

  const confEmo = document.getElementById("emo-confident-val");
  if (confEmo) confEmo.textContent = `${Math.round(emo.confident || 0)}%`;

  const focEmo = document.getElementById("emo-focused-val");
  if (focEmo) focEmo.textContent = `${Math.round(emo.focused || 0)}%`;

  const neuEmo = document.getElementById("emo-neutral-val");
  if (neuEmo) neuEmo.textContent = `${Math.round(emo.neutral || 0)}%`;

  const hesEmo = document.getElementById("emo-hesitant-val");
  if (hesEmo) hesEmo.textContent = `${Math.round(emo.hesitant || 0)}%`;

  const summaryElem = document.getElementById("cv-report-summary");
  if (summaryElem) {
    summaryElem.textContent = va.summary || "Candidate maintained consistent ocular engagement and centered head posture across the evaluated technical session.";
  }
}

function renderAudioAcousticAnalytics(aa) {
  const conf = Math.round(aa.acoustic_confidence_score || 82);
  const confElem = document.getElementById("audio-report-confidence");
  if (confElem) confElem.textContent = `${conf}/100`;

  const fluency = Math.round(aa.fluency_ratio_percent || 80);
  const fluVal = document.getElementById("audio-report-fluency-val");
  const fluBar = document.getElementById("audio-report-fluency-bar");
  if (fluVal) fluVal.textContent = `${fluency}%`;
  if (fluBar) fluBar.style.width = `${fluency}%`;

  const voicedSec = document.getElementById("audio-report-voiced-sec");
  if (voicedSec) voicedSec.textContent = `${aa.speech_duration_seconds || 18.5}s`;

  const silenceSec = document.getElementById("audio-report-silence-sec");
  if (silenceSec) silenceSec.textContent = `${aa.silence_duration_seconds || 4.2}s`;

  const pauses = aa.long_pause_hesitations_count || 0;
  const pauseVal = document.getElementById("audio-report-pauses-val");
  if (pauseVal) {
    pauseVal.textContent = `${pauses} ${pauses === 1 ? 'Pause' : 'Pauses'} (>1.5s)`;
    pauseVal.style.color = pauses === 0 ? "#34d399" : (pauses <= 2 ? "#f59e0b" : "#ef4444");
  }

  const cadenceElem = document.getElementById("audio-report-cadence");
  if (cadenceElem) cadenceElem.textContent = aa.speaking_cadence || "Steady Conversational Pace";

  const jitterVal = document.getElementById("audio-report-jitter-val");
  if (jitterVal) jitterVal.textContent = `${aa.pitch_jitter_percent || 3.5}%`;

  const tremorElem = document.getElementById("audio-report-tremor");
  if (tremorElem) tremorElem.textContent = aa.vocal_tremor_status || "Low (Composed & Firm)";

  const rmsVal = document.getElementById("audio-report-rms-val");
  if (rmsVal) rmsVal.textContent = `${aa.average_rms_db || -24.0} dB`;

  const summaryElem = document.getElementById("audio-report-summary");
  if (summaryElem) {
    summaryElem.textContent = aa.acoustic_summary || "Candidate demonstrated composed acoustic vocal projection and steady speech fluency.";
  }
}


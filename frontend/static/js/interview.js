import { apiRequest, showToast } from "./api.js";
import { CameraPreview } from "./camera-preview.js";
import { AudioRecorder } from "./audio-recorder.js";

let interviewId = null;
let currentQuestion = null;
let camera = null;
let recorder = null;
let recordedAudioData = null;
let selectedOption = null;
let nextQuestionAvailable = false;
let isInterviewCompleted = false;

function formatTime(seconds) {
  const sec = Math.max(0, Math.floor(seconds || 0));
  const m = Math.floor(sec / 60).toString().padStart(2, "0");
  const s = (sec % 60).toString().padStart(2, "0");
  return `${m}:${s}`;
}

document.addEventListener("DOMContentLoaded", async () => {
  const urlParams = new URLSearchParams(window.location.search);
  interviewId = urlParams.get("id");

  if (!interviewId) {
    showToast("No interview ID specified. Redirecting to dashboard.", "error");
    setTimeout(() => { window.location.href = "/dashboard"; }, 1000);
    return;
  }

  // Setup Camera Preview with Computer Vision (CV) HUD
  const videoElem = document.getElementById("live-video");
  const placeholder = document.getElementById("live-cam-placeholder");
  const cvCanvas = document.getElementById("cv-hud-canvas");
  camera = new CameraPreview(videoElem, placeholder, cvCanvas, interviewId);
  camera.start().catch(() => {});

  document.getElementById("toggle-cam-live").addEventListener("click", () => {
    camera.toggle();
  });

  // Setup Audio Recorder with VU Meter & Real-time Web Speech transcription
  const vuBar = document.getElementById("live-vu-bar");
  const vuText = document.getElementById("live-vu-text");
  const timerDisplay = document.getElementById("timer-display");
  const recIndicator = document.getElementById("rec-indicator");
  const liveTranscriptBox = document.getElementById("speech-live-box");
  const liveTranscriptStream = document.getElementById("live-transcript-stream");

  recorder = new AudioRecorder({
    onLevelChange: (level) => {
      vuBar.style.width = `${level}%`;
      vuText.textContent = `${level}%`;
    },
    onTimeUpdate: (secs) => {
      timerDisplay.textContent = formatTime(secs);
    },
    onStateChange: (state) => {
      if (state === "RECORDING") {
        recIndicator.style.display = "flex";
        liveTranscriptBox.style.display = "block";
      } else {
        recIndicator.style.display = "none";
      }
    },
    onTranscriptUpdate: (fullText, interim) => {
      liveTranscriptStream.textContent = (fullText + " " + interim).trim() || "Listening for your voice...";
    }
  });

  // Load Interview and Current Question
  await loadCurrentQuestion();

  // Attach button event listeners
  setupActionButtons();
});

async function loadCurrentQuestion() {
  try {
    const interview = await apiRequest(`/api/interviews/${interviewId}`);
    
    if (interview.state === "COMPLETED") {
      window.location.href = `/report?id=${interviewId}`;
      return;
    }

    // Update Difficulty Badge
    const diffBadge = document.getElementById("difficulty-badge");
    diffBadge.textContent = interview.current_difficulty;
    diffBadge.className = `badge badge-${interview.current_difficulty.toLowerCase()}`;

    // Update Progress
    const total = interview.total_questions;
    const currentIdx = interview.current_question_index || 1;
    document.getElementById("progress-text").textContent = `Question ${currentIdx} of ${total}`;
    const pct = Math.round((currentIdx / total) * 100);
    document.getElementById("progress-fill").style.width = `${pct}%`;

    // Fetch Question details
    currentQuestion = await apiRequest(`/api/interviews/${interviewId}/current-question`);

    // Basic question info
    document.getElementById("q-label").textContent = `Question ${currentQuestion.order_index} ${currentQuestion.is_followup ? "• Dynamic Follow-up" : ""}`;
    document.getElementById("q-text").textContent = currentQuestion.question_text;
    document.getElementById("q-skill").textContent = currentQuestion.skill_assessed;
    document.getElementById("q-category").textContent = (currentQuestion.category || "TECHNICAL").replace(/_/g, " ").toUpperCase();

    // Render by Question Type (SPOKEN, MCQ, CODE)
    renderQuestionByType(currentQuestion);

    // Reset recorder & feedback UI
    resetRecorderUI();
  } catch (err) {
    showToast("Error loading question: " + err.message, "error");
  }
}

function formatStarterCode(rawSnippet, question) {
  let snippet = (rawSnippet || "def solve(*args, **kwargs):\n    pass\n").trim();

  // Check if question is "Correct the code" / Refactor / Bugfix challenge
  const qText = (question && question.question_text ? question.question_text.toLowerCase() : "");
  const skill = (question && question.skill_assessed ? question.skill_assessed.toLowerCase() : "");
  const isBugfixOrRefactor = (
    qText.includes("fix") ||
    qText.includes("correct") ||
    qText.includes("bug") ||
    qText.includes("refactor") ||
    qText.includes("blocking") ||
    qText.includes("defect") ||
    qText.includes("optimize the following") ||
    skill.includes("debugging") ||
    skill.includes("refactor") ||
    (!snippet.includes("pass") && snippet.includes("def "))
  );

  if (isBugfixOrRefactor) {
    // Mode 2: "Correct the code" -> in second nothing! NO starter comment!
    snippet = snippet.replace(/#\s*-{4,}\s*\n\s*#\s*>>>\s*START YOUR CODE HERE\s*<<<\s*\n\s*#\s*-{4,}\s*\n?/gi, "");
    snippet = snippet.replace(/#\s*>>>\s*START YOUR CODE HERE\s*<<<\s*\n?/gi, "");
    return snippet.trim();
  }

  // Mode 1: DSA Problem (Array, LinkedList, String, etc.) -> starter comment required
  if (!snippet.includes("START YOUR CODE HERE") && !snippet.includes("WRITE YOUR SOLUTION")) {
    if (snippet.includes("pass")) {
      snippet = snippet.replace("pass", "# -----------------------------------------------------\n    # >>> START YOUR CODE HERE <<<\n    # -----------------------------------------------------\n    pass");
    } else {
      snippet += "\n\n    # -----------------------------------------------------\n    # >>> START YOUR CODE HERE <<<\n    # -----------------------------------------------------\n    pass\n";
    }
  }
  return snippet;
}

function renderQuestionByType(question) {
  const typeBadge = document.getElementById("q-type-badge");
  const mcqContainer = document.getElementById("mcq-container");
  const codeContainer = document.getElementById("code-container");
  const qType = question.question_type || "SPOKEN";
  selectedOption = null;

  if (qType === "MCQ") {
    typeBadge.textContent = "MULTIPLE CHOICE (MCQ)";
    typeBadge.style.background = "rgba(16, 185, 129, 0.2)";
    typeBadge.style.color = "#34d399";
    mcqContainer.style.display = "block";
    codeContainer.style.display = "none";
    renderMcqOptions(question.options || []);
    document.getElementById("recorder-instruction").innerHTML = "Select an option above. You can optionally click <strong>Start Spoken Answer</strong> to articulate your reasoning.";
    // Enable submit section right away for convenience
    document.getElementById("playback-section").style.display = "block";
    document.getElementById("audio-playback").style.display = "none";
  } else if (qType === "CODE") {
    typeBadge.textContent = "PRACTICAL CODE CHALLENGE";
    typeBadge.style.background = "rgba(168, 85, 247, 0.2)";
    typeBadge.style.color = "#c084fc";
    mcqContainer.style.display = "none";
    codeContainer.style.display = "block";
    document.getElementById("code-lang-label").textContent = (question.language || "python").toUpperCase();
    document.getElementById("code-editor").value = formatStarterCode(question.code_snippet, question);
    document.getElementById("recorder-instruction").innerHTML = "Type your solution above and click <strong>▶ Run Code</strong> to test against test cases. Optionally articulate your complexity out loud.";
    document.getElementById("playback-section").style.display = "block";
    document.getElementById("audio-playback").style.display = "none";
    renderCodeDetails(question);
  } else {
    typeBadge.textContent = "SPOKEN DEEP DIVE";
    typeBadge.style.background = "rgba(99, 102, 241, 0.2)";
    typeBadge.style.color = "#a5b4fc";
    mcqContainer.style.display = "none";
    codeContainer.style.display = "none";
    document.getElementById("recorder-instruction").innerHTML = "Click <strong>Start Spoken Answer</strong> and explain your approach out loud.";
    document.getElementById("playback-section").style.display = "none";
  }
}

function escapeHtml(str) {
  if (str === null || str === undefined) return "";
  if (typeof str !== "string") str = typeof str === "object" ? JSON.stringify(str) : String(str);
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function renderCodeDetails(question) {
  // 1. Render Examples
  const exSection = document.getElementById("code-examples-section");
  const exList = document.getElementById("code-examples-list");
  if (question.examples && question.examples.length > 0) {
    exList.innerHTML = "";
    question.examples.forEach((ex, idx) => {
      const card = document.createElement("div");
      card.style.cssText = "background: #0f172a; border: 1px solid var(--border-subtle); border-radius: var(--radius-md); padding: 10px 14px; font-size: 0.85rem;";
      card.innerHTML = `
        <div style="font-weight: 700; color: #93c5fd; margin-bottom: 4px;">Example ${idx + 1}:</div>
        <div style="margin-bottom: 3px;"><strong style="color: #94a3b8;">Input:</strong> <code style="color: #f1f5f9; background: #020617; padding: 2px 6px; border-radius: 4px;">${escapeHtml(ex.input)}</code></div>
        <div style="margin-bottom: 3px;"><strong style="color: #94a3b8;">Output:</strong> <code style="color: #34d399; background: #020617; padding: 2px 6px; border-radius: 4px;">${escapeHtml(ex.output)}</code></div>
        ${ex.explanation ? `<div style="color: #cbd5e1; margin-top: 4px;"><strong style="color: #94a3b8;">Explanation:</strong> ${escapeHtml(ex.explanation)}</div>` : ""}
      `;
      exList.appendChild(card);
    });
    exSection.style.display = "block";
  } else {
    exSection.style.display = "none";
  }

  // 2. Render Constraints
  const constSection = document.getElementById("code-constraints-section");
  const constList = document.getElementById("code-constraints-list");
  if (question.constraints && question.constraints.length > 0) {
    constList.innerHTML = "";
    question.constraints.forEach((c) => {
      const li = document.createElement("li");
      li.textContent = c;
      constList.appendChild(li);
    });
    constSection.style.display = "block";
  } else {
    constSection.style.display = "none";
  }

  // 3. Reset Drawer State
  document.getElementById("test-case-tabs").innerHTML = "";
  document.getElementById("test-overall-banner").style.display = "none";
  document.getElementById("test-case-empty").style.display = "block";
  document.getElementById("test-case-details").style.display = "none";
  document.getElementById("test-console-view").style.display = "none";
  const statusPill = document.getElementById("code-status-pill");
  if (statusPill) {
    statusPill.textContent = "● Ready";
    statusPill.style.color = "#94a3b8";
  }
}

async function executeRunCode() {
  const runBtn = document.getElementById("run-code-btn");
  const codeEditor = document.getElementById("code-editor");
  const statusPill = document.getElementById("code-status-pill");
  const code = codeEditor.value;

  if (!code || !code.trim()) {
    showToast("Please write or modify your code before running tests.", "warning");
    return;
  }

  runBtn.disabled = true;
  runBtn.innerHTML = `<span>⏳ Running...</span>`;
  statusPill.textContent = "● Executing Sandbox...";
  statusPill.style.color = "#f59e0b";

  try {
    const res = await apiRequest(`/api/interviews/${interviewId}/answers/run-code/${currentQuestion.id}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        code: code,
        language: currentQuestion.language || "python"
      })
    });

    statusPill.textContent = res.all_passed ? "● All Tests Passed" : "● Tests Finished";
    statusPill.style.color = res.all_passed ? "#10b981" : "#ef4444";

    renderTestResultsDrawer(res);
    showToast(res.all_passed ? "All test cases passed!" : "Some test cases failed.", res.all_passed ? "success" : "warning");
  } catch (err) {
    statusPill.textContent = "● Execution Error";
    statusPill.style.color = "#ef4444";
    showToast("Code execution error: " + err.message, "error");
  } finally {
    runBtn.disabled = false;
    runBtn.innerHTML = `<span>▶ Run Code</span>`;
  }
}

function renderTestResultsDrawer(res) {
  const tabsContainer = document.getElementById("test-case-tabs");
  const banner = document.getElementById("test-overall-banner");
  const emptyMsg = document.getElementById("test-case-empty");
  const details = document.getElementById("test-case-details");
  const consoleView = document.getElementById("test-console-view");
  const consoleOutput = document.getElementById("console-output");

  emptyMsg.style.display = "none";
  banner.style.display = "block";

  if (res.all_passed) {
    banner.style.background = "rgba(16, 185, 129, 0.15)";
    banner.style.color = "#34d399";
    banner.innerHTML = `✓ Accepted — ${res.passed_cases}/${res.total_cases} Test Cases Passed (${(res.runtime_ms || 1.0).toFixed(1)} ms)`;
  } else if (res.error) {
    banner.style.background = "rgba(239, 68, 68, 0.15)";
    banner.style.color = "#f87171";
    banner.innerHTML = `✗ Execution Error: ${escapeHtml(res.error)}`;
  } else {
    banner.style.background = "rgba(239, 68, 68, 0.15)";
    banner.style.color = "#f87171";
    banner.innerHTML = `✗ Wrong Answer — ${res.passed_cases}/${res.total_cases} Test Cases Passed (${(res.runtime_ms || 1.0).toFixed(1)} ms)`;
  }

  consoleOutput.textContent = res.stdout || "(No stdout output)";

  tabsContainer.innerHTML = "";
  if (res.results && res.results.length > 0) {
    res.results.forEach((tc, idx) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "btn btn-sm";
      btn.style.cssText = `
        background: ${idx === 0 ? "rgba(99, 102, 241, 0.25)" : "transparent"};
        color: ${idx === 0 ? "#fff" : "#94a3b8"};
        font-size: 0.75rem;
        padding: 4px 10px;
        border-radius: 4px;
        display: flex;
        align-items: center;
        gap: 6px;
      `;
      const isPassed = tc.status === "PASSED";
      btn.innerHTML = `
        <span style="color: ${isPassed ? "#34d399" : "#f87171"}; font-weight: 700;">${isPassed ? "✓" : "✗"}</span>
        <span>Case ${idx + 1}</span>
      `;

      btn.addEventListener("click", () => {
        tabsContainer.querySelectorAll("button").forEach(b => {
          b.style.background = "transparent";
          b.style.color = "#94a3b8";
        });
        document.getElementById("test-console-tab").style.background = "transparent";
        document.getElementById("test-console-tab").style.color = "#94a3b8";
        btn.style.background = "rgba(99, 102, 241, 0.25)";
        btn.style.color = "#fff";
        showTestCaseDetails(tc);
      });

      tabsContainer.appendChild(btn);
    });

    showTestCaseDetails(res.results[0]);
  } else {
    details.style.display = "none";
    consoleView.style.display = "block";
  }
}

function showTestCaseDetails(tc) {
  document.getElementById("test-case-details").style.display = "block";
  document.getElementById("test-console-view").style.display = "none";
  document.getElementById("tc-input").textContent = tc.input || "N/A";
  document.getElementById("tc-expected").textContent = typeof tc.expected === "object" ? JSON.stringify(tc.expected) : String(tc.expected || "N/A");
  
  const actualPre = document.getElementById("tc-actual");
  actualPre.textContent = typeof tc.actual === "object" ? JSON.stringify(tc.actual) : String(tc.actual || "N/A");
  if (tc.status === "PASSED") {
    actualPre.style.color = "#34d399";
  } else {
    actualPre.style.color = "#f87171";
  }

  document.getElementById("tc-runtime").textContent = `Runtime: ${tc.runtime_ms || 1.0} ms`;
}

function renderMcqOptions(options) {
  const list = document.getElementById("mcq-options-list");
  list.innerHTML = "";

  options.forEach((opt) => {
    const card = document.createElement("div");
    card.className = "mcq-option-card";
    card.style.cssText = `
      background: var(--bg-card);
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-md);
      padding: 12px 16px;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 12px;
      transition: all var(--transition-fast);
    `;
    card.setAttribute("data-opt-id", opt.id);
    card.innerHTML = `
      <div style="width: 28px; height: 28px; border-radius: 50%; background: var(--bg-card-alt); border: 1px solid var(--border-subtle); display: flex; align-items: center; justify-content: center; font-weight: 700; color: #fff; font-size: 0.85rem;">
        ${opt.id}
      </div>
      <div style="flex: 1; font-size: 0.95rem; color: #f1f5f9;">${opt.text}</div>
    `;

    card.addEventListener("click", () => {
      document.querySelectorAll(".mcq-option-card").forEach((c) => {
        c.style.borderColor = "var(--border-subtle)";
        c.style.background = "var(--bg-card)";
      });
      card.style.borderColor = "var(--accent-primary)";
      card.style.background = "rgba(99, 102, 241, 0.12)";
      selectedOption = opt.id;
      showToast(`Selected Option ${opt.id}`, "info");
    });

    list.appendChild(card);
  });
}

function resetRecorderUI() {
  recorder.reset();
  document.getElementById("recorder-card").style.display = "flex";
  document.getElementById("processing-card").style.display = "none";
  document.getElementById("feedback-card").style.display = "none";
  document.getElementById("speech-live-box").style.display = "none";
  document.getElementById("live-transcript-stream").textContent = "Listening for your voice...";
  document.getElementById("confirmed-transcript").value = "";
  document.getElementById("record-btn").style.display = "inline-flex";
  document.getElementById("stop-btn").style.display = "none";
  document.getElementById("timer-display").textContent = "00:00";
  recordedAudioData = null;

  if (currentQuestion && currentQuestion.question_type === "SPOKEN") {
    document.getElementById("playback-section").style.display = "none";
    document.getElementById("audio-playback").style.display = "none";
  }
}

function setupActionButtons() {
  const recordBtn = document.getElementById("record-btn");
  const stopBtn = document.getElementById("stop-btn");
  const retryBtn = document.getElementById("retry-btn");
  const submitBtn = document.getElementById("submit-btn");
  const nextQBtn = document.getElementById("next-q-btn");
  const endBtn = document.getElementById("end-interview-btn");
  const resetCodeBtn = document.getElementById("reset-code-btn");

  if (resetCodeBtn) {
    resetCodeBtn.addEventListener("click", () => {
      if (currentQuestion && currentQuestion.code_snippet) {
        document.getElementById("code-editor").value = formatStarterCode(currentQuestion.code_snippet, currentQuestion);
        showToast("Code reset to starter template.", "info");
      }
    });
  }

  // Handle Tab Key Indentation in Code Editor
  const codeEditor = document.getElementById("code-editor");
  if (codeEditor) {
    codeEditor.addEventListener("keydown", (e) => {
      if (e.key === "Tab") {
        e.preventDefault();
        const start = codeEditor.selectionStart;
        const end = codeEditor.selectionEnd;
        codeEditor.value = codeEditor.value.substring(0, start) + "    " + codeEditor.value.substring(end);
        codeEditor.selectionStart = codeEditor.selectionEnd = start + 4;
      }
    });
  }

  // Handle ▶ Run Code Test Runner
  const runCodeBtn = document.getElementById("run-code-btn");
  if (runCodeBtn) {
    runCodeBtn.addEventListener("click", executeRunCode);
  }

  // Handle Stdout Console Tab Toggle
  const testConsoleTab = document.getElementById("test-console-tab");
  if (testConsoleTab) {
    testConsoleTab.addEventListener("click", () => {
      document.querySelectorAll("#test-case-tabs button").forEach(b => {
        b.style.background = "transparent";
        b.style.color = "#94a3b8";
      });
      testConsoleTab.style.background = "rgba(99, 102, 241, 0.25)";
      testConsoleTab.style.color = "#fff";
      document.getElementById("test-case-details").style.display = "none";
      document.getElementById("test-console-view").style.display = "block";
    });
  }

  recordBtn.addEventListener("click", async () => {
    try {
      await recorder.start();
      recordBtn.style.display = "none";
      stopBtn.style.display = "inline-flex";
      document.getElementById("recorder-instruction").textContent = "Recording spoken answer... Speak clearly into your microphone.";
    } catch (err) {
      showToast("Cannot record: " + err.message, "error");
    }
  });

  stopBtn.addEventListener("click", async () => {
    recordedAudioData = await recorder.stop();
    stopBtn.style.display = "none";
    recordBtn.style.display = "inline-flex";

    document.getElementById("playback-section").style.display = "block";
    const player = document.getElementById("audio-playback");
    if (recordedAudioData && recordedAudioData.blob) {
      player.src = URL.createObjectURL(recordedAudioData.blob);
      player.style.display = "block";
    }

    // Prefill confirmed transcript with browser-native real-time recognition
    const confirmedBox = document.getElementById("confirmed-transcript");
    if (recordedAudioData && recordedAudioData.browserTranscript) {
      confirmedBox.value = recordedAudioData.browserTranscript;
    }
    document.getElementById("recorder-instruction").textContent = "Spoken answer captured. Review or adjust your transcript below, then submit.";
  });

  retryBtn.addEventListener("click", () => {
    resetRecorderUI();
    if (currentQuestion && ["MCQ", "CODE"].includes(currentQuestion.question_type)) {
      document.getElementById("playback-section").style.display = "block";
    }
  });

  submitBtn.addEventListener("click", async () => {
    const qType = currentQuestion.question_type || "SPOKEN";

    // Validate inputs
    if (qType === "MCQ" && !selectedOption && !recordedAudioData) {
      showToast("Please choose an answer option or record your explanation.", "error");
      return;
    }

    const confirmedTranscript = document.getElementById("confirmed-transcript").value.trim();
    const codeSubmission = (qType === "CODE") ? document.getElementById("code-editor").value : null;

    // Switch to processing view
    document.getElementById("recorder-card").style.display = "none";
    document.getElementById("processing-card").style.display = "flex";

    const formData = new FormData();
    formData.append("question_id", currentQuestion.id);
    formData.append("duration_seconds", recordedAudioData ? (recordedAudioData.durationSeconds || 10) : 0);
    if (recordedAudioData && recordedAudioData.blob) {
      formData.append("audio_file", recordedAudioData.blob, "answer.webm");
    }
    if (confirmedTranscript) {
      formData.append("browser_transcript", confirmedTranscript);
    }
    if (selectedOption) {
      formData.append("selected_option", selectedOption);
    }
    if (codeSubmission) {
      formData.append("code_submission", codeSubmission);
    }

    try {
      const result = await fetch(`/api/interviews/${interviewId}/answers/audio`, {
        method: "POST",
        body: formData
      });

      if (!result.ok) {
        const err = await result.json();
        throw new Error(err.error || "Submission failed");
      }

      const evalData = await result.json();
      nextQuestionAvailable = evalData.next_question_available;
      isInterviewCompleted = evalData.is_interview_completed;

      // Show Feedback Card
      document.getElementById("processing-card").style.display = "none";
      const fbCard = document.getElementById("feedback-card");
      fbCard.style.display = "block";

      const scoreBadge = document.getElementById("fb-score-badge");
      const roundScore = Math.round(evalData.overall_score || 0);
      scoreBadge.textContent = `Score: ${roundScore}/100`;

      if (roundScore < 50) {
        scoreBadge.style.background = "rgba(239, 68, 68, 0.2)";
        scoreBadge.style.color = "#f87171";
        scoreBadge.style.border = "1px solid rgba(239, 68, 68, 0.4)";
        fbCard.style.borderLeft = "4px solid #ef4444";
      } else if (roundScore < 75) {
        scoreBadge.style.background = "rgba(245, 158, 11, 0.2)";
        scoreBadge.style.color = "#fbbf24";
        scoreBadge.style.border = "1px solid rgba(245, 158, 11, 0.4)";
        fbCard.style.borderLeft = "4px solid #f59e0b";
      } else {
        scoreBadge.style.background = "rgba(16, 185, 129, 0.2)";
        scoreBadge.style.color = "#34d399";
        scoreBadge.style.border = "1px solid rgba(16, 185, 129, 0.4)";
        fbCard.style.borderLeft = "4px solid #10b981";
      }

      const explBox = document.getElementById("fb-explanation-box");
      if (evalData.is_correct !== null && evalData.is_correct !== undefined) {
        explBox.innerHTML = evalData.is_correct
          ? `<span style="color: #34d399; font-weight: 700;">✓ Correct!</span> Option ${evalData.selected_option}. ${evalData.explanation || ""}`
          : `<span style="color: #f87171; font-weight: 700;">✗ Incorrect.</span> You selected Option ${evalData.selected_option}. Correct is Option ${evalData.correct_option}. ${evalData.explanation || ""}`;
      } else if (evalData.code_feedback) {
        explBox.innerHTML = `<span style="color: #a5b4fc; font-weight: 600;">Code Evaluation:</span> ${evalData.code_feedback}`;
      } else {
        explBox.innerHTML = `<span style="color: #34d399; font-weight: 600;">Spoken Assessment:</span> Evaluation recorded against expected concepts.`;
      }

      document.getElementById("fb-text").textContent = evalData.feedback || "Good progress.";

      // Real-time Adaptive Engine Feedback
      if (evalData.current_difficulty) {
        const diffBadge = document.getElementById("difficulty-badge");
        if (diffBadge && diffBadge.textContent.trim() !== evalData.current_difficulty.trim()) {
          const oldDiff = diffBadge.textContent.trim();
          diffBadge.textContent = evalData.current_difficulty;
          diffBadge.className = `badge badge-${evalData.current_difficulty.toLowerCase()}`;
          diffBadge.style.transition = "transform 0.3s ease, box-shadow 0.3s ease";
          diffBadge.style.transform = "scale(1.2)";
          setTimeout(() => { diffBadge.style.transform = "scale(1.0)"; }, 400);
          showToast(`⚡ Adaptive Engine: Difficulty calibrated from ${oldDiff} to ${evalData.current_difficulty} based on response score (${Math.round(evalData.overall_score)}/100)!`, "info");
        }
      }

      nextQBtn.textContent = isInterviewCompleted ? "Complete Interview & View Assessment Report →" : "Next Question →";
      fbCard.scrollIntoView({ behavior: "smooth" });
    } catch (err) {
      showToast("Evaluation error: " + err.message, "error");
      document.getElementById("recorder-card").style.display = "flex";
      document.getElementById("processing-card").style.display = "none";
    }
  });

  nextQBtn.addEventListener("click", async () => {
    if (isInterviewCompleted) {
      showToast("Interview concluded! Loading comprehensive report...", "success");
      setTimeout(() => {
        window.location.href = `/report?id=${interviewId}`;
      }, 500);
    } else {
      await loadCurrentQuestion();
    }
  });

  endBtn.addEventListener("click", async () => {
    if (confirm("Are you sure you want to conclude this interview session early? A report will be generated for questions answered so far.")) {
      endBtn.disabled = true;
      try {
        await apiRequest(`/api/interviews/${interviewId}/end`, { method: "POST" });
        showToast("Concluding interview...", "info");
        setTimeout(() => {
          window.location.href = `/report?id=${interviewId}`;
        }, 600);
      } catch (err) {
        endBtn.disabled = false;
        showToast("Failed to end interview: " + err.message, "error");
      }
    }
  });
}


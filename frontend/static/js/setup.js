import { apiRequest, showToast } from "./api.js";
import { CameraPreview } from "./camera-preview.js";
import { AudioRecorder } from "./audio-recorder.js";

let camera = null;
let micTester = null;
let isMicTesting = false;

document.addEventListener("DOMContentLoaded", async () => {
  const urlParams = new URLSearchParams(window.location.search);
  let resumeId = urlParams.get("resume_id");

  // If no resume_id passed, fetch latest resume from API
  if (!resumeId) {
    try {
      const interviews = await apiRequest("/api/interviews");
      if (interviews.length > 0 && interviews[0].resume_id) {
        resumeId = interviews[0].resume_id;
      }
    } catch (e) {
      console.warn("Could not find resume automatically", e);
    }
  }

  // Camera setup
  const videoElem = document.getElementById("cam-preview");
  const placeholder = document.getElementById("cam-placeholder");
  camera = new CameraPreview(videoElem, placeholder);

  const toggleCamBtn = document.getElementById("toggle-cam-btn");
  toggleCamBtn.addEventListener("click", async () => {
    if (!camera.isEnabled) {
      toggleCamBtn.textContent = "Starting...";
      const ok = await camera.start();
      toggleCamBtn.textContent = ok ? "Stop Camera" : "Test Camera";
      if (ok) showToast("Camera preview active", "success");
    } else {
      camera.stop();
      toggleCamBtn.textContent = "Test Camera";
    }
  });

  // Mic setup
  const vuBar = document.getElementById("vu-bar");
  const vuText = document.getElementById("vu-level-text");
  const testMicBtn = document.getElementById("test-mic-btn");

  micTester = new AudioRecorder({
    onLevelChange: (level) => {
      vuBar.style.width = `${level}%`;
      vuText.textContent = `${level}%`;
    }
  });

  testMicBtn.addEventListener("click", async () => {
    if (!isMicTesting) {
      try {
        testMicBtn.textContent = "Stop Mic Test";
        isMicTesting = true;
        await micTester.start();
        showToast("Speak into your microphone to verify audio levels", "info");
      } catch (err) {
        testMicBtn.textContent = "Test Microphone";
        isMicTesting = false;
        showToast("Microphone permission denied: " + err.message, "error");
      }
    } else {
      await micTester.stop();
      testMicBtn.textContent = "Test Microphone";
      isMicTesting = false;
      vuBar.style.width = "0%";
      vuText.textContent = "0%";
    }
  });

  // Dynamic Question Count Controls
  const qInput = document.getElementById("total-questions");
  const qLabel = document.getElementById("question-count-label");
  const presetBtns = document.querySelectorAll(".q-preset-btn");

  function updateQuestionCountUI(val) {
    let count = parseInt(val) || 5;
    if (count < 1) count = 1;
    if (count > 15) count = 15;
    qInput.value = count;
    if (qLabel) qLabel.textContent = `${count} ${count === 1 ? "Question" : "Questions"}`;

    presetBtns.forEach(btn => {
      const bCount = parseInt(btn.getAttribute("data-count"));
      if (bCount === count) {
        btn.classList.add("btn-primary");
        btn.classList.remove("btn-secondary");
      } else {
        btn.classList.remove("btn-primary");
        btn.classList.add("btn-secondary");
      }
    });
  }

  presetBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      const val = parseInt(btn.getAttribute("data-count"));
      updateQuestionCountUI(val);
    });
  });

  if (qInput) {
    qInput.addEventListener("input", (e) => {
      updateQuestionCountUI(e.target.value);
    });
  }

  // Start Interview action
  const startBtn = document.getElementById("start-btn");
  startBtn.addEventListener("click", async () => {
    if (!resumeId) {
      showToast("Please upload a resume first.", "error");
      setTimeout(() => { window.location.href = "/resume"; }, 1000);
      return;
    }

    startBtn.disabled = true;
    startBtn.textContent = "Generating AI Questions...";

    // Clean up hardware test streams before entering room
    if (camera.isEnabled) camera.stop();
    if (isMicTesting) await micTester.stop();

    try {
      const totalQVal = parseInt(document.getElementById("total-questions")?.value) || 5;
      const countClamped = Math.min(15, Math.max(1, totalQVal));

      const payload = {
        resume_id: parseInt(resumeId),
        target_role: document.getElementById("target-role").value,
        interview_type: document.getElementById("interview-type").value,
        initial_difficulty: document.getElementById("difficulty").value,
        question_mix: document.getElementById("question-mix") ? document.getElementById("question-mix").value : "mixed",
        total_questions: countClamped
      };

      const interview = await apiRequest("/api/interviews", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      // Start session
      await apiRequest(`/api/interviews/${interview.id}/start`, { method: "POST" });

      showToast("Interview prepared! Launching interview room...", "success");
      setTimeout(() => {
        window.location.href = `/interview?id=${interview.id}`;
      }, 600);
    } catch (err) {
      startBtn.disabled = false;
      startBtn.textContent = "Generate Personalized Questions & Start Interview →";
      showToast(err.message || "Failed to configure interview session. Please check parameters.", "error");
    }
  });
});

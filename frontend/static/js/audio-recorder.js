/**
 * Audio Recording Controller with real-time VU meter & Web Speech API recognition
 */

export class AudioRecorder {
  constructor(options = {}) {
    this.onLevelChange = options.onLevelChange || (() => {});
    this.onTimeUpdate = options.onTimeUpdate || (() => {});
    this.onStateChange = options.onStateChange || (() => {});
    this.onTranscriptUpdate = options.onTranscriptUpdate || (() => {});

    this.mediaRecorder = null;
    this.audioStream = null;
    this.audioChunks = [];
    this.audioContext = null;
    this.analyser = null;
    this.animFrameId = null;

    this.startTime = null;
    this.timerInterval = null;
    this.recordedBlob = null;
    this.durationSeconds = 0;

    // Web Speech API for real-time live transcription
    this.speechRecognizer = null;
    this.browserTranscript = "";
    this._initSpeechRecognizer();
  }

  _initSpeechRecognizer() {
    const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRec) {
      try {
        this.speechRecognizer = new SpeechRec();
        this.speechRecognizer.continuous = true;
        this.speechRecognizer.interimResults = true;
        this.speechRecognizer.lang = "en-US";

        this.speechRecognizer.onresult = (event) => {
          let interim = "";
          let finalPiece = "";
          for (let i = event.resultIndex; i < event.results.length; ++i) {
            if (event.results[i].isFinal) {
              finalPiece += event.results[i][0].transcript + " ";
            } else {
              interim += event.results[i][0].transcript;
            }
          }
          if (finalPiece) {
            this.browserTranscript = (this.browserTranscript + " " + finalPiece).trim();
          }
          this.onTranscriptUpdate(this.browserTranscript, interim);
        };

        this.speechRecognizer.onerror = (err) => {
          console.warn("Web Speech API notice:", err.error);
        };
      } catch (e) {
        console.warn("Web Speech API not initialized:", e);
      }
    }
  }

  async start() {
    this.audioChunks = [];
    this.recordedBlob = null;
    this.durationSeconds = 0;
    this.browserTranscript = "";

    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      throw new Error("Your browser does not support audio recording (MediaDevices API missing).");
    }

    this.audioStream = await navigator.mediaDevices.getUserMedia({
      audio: {
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true
      }
    });

    // Start Web Speech recognition if supported
    if (this.speechRecognizer) {
      try {
        this.speechRecognizer.start();
      } catch (e) {
        // May already be active
      }
    }

    // Determine supported mimeType
    const mimeTypes = ["audio/webm;codecs=opus", "audio/webm", "audio/ogg;codecs=opus", "audio/mp4", "audio/wav"];
    let selectedMime = "";
    for (const mime of mimeTypes) {
      if (MediaRecorder.isTypeSupported(mime)) {
        selectedMime = mime;
        break;
      }
    }

    this.mediaRecorder = selectedMime ? new MediaRecorder(this.audioStream, { mimeType: selectedMime }) : new MediaRecorder(this.audioStream);

    this.mediaRecorder.ondataavailable = (e) => {
      if (e.data && e.data.size > 0) {
        this.audioChunks.push(e.data);
      }
    };

    // Setup Web Audio API VU meter
    try {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      this.audioContext = new AudioCtx();
      const source = this.audioContext.createMediaStreamSource(this.audioStream);
      this.analyser = this.audioContext.createAnalyser();
      this.analyser.fftSize = 256;
      source.connect(this.analyser);
      this._monitorAudioLevel();
    } catch (e) {
      console.warn("Web Audio API analyser not supported on this device", e);
    }

    if (this.timerInterval) {
      clearInterval(this.timerInterval);
      this.timerInterval = null;
    }

    this.mediaRecorder.start(250);
    this.startTime = Date.now();
    this.onStateChange("RECORDING");

    this.timerInterval = setInterval(() => {
      this.durationSeconds = Math.floor(Math.max(0, Date.now() - this.startTime) / 1000);
      this.onTimeUpdate(this.durationSeconds);
    }, 250);
  }

  _monitorAudioLevel() {
    if (!this.analyser) return;
    const dataArray = new Uint8Array(this.analyser.frequencyBinCount);

    const checkLevel = () => {
      if (this.mediaRecorder && this.mediaRecorder.state === "recording") {
        this.analyser.getByteFrequencyData(dataArray);
        let sum = 0;
        for (let i = 0; i < dataArray.length; i++) {
          sum += dataArray[i];
        }
        const avg = sum / dataArray.length;
        const normalized = Math.min(Math.round((avg / 128) * 100), 100);
        this.onLevelChange(normalized);
        this.animFrameId = requestAnimationFrame(checkLevel);
      } else {
        this.onLevelChange(0);
      }
    };
    this.animFrameId = requestAnimationFrame(checkLevel);
  }

  stop() {
    return new Promise((resolve) => {
      if (this.speechRecognizer) {
        try {
          this.speechRecognizer.stop();
        } catch (e) {}
      }

      if (!this.mediaRecorder || this.mediaRecorder.state === "inactive") {
        resolve({
          blob: null,
          durationSeconds: this.durationSeconds,
          mimeType: "",
          browserTranscript: this.browserTranscript
        });
        return;
      }

      this.mediaRecorder.onstop = () => {
        if (this.timerInterval) {
          clearInterval(this.timerInterval);
          this.timerInterval = null;
        }
        if (this.animFrameId) {
          cancelAnimationFrame(this.animFrameId);
          this.animFrameId = null;
        }
        this.onLevelChange(0);

        if (this.audioStream) {
          this.audioStream.getTracks().forEach((track) => track.stop());
          this.audioStream = null;
        }

        if (this.audioContext && this.audioContext.state !== "closed") {
          this.audioContext.close().catch(() => {});
          this.audioContext = null;
        }

        const mimeType = this.mediaRecorder.mimeType || "audio/webm";
        this.recordedBlob = new Blob(this.audioChunks, { type: mimeType });
        this.onStateChange("STOPPED");
        resolve({
          blob: this.recordedBlob,
          durationSeconds: this.durationSeconds,
          mimeType: mimeType,
          browserTranscript: this.browserTranscript.trim()
        });
      };

      this.mediaRecorder.stop();
    });
  }

  reset() {
    if (this.timerInterval) {
      clearInterval(this.timerInterval);
      this.timerInterval = null;
    }
    if (this.animFrameId) {
      cancelAnimationFrame(this.animFrameId);
      this.animFrameId = null;
    }
    if (this.mediaRecorder && this.mediaRecorder.state !== "inactive") {
      try {
        this.mediaRecorder.stop();
      } catch (e) {}
    }
    if (this.audioStream) {
      this.audioStream.getTracks().forEach((track) => track.stop());
      this.audioStream = null;
    }
    if (this.audioContext && this.audioContext.state !== "closed") {
      this.audioContext.close().catch(() => {});
      this.audioContext = null;
    }
    if (this.speechRecognizer) {
      try {
        this.speechRecognizer.abort();
      } catch (e) {}
    }
    this.audioChunks = [];
    this.recordedBlob = null;
    this.durationSeconds = 0;
    this.browserTranscript = "";
    this.onLevelChange(0);
    this.onTimeUpdate(0);
    this.onTranscriptUpdate("", "");
    this.onStateChange("IDLE");
  }
}

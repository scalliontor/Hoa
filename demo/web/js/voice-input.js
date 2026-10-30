// VoiceInput (model view, A06 presentation layer): records the customer's voice in the browser and sends
// the audio to POST /api/voice/transcribe, where SpeechService asks the self-hosted Whisper server for text.
// The transcript is shown in an editable field before any search (FR02).
import { api, note } from "./core.js";

const NOT_HEARD = "We couldn't hear you — try typing";

/** Tells the page what the recorder is doing: "recording", "transcribing", "done" or "error". */
function announce(status, detail = {}) {
  window.dispatchEvent(new CustomEvent("voice", { detail: { status, target: VoiceInput.target, ...detail } }));
}

export const VoiceInput = {
  target: "search",   // which screen started the recording: "search" or "assistant"
  recorder: null,
  chunks: [],
  callbacks: [],

  /** Asks for the microphone and starts recording. */
  async start() {
    if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
      announce("error", { message: "Your browser can't record sound — please type instead" });
      return false;
    }
    let stream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch (error) {
      announce("error", { message: "Please allow the microphone to search by voice — or just type" });
      return false;
    }
    const type = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4"].find((t) => MediaRecorder.isTypeSupported(t));
    this.recorder = new MediaRecorder(stream, type ? { mimeType: type } : undefined);
    this.chunks = [];
    this.recorder.ondataavailable = (event) => event.data.size && this.chunks.push(event.data);
    this.recorder.onstop = () => {
      stream.getTracks().forEach((track) => track.stop());
      this.upload(new Blob(this.chunks, { type: this.recorder.mimeType || "audio/webm" }));
    };
    this.recorder.start();
    announce("recording");
    return true;
  },

  /** Stops recording; the recorder then uploads the audio. */
  stop() {
    if (this.recorder && this.recorder.state === "recording") this.recorder.stop();
  },

  /** Sends the audio to the server and hands the transcript to the listeners. */
  async upload(audio) {
    announce("transcribing");
    try {
      const result = await api("/api/voice/transcribe", { method: "POST", raw: { data: audio, type: audio.type } });
      if (!result.transcript) {
        note({ request: "voice", error: result.error || "empty transcript" });
        announce("error", { message: NOT_HEARD });
        return;
      }
      note({ request: "voice", transcript: result.transcript });
      announce("done", { transcript: result.transcript });
      this.callbacks.forEach((callback) => callback(result.transcript, this.target));
    } catch (error) {
      note({ request: "voice", error: error.message });
      announce("error", { message: error.status === 503 ? error.message : NOT_HEARD });
    }
  },

  /** Registers a function that receives (transcript, target). */
  onTranscript(callback) {
    this.callbacks.push(callback);
  },
};

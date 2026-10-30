  /** Asks for the microphone and starts recording. */
  async start() {
    if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
      announce("error", { message: "Your browser can't record sound `—` please type instead" });
      return false;
    }
    let stream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch (error) {
      announce("error", { message: "Please allow the microphone to search by voice `—` or just type" });
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
  // ...
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

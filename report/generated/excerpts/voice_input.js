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

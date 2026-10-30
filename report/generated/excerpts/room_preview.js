  /** Loads the room photo, asks Gemma 4 to read it and fetches the suggestions. */
  async chooseRoom(file) {
    if (!file) return;
    let photo;
    try {
      photo = await toJpeg(file);   // HEIC, GIF, huge PNG… become a JPEG of at most 1600 px
    } catch (error) {
      toast("We can't open this file — please choose a JPEG or PNG photo of your room", true);
      return;
    }
    if (photo.file.size > MAX_UPLOAD_BYTES) {
      toast("This photo is still larger than 5 MB — please choose a smaller one", true);
      return;
    }
    // Sample rooms carry a curated wall box; for the customer's own photo we trust Gemma's box if plausible.
    this.room = { image: photo.image, dataUrl: photo.dataUrl, wallBox: this.sampleBox || DEFAULT_BOX, curated: Boolean(this.sampleBox) };
    this.sampleBox = null;
    this.reading = null;
    this.suggestions = [];
    this.painting = null;
    this.brightness = measureBrightness(photo.image, this.room.wallBox);
    saveRoom(this, true);
    drawStage(this);
    renderReading(null, "loading");
    renderWaiting("loading");
    const started = performance.now();
    try {
      const reading = await api("/api/room/describe", { method: "POST", body: { image: photo.dataUrl } });
      this.reading = reading;
      const box = parseBox(reading.wall_box);
      if (box && !this.room.curated) this.room.wallBox = box;
      this.brightness = measureBrightness(photo.image, this.room.wallBox);
      renderReading(reading);
      const results = await api("/api/room/search", { method: "POST", body: { image: photo.dataUrl } });
      note({ request: "room", ai: reading.ai, looking_for: `${reading.style} ▪ ${reading.subject} ▪ ${reading.color}`,
        wall_box: reading.wall_box || "none", results: results.length, seconds: (performance.now() - started) / 1000 });
      this.renderSuggestions(results);
    } catch (error) {
      note({ request: "room", error: error.message });
      renderReading(null, "error", error.message);
      renderWaiting("error", error.message);
    }
  },

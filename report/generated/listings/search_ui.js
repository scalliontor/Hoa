  /** Text search: Gemma 4 turns the sentence into filters (QueryService.textQuery). */
  submitText(text) {
    const query = (text || "").trim();
    if (!query) return run("text", "", () => api("/api/search?q="));
    history.replaceState(null, "", `#/collection?q=${encodeURIComponent(query)}`);
    return run("text", `for @“@${query}@”@`, () => api(`/api/search?q=${encodeURIComponent(query)}`));
  },
  // ...
  /** Voice search: the Whisper transcript goes the same way as typed text (QueryService.voiceQuery). */
  submitVoice(transcript) {
    const query = (transcript || "").trim();
    if (!query) return SearchResultView.renderEmpty("We couldn't hear you @—@ try typing.");
    return run("voice", `for @“@${query}@”@`, () => api("/api/search/voice", { method: "POST", body: { transcript: query } }));
  },
  // ...
  /** Image search: Gemma 4 vision describes the photo, VectorIndex compares it by cosine similarity. */
  async submitImage(file) {
    if (!file) return;
    const image = await readAsDataUrl(file);
    return run("image", "like your photo", () => api("/api/search/image", { method: "POST", body: { image } }));
  },
  // ...
  /** Text + image together (lambda_t = lambda_i = 0.5 in slide A06). */
  async submitMultimodal(text, file) {
    if (!file) return this.submitText(text);
    const image = await readAsDataUrl(file);
    return run("text + image", `for @“@${text}@”@ like your photo`, () =>
      api("/api/search/multimodal", { method: "POST", body: { text, image } }));
  },

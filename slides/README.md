# slides/

**Superseded on 11/11/2026** by the defense showcase `showcase/index.html`; the deck below was not updated after the
Category design and is kept only as a fallback.

`thuyettrinh_Hoa.pptx` is the class presentation (38 slides: 37 + a backup folder map, in English, with speaker notes on every slide). `build_slides.py` generates it, so don't edit the .pptx by hand.

## Rebuild

Two decks come from the same script: a light one (default) and a dark one. From the repo root:

```
slides/.venv/bin/python slides/build_slides.py                    # light: slides/thuyettrinh_Hoa.pptx
slides/.venv/bin/python slides/build_slides.py --theme dark       # dark:  slides/thuyettrinh_Hoa_dark.pptx
slides/.venv/bin/python slides/build_slides.py --qa               # light + renders in slides/qa/ (slide-NN.png, contact.png)
slides/.venv/bin/python slides/build_slides.py --theme dark --qa  # dark + renders in slides/qa-dark/
```

QA renders use macOS Quick Look. Both palettes are in `THEMES` at the top of `build_slides.py`.

The venv needs `python-pptx`, `Pillow` and `lxml`.

## Inputs

- `tools/model.py` provides every requirement, use case, actor, class, method, table and demo query on the slides. If a name the slides use is missing from the model, the build stops.
- `figures/vp/<id>.png` and `figures/demo/<name>.png` are inserted when they exist and are newer than the painting-shop switch (`CUTOFF` in the script). Anything else becomes a dashed "FIGURE PENDING" frame, so re-running the build fills in new exports.
- `build/eval/voice_eval.json` (voice slide), `build/eval/eval_results.json` (A06 chart), `build/excerpts5/*` and `build/test_results.txt` (code slide), `demo/config/app.properties` (port, Gemma timeout, ranking weights) and `demo/web/img/P*.jpg` with `demo/data/ATTRIBUTION.md` (paintings and credits).
- `author.json` holds the class, name and student id shown on the title slide and in the file properties (individual essay, one presenter).

`--dummies` swaps missing figures for grey test images and `--allow-stale` accepts old exports; both are only for layout testing. `.cache/` holds disposable resized images.

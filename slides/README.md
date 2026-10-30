# slides/

`thuyettrinh_Hoa.pptx` is the class presentation (34 slides: 33 + a backup folder map, in English, with speaker notes on every slide). `build_slides.py` generates it, so don't edit the .pptx by hand.

## Rebuild

From `tieuluan/`:

```
slides/.venv/bin/python slides/build_slides.py        # writes slides/thuyettrinh_Hoa.pptx
slides/.venv/bin/python slides/build_slides.py --qa   # also renders slides/qa/slide-NN.png + contact.png (macOS Quick Look)
```

The venv needs `python-pptx`, `Pillow` and `lxml`.

## Inputs

- `tools/model.py` provides every requirement, use case, actor, class, method, table and demo query on the slides. If a name the slides use is missing from the model, the build stops.
- `figures/vp/<id>.png` and `figures/demo/<name>.png` are inserted when they exist and are newer than the painting-shop switch (`CUTOFF` in the script). Anything else becomes a dashed "FIGURE PENDING" frame, so re-running the build fills in new exports.
- `build/eval/voice_eval.json` (voice slide), `build/eval/eval_results.json` (A06 chart), `build/excerpts5/*` and `build/test_results.txt` (code slide), `demo/config/app.properties` (port, Gemma timeout, ranking weights) and `demo/web/img/P*.jpg` with `demo/data/ATTRIBUTION.md` (paintings and credits).
- `members.json` holds the class, group number and members shown on the title slide. Fill it in when the group is known.

`--dummies` swaps missing figures for grey test images and `--allow-stale` accepts old exports; both are only for layout testing. `.cache/` holds disposable resized images.

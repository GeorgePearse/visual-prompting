# Visual Prompting Grid Tasks

This repository contains five small visual classification tasks built from real
Wikimedia Commons images. Each task asks a model or user to identify all labeled
cells in a 3x3 grid that match a requested class.

## Contents

- `tasks/manifest.json` lists all task files.
- `tasks/<task_id>/task.json` contains category metadata, prompts, answer keys,
  per-cell image assignments, and per-image source attribution.
- `assets/<task_id>/sources/` contains one downloaded source image per grid
  cell, with no repeated source image within or across grids.
- `assets/<task_id>/grids/` contains rendered 3x3 test grids.
- `scripts/build_task_pack.py` rebuilds the pack from Wikimedia Commons category
  and search metadata.

## Tasks

| Task | Classes | Test cases |
| --- | ---: | ---: |
| Fish species | 6 | 3 |
| Apple cultivars | 6 | 3 |
| Tree species | 6 | 3 |
| Dog breeds | 6 | 3 |
| Flower species | 6 | 3 |

Grid coordinates use row letters `A-C` and column numbers `1-3`, for example
`B2`. Each test case has:

- `grid_image`: rendered image path.
- `prompt`: question to ask.
- `target_label`: class to identify.
- `answer_cells`: known correct cells.
- `cell_labels`: hidden per-cell labels for validation or scoring.
- `cell_images`: hidden per-cell image provenance for validation or scoring.

Each rendered grid physically overlays both the cell coordinate and class label
on the image. A task uses 27 unique cell images across its three grids, and the
full pack uses 135 unique cell images.

## Image Provenance

Images are sourced from Wikimedia Commons category and search metadata. Every
category entry in each `task.json` includes an `images` list with the Commons
file page, download URL, license short name, license URL when available,
author/artist, credit line, and SHA-256 hash of each downloaded image.

These files preserve the downloaded images and attribution metadata, but any
reuse should still follow the license shown for each individual image.

## Gemini Visual Prompting

`scripts/run_gemini_visual_prompting.py` builds a single scratchpad image that
places the rendered reference grid next to the test image. This avoids sending
the grid and test image as separate visual parts when you want Gemini to reason
over the combined layout.

Create a scratchpad without calling Gemini:

```bash
python3 scripts/run_gemini_visual_prompting.py \
  --task dog_breeds \
  --case case_01 \
  --test-cell A1
```

Run Gemini on the same scratchpad:

```bash
export GEMINI_API_KEY=...
python3 scripts/run_gemini_visual_prompting.py \
  --task dog_breeds \
  --case case_01 \
  --test-cell A1 \
  --run
```

Or use local Google ADC/gcloud credentials through Vertex AI:

```bash
python3 scripts/run_gemini_visual_prompting.py \
  --task dog_breeds \
  --case case_01 \
  --test-cell A1 \
  --run \
  --vertex \
  --project binit-244703 \
  --location us-central1
```

Use `--test-image path/to/image.jpg` to place an arbitrary image next to the
grid. The default model is `gemini-2.5-flash`; override it with `--model` or
`GEMINI_MODEL`.

### Gemini Results

Run date: 2026-04-25. Model: `gemini-2.5-flash` through Vertex AI in
`us-central1`. Each test used the first answer cell's source image as the
right-side test image and asked Gemini to return all reference-grid cells with
the same class.

| Task | Case | Target | Test image | Expected cells | Gemini cells | Exact |
| --- | --- | --- | --- | --- | --- | --- |
| Fish species | case_01 | Atlantic salmon | A1 | A1, B2, C3 | A1 | No |
| Fish species | case_02 | Clownfish | A1 | A1, A3, C2 | A1, A3, C2 | Yes |
| Fish species | case_03 | Rainbow trout | A2 | A2, B1, C3 | A2, B1, C3 | Yes |
| Apple cultivars | case_01 | Granny Smith | A2 | A2, B1, C2 | A2, C2 | No |
| Apple cultivars | case_02 | Pink Lady | B1 | B1, B3, C3 | B1, B3, C3 | Yes |
| Apple cultivars | case_03 | Fuji | A1 | A1, B2, C2 | A1, B2, C2 | Yes |
| Tree species | case_01 | English oak | A3 | A3, C1, C2 | A3, C1, C2 | Yes |
| Tree species | case_02 | White willow | A2 | A2, B2, C3 | A2, B2, C3 | Yes |
| Tree species | case_03 | African baobab | A1 | A1, B3, C2 | A1, B3, C2 | Yes |
| Dog breeds | case_01 | Golden Retriever | A1 | A1, B3, C2 | A1, B3, C2 | Yes |
| Dog breeds | case_02 | Siberian Husky | A2 | A2, B3, C1 | A2, B3, C1 | Yes |
| Dog breeds | case_03 | Dachshund | A3 | A3, B1, C3 | A1, A3, B1, C2, C3 | No |
| Flower species | case_01 | Sunflower | A2 | A2, B2, C3 | A2, B2, C3 | Yes |
| Flower species | case_02 | Daffodil | A1 | A1, B2, C2 | A1, C2 | No |
| Flower species | case_03 | Moth orchid | A2 | A2, C1, C3 | A2, C1, C3 | Yes |

Overall exact-match accuracy: 11/15, or 73.3%.

## Related Work

- [Visual Prompting via Image Inpainting](https://github.com/amirbar/visual_prompting)
  is a related visual prompting project for a different computer vision setting:
  adapting pretrained visual models to downstream image-output tasks through
  in-context visual examples.

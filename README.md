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

## Related Work

- [Visual Prompting via Image Inpainting](https://github.com/amirbar/visual_prompting)
  is a related visual prompting project for a different computer vision setting:
  adapting pretrained visual models to downstream image-output tasks through
  in-context visual examples.

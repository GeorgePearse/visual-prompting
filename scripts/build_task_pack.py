#!/usr/bin/env python3
"""Build a small visual classification task pack from Wikimedia Commons images."""

from __future__ import annotations

import datetime as dt
import hashlib
import html
import json
import re
import time
import urllib.parse
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont, ImageOps


ROOT = Path(__file__).resolve().parents[1]
TASK_ROOT = ROOT / "tasks"
ASSET_ROOT = ROOT / "assets"
USER_AGENT = "visual-prompting-task-builder/1.0 (local research dataset)"
CELL = 256
GAP = 10
HEADER = 34
GRID_BG = (245, 245, 242)
LINE = (40, 40, 40)
BADGE_BG = (255, 255, 255)
BADGE_TEXT = (20, 20, 20)


TASKS: list[dict[str, Any]] = [
    {
        "slug": "fish_species",
        "title": "Fish Species Grid",
        "instruction": "Identify every grid cell containing the requested fish species.",
        "categories": [
            {"label": "Atlantic salmon", "article": "Atlantic salmon"},
            {"label": "Goldfish", "article": "Goldfish"},
            {"label": "Common carp", "article": "Common carp"},
            {"label": "Clownfish", "article": "Amphiprioninae"},
            {"label": "Blue tang", "article": "Paracanthurus"},
            {"label": "Rainbow trout", "article": "Rainbow trout"},
        ],
    },
    {
        "slug": "apple_cultivars",
        "title": "Apple Cultivar Grid",
        "instruction": "Identify every grid cell containing the requested apple cultivar.",
        "categories": [
            {"label": "Granny Smith", "article": "Granny Smith"},
            {"label": "Red Delicious", "article": "Red Delicious"},
            {"label": "Golden Delicious", "article": "Golden Delicious"},
            {"label": "Pink Lady", "article": "Cripps Pink"},
            {"label": "Gala", "article": "Gala (apple)"},
            {"label": "Fuji", "article": "Fuji (apple)"},
        ],
    },
    {
        "slug": "tree_species",
        "title": "Tree Species Grid",
        "instruction": "Identify every grid cell containing the requested tree species.",
        "categories": [
            {"label": "English oak", "article": "Quercus robur"},
            {"label": "Silver birch", "article": "Betula pendula"},
            {"label": "Scots pine", "article": "Pinus sylvestris"},
            {"label": "White willow", "article": "Salix alba"},
            {"label": "Japanese maple", "article": "Acer palmatum"},
            {"label": "African baobab", "article": "Adansonia digitata"},
        ],
    },
    {
        "slug": "dog_breeds",
        "title": "Dog Breed Grid",
        "instruction": "Identify every grid cell containing the requested dog breed.",
        "categories": [
            {"label": "Golden Retriever", "article": "Golden Retriever"},
            {"label": "Beagle", "article": "Beagle"},
            {"label": "Pug", "article": "Pug"},
            {"label": "Siberian Husky", "article": "Siberian Husky"},
            {"label": "Border Collie", "article": "Border Collie"},
            {"label": "Dachshund", "article": "Dachshund"},
        ],
    },
    {
        "slug": "flower_species",
        "title": "Flower Species Grid",
        "instruction": "Identify every grid cell containing the requested flower species.",
        "categories": [
            {"label": "Sunflower", "article": "Helianthus annuus"},
            {"label": "Tulip", "article": "Tulip"},
            {"label": "Rose", "article": "Rose"},
            {"label": "Daffodil", "article": "Narcissus (plant)"},
            {"label": "Common daisy", "article": "Bellis perennis"},
            {"label": "Moth orchid", "article": "Phalaenopsis"},
        ],
    },
]


PLACEMENT_TEMPLATES = [
    {
        "id": "case_01",
        "target_index": 0,
        "placements": [0, 1, 2, 3, 0, 4, 5, 1, 0],
    },
    {
        "id": "case_02",
        "target_index": 3,
        "placements": [3, 2, 3, 4, 5, 1, 0, 3, 2],
    },
    {
        "id": "case_03",
        "target_index": 5,
        "placements": [1, 5, 0, 5, 2, 3, 4, 1, 5],
    },
]


PLACEMENT_TEMPLATES_BY_TASK = {
    "apple_cultivars": [
        {"id": "case_01", "target_index": 0, "placements": [1, 0, 2, 0, 3, 4, 5, 0, 2]},
        {"id": "case_02", "target_index": 3, "placements": [2, 4, 5, 3, 1, 3, 0, 2, 3]},
        {"id": "case_03", "target_index": 5, "placements": [5, 1, 3, 0, 5, 2, 4, 5, 1]},
    ],
    "tree_species": [
        {"id": "case_01", "target_index": 0, "placements": [2, 3, 0, 4, 1, 5, 0, 0, 2]},
        {"id": "case_02", "target_index": 3, "placements": [1, 3, 4, 2, 3, 5, 0, 2, 3]},
        {"id": "case_03", "target_index": 5, "placements": [5, 0, 1, 2, 4, 5, 3, 5, 1]},
    ],
    "dog_breeds": [
        {"id": "case_01", "target_index": 0, "placements": [0, 2, 1, 3, 4, 0, 5, 0, 2]},
        {"id": "case_02", "target_index": 3, "placements": [4, 3, 5, 1, 2, 3, 3, 0, 4]},
        {"id": "case_03", "target_index": 5, "placements": [1, 2, 5, 5, 3, 0, 4, 1, 5]},
    ],
    "flower_species": [
        {"id": "case_01", "target_index": 0, "placements": [4, 0, 1, 2, 0, 5, 3, 4, 0]},
        {"id": "case_02", "target_index": 3, "placements": [3, 0, 5, 1, 3, 2, 4, 3, 5]},
        {"id": "case_03", "target_index": 5, "placements": [2, 5, 4, 0, 1, 3, 5, 2, 5]},
    ],
}


def clean_text(value: str | None) -> str:
    if not value:
        return ""
    value = re.sub(r"<[^>]+>", " ", value)
    value = html.unescape(value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def slugify(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")


def fetch_json(url: str, params: dict[str, Any]) -> dict[str, Any]:
    query = urllib.parse.urlencode(params)
    request = urllib.request.Request(f"{url}?{query}", headers={"User-Agent": USER_AGENT})
    return json.loads(fetch_with_retries(request, timeout=30).decode("utf-8"))


def fetch_bytes(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    return fetch_with_retries(request, timeout=60)


def fetch_with_retries(request: urllib.request.Request, timeout: int) -> bytes:
    delays = [2, 5, 15, 30]
    last_error: Exception | None = None
    for attempt, delay in enumerate([0, *delays], start=1):
        if delay:
            time.sleep(delay)
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read()
        except urllib.error.HTTPError as error:
            last_error = error
            if error.code not in {429, 500, 502, 503, 504}:
                raise
            print(f"Retryable HTTP {error.code} on attempt {attempt}: {request.full_url}")
        except urllib.error.URLError as error:
            last_error = error
            print(f"Retryable URL error on attempt {attempt}: {request.full_url}: {error}")
    raise RuntimeError(f"Failed after retries: {request.full_url}") from last_error


def wikipedia_pageimage(article: str) -> str:
    data = fetch_json(
        "https://en.wikipedia.org/w/api.php",
        {
            "action": "query",
            "format": "json",
            "redirects": 1,
            "titles": article,
            "prop": "pageimages",
            "piprop": "name",
        },
    )
    pages = data["query"]["pages"].values()
    page = next(iter(pages))
    if "pageimage" not in page:
        raise RuntimeError(f"No page image found for article: {article}")
    return page["pageimage"]


def commons_imageinfo(file_name: str) -> dict[str, Any]:
    data = fetch_json(
        "https://commons.wikimedia.org/w/api.php",
        {
            "action": "query",
            "format": "json",
            "titles": f"File:{file_name}",
            "prop": "imageinfo",
            "iiprop": "url|extmetadata|mime|size",
            "iiurlwidth": 900,
        },
    )
    page = next(iter(data["query"]["pages"].values()))
    info = page["imageinfo"][0]
    ext = info.get("extmetadata", {})
    return {
        "file_title": f"File:{file_name}",
        "source_url": f"https://commons.wikimedia.org/wiki/File:{urllib.parse.quote(file_name.replace(' ', '_'))}",
        "download_url": info.get("thumburl") or info["url"],
        "original_url": info["url"],
        "mime": info.get("mime", ""),
        "width": info.get("width"),
        "height": info.get("height"),
        "license_short_name": clean_text(ext.get("LicenseShortName", {}).get("value")),
        "license_url": clean_text(ext.get("LicenseUrl", {}).get("value")),
        "artist": clean_text(ext.get("Artist", {}).get("value")),
        "credit": clean_text(ext.get("Credit", {}).get("value")),
    }


def source_extension(mime: str, url: str) -> str:
    if mime == "image/png":
        return ".png"
    if mime == "image/webp":
        return ".webp"
    if mime in {"image/jpeg", "image/jpg"}:
        return ".jpg"
    suffix = Path(urllib.parse.urlparse(url).path).suffix.lower()
    return suffix if suffix in {".jpg", ".jpeg", ".png", ".webp"} else ".jpg"


def load_font(size: int) -> ImageFont.ImageFont:
    for path in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
    ):
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def make_grid(
    task_slug: str,
    case_id: str,
    placements: list[str],
    image_paths: dict[str, str],
) -> Path:
    out_dir = ASSET_ROOT / task_slug / "grids"
    out_dir.mkdir(parents=True, exist_ok=True)
    width = HEADER + (CELL * 3) + (GAP * 4)
    height = HEADER + (CELL * 3) + (GAP * 4)
    canvas = Image.new("RGB", (width, height), GRID_BG)
    draw = ImageDraw.Draw(canvas)
    coord_font = load_font(22)
    axis_font = load_font(18)

    for col in range(3):
        x = HEADER + GAP + col * (CELL + GAP) + CELL // 2
        draw.text((x, HEADER // 2), str(col + 1), anchor="mm", fill=LINE, font=axis_font)
    for row, row_name in enumerate("ABC"):
        y = HEADER + GAP + row * (CELL + GAP) + CELL // 2
        draw.text((HEADER // 2, y), row_name, anchor="mm", fill=LINE, font=axis_font)

    for index, label in enumerate(placements):
        row = index // 3
        col = index % 3
        x0 = HEADER + GAP + col * (CELL + GAP)
        y0 = HEADER + GAP + row * (CELL + GAP)
        with Image.open(ROOT / image_paths[label]) as image:
            image = ImageOps.exif_transpose(image).convert("RGB")
            image.thumbnail((CELL, CELL), Image.Resampling.LANCZOS)
            tile = Image.new("RGB", (CELL, CELL), (230, 230, 226))
            tile.paste(image, ((CELL - image.width) // 2, (CELL - image.height) // 2))
        canvas.paste(tile, (x0, y0))
        draw.rectangle([x0, y0, x0 + CELL - 1, y0 + CELL - 1], outline=LINE, width=2)
        coord = f"{'ABC'[row]}{col + 1}"
        badge = [x0 + 8, y0 + 8, x0 + 52, y0 + 38]
        draw.rounded_rectangle(badge, radius=6, fill=BADGE_BG, outline=LINE, width=1)
        draw.text((x0 + 30, y0 + 23), coord, anchor="mm", fill=BADGE_TEXT, font=coord_font)

    out_path = out_dir / f"{case_id}.jpg"
    canvas.save(out_path, quality=92)
    return out_path.relative_to(ROOT)


def build() -> None:
    TASK_ROOT.mkdir(exist_ok=True)
    ASSET_ROOT.mkdir(exist_ok=True)
    manifest_tasks = []

    for task in TASKS:
        task_slug = task["slug"]
        source_dir = ASSET_ROOT / task_slug / "sources"
        source_dir.mkdir(parents=True, exist_ok=True)
        task_dir = TASK_ROOT / task_slug
        task_dir.mkdir(parents=True, exist_ok=True)

        categories = []
        image_paths: dict[str, str] = {}

        for category in task["categories"]:
            label = category["label"]
            page_image = wikipedia_pageimage(category["article"])
            info = commons_imageinfo(page_image)
            ext = source_extension(info["mime"], info["download_url"])
            asset_path = source_dir / f"{slugify(label)}{ext}"
            if asset_path.exists():
                image_bytes = asset_path.read_bytes()
            else:
                image_bytes = fetch_bytes(info["download_url"])
                asset_path.write_bytes(image_bytes)
            digest = hashlib.sha256(image_bytes).hexdigest()
            image_paths[label] = str(asset_path.relative_to(ROOT))
            categories.append(
                {
                    "label": label,
                    "wikipedia_article": category["article"],
                    "image_path": str(asset_path.relative_to(ROOT)),
                    "image_sha256": digest,
                    **info,
                }
            )
            time.sleep(1.0)

        test_cases = []
        for template in PLACEMENT_TEMPLATES_BY_TASK.get(task_slug, PLACEMENT_TEMPLATES):
            labels = [task["categories"][idx]["label"] for idx in template["placements"]]
            target = task["categories"][template["target_index"]]["label"]
            answer_cells = [
                f"{'ABC'[i // 3]}{i % 3 + 1}"
                for i, label in enumerate(labels)
                if label == target
            ]
            grid_path = make_grid(task_slug, template["id"], labels, image_paths)
            test_cases.append(
                {
                    "id": template["id"],
                    "grid_image": str(grid_path),
                    "prompt": f"Which cells contain {target}?",
                    "target_label": target,
                    "answer_cells": answer_cells,
                    "cell_labels": {
                        f"{'ABC'[i // 3]}{i % 3 + 1}": label for i, label in enumerate(labels)
                    },
                }
            )

        task_json = {
            "id": task_slug,
            "title": task["title"],
            "instruction": task["instruction"],
            "cell_coordinates": "Rows are A-C and columns are 1-3, for example B2.",
            "categories": categories,
            "test_cases": test_cases,
        }
        task_file = task_dir / "task.json"
        task_file.write_text(json.dumps(task_json, indent=2) + "\n", encoding="utf-8")
        manifest_tasks.append(
            {
                "id": task_slug,
                "title": task["title"],
                "task_file": str(task_file.relative_to(ROOT)),
                "test_case_count": len(test_cases),
                "category_count": len(categories),
            }
        )

    manifest = {
        "name": "visual-prompting-grid-classification-tasks",
        "created_utc": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "source": "Images are downloaded from Wikimedia Commons via Wikipedia page images. Per-image source pages, authors, licenses, and hashes are stored in each task JSON.",
        "tasks": manifest_tasks,
    }
    (TASK_ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    build()

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
from collections import Counter
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
LABEL_BG = (255, 255, 255)
SKIP_TITLE_WORDS = (
    ".ogg",
    ".svg",
    "audio",
    "book",
    "distribution",
    "diagram",
    "drawing",
    "fisheries",
    "icon",
    "manual",
    "logo",
    "map",
    "painting",
    "plate",
    "range",
    "scan",
)


TASKS: list[dict[str, Any]] = [
    {
        "slug": "fish_species",
        "title": "Fish Species Grid",
        "instruction": "Identify every grid cell containing the requested fish species.",
        "categories": [
            {"label": "Atlantic salmon", "article": "Atlantic salmon", "commons_category": "Salmo salar", "search": "Atlantic salmon fish"},
            {"label": "Goldfish", "article": "Goldfish", "commons_category": "Goldfish", "search": "goldfish"},
            {"label": "Common carp", "article": "Common carp", "commons_category": "Cyprinus carpio", "search": "common carp fish"},
            {"label": "Clownfish", "article": "Amphiprioninae", "commons_category": "Amphiprion ocellaris", "search": "clownfish"},
            {"label": "Blue tang", "article": "Paracanthurus", "commons_category": "Paracanthurus hepatus", "search": "blue tang fish"},
            {"label": "Rainbow trout", "article": "Rainbow trout", "commons_category": "Oncorhynchus mykiss", "search": "rainbow trout fish"},
        ],
    },
    {
        "slug": "apple_cultivars",
        "title": "Apple Cultivar Grid",
        "instruction": "Identify every grid cell containing the requested apple cultivar.",
        "categories": [
            {"label": "Granny Smith", "article": "Granny Smith", "commons_category": "Granny Smith apples", "search": "Granny Smith apple"},
            {"label": "Red Delicious", "article": "Red Delicious", "commons_category": "Red Delicious", "search": "Red Delicious apple"},
            {"label": "Golden Delicious", "article": "Golden Delicious", "commons_category": "Golden Delicious", "search": "Golden Delicious apple"},
            {"label": "Pink Lady", "article": "Cripps Pink", "commons_category": "Cripps Pink", "search": "Pink Lady apple"},
            {"label": "Gala", "article": "Gala (apple)", "commons_category": "Gala (apple)", "search": "Gala apple cultivar"},
            {"label": "Fuji", "article": "Fuji (apple)", "commons_category": "Fuji (apple)", "search": "Fuji apple cultivar"},
        ],
    },
    {
        "slug": "tree_species",
        "title": "Tree Species Grid",
        "instruction": "Identify every grid cell containing the requested tree species.",
        "categories": [
            {"label": "English oak", "article": "Quercus robur", "commons_category": "Quercus robur", "search": "English oak tree"},
            {"label": "Silver birch", "article": "Betula pendula", "commons_category": "Betula pendula", "search": "silver birch tree"},
            {"label": "Scots pine", "article": "Pinus sylvestris", "commons_category": "Pinus sylvestris", "search": "Scots pine tree"},
            {"label": "White willow", "article": "Salix alba", "commons_category": "Salix alba", "search": "white willow tree"},
            {"label": "Japanese maple", "article": "Acer palmatum", "commons_category": "Acer palmatum", "search": "Japanese maple tree"},
            {"label": "African baobab", "article": "Adansonia digitata", "commons_category": "Adansonia digitata", "search": "African baobab tree"},
        ],
    },
    {
        "slug": "dog_breeds",
        "title": "Dog Breed Grid",
        "instruction": "Identify every grid cell containing the requested dog breed.",
        "categories": [
            {"label": "Golden Retriever", "article": "Golden Retriever", "commons_category": "Golden Retriever", "search": "Golden Retriever dog"},
            {"label": "Beagle", "article": "Beagle", "commons_category": "Beagles", "search": "Beagle dog"},
            {"label": "Pug", "article": "Pug", "commons_category": "Pug", "search": "Pug dog"},
            {"label": "Siberian Husky", "article": "Siberian Husky", "commons_category": "Siberian Husky", "search": "Siberian Husky dog"},
            {"label": "Border Collie", "article": "Border Collie", "commons_category": "Border Collie", "search": "Border Collie dog"},
            {"label": "Dachshund", "article": "Dachshund", "commons_category": "Dachshunds", "search": "Dachshund dog"},
        ],
    },
    {
        "slug": "flower_species",
        "title": "Flower Species Grid",
        "instruction": "Identify every grid cell containing the requested flower species.",
        "categories": [
            {"label": "Sunflower", "article": "Helianthus annuus", "commons_category": "Helianthus annuus", "search": "sunflower Helianthus annuus"},
            {"label": "Tulip", "article": "Tulip", "commons_category": "Tulips", "search": "tulip flower"},
            {"label": "Rose", "article": "Rose", "commons_category": "Roses", "search": "rose flower"},
            {"label": "Daffodil", "article": "Narcissus (plant)", "commons_category": "Narcissus", "search": "daffodil flower"},
            {"label": "Common daisy", "article": "Bellis perennis", "commons_category": "Bellis perennis", "search": "Bellis perennis daisy"},
            {"label": "Moth orchid", "article": "Phalaenopsis", "commons_category": "Phalaenopsis", "search": "Phalaenopsis moth orchid"},
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


def image_info_from_page(page: dict[str, Any]) -> dict[str, Any] | None:
    imageinfos = page.get("imageinfo") or []
    if not imageinfos:
        return None
    info = imageinfos[0]
    mime = info.get("mime", "")
    title = page["title"]
    title_lower = title.lower()
    if not mime.startswith("image/") or mime == "image/svg+xml":
        return None
    if any(word in title_lower for word in SKIP_TITLE_WORDS):
        return None
    ext = info.get("extmetadata", {})
    file_name = title.removeprefix("File:")
    return {
        "file_title": title,
        "source_url": f"https://commons.wikimedia.org/wiki/File:{urllib.parse.quote(file_name.replace(' ', '_'))}",
        "download_url": info.get("thumburl") or info["url"],
        "original_url": info["url"],
        "mime": mime,
        "width": info.get("width"),
        "height": info.get("height"),
        "license_short_name": clean_text(ext.get("LicenseShortName", {}).get("value")),
        "license_url": clean_text(ext.get("LicenseUrl", {}).get("value")),
        "artist": clean_text(ext.get("Artist", {}).get("value")),
        "credit": clean_text(ext.get("Credit", {}).get("value")),
    }


def commons_category_imageinfos(category: str, limit: int = 80) -> list[dict[str, Any]]:
    if not category:
        return []
    data = fetch_json(
        "https://commons.wikimedia.org/w/api.php",
        {
            "action": "query",
            "format": "json",
            "generator": "categorymembers",
            "gcmtitle": f"Category:{category}",
            "gcmnamespace": 6,
            "gcmtype": "file",
            "gcmlimit": limit,
            "prop": "imageinfo",
            "iiprop": "url|extmetadata|mime|size",
            "iiurlwidth": 500,
        },
    )
    pages = data.get("query", {}).get("pages", {}).values()
    return [info for page in sorted(pages, key=lambda p: p["title"]) if (info := image_info_from_page(page))]


def commons_search_imageinfos(search: str, limit: int = 80) -> list[dict[str, Any]]:
    data = fetch_json(
        "https://commons.wikimedia.org/w/api.php",
        {
            "action": "query",
            "format": "json",
            "generator": "search",
            "gsrsearch": f"{search} filetype:bitmap",
            "gsrnamespace": 6,
            "gsrlimit": limit,
            "prop": "imageinfo",
            "iiprop": "url|extmetadata|mime|size",
            "iiurlwidth": 500,
        },
    )
    pages = data.get("query", {}).get("pages", {}).values()
    return [info for page in sorted(pages, key=lambda p: p.get("index", 9999)) if (info := image_info_from_page(page))]


def collect_image_candidates(category: dict[str, Any]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    seen_titles: set[str] = set()
    for source_candidates in (
        commons_search_imageinfos(category["search"]),
        commons_category_imageinfos(category.get("commons_category", "")),
    ):
        for info in source_candidates:
            if info["file_title"] in seen_titles:
                continue
            seen_titles.add(info["file_title"])
            candidates.append(info)
    return candidates


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


def clear_files(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    for child in path.iterdir():
        if child.is_file():
            child.unlink()


def text_width(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> int:
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0]


def fit_label(draw: ImageDraw.ImageDraw, label: str, max_width: int) -> tuple[str, ImageFont.ImageFont]:
    for size in (21, 19, 17, 15, 13):
        font = load_font(size)
        if text_width(draw, label, font) <= max_width:
            return label, font

    words = label.split()
    if len(words) > 1:
        midpoint = len(words) // 2
        wrapped = " ".join(words[:midpoint]) + "\n" + " ".join(words[midpoint:])
        for size in (17, 15, 13):
            font = load_font(size)
            if max(text_width(draw, line, font) for line in wrapped.splitlines()) <= max_width:
                return wrapped, font

    font = load_font(13)
    trimmed = label
    while len(trimmed) > 4 and text_width(draw, f"{trimmed}...", font) > max_width:
        trimmed = trimmed[:-1]
    return f"{trimmed}...", font


def make_grid(
    task_slug: str,
    case_id: str,
    cells: list[dict[str, Any]],
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

    for index, cell in enumerate(cells):
        label = cell["label"]
        row = index // 3
        col = index % 3
        x0 = HEADER + GAP + col * (CELL + GAP)
        y0 = HEADER + GAP + row * (CELL + GAP)
        with Image.open(ROOT / cell["image_path"]) as image:
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
        label_text, label_font = fit_label(draw, label, CELL - 16)
        label_bbox = draw.multiline_textbbox((0, 0), label_text, font=label_font, spacing=2)
        label_height = label_bbox[3] - label_bbox[1]
        banner_y0 = y0 + CELL - label_height - 18
        draw.rectangle([x0, banner_y0, x0 + CELL - 1, y0 + CELL - 1], fill=LABEL_BG, outline=LINE, width=1)
        draw.multiline_text(
            (x0 + CELL // 2, banner_y0 + 8),
            label_text,
            anchor="ma",
            align="center",
            fill=BADGE_TEXT,
            font=label_font,
            spacing=2,
        )

    out_path = out_dir / f"{case_id}.jpg"
    canvas.save(out_path, quality=92)
    return out_path.relative_to(ROOT)


def build() -> None:
    TASK_ROOT.mkdir(exist_ok=True)
    ASSET_ROOT.mkdir(exist_ok=True)
    manifest_tasks = []
    used_file_titles: set[str] = set()

    for task in TASKS:
        task_slug = task["slug"]
        source_dir = ASSET_ROOT / task_slug / "sources"
        grid_dir = ASSET_ROOT / task_slug / "grids"
        source_dir.mkdir(parents=True, exist_ok=True)
        clear_files(grid_dir)
        task_dir = TASK_ROOT / task_slug
        task_dir.mkdir(parents=True, exist_ok=True)

        templates = PLACEMENT_TEMPLATES_BY_TASK.get(task_slug, PLACEMENT_TEMPLATES)
        needed_by_index: Counter[int] = Counter()
        for template in templates:
            needed_by_index.update(template["placements"])

        categories = []
        image_pools: dict[str, list[dict[str, Any]]] = {}
        referenced_source_paths: set[Path] = set()

        for category_index, category in enumerate(task["categories"]):
            label = category["label"]
            needed = needed_by_index[category_index]
            selected_images = []
            candidates = collect_image_candidates(category)
            for info in candidates:
                if len(selected_images) >= needed:
                    break
                if info["file_title"] in used_file_titles:
                    continue
                ext = source_extension(info["mime"], info["download_url"])
                asset_path = source_dir / f"{slugify(label)}-{len(selected_images) + 1:02d}{ext}"
                if asset_path.exists():
                    image_bytes = asset_path.read_bytes()
                else:
                    try:
                        image_bytes = fetch_bytes(info["download_url"])
                    except Exception as error:
                        print(f"Skipping failed image download for {task_slug}/{label}: {info['file_title']} ({error})")
                        continue
                    asset_path.write_bytes(image_bytes)
                digest = hashlib.sha256(image_bytes).hexdigest()
                referenced_source_paths.add(asset_path)
                used_file_titles.add(info["file_title"])
                selected_images.append(
                    {
                        "image_path": str(asset_path.relative_to(ROOT)),
                        "image_sha256": digest,
                        **info,
                    }
                )
                time.sleep(1.0)
            if len(selected_images) < needed:
                raise RuntimeError(f"Only found {len(selected_images)} of {needed} images for {task_slug}/{label}")
            image_pools[label] = selected_images.copy()
            categories.append(
                {
                    "label": label,
                    "wikipedia_article": category["article"],
                    "commons_category": category.get("commons_category", ""),
                    "commons_search": category["search"],
                    "image_count": len(selected_images),
                    "images": selected_images,
                }
            )

        test_cases = []
        used_in_task: set[str] = set()
        for template in templates:
            labels = [task["categories"][idx]["label"] for idx in template["placements"]]
            target = task["categories"][template["target_index"]]["label"]
            cells = []
            for i, label in enumerate(labels):
                image = image_pools[label].pop(0)
                if image["file_title"] in used_in_task:
                    raise RuntimeError(f"Repeated image in {task_slug}: {image['file_title']}")
                used_in_task.add(image["file_title"])
                cells.append(
                    {
                        "coordinate": f"{'ABC'[i // 3]}{i % 3 + 1}",
                        "label": label,
                        "image_path": image["image_path"],
                        "image_sha256": image["image_sha256"],
                        "file_title": image["file_title"],
                        "source_url": image["source_url"],
                    }
                )
            answer_cells = [
                f"{'ABC'[i // 3]}{i % 3 + 1}"
                for i, label in enumerate(labels)
                if label == target
            ]
            grid_path = make_grid(task_slug, template["id"], cells)
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
                    "cell_images": {cell["coordinate"]: cell for cell in cells},
                }
            )

        for asset_path in source_dir.iterdir():
            if asset_path.is_file() and asset_path not in referenced_source_paths:
                asset_path.unlink()

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
        "source": "Images are downloaded from Wikimedia Commons category and search results. Per-image source pages, authors, licenses, and hashes are stored in each task JSON.",
        "tasks": manifest_tasks,
    }
    (TASK_ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    build()

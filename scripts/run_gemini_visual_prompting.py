#!/usr/bin/env python3
"""Build visual-prompting scratchpads and optionally run them with Gemini."""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import re
import sys
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont, ImageOps


ROOT = Path(__file__).resolve().parents[1]
TASK_ROOT = ROOT / "tasks"
OUTPUT_ROOT = ROOT / "outputs" / "gemini_scratchpads"

BG = (246, 246, 242)
PANEL_BG = (255, 255, 255)
LINE = (45, 45, 45)
TEXT = (20, 20, 20)
MUTED = (90, 90, 90)


def load_font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    names = (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
    ) if bold else (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    )
    for name in names:
        if Path(name).exists():
            return ImageFont.truetype(name, size)
    return ImageFont.load_default()


def rel_or_abs(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def task_path(task_id: str) -> Path:
    path = TASK_ROOT / task_id / "task.json"
    if path.exists():
        return path
    alt = TASK_ROOT / f"{task_id}.json"
    if alt.exists():
        return alt
    raise FileNotFoundError(f"No task JSON found for {task_id!r}")


def load_task(task_id: str) -> dict[str, Any]:
    return json.loads(task_path(task_id).read_text(encoding="utf-8"))


def select_case(task: dict[str, Any], case_id: str | None) -> dict[str, Any]:
    cases = task["test_cases"]
    if case_id is None:
        return cases[0]
    for case in cases:
        if case["id"] == case_id:
            return case
    valid = ", ".join(case["id"] for case in cases)
    raise ValueError(f"Unknown case {case_id!r}; expected one of: {valid}")


def first_answer_cell(case: dict[str, Any]) -> str:
    answer_cells = case.get("answer_cells") or []
    if not answer_cells:
        raise ValueError(f"Case {case['id']} has no answer cells")
    return answer_cells[0]


def normalize_cell(cell: str) -> str:
    cell = cell.strip().upper()
    if not re.fullmatch(r"[A-C][1-3]", cell):
        raise ValueError(f"Invalid cell {cell!r}; expected A1-C3")
    return cell


def resolve_image_path(path: str) -> Path:
    image_path = Path(path)
    if not image_path.is_absolute():
        image_path = ROOT / image_path
    if not image_path.exists():
        raise FileNotFoundError(f"Image does not exist: {rel_or_abs(image_path)}")
    return image_path


def image_for_cell(case: dict[str, Any], cell: str) -> Path:
    cell = normalize_cell(cell)
    try:
        return resolve_image_path(case["cell_images"][cell]["image_path"])
    except KeyError as error:
        raise ValueError(f"Case {case['id']} does not define cell {cell}") from error


def fit_image(path: Path, max_size: tuple[int, int]) -> Image.Image:
    with Image.open(path) as image:
        image = ImageOps.exif_transpose(image).convert("RGB")
        image.thumbnail(max_size, Image.Resampling.LANCZOS)
        return image.copy()


def draw_centered_text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    font: ImageFont.ImageFont,
    fill: tuple[int, int, int] = TEXT,
) -> None:
    draw.text(xy, text, anchor="mm", font=font, fill=fill)


def make_scratchpad(
    *,
    task: dict[str, Any],
    case: dict[str, Any],
    test_image_path: Path,
    out_path: Path,
) -> Path:
    grid_path = resolve_image_path(case["grid_image"])
    grid = fit_image(grid_path, (900, 900))
    test_image = fit_image(test_image_path, (470, 660))

    pad = 24
    gap = 22
    header_h = 48
    panel_w = 540
    content_h = max(grid.height, 760)
    width = pad * 2 + grid.width + gap + panel_w
    height = pad * 2 + header_h + content_h

    canvas = Image.new("RGB", (width, height), BG)
    draw = ImageDraw.Draw(canvas)
    title_font = load_font(20, bold=True)
    meta_font = load_font(15)

    grid_x = pad
    panel_x = pad + grid.width + gap
    content_y = pad + header_h

    draw.rectangle([grid_x, pad, grid_x + grid.width, pad + header_h - 8], fill=PANEL_BG, outline=LINE, width=1)
    draw.rectangle([panel_x, pad, panel_x + panel_w, pad + header_h - 8], fill=PANEL_BG, outline=LINE, width=1)
    draw_centered_text(draw, (grid_x + grid.width // 2, pad + 20), "REFERENCE GRID", title_font)
    draw_centered_text(draw, (panel_x + panel_w // 2, pad + 20), "TEST IMAGE", title_font)

    canvas.paste(grid, (grid_x, content_y))
    draw.rectangle([grid_x, content_y, grid_x + grid.width - 1, content_y + grid.height - 1], outline=LINE, width=2)

    panel_y0 = content_y
    panel_y1 = content_y + content_h
    draw.rectangle([panel_x, panel_y0, panel_x + panel_w, panel_y1], fill=PANEL_BG, outline=LINE, width=2)

    test_x = panel_x + (panel_w - test_image.width) // 2
    test_y = panel_y0 + 46 + (content_h - 140 - test_image.height) // 2
    draw.rectangle(
        [test_x - 8, test_y - 8, test_x + test_image.width + 8, test_y + test_image.height + 8],
        fill=(238, 238, 234),
        outline=LINE,
        width=1,
    )
    canvas.paste(test_image, (test_x, test_y))
    draw.rectangle([test_x, test_y, test_x + test_image.width - 1, test_y + test_image.height - 1], outline=LINE, width=1)

    footer = f"{task['id']} / {case['id']} / {rel_or_abs(test_image_path)}"
    draw_centered_text(draw, (panel_x + panel_w // 2, panel_y1 - 44), footer, meta_font, fill=MUTED)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out_path, quality=92)
    return out_path


def default_prompt() -> str:
    return (
        "The single image is a visual scratchpad. It contains a labeled 3x3 reference grid "
        "on the left and one unlabeled test image on the right. Use the grid visually. "
        "Identify every reference-grid cell whose class matches the test image. "
        'Return only JSON in this form: {"cells":["A1"],"label":"class name"}'
    )


def run_gemini(
    image_path: Path,
    prompt: str,
    model: str,
    *,
    vertexai: bool,
    project: str | None,
    location: str | None,
) -> str:
    try:
        from google import genai
        from google.genai import types
    except ImportError as error:
        raise RuntimeError("Install the Google GenAI SDK with: pip install google-genai") from error

    mime_type = mimetypes.guess_type(image_path.name)[0] or "image/jpeg"
    client_kwargs: dict[str, Any] = {}
    if vertexai:
        client_kwargs["vertexai"] = True
        if project:
            client_kwargs["project"] = project
        if location:
            client_kwargs["location"] = location

    client = genai.Client(**client_kwargs)
    response = client.models.generate_content(
        model=model,
        contents=[
            types.Part.from_bytes(data=image_path.read_bytes(), mime_type=mime_type),
            prompt,
        ],
    )
    return response.text or ""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compose a visual prompting scratchpad with the grid beside the test image, then optionally call Gemini.",
    )
    parser.add_argument("--task", default="dog_breeds", help="Task id, e.g. dog_breeds")
    parser.add_argument("--case", default=None, help="Case id, e.g. case_01. Defaults to the first case.")
    parser.add_argument("--test-cell", default=None, help="Use a cell's source image as the test image, e.g. A1.")
    parser.add_argument("--test-image", default=None, help="Path to an arbitrary test image.")
    parser.add_argument("--out", default=None, help="Scratchpad output path.")
    parser.add_argument("--run", action="store_true", help="Call Gemini with the composed scratchpad.")
    parser.add_argument("--model", default=os.environ.get("GEMINI_MODEL", "gemini-2.5-flash"))
    parser.add_argument("--vertex", action="store_true", help="Use Vertex AI with Google ADC/gcloud credentials.")
    parser.add_argument("--project", default=os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("CLOUDSDK_CORE_PROJECT"))
    parser.add_argument("--location", default=os.environ.get("GOOGLE_CLOUD_LOCATION") or "us-central1")
    parser.add_argument("--prompt", default=default_prompt(), help="Text prompt sent with the scratchpad.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    task = load_task(args.task)
    case = select_case(task, args.case)

    if args.test_image and args.test_cell:
        raise ValueError("Pass either --test-image or --test-cell, not both")
    if args.test_image:
        test_image_path = resolve_image_path(args.test_image)
        test_id = test_image_path.stem
    else:
        test_cell = normalize_cell(args.test_cell) if args.test_cell else first_answer_cell(case)
        test_image_path = image_for_cell(case, test_cell)
        test_id = test_cell

    out_path = Path(args.out) if args.out else OUTPUT_ROOT / args.task / f"{case['id']}_{test_id}.jpg"
    if not out_path.is_absolute():
        out_path = ROOT / out_path

    scratchpad = make_scratchpad(task=task, case=case, test_image_path=test_image_path, out_path=out_path)
    print(f"scratchpad={rel_or_abs(scratchpad)}")

    if not args.run:
        return 0

    answer = run_gemini(
        scratchpad,
        args.prompt,
        args.model,
        vertexai=args.vertex,
        project=args.project,
        location=args.location,
    )
    print(answer.strip())
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1)

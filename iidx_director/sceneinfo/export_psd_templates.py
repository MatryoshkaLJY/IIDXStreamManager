#!/usr/bin/env python3
"""Export PSD layers as independent OBS scene assets.

Text layers remain DOM nodes so the director can replace their contents. Every
other visible leaf layer is exported as its own transparent PNG and inserted
in PSD stack order. This preserves layer boundaries and allows the red board
layers to be hue-shifted independently at runtime.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path
from typing import Any

from PIL import Image
from psd_tools import PSDImage

CANVAS = (1920, 1080)
PSD_TEMPLATES = {
    "dp_arena": "dp arena.psd",
    "dp_bpl": "dp bpl.psd",
    "sp_arena": "sp arena.psd",
    "sp_bpl": "sp bpl.psd",
    "live": "现场画面.psd",
}
FONT_ALIASES = {
    "FZCCHJW--GB1-0": "FZCCHJW",
    "FZLTTHJW--GB1-0": "FZLTTHJW",
}
TOKEN_ALIASES = {
    "背景色": "background_color",
    "背景板": "background_board",
    "题头": "header",
    "左边": "left",
    "右边": "right",
    "左边队伍名": "left_team_name",
    "右边队伍名": "right_team_name",
    "左边分数": "left_score",
    "右边分数": "right_score",
    "左边队员名": "left_player",
    "右边队员名": "right_player",
    "弹幕和实时画面": "chat_live",
    "弹幕": "chat",
    "广告": "advertisement",
    "红板": "red_board",
    "红名板": "red_name_board",
    "红板长": "red_board_long",
    "CHAT": "chat_title",
    "<图像>": "image",
}
HUE_LAYER_NAMES = {"红板", "红名板", "红板长"}


def _clean_name(value: str | None) -> str:
    raw = getattr(value, "value", value) or "layer"
    return str(raw).replace("\x00", "").strip() or "layer"


def _slug(text: str) -> str:
    text = _clean_name(text)
    if text in TOKEN_ALIASES:
        return TOKEN_ALIASES[text]
    text = re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_").lower()
    return text or "layer"


def _rgb(fill: Any) -> str:
    values = (fill or {}).get("Values", [1, 1, 1, 1])
    rgb = [max(0, min(255, round(float(value) * 255))) for value in values[:3]]
    return "#%02x%02x%02x" % tuple(rgb)


def _text_id(name: str, path: list[str], index: int) -> str:
    name = _clean_name(name)
    lower = name.lower()
    joined = "/".join(path).lower()
    if name == "TPL S3":
        return "header_brand"
    if name in {"DP个人赛", "SP个人赛", "DP团队赛", "SP团队赛"}:
        return "header_match_type"
    if name == "ROUND 1":
        return "header_round"
    if name == "SCRATCH":
        return "header_theme"
    if name == "CHAT":
        return "chat_title"
    if name == "duiyuan":
        match = re.search(r"([1-4])号机", joined)
        if match:
            return f"machine_{match.group(1)}_player"
        if "左边" in joined:
            return "left_player"
        if "右边" in joined:
            return "right_player"
    aliases = {
        "左边队名": "left_team_name",
        "右边队名": "right_team_name",
        "29pt": "left_points" if "左边" in joined else "right_points",
        "30pt": "right_points" if "右边" in joined else "left_points",
        "左边队员名": "left_player",
        "右边队员名": "right_player",
    }
    if lower in aliases:
        return aliases[lower]
    return f"text_{_slug(name)}_{index}"


def _image_id(name: str, path: list[str], index: int) -> str:
    parts = [_slug(part) for part in path if _clean_name(part) not in {"背景色", "背景板"}]
    return f"image_{'_'.join(parts) or _slug(name)}_{index}"


def _walk(layer: Any, path: list[str]) -> list[tuple[Any, list[str]]]:
    name = _clean_name(getattr(layer, "name", None))
    current_path = [*path, name]
    kind = getattr(layer, "kind", None)
    if kind == "type":
        return [(layer, current_path)] if layer.visible else []
    if kind == "group" and not layer.visible:
        return []
    result: list[tuple[Any, list[str]]] = []
    if kind != "group" and layer.visible:
        result.append((layer, current_path))
    if kind == "group" and hasattr(layer, "__iter__"):
        for child in layer:
            result.extend(_walk(child, current_path))
    return result


def _text_manifest(layer: Any, path: list[str], scale_x: float, scale_y: float, index: int) -> dict[str, Any]:
    x1, y1, x2, y2 = layer.bbox
    engine = layer.engine_dict
    style = engine.get("StyleRun", {}).get("RunArray", [{}])[0]
    style_data = style.get("StyleSheet", {}).get("StyleSheetData", {})
    raw_font_name = (layer.resource_dict.get("FontSet") or [{}])[style_data.get("Font", 0)].get("Name", "Noto Sans")
    font_name = str(getattr(raw_font_name, "value", raw_font_name))
    font_family = FONT_ALIASES.get(font_name, font_name)
    font_size = float(style_data.get("FontSize", max(12, y2 - y1)))
    return {
        "kind": "text",
        "id": _text_id(layer.name, path, index),
        "default": _clean_name(layer.text).replace("\r", "\n").strip(),
        "x": round(x1 / scale_x, 3),
        "y": round(y1 / scale_y, 3),
        "width": round((x2 - x1) / scale_x, 3),
        "height": round((y2 - y1) / scale_y, 3),
        "fontSize": round(font_size / ((scale_x + scale_y) / 2), 3),
        "fontFamily": font_family,
        "fontFallback": "FZCCHJW" if font_family == "FZLTTHJW" else "Arial",
        "fontWeight": 400,
        "color": _rgb(style_data.get("FillColor")),
        "horizontalScale": round(float(style_data.get("HorizontalScale", 1.0) or 1.0), 4),
        "textAlign": "left",
        "verticalAlign": "center",
    }


def _write_layer_image(layer: Any, path: list[str], template: str, index: int, output: Path, scale_x: float, scale_y: float) -> dict[str, Any]:
    x1, y1, x2, y2 = layer.bbox
    image = layer.topil()
    if image is None:
        image = layer.composite(force=True)
    if image is None:
        raise RuntimeError(f"unable to render PSD layer: {'/'.join(path)}")
    image = image.convert("RGBA")
    width = max(1, round((x2 - x1) / scale_x))
    height = max(1, round((y2 - y1) / scale_y))
    image = image.resize((width, height), Image.Resampling.LANCZOS)
    image_id = _image_id(layer.name, path, index)
    asset = output / "assets" / "layers" / template / f"{index:03d}_{image_id}.png"
    asset.parent.mkdir(parents=True, exist_ok=True)
    image.save(asset, optimize=True)
    item: dict[str, Any] = {
        "kind": "image",
        "id": image_id,
        "src": asset.relative_to(output).as_posix(),
        "x": round(x1 / scale_x, 3),
        "y": round(y1 / scale_y, 3),
        "width": width,
        "height": height,
    }
    if _clean_name(layer.name) in HUE_LAYER_NAMES:
        item["hueKey"] = image_id
    return item


def _copy_fonts(source: Path, output: Path) -> list[dict[str, str]]:
    fonts_dir = output / "assets" / "fonts"
    fonts_dir.mkdir(parents=True, exist_ok=True)
    fonts: list[dict[str, str]] = []
    for font in sorted(source.glob("*")):
        if font.suffix.lower() not in {".ttf", ".otf", ".woff", ".woff2"}:
            continue
        destination = fonts_dir / font.name
        shutil.copy2(font, destination)
        family = font.stem
        fonts.append({"family": family, "src": destination.relative_to(output).as_posix()})
    return fonts


def export_one(source: Path, template: str, output: Path) -> dict[str, Any]:
    psd = PSDImage.open(source)
    scale_x = psd.width / CANVAS[0]
    scale_y = psd.height / CANVAS[1]
    shutil.rmtree(output / "assets" / "layers" / template, ignore_errors=True)
    # Composite once so PSD text bounds are populated for files with incomplete
    # text records (notably the 1920x1080 DP arena source).
    psd.composite(force=True)
    layers: list[dict[str, Any]] = []
    index = 0
    for root in psd:
        for layer, path in _walk(root, []):
            if getattr(layer, "kind", None) == "type":
                layers.append(_text_manifest(layer, path, scale_x, scale_y, index))
            else:
                layers.append(_write_layer_image(layer, path, template, index, output, scale_x, scale_y))
            index += 1
    return {"layers": layers}


def _resolve_source(source_dir: Path, filename: str) -> Path:
    candidate = source_dir / filename
    backup = source_dir / f"{filename}~"
    if not backup.exists():
        return candidate
    try:
        psd = PSDImage.open(candidate)
        text_layers = []
        leaf_count = 0
        for root in psd:
            for layer, _ in _walk(root, []):
                leaf_count += 1
                if getattr(layer, "kind", None) == "type":
                    text_layers.append(layer)
        if text_layers and any(layer.bbox == (0, 0, 0, 0) for layer in text_layers):
            print(f"Using backup PSD for incomplete text bounds: {backup.name}")
            return backup
        if leaf_count < 15 and filename == "dp arena.psd":
            print(f"Using backup PSD for incomplete layer stack: {backup.name}")
            return backup
    except Exception as exc:
        print(f"Warning: cannot inspect {candidate.name}: {exc}")
    return candidate


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True, help="Directory containing PSD files and fonts")
    parser.add_argument("--output", type=Path, default=Path(__file__).parent)
    args = parser.parse_args()

    templates = {}
    for template, filename in PSD_TEMPLATES.items():
        source = _resolve_source(args.source, filename)
        if not source.exists():
            raise SystemExit(f"missing PSD: {source}")
        print(f"Exporting {source.name} -> {template}")
        templates[template] = export_one(source, template, args.output)
    manifest = {
        "canvas": {"width": CANVAS[0], "height": CANVAS[1]},
        "fonts": _copy_fonts(args.source, args.output),
        "templates": templates,
    }
    serialized = json.dumps(manifest, ensure_ascii=False, indent=2)
    (args.output / "manifest.json").write_text(serialized + "\n", encoding="utf-8")
    (args.output / "manifest.js").write_text("window.IIDX_SCENE_MANIFEST = " + serialized + ";\n", encoding="utf-8")


if __name__ == "__main__":
    main()

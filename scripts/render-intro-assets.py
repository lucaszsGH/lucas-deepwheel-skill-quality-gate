#!/usr/bin/env python3
"""Validate and render bilingual GitHub intro SVG assets without network access."""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import struct
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INTRO = ROOT / "assets" / "intro"
MANIFEST = ROOT / "docs" / "PUBLIC-SURFACE-REVIEW.json"
BRAND_SKILL = "lucas-deepwheel-brand-apply"
ASSETS = (
    "quality-gate-hero-en",
    "quality-gate-hero-zh-CN",
    "quality-gate-workflow-en",
    "quality-gate-workflow-zh-CN",
)
REQUIRED_COPY = {
    "quality-gate-hero-en.svg": "Keep every surface in sync.",
    "quality-gate-hero-zh-CN.svg": "让每个公开面都同步。",
    "quality-gate-workflow-en.svg": "Reconcile GitHub, Actions, install",
    "quality-gate-workflow-zh-CN.svg": "对账 GitHub、Actions、安装版",
}
FORBIDDEN_COLORS = {"#1D1D1F", "#1E6FE8", "#111720", "#F8FAFC"}


def fail(message: str) -> None:
    raise SystemExit("FAIL: " + message)


def load_contract() -> dict:
    try:
        data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail("public-surface review manifest is unavailable: " + type(exc).__name__)
    contract = data.get("production_contract")
    if not isinstance(contract, dict):
        fail("consumer and brand production contract is missing")
    if contract.get("design_system") != BRAND_SKILL:
        fail("DeepWheel Brand Apply is not declared")
    if contract.get("content_languages") != ["en", "zh-CN"]:
        fail("English and Chinese release surfaces are not both declared")
    if contract.get("consumer_reviewed") is not True or contract.get("brand_reviewed") is not True:
        fail("consumer or brand review is incomplete")
    return contract


def allowed_colors() -> set[str]:
    token_text = (INTRO / "source" / "visual-tokens.json").read_text(encoding="utf-8")
    return {value.upper() for value in re.findall(r"#[0-9A-Fa-f]{6}", token_text)}


def png_size(path: Path) -> tuple[int, int] | None:
    try:
        header = path.read_bytes()[:24]
    except OSError:
        return None
    if len(header) != 24 or header[:8] != b"\x89PNG\r\n\x1a\n" or header[12:16] != b"IHDR":
        return None
    return struct.unpack(">II", header[16:24])


def check_sources(require_png: bool = True) -> None:
    load_contract()
    palette = allowed_colors()
    problems = []
    for stem in ASSETS:
        svg = INTRO / (stem + ".svg")
        png = INTRO / (stem + ".png")
        if not svg.is_file():
            problems.append(svg.name + " missing")
            continue
        text = svg.read_text(encoding="utf-8")
        if 'width="1600" height="900" viewBox="0 0 1600 900"' not in text:
            problems.append(svg.name + " is not exact 1600x900")
        if "<title" not in text or "<desc" not in text:
            problems.append(svg.name + " lacks accessible title/desc")
        marker = REQUIRED_COPY[svg.name]
        if marker not in text:
            problems.append(svg.name + " misses consumer copy: " + marker)
        colors = {value.upper() for value in re.findall(r"#[0-9A-Fa-f]{6}", text)}
        invalid = sorted(colors - palette)
        forbidden = sorted(colors & FORBIDDEN_COLORS)
        if invalid:
            problems.append(svg.name + " uses colors outside visual tokens: " + ", ".join(invalid))
        if forbidden:
            problems.append(svg.name + " uses retired DeepWheel colors: " + ", ".join(forbidden))
        if require_png and png_size(png) != (1600, 900):
            problems.append(png.name + " is not an exact 1600x900 PNG")
    if problems:
        fail("; ".join(problems))


def find_chromium() -> str:
    configured = os.environ.get("CHROMIUM_BIN")
    candidates = [
        configured,
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        shutil.which("google-chrome"),
        shutil.which("chromium"),
    ]
    for value in candidates:
        if value and Path(value).is_file():
            return value
    fail("Chromium renderer is unavailable; set CHROMIUM_BIN")


def sharp_runtime() -> tuple[str, dict[str, str]] | None:
    node = os.environ.get("NODE_BIN") or shutil.which("node")
    if not node or not Path(node).is_file():
        return None
    env = dict(os.environ)
    probe = subprocess.run(
        [node, "-e", "require('sharp')"],
        text=True,
        capture_output=True,
        check=False,
        env=env,
        timeout=15,
    )
    return (node, env) if probe.returncode == 0 else None


def render_all() -> None:
    sharp = sharp_runtime()
    chromium = None if sharp else find_chromium()
    with tempfile.TemporaryDirectory(prefix="quality-gate-intro-") as temp:
        temp_root = Path(temp)
        profile = temp_root / "profile"
        rendered = []
        for stem in ASSETS:
            source = INTRO / (stem + ".svg")
            output = temp_root / (stem + ".png")
            if sharp:
                node, node_env = sharp
                script = (
                    "const sharp=require('sharp');const [src,dst]=process.argv.slice(1);"
                    "sharp(src).png().toFile(dst).catch(e=>{console.error(e.message);process.exit(1)});"
                )
                result = subprocess.run(
                    [node, "-e", script, str(source), str(output)],
                    text=True,
                    capture_output=True,
                    check=False,
                    env=node_env,
                    timeout=60,
                )
                if result.returncode != 0 or png_size(output) != (1600, 900):
                    fail("Sharp render failed for " + source.name)
                rendered.append((output, INTRO / output.name))
                continue
            command = [
                str(chromium),
                "--headless=new",
                "--disable-gpu",
                "--hide-scrollbars",
                "--run-all-compositor-stages-before-draw",
                "--user-data-dir=" + str(profile),
                "--window-size=1600,900",
                "--screenshot=" + str(output),
                source.as_uri(),
            ]
            result = subprocess.run(command, text=True, capture_output=True, check=False, timeout=60)
            if result.returncode == 0 and png_size(output) == (3200, 1800):
                sips = shutil.which("sips") or "/usr/bin/sips"
                resized = temp_root / (stem + "-1600.png")
                resize = subprocess.run(
                    [sips, "-z", "900", "1600", str(output), "--out", str(resized)],
                    text=True,
                    capture_output=True,
                    check=False,
                    timeout=60,
                )
                if resize.returncode == 0:
                    os.replace(str(resized), str(output))
            if result.returncode != 0 or png_size(output) != (1600, 900):
                fail("render failed for " + source.name + "; output size=" + str(png_size(output)))
            rendered.append((output, INTRO / output.name))
        for source, destination in rendered:
            os.replace(str(source), str(destination))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="render SVG sources to PNG derivatives")
    parser.add_argument("--brand-skill", help="explicit design-system declaration required for --write")
    parser.add_argument("--consumer-reviewed", action="store_true", help="confirm the consumer brief was reviewed")
    args = parser.parse_args()
    check_sources(require_png=not args.write)
    if args.write:
        if args.brand_skill != BRAND_SKILL or not args.consumer_reviewed:
            fail("--write requires Brand Apply and consumer-review acknowledgements")
        render_all()
        check_sources(require_png=True)
    print("PASS: bilingual consumer and DeepWheel brand intro assets are aligned")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

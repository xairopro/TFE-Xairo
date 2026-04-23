#!/usr/bin/env python3
"""
castelo_svg.py – Generates a futuristic animated SVG silhouette from a
castle photograph, plus a static (fully-drawn) version.

The SVG lines "draw themselves" over exactly 120 seconds (2 min) using
the stroke-dasharray / stroke-dashoffset CSS technique, with a glowing
cyan/teal cyberpunk aesthetic.  The upper half of the image (the castle)
gets more drawing time; the lower half draws faster at the end.

Usage:
    python castelo_monterrei.py [input_image] [output_dir] [prefix] [--no-video]

If no arguments are given the script looks for 'Castelo/castillo-de-monterrei.png'
and outputs into the 'Castelo/' directory.

Outputs:
    castelo_futurista.svg                    – animated (2-minute draw)
    castelo_futurista_static.svg             – fully drawn, dark background
    castelo_futurista_static_transparent.svg – fully drawn, transparent background
    castelo_futurista.mp4                    – 2-minute video (requires ffmpeg)
"""

import sys
import os
import math
import pathlib
import copy
import subprocess
import shutil
import tempfile
import threading
import concurrent.futures
import xml.etree.ElementTree as ET
import argparse

import cv2
import numpy as np

# ──────────────────────────── configuration ────────────────────────────
INPUT_DEFAULT = os.path.join("Castelo", "castillo-de-monterrei.png")
OUTPUT_DIR_DEFAULT = "Castelo"
PREFIX_DEFAULT = "castelo_monterrei"

STROKE_COLOR = "#40E0D0"          # cyan / teal
BG_COLOR = "#0a0e1a"              # very dark blue-black
STROKE_WIDTH = 1.2                # base stroke
THIN_STROKE = 0.6                 # for finer detail paths

TOTAL_DURATION_S = 120            # animation length in seconds (2 min)

TITLE_TEXT = "Castelo de Monterrei"

# Canny edge detection thresholds
CANNY_LOW = 40
CANNY_HIGH = 130

# Contour simplification factor (fraction of arc-length)
EPSILON_FACTOR = 0.0015

# Minimum contour arc-length to keep (removes noise)
MIN_ARC_LENGTH = 20

# Target SVG width in pixels (height scales proportionally)
SVG_WIDTH = 1920

# Top-left dead zone: contours whose bounding box sits entirely inside
# this rectangle are dropped (removes stray cloud / sky lines).
# Expressed as fractions of (width, height).
DEAD_ZONE_X_FRAC = 0.25
DEAD_ZONE_Y_FRAC = 0.18


# ──────────────────────────── helpers ──────────────────────────────────

def detect_edges(img_path: str) -> tuple[np.ndarray, int, int]:
    """Return Canny edge map and image dimensions after resize."""
    img = cv2.imread(img_path, cv2.IMREAD_COLOR)
    if img is None:
        sys.exit(f"Error: cannot read image '{img_path}'")
    h, w = img.shape[:2]

    # Resize for consistent processing
    scale = SVG_WIDTH / w
    img = cv2.resize(img, (SVG_WIDTH, int(h * scale)), interpolation=cv2.INTER_AREA)
    h, w = img.shape[:2]

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Contrast-limited adaptive histogram equalization for better edges
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
    gray = clahe.apply(gray)

    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blur, CANNY_LOW, CANNY_HIGH)

    # Light dilation to close small gaps
    kernel = np.ones((2, 2), np.uint8)
    edges = cv2.dilate(edges, kernel, iterations=1)

    return edges, w, h


def _in_dead_zone(contour: np.ndarray, w: int, h: int) -> bool:
    """True if the contour sits entirely inside the top-left dead zone."""
    pts = contour.squeeze()
    if pts.ndim == 1:
        return True
    max_x = DEAD_ZONE_X_FRAC * w
    max_y = DEAD_ZONE_Y_FRAC * h
    return bool(pts[:, 0].max() < max_x and pts[:, 1].max() < max_y)


def extract_contours(edges: np.ndarray, w: int, h: int) -> list[np.ndarray]:
    """Find, simplify, and filter contours from the edge map."""
    contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

    simplified = []
    for cnt in contours:
        arc = cv2.arcLength(cnt, closed=False)
        if arc < MIN_ARC_LENGTH:
            continue
        eps = EPSILON_FACTOR * arc
        approx = cv2.approxPolyDP(cnt, eps, closed=False)
        if len(approx) < 2:
            continue
        if _in_dead_zone(approx, w, h):
            continue
        simplified.append((arc, approx))

    simplified.sort(key=lambda x: x[0], reverse=True)
    return [pts for _, pts in simplified]


def contour_to_svg_path(contour: np.ndarray) -> str:
    """Convert an OpenCV contour to an SVG 'd' attribute string."""
    pts = contour.squeeze()
    if pts.ndim == 1:
        return ""
    parts = [f"M{pts[0][0]:.1f},{pts[0][1]:.1f}"]
    for x, y in pts[1:]:
        parts.append(f"L{x:.1f},{y:.1f}")
    return " ".join(parts)


def path_length_approx(contour: np.ndarray) -> float:
    """Approximate the drawn length of the contour path."""
    pts = contour.squeeze()
    if pts.ndim == 1:
        return 0.0
    total = 0.0
    for i in range(1, len(pts)):
        dx = pts[i][0] - pts[i - 1][0]
        dy = pts[i][1] - pts[i - 1][1]
        total += math.hypot(dx, dy)
    return total


# ──────────────────── title text as SVG path letters ───────────────────

def _text_path_d(text: str, x0: float, y0: float, char_w: float,
                 char_h: float, spacing: float) -> list[tuple[str, float]]:
    """
    Return a list of (d-string, approx-length) for each character,
    rendered with simple mono-stroke vector glyphs.
    """
    # Minimal single-stroke font: each char defined as a list of
    # polylines in a 0–1 normalised box.  None separates substrokes.
    glyphs: dict[str, list] = {
        "A": [(0,1),(0.5,0),(1,1),None,(0.15,0.6),(0.85,0.6)],
        "B": [(0,1),(0,0),(0.7,0),(0.9,0.15),(0.7,0.45),(0,0.45),(0.7,0.45),(0.95,0.65),(0.7,1),(0,1)],
        "C": [(0.9,0.15),(0.5,0),(0.1,0.2),(0,0.5),(0.1,0.8),(0.5,1),(0.9,0.85)],
        "D": [(0,1),(0,0),(0.6,0),(0.9,0.2),(1,0.5),(0.9,0.8),(0.6,1),(0,1)],
        "E": [(0.9,0),(0,0),(0,0.5),(0.7,0.5),None,(0,0.5),(0,1),(0.9,1)],
        "F": [(0.9,0),(0,0),(0,0.5),(0.7,0.5),None,(0,0.5),(0,1)],
        "G": [(0.9,0.15),(0.5,0),(0.1,0.2),(0,0.5),(0.1,0.8),(0.5,1),(0.9,0.85),(0.9,0.5),(0.55,0.5)],
        "H": [(0,0),(0,1),None,(1,0),(1,1),None,(0,0.5),(1,0.5)],
        "I": [(0.3,0),(0.7,0),None,(0.5,0),(0.5,1),None,(0.3,1),(0.7,1)],
        "J": [(0.2,0),(0.8,0),None,(0.5,0),(0.5,0.85),(0.3,1),(0.1,0.85)],
        "K": [(0,0),(0,1),None,(0.9,0),(0,0.5),(0.9,1)],
        "L": [(0,0),(0,1),(0.9,1)],
        "M": [(0,1),(0,0),(0.5,0.5),(1,0),(1,1)],
        "N": [(0,1),(0,0),(1,1),(1,0)],
        "O": [(0.5,0),(0.1,0.2),(0,0.5),(0.1,0.8),(0.5,1),(0.9,0.8),(1,0.5),(0.9,0.2),(0.5,0)],
        "P": [(0,1),(0,0),(0.7,0),(0.9,0.15),(0.9,0.35),(0.7,0.5),(0,0.5)],
        "Q": [(0.5,0),(0.1,0.2),(0,0.5),(0.1,0.8),(0.5,1),(0.9,0.8),(1,0.5),(0.9,0.2),(0.5,0),None,(0.65,0.75),(1,1)],
        "R": [(0,1),(0,0),(0.7,0),(0.9,0.15),(0.9,0.35),(0.7,0.5),(0,0.5),(0.7,0.5),(0.95,1)],
        "S": [(0.9,0.15),(0.5,0),(0.1,0.15),(0.1,0.35),(0.5,0.5),(0.9,0.65),(0.9,0.85),(0.5,1),(0.1,0.85)],
        "T": [(0,0),(1,0),None,(0.5,0),(0.5,1)],
        "U": [(0,0),(0,0.8),(0.2,1),(0.8,1),(1,0.8),(1,0)],
        "V": [(0,0),(0.5,1),(1,0)],
        "W": [(0,0),(0.25,1),(0.5,0.45),(0.75,1),(1,0)],
        "X": [(0,0),(1,1),None,(1,0),(0,1)],
        "Y": [(0,0),(0.5,0.5),(1,0),None,(0.5,0.5),(0.5,1)],
        "Z": [(0,0),(1,0),(0,1),(1,1)],
        " ": [],
    }

    results: list[tuple[str, float]] = []
    cx = x0
    for ch in text.upper():
        strokes = glyphs.get(ch, glyphs.get(" ", []))
        if not strokes:
            cx += spacing
            continue
        # Split on None to get sub-polylines
        subs: list[list[tuple[float, float]]] = []
        current: list[tuple[float, float]] = []
        for pt in strokes:
            if pt is None:
                if current:
                    subs.append(current)
                    current = []
            else:
                current.append(pt)  # type: ignore[arg-type]
        if current:
            subs.append(current)

        parts: list[str] = []
        total_len = 0.0
        for sub in subs:
            first = True
            prev_x = prev_y = 0.0
            for rx, ry in sub:
                px = cx + rx * char_w
                py = y0 + ry * char_h
                if first:
                    parts.append(f"M{px:.1f},{py:.1f}")
                    first = False
                else:
                    parts.append(f"L{px:.1f},{py:.1f}")
                    total_len += math.hypot(px - prev_x, py - prev_y)
                prev_x, prev_y = px, py

        if parts:
            results.append((" ".join(parts), max(total_len, 1.0)))
        cx += char_w + spacing

    return results


# ──────────────────────────── SVG generation ───────────────────────────

def _add_defs(svg: ET.Element) -> None:
    """Add glow filter definitions."""
    defs = ET.SubElement(svg, "defs")
    filt = ET.SubElement(defs, "filter", {"id": "glow", "x": "-50%", "y": "-50%",
                                           "width": "200%", "height": "200%"})
    ET.SubElement(filt, "feGaussianBlur", {"in": "SourceGraphic",
                                            "stdDeviation": "3",
                                            "result": "blur"})
    merge = ET.SubElement(filt, "feMerge")
    ET.SubElement(merge, "feMergeNode", {"in": "blur"})
    ET.SubElement(merge, "feMergeNode", {"in": "blur"})
    ET.SubElement(merge, "feMergeNode", {"in": "SourceGraphic"})

    filt2 = ET.SubElement(defs, "filter", {"id": "glow-outer", "x": "-80%", "y": "-80%",
                                            "width": "260%", "height": "260%"})
    ET.SubElement(filt2, "feGaussianBlur", {"in": "SourceGraphic",
                                             "stdDeviation": "8",
                                             "result": "blur2"})
    merge2 = ET.SubElement(filt2, "feMerge")
    ET.SubElement(merge2, "feMergeNode", {"in": "blur2"})
    ET.SubElement(merge2, "feMergeNode", {"in": "SourceGraphic"})

    # Extra-strong glow for the title
    filt3 = ET.SubElement(defs, "filter", {"id": "glow-title", "x": "-50%", "y": "-100%",
                                            "width": "200%", "height": "300%"})
    ET.SubElement(filt3, "feGaussianBlur", {"in": "SourceGraphic",
                                             "stdDeviation": "5",
                                             "result": "blur3"})
    merge3 = ET.SubElement(filt3, "feMerge")
    ET.SubElement(merge3, "feMergeNode", {"in": "blur3"})
    ET.SubElement(merge3, "feMergeNode", {"in": "blur3"})
    ET.SubElement(merge3, "feMergeNode", {"in": "SourceGraphic"})


def build_svg(contours: list[np.ndarray], width: int, height: int,
              *, animated: bool = True, bg_color: str = BG_COLOR) -> str:
    """Build the SVG as a string.

    animated=False  → paths are fully visible (no animation).
    bg_color="none" → transparent background.
    """

    # ── Divide contours into 10 temporal groups (staggered draw) ──
    # The upper half of the image (castle) gets 70 % of the total time,
    # the lower half (trees / ground) gets the remaining 30 %.
    n_groups = 10
    groups: list[list[tuple[str, float, float]]] = [[] for _ in range(n_groups)]

    for cnt in contours:
        pts = cnt.squeeze()
        if pts.ndim == 1:
            continue
        cy = float(pts[:, 1].mean())
        bucket = min(int(cy / height * n_groups), n_groups - 1)
        d = contour_to_svg_path(cnt)
        length = path_length_approx(cnt)
        if d and length > 0:
            arc = cv2.arcLength(cnt, closed=False)
            groups[bucket].append((d, length, arc))

    # Upper-half groups (0..4) get 70 % of time, lower-half (5..9) get 30 %
    upper_time = TOTAL_DURATION_S * 0.70   # 84 s for top half
    lower_time = TOTAL_DURATION_S * 0.30   # 36 s for bottom half
    n_upper = n_groups // 2                # 5 groups
    n_lower = n_groups - n_upper           # 5 groups

    # ── Build SVG tree ──
    bg_style = f"background:{bg_color}" if bg_color != "none" else ""
    svg = ET.Element("svg", {
        "xmlns": "http://www.w3.org/2000/svg",
        "viewBox": f"0 0 {width} {height}",
        "width": str(width),
        "height": str(height),
        **(dict(style=bg_style) if bg_style else {}),
    })

    _add_defs(svg)

    style_parts = [
        "/* auto-generated futuristic castle animation */",
    ]
    if bg_color != "none":
        style_parts.append(f"svg {{ background: {bg_color}; }}")

    path_id = 0
    for gi, group in enumerate(groups):
        if gi < n_upper:
            # Upper half: spread across 0 → upper_time with generous overlap
            delay = gi * (upper_time / n_upper)
            draw_time = upper_time / n_upper * 1.6
        else:
            # Lower half: starts after upper_time, faster drawing
            li = gi - n_upper
            delay = upper_time + li * (lower_time / n_lower)
            draw_time = lower_time / n_lower * 1.6
        draw_time = min(draw_time, TOTAL_DURATION_S - delay)

        for d, length, arc in group:
            pid = f"p{path_id}"
            dash = math.ceil(length) + 10

            sw = STROKE_WIDTH if arc > 80 else THIN_STROKE
            fid = "glow" if arc > 120 else "glow-outer"

            if animated:
                style_parts.append(
                    f"#{pid} {{\n"
                    f"  stroke-dasharray: {dash};\n"
                    f"  stroke-dashoffset: {dash};\n"
                    f"  animation: draw-{pid} {draw_time:.2f}s linear {delay:.2f}s forwards;\n"
                    f"}}"
                )
                style_parts.append(
                    f"@keyframes draw-{pid} {{\n"
                    f"  to {{ stroke-dashoffset: 0; }}\n"
                    f"}}"
                )

            ET.SubElement(svg, "path", {
                "id": pid,
                "d": d,
                "fill": "none",
                "stroke": STROKE_COLOR,
                "stroke-width": f"{sw}",
                "stroke-linecap": "round",
                "stroke-linejoin": "round",
                "filter": f"url(#{fid})",
                "opacity": "0.92",
            })
            path_id += 1

    style_el = ET.SubElement(svg, "style")
    style_el.text = "\n".join(style_parts)

    # ── Serialise ──
    ET.indent(svg, space="  ")
    xml_bytes = ET.tostring(svg, encoding="unicode", xml_declaration=False)
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_bytes


# ──────────────── direct-render MP4 (numpy/cv2, no rsvg) ─────────────

def _cumlen(pts: np.ndarray) -> np.ndarray:
    """Cumulative arc-length at each vertex (shape N,), starting at 0."""
    d = np.diff(pts, axis=0)
    return np.concatenate([[0.0], np.cumsum(np.hypot(d[:, 0], d[:, 1]))])


def _partial_pts(pts: np.ndarray, cl: np.ndarray, frac: float) -> np.ndarray:
    """Return the first `frac` fraction of a polyline as float32 Nx2 array."""
    if frac >= 1.0:
        return pts
    total = cl[-1]
    if total == 0.0:
        return pts[:1]
    target = total * frac
    idx = int(np.searchsorted(cl, target, side="right")) - 1
    idx = max(0, min(idx, len(pts) - 2))
    seg = cl[idx + 1] - cl[idx]
    if seg > 0.0:
        t = (target - cl[idx]) / seg
        interp = pts[idx] + t * (pts[idx + 1] - pts[idx])
        return np.vstack([pts[:idx + 1], interp[np.newaxis]]).astype(np.float32)
    return pts[:idx + 1].astype(np.float32)


def _parse_d_to_strokes(d: str) -> list[np.ndarray]:
    """Convert a simple M/L SVG path string into a list of polyline arrays."""
    import re
    strokes: list[np.ndarray] = []
    cur: list[list[float]] = []
    for cmd, xs, ys in re.findall(r"([ML])([\d.]+),([\d.]+)", d):
        pt = [float(xs), float(ys)]
        if cmd == "M" and cur:
            strokes.append(np.array(cur, dtype=np.float32))
            cur = [pt]
        else:
            cur.append(pt)
    if cur:
        strokes.append(np.array(cur, dtype=np.float32))
    return strokes


def _draw_partial(canvas: np.ndarray,
                  strokes: list[np.ndarray], cls: list[np.ndarray],
                  total_len: float, frac: float,
                  color: tuple, thickness: int) -> None:
    """Draw *frac* of a multi-sub-stroke path onto *canvas* (in-place)."""
    if frac <= 0.0 or total_len == 0.0:
        return
    remaining = total_len * min(frac, 1.0)
    for pts, cl in zip(strokes, cls):
        slen = cl[-1]
        if len(pts) < 2 or slen == 0:
            continue
        if remaining >= slen:
            pi = pts.reshape(-1, 1, 2).astype(np.int32)
            cv2.polylines(canvas, [pi], False, color, thickness, cv2.LINE_AA)
            remaining -= slen
        else:
            partial = _partial_pts(pts, cl, remaining / slen)
            if len(partial) >= 2:
                pi = partial.reshape(-1, 1, 2).astype(np.int32)
                cv2.polylines(canvas, [pi], False, color, thickness, cv2.LINE_AA)
            break


def _collect_video_items(contours: list[np.ndarray], width: int, height: int):
    """Mirror build_svg timing; return pre-processed items for rendering.

    Returns
    -------
    contour_items : list of (strokes, cls, total_len, delay, duration, thick)
    title_items   : list of (strokes, cls, total_len, delay, duration, thick)
    """
    n_groups  = 10
    upper_time = TOTAL_DURATION_S * 0.70
    lower_time = TOTAL_DURATION_S * 0.30
    n_upper    = n_groups // 2
    n_lower    = n_groups - n_upper

    groups: list[list] = [[] for _ in range(n_groups)]
    for cnt in contours:
        pts = cnt.squeeze()
        if pts.ndim == 1 or len(pts) < 2:
            continue
        pts = pts.astype(np.float32)
        cy  = float(pts[:, 1].mean())
        bucket = min(int(cy / height * n_groups), n_groups - 1)
        arc = cv2.arcLength(cnt, closed=False)
        thick = 2 if arc > 80 else 1
        cl  = _cumlen(pts)
        tl  = float(cl[-1])
        if tl > 0:
            groups[bucket].append(([pts], [cl], tl, arc, thick))

    contour_items = []
    for gi, group in enumerate(groups):
        if gi < n_upper:
            delay     = gi * (upper_time / n_upper)
            draw_time = upper_time / n_upper * 1.6
        else:
            li        = gi - n_upper
            delay     = upper_time + li * (lower_time / n_lower)
            draw_time = lower_time / n_lower * 1.6
        draw_time = min(draw_time, TOTAL_DURATION_S - delay)
        for strokes, cls, tl, arc, thick in group:
            contour_items.append((strokes, cls, tl, delay, draw_time, thick))

    title_items = []

    return contour_items, title_items


def _render_frame_np(contour_items, title_items,
                     t: float, width: int, height: int) -> np.ndarray:
    """Render one animation frame at time *t* as a BGR uint8 array."""
    _C = (208, 224, 64)   # #40E0D0 → BGR

    sharp = np.zeros((height, width, 3), dtype=np.uint8)

    for strokes, cls, tl, delay, duration, thick in contour_items:
        elapsed = t - delay
        if elapsed <= 0.0 or duration <= 0.0:
            continue
        _draw_partial(sharp, strokes, cls, tl, elapsed / duration, _C, thick)

    for strokes, cls, tl, delay, duration, thick in title_items:
        elapsed = t - delay
        if elapsed <= 0.0 or duration <= 0.0:
            continue
        _draw_partial(sharp, strokes, cls, tl, elapsed / duration, _C, thick)

    # Glow: simulate SVG feGaussianBlur (stdDev 3 and 8) + feMerge
    glow_near = cv2.GaussianBlur(sharp, (0, 0), sigmaX=3)
    glow_far  = cv2.GaussianBlur(sharp, (0, 0), sigmaX=8)

    # Background #0a0e1a → BGR = (26, 14, 10)
    frame = np.full((height, width, 3), [26, 14, 10], dtype=np.float32)
    frame += glow_far.astype(np.float32)  * 0.5
    frame += glow_near.astype(np.float32) * 1.2
    frame += sharp.astype(np.float32)
    np.clip(frame, 0, 255, out=frame)
    return frame.astype(np.uint8)


def export_mp4(contours: list, width: int, height: int,
               duration_s: int, output_path: str, fps: int = 24) -> bool:
    """Render the animation directly with numpy/cv2 at full resolution.

    Frames are rendered in parallel (ThreadPoolExecutor) and piped straight
    to ffmpeg — no rsvg-convert, no temp PNGs, no quality loss.
    """
    if not shutil.which("ffmpeg"):
        print("  ⚠ ffmpeg not found – skipping MP4 export.")
        print("    Install with:  brew install ffmpeg")
        return False

    contour_items, title_items = _collect_video_items(contours, width, height)
    total_frames = duration_s * fps
    workers      = min(os.cpu_count() or 4, 8)
    batch_size   = workers * 4   # frames held in memory per batch

    print(f"    Rendering {total_frames} frames "
          f"({fps} fps, {width}×{height}, {workers} workers) …")

    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo", "-vcodec", "rawvideo",
        "-s", f"{width}x{height}",
        "-pix_fmt", "bgr24",
        "-r", str(fps),
        "-i", "pipe:0",
        "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease:flags=lanczos,"
               "pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=black",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-preset", "medium", "-crf", "18",
        output_path,
    ]
    proc = subprocess.Popen(
        ffmpeg_cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            for b_start in range(0, total_frames, batch_size):
                b_end = min(b_start + batch_size, total_frames)
                futs  = {
                    pool.submit(
                        _render_frame_np, contour_items, title_items,
                        fi / fps, width, height
                    ): fi
                    for fi in range(b_start, b_end)
                }
                # Collect in render order (arbitrary), then write in frame order
                rendered: dict[int, bytes] = {}
                for fut in concurrent.futures.as_completed(futs):
                    rendered[futs[fut]] = fut.result().tobytes()
                for fi in range(b_start, b_end):
                    proc.stdin.write(rendered[fi])

                if b_start == 0 or b_end == total_frames or \
                        (b_start // (fps * 10)) < (b_end // (fps * 10)):
                    print(f"      {b_end / total_frames * 100:5.1f}%"
                          f"  ({b_end}/{total_frames} frames)")
    except BrokenPipeError:
        pass
    finally:
        try:
            proc.stdin.close()
        except Exception:
            pass

    proc.wait()
    stderr = proc.stderr.read()
    if proc.returncode != 0:
        print(f"  ⚠ ffmpeg failed (exit {proc.returncode}):")
        for line in stderr.decode(errors="replace").strip().splitlines()[-10:]:
            print(f"    {line}")
        return False
    return True


# ──────────────────────────── main ─────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Generate futuristic SVG silhouette from a photo.")
    parser.add_argument("input_image", nargs="?", default=INPUT_DEFAULT,
                        help="Path to the input image")
    parser.add_argument("output_dir", nargs="?", default=OUTPUT_DIR_DEFAULT,
                        help="Directory for output files")
    parser.add_argument("prefix", nargs="?", default=PREFIX_DEFAULT,
                        help="Prefix for output filenames")
    parser.add_argument("--no-video", action="store_true",
                        help="Skip MP4 video generation")
    args = parser.parse_args()

    input_path = args.input_image
    output_dir = args.output_dir
    prefix = args.prefix
    skip_video = args.no_video

    # Ensure output directory exists
    pathlib.Path(output_dir).mkdir(parents=True, exist_ok=True)

    out_animated = os.path.join(output_dir, f"{prefix}_1.svg")
    out_static = os.path.join(output_dir, f"{prefix}_static_1.svg")
    out_transparent = os.path.join(output_dir, f"{prefix}_transparent_1.svg")
    out_mp4 = os.path.join(output_dir, f"{prefix}_1.mp4")

    if not pathlib.Path(input_path).is_file():
        sys.exit(f"Error: input image '{input_path}' not found.")

    total_steps = 6 if skip_video else 7

    print(f"[1/{total_steps}] Reading image: {input_path}")
    edges, w, h = detect_edges(input_path)

    print(f"[2/{total_steps}] Extracting contours (filtering top-left sky) …")
    contours = extract_contours(edges, w, h)
    print(f"       → {len(contours)} paths retained")

    print(f"[3/{total_steps}] Building animated SVG ({TOTAL_DURATION_S}s draw) …")
    svg_anim = build_svg(contours, w, h, animated=True)
    pathlib.Path(out_animated).write_text(svg_anim, encoding="utf-8")
    print(f"       → {out_animated}")

    print(f"[4/{total_steps}] Building static SVG (dark background) …")
    svg_static = build_svg(contours, w, h, animated=False)
    pathlib.Path(out_static).write_text(svg_static, encoding="utf-8")
    print(f"       → {out_static}")

    print(f"[5/{total_steps}] Building static SVG (transparent background) …")
    svg_transparent = build_svg(contours, w, h, animated=False, bg_color="none")
    pathlib.Path(out_transparent).write_text(svg_transparent, encoding="utf-8")
    print(f"       → {out_transparent}")

    ok = False
    if not skip_video:
        print(f"[6/{total_steps}] Exporting MP4 ({TOTAL_DURATION_S}s, 24 fps) …")
        ok = export_mp4(contours, w, h, TOTAL_DURATION_S, out_mp4)
        if ok:
            print(f"       → {out_mp4}")

    step_done = total_steps
    print(f"[{step_done}/{total_steps}] Done!")
    print(f"       Outputs:")
    print(f"         {out_animated}  (SVG animado, 2 min)")
    print(f"         {out_static}  (estático, fondo escuro)")
    print(f"         {out_transparent}  (estático, fondo transparente)")
    if ok:
        print(f"         {out_mp4}  (vídeo, 2 min)")


if __name__ == "__main__":
    main()

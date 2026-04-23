#!/usr/bin/env python3
"""Quick 10-frame test of the MP4 pipeline using the existing animated SVG."""
import sys, pathlib, tempfile, shutil, subprocess, re
import xml.etree.ElementTree as ET

SVG_FILE = "castelo_futurista.svg"
BG_COLOR = "#0a0e1a"

svg_text = pathlib.Path(SVG_FILE).read_text()
print(f"SVG loaded: {len(svg_text)} chars")

# Register namespace so ET.tostring doesn't add ns0: prefixes
ET.register_namespace("", "http://www.w3.org/2000/svg")

# Parse
raw_xml = svg_text.split("\n", 1)[1]
tree = ET.fromstring(raw_xml)

# Find <style>
NS = "{http://www.w3.org/2000/svg}"
style_el = tree.find(f"{NS}style") or tree.find("style")
if style_el is None:
    for el in tree.iter():
        if el.tag.endswith("style"):
            style_el = el
            break

if style_el is None:
    sys.exit("No <style> found!")
print(f"<style> found, text length: {len(style_el.text or '')}")

# Parse animation params from CSS
params = []
lines = style_el.text.split("\n")
i = 0
while i < len(lines):
    m = re.match(r"^(#p\d+)\s*\{", lines[i])
    if m:
        pid = m.group(1)
        block = [lines[i]]
        i += 1
        while i < len(lines) and not lines[i].strip().startswith("}"):
            block.append(lines[i])
            i += 1
        if i < len(lines):
            i += 1
        da = do = dur = delay = None
        for bl in block:
            x = re.search(r"stroke-dasharray:\s*(\d+)", bl)
            if x: da = int(x.group(1))
            x = re.search(r"stroke-dashoffset:\s*(\d+)", bl)
            if x: do = int(x.group(1))
            x = re.search(r"animation:.*?(\d+\.?\d*)s\s+linear\s+(\d+\.?\d*)s", bl)
            if x: dur, delay = float(x.group(1)), float(x.group(2))
        if da and do and dur:
            params.append((pid, da, do, dur, delay or 0.0))
        continue
    i += 1

print(f"Parsed {len(params)} animation params")

# Get SVG dimensions from viewBox
vb = tree.get("viewBox", "0 0 1920 1280").split()
W, H = int(float(vb[2])), int(float(vb[3]))
print(f"Dimensions: {W}x{H}")

# Render 10 test frames
tmpdir = tempfile.mkdtemp(prefix="castelo_test10_")
tmp_svg = pathlib.Path(tmpdir) / "_frame.svg"
rw, rh = W // 2, H // 2
fps = 15

for fi in range(10):
    t = fi * 12.0  # spread across 0–108s of the 120s animation
    # Bake CSS
    css_parts = [f"svg {{ background: {BG_COLOR}; }}"]
    for pid, da, do_init, dur, delay in params:
        elapsed = max(0.0, t - delay)
        progress = min(1.0, elapsed / dur)
        offset = do_init * (1.0 - progress)
        css_parts.append(f"{pid} {{ stroke-dasharray: {da}; stroke-dashoffset: {offset:.1f}; }}")
    style_el.text = "\n".join(css_parts)

    frame_xml = '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(tree, encoding="unicode")
    tmp_svg.write_text(frame_xml, encoding="utf-8")
    out_png = pathlib.Path(tmpdir) / f"frame_{fi:06d}.png"

    proc = subprocess.run(
        ["rsvg-convert", "-w", str(rw), "-h", str(rh), "-f", "png", "-o", str(out_png), str(tmp_svg)],
        capture_output=True, stdin=subprocess.DEVNULL,
    )
    import os
    sz = os.path.getsize(out_png) if out_png.exists() else 0
    print(f"  frame {fi} (t={t:.0f}s): rsvg exit={proc.returncode}, png={sz} bytes")
    if proc.returncode != 0:
        print(f"    stderr: {proc.stderr[:300]}")
        break

# Encode test MP4
pat = str(pathlib.Path(tmpdir) / "frame_%06d.png")
cmd = [
    "ffmpeg", "-y", "-framerate", str(fps), "-i", pat,
    "-vf", f"scale={W}:{H}:flags=lanczos,pad=ceil(iw/2)*2:ceil(ih/2)*2",
    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "fast", "-crf", "20",
    str(pathlib.Path(tmpdir) / "test.mp4"),
]
r = subprocess.run(cmd, capture_output=True, text=True, stdin=subprocess.DEVNULL)
print(f"ffmpeg exit: {r.returncode}")
if r.returncode != 0:
    for line in r.stderr.strip().splitlines()[-5:]:
        print(f"  {line}")
else:
    mp4 = pathlib.Path(tmpdir) / "test.mp4"
    print(f"MP4 OK: {os.path.getsize(mp4)} bytes")

shutil.rmtree(tmpdir)
print("Test done.")

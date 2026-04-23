#!/usr/bin/env python3
"""Quick test: render 3 frames and try ffmpeg encoding."""
import subprocess, tempfile, pathlib, os, shutil

tmpdir = tempfile.mkdtemp(prefix="castelo_test_")
svg_path = pathlib.Path(tmpdir) / "test.svg"
svg = pathlib.Path("castelo_futurista_static.svg").read_text()
svg_path.write_text(svg)

for i in range(3):
    out = f"{tmpdir}/frame_{i:06d}.png"
    r = subprocess.run(
        ["rsvg-convert", "-w", "1920", "-h", "1280", "-f", "png", "-o", out, str(svg_path)],
        capture_output=True, stdin=subprocess.DEVNULL,
    )
    if r.returncode != 0:
        print(f"rsvg FAIL: {r.stderr}")
        break
    sz = os.path.getsize(out)
    print(f"frame {i}: {sz} bytes")

pat = f"{tmpdir}/frame_%06d.png"
r = subprocess.run([
    "ffmpeg", "-y", "-framerate", "30", "-i", pat,
    "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2",
    "-c:v", "libx264", "-pix_fmt", "yuv420p",
    "-preset", "fast", "-crf", "18",
    f"{tmpdir}/test.mp4",
], capture_output=True, text=True, stdin=subprocess.DEVNULL)

print(f"ffmpeg exit: {r.returncode}")
if r.returncode != 0:
    for line in r.stderr.strip().splitlines()[-10:]:
        print(line)
else:
    print(f"MP4 size: {os.path.getsize(tmpdir + '/test.mp4')} bytes")

shutil.rmtree(tmpdir)

"""Generate the sleepy skull startup animation from tools/startup_skull.png (64x32 per panel).

Needs Pillow (pip install pillow).

    python tools/startup_skull_gen.py preview startup-skull-preview.gif
    python tools/startup_skull_gen.py frames expressions/startup_skull

"frames" writes the unique PNGs as "startup_skull (N).png" and prints the frame
sequence to paste into the "startup_skull" expression in animation.json.
"""
import json
import math
import os
import sys
from PIL import Image

W, H = 64, 32
FRAME_MS = 40
SOURCE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "startup_skull.png")
OFFSET_X = (W - 32) // 2
EYE_GLOW = (230, 210, 255)
EYES = [(x, y) for y in (22, 23) for x in (10, 11, 12, 13, 18, 19, 20, 21)]


def load_parts():
    """Splits the 32x32 source into ring, zz and skull pixels: {(x, y): color}.
    The dark grey background becomes black, since black is "off" on the panels."""
    src = Image.open(SOURCE).convert("RGB")
    if src.size != (32, 32):
        raise ValueError(f"{SOURCE} must be 32x32, got {src.size}")
    ring, zz, skull = {}, {}, {}
    for y in range(32):
        for x in range(32):
            c = src.getpixel((x, y))
            if max(c) < 0x40:
                continue
            if min(c) > 0xC0:
                (zz if 8 <= x <= 23 and 2 <= y <= 13 else ring)[(x, y)] = c
            else:
                skull[(x, y)] = c
    return ring, zz, skull


def ring_order(ring):
    """Ring pixels sorted clockwise from the top."""
    def angle(p):
        return (math.atan2(p[0] - 15.5, -(p[1] - 15.5)) + 2 * math.pi) % (2 * math.pi)
    return sorted(ring, key=angle)


def render(layers):
    """layers: list of ({(x, y): color}, brightness 0-1), later layers drawn on top."""
    img = Image.new("RGB", (W, H))
    px = img.load()
    for pixels, level in layers:
        for (x, y), c in pixels.items():
            px[x + OFFSET_X, y] = tuple(round(v * level) for v in c)
    return img


def ms(milliseconds):
    return max(1, round(milliseconds / FRAME_MS))


def build():
    """Returns (unique frames, sequence of 1-based frame numbers, one per FRAME_MS)."""
    ring, zz, skull = load_parts()
    small_z = {p: c for p, c in zz.items() if p[0] <= 13}
    eyes = {p: EYE_GLOW for p in EYES}
    frames, seq, seen = [], [], {}

    def add(img, hold_frames=1):
        # Reuse identical frames so they only take flash space once
        key = img.tobytes()
        if key not in seen:
            frames.append(img)
            seen[key] = len(frames)
        seq.extend([seen[key]] * hold_frames)

    add(render([]), ms(240))

    # Ring draws in clockwise from the top
    order = ring_order(ring)
    steps = 16
    for s in range(1, steps + 1):
        drawn = {p: ring[p] for p in order[:round(len(order) * s / steps)]}
        add(render([(drawn, 1)]))

    # Skull fades in
    for s in range(1, 11):
        add(render([(ring, 1), (skull, s / 10)]))

    # Snoring: z, then zZ, then quiet, twice
    for _ in range(2):
        add(render([(ring, 1), (skull, 1), (small_z, 1)]), ms(400))
        add(render([(ring, 1), (skull, 1), (zz, 1)]), ms(600))
        add(render([(ring, 1), (skull, 1)]), ms(300))

    # Wakes up: eyes light up and the full logo holds
    for s in range(1, 5):
        add(render([(ring, 1), (skull, 1), (eyes, s / 4)]))
    add(render([(ring, 1), (skull, 1), (zz, 1), (eyes, 1)]), ms(1500))

    # Everything fades out
    for s in range(11, -1, -1):
        add(render([(ring, s / 12), (skull, s / 12), (zz, s / 12), (eyes, s / 12)]))
    return frames, seq


def preview(out):
    frames, seq = build()
    scale, gap = 6, 12
    rendered, durations, last = [], [], None
    for idx in seq:
        if idx == last:
            durations[-1] += FRAME_MS
            continue
        big = frames[idx - 1].resize((W * scale, H * scale), Image.NEAREST)
        canvas = Image.new("RGB", (W * 2 * scale + gap, H * scale), (24, 24, 24))
        canvas.paste(big, (0, 0))
        canvas.paste(big, (W * scale + gap, 0))   # flip_right is false: both panels match
        rendered.append(canvas)
        durations.append(FRAME_MS)
        last = idx
    durations[-1] += 1500
    rendered[0].save(out, save_all=True, append_images=rendered[1:], duration=durations, loop=0)
    print(f"{len(frames)} unique frames, {len(seq) * FRAME_MS / 1000:.1f}s long")


def write_frames(out_dir):
    frames, seq = build()
    os.makedirs(out_dir, exist_ok=True)
    for i, f in enumerate(frames, 1):
        f.save(f"{out_dir}/startup_skull ({i}).png")
    print(len(frames))
    print(json.dumps(seq))


if __name__ == "__main__":
    {"preview": preview, "frames": write_frames}[sys.argv[1]](sys.argv[2])

#!/usr/bin/env python3
"""ZapClin 15s cinematic vertical commercial composer."""

from __future__ import annotations

import math
import os
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

ROOT = Path("/workspace/zapclin-commercial")
ASSETS = Path("/opt/cursor/artifacts/assets")
FONTS = ROOT / "fonts"
OUT_DIR = ROOT / "out"
FRAMES = ROOT / "render_frames"
W, H = 1080, 1920
FPS = 30
DURATION = 15.0
TOTAL = int(DURATION * FPS)  # 450

FONT_DISPLAY = str(FONTS / "Oswald-Bold.ttf")
FONT_BEBAS = str(FONTS / "BebasNeue-Regular.ttf")
FONT_BODY = str(FONTS / "Montserrat-SemiBold.ttf")
FONT_MED = str(FONTS / "Montserrat-Medium.ttf")
LOGO = Path("/workspace/assets/logo-oficial-transp.png")

SCENES = {
    "s1": ASSETS / "zapclin_scene1_helmet_closeup.png",
    "s1b": ASSETS / "zapclin_scene1b_helmet_pullback.png",
    "s2": ASSETS / "zapclin_scene2_gear_details.png",
    "s3": ASSETS / "zapclin_scene3_helmet_interior.png",
    "s4": ASSETS / "zapclin_scene4_clean_helmet.png",
    "s4b": ASSETS / "zapclin_scene4b_visor_shine.png",
    "s5": ASSETS / "zapclin_scene5_hero_shot.png",
}


def ensure_dirs() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    FRAMES.mkdir(parents=True, exist_ok=True)
    for p in FRAMES.glob("*.png"):
        p.unlink()


def load_base(path: Path) -> Image.Image:
    im = Image.open(path).convert("RGB")
    # Upscale to at least cover 1080x1920 with room for Ken Burns
    target_w, target_h = int(W * 1.22), int(H * 1.22)
    im = im.resize((target_w, target_h), Image.Resampling.LANCZOS)
    # Mild cinematic grade
    im = ImageEnhance.Contrast(im).enhance(1.08)
    im = ImageEnhance.Color(im).enhance(0.95)
    im = ImageEnhance.Sharpness(im).enhance(1.15)
    return im


def sample_ken(
    base: Image.Image,
    t: float,
    *,
    zoom_from: float = 1.0,
    zoom_to: float = 1.12,
    pan_x: float = 0.0,
    pan_y: float = 0.0,
    ease: str = "ease_in_out",
) -> Image.Image:
    """Crop a 1080x1920 window with Ken Burns motion. t in [0,1]."""
    if ease == "ease_in_out":
        u = 0.5 - 0.5 * math.cos(math.pi * t)
    elif ease == "ease_out":
        u = 1 - (1 - t) ** 2
    elif ease == "ease_in":
        u = t * t
    else:
        u = t

    zoom = zoom_from + (zoom_to - zoom_from) * u
    bw, bh = base.size
    cw, ch = int(W / zoom), int(H / zoom)
    # center + pan (pan in fraction of leftover)
    max_x = bw - cw
    max_y = bh - ch
    cx = max_x * 0.5 + pan_x * max_x * 0.5 * u
    cy = max_y * 0.5 + pan_y * max_y * 0.5 * u
    cx = max(0, min(max_x, cx))
    cy = max(0, min(max_y, cy))
    crop = base.crop((int(cx), int(cy), int(cx) + cw, int(cy) + ch))
    return crop.resize((W, H), Image.Resampling.LANCZOS)


def font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size)


def draw_centered_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    y: int,
    fnt: ImageFont.FreeTypeFont,
    fill=(255, 255, 255, 255),
    stroke: int = 0,
    stroke_fill=(0, 0, 0, 180),
) -> None:
    bbox = draw.textbbox((0, 0), text, font=fnt)
    tw = bbox[2] - bbox[0]
    x = (W - tw) // 2
    draw.text(
        (x, y),
        text,
        font=fnt,
        fill=fill,
        stroke_width=stroke,
        stroke_fill=stroke_fill,
    )


def wrap_text(text: str, fnt: ImageFont.FreeTypeFont, max_w: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    cur = ""
    dummy = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    for w in words:
        trial = (cur + " " + w).strip()
        bb = dummy.textbbox((0, 0), trial, font=fnt)
        if bb[2] - bb[0] <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def overlay_text_block(
    frame: Image.Image,
    lines: list[str],
    *,
    alpha: float,
    y_start: int,
    size: int = 52,
    color=(255, 255, 255),
    accent_word: str | None = None,
    accent_color=(220, 30, 40),
    font_path: str = FONT_DISPLAY,
    letter_space: int = 8,
) -> Image.Image:
    if alpha <= 0.01:
        return frame
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    fnt = font(font_path, size)
    y = y_start
    for line in lines:
        if accent_word and accent_word in line.upper():
            # split around accent
            up = line.upper()
            idx = up.find(accent_word)
            before = line[:idx]
            mid = line[idx : idx + len(accent_word)]
            after = line[idx + len(accent_word) :]
            parts = [(before, color), (mid, accent_color), (after, color)]
            total_w = 0
            sizes = []
            for t, _ in parts:
                bb = draw.textbbox((0, 0), t, font=fnt)
                sizes.append(bb[2] - bb[0])
                total_w += bb[2] - bb[0]
            x = (W - total_w) // 2
            for (t, c), tw in zip(parts, sizes):
                if t:
                    draw.text(
                        (x, y),
                        t,
                        font=fnt,
                        fill=(*c, int(255 * alpha)),
                        stroke_width=2,
                        stroke_fill=(0, 0, 0, int(160 * alpha)),
                    )
                x += tw
        else:
            draw_centered_text(
                draw,
                line,
                y,
                fnt,
                fill=(*color, int(255 * alpha)),
                stroke=2,
                stroke_fill=(0, 0, 0, int(160 * alpha)),
            )
        y += size + letter_space
    # soft vignette under text for readability
    vignette = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    vd = ImageDraw.Draw(vignette)
    band_h = size * len(lines) + 80
    vd.rectangle(
        (0, y_start - 40, W, y_start + band_h),
        fill=(0, 0, 0, int(70 * alpha)),
    )
    vignette = vignette.filter(ImageFilter.GaussianBlur(18))
    out = frame.convert("RGBA")
    out = Image.alpha_composite(out, vignette)
    out = Image.alpha_composite(out, overlay)
    return out.convert("RGB")


def fade_alpha(t: float, fade_in: float = 0.35, hold_end: float = 0.85) -> float:
    """t local 0..1 within scene."""
    if t < fade_in:
        return t / fade_in
    if t > hold_end:
        return max(0.0, (1 - t) / (1 - hold_end))
    return 1.0


def flash_white(frame: Image.Image, amount: float) -> Image.Image:
    if amount <= 0:
        return frame
    white = Image.new("RGB", frame.size, (255, 255, 255))
    return Image.blend(frame, white, min(1.0, amount))


def light_sweep(frame: Image.Image, t: float) -> Image.Image:
    """Diagonal light sweep overlay."""
    if t < 0 or t > 1:
        return frame
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    # moving band
    cx = int(-200 + t * (W + 400))
    for i in range(80):
        a = int(40 * math.sin(math.pi * i / 80) * (0.4 + 0.6 * math.sin(t * math.pi)))
        x = cx + i * 3
        draw.polygon(
            [(x, 0), (x + 60, 0), (x - 200, H), (x - 260, H)],
            fill=(255, 255, 255, a),
        )
    out = frame.convert("RGBA")
    out = Image.alpha_composite(out, overlay)
    return out.convert("RGB")


def add_particles(frame: Image.Image, seed: int, density: int = 40, bright: bool = False) -> Image.Image:
    rng = np.random.default_rng(seed)
    out = frame.convert("RGBA")
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    for _ in range(density):
        x = int(rng.integers(0, W))
        y = int(rng.integers(0, H))
        r = int(rng.integers(1, 3 if not bright else 4))
        a = int(rng.integers(30, 120 if not bright else 180))
        col = (255, 255, 255, a) if not bright else (255, 240, 220, a)
        draw.ellipse((x - r, y - r, x + r, y + r), fill=col)
    out = Image.alpha_composite(out, layer)
    return out.convert("RGB")


def paste_logo(frame: Image.Image, alpha: float, y: int = 1480) -> Image.Image:
    if alpha <= 0.01:
        return frame
    logo = Image.open(LOGO).convert("RGBA")
    # scale logo
    lw = 420
    ratio = lw / logo.width
    lh = int(logo.height * ratio)
    logo = logo.resize((lw, lh), Image.Resampling.LANCZOS)
    # apply alpha
    r, g, b, a = logo.split()
    a = a.point(lambda p: int(p * alpha))
    logo = Image.merge("RGBA", (r, g, b, a))
    out = frame.convert("RGBA")
    x = (W - lw) // 2
    out.alpha_composite(logo, (x, y))
    return out.convert("RGB")


def crossfade(a: Image.Image, b: Image.Image, t: float) -> Image.Image:
    return Image.blend(a, b, max(0.0, min(1.0, t)))


def render_frame(i: int, bases: dict[str, Image.Image]) -> Image.Image:
    t = i / FPS  # absolute seconds

    # --- Scene timing ---
    # 0-3: helmet closeup
    # 3-6: gear
    # 6-9: interior dirty
    # 9-12: clean transform
    # 12-15: hero + logo

    if t < 3.0:
        local = t / 3.0
        # blend extreme closeup into slight pullback near end
        a = sample_ken(bases["s1"], local, zoom_from=1.0, zoom_to=1.14, pan_y=-0.15, ease="ease_in")
        b = sample_ken(bases["s1b"], local, zoom_from=1.08, zoom_to=1.0, pan_y=0.1, ease="ease_out")
        frame = crossfade(a, b, max(0, (local - 0.65) / 0.35))
        frame = add_particles(frame, seed=i, density=55)
        alpha = fade_alpha(local, 0.25, 0.9)
        frame = overlay_text_block(
            frame,
            ["VOCÊ CUIDA DA SUA MOTO..."],
            alpha=alpha,
            y_start=1600,
            size=44,
            font_path=FONT_BODY,
        )

    elif t < 6.0:
        local = (t - 3.0) / 3.0
        # quick cuts feel via pan changes
        if local < 0.33:
            u = local / 0.33
            frame = sample_ken(bases["s2"], u, zoom_from=1.05, zoom_to=1.18, pan_x=-0.4, pan_y=0.2)
        elif local < 0.66:
            u = (local - 0.33) / 0.33
            frame = sample_ken(bases["s2"], u, zoom_from=1.12, zoom_to=1.05, pan_x=0.35, pan_y=-0.25)
        else:
            u = (local - 0.66) / 0.34
            frame = sample_ken(bases["s2"], u, zoom_from=1.0, zoom_to=1.1, pan_y=0.3)
        frame = add_particles(frame, seed=1000 + i, density=30)
        alpha = fade_alpha(local, 0.2, 0.88)
        frame = overlay_text_block(
            frame,
            ["...DO SEU EQUIPAMENTO..."],
            alpha=alpha,
            y_start=1600,
            size=42,
            font_path=FONT_BODY,
        )

    elif t < 9.0:
        local = (t - 6.0) / 3.0
        frame = sample_ken(
            bases["s3"], local, zoom_from=1.0, zoom_to=1.2, pan_y=0.1, ease="ease_in"
        )
        # intensify particles as "microscopic dirt"
        dens = int(40 + local * 80)
        frame = add_particles(frame, seed=2000 + i, density=dens)
        # slight darken for tension
        frame = ImageEnhance.Brightness(frame).enhance(0.92 - 0.08 * local)
        alpha = fade_alpha(local, 0.15, 0.92)
        frame = overlay_text_block(
            frame,
            ["E DO QUE", "CUIDA DE VOCÊ?"],
            alpha=alpha,
            y_start=720,
            size=72,
            accent_word="VOCÊ?",
            font_path=FONT_DISPLAY,
            letter_space=14,
        )

    elif t < 12.0:
        local = (t - 9.0) / 3.0
        # impact flash at start
        dirty = sample_ken(bases["s3"], 1.0, zoom_from=1.2, zoom_to=1.2)
        clean = sample_ken(bases["s4"], local, zoom_from=1.08, zoom_to=1.0, ease="ease_out")
        shine = sample_ken(bases["s4b"], local, zoom_from=1.05, zoom_to=1.12, pan_x=0.2)
        if local < 0.12:
            # white flash transition
            frame = crossfade(dirty, clean, local / 0.12)
            frame = flash_white(frame, 1.0 - abs(local - 0.06) / 0.06)
        elif local < 0.55:
            u = (local - 0.12) / 0.43
            frame = crossfade(clean, shine, u * 0.35)
            frame = light_sweep(frame, u)
        else:
            u = (local - 0.55) / 0.45
            frame = sample_ken(bases["s4"], u, zoom_from=1.0, zoom_to=1.06)
            frame = light_sweep(frame, 0.3 + u * 0.4)
        frame = add_particles(frame, seed=3000 + i, density=70, bright=True)
        alpha = fade_alpha(local, 0.18, 0.9)
        frame = overlay_text_block(
            frame,
            ["SEU CAPACETE TAMBÉM", "MERECE CUIDADO."],
            alpha=alpha,
            y_start=1520,
            size=46,
            font_path=FONT_BODY,
            letter_space=10,
        )

    else:
        local = (t - 12.0) / 3.0
        frame = sample_ken(
            bases["s5"], local, zoom_from=1.06, zoom_to=1.0, pan_y=-0.05, ease="ease_out"
        )
        # subtle grade
        frame = ImageEnhance.Contrast(frame).enhance(1.05)
        logo_a = fade_alpha(local, 0.25, 1.0)
        frame = paste_logo(frame, logo_a, y=1180)
        # brand texts
        text_a = fade_alpha(max(0, (local - 0.15) / 0.85), 0.2, 1.0)
        overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        # dark lower gradient
        for yy in range(1100, H):
            a = int(160 * ((yy - 1100) / (H - 1100)) * text_a)
            draw.line([(0, yy), (W, yy)], fill=(0, 0, 0, a))

        f_title = font(FONT_BEBAS, 96)
        f_sub = font(FONT_MED, 34)
        f_tag = font(FONT_BODY, 28)
        # ZAPCLIN wordmark (in case logo is icon-heavy)
        draw_centered_text(
            draw,
            "ZAPCLIN",
            1380,
            f_title,
            fill=(255, 255, 255, int(255 * text_a)),
            stroke=1,
            stroke_fill=(0, 0, 0, int(100 * text_a)),
        )
        draw_centered_text(
            draw,
            "Higienização de Capacetes",
            1490,
            f_sub,
            fill=(220, 220, 220, int(240 * text_a)),
        )
        # red accent line
        if text_a > 0.2:
            draw.rectangle(
                (W // 2 - 60, 1555, W // 2 + 60, 1559),
                fill=(220, 30, 40, int(230 * text_a)),
            )
        tag_a = fade_alpha(max(0, (local - 0.4) / 0.6), 0.25, 1.0)
        draw_centered_text(
            draw,
            "MAIS QUE LIMPEZA. É CUIDADO.",
            1600,
            f_tag,
            fill=(255, 255, 255, int(255 * tag_a)),
            stroke=1,
            stroke_fill=(0, 0, 0, int(120 * tag_a)),
        )
        out = frame.convert("RGBA")
        out = Image.alpha_composite(out, overlay)
        frame = out.convert("RGB")
        frame = add_particles(frame, seed=4000 + i, density=25)

    # film grain
    arr = np.asarray(frame).astype(np.float32)
    rng = np.random.default_rng(i * 17 + 3)
    grain = rng.normal(0, 4.5, arr.shape).astype(np.float32)
    arr = np.clip(arr + grain, 0, 255).astype(np.uint8)
    frame = Image.fromarray(arr, "RGB")

    # letterbox-safe soft vignette
    vig = Image.new("RGB", (W, H), (0, 0, 0))
    mask = Image.new("L", (W, H), 0)
    md = ImageDraw.Draw(mask)
    md.ellipse((-120, -80, W + 120, H + 80), fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(80))
    frame = Image.composite(frame, Image.blend(frame, vig, 0.35), mask)

    return frame


def synthesize_audio(path: Path) -> None:
    """Cinematic-ish bed: rising drone, silence tension, impact, resolve."""
    sr = 44100
    n = int(sr * DURATION)
    t = np.linspace(0, DURATION, n, endpoint=False)
    audio = np.zeros(n, dtype=np.float64)

    def env(start, attack, hold, release, total=DURATION):
        e = np.zeros_like(t)
        for i, ti in enumerate(t):
            if ti < start:
                e[i] = 0
            elif ti < start + attack:
                e[i] = (ti - start) / attack
            elif ti < start + attack + hold:
                e[i] = 1.0
            elif ti < start + attack + hold + release:
                e[i] = 1.0 - (ti - start - attack - hold) / release
            else:
                e[i] = 0
        return e

    # low drone 0-6s growing
    drone = 0.22 * np.sin(2 * np.pi * 55 * t)
    drone += 0.12 * np.sin(2 * np.pi * 82.5 * t)
    drone += 0.05 * np.sin(2 * np.pi * 110 * t + 0.3)
    audio += drone * env(0, 0.8, 4.5, 0.7) * (0.4 + 0.6 * np.clip(t / 6, 0, 1))

    # mid pulse / heartbeat-ish 0-6
    pulse = 0.08 * np.sin(2 * np.pi * 2.2 * t) * np.sin(2 * np.pi * 110 * t)
    audio += pulse * env(0.5, 0.5, 4.5, 0.5)

    # sudden drop / near silence 6-8.7 with sparse high ticks
    tension = 0.04 * np.sin(2 * np.pi * 220 * t) * np.sin(2 * np.pi * 0.7 * t)
    audio += tension * env(6.0, 0.2, 2.4, 0.3)

    # impact at 9.0s
    impact_t = t - 9.0
    impact = np.zeros_like(t)
    mask = impact_t >= 0
    impact[mask] = np.exp(-impact_t[mask] * 8) * (
        0.9 * np.sin(2 * np.pi * 60 * impact_t[mask])
        + 0.5 * np.sin(2 * np.pi * 90 * impact_t[mask])
        + 0.25 * np.sin(2 * np.pi * 40 * impact_t[mask])
    )
    # noise burst
    rng = np.random.default_rng(42)
    noise = rng.normal(0, 1, n)
    noise_env = np.zeros_like(t)
    noise_env[mask] = np.exp(-impact_t[mask] * 14) * 0.35
    audio += impact + noise * noise_env

    # resolve pad 9-15
    pad = 0.14 * np.sin(2 * np.pi * 130.8 * t)  # C3-ish
    pad += 0.10 * np.sin(2 * np.pi * 164.8 * t)
    pad += 0.08 * np.sin(2 * np.pi * 196.0 * t)
    pad += 0.05 * np.sin(2 * np.pi * 261.6 * t)
    audio += pad * env(9.05, 0.6, 4.5, 0.8)

    # soft shimmer 10-15
    shimmer = 0.03 * np.sin(2 * np.pi * 523.25 * t + 2 * np.sin(2 * np.pi * 0.5 * t))
    audio += shimmer * env(10.0, 0.8, 3.5, 0.7)

    # normalize
    peak = np.max(np.abs(audio)) + 1e-9
    audio = 0.85 * audio / peak
    # soft clip
    audio = np.tanh(audio * 1.1)

    # write wav via raw + ffmpeg
    raw = (audio * 32767).astype(np.int16)
    raw_path = path.with_suffix(".raw")
    raw.tofile(raw_path)
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "s16le",
            "-ar",
            str(sr),
            "-ac",
            "1",
            "-i",
            str(raw_path),
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            str(path),
        ],
        check=True,
        capture_output=True,
    )
    raw_path.unlink(missing_ok=True)


def encode_video(audio_path: Path, out_path: Path) -> None:
    # ffmpeg from image sequence
    pattern = str(FRAMES / "frame_%04d.png")
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-framerate",
            str(FPS),
            "-i",
            pattern,
            "-i",
            str(audio_path),
            "-c:v",
            "libx264",
            "-preset",
            "slow",
            "-crf",
            "16",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-shortest",
            "-movflags",
            "+faststart",
            "-r",
            str(FPS),
            str(out_path),
        ],
        check=True,
        capture_output=True,
    )


def main() -> None:
    ensure_dirs()
    print("Loading bases...")
    bases = {k: load_base(v) for k, v in SCENES.items()}
    print(f"Rendering {TOTAL} frames @ {FPS}fps ({W}x{H})...")
    for i in range(TOTAL):
        frame = render_frame(i, bases)
        frame.save(FRAMES / f"frame_{i:04d}.png", optimize=False)
        if i % 30 == 0:
            print(f"  {i}/{TOTAL} ({i/FPS:.1f}s)")
    print("Synthesizing audio...")
    audio_path = OUT_DIR / "score.m4a"
    synthesize_audio(audio_path)
    print("Encoding video...")
    out_path = OUT_DIR / "zapclin_comercial_15s_9x16.mp4"
    encode_video(audio_path, out_path)
    # also copy to artifacts
    art = Path("/opt/cursor/artifacts/zapclin_comercial_15s_9x16.mp4")
    subprocess.run(["cp", str(out_path), str(art)], check=True)
    print("Done:", out_path)
    print("Artifact:", art)
    subprocess.run(
        ["ffprobe", "-hide_banner", str(out_path)],
        check=False,
    )


if __name__ == "__main__":
    main()

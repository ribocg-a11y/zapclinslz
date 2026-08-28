#!/usr/bin/env python3
"""Gera vídeo vertical 9:16 da ZapClin para redes sociais."""

from __future__ import annotations

import asyncio
import math
import subprocess
import textwrap
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "social-media"
ASSETS = ROOT / "assets"
FONTS = OUT_DIR

W, H = 1080, 1920
FPS = 30

BG = (7, 11, 26)
CYAN = (92, 255, 215)
CYAN_DEEP = (0, 200, 224)
TEXT = (244, 247, 255)
MUTED = (154, 163, 191)
GREEN = (143, 209, 79)
GOLD = (240, 193, 75)


@dataclass
class Scene:
    duration: float
    narration: str
    headline: str
    subline: str = ""
    image: str | None = None
    image2: str | None = None
    style: str = "default"


SCENES: list[Scene] = [
    Scene(
        3.2,
        "Quer um jeito mais rápido de manter seu capacete sempre fresco?",
        "CAPACETE SEMPRE FRESCO?",
        style="hook",
    ),
    Scene(
        5.0,
        "Sabia que uma higienização rápida pode prolongar a vida útil do seu capacete? Veja como!",
        "PROLONGUE A VIDA",
        "DO SEU CAPACETE",
        image="logo-oficial-transp.png",
        style="fact",
    ),
    Scene(
        6.0,
        "Suor, poeira e umidade acumulam germes e fungos no forro — e isso encurta a durabilidade do equipamento.",
        "O PROBLEMA",
        "Germes · Odor · Desgaste",
        image="antes-forro.jpg",
        style="problem",
    ),
    Scene(
        8.0,
        "Na ZapClin, a higienização profissional elimina odores e microrganismos em ciclos de oito a doze minutos.",
        "A SOLUÇÃO ZAPCLIN",
        "8–12 min · Higienização profissional",
        image="hero-loja.jpg",
        style="solution",
    ),
    Scene(
        8.0,
        "Resultado: forro limpo, cheiro agradável e capacete pronto para a próxima viagem.",
        "ANTES → DEPOIS",
        "Forro limpo e sem odor",
        image="antes-forro.jpg",
        image2="depois-forro.jpg",
        style="compare",
    ),
    Scene(
        8.0,
        "A partir de quinze reais no Golden Shopping Calhau. Deixa o capacete e segue sua rotina!",
        "ZAPCLIN",
        "Golden Shopping Calhau · Quiosque 01\nWhatsApp (98) 98147-9616 · A partir de R$ 15",
        image="loja-balcao.jpg",
        style="cta",
    ),
]


def load_font(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONTS / name), size)


def gradient_bg() -> Image.Image:
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    for y in range(H):
        t = y / H
        r = int(BG[0] + (15 - BG[0]) * t * 0.4)
        g = int(BG[1] + (23 - BG[1]) * t * 0.4)
        b = int(BG[2] + (48 - BG[2]) * t * 0.4)
        draw.line([(0, y), (W, y)], fill=(r, g, b))

    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gdraw = ImageDraw.Draw(glow)
    gdraw.ellipse([W // 2 - 500, -200, W // 2 + 500, 500], fill=(0, 200, 224, 45))
    gdraw.ellipse([W - 300, 200, W + 200, 700], fill=(92, 255, 215, 25))
    img = Image.alpha_composite(img.convert("RGBA"), glow).convert("RGB")
    return img


def draw_grid(img: Image.Image) -> Image.Image:
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    step = 72
    for x in range(0, W, step):
        draw.line([(x, 0), (x, H)], fill=(255, 255, 255, 8))
    for y in range(0, H, step):
        draw.line([(0, y), (W, y)], fill=(255, 255, 255, 8))
    return Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")


def fit_image(path: Path, box: tuple[int, int, int, int], radius: int = 28) -> Image.Image:
    x0, y0, x1, y1 = box
    bw, bh = x1 - x0, y1 - y0
    src = Image.open(path).convert("RGB")
    fitted = ImageOps.fit(src, (bw, bh), method=Image.Resampling.LANCZOS)

    mask = Image.new("L", (bw, bh), 0)
    mdraw = ImageDraw.Draw(mask)
    mdraw.rounded_rectangle([0, 0, bw, bh], radius=radius, fill=255)
    fitted.putalpha(mask)

    border = Image.new("RGBA", (bw + 6, bh + 6), (0, 0, 0, 0))
    bdraw = ImageDraw.Draw(border)
    bdraw.rounded_rectangle([0, 0, bw + 5, bh + 5], radius=radius + 2, outline=(*CYAN, 120), width=3)
    border.paste(fitted, (3, 3), fitted)
    return border


def wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        test = f"{current} {word}".strip()
        if font.getlength(test) <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [text]


def draw_centered_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    y: int,
    font: ImageFont.FreeTypeFont,
    fill: tuple[int, ...],
    max_width: int = 920,
    line_gap: int = 12,
) -> int:
    lines = wrap_text(text, font, max_width) if "\n" not in text else text.split("\n")
    total_h = len(lines) * (font.size + line_gap) - line_gap
    cy = y
    for line in lines:
        lw = font.getlength(line)
        draw.text(((W - lw) / 2, cy), line, font=font, fill=fill)
        cy += font.size + line_gap
    return y + total_h


def render_frame(scene: Scene, progress: float, frame_idx: int) -> Image.Image:
    img = draw_grid(gradient_bg())
    draw = ImageDraw.Draw(img)

    pulse = 0.5 + 0.5 * math.sin(frame_idx * 0.12)
    accent = tuple(int(c * (0.85 + 0.15 * pulse)) for c in CYAN)

    # Logo top
    logo_path = ASSETS / "logo-nav.png"
    if logo_path.exists():
        logo = Image.open(logo_path).convert("RGBA")
        lw = 280
        lh = int(logo.height * lw / logo.width)
        logo = logo.resize((lw, lh), Image.Resampling.LANCZOS)
        img.paste(logo, ((W - lw) // 2, 70), logo)

    title_font = load_font("Oxanium-Bold.ttf", 62)
    sub_font = load_font("Manrope-SemiBold.ttf", 34)
    body_font = load_font("Manrope-Regular.ttf", 30)
    badge_font = load_font("Manrope-Bold.ttf", 28)

    y_head = 260

    if scene.style == "hook":
        draw.rounded_rectangle([60, y_head - 20, W - 60, y_head + 200], radius=24, outline=accent, width=3)
        draw_centered_text(draw, scene.headline, y_head + 20, title_font, TEXT)
        icon = ASSETS / "helmet-icon.svg"
        # draw emoji-style helmet area
        draw.ellipse([W // 2 - 120, 620, W // 2 + 120, 860], outline=(*CYAN, int(180 * pulse)), width=4)
        draw.text((W // 2 - 40, 700), "🪖", font=load_font("Manrope-Regular.ttf", 90), fill=TEXT, embedded_color=True)
        draw_centered_text(draw, "Odores · Suor · Bacterias", 980, sub_font, MUTED)

    elif scene.style == "fact":
        draw_centered_text(draw, scene.headline, y_head, title_font, CYAN)
        draw_centered_text(draw, scene.subline, y_head + 90, title_font, TEXT)
        if scene.image:
            pic = fit_image(ASSETS / scene.image, (140, 520, W - 140, 1180))
            img.paste(pic, (140 - 3, 520 - 3), pic)
        draw.rounded_rectangle([120, 1260, W - 120, 1340], radius=18, fill=(15, 23, 48))
        draw_centered_text(draw, "Higienização = mais vida útil", 1280, badge_font, GREEN)

    elif scene.style == "problem":
        draw_centered_text(draw, scene.headline, y_head, title_font, (255, 93, 108))
        draw_centered_text(draw, scene.subline, y_head + 80, sub_font, MUTED)
        if scene.image:
            pic = fit_image(ASSETS / scene.image, (80, 480, W - 80, 1180), radius=32)
            img.paste(pic, (77, 477), pic)
        draw.rounded_rectangle([100, 1240, W - 100, 1380], radius=20, fill=(40, 12, 18))
        draw_centered_text(draw, "⚠️  Forro comprometido = desgaste acelerado", 1275, body_font, (255, 180, 180))

    elif scene.style == "solution":
        draw_centered_text(draw, scene.headline, y_head, title_font, CYAN)
        draw_centered_text(draw, scene.subline, y_head + 80, sub_font, TEXT)
        if scene.image:
            pic = fit_image(ASSETS / scene.image, (80, 480, W - 80, 1080))
            img.paste(pic, (77, 477), pic)
        # timer badge
        draw.rounded_rectangle([200, 1120, W - 200, 1280], radius=24, fill=(15, 23, 48), outline=CYAN, width=2)
        draw_centered_text(draw, "⏱  8 min", 1165, load_font("Oxanium-Bold.ttf", 72), CYAN)
        draw_centered_text(draw, "Higienização rápida · Essencial · Profunda", 1310, body_font, MUTED)

    elif scene.style == "compare":
        draw_centered_text(draw, scene.headline, y_head, title_font, GREEN)
        draw_centered_text(draw, scene.subline, y_head + 80, sub_font, TEXT)
        if scene.image and scene.image2:
            h = 520
            pic1 = fit_image(ASSETS / scene.image, (60, 480, W // 2 - 20, 480 + h))
            pic2 = fit_image(ASSETS / scene.image2, (W // 2 + 20, 480, W - 60, 480 + h))
            img.paste(pic1, (57, 477), pic1)
            img.paste(pic2, (W // 2 + 17, 477), pic2)
            draw.text((W // 4 - 30, 1020), "ANTES", font=badge_font, fill=MUTED)
            draw.text((3 * W // 4 - 40, 1020), "DEPOIS", font=badge_font, fill=GREEN)
            draw.text((W // 2 - 20, 700), "→", font=load_font("Oxanium-Bold.ttf", 80), fill=CYAN)
        draw_centered_text(draw, "Cheiro agradável · Forro preservado", 1120, body_font, TEXT)

    elif scene.style == "cta":
        draw_centered_text(draw, scene.headline, y_head, load_font("Oxanium-Bold.ttf", 78), CYAN)
        if scene.image:
            pic = fit_image(ASSETS / scene.image, (80, 420, W - 80, 900))
            img.paste(pic, (77, 417), pic)
        draw.rounded_rectangle([70, 940, W - 70, 1220], radius=28, fill=(15, 23, 48), outline=GOLD, width=2)
        draw_centered_text(draw, scene.subline.split("\n")[0], 980, sub_font, TEXT)
        draw_centered_text(draw, scene.subline.split("\n")[1] if "\n" in scene.subline else "", 1050, body_font, MUTED)
        draw.rounded_rectangle([180, 1280, W - 180, 1380], radius=40, fill=CYAN_DEEP)
        draw_centered_text(draw, "A PARTIR DE R$ 15", 1310, load_font("Oxanium-Bold.ttf", 42), BG)
        draw_centered_text(draw, "zapclinslz.com  ·  @zapclinhigienizacao", 1440, body_font, MUTED)

    # Progress bar
    bar_w = int((W - 160) * progress)
    draw.rounded_rectangle([80, H - 80, W - 80, H - 56], radius=12, fill=(15, 23, 48))
    if bar_w > 0:
        draw.rounded_rectangle([80, H - 80, 80 + bar_w, H - 56], radius=12, fill=CYAN)

    # Hashtag strip (subtle)
    if scene.style == "cta":
        tags = "#helmetcleaning  #motorcyclehacks  #helmetfresh"
        draw_centered_text(draw, tags, H - 160, load_font("Manrope-Regular.ttf", 22), (*MUTED,))

    return img


async def synthesize_narration() -> Path:
    import edge_tts

    voice = "pt-BR-FranciscaNeural"
    text = " ".join(s.narration for s in SCENES)
    out = OUT_DIR / "narracao.mp3"
    communicate = edge_tts.Communicate(text, voice, rate="+5%")
    await communicate.save(str(out))
    return out


def get_audio_duration(path: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return float(result.stdout.strip())


def build_video(audio_path: Path) -> Path:
    audio_dur = get_audio_duration(audio_path)
    planned = sum(s.duration for s in SCENES)
    scale = audio_dur / planned
    scene_durations = [s.duration * scale for s in SCENES]
    total_frames = int(math.ceil(audio_dur * FPS))

    frames_dir = OUT_DIR / "frames"
    frames_dir.mkdir(exist_ok=True)
    for old in frames_dir.glob("*.png"):
        old.unlink()

    frame_paths: list[Path] = []
    global_progress = 0.0
    frame_idx = 0

    for scene, dur in zip(SCENES, scene_durations):
        scene_frames = max(1, int(dur * FPS))
        for i in range(scene_frames):
            progress = (frame_idx + 1) / total_frames
            scene_progress = i / scene_frames
            img = render_frame(scene, scene_progress, frame_idx)
            path = frames_dir / f"frame_{frame_idx:05d}.png"
            img.save(path, optimize=True)
            frame_paths.append(path)
            frame_idx += 1

    # Pad or trim to match audio
    while len(frame_paths) < total_frames:
        frame_paths.append(frame_paths[-1])
    frame_paths = frame_paths[:total_frames]

    silent_video = OUT_DIR / "video_silent.mp4"
    final_video = OUT_DIR / "zapclin-capacete-fresco-9x16.mp4"
    artifacts_video = Path("/opt/cursor/artifacts/zapclin-capacete-fresco-9x16.mp4")

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-framerate",
            str(FPS),
            "-i",
            str(frames_dir / "frame_%05d.png"),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-crf",
            "20",
            str(silent_video),
        ],
        check=True,
        capture_output=True,
    )

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(silent_video),
            "-i",
            str(audio_path),
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-shortest",
            str(final_video),
        ],
        check=True,
        capture_output=True,
    )

    artifacts_video.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["cp", str(final_video), str(artifacts_video)], check=True)
    return final_video


def main() -> None:
    print("Gerando narração PT-BR...")
    audio = asyncio.run(synthesize_narration())
    print(f"Áudio: {audio} ({get_audio_duration(audio):.1f}s)")
    print("Renderizando vídeo 9:16...")
    video = build_video(audio)
    print(f"Vídeo pronto: {video}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Generate a 30s Instagram Reel (9:16) for ZapClin from flyer + caption copy."""

from __future__ import annotations

import math
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

# --- Config ---
W, H = 1080, 1920
FPS = 30
DURATION = 30.0
TOTAL_FRAMES = int(FPS * DURATION)

CYAN = (0, 173, 239)  # #00ADEF
WHITE = (255, 255, 255)
NEAR_WHITE = (240, 248, 255)
BLACK = (0, 0, 0)
DARK = (10, 12, 16)

ROOT = Path("/workspace")
FLYER = ROOT / "assets/reels/zapclin_flyer_source.jpg"
if not FLYER.exists():
    FLYER = Path(
        "/home/ubuntu/.cursor/projects/workspace/assets/01a03e68-2baa-7364-8a5b-3eaa66f1d618.jpg"
    )
OUT_DIR = Path("/tmp/zapclin-reel/frames")
VIDEO_OUT = ROOT / "assets/reels/zapclin_instagram_reel_30s.mp4"

FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(FONT_BOLD if bold else FONT_REG, size)


def ease_out_cubic(t: str | float) -> float:
    t = float(t)
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def ease_in_out(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return 3 * t * t - 2 * t * t * t


def clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def scene_opacity(t: float, start: float, end: float, fade: float = 0.45) -> float:
    """Opacity for a scene active between start..end with fade in/out.

    Fade-out finishes exactly at `end`; fade-in begins exactly at `start`.
    Callers must leave a gap between one scene's end and the next start.
    """
    if fade <= 0:
        return 1.0 if start <= t <= end else 0.0
    if t < start or t > end:
        return 0.0
    # fade in on [start, start+fade]
    if t < start + fade:
        return ease_out_cubic((t - start) / fade)
    # fade out on [end-fade, end]
    if t > end - fade:
        return ease_out_cubic((end - t) / fade)
    return 1.0


def text_size(draw: ImageDraw.ImageDraw, text: str, fnt: ImageFont.FreeTypeFont) -> tuple[int, int]:
    bbox = draw.textbbox((0, 0), text, font=fnt)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def wrap_text(draw: ImageDraw.ImageDraw, text: str, fnt: ImageFont.FreeTypeFont, max_w: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    cur = ""
    for w in words:
        test = f"{cur} {w}".strip()
        tw, _ = text_size(draw, test, fnt)
        if tw <= max_w:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def draw_centered_lines(
    base: Image.Image,
    lines: list[tuple[str, tuple[int, int, int], ImageFont.FreeTypeFont]],
    cy: int,
    opacity: float,
    line_gap: int = 12,
    shadow: bool = True,
) -> None:
    if opacity <= 0.01:
        return
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    heights = []
    widths = []
    for text, _color, fnt in lines:
        tw, th = text_size(draw, text, fnt)
        widths.append(tw)
        heights.append(th)
    total_h = sum(heights) + line_gap * (len(lines) - 1)
    y = cy - total_h // 2
    for i, (text, color, fnt) in enumerate(lines):
        tw, th = widths[i], heights[i]
        x = (W - tw) // 2
        if shadow:
            draw.text((x + 3, y + 4), text, font=fnt, fill=(0, 0, 0, int(180 * opacity)))
        draw.text((x, y), text, font=fnt, fill=(*color, int(255 * opacity)))
        y += th + line_gap
    base.alpha_composite(overlay)


def draw_left_block(
    base: Image.Image,
    items: list[tuple[str, tuple[int, int, int], ImageFont.FreeTypeFont]],
    x: int,
    y: int,
    opacity: float,
    max_w: int | None = None,
    line_gap: int = 10,
) -> int:
    if opacity <= 0.01:
        return y
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    cy = y
    for text, color, fnt in items:
        lines = [text] if max_w is None else wrap_text(draw, text, fnt, max_w)
        for line in lines:
            draw.text((x + 2, cy + 3), line, font=fnt, fill=(0, 0, 0, int(160 * opacity)))
            draw.text((x, cy), line, font=fnt, fill=(*color, int(255 * opacity)))
            _, th = text_size(draw, line, fnt)
            cy += th + 4
        cy += line_gap
    base.alpha_composite(overlay)
    return cy


def draw_pill(
    base: Image.Image,
    text: str,
    cx: int,
    cy: int,
    opacity: float,
    fill: tuple[int, int, int] = CYAN,
    text_color: tuple[int, int, int] = WHITE,
    pad_x: int = 42,
    pad_y: int = 22,
    fnt: ImageFont.FreeTypeFont | None = None,
) -> None:
    if opacity <= 0.01:
        return
    fnt = fnt or font(36, True)
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    tw, th = text_size(draw, text, fnt)
    w = tw + pad_x * 2
    h = th + pad_y * 2
    x0 = cx - w // 2
    y0 = cy - h // 2
    # soft glow
    glow = Image.new("RGBA", base.size, (0, 0, 0, 0))
    gdraw = ImageDraw.Draw(glow)
    gdraw.rounded_rectangle(
        [x0 - 8, y0 - 8, x0 + w + 8, y0 + h + 8],
        radius=18,
        fill=(*fill, int(70 * opacity)),
    )
    glow = glow.filter(ImageFilter.GaussianBlur(12))
    base.alpha_composite(glow)
    draw.rounded_rectangle([x0, y0, x0 + w, y0 + h], radius=14, fill=(*fill, int(240 * opacity)))
    draw.text((x0 + pad_x, y0 + pad_y - 2), text, font=fnt, fill=(*text_color, int(255 * opacity)))
    base.alpha_composite(overlay)


def draw_corners(base: Image.Image, x0: int, y0: int, x1: int, y1: int, opacity: float, size: int = 28) -> None:
    if opacity <= 0.01:
        return
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    a = int(255 * opacity)
    lw = 4
    # TL
    draw.line([(x0, y0 + size), (x0, y0), (x0 + size, y0)], fill=(*CYAN, a), width=lw)
    # TR
    draw.line([(x1 - size, y0), (x1, y0), (x1, y0 + size)], fill=(*CYAN, a), width=lw)
    # BL
    draw.line([(x0, y1 - size), (x0, y1), (x0 + size, y1)], fill=(*CYAN, a), width=lw)
    # BR
    draw.line([(x1 - size, y1), (x1, y1), (x1, y1 - size)], fill=(*CYAN, a), width=lw)
    base.alpha_composite(overlay)


def prepare_flyer() -> Image.Image:
    """Build an oversized clean plate: dark branded canvas + helmet crop (no flyer copy)."""
    src = Image.open(FLYER).convert("RGB")
    sw, sh = src.size
    # Helmet lives on the right/lower half of the flyer — crop tightly to product
    # Avoid left copy column and bottom impact line as much as possible
    helmet = src.crop((int(sw * 0.45), int(sh * 0.32), int(sw * 0.99), int(sh * 0.78)))
    # Paint out any residual bottom typography still in the crop
    hw0, hh0 = helmet.size
    cover = Image.new("RGBA", helmet.size, (0, 0, 0, 0))
    cd = ImageDraw.Draw(cover)
    for i in range(int(hh0 * 0.32)):
        a = int(255 * (i / (hh0 * 0.32)) ** 0.55)
        y = hh0 - 1 - i
        cd.line([(0, y), (hw0, y)], fill=(8, 10, 14, a))
    # Soft left edge fade (may include partial icons/copy)
    for i in range(int(hw0 * 0.18)):
        a = int(200 * (1 - i / (hw0 * 0.18)))
        cd.line([(i, 0), (i, hh0)], fill=(8, 10, 14, a))
    helmet = Image.alpha_composite(helmet.convert("RGBA"), cover).convert("RGB")
    # Dark cinematic canvas larger than 1080x1920 for Ken Burns
    canvas_w, canvas_h = int(W * 1.35), int(H * 1.28)
    canvas = Image.new("RGB", (canvas_w, canvas_h), DARK)
    # Radial-ish cyan/black gradient
    grad = Image.new("RGB", (canvas_w, canvas_h), DARK)
    gd = ImageDraw.Draw(grad)
    for i in range(canvas_h):
        # top darker, mid slightly cyan-tinted
        t = i / canvas_h
        r = int(8 + 6 * t)
        g = int(10 + 28 * (1 - abs(t - 0.45) * 1.5))
        b = int(14 + 42 * (1 - abs(t - 0.4) * 1.4))
        gd.line([(0, i), (canvas_w, i)], fill=(max(0, r), max(0, min(40, g)), max(0, min(55, b))))
    canvas = Image.blend(canvas, grad, 0.85)

    # Scale helmet to dominate right side
    target_h = int(canvas_h * 0.92)
    ratio = target_h / helmet.height
    hw, hh = int(helmet.width * ratio), target_h
    helmet = helmet.resize((hw, hh), Image.Resampling.LANCZOS)
    # Soft edge mask so helmet blends into dark plate
    mask = Image.new("L", helmet.size, 0)
    md = ImageDraw.Draw(mask)
    md.ellipse(
        [-int(hw * 0.05), int(hh * 0.02), int(hw * 1.05), int(hh * 1.05)],
        fill=255,
    )
    mask = mask.filter(ImageFilter.GaussianBlur(48))
    paste_x = canvas_w - hw + int(hw * 0.08)
    paste_y = int(canvas_h * 0.08)
    canvas.paste(helmet, (paste_x, paste_y), mask)
    # Soft vignette
    vig = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    vd = ImageDraw.Draw(vig)
    for r in range(0, 220, 2):
        a = int(100 * (r / 220) ** 1.5)
        vd.rectangle([r, r, canvas_w - r, canvas_h - r], outline=(0, 0, 0, a))
    canvas = Image.alpha_composite(canvas.convert("RGBA"), vig).convert("RGB")
    return canvas


def ken_burns_crop(flyer: Image.Image, t: float) -> Image.Image:
    """Slow zoom + slight pan across 30s toward the helmet."""
    progress = ease_in_out(t / DURATION)
    zoom = 1.0 + 0.16 * progress
    cw = int(W / zoom)
    ch = int(H / zoom)
    max_x = max(0, flyer.width - cw)
    max_y = max(0, flyer.height - ch)
    x = int(max_x * (0.35 + 0.55 * progress))
    y = int(max_y * (0.15 + 0.40 * progress))
    return flyer.crop((x, y, x + cw, y + ch)).resize((W, H), Image.Resampling.LANCZOS)


def cinematic_bg(img: Image.Image, blur_radius: float = 1.2, dark: float = 0.28) -> Image.Image:
    """Light polish — plate is already clean (no flyer typography)."""
    out = img.convert("RGBA")
    if blur_radius > 0.4:
        out = out.filter(ImageFilter.GaussianBlur(radius=blur_radius))
    if dark > 0.01:
        veil = Image.new("RGBA", out.size, (0, 0, 0, int(255 * dark)))
        out = Image.alpha_composite(out, veil)
    tint = Image.new("RGBA", out.size, (0, 30, 48, 28))
    out = Image.alpha_composite(out, tint)
    return out


def render_frame(flyer: Image.Image, frame_i: int) -> Image.Image:
    t = frame_i / FPS

    bg = ken_burns_crop(flyer, t)
    blur = 0.8 + 0.4 * scene_opacity(t, 0.0, 5.0, 1.0)
    dark = 0.22 + 0.18 * scene_opacity(t, 20.0, 30.0, 0.6)
    frame = cinematic_bg(bg, blur_radius=blur, dark=dark)

    # Soft top/bottom gradient for text
    grad = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gdraw = ImageDraw.Draw(grad)
    for i in range(420):
        a = int(170 * (1 - i / 420))
        gdraw.line([(0, i), (W, i)], fill=(0, 0, 0, a))
    for i in range(500):
        a = int(190 * (1 - i / 500))
        y = H - 1 - i
        gdraw.line([(0, y), (W, y)], fill=(0, 0, 0, a))
    frame.alpha_composite(grad)

    # --- LOGO always subtle ---
    logo_op = 0.85 if t > 0.3 else ease_out_cubic(t / 0.3) * 0.85
    draw_left_block(
        frame,
        [
            ("ZapClin", CYAN, font(34, True)),
            ("Higienização de Capacetes", NEAR_WHITE, font(18, False)),
        ],
        x=48,
        y=48,
        opacity=logo_op,
        line_gap=2,
    )

    # Exclusive windows (gap between scenes — no crossfade overlap):
    # 0.4–3.5 hook | 3.9–8.2 completa | 8.6–13.9 benefícios
    # 14.3–19.1 impact | 19.5–23.6 oferta | 24.2–30.0 CTA

    # --- SCENE 1: Hook ---
    op1 = scene_opacity(t, 0.4, 3.5, 0.3)
    if op1 > 0:
        slide = int((1 - ease_out_cubic(min(1, max(0, (t - 0.4) / 0.3)))) * 40)
        draw_centered_lines(
            frame,
            [
                ("CAPACETE FEDENDO?", WHITE, font(58, True)),
                ("Em São Luís resolve em 8 minutos.", CYAN, font(30, True)),
            ],
            cy=420 + slide,
            opacity=op1,
            line_gap=18,
        )

    # --- SCENE 2: Higienização completa ---
    op2 = scene_opacity(t, 3.9, 8.2, 0.3)
    if op2 > 0:
        slide = int((1 - ease_out_cubic(min(1, max(0, (t - 3.9) / 0.3)))) * 36)
        draw_centered_lines(
            frame,
            [
                ("HIGIENIZAÇÃO", WHITE, font(64, True)),
                ("COMPLETA", CYAN, font(72, True)),
                ("Seu capacete merece mais", NEAR_WHITE, font(28, False)),
                ("que uma simples limpeza.", NEAR_WHITE, font(28, False)),
            ],
            cy=460 + slide,
            opacity=op2,
            line_gap=10,
        )

    # --- SCENE 3: Benefícios ---
    op3 = scene_opacity(t, 8.6, 13.9, 0.3)
    if op3 > 0:
        benefits = [
            ("LIMPEZA", "Remove sujeiras, oleosidade e resíduos.", 8.9),
            ("HIGIENIZAÇÃO", "Elimina odores e impurezas.", 10.1),
            ("DESODORIZAÇÃO", "Frescor por muito mais tempo.", 11.3),
        ]
        y = 360
        draw_centered_lines(
            frame,
            [("PROCESSO COMPLETO", CYAN, font(26, True))],
            cy=300,
            opacity=op3,
        )
        for title, desc, start in benefits:
            local = scene_opacity(t, start, 13.9, 0.28) * op3
            if local <= 0.01:
                y += 150
                continue
            overlay = Image.new("RGBA", frame.size, (0, 0, 0, 0))
            d = ImageDraw.Draw(overlay)
            d.rectangle([70, y, 78, y + 100], fill=(*CYAN, int(230 * local)))
            d.text((100, y), title, font=font(36, True), fill=(*WHITE, int(255 * local)))
            for j, line in enumerate(wrap_text(d, desc, font(24, False), 860)):
                d.text((100, y + 48 + j * 30), line, font=font(24, False), fill=(*NEAR_WHITE, int(230 * local)))
            frame.alpha_composite(overlay)
            y += 150

    # --- SCENE 4: Impact ---
    op4 = scene_opacity(t, 14.3, 19.1, 0.3)
    if op4 > 0:
        draw_corners(frame, 90, 520, W - 90, 820, op4, size=36)
        draw_centered_lines(
            frame,
            [
                ("VOCÊ NÃO VÊ,", WHITE, font(48, True)),
                ("MAS ESTÁ LÁ.", CYAN, font(52, True)),
            ],
            cy=640,
            opacity=op4,
            line_gap=14,
        )
        draw_centered_lines(
            frame,
            [
                ("Você usa todos os dias.", NEAR_WHITE, font(26, False)),
                ("Quando foi a última vez que cuidou dele?", NEAR_WHITE, font(26, False)),
            ],
            cy=920,
            opacity=op4 * scene_opacity(t, 15.4, 19.1, 0.28),
            line_gap=8,
        )

    # --- SCENE 5: Offer ---
    op5 = scene_opacity(t, 19.5, 23.6, 0.3)
    if op5 > 0:
        draw_centered_lines(
            frame,
            [
                ("NÃO É SÓ MÁQUINA", WHITE, font(34, True)),
                ("É PROCESSO PROFISSIONAL", CYAN, font(34, True)),
            ],
            cy=380,
            opacity=op5,
            line_gap=10,
        )
        offers = [
            ("8 MIN", "Enquanto você", "fica no shopping", 19.9),
            ("A PARTIR", "de R$ 15", "higienização", 20.5),
            ("CALHAU", "Golden Shopping", "Quiosque 01", 21.1),
        ]
        xs = [180, 540, 900]
        for i, (a, b, c, start) in enumerate(offers):
            loc = scene_opacity(t, start, 23.6, 0.28) * op5
            if loc <= 0.01:
                continue
            overlay = Image.new("RGBA", frame.size, (0, 0, 0, 0))
            d = ImageDraw.Draw(overlay)
            cx = xs[i]
            for j, (txt, col, fnt) in enumerate(
                [
                    (a, CYAN, font(36, True)),
                    (b, WHITE, font(26, True)),
                    (c, NEAR_WHITE, font(20, False)),
                ]
            ):
                tw, _ = text_size(d, txt, fnt)
                d.text(
                    (cx - tw // 2 + 2, 620 + j * 42 + 3),
                    txt,
                    font=fnt,
                    fill=(0, 0, 0, int(160 * loc)),
                )
                d.text((cx - tw // 2, 620 + j * 42), txt, font=fnt, fill=(*col, int(255 * loc)))
            frame.alpha_composite(overlay)

        draw_centered_lines(
            frame,
            [
                ("Remove odor e germes.", NEAR_WHITE, font(28, False)),
                ("Capacete pronto na sua rotina.", NEAR_WHITE, font(28, False)),
            ],
            cy=920,
            opacity=op5 * scene_opacity(t, 21.5, 23.4, 0.28),
            line_gap=8,
        )

    # --- SCENE 6: CTA ---
    op6 = scene_opacity(t, 24.2, 30.0, 0.35)
    if op6 > 0:
        pulse = 0.92 + 0.08 * math.sin(t * 6.0)
        draw_centered_lines(
            frame,
            [
                ("AGENDE SUA", WHITE, font(44, True)),
                ("HIGIENIZAÇÃO", CYAN, font(56, True)),
            ],
            cy=520,
            opacity=op6,
            line_gap=8,
        )
        draw_pill(
            frame,
            "WHATSAPP  98 98147-9616",
            cx=W // 2,
            cy=720,
            opacity=op6 * pulse,
            fnt=font(30, True),
        )
        draw_centered_lines(
            frame,
            [
                ("zapclinslz.com", WHITE, font(28, True)),
                ("Golden Shopping Calhau • Quiosque 01", NEAR_WHITE, font(22, False)),
                ("SÃO LUÍS • MA", CYAN, font(24, True)),
            ],
            cy=980,
            opacity=op6,
            line_gap=10,
        )
        draw_centered_lines(
            frame,
            [
                ("Salva o Reel e manda pro amigo", NEAR_WHITE, font(22, False)),
                ("que tá com o capacete fedendo.", NEAR_WHITE, font(22, False)),
            ],
            cy=1200,
            opacity=op6 * scene_opacity(t, 25.8, 30.0, 0.3),
            line_gap=6,
        )

    # Film grain-ish subtle vignette corners
    vig = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    vd = ImageDraw.Draw(vig)
    for r in range(0, 180, 2):
        a = int(90 * (r / 180) ** 1.6)
        vd.rectangle([r, r, W - r, H - r], outline=(0, 0, 0, a))
    frame.alpha_composite(vig)

    return frame.convert("RGB")


def _render_range(args: tuple[int, int, str, str]) -> int:
    start, end, flyer_path, out_dir = args
    local_flyer = Image.open(flyer_path).convert("RGB")
    out = Path(out_dir)
    for i in range(start, end):
        frame = render_frame(local_flyer, i)
        frame.save(out / f"frame_{i:04d}.jpg", quality=88, optimize=True)
    return end - start


def main() -> None:
    from concurrent.futures import ProcessPoolExecutor, as_completed
    import multiprocessing as mp

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    VIDEO_OUT.parent.mkdir(parents=True, exist_ok=True)

    print("Preparing flyer...")
    flyer = prepare_flyer()
    flyer_path = Path("/tmp/zapclin-reel/flyer_prepared.jpg")
    flyer_path.parent.mkdir(parents=True, exist_ok=True)
    flyer.save(flyer_path, quality=95)
    print(f"Flyer prepared: {flyer.size}")

    print(f"Rendering {TOTAL_FRAMES} frames @ {FPS}fps...")
    workers = max(2, min(8, mp.cpu_count()))
    chunk = max(30, TOTAL_FRAMES // (workers * 4))
    ranges = [
        (i, min(i + chunk, TOTAL_FRAMES), str(flyer_path), str(OUT_DIR))
        for i in range(0, TOTAL_FRAMES, chunk)
    ]
    done = 0
    with ProcessPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(_render_range, r): r for r in ranges}
        for fut in as_completed(futs):
            done += fut.result()
            print(f"  {done}/{TOTAL_FRAMES} frames")

    print("Encoding video with ffmpeg...")
    cmd = (
        f'ffmpeg -y -framerate {FPS} -i "{OUT_DIR}/frame_%04d.jpg" '
        f'-c:v libx264 -pix_fmt yuv420p -profile:v high -level 4.1 '
        f'-crf 18 -preset medium -movflags +faststart '
        f'-t {DURATION} "{VIDEO_OUT}"'
    )
    rc = os.system(cmd)
    if rc != 0:
        raise SystemExit(f"ffmpeg failed with code {rc}")
    print(f"Done: {VIDEO_OUT}")
    print(f"Size: {VIDEO_OUT.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Vídeo institucional ZapClin — higienização e limpeza de capacetes em São Luís."""

from __future__ import annotations

import asyncio
import subprocess
import textwrap
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "social-media"
PHOTOS = OUT / "institucional"
FONTS = OUT
ASSETS = ROOT / "assets"
ARTIFACTS = Path("/opt/cursor/artifacts")

W, H = 1080, 1920
FPS = 30


@dataclass
class Scene:
    photo: str
    duration: float
    narration: str
    headline: str
    subline: str


SCENES: list[Scene] = [
    Scene(
        "loja-equipamentos.jpg",
        7.5,
        "ZapClin. Especialistas em higienização e limpeza de capacetes em São Luís.",
        "ZAPCLIN",
        "Higienização e limpeza de capacetes · São Luís/MA",
    ),
    Scene(
        "capacete-ls2-carbon.jpg",
        8.0,
        "Seu equipamento de proteção acumula suor, poeira e bactérias a cada viagem. "
        "Nós eliminamos germes, fungos e odores com processo profissional.",
        "HIGIENIZAÇÃO DE CAPACETES",
        "Germes · Fungos · Odores eliminados",
    ),
    Scene(
        "capacete-airoh.jpg",
        8.0,
        "Limpeza de capacete com equipamentos dedicados, feita por quem entende de moto "
        "e de segurança no trânsito.",
        "LIMPEZA DE CAPACETE",
        "Equipamentos dedicados · Processo seguro",
    ),
    Scene(
        "capacete-kyt-brasil.jpg",
        8.0,
        "Do forro interno à viseira: higienização, limpeza e revitalização premium "
        "para capacetes de moto em São Luís.",
        "CUIDADO COMPLETO",
        "Forro · Viseira · Casca · Acabamento premium",
    ),
    Scene(
        "capacete-kyt-amarelo.jpg",
        7.5,
        "Resultado impecável. Capacete limpo, higienizado e pronto para a estrada.",
        "RESULTADO IMPECÁVEL",
        "Capacete limpo · Cheiro agradável · Pronto para rodar",
    ),
    Scene(
        "loja-equipamentos.jpg",
        8.0,
        "ZapClin — Golden Shopping Calhau, Quiosque zero um, São Luís. "
        "A partir de quinze reais. Sua segurança começa com um capacete higienizado.",
        "VISITE A ZAPCLIN",
        "Golden Shopping Calhau · Quiosque 01 · São Luís\nWhatsApp (98) 98147-9616 · A partir de R$ 15",
    ),
]


def run(cmd: list[str]) -> None:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\n{result.stderr}")


def escape_drawtext(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace(":", "\\:")
        .replace("'", "\\'")
        .replace("%", "\\%")
    )


def prep_photo(src: Path, work: Path) -> Path:
    """Reduz fotos enormes para acelerar o ffmpeg."""
    from PIL import Image

    Image.MAX_IMAGE_PIXELS = None
    prepared = work / f"prep_{src.stem}.jpg"
    if prepared.exists():
        return prepared
    img = Image.open(src).convert("RGB")
    img.thumbnail((2400, 2400), Image.Resampling.LANCZOS)
    img.save(prepared, quality=92, optimize=True)
    return prepared


def make_scene_video(scene: Scene, index: int, work: Path) -> Path:
    src = prep_photo(PHOTOS / scene.photo, work)
    out = work / f"scene_{index:02d}.mp4"
    frames = int(scene.duration * FPS)

    headline = escape_drawtext(scene.headline)
    sub = escape_drawtext(scene.subline.replace("\n", "\\n"))

    oxanium = str(FONTS / "Oxanium-Bold.ttf")
    manrope = str(FONTS / "Manrope-SemiBold.ttf")
    manrope_reg = str(FONTS / "Manrope-Regular.ttf")

    # Ken Burns + gradient overlay + text
    vf = (
        f"scale={W*2}:{H*2}:force_original_aspect_ratio=increase,"
        f"crop={W*2}:{H*2},"
        f"zoompan=z='1+0.0008*on':x='(iw-iw/zoom)/2':y='(ih-ih/zoom)/2':"
        f"d={frames}:s={W}x{H}:fps={FPS},"
        f"drawbox=x=0:y=ih*0.62:w=iw:h=ih*0.38:color=black@0.55:t=fill,"
        f"drawtext=fontfile='{oxanium}':text='{headline}':"
        f"fontcolor=0x5cffd7:fontsize=52:x=(w-text_w)/2:y=h*0.66:borderw=0,"
        f"drawtext=fontfile='{manrope}':text='{sub}':"
        f"fontcolor=white:fontsize=34:x=(w-text_w)/2:y=h*0.74:borderw=0,"
        f"drawtext=fontfile='{manrope_reg}':text='São Luís · MA':"
        f"fontcolor=0x9aa3bf:fontsize=26:x=(w-text_w)/2:y=h*0.92:borderw=0"
    )

    run(
        [
            "ffmpeg",
            "-y",
            "-loop",
            "1",
            "-i",
            str(src),
            "-vf",
            vf,
            "-t",
            str(scene.duration),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-crf",
            "18",
            "-an",
            str(out),
        ]
    )
    return out


async def synthesize() -> Path:
    import edge_tts

    text = " ".join(s.narration for s in SCENES)
    out = OUT / "institucional-narracao.mp3"
    comm = edge_tts.Communicate(text, "pt-BR-AntonioNeural", rate="-2%")
    await comm.save(str(out))
    return out


def concat_scenes(clips: list[Path], work: Path) -> Path:
    silent = work / "silent.mp4"
    list_file = work / "concat.txt"
    list_file.write_text("\n".join(f"file '{c}'" for c in clips))

    run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(list_file),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-crf",
            "18",
            str(silent),
        ]
    )
    return silent


def add_logo_and_audio(silent: Path, audio: Path, final: Path) -> None:
    logo = ASSETS / "logo-nav.png"
    run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(silent),
            "-i",
            str(audio),
            "-i",
            str(logo),
            "-filter_complex",
            (
                "[2:v]scale=220:-1[logo];"
                "[0:v][logo]overlay=(W-w)/2:60:format=auto,format=yuv420p[v]"
            ),
            "-map",
            "[v]",
            "-map",
            "1:a",
            "-c:v",
            "libx264",
            "-crf",
            "18",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-shortest",
            str(final),
        ]
    )


def write_srt(audio_dur: float) -> Path:
    srt = OUT / "institucional-legendas.srt"
    total_planned = sum(s.duration for s in SCENES)
    scale = audio_dur / total_planned
    t = 0.0
    blocks: list[str] = []
    for i, scene in enumerate(SCENES, 1):
        dur = scene.duration * scale
        start = format_srt_time(t)
        end = format_srt_time(t + dur)
        lines = textwrap.wrap(scene.narration, width=42)
        blocks.append(f"{i}\n{start} --> {end}\n" + "\n".join(lines) + "\n")
        t += dur
    srt.write_text("\n".join(blocks), encoding="utf-8")
    return srt


def format_srt_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def write_copy() -> None:
    copy = OUT / "copy-institucional.txt"
    copy.write_text(
        """═══════════════════════════════════════
 ZAPCLIN — VÍDEO INSTITUCIONAL
 Higienização e limpeza de capacetes · São Luís
═══════════════════════════════════════

▸ TÍTULOS SUGERIDOS

1. Higienização de Capacetes em São Luís | ZapClin
2. Limpeza de Capacete Profissional — ZapClin São Luís
3. ZapClin — Especialistas em Capacetes Limpos e Higienizados

▸ LEGENDA (Instagram / TikTok / Facebook / LinkedIn)

🪖 Higienização e limpeza de capacetes em São Luís!

Na ZapClin cuidamos do equipamento que te protege na estrada. Eliminamos germes, fungos e odores do forro, fazemos limpeza interna e externa e entregamos seu capacete impecável — pronto para a próxima viagem.

✅ Higienização de capacetes (8–12 min)
✅ Limpeza de capacete profissional
✅ Lavagem e revitalização premium
✅ Secagem pós-chuva

📍 Golden Shopping Calhau — Quiosque 01, São Luís/MA
📲 WhatsApp: (98) 98147-9616
🌐 zapclinslz.com
📸 @zapclinhigienizacao

#ZapClin #HigienizaçãoDeCapacete #LimpezaDeCapacete #CapaceteLimpo #MotoSãoLuís #Motoboy #SãoLuís #GoldenShoppingCalhau

▸ TEXTO CURTO (X / Twitter)

Higienização e limpeza de capacetes em São Luís 🪖 ZapClin — Golden Shopping Calhau. A partir de R$ 15. #LimpezaDeCapacete #HigienizaçãoDeCapacete #SãoLuís
""",
        encoding="utf-8",
    )


def main() -> None:
    work = OUT / "institucional-work"
    work.mkdir(exist_ok=True)

    print("Baixando fontes (se necessário)...")
    for url, name in [
        (
            "https://cdn.jsdelivr.net/fontsource/fonts/oxanium@5.2.5/latin-700-normal.ttf",
            "Oxanium-Bold.ttf",
        ),
        (
            "https://cdn.jsdelivr.net/fontsource/fonts/manrope@5.2.5/latin-600-normal.ttf",
            "Manrope-SemiBold.ttf",
        ),
        (
            "https://cdn.jsdelivr.net/fontsource/fonts/manrope@5.2.5/latin-400-normal.ttf",
            "Manrope-Regular.ttf",
        ),
    ]:
        dest = FONTS / name
        if not dest.exists() or dest.read_bytes()[:4] != b"\x00\x01\x00\x00":
            run(["curl", "-sL", url, "-o", str(dest)])

    print("Gerando cenas...")
    clips = [make_scene_video(s, i, work) for i, s in enumerate(SCENES)]

    print("Concatenando...")
    silent = concat_scenes(clips, work)

    print("Gerando narração PT-BR...")
    audio = asyncio.run(synthesize())

    probe = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(audio),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    audio_dur = float(probe.stdout.strip())

    final = OUT / "zapclin-institucional-9x16.mp4"
    print("Adicionando logo e áudio...")
    add_logo_and_audio(silent, audio, final)

    write_srt(audio_dur)
    write_copy()

    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    run(["cp", str(final), str(ARTIFACTS / final.name)])

    # Versão 1:1 para feed
    square = OUT / "zapclin-institucional-1x1.mp4"
    run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(final),
            "-vf",
            "crop=1080:1080:0:420,scale=1080:1080",
            "-c:v",
            "libx264",
            "-crf",
            "18",
            "-c:a",
            "copy",
            str(square),
        ]
    )
    run(["cp", str(square), str(ARTIFACTS / square.name)])

    print(f"✓ Vídeo 9:16: {final}")
    print(f"✓ Vídeo 1:1: {square}")
    print(f"✓ Legendas: {OUT / 'institucional-legendas.srt'}")
    print(f"✓ Copy: {OUT / 'copy-institucional.txt'}")


if __name__ == "__main__":
    main()

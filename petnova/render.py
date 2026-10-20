"""Ilustrações próprias com Pillow e vídeos gráficos FFmpeg, sem assets externos."""
import json
import os
from pathlib import Path
import shutil
import subprocess

from PIL import Image, ImageDraw, ImageFont

CREAM = "#f7f4e9"
FOREST = "#204e3c"
MINT = "#d6e4ce"
CLAY = "#c86c4c"
INK = "#203a2c"


def font(size, bold=False):
    candidates = [os.environ.get("PETNOVA_FONT_BOLD" if bold else "PETNOVA_FONT", ""),
                  f"/usr/share/fonts/truetype/dejavu/DejaVuSans{'-Bold' if bold else ''}.ttf",
                  f"C:/Windows/Fonts/{'arialbd' if bold else 'arial'}.ttf",
                  "/System/Library/Fonts/Supplemental/Arial.ttf"]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return ImageFont.truetype(candidate, size)
    return ImageFont.truetype("DejaVuSans.ttf", size)


def wrapped(draw, text, x, y, max_width, size, fill=INK, bold=False, leading=1.25):
    face = font(size, bold)
    line = ""
    for word in text.split():
        candidate = (line + " " + word).strip()
        if draw.textlength(candidate, font=face) > max_width and line:
            draw.text((x, y), line, font=face, fill=fill)
            y += int(size * leading)
            line = word
        else:
            line = candidate
    if line:
        draw.text((x, y), line, font=face, fill=fill)
        y += int(size * leading)
    return y


def pet_art(draw, cx, cy, radius, dog=False):
    """Mascote vetorial desenhada no próprio ficheiro; não representa o produto."""
    r = radius
    def box(x1, y1, x2, y2):
        return (cx + x1*r, cy + y1*r, cx + x2*r, cy + y2*r)
    draw.ellipse(box(-1.55, -.85, 1.55, 1.65), fill=MINT)
    coat = "#e1ac75" if dog else "#efc398"
    if dog:
        draw.ellipse(box(-1.15, -.72, -.48, .83), fill="#875b43")
        draw.ellipse(box(.48, -.72, 1.15, .83), fill="#875b43")
    else:
        draw.polygon([(cx-r*.9, cy-r*.15), (cx-r*.82, cy-r*1.05), (cx-r*.2, cy-r*.55)], fill=coat)
        draw.polygon([(cx+r*.9, cy-r*.15), (cx+r*.82, cy-r*1.05), (cx+r*.2, cy-r*.55)], fill=coat)
        draw.polygon([(cx-r*.75, cy-r*.35), (cx-r*.73, cy-r*.8), (cx-r*.4, cy-r*.5)], fill="#cd896d")
        draw.polygon([(cx+r*.75, cy-r*.35), (cx+r*.73, cy-r*.8), (cx+r*.4, cy-r*.5)], fill="#cd896d")
    draw.ellipse(box(-.92, -.7, .92, 1.05), fill=coat)
    draw.ellipse(box(-.5, -.05, -.36, .13), fill=INK)
    draw.ellipse(box(.36, -.05, .5, .13), fill=INK)
    draw.ellipse(box(-.52, .32, .52, .88), fill="#fbebd9")
    draw.ellipse(box(-.15, .29, .15, .47), fill=INK)
    draw.arc(box(-.32, .35, 0, .69), 0, 95, fill=INK, width=max(2, int(r*.025)))
    draw.arc(box(0, .35, .32, .69), 85, 180, fill=INK, width=max(2, int(r*.025)))
    if not dog:
        for side in (-1, 1):
            for delta in (-.1, .1):
                draw.line([(cx+side*r*.5, cy+r*(.43+delta)), (cx+side*r*1.05, cy+r*(.4+delta))], fill=INK, width=max(2, int(r*.02)))


def card(post, scene, path, size=(1080, 1920), index=0):
    width, height = size
    ad = height < 1600
    image = Image.new("RGB", size, CREAM)
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((72, 76, 425, 139), radius=31, fill=FOREST)
    draw.text((98, 87), "PETNOVA PORTUGAL", font=font(25, True), fill=CREAM)
    draw.text((76, 173), "VIDA COM CÃES E GATOS", font=font(23, True), fill=FOREST)
    y = wrapped(draw, scene["title"], 76, 239, 900, 64 if ad else 76, bold=True)
    y = wrapped(draw, scene["body"], 79, y+27, 880, 32 if ad else 38, leading=1.4)
    art_y = max(y + 185, 825 if ad else 1100)
    pet_art(draw, width//2, art_y, 157 if ad else 210, dog=post["theme"] == "passeio")
    draw.text((78, height-263), "ILUSTRAÇÃO DE CONCEITO", font=font(23, True), fill=FOREST)
    draw.rounded_rectangle((72, height-202, width-72, height-84), radius=22, fill=FOREST)
    draw.text((100, height-188), "LOJA EM DEMONSTRAÇÃO", font=font(28, True), fill=CREAM)
    draw.text((100, height-141), "Sem encomendas nem pagamentos.", font=font(25), fill=CREAM)
    if not ad:
        for n in range(4):
            x = 78+n*235
            draw.rounded_rectangle((x, height-47, x+210, height-41), radius=3, fill=CLAY if n == index else MINT)
    image.save(path)


def srt_time(value):
    millis = round(value * 1000)
    seconds, ms = divmod(millis, 1000)
    minutes, sec = divmod(seconds, 60)
    hour, minute = divmod(minutes, 60)
    return f"{hour:02}:{minute:02}:{sec:02},{ms:03}"


def write_subtitles(post, path, duration):
    part = duration / len(post["scenes"])
    parts = []
    for index, scene in enumerate(post["scenes"]):
        parts.append(f"{index+1}\n{srt_time(index*part)} --> {srt_time((index+1)*part)}\n{scene['title']}\n{scene['body']}\n")
    Path(path).write_text("\n".join(parts), encoding="utf-8")


def inspect_video(path):
    result = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
                            check=True, capture_output=True, text=True, timeout=30)
    data = json.loads(result.stdout)
    video = next(stream for stream in data["streams"] if stream["codec_type"] == "video")
    return {"width": video["width"], "height": video["height"], "codec": video["codec_name"],
            "pixel_format": video["pix_fmt"], "duration": float(data["format"]["duration"]),
            "audio": any(stream["codec_type"] == "audio" for stream in data["streams"])}


def render_post(post, output, duration=24):
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise RuntimeError("Instala FFmpeg (incluindo ffprobe) ou usa --sem-video.")
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    card(post, post["scenes"][0], output / "anuncio.png", (1080, 1350))
    frames = []
    for index, scene in enumerate(post["scenes"]):
        path = output / f"cena-{index+1}.png"
        card(post, scene, path, index=index)
        frames.append(path)
    part = duration / len(frames)
    command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-filter_complex_threads", "1"]
    for frame in frames:
        command += ["-loop", "1", "-framerate", "30", "-t", str(part), "-i", str(frame)]
    command += ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"]
    filters = []
    for index in range(len(frames)):
        filters.append(f"[{index}:v]zoompan=z='1.015+0.00004*on':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':d=1:s=1080x1920:fps=30,setsar=1,setpts=PTS-STARTPTS[v{index}]")
    filters.append("".join(f"[v{i}]" for i in range(len(frames))) + f"concat=n={len(frames)}:v=1:a=0,format=yuv420p[out]")
    temporary = output / "video.tmp.mp4"
    command += ["-filter_complex", ";".join(filters), "-map", "[out]", "-map", f"{len(frames)}:a",
                "-t", str(duration), "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-threads", "2",
                "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart", str(temporary)]
    try:
        subprocess.run(command, check=True, capture_output=True, text=True, timeout=240)
        metadata = inspect_video(temporary)
        if (metadata["width"], metadata["height"], metadata["codec"]) != (1080, 1920, "h264"):
            raise RuntimeError("Formato de vídeo inesperado.")
        if abs(metadata["duration"] - duration) > 0.3 or not metadata["audio"]:
            raise RuntimeError("Duração ou pista de áudio inválida.")
        temporary.replace(output / "video.mp4")
    finally:
        temporary.unlink(missing_ok=True)
    (output / "video-info.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return metadata

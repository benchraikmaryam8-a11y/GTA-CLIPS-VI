#!/usr/bin/env python3
"""Create a 35s vertical GTA CLIPS VI intro from openly licensed Commons video or graphics.

Only CC0/public-domain and CC BY 3.0/4.0 media are downloaded. Generic fallback clips
are b-roll, not claimed to be GTA VI footage. Requires ffmpeg and ffprobe on PATH.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MEDIA = ROOT / "assets" / "downloads"
OUT = ROOT / "output"
WIDTH, HEIGHT, FPS = 1080, 1920, 30
DURATION = 35

# Explicitly time the requested beats: hook (0-3), montage (3-10), action (10-20),
# channel reveal (20-30), and CTA (30-35).
SCENES = [
    (3, "THE NEXT LEVEL\\nOF GAMING IS HERE!", "0x100629", "0x04d9ff"),
    (7, "VICE CITY\\nAFTER DARK", "0x170521", "0xff2e9a"),
    (10, "HIGH SPEED.\\nHIGH STAKES.", "0x07152b", "0x8c4dff"),
    (10, "GTA CLIPS VI", "0x100629", "0xff2e9a"),
    (5, "EPIC CLIPS. CRAZY MOMENTS. GTA VI!\\nSUBSCRIBE NOW AND JOIN THE ADVENTURE!", "0x07152b", "0x04d9ff"),
]


def run(cmd: list[str], *, capture: bool = False) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(cmd, check=True, text=True, capture_output=capture)
    except subprocess.CalledProcessError as exc:
        if capture and exc.stderr:
            print(exc.stderr[-3000:], file=sys.stderr)
        raise


def commons_search(query: str, limit: int = 12) -> list[dict]:
    """Find freely licensed Commons video files; return their metadata, not arbitrary URLs."""
    params = {
        "action": "query", "format": "json", "generator": "search",
        "gsrsearch": f'filetype:video {query}', "gsrnamespace": "6",
        "gsrlimit": str(limit), "prop": "imageinfo", "iiprop": "url|extmetadata",
    }
    url = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "GTACLIPSVI-ShortsGenerator/1.0 (open media discovery)"})
    with urllib.request.urlopen(req, timeout=25) as response:
        data = json.load(response)
    pages = data.get("query", {}).get("pages", {}).values()
    result = []
    for page in pages:
        infos = page.get("imageinfo", [])
        if not infos:
            continue
        info = infos[0]
        meta = info.get("extmetadata", {})
        license_short = re.sub(r"<[^>]+>", "", meta.get("LicenseShortName", {}).get("value", "")).strip()
        license_url = re.sub(r"<[^>]+>", "", meta.get("LicenseUrl", {}).get("value", "")).strip()
        low = license_short.lower()
        allowed = ("cc0" in low or "public domain" in low or
                   ("cc by" in low and ("3.0" in low or "4.0" in low)))
        media_url = info.get("url", "")
        if allowed and media_url.lower().split("?")[0].endswith((".mp4", ".webm", ".ogv", ".mov")):
            result.append({
                "title": page.get("title", ""), "url": media_url,
                "description_url": info.get("descriptionurl", ""),
                "license": license_short, "license_url": license_url,
                "artist": re.sub(r"<[^>]+>", "", meta.get("Artist", {}).get("value", "")).strip(),
            })
    return result


def discover_and_download() -> list[dict]:
    MEDIA.mkdir(parents=True, exist_ok=True)
    found: list[dict] = []
    # Search for GTA VI first. If Commons has no eligible clips, use generic cinematic b-roll.
    for query in ("Grand Theft Auto VI", '"GTA 6"', "Vice City gameplay", "Miami city night", "sports car night", "beach aerial"):
        try:
            candidates = commons_search(query)
        except Exception as exc:
            print(f"Commons search failed for {query!r}: {exc}", file=sys.stderr)
            continue
        for item in candidates:
            if any(x["url"] == item["url"] for x in found):
                continue
            found.append(item)
            if len(found) >= 5:
                break
        if len(found) >= 5:
            break
        time.sleep(0.25)

    saved = []
    for index, item in enumerate(found):
        ext = Path(urllib.parse.urlparse(item["url"]).path).suffix.lower()
        if ext not in (".mp4", ".webm", ".ogv", ".mov"):
            continue
        dest = MEDIA / f"commons_{index:02d}{ext}"
        try:
            req = urllib.request.Request(item["url"], headers={"User-Agent": "GTACLIPSVI-ShortsGenerator/1.0"})
            with urllib.request.urlopen(req, timeout=60) as response, dest.open("wb") as handle:
                shutil.copyfileobj(response, handle)
            item["local_path"] = str(dest)
            saved.append(item)
            print(f"Downloaded licensed Commons video: {item['title']} ({item['license']})")
        except Exception as exc:
            print(f"Could not download {item['title']}: {exc}", file=sys.stderr)
            dest.unlink(missing_ok=True)
    return saved


def media_files() -> list[Path]:
    if not MEDIA.exists():
        return []
    valid = []
    for path in sorted(MEDIA.iterdir()):
        if path.suffix.lower() not in (".mp4", ".webm", ".ogv", ".mov", ".mkv"):
            continue
        probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)], text=True, capture_output=True)
        if probe.returncode == 0 and probe.stdout.strip():
            valid.append(path)
    return valid


def escape_filter_path(path: Path) -> str:
    # FFmpeg filter parser escaping for absolute textfile paths.
    return str(path.resolve()).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def render_scene(index: int, duration: int, text: str, base: str, accent: str, source: Path | None, target: Path):
    text_path = OUT / f"scene_{index}.txt"
    # drawtext reads from file so punctuation/newlines are not interpreted as filter syntax.
    text_path.write_text(text.replace("\\n", "\n"), encoding="utf-8")
    textfile = escape_filter_path(text_path)
    # Animated neon bars and a subtle dark overlay keep text legible over licensed footage.
    overlays = (
        f",drawbox=x='mod(t*240\\,1480)-200':y=220:w=190:h=8:color={accent}@0.85:t=fill"
        f",drawbox=x='1080-mod(t*180\\,1280)':y=1680:w=150:h=7:color=0x8c4dff@0.9:t=fill"
    )
    vf = (f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,crop={WIDTH}:{HEIGHT},"
          f"setsar=1,fps={FPS},drawbox=x=0:y=0:w=iw:h=ih:color=black@0.40:t=fill"
          f"{overlays},drawtext=font='DejaVu Sans':textfile='{textfile}':"
          f"fontcolor=white:fontsize=72:line_spacing=24:borderw=3:bordercolor=black@0.75:"
          f"shadowcolor={accent}@0.9:shadowx=0:shadowy=0:x=(w-text_w)/2:y=(h-text_h)/2:"
          f"alpha='if(lt(t,0.35),t/0.35,if(gt(t,{duration-0.3}),({duration}-t)/0.3,1))',format=yuv420p")
    if source:
        cmd = ["ffmpeg", "-y", "-stream_loop", "-1", "-i", str(source), "-t", str(duration), "-vf", vf,
               "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", str(target)]
    else:
        # Original procedural animated background; no external footage required.
        vf = (f"drawbox=x='mod(t*190\\,1280)-200':y=0:w=340:h=ih:color={accent}@0.14:t=fill"
              f",drawbox=x=0:y='mod(t*120\\,2100)-180':w=iw:h=12:color=0x8c4dff@0.38:t=fill"
              f",drawtext=font='DejaVu Sans':textfile='{textfile}':fontcolor=white:fontsize=72:"
              f"line_spacing=24:borderw=3:bordercolor=black@0.75:shadowcolor={accent}@0.95:shadowx=0:shadowy=0:"
              f"x=(w-text_w)/2:y=(h-text_h)/2:alpha='if(lt(t,0.35),t/0.35,if(gt(t,{duration-0.3}),({duration}-t)/0.3,1))',format=yuv420p")
        cmd = ["ffmpeg", "-y", "-f", "lavfi", "-i", f"color=c={base}:s={WIDTH}x{HEIGHT}:r={FPS}:d={duration}",
               "-vf", vf, "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", str(target)]
    run(cmd)


def make_audio(path: Path):
    # A locally synthesized pulse/lead bed, with gentle fade in/out. No external music is used.
    expr = "0.10*sin(2*PI*55*t)+0.06*sin(2*PI*110*t)*(0.5+0.5*sin(2*PI*2*t))+0.035*sin(2*PI*220*t)*(0.5+0.5*sin(2*PI*4*t))+0.02*sin(2*PI*440*t)*(0.5+0.5*sin(2*PI*1*t))"
    run(["ffmpeg", "-y", "-f", "lavfi", "-i", f"aevalsrc={expr}:s=44100:d={DURATION}",
         "-af", f"afade=t=in:st=0:d=1,afade=t=out:st={DURATION-2}:d=2,volume=0.8", "-c:a", "aac", "-b:a", "192k", str(path)])


def write_credits(items: list[dict], files: list[Path]):
    lines = ["GTA CLIPS VI Shorts intro — media credits", "", "Generated music and graphics: synthesized/created locally by make_short.py.", ""]
    by_path = {str(Path(x.get("local_path", "")).resolve()): x for x in items if x.get("local_path")}
    if not files:
        lines.append("No external video footage was used; the video uses procedural graphics only.")
    else:
        for path in files:
            item = by_path.get(str(path.resolve()))
            if item:
                lines += [f"Title: {item['title']}", f"Creator: {item.get('artist') or 'Not provided in source metadata'}",
                          f"License: {item['license']} ({item.get('license_url') or 'see source page'})",
                          f"Source: {item.get('description_url') or item['url']}", ""]
            else:
                lines += [f"Local file: {path.name}", "Add the creator, license, and source URL here before publishing.", ""]
    (OUT / "credits.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-download", action="store_true", help="Skip Commons discovery; render with local clips or graphics.")
    args = parser.parse_args()
    for tool in ("ffmpeg", "ffprobe"):
        if not shutil.which(tool):
            raise SystemExit(f"Required tool not found: {tool}. Install FFmpeg and ensure {tool} is on PATH.")
    OUT.mkdir(parents=True, exist_ok=True)
    items = []
    if not args.no_download:
        items = discover_and_download()
    clips = media_files()
    if not clips:
        print("No local/licensed video found. Rendering original animated graphics; no GTA VI gameplay is included.")
    elif not items:
        print("Using local video files. Check their licenses and add attribution before publishing.")
    segment_paths = []
    cursor = 0
    for i, (duration, text, base, accent) in enumerate(SCENES):
        source = clips[i % len(clips)] if clips else None
        segment = OUT / f"segment_{i:02d}.mp4"
        render_scene(i, duration, text, base, accent, source, segment)
        segment_paths.append(segment)
        cursor += duration
    concat_file = OUT / "concat.txt"
    concat_file.write_text("\n".join(f"file '{p.resolve()}'" for p in segment_paths) + "\n", encoding="utf-8")
    silent = OUT / "video_silent.mp4"
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file), "-c", "copy", str(silent)])
    audio = OUT / "soundtrack.m4a"
    make_audio(audio)
    final = OUT / "gta-clips-vi-intro.mp4"
    run(["ffmpeg", "-y", "-i", str(silent), "-i", str(audio), "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
         "-shortest", "-movflags", "+faststart", str(final)])
    write_credits(items, clips)
    print(f"Finished: {final}")
    print(f"Credits:  {OUT / 'credits.txt'}")
    print("Review the video and verify all source licenses/attributions before upload.")


if __name__ == "__main__":
    main()

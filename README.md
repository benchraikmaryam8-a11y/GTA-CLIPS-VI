# GTA CLIPS VI — Shorts intro generator

Generate a 35-second, 1080×1920 YouTube Shorts intro with Python and FFmpeg. It searches Wikimedia Commons for video clips and downloads only files whose metadata identifies them as CC0 or CC BY. It records required credits. It never downloads YouTube/Twitch videos or bypasses access controls.

**Important:** this does not guarantee that licensed GTA VI gameplay exists. The script searches for GTA VI footage first; when none is found, it can use clearly generic, openly licensed city/car/beach video as visual b-roll, or render animated neon graphics. It does not represent generic b-roll as GTA VI gameplay. Official trailers and other copyrighted footage are not used unless independently released under an eligible license.

## Requirements

- Python 3.9+
- FFmpeg and ffprobe on `PATH`
- Internet access for optional Wikimedia Commons discovery
- Optional: `espeak` for locally generated narration (no API/account required)

No Python packages, paid APIs, subscriptions, or watermarks are required.

## Run

```bash
python3 make_short.py
```

The script searches for eligible Commons videos and downloads a small number to `assets/downloads/`, then renders `output/gta-clips-vi-intro.mp4` and `output/credits.txt`. If no eligible video is found, it creates an animated, text-led intro instead. Inspect the downloaded visuals and the credits before publishing. The generator does not download the final video from YouTube or other platforms.

To skip online discovery and render only procedural graphics:

```bash
python3 make_short.py --no-download
```

To use already downloaded/local video files, put them in `assets/downloads/`; keep their original license information and add the required attribution to `output/credits.txt` before publishing.

## Footage and licensing

Wikimedia Commons search results are not automatically safe just because they are online. This script checks the file's recorded license metadata and accepts only CC0/public-domain declarations or CC BY 3.0/4.0 variants. CC BY requires attribution; the generated credits file contains the metadata Commons provides. Verify the source page, license, attribution, and any depicted trademarks/people yourself before upload. This is a practical filter, not legal advice or a guarantee of monetization rights. The search may return no GTA VI gameplay at all; the game-specific search is not broadened to unauthorized trailer mirrors or rips.

The music bed and simple sound accents are synthesized locally by FFmpeg. Optional narration uses the installed local `espeak` binary. The generated graphics are original procedural visuals.

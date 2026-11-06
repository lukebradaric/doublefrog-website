"""Copy the GOONS! press kit into presskit/ and make web-sized copies for the page.

    python -I tools/build_presskit_assets.py "D:/Unity/Projects/goons/Tools/PressKit/Output"

Only what the page shows is copied: originals to presskit/files/ (linked for download), the zip to
presskit/, and display copies to presskit/web/. Pixel art is detected by its whole-pixel upscale and stored at native size (lossless
WebP, scaled back up in CSS with image-rendering: pixelated); everything else becomes a lossy WebP
about 1600px wide. The three GIFs also get small looping MP4s. Needs Pillow and ffmpeg.
"""

import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageChops

SITE = Path(__file__).resolve().parent.parent / "presskit"
FOLDERS = {
    "Logos": "logos",
    "Key Art": "key-art",
    "Screenshots": "screenshots",
    "Video": "video",
}
WEB_WIDTH = 1600
HERO = "GOONS_KeyArt_NoLogo_Wide_3840x1240.png"


def pixel_scale(image):
    """The largest whole-pixel factor the image was upscaled by, or 1."""
    # Fully transparent pixels can hold any colour; blank them so they don't break the match.
    image = Image.composite(image, Image.new("RGBA", image.size), image.getchannel("A"))
    width, height = image.size
    for factor in (16, 12, 10, 8, 6, 5, 4, 3, 2):
        if width % factor or height % factor:
            continue
        small = image.resize((width // factor, height // factor), Image.Resampling.NEAREST)
        diff = ImageChops.difference(image, small.resize(image.size, Image.Resampling.NEAREST))
        # getbbox() on RGBA only looks at alpha, so check every band.
        if not any(band.getbbox() for band in diff.split()):
            return factor
    return 1


def web_copy(source, target):
    image = Image.open(source).convert("RGBA")
    factor = pixel_scale(image)
    if factor > 1:
        native = image.resize((image.width // factor, image.height // factor), Image.Resampling.NEAREST)
        if native.width <= WEB_WIDTH:
            native.save(target, "WEBP", lossless=True)
            return "px", native.size
        image = native
    width = 1920 if source.name == HERO else WEB_WIDTH
    if image.width > width:
        image = image.resize((width, round(image.height * width / image.width)), Image.Resampling.LANCZOS)
    image.save(target, "WEBP", quality=88, method=6)
    return "smooth", image.size


def main():
    output = Path(sys.argv[1])
    kit = output / "GOONS_PressKit"
    for stale in (SITE / "files", SITE / "web"):
        shutil.rmtree(stale, ignore_errors=True)
    shutil.copy2(output / "GOONS_PressKit.zip", SITE / "GOONS_PressKit.zip")
    for source_folder, slug in FOLDERS.items():
        files, web = SITE / "files" / slug, SITE / "web" / slug
        files.mkdir(parents=True, exist_ok=True)
        web.mkdir(parents=True, exist_ok=True)
        for source in sorted((kit / source_folder).iterdir()):
            if not source.is_file():
                continue
            shutil.copy2(source, files / source.name)
            if source.suffix == ".png":
                kind, size = web_copy(source, web / (source.stem + ".webp"))
            elif source.suffix == ".gif":
                subprocess.run(
                    ["ffmpeg", "-y", "-v", "error", "-i", str(source), "-movflags", "+faststart",
                     "-pix_fmt", "yuv420p", "-c:v", "libx264", "-crf", "23", "-an",
                     str(web / (source.stem + ".mp4"))],
                    check=True,
                )
                kind, size = "loop", Image.open(source).size
            else:
                kind, size = "original", None
            print(f"{slug}/{source.name}\t{kind}\t{size}\t{source.stat().st_size}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
make_pdf.py

Usage examples:
  python3 make_pdf.py --cover --lang both --quality web --out fanfan_final.pdf
  python3 make_pdf.py --out fanfan_final.pdf

What it does:
- Reads images from the "KRS规格书" directory (common image extensions).
- Optionally generates a bilingual cover (zh / en / both) and optionally places a logo.
- Merges images (cover first if requested) into a single PDF using img2pdf.
- Optionally compresses the resulting PDF with Ghostscript (if installed).
- Compatible with multiple Pillow versions (uses textbbox/textsize/font.getsize fallback).
"""

from __future__ import annotations
import argparse
import sys
import os
import shutil
import subprocess
from pathlib import Path
from typing import List, Tuple
import tempfile

try:
    from PIL import Image, ImageDraw, ImageFont
except Exception as e:
    print("Pillow (PIL) is required. Install with: pip install pillow")
    raise

try:
    import img2pdf
except Exception as e:
    print("img2pdf is required. Install with: pip install img2pdf")
    raise

try:
    from natsort import natsorted
except Exception:
    print("natsort is recommended for correct file ordering. Install with: pip install natsort")
    # fallback to simple sorted
    def natsorted(x):  # type: ignore
        return sorted(x)

# Default folder where images live
DEFAULT_IMAGES_DIR = "KRS规格书"
SUPPORTED_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".webp"}


def find_images_in_dir(dirpath: Path) -> List[Path]:
    if not dirpath.exists() or not dirpath.is_dir():
        return []
    imgs = [p for p in dirpath.iterdir() if p.suffix.lower() in SUPPORTED_IMAGE_EXTS and p.is_file()]
    return natsorted(imgs)


def text_size_compat(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont) -> Tuple[int, int]:
    """
    Measure text width and height in a Pillow-version-compatible way.
    """
    if hasattr(draw, "textbbox"):
        bbox = draw.textbbox((0, 0), text, font=font)
        return bbox[2] - bbox[0], bbox[3] - bbox[1]
    if hasattr(draw, "textsize"):
        return draw.textsize(text, font=font)
    if hasattr(font, "getsize"):
        return font.getsize(text)
    # fallback estimation
    return (len(text) * getattr(font, "size", 24) // 2, int(getattr(font, "size", 24) * 1.2))


def make_cover_image(
    title_zh: str,
    title_en: str,
    logo_path: Path | None,
    lang: str = "both",
    size=(1654, 2339),
    title_font_size=64,
    subtitle_font_size=36,
    bg_color=(255, 255, 255),
) -> Path:
    """
    Create a cover image (PNG) and return its Path.
    size: default roughly A4 at 150 DPI: 1654x2339
    """
    W, H = size
    im = Image.new("RGB", (W, H), color=bg_color)
    draw = ImageDraw.Draw(im)

    # Try to find a reasonable font; fallback to default if not found.
    def load_font(preferred_size):
        # Common system fonts (may vary by OS); fallbacks to default.
        candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/Library/Fonts/Arial.ttf",
            "/System/Library/Fonts/Supplemental/Arial.ttf",
            str(Path(__file__).parent / "fonts" / "DejaVuSans.ttf"),
        ]
        for c in candidates:
            try:
                if Path(c).exists():
                    return ImageFont.truetype(c, preferred_size)
            except Exception:
                continue
        # fallback
        return ImageFont.load_default()

    font_title = load_font(title_font_size)
    font_sub = load_font(subtitle_font_size)

    y = int(H * 0.18)

    # draw optional logo at top center if provided
    if logo_path and logo_path.exists():
        try:
            logo = Image.open(logo_path).convert("RGBA")
            # scale logo to fit width ~ 30% of page width
            max_logo_w = int(W * 0.3)
            wratio = max_logo_w / logo.width
            logo_h = int(logo.height * wratio)
            logo = logo.resize((max_logo_w, logo_h), Image.LANCZOS)
            im.paste(logo, ((W - max_logo_w) // 2, 40), logo if logo.mode == "RGBA" else None)
            y = 40 + logo_h + 30
        except Exception as e:
            print(f"Warning: failed to open or paste logo {logo_path}: {e}")

    def draw_centered_text(text: str, font: ImageFont.FreeTypeFont, start_y: int, line_spacing: int = 10):
        nonlocal draw, W
        lines = text.splitlines() if text else [""]
        cur_y = start_y
        for line in lines:
            w, h = text_size_compat(draw, line, font)
            draw.text(((W - w) / 2, cur_y), line, fill="black", font=font)
            cur_y += h + line_spacing
        return cur_y

    # Title and subtitle selection based on lang
    if lang == "zh":
        title_text = title_zh
        sub_text = ""
    elif lang == "en":
        title_text = title_en
        sub_text = ""
    else:  # both
        title_text = title_zh
        sub_text = title_en

    # Draw title
    y_after_title = draw_centered_text(title_text, font_title, y, line_spacing=12)

    # Draw subtitle a bit lower
    if sub_text:
        y_after_sub = draw_centered_text(sub_text, font_sub, y_after_title + 20, line_spacing=8)

    # Footer: small text with generation note
    footer_font = load_font(18)
    footer = "Generated by make_pdf.py"
    fw, fh = text_size_compat(draw, footer, footer_font)
    draw.text((W - fw - 40, H - fh - 40), footer, fill=(80, 80, 80), font=footer_font)

    # Save to temporary file
    tmpdir = Path(tempfile.gettempdir())
    cover_path = tmpdir / f"cover_{os.getpid()}.png"
    im.save(cover_path, format="PNG")
    print(f"[+] Generated cover image: {cover_path}")
    return cover_path


def build_pdf_from_images(image_paths: List[Path], output_pdf: Path) -> None:
    if not image_paths:
        raise ValueError("No images to convert to PDF.")
    # img2pdf expects bytes or file paths; convert Paths to strings
    image_files = [str(p) for p in image_paths]
    try:
        with open(output_pdf, "wb") as f:
            f.write(img2pdf.convert(image_files))
    except Exception as e:
        print("Error while creating PDF with img2pdf:", e)
        raise
    print(f"[+] Created PDF: {output_pdf}")


def compress_pdf_with_ghostscript(input_pdf: Path, output_pdf: Path, quality: str = "web") -> bool:
    """
    Compress using ghostscript. quality: 'web' -> /ebook, 'printer' -> /printer
    Returns True if compression succeeded.
    """
    quality_map = {"web": "/ebook", "printer": "/printer"}
    preset = quality_map.get(quality, "/ebook")
    gs_cmd = shutil.which("gs") or shutil.which("ghostscript")
    if not gs_cmd:
        print("Ghostscript not found; skipping compression.")
        return False

    cmd = [
        gs_cmd,
        "-sDEVICE=pdfwrite",
        "-dCompatibilityLevel=1.4",
        "-dPDFSETTINGS=" + preset,
        "-dNOPAUSE",
        "-dQUIET",
        "-dBATCH",
        f"-sOutputFile={str(output_pdf)}",
        str(input_pdf),
    ]
    try:
        subprocess.check_call(cmd)
        print(f"[+] Compressed PDF written to: {output_pdf}")
        return True
    except subprocess.CalledProcessError as e:
        print("Ghostscript compression failed:", e)
        return False


def parse_args():
    p = argparse.ArgumentParser(description="Create a PDF from images in the KRS规格书 folder")
    p.add_argument("--cover", action="store_true", help="Generate and prepend a cover page")
    p.add_argument("--lang", choices=("zh", "en", "both"), default="both", help="Cover language")
    p.add_argument("--logo", type=str, default=None, help="Logo image path to include on the cover")
    p.add_argument("--quality", choices=("web", "printer"), default="web", help="Compression quality (web smaller, printer higher)")
    p.add_argument("--out", type=str, default="fanfan_final.pdf", help="Output PDF filename")
    p.add_argument("--images-dir", type=str, default=DEFAULT_IMAGES_DIR, help="Directory with input images")
    return p.parse_args()


def main():
    args = parse_args()
    images_dir = Path(args.images_dir)
    out_pdf = Path(args.out).resolve()

    print(f"[+] Searching images in: {images_dir}")
    images = find_images_in_dir(images_dir)
    if not images:
        print(f"No images found in {images_dir}. Please ensure the directory exists and contains images.")
        sys.exit(1)

    tmp_files: List[Path] = []
    try:
        # Optionally create cover
        if args.cover:
            logo_p = Path(args.logo) if args.logo else None
            cover_img = make_cover_image(
                title_zh="KRS 规格书",
                title_en="KRS Specification",
                logo_path=logo_p,
                lang=args.lang,
            )
            tmp_files.append(cover_img)
            # Prepend cover as first image
            images = [cover_img] + images

        # Ensure output dir exists
        out_pdf.parent.mkdir(parents=True, exist_ok=True)

        # Build PDF from images
        print("[+] Building PDF from images...")
        build_pdf_from_images(images, out_pdf)

        # Try to compress using ghostscript; write to temp then replace if success
        compressed_pdf = out_pdf.with_suffix(".compressed.pdf")
        if compress_pdf_with_ghostscript(out_pdf, compressed_pdf, quality=args.quality):
            # Replace original
            shutil.move(str(compressed_pdf), str(out_pdf))
            print(f"[+] Replaced original PDF with compressed PDF: {out_pdf}")
        else:
            if compressed_pdf.exists():
                compressed_pdf.unlink()

    finally:
        # cleanup temporary generated images (covers)
        for t in tmp_files:
            try:
                if t.exists():
                    t.unlink()
            except Exception:
                pass

    print("[+] Done. Output:", out_pdf)


if __name__ == "__main__":
    main()

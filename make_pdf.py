#!/usr/bin/env python3
# make_pdf.py
# Generate a PDF from images in KRS规格书/ and optionally create a simple cover.

import os
import sys
import argparse
import img2pdf
from PIL import Image, ImageDraw, ImageFont
import subprocess
import re


def natural_key(s):
    # Split strings into list of ints and text for natural sorting
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r"(\\d+)", s)]


def make_cover(text_title, text_sub, logo_path=None, out='cover.pdf'):
    W, H = 1240, 1754  # roughly A4 at 150 DPI
    im = Image.new('RGB', (W, H), 'white')
    draw = ImageDraw.Draw(im)
    try:
        font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 64)
        font_sub = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 28)
    except Exception:
        font_title = ImageFont.load_default()
        font_sub = ImageFont.load_default()

    # Title (centered)
    lines = text_title.split('\n')
    y = 220
    for line in lines:
        # use textbbox to好 —— Action 失败的原因很明确：脚本在调用 draw.textsize(...) 时抛出 Attribute get size (compatible with newer Pillow)
        bbox = draw.textbbox((0, 0), line, font=font_title)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        draw.textError，意思是当前 runner 上的 Pillow/ ImageDraw 没有这个方法。(((W - w) / 2, y), line, fill='black', font=font_title)
        y += h + 10解决办法有两种（我推荐修改代码以兼容不同 Pillow 版本）。

最简单明了的修复（推荐）


    # Subtitle
    bbox = draw.textbbox((0, 0), text_sub, font=- 用 draw.textbbox(...)（Pillow 新版）或 font.getsize(...)（兼容旧版）来代替 drawfont_sub)
    w = bbox[2] - bbox[0]
    h.textsize(...)，并用 try/except 兼容两种情况。

把 make_pdf.py 中 make_cover 函数的两处 textsize 调用按下面代码替换（整段可直接复制粘贴到编辑器，替换原来的 = bbox[3] - bbox[1]
    draw.text(((W - w) / 2, y + 40), text_sub, fill='black', font=相关行）：

```python
# Title (centered)
lines = text_title.split('\n')
y = 220
for line infont_sub)

    # Logo (optional)
    if logo_path and os.path.exists lines:
    try:
        # Pillow >= 8/9: use textbbox
        bbox = draw.textbbox((0, 0), line, font=font_title)
        w, h = bbox[2] - bbox[0], bbox[3] - bbox[1(logo_path):
        try:
            logo = Image.open(logo_path).convert('RGBA')
            logo.thumbnail((300, 300))
            im.paste(logo, (int((]
    except AttributeError:
        # older Pillow: fallback to font.getsize
        w, h = font_title.getsize(line)
    draw.text(((W - w) / 2, y), line, fill='black', font=font_title)
    y += h + 10W - logo.width) / 2), H - 420), logo)
        except Exception:
            pass

    im.save

# Subtitle
try:
    bbox = draw.textbbox((0, 0), text_sub, font=font_sub)
    w, h(out, 'PDF', resolution=150)
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--cover', action='store_true')
    parser.add_argument('--lang', choices=['zh', 'en', 'both'], default='zh')
    parser.add_argument('--logo', default=None)
    parser.add_argument('--quality', choices=['web', 'print'], default='web')
    parser.add_argument('--src', default='KRS规格书')
    parser.add_argument('--out', default='fanfan_final.pdf')
    args = parser.parse_args()

    img_dir = args.src
    if not os.path.isdir(img_dir):
        print(f"Source directory '{img_dir}' not found. Exiting.")
        sys.exit(1)

    imgs = [f for f in os.listdir(img_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    if not imgs:
        print('No images found in', img_dir)
        sys.exit(1)

    imgs.sort(key=natural_key)
    img_paths = [os.path.join(img_dir, f) for f in imgs]

    # Optional cover
    cover_file = None
    if args.cover:
        if args.lang == 'zh':
            title = 'Fanfan KRS 规格书'
            subtitle = 'Company • 联系方式'
        elif args.lang == 'en':
            title = 'Fanfan KRS Brochure'
            subtitle = 'Company • Contact'
        else:
            title = 'Fanfan KRS 规格书\nFanfan KRS Brochure'
            subtitle = 'Company • 联系方式 • Contact'
        cover_file = make_cover(title, subtitle, logo_path=args.logo, out='cover.pdf')

    raw_pdf = 'fanfan_raw.pdf'
    print('Converting images to PDF...')
    try:
        with open(raw_pdf, 'wb') as f:
            f.write(img2pdf.convert(img_paths))
    except Exception as e:
        print('Error while creating raw PDF:', e)
        sys.exit(1)

    # Compress/optimize using ghostscript if available
    out_file = args.out
    preset = '/ebook' if args.quality == 'web' else '/printer'

    # If cover exists, merge cover + raw first
    if cover_file:
        merged = 'fanfan_with_cover.pdf'
        try:
            subprocess.check_call(['pdfunite', cover_file, raw_pdf, merged])
            os.replace(merged, raw_pdf)
        except Exception:
            # fallback: just concatenate using img2pdf (cover regenerated as image)
            print('pdfunite not available or failed; proceeding without merging cover via pdfunite')

    # Try ghostscript
    gs_path = shutil_which('gs')
    if gs_path:
        try:
            print('Running ghostscript optimization...')
            subprocess.check_call(['gs', '-sDEVICE=pdfwrite', '-dCompatibilityLevel=1.4', '-dPDFSETTINGS=' + preset, '-dNOPAUSE', '-dQUIET', '-dBATCH', '-sOutputFile=' + out_file, raw_pdf])
        except Exception as e:
            print('Ghostscript failed, copying raw pdf to out file. Error:', e)
            os.replace(raw_pdf, out_file)
    else:
        # No ghostscript: just move raw
        print('Ghostscript not found; outputting raw PDF as', out_file)
        os.replace(raw_pdf, out_file)

    print('Generated', out_file)


def shutil_which(cmd):
    # simple which replacement to keep stdlib-only dependency
    from shutil import which
    return which(cmd)


if __name__ == '__main__':
    main()

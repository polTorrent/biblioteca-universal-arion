#!/usr/bin/env python3
"""Genera portada per der-wille-zur-macht."""
import io
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

WIDTH, HEIGHT = 896, 1152
BG_COLOR = "#F5F1E8"
TEXT_COLOR = "#1A1A1A"
ACCENT = "#3D3D3D"

img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
draw = ImageDraw.Draw(img)

cx, cy = WIDTH // 2, int(HEIGHT * 0.45)

# Anvil
anvil_w, anvil_h = 180, 70
anvil_top_w = 140
anvil_base_y = cy + 60

draw.rectangle(
    [cx - anvil_w // 2, anvil_base_y, cx + anvil_w // 2, anvil_base_y + anvil_h],
    fill=ACCENT,
)
anvil_top_y = anvil_base_y - 30
draw.polygon(
    [
        (cx - anvil_top_w // 2 - 20, anvil_base_y),
        (cx + anvil_top_w // 2 + 40, anvil_base_y),
        (cx + anvil_top_w // 2, anvil_top_y),
        (cx - anvil_top_w // 2, anvil_top_y),
    ],
    fill=ACCENT,
)
draw.polygon(
    [
        (cx + anvil_top_w // 2 + 40, anvil_base_y),
        (cx + anvil_top_w // 2 + 70, anvil_base_y - 10),
        (cx + anvil_top_w // 2, anvil_top_y),
    ],
    fill=ACCENT,
)

# Hammer
hammer_head_w, hammer_head_h = 80, 45
hx, hy = cx - 20, anvil_top_y - 80

handle_len = 140
angle = math.radians(50)
handle_x1 = hx - 8
handle_y1 = hy + hammer_head_h // 2
handle_x2 = handle_x1 - math.sin(angle) * handle_len
handle_y2 = handle_y1 + math.cos(angle) * handle_len

hw = 10
perp_dx = math.cos(angle) * hw
perp_dy = math.sin(angle) * hw
draw.polygon(
    [
        (handle_x1 - perp_dx, handle_y1 - perp_dy),
        (handle_x1 + perp_dx, handle_y1 + perp_dy),
        (handle_x2 + perp_dx, handle_y2 + perp_dy),
        (handle_x2 - perp_dx, handle_y2 - perp_dy),
    ],
    fill=ACCENT,
)

draw.rectangle(
    [hx - hammer_head_w // 2, hy, hx + hammer_head_w // 2, hy + hammer_head_h],
    fill=ACCENT,
)

# Sparks
spark_color = "#8B6914"
sparks = [
    (cx + 30, anvil_top_y - 15, 12),
    (cx - 40, anvil_top_y - 20, 10),
    (cx + 50, anvil_top_y - 5, 8),
    (cx - 55, anvil_top_y - 10, 9),
    (cx + 15, anvil_top_y - 35, 7),
    (cx - 25, anvil_top_y - 30, 6),
]
for i, (sx, sy, sl) in enumerate(sparks):
    angle_s = math.radians(30 + i * 50)
    ex = sx + math.cos(angle_s) * sl
    ey = sy - math.sin(angle_s) * sl
    draw.line([(sx, sy), (ex, ey)], fill=spark_color, width=2)

# Glowing metal on anvil
draw.rectangle([cx - 25, anvil_top_y + 2, cx + 25, anvil_top_y + 8], fill="#B8860B")


def load_font(paths, size):
    for p in paths:
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            continue
    return ImageFont.load_default()


fonts_sb = [
    "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
]
fonts_sr = [
    "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
]
fonts_sn = [
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]

# Title
title_size = int(HEIGHT * 0.045)
font_title = load_font(fonts_sb, title_size)
title_text = "LA VOLUNTAT DE PODER"

margin_x = int(WIDTH * 0.08)
max_w = WIDTH - 2 * margin_x
words = title_text.split()
tlines = []
current = ""
for w in words:
    test = (current + " " + w).strip()
    bbox = draw.textbbox((0, 0), test, font=font_title)
    if bbox[2] - bbox[0] <= max_w:
        current = test
    else:
        if current:
            tlines.append(current)
        current = w
if current:
    tlines.append(current)

title_y = int(HEIGHT * 0.05)
line_h = int(title_size * 1.3)
for i, line in enumerate(tlines):
    bbox = draw.textbbox((0, 0), line, font=font_title)
    lw = bbox[2] - bbox[0]
    x = (WIDTH - lw) // 2
    draw.text((x, title_y + i * line_h), line, font=font_title, fill=TEXT_COLOR)

# Author
author_size = int(HEIGHT * 0.042)
font_author = load_font(fonts_sr, author_size)
author_text = "Friedrich Nietzsche"
bbox = draw.textbbox((0, 0), author_text, font=font_author)
aw = bbox[2] - bbox[0]
author_y = int(HEIGHT * 0.83)
draw.text(((WIDTH - aw) // 2, author_y), author_text, font=font_author, fill=TEXT_COLOR)

# Editorial + logo
editorial_size = int(HEIGHT * 0.018)
font_editorial = load_font(fonts_sn, editorial_size)
editorial_text = "Biblioteca Arion"

logo_path = Path("/home/jo/biblioteca-universal-arion/assets/logo/logo_arion_v1.png")
logo_size = 65
editorial_y = int(HEIGHT * 0.92)
logo = None
if logo_path.exists():
    try:
        logo_orig = Image.open(logo_path).convert("RGBA")
        data = logo_orig.getdata()
        new_data = [
            (255, 255, 255, 0)
            if (it[0] > 250 and it[1] > 250 and it[2] > 250)
            else it
            for it in data
        ]
        logo_orig.putdata(new_data)
        scale = 4
        big = logo_size * scale
        circle = Image.new("RGBA", (big, big), (0, 0, 0, 0))
        cd = ImageDraw.Draw(circle)
        border = max(4, int(big * 0.025))
        cd.ellipse(
            [border, border, big - border - 1, big - border - 1],
            fill="#FFFFFF",
            outline="#1A1A1A",
            width=border,
        )
        inner = int(big * 0.78)
        aspect = logo_orig.width / logo_orig.height
        if aspect > 1:
            lw2, lh2 = inner, int(inner / aspect)
        else:
            lh2, lw2 = inner, int(inner * aspect)
        logo_resized = logo_orig.resize((lw2, lh2), Image.Resampling.LANCZOS)
        lx, ly = (big - lw2) // 2, (big - lh2) // 2
        circle.paste(logo_resized, (lx, ly), logo_resized)
        logo = circle.resize((logo_size, logo_size), Image.Resampling.LANCZOS)
    except Exception as e:
        print(f"Logo error: {e}")

bbox = draw.textbbox((0, 0), editorial_text, font=font_editorial)
ew = bbox[2] - bbox[0]
eh = bbox[3] - bbox[1]

if logo:
    gap = 10
    total = logo_size + gap + ew
    sx = (WIDTH - total) // 2
    ly2 = editorial_y - (logo_size - eh) // 2
    img_rgba = img.convert("RGBA")
    img_rgba.paste(logo, (sx, ly2), logo)
    img = img_rgba.convert("RGB")
    draw = ImageDraw.Draw(img)
    draw.text(
        (sx + logo_size + gap, editorial_y),
        editorial_text,
        font=font_editorial,
        fill=TEXT_COLOR,
    )
else:
    draw.text(
        ((WIDTH - ew) // 2, editorial_y),
        editorial_text,
        font=font_editorial,
        fill=TEXT_COLOR,
    )

output_path = Path(
    "/home/jo/biblioteca-universal-arion/obres/filosofia/nietzsche/der-wille-zur-macht/portada.png"
)
img.save(output_path, format="PNG", compress_level=1)
print(f"Portada saved: {output_path} ({output_path.stat().st_size / 1024:.0f} KB)")

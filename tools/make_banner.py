# -*- coding: utf-8 -*-
"""Draw the App Store banner for 3A-dealer.

    python tools/make_banner.py

The banner is the card picture in the listing. Until now the card was
``screenshot_1.png``: a full screenshot shrunk to thumbnail size reads as a
grey smudge, while the competing apps show a title you can read at a glance.

Colours are taken from ``adealer/static/description/icon.png`` rather than
written out here, so a redrawn icon cannot leave the banner behind.
"""
import os

from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
DESC = os.path.join(os.path.dirname(HERE), "adealer", "static", "description")

SS = 4  # supersampling: Pillow has no antialiased drawing of its own

WHITE = (255, 255, 255)
MUTED = (176, 187, 205)

TITLE = "3A-dealer"

# Both languages on the card: the page is in English because the store is, but
# the people who buy this are searching in Ukrainian and recognise their own
# three trades faster than a translation of them.
SUBTITLE_EN = "Showroom  \u00b7  Parts  \u00b7  Service workshop"
SUBTITLE_UK = "\u0410\u0432\u0442\u043e\u0441\u0430\u043b\u043e\u043d  \u00b7  " \
              "\u0410\u0432\u0442\u043e\u0437\u0430\u043f\u0447\u0430\u0441\u0442\u0438\u043d\u0438  \u00b7  " \
              "\u0410\u0432\u0442\u043e\u0440\u0435\u043c\u043e\u043d\u0442"
DETAIL = "sale order \u2192 repair order \u2192 act \u2192 invoice"


def vertical_gradient(size, top, bottom):
    """A one-pixel strip stretched to size -- cheaper than per-pixel work."""
    width, height = size
    strip = Image.new("RGB", (1, height))
    for y in range(height):
        t = y / max(height - 1, 1)
        strip.putpixel(
            (0, y),
            tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)),
        )
    return strip.resize(size, Image.BICUBIC)


def icon_palette(icon):
    """The icon's background gradient plus its most saturated colour.

    Picking the accent by saturation rather than by sampling a fixed point
    works whatever the icon draws -- lettering, a glyph or a ring.
    """
    rgb = icon.convert("RGB")
    size = rgb.size[0]
    top = rgb.getpixel((size // 2, int(size * 0.06)))
    bottom = rgb.getpixel((size // 2, int(size * 0.94)))

    best, best_score = None, -1
    small = rgb.resize((64, 64), Image.BOX)
    for count, colour in small.getcolors(64 * 64):
        lo, hi = min(colour), max(colour)
        saturation = (hi - lo) / 255.0
        # Weight by how often it appears, so a stray antialiasing pixel cannot
        # win over the actual accent.
        score = saturation * (hi / 255.0) * (count ** 0.25)
        if score > best_score:
            best, best_score = colour, score
    return top, bottom, best


def load_font(px, bold=False):
    names = ("arialbd.ttf", "calibrib.ttf") if bold else ("arial.ttf", "calibri.ttf")
    for name in names:
        path = os.path.join(r"C:\Windows\Fonts", name)
        if os.path.exists(path):
            return ImageFont.truetype(path, px)
    return ImageFont.load_default()


def fit_font(draw, text, max_width, start_px, bold=False):
    """Largest size at which the line still fits its column."""
    px = start_px
    while px > 8:
        font = load_font(px, bold=bold)
        if draw.textlength(text, font=font) <= max_width:
            return font
        px = int(px * 0.94)
    return load_font(px, bold=bold)


def build_banner(icon, width=560, height=315):
    w, h = width * SS, height * SS
    top, bottom, accent = icon_palette(icon)
    canvas = vertical_gradient((w, h), top, bottom).convert("RGBA")

    margin = int(w * 0.07)
    mark_px = int(h * 0.42)
    mark_y = (h - mark_px) // 2
    mark = icon.convert("RGBA").resize((mark_px, mark_px), Image.LANCZOS)

    # A soft shadow so the tile sits above the background rather than in it.
    shadow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    shadow.paste(
        Image.new("RGBA", (mark_px, mark_px), (0, 0, 0, 110)),
        (margin, mark_y + int(h * 0.022)),
        mark.split()[3],
    )
    canvas = Image.alpha_composite(
        canvas, shadow.filter(ImageFilter.GaussianBlur(int(h * 0.022)))
    )
    canvas.paste(mark, (margin, mark_y), mark)

    draw = ImageDraw.Draw(canvas)
    text_x = margin + mark_px + int(w * 0.05)
    column = w - text_x - margin

    title_font = fit_font(draw, TITLE, column, int(h * 0.125), bold=True)
    # One size for both language lines, so neither reads as the afterthought:
    # whichever is longer decides, and the shorter one is set to match.
    sub_px = min(
        fit_font(draw, SUBTITLE_EN, column, int(h * 0.055)).size,
        fit_font(draw, SUBTITLE_UK, column, int(h * 0.055)).size,
    )
    sub_font = load_font(sub_px)
    detail_font = fit_font(draw, DETAIL, column, int(h * 0.043))

    # Tighter between the two translations of the same line than between
    # different lines -- that is what makes them read as one pair.
    gap_title, gap_pair, gap_detail = int(h * 0.050), int(h * 0.028), int(h * 0.044)
    block = (title_font.size + gap_title + sub_font.size + gap_pair
             + sub_font.size + gap_detail + detail_font.size)
    y = (h - block) // 2

    draw.text((text_x, y), TITLE, font=title_font, fill=WHITE, anchor="la")
    y += title_font.size + gap_title
    draw.text((text_x, y), SUBTITLE_EN, font=sub_font, fill=accent, anchor="la")
    y += sub_font.size + gap_pair
    draw.text((text_x, y), SUBTITLE_UK, font=sub_font, fill=accent, anchor="la")
    y += sub_font.size + gap_detail
    draw.text((text_x, y), DETAIL, font=detail_font, fill=MUTED, anchor="la")

    return canvas.resize((width, height), Image.LANCZOS).convert("RGB")


def main():
    icon = Image.open(os.path.join(DESC, "icon.png"))
    banner = build_banner(icon)
    out = os.path.join(DESC, "banner.png")
    banner.save(out, optimize=True)
    print("banner.png  560x315  %.1f KB" % (os.path.getsize(out) / 1024))


if __name__ == "__main__":
    main()

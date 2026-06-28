"""
generate_icons.py — Pixel-art placeholder icons for Vacuum World.

Generates 48×48 PNG sprites for: robot, dirt, wall, pet.
Each icon is drawn on a transparent canvas using a 3×3 "macro-pixel" grid
(each macro-pixel = 6×6 real pixels → 8 columns × 8 rows of macro-pixels).

Run:
    python generate_icons.py
    python generate_icons.py --size 64 --out assets/
"""

import argparse
from pathlib import Path
from PIL import Image, ImageDraw


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_canvas(size: int) -> tuple[Image.Image, ImageDraw.Draw, int]:
    """Return a transparent RGBA canvas plus the macro-pixel tile size."""
    img  = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    tile = size // 8          # 8 macro-pixels per axis
    return img, draw, tile


def px(draw: ImageDraw.Draw, col: int, row: int, tile: int, color: tuple):
    """Draw one macro-pixel at grid position (col, row)."""
    x0, y0 = col * tile, row * tile
    draw.rectangle([x0, y0, x0 + tile - 1, y0 + tile - 1], fill=color)


# Colour palettes (RGBA)
TRANSPARENT = (0,   0,   0,   0)
BLACK       = (20,  20,  20, 255)
WHITE       = (240, 240, 240, 255)


# ---------------------------------------------------------------------------
# Icon definitions  (each returns a PIL Image)
# ---------------------------------------------------------------------------

def make_robot(size: int) -> Image.Image:
    """
    Pixel-art vacuum robot — round blue body, antenna, two wheels.

    Grid layout (0-indexed col, row):
        . = transparent
        B = body blue
        L = light blue highlight
        W = dark wheel
        A = antenna tip (yellow)
        E = eye (white/black)
    """
    BODY   = (70,  130, 210, 255)   # medium blue
    LIGHT  = (120, 180, 255, 255)   # highlight
    DARK   = (30,  60,  120, 255)   # shadow
    WHEEL  = (40,  40,   50, 255)   # near-black wheel
    ANTENA = (255, 220,  50, 255)   # yellow tip
    EYE_W  = (240, 240, 240, 255)
    EYE_B  = (10,  10,   10, 255)

    img, draw, t = make_canvas(size)
    P = lambda c, r, col: px(draw, c, r, t, col)

    # Antenna
    P(4, 0, ANTENA)
    P(4, 1, DARK)

    # Body top arc  (row 2)
    for c in [2, 3, 4, 5]:  P(c, 2, BODY)
    P(2, 2, LIGHT)

    # Body middle rows 3-5
    for r in [3, 4, 5]:
        for c in [1, 2, 3, 4, 5, 6]:  P(c, r, BODY)
    # Highlights
    for r in [3, 4]:  P(1, r, LIGHT);  P(2, r, LIGHT)

    # Eyes (row 3)
    P(2, 3, EYE_W);  P(3, 3, EYE_W)
    P(2, 3, EYE_B)                  # pupil (overwrite centre pixel)
    P(5, 3, EYE_W);  P(4, 3, EYE_W)
    P(5, 3, EYE_B)

    # Body bottom / suction row 6
    for c in [2, 3, 4, 5]:  P(c, 6, DARK)
    P(3, 6, BODY);  P(4, 6, BODY)

    # Wheels row 7
    P(1, 7, WHEEL);  P(2, 7, WHEEL)
    P(5, 7, WHEEL);  P(6, 7, WHEEL)

    return img


def make_dirt(size: int) -> Image.Image:
    """
    Pixel-art dirt patch — scattered brown / tan clumps on transparent BG.
    """
    BROWN  = (139,  90,  43, 255)
    TAN    = (180, 130,  70, 255)
    DARK_B = ( 90,  55,  20, 255)

    img, draw, t = make_canvas(size)
    P = lambda c, r, col: px(draw, c, r, t, col)

    # Large clump left
    for (c, r) in [(1,4),(2,4),(1,5),(2,5),(3,5),(1,6),(2,6)]:
        P(c, r, BROWN)
    P(1, 4, TAN);  P(2, 4, TAN)

    # Small clump right
    for (c, r) in [(4,3),(5,3),(4,4),(5,4),(5,5),(6,5)]:
        P(c, r, DARK_B)
    P(4, 3, TAN);  P(5, 3, BROWN)

    # Tiny specks
    for (c, r) in [(3,2),(6,6),(2,7),(5,7),(7,4)]:
        P(c, r, BROWN)

    return img


def make_wall(size: int) -> Image.Image:
    """
    Pixel-art brick wall — classic red-brick pattern with mortar lines.
    """
    BRICK  = (180,  70,  40, 255)
    MORTAR = (210, 185, 155, 255)
    SHADOW = (140,  50,  25, 255)
    LIGHT  = (220, 110,  80, 255)

    img, draw, t = make_canvas(size)
    P = lambda c, r, col: px(draw, c, r, t, col)

    # Fill entire tile as brick base
    for r in range(8):
        for c in range(8):
            P(c, r, BRICK)

    # Mortar horizontal rows at rows 0, 3, 6 (every 3 rows)
    for r in [0, 3, 6]:
        for c in range(8):
            P(c, r, MORTAR)

    # Mortar vertical joints — offset per brick row
    # Even brick rows (rows 1-2): joints at cols 0 and 4
    for r in [1, 2]:
        P(0, r, MORTAR);  P(4, r, MORTAR)

    # Odd brick rows (rows 4-5): joints at cols 2 and 6
    for r in [4, 5]:
        P(2, r, MORTAR);  P(6, r, MORTAR)

    # Same for rows 7 (bottom partial brick row)
    P(0, 7, MORTAR);  P(4, 7, MORTAR)

    # Highlight top-left of each brick
    for (c, r) in [(1,1),(5,1),(3,4),(7,4),(1,7),(5,7)]:
        P(c, r, LIGHT)

    # Shadow bottom-right of each brick
    for (c, r) in [(3,2),(7,2),(1,5),(5,5)]:
        P(c, r, SHADOW)

    return img


def make_pet(size: int) -> Image.Image:
    """
    Pixel-art cat/pet — orange tabby with pointy ears, whiskers, tail.
    """
    ORANGE = (230, 130,  50, 255)
    LIGHT  = (255, 190, 100, 255)
    DARK   = (160,  80,  20, 255)
    STRIPE = (200,  95,  30, 255)
    EYE_G  = ( 80, 200,  80, 255)   # green eyes
    EYE_B  = (  0,   0,   0, 255)
    NOSE   = (220,  80,  80, 255)
    WHITE  = (245, 245, 245, 255)

    img, draw, t = make_canvas(size)
    P = lambda c, r, col: px(draw, c, r, t, col)

    # Ears (row 0-1)
    P(1, 0, ORANGE);  P(6, 0, ORANGE)
    P(1, 1, ORANGE);  P(2, 1, LIGHT)
    P(6, 1, ORANGE);  P(5, 1, LIGHT)

    # Head (rows 1-4)
    for r in [1, 2, 3, 4]:
        for c in [2, 3, 4, 5]:
            P(c, r, ORANGE)
    P(2, 1, LIGHT);  P(3, 1, LIGHT)    # highlight top

    # Tabby stripe on forehead
    P(4, 2, STRIPE);  P(4, 3, STRIPE)

    # Eyes row 3
    P(2, 3, EYE_G);  P(5, 3, EYE_G)
    P(2, 3, EYE_B);  P(5, 3, EYE_B)   # pupils

    # Nose row 4
    P(3, 4, NOSE);  P(4, 4, WHITE)

    # Body rows 5-6
    for c in [1, 2, 3, 4, 5, 6]:
        P(c, 5, ORANGE)
        P(c, 6, ORANGE)
    P(1, 5, LIGHT);  P(2, 5, LIGHT)   # chest highlight
    P(3, 6, STRIPE); P(5, 6, STRIPE)  # belly stripes

    # Legs row 7
    P(1, 7, DARK);  P(2, 7, ORANGE)
    P(5, 7, ORANGE);P(6, 7, DARK)

    # Tail (right side, rows 2-5)
    P(7, 3, ORANGE);  P(7, 4, ORANGE)
    P(7, 5, DARK);    P(6, 2, STRIPE)

    return img


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

GENERATORS = {
    "robot.png": make_robot,
    "dirt.png":  make_dirt,
    "wall.png":  make_wall,
    "pet.png":   make_pet,
}


def generate_all(out_dir: str = "assets", size: int = 48):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    for filename, fn in GENERATORS.items():
        path = out / filename
        img  = fn(size)
        img.save(path, "PNG")
        print(f"  ✓  {path}  ({size}×{size}px)")

    print(f"\nAll {len(GENERATORS)} icons saved to '{out}'.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate pixel-art icons for Vacuum World.")
    parser.add_argument("--size", type=int, default=48, help="Icon size in pixels (default: 48)")
    parser.add_argument("--out",  type=str, default="assets", help="Output directory (default: assets/)")
    args = parser.parse_args()

    print(f"Generating {args.size}×{args.size} pixel-art icons → '{args.out}/'")
    generate_all(out_dir=args.out, size=args.size)

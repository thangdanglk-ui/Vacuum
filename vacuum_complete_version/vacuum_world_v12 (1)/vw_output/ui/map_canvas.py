"""
VacuumCanvas — Map canvas với PNG sprite support và smooth animation.
Tự động dùng PNG sprites nếu có trong assets/, fallback về vector nếu không.
"""
import tkinter as tk
import os
from map_generator import (WALL, FURNITURE, DUST, DUST2, DOCK, DOCK2, FLOOR, DOOR,
                            GRID_ROWS, GRID_COLS)

CELL_SIZE = 26
UNKNOWN   = -1

COLOR_FLOOR_DEFAULT = "#EDE4D3"
COLOR_FLOOR_LINE    = "#D8CBB5"
COLOR_WALL          = "#455A64"
COLOR_WALL_BRICK    = "#37474F"
COLOR_DUST_DOT      = "#9E9E9E"
COLOR_DOCK          = "#43A047"
COLOR_UNKNOWN       = "#1A1A2E"
COLOR_VISITED       = "#4FC3F7"

# Assets folder relative to this file
_ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")


def _load_sprite(name: str, size: int):
    """Load PNG sprite from assets/. Returns PhotoImage or None."""
    try:
        from PIL import Image, ImageTk
        path = os.path.join(_ASSETS_DIR, name)
        if os.path.exists(path):
            img = Image.open(path).convert("RGBA").resize((size, size), Image.LANCZOS)
            return ImageTk.PhotoImage(img)
    except ImportError:
        pass
    return None


class VacuumCanvas(tk.Canvas):
    def __init__(self, master, grid, dock, dust_cells,
                 rows=GRID_ROWS, cols=GRID_COLS,
                 room_info=None, furniture_map=None, door_info=None,
                 **kwargs):
        width  = cols * CELL_SIZE
        height = rows * CELL_SIZE
        super().__init__(master, width=width, height=height,
                         bg=COLOR_UNKNOWN, highlightthickness=0, **kwargs)
        self.grid_data      = grid
        self.dock           = dock
        self.rows           = rows
        self.cols           = cols
        self.room_info      = room_info or []
        self.furniture_map  = furniture_map or {}
        self.door_info      = {(r, c): orient for r, c, orient in (door_info or [])}

        self._floor_color   = self._build_floor_colors()
        self._drawn_anchors = set()

        self._cell_items    = {}
        self._robot_parts   = []
        self._robot2_parts  = []
        self._pet_parts     = []
        self._trail         = set()
        self.show_known     = False
        self.known_grid     = None

        # Load PNG sprites (None if Pillow not installed or file missing)
        cs = CELL_SIZE
        self._sprite_robot = _load_sprite("robot.png", cs)
        self._sprite_dirt  = _load_sprite("dirt.png",  cs)
        self._sprite_wall  = _load_sprite("wall.png",  cs)
        self._sprite_pet   = _load_sprite("pet.png",   cs)
        # Keep refs to prevent GC
        self._sprite_refs  = [self._sprite_robot, self._sprite_dirt,
                               self._sprite_wall, self._sprite_pet]

        self._draw_full()

    # ── Floor color map ─────────────────────────────────────────────
    def _build_floor_colors(self):
        colors = [[COLOR_FLOOR_DEFAULT]*self.cols for _ in range(self.rows)]
        for rtype, r1, c1, r2, c2, color in self.room_info:
            for r in range(r1+1, r2):
                for c in range(c1+1, c2):
                    colors[r][c] = color
        return colors

    # ── Draw full / unknown ─────────────────────────────────────────
    def _draw_full(self):
        self.delete("all")
        self._cell_items    = {}
        self._drawn_anchors = set()
        for r in range(self.rows):
            for c in range(self.cols):
                self._draw_cell(r, c, self.grid_data[r][c], known=True)

    def _draw_unknown_full(self):
        self.delete("all")
        self._cell_items    = {}
        self._drawn_anchors = set()
        for r in range(self.rows):
            for c in range(self.cols):
                self._draw_cell(r, c, UNKNOWN, known=False)
        # Sau khi xóa "all", các robot/pet parts đã bị xóa — reset để
        # move_robot / move_robot2 / draw_pet sẽ vẽ lại đúng sau đó
        self._robot_parts  = []
        self._robot2_parts = []
        self._pet_parts    = []

    def set_known_grid(self, known_grid):
        self.show_known = True
        self.known_grid = known_grid
        self._draw_unknown_full()
        self.refresh_known()

    def refresh_known(self):
        if not self.known_grid:
            return
        for r in range(self.rows):
            for c in range(self.cols):
                cell = self.known_grid[r][c]
                prev = self._cell_items.get((r, c))
                if prev is None or prev[1] != cell:
                    self._draw_cell(r, c, cell, known=(cell != UNKNOWN))

    # ── Draw individual cell ─────────────────────────────────────────
    def _draw_cell(self, r, c, cell, known=True):
        cs = CELL_SIZE
        x1, y1 = c*cs, r*cs
        x2, y2 = x1+cs, y1+cs
        cx, cy  = x1+cs//2, y1+cs//2

        # Clear existing items
        if (r, c) in self._cell_items:
            for item in self._cell_items[(r, c)][0]:
                self.delete(item)
            self._drawn_anchors.discard((r, c))

        items = []

        if not known or cell == UNKNOWN:
            items.append(self.create_rectangle(
                x1, y1, x2, y2, fill=COLOR_UNKNOWN, outline="#0D0D1A"))
            self._cell_items[(r, c)] = (items, UNKNOWN)
            return

        floor_color = self._floor_color[r][c]

        if cell == FLOOR:
            items += self._draw_floor(x1, y1, x2, y2, floor_color)

        elif cell == WALL:
            items += self._draw_wall(x1, y1, x2, y2, cs)

        elif cell == FURNITURE:
            items += self._draw_floor(x1, y1, x2, y2, floor_color)
            items += self._draw_furniture_piece(r, c, x1, y1, x2, y2)

        elif cell == DUST:
            items += self._draw_floor(x1, y1, x2, y2, floor_color)
            items += self._draw_dust(x1, y1, cx, cy)

        elif cell == DUST2:
            items += self._draw_floor(x1, y1, x2, y2, floor_color)
            items += self._draw_dust2(x1, y1, cx, cy)

        elif cell == DOCK:
            items += self._draw_dock(x1, y1, x2, y2, cx, cy)

        elif cell == DOCK2:
            items += self._draw_dock2(x1, y1, x2, y2, cx, cy)

        elif cell == DOOR:
            orient = self.door_info.get((r, c), 'h')
            items += self._draw_door(x1, y1, x2, y2, cx, cy, cs, orient)

        self._cell_items[(r, c)] = (items, cell)

    # ── Floor ────────────────────────────────────────────────────────
    def _draw_floor(self, x1, y1, x2, y2, color):
        cs = CELL_SIZE
        items = [self.create_rectangle(x1, y1, x2, y2,
                                       fill=color, outline=COLOR_FLOOR_LINE)]
        items.append(self.create_line(x1, y1+cs//3, x2, y1+cs//3,
                                      fill=COLOR_FLOOR_LINE, width=1))
        items.append(self.create_line(x1, y1+2*cs//3, x2, y1+2*cs//3,
                                      fill=COLOR_FLOOR_LINE, width=1))
        return items

    # ── Wall — PNG sprite or vector fallback ─────────────────────────
    def _draw_wall(self, x1, y1, x2, y2, cs):
        if self._sprite_wall:
            item = self.create_image(x1, y1, image=self._sprite_wall, anchor="nw")
            return [item]
        # Vector brick fallback
        items = [self.create_rectangle(x1, y1, x2, y2,
                                       fill=COLOR_WALL, outline=COLOR_WALL_BRICK)]
        bh = cs // 3
        for i, by in enumerate(range(y1, y2, bh)):
            items.append(self.create_line(x1, by, x2, by,
                                          fill=COLOR_WALL_BRICK, width=1))
            offset = (cs//2) if i % 2 == 0 else 0
            bx = x1 + offset
            if x1 < bx < x2:
                items.append(self.create_line(bx, by, bx, min(by+bh, y2),
                                              fill=COLOR_WALL_BRICK, width=1))
        return items

    # ── Dust — PNG sprite or vector fallback ─────────────────────────
    def _draw_dust(self, x1, y1, cx, cy):
        if self._sprite_dirt:
            item = self.create_image(x1, y1, image=self._sprite_dirt, anchor="nw")
            return [item]
        # Vector dots fallback
        items = []
        for dx, dy, r in [(-6,-5,2),(5,-3,1),(-3,4,2),(6,5,1),(0,1,2),
                           (-5,5,1),(4,-6,1)]:
            items.append(self.create_oval(
                cx+dx-r, cy+dy-r, cx+dx+r, cy+dy+r,
                fill=COLOR_DUST_DOT, outline=""))
        return items

    def _draw_dust2(self, x1, y1, cx, cy):
        # Green dust for Robot 2
        items = []
        for dx, dy, r in [(-6,-5,2),(5,-3,1),(-3,4,2),(6,5,1),(0,1,2),
                           (-5,5,1),(4,-6,1)]:
            items.append(self.create_oval(
                cx+dx-r, cy+dy-r, cx+dx+r, cy+dy+r,
                fill="#4CAF50", outline=""))
        return items

    # ── Dock ─────────────────────────────────────────────────────────
    def _draw_dock(self, x1, y1, x2, y2, cx, cy):
        items = [self.create_rectangle(x1, y1, x2, y2,
                                       fill=COLOR_DOCK, outline="#2E7D32", width=2)]
        items.append(self.create_polygon(
            cx+2, y1+3, cx-3, cy, cx+1, cy, cx-2, y2-3, cx+3, cy, cx-1, cy,
            fill="#FFF176", outline="#F9A825", width=1))
        return items

    def _draw_dock2(self, x1, y1, x2, y2, cx, cy):
        # Dock for Robot 2 (Green) - use cyan/teal color to distinguish
        items = [self.create_rectangle(x1, y1, x2, y2,
                                       fill="#009688", outline="#00695C", width=2)]
        items.append(self.create_polygon(
            cx+2, y1+3, cx-3, cy, cx+1, cy, cx-2, y2-3, cx+3, cy, cx-1, cy,
            fill="#E0F2F1", outline="#B2DFDB", width=1))
        return items

    # ── Door ─────────────────────────────────────────────────────────
    def _draw_door(self, x1, y1, x2, y2, cx, cy, cs, orient):
        items = []
        items.append(self.create_rectangle(x1, y1, x2, y2,
                                           fill="#D7CCC8", outline="#A1887F"))
        if orient == 'h':
            items.append(self.create_rectangle(x1, y1, x2, y1+3,
                                               fill="#6D4C41", outline=""))
            items.append(self.create_rectangle(x1, y2-3, x2, y2,
                                               fill="#6D4C41", outline=""))
            items.append(self.create_line(x1+2, y1+3, x1+2, y2-3,
                                          fill="#8D6E63", width=3))
            items.append(self.create_line(x1+2, y1+3, x2-4, y1+8,
                                          fill="#A1887F", width=3))
            items.append(self.create_oval(x2-7, cy-2, x2-3, cy+2,
                                          fill="#FFD54F", outline="#F9A825"))
        else:
            items.append(self.create_rectangle(x1, y1, x1+3, y2,
                                               fill="#6D4C41", outline=""))
            items.append(self.create_rectangle(x2-3, y1, x2, y2,
                                               fill="#6D4C41", outline=""))
            items.append(self.create_line(x1+3, y1+2, x2-3, y1+2,
                                          fill="#8D6E63", width=3))
            items.append(self.create_line(x1+3, y1+2, x1+8, y2-4,
                                          fill="#A1887F", width=3))
            items.append(self.create_oval(cx-2, y2-7, cx+2, y2-3,
                                          fill="#FFD54F", outline="#F9A825"))
        return items

    # ── Furniture ────────────────────────────────────────────────────
    def _draw_furniture_piece(self, r, c, x1, y1, x2, y2):
        info = self.furniture_map.get((r, c))
        if not info:
            return self._draw_generic_box(x1, y1, x2, y2)
        name, ar, ac, fw, fh = info
        if (ar, ac) != (r, c):
            return [self.create_rectangle(x1, y1, x2, y2,
                                          fill=self._furniture_base_color(name),
                                          outline="#5D4037")]
        cs = CELL_SIZE
        bx1, by1 = ac*cs, ar*cs
        bx2, by2 = bx1 + fw*cs, by1 + fh*cs
        drawer = self._FURNITURE_DRAWERS.get(name, self._draw_generic_furniture)
        items = drawer(self, bx1, by1, bx2, by2)
        self._drawn_anchors.add((r, c))
        return items

    def _furniture_base_color(self, name):
        return {
            "sofa":"#8D6E63","bed":"#90A4AE","wardrobe":"#795548",
            "tv":"#263238","fridge":"#ECEFF1","stove":"#424242",
            "counter":"#A1887F","sink":"#B0BEC5","bathtub":"#E1F5FE",
            "toilet":"#FAFAFA","washer":"#CFD8DC","dryer":"#CFD8DC",
            "desk":"#8D6E63","nightstand":"#795548","bookshelf":"#6D4C41",
            "coffee_table":"#A1887F","dining_table":"#A1887F","shelf":"#8D6E63",
        }.get(name, "#A1887F")

    def _draw_generic_box(self, x1, y1, x2, y2):
        return [self.create_rectangle(x1+2, y1+2, x2-2, y2-2,
                                      fill="#A1887F", outline="#5D4037")]

    def _draw_generic_furniture(self, x1, y1, x2, y2):
        return [self.create_rectangle(x1+2, y1+2, x2-2, y2-2,
                                      fill="#A1887F", outline="#5D4037", width=1)]

    def _draw_sofa(self, x1, y1, x2, y2):
        items = [self.create_rectangle(x1+2, y1+2, x2-2, y2-2, fill="#8D6E63", outline="#5D4037")]
        items.append(self.create_rectangle(x1+2, y1+2, x2-2, y1+8, fill="#6D4C41", outline=""))
        w = (x2-x1)//3
        for i in range(min(3, (x2-x1)//w if w else 1)):
            gx = x1 + 4 + i*w
            items.append(self.create_rectangle(gx, y1+9, gx+w-4, y1+16, fill="#A1887F", outline="#6D4C41"))
        for fx in [x1+3, x2-6]:
            items.append(self.create_rectangle(fx, y2-3, fx+3, y2, fill="#3E2723", outline=""))
        return items

    def _draw_bed(self, x1, y1, x2, y2):
        items = [self.create_rectangle(x1+1, y1+1, x2-1, y2-1, fill="#90A4AE", outline="#546E7A")]
        items.append(self.create_rectangle(x1+1, y1+1, x2-1, y1+10, fill="#78909C", outline="#546E7A"))
        pw = (x2-x1-8)//2
        items.append(self.create_rectangle(x1+4, y1+3, x1+4+pw, y1+8, fill="#ECEFF1", outline="#CFD8DC"))
        items.append(self.create_rectangle(x2-4-pw, y1+3, x2-4, y1+8, fill="#ECEFF1", outline="#CFD8DC"))
        items.append(self.create_rectangle(x1+1, y1+12, x2-1, y2-1, fill="#B0BEC5", outline="#90A4AE"))
        items.append(self.create_line(x1+1, (y1+y2)//2, x2-1, (y1+y2)//2, fill="#90A4AE", width=1))
        return items

    def _draw_wardrobe(self, x1, y1, x2, y2):
        items = [self.create_rectangle(x1+1, y1+1, x2-1, y2-1, fill="#795548", outline="#4E342E")]
        midx = (x1+x2)//2
        items.append(self.create_line(midx, y1+1, midx, y2-1, fill="#4E342E", width=1))
        for hx in [midx-4, midx+4]:
            items.append(self.create_oval(hx-1, (y1+y2)//2-2, hx+1, (y1+y2)//2+2, fill="#D7CCC8", outline=""))
        return items

    def _draw_tv(self, x1, y1, x2, y2):
        items = [self.create_rectangle(x1+1, y1+1, x2-1, y2-5, fill="#212121", outline="#000")]
        items.append(self.create_rectangle(x1+3, y1+3, x2-3, y2-7, fill="#37474F", outline=""))
        midx = (x1+x2)//2
        items.append(self.create_rectangle(midx-3, y2-5, midx+3, y2-1, fill="#424242", outline=""))
        return items

    def _draw_fridge(self, x1, y1, x2, y2):
        items = [self.create_rectangle(x1+1, y1+1, x2-1, y2-1, fill="#ECEFF1", outline="#B0BEC5")]
        midy = y1 + (y2-y1)//3
        items.append(self.create_line(x1+1, midy, x2-1, midy, fill="#B0BEC5", width=1))
        items.append(self.create_rectangle(x2-4, y1+3, x2-2, y1+7, fill="#90A4AE", outline=""))
        items.append(self.create_rectangle(x2-4, midy+3, x2-2, midy+9, fill="#90A4AE", outline=""))
        return items

    def _draw_stove(self, x1, y1, x2, y2):
        items = [self.create_rectangle(x1+1, y1+1, x2-1, y2-1, fill="#424242", outline="#212121")]
        cx, cy = (x1+x2)//2, (y1+y2)//2
        items.append(self.create_oval(cx-6, cy-6, cx-1, cy-1, fill="#616161", outline="#000"))
        items.append(self.create_oval(cx+1, cy-6, cx+6, cy-1, fill="#616161", outline="#000"))
        return items

    def _draw_counter(self, x1, y1, x2, y2):
        items = [self.create_rectangle(x1+1, y1+1, x2-1, y2-1, fill="#A1887F", outline="#6D4C41")]
        items.append(self.create_rectangle(x1+1, y1+1, x2-1, y1+4, fill="#D7CCC8", outline=""))
        return items

    def _draw_sink(self, x1, y1, x2, y2):
        items = [self.create_rectangle(x1+1, y1+1, x2-1, y2-1, fill="#CFD8DC", outline="#90A4AE")]
        cx, cy = (x1+x2)//2, (y1+y2)//2
        items.append(self.create_oval(x1+4, y1+4, x2-4, y2-6, fill="#B0BEC5", outline="#78909C"))
        items.append(self.create_line(cx, y1+2, cx, y1+5, fill="#607D8B", width=2))
        return items

    def _draw_bathtub(self, x1, y1, x2, y2):
        items = [self.create_rectangle(x1+1, y1+1, x2-1, y2-1, fill="#E1F5FE", outline="#4FC3F7", width=2)]
        items.append(self.create_oval(x1+3, y1+3, x2-3, y2-3, fill="#FFFFFF", outline="#81D4FA"))
        return items

    def _draw_toilet(self, x1, y1, x2, y2):
        cx, cy = (x1+x2)//2, (y1+y2)//2
        items = [self.create_rectangle(x1+3, y1+1, x2-3, y1+6, fill="#FAFAFA", outline="#BDBDBD")]
        items.append(self.create_oval(x1+2, y1+5, x2-2, y2-1, fill="#FFFFFF", outline="#BDBDBD", width=2))
        items.append(self.create_oval(x1+5, y1+8, x2-5, y2-4, fill="#E0E0E0", outline=""))
        return items

    def _draw_washer(self, x1, y1, x2, y2):
        items = [self.create_rectangle(x1+1, y1+1, x2-1, y2-1, fill="#CFD8DC", outline="#90A4AE")]
        cx, cy = (x1+x2)//2, (y1+y2)//2+1
        r = min(x2-x1, y2-y1)//2 - 3
        items.append(self.create_oval(cx-r, cy-r, cx+r, cy+r, fill="#37474F", outline="#90A4AE", width=2))
        items.append(self.create_oval(cx-r+3, cy-r+3, cx+r-3, cy+r-3, fill="#546E7A", outline=""))
        items.append(self.create_oval(x1+3, y1+2, x1+6, y1+5, fill="#FFD54F", outline=""))
        return items

    def _draw_dryer(self, x1, y1, x2, y2):
        items = [self.create_rectangle(x1+1, y1+1, x2-1, y2-1, fill="#D7CCC8", outline="#A1887F")]
        cx, cy = (x1+x2)//2, (y1+y2)//2+1
        r = min(x2-x1, y2-y1)//2 - 3
        items.append(self.create_oval(cx-r, cy-r, cx+r, cy+r, fill="#6D4C41", outline="#A1887F", width=2))
        items.append(self.create_oval(cx-r+3, cy-r+3, cx+r-3, cy+r-3, fill="#8D6E63", outline=""))
        items.append(self.create_oval(x1+3, y1+2, x1+6, y1+5, fill="#EF5350", outline=""))
        return items

    def _draw_table(self, x1, y1, x2, y2):
        items = [self.create_rectangle(x1+1, y1+1, x2-1, y2-1, fill="#A1887F", outline="#6D4C41")]
        items.append(self.create_rectangle(x1+2, y1+2, x2-2, y1+5, fill="#BCAAA4", outline=""))
        for fx, fy in [(x1+2,y1+2),(x2-5,y1+2),(x1+2,y2-5),(x2-5,y2-5)]:
            items.append(self.create_rectangle(fx, fy, fx+3, fy+3, fill="#5D4037", outline=""))
        return items

    def _draw_shelf_box(self, x1, y1, x2, y2):
        items = [self.create_rectangle(x1+1, y1+1, x2-1, y2-1, fill="#6D4C41", outline="#4E342E")]
        n = 3
        h = (y2-y1-2) / n
        for i in range(1, n):
            yy = y1 + 1 + int(i*h)
            items.append(self.create_line(x1+1, yy, x2-1, yy, fill="#4E342E", width=1))
        for i, bx in enumerate(range(x1+3, x2-3, 4)):
            items.append(self.create_rectangle(bx, y1+3, bx+2, y1+int(h)-2,
                fill=["#EF5350","#42A5F5","#66BB6A","#FFCA28"][i%4], outline=""))
        return items

    def _draw_nightstand(self, x1, y1, x2, y2):
        items = [self.create_rectangle(x1+1, y1+1, x2-1, y2-1, fill="#795548", outline="#4E342E")]
        items.append(self.create_rectangle(x1+3, y1+3, x2-3, y1+8, fill="#8D6E63", outline="#4E342E"))
        items.append(self.create_oval((x1+x2)//2-1, y1+5, (x1+x2)//2+1, y1+7, fill="#D7CCC8", outline=""))
        return items

    def _draw_plant(self, x1, y1, x2, y2):
        items = []
        cx = (x1+x2)//2
        items.append(self.create_polygon(
            x1+3, y2-2, x2-3, y2-2, x2-5, y1+int((y2-y1)*0.6), x1+5, y1+int((y2-y1)*0.6),
            fill="#A1887F", outline="#6D4C41"))
        leaf_y = y1 + int((y2-y1)*0.45)
        items.append(self.create_oval(cx-7, leaf_y-9, cx+1, leaf_y-1, fill="#66BB6A", outline="#388E3C"))
        items.append(self.create_oval(cx-1, leaf_y-9, cx+7, leaf_y-1, fill="#81C784", outline="#388E3C"))
        items.append(self.create_oval(cx-4, leaf_y-13, cx+4, leaf_y-5, fill="#4CAF50", outline="#388E3C"))
        return items

    def _draw_lamp(self, x1, y1, x2, y2):
        cx = (x1+x2)//2
        items = [self.create_line(cx, y1+4, cx, y2-2, fill="#5D4037", width=2)]
        items.append(self.create_oval(cx-4, y2-4, cx+4, y2-1, fill="#4E342E", outline=""))
        items.append(self.create_polygon(cx-6, y1+4, cx+6, y1+4, cx+4, y1, cx-4, y1,
                                         fill="#FFF176", outline="#FBC02D"))
        return items

    def _draw_rug(self, x1, y1, x2, y2):
        items = [self.create_rectangle(x1+1, y1+1, x2-1, y2-1, fill="#EF9A9A", outline="#C62828")]
        items.append(self.create_rectangle(x1+5, y1+5, x2-5, y2-5, fill="", outline="#FFCDD2"))
        items.append(self.create_rectangle(x1+9, y1+9, x2-9, y2-9, fill="", outline="#FFCDD2"))
        return items

    def _draw_armchair(self, x1, y1, x2, y2):
        items = [self.create_rectangle(x1+2, y1+4, x2-2, y2-2, fill="#FF8A65", outline="#D84315")]
        items.append(self.create_rectangle(x1+2, y1+1, x2-2, y1+6, fill="#FFAB91", outline="#D84315"))
        items.append(self.create_rectangle(x1, y1+5, x1+3, y2-2, fill="#FFAB91", outline="#D84315"))
        items.append(self.create_rectangle(x2-3, y1+5, x2, y2-2, fill="#FFAB91", outline="#D84315"))
        return items

    def _draw_mirror(self, x1, y1, x2, y2):
        cx, cy = (x1+x2)//2, (y1+y2)//2
        items = [self.create_oval(x1+1, y1+1, x2-1, y2-1, fill="#B3E5FC", outline="#90A4AE", width=2)]
        items.append(self.create_line(cx-3, cy-3, cx+2, cy+2, fill="#FFFFFF", width=1))
        return items

    def _draw_basket(self, x1, y1, x2, y2):
        items = [self.create_polygon(x1+2, y1+3, x2-2, y1+3, x2-3, y2-1, x1+3, y2-1,
                                     fill="#FFCC80", outline="#EF6C00")]
        items.append(self.create_line(x1+2, y1+3, x2-2, y1+3, fill="#E65100", width=1))
        items.append(self.create_arc(x1+3, y1-2, x2-3, y1+5, start=0, extent=180,
                                     outline="#EF6C00", width=2, style="arc"))
        return items

    def _draw_chair(self, x1, y1, x2, y2):
        items = [self.create_rectangle(x1+3, y1+5, x2-3, y2-3, fill="#A1887F", outline="#5D4037")]
        items.append(self.create_rectangle(x1+3, y1+1, x2-3, y1+5, fill="#8D6E63", outline="#5D4037"))
        for fx in [x1+3, x2-5]:
            items.append(self.create_rectangle(fx, y2-3, fx+2, y2, fill="#3E2723", outline=""))
        return items

    _FURNITURE_DRAWERS = {
        "sofa": _draw_sofa, "bed": _draw_bed, "wardrobe": _draw_wardrobe,
        "tv": _draw_tv, "fridge": _draw_fridge, "stove": _draw_stove,
        "counter": _draw_counter, "sink": _draw_sink, "bathtub": _draw_bathtub,
        "toilet": _draw_toilet, "washer": _draw_washer, "dryer": _draw_dryer,
        "coffee_table": _draw_table, "dining_table": _draw_table, "desk": _draw_table,
        "bookshelf": _draw_shelf_box, "shelf": _draw_shelf_box,
        "nightstand": _draw_nightstand, "plant": _draw_plant, "lamp": _draw_lamp,
        "rug": _draw_rug, "armchair": _draw_armchair, "mirror": _draw_mirror,
        "basket": _draw_basket, "chair": _draw_chair,
    }

    # ── Trail ────────────────────────────────────────────────────────
    def mark_visited(self, pos):
        """Trail bị tắt theo yêu cầu (không muốn hiện ô nước cyan)."""
        pass

    def flash_backtrack(self, pos):
        """Nháy đỏ ô vừa backtrack — hiệu ứng CSP quay lui."""
        if pos is None:
            return
        cs = CELL_SIZE
        r, c = pos
        x1, y1 = c*cs, r*cs
        x2, y2 = x1+cs, y1+cs
        flash = self.create_rectangle(x1+1, y1+1, x2-1, y2-1,
                                       fill="#F38BA8", outline="", tags="flash")
        self.tag_raise(flash)
        self.after(150, lambda: self.delete(flash))

    def update_cell_after_vacuum(self, pos):
        r, c = pos
        if self.show_known and self.known_grid:
            self.known_grid[r][c] = FLOOR
        self.grid_data[r][c] = FLOOR
        self._draw_cell(r, c, FLOOR, known=True)

    # ── Robot 1 (tím — vector) ───────────────────────────────────────
    def _draw_robot(self, cx, cy, battery_ratio):
        parts = []
        cs  = CELL_SIZE
        rad = cs//2 - 2
        # Thân tròn
        parts.append(self.create_oval(
            cx-rad, cy-rad, cx+rad, cy+rad,
            fill="#7E57C2", outline="#4527A0", width=2))
        # Mắt cảm biến
        parts.append(self.create_oval(
            cx-3, cy-3, cx+3, cy+3, fill="#E1BEE7", outline=""))
        # Vòng pin
        bcolor = ("#66BB6A" if battery_ratio > 0.5 else
                  "#FFA726" if battery_ratio > 0.2 else "#EF5350")
        extent = max(1, int(360 * battery_ratio))
        parts.append(self.create_arc(
            cx-rad-3, cy-rad-3, cx+rad+3, cy+rad+3,
            start=90, extent=-extent,
            outline=bcolor, width=3, style="arc"))
        for p in parts:
            self.tag_raise(p)
        return parts

    def move_robot(self, pos, battery_ratio):
        for item in self._robot_parts:
            self.delete(item)
        cs = CELL_SIZE
        r, c = pos
        self._robot_parts = self._draw_robot(c*cs+cs//2, r*cs+cs//2, battery_ratio)

    def move_robot_smooth(self, from_pos, to_pos, battery_ratio,
                          steps=6, delay=12, on_done=None):
        cs = CELL_SIZE
        x0 = from_pos[1]*cs+cs//2; y0 = from_pos[0]*cs+cs//2
        x1 = to_pos[1]*cs+cs//2;   y1 = to_pos[0]*cs+cs//2
        dx, dy = (x1-x0)/steps, (y1-y0)/steps

        def _step(i, cx, cy):
            for item in self._robot_parts:
                self.delete(item)
            self._robot_parts = self._draw_robot(int(cx), int(cy), battery_ratio)
            if i < steps:
                self.after(delay, lambda: _step(i+1, cx+dx, cy+dy))
            else:
                if on_done:
                    on_done()
        _step(0, x0, y0)

    # ── Robot 2 (xanh lá — Complex Environment dual mode) ───────────
    def _draw_robot2(self, cx, cy, battery_ratio):
        parts = []
        cs  = CELL_SIZE
        rad = cs//2 - 2
        parts.append(self.create_oval(
            cx-rad, cy-rad, cx+rad, cy+rad,
            fill="#00897B", outline="#004D40", width=2))
        parts.append(self.create_oval(
            cx-3, cy-3, cx+3, cy+3, fill="#B2DFDB", outline=""))
        bcolor = ("#66BB6A" if battery_ratio > 0.5 else
                  "#FFA726" if battery_ratio > 0.2 else "#EF5350")
        extent = max(1, int(360 * battery_ratio))
        parts.append(self.create_arc(
            cx-rad-3, cy-rad-3, cx+rad+3, cy+rad+3,
            start=90, extent=-extent,
            outline=bcolor, width=3, style="arc"))
        for p in parts:
            self.tag_raise(p)
        return parts

    def move_robot2(self, pos, battery_ratio):
        for item in self._robot2_parts:
            self.delete(item)
        cs = CELL_SIZE
        r, c = pos
        self._robot2_parts = self._draw_robot2(c*cs+cs//2, r*cs+cs//2, battery_ratio)

    def move_robot2_smooth(self, from_pos, to_pos, battery_ratio,
                           steps=6, delay=12, on_done=None):
        cs = CELL_SIZE
        x0 = from_pos[1]*cs+cs//2; y0 = from_pos[0]*cs+cs//2
        x1 = to_pos[1]*cs+cs//2;   y1 = to_pos[0]*cs+cs//2
        dx, dy = (x1-x0)/steps, (y1-y0)/steps

        def _step(i, cx, cy):
            for item in self._robot2_parts:
                self.delete(item)
            self._robot2_parts = self._draw_robot2(int(cx), int(cy), battery_ratio)
            if i < steps:
                self.after(delay, lambda: _step(i+1, cx+dx, cy+dy))
            else:
                if on_done:
                    on_done()
        _step(0, x0, y0)

    # ── Pet — PNG sprite or vector fallback ──────────────────────────
    def _draw_cat_at(self, cx, cy):
        parts = []
        cs = CELL_SIZE
        if self._sprite_pet:
            half = cs // 2
            item = self.create_image(cx - half, cy - half,
                                     image=self._sprite_pet, anchor="nw")
            parts.append(item)
        else:
            # Vector cat fallback
            s = cs // 2
            parts.append(self.create_oval(cx-s, cy-s, cx+s, cy+s,
                                          fill="#FFCDD2", outline="#E53935", width=1))
            bw, bh = int(s*0.9), int(s*0.55)
            parts.append(self.create_oval(cx-bw, cy-bh, cx+bw, cy+bh,
                                          fill="#FF8A65", outline="#E64A19", width=1))
            hw, hh = int(s*0.55), int(s*0.5)
            hy = cy - int(s*0.3)
            parts.append(self.create_oval(cx-hw, hy-hh, cx+hw, hy+hh,
                                          fill="#FF8A65", outline="#E64A19", width=1))
            parts.append(self.create_polygon(
                cx-hw+2, hy-hh+4, cx-hw-6, hy-hh-8, cx-hw+10, hy-hh+2,
                fill="#FF8A65", outline="#E64A19", width=1))
            parts.append(self.create_polygon(
                cx+hw-2, hy-hh+4, cx+hw+6, hy-hh-8, cx+hw-10, hy-hh+2,
                fill="#FF8A65", outline="#E64A19", width=1))
            ey = hy - 2
            parts.append(self.create_oval(cx-int(hw*0.45)-2, ey-2,
                                          cx-int(hw*0.45)+2, ey+2, fill="#1A1A1A", outline=""))
            parts.append(self.create_oval(cx+int(hw*0.45)-2, ey-2,
                                          cx+int(hw*0.45)+2, ey+2, fill="#1A1A1A", outline=""))
            parts.append(self.create_oval(cx-2, hy+2, cx+2, hy+5, fill="#E91E63", outline=""))
        for p in parts:
            self.tag_raise(p)
        return parts

    def draw_pet(self, pos, symbol="cat"):
        for item in self._pet_parts:
            self.delete(item)
        self._pet_parts = []
        if pos is None:
            return
        cs = CELL_SIZE
        r, c = pos
        self._pet_parts = self._draw_cat_at(c*cs+cs//2, r*cs+cs//2)

    def move_pet_smooth(self, from_pos, to_pos, steps=5, delay=10, on_done=None):
        cs = CELL_SIZE
        x0 = from_pos[1]*cs+cs//2; y0 = from_pos[0]*cs+cs//2
        x1 = to_pos[1]*cs+cs//2;   y1 = to_pos[0]*cs+cs//2
        dx, dy = (x1-x0)/steps, (y1-y0)/steps

        def _step(i, cx, cy):
            for item in self._pet_parts:
                self.delete(item)
            self._pet_parts = self._draw_cat_at(int(cx), int(cy))
            if i < steps:
                self.after(delay, lambda: _step(i+1, cx+dx, cy+dy))
            else:
                if on_done:
                    on_done()
        _step(0, x0, y0)

    def clear_pet(self):
        for item in self._pet_parts:
            self.delete(item)
        self._pet_parts = []

    # ── Reset ─────────────────────────────────────────────────────────
    def reset_display(self):
        self.delete("all")
        self._cell_items    = {}
        self._robot_parts   = []
        self._robot2_parts  = []
        self._pet_parts     = []
        self._trail         = set()
        self.show_known     = False
        self.known_grid     = None
        self._floor_color   = self._build_floor_colors()
        self._drawn_anchors = set()
        self._draw_full()

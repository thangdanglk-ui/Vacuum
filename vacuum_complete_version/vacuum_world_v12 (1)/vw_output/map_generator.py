import random
from collections import deque

FLOOR     = 0
WALL      = 1
FURNITURE = 2
DUST      = 3
DOCK      = 4
DOOR      = 5
DUST2     = 6
DOCK2     = 7

GRID_ROWS      = 24
GRID_COLS      = 28
BATTERY_MAX    = 150
DUST_COUNT     = 15
PARTIAL_RADIUS = 2

ROOM_TYPES = ["living", "bedroom", "kitchen", "bathroom", "laundry"]
ROOM_COLORS = {
    "living":  "#F5ECD7",
    "bedroom": "#E8D5F0",
    "kitchen": "#D7ECD7",
    "bathroom":"#D7E8EC",
    "laundry": "#EDE9D7",
}
ROOM_NAMES_VN = {
    "living":  "Phòng khách",
    "bedroom": "Phòng ngủ",
    "kitchen": "Phòng bếp",
    "bathroom":"Phòng tắm",
    "laundry": "Phòng giặt",
}

# (tên đồ vật, width, height) — width/height tính theo số ô
ROOM_FURNITURE = {
    "living":  [("sofa",3,1), ("coffee_table",2,1), ("tv",2,1), ("bookshelf",1,2),
                ("armchair",1,1), ("plant",1,1), ("rug",2,2), ("lamp",1,1)],
    "bedroom": [("bed",2,3), ("wardrobe",1,2), ("desk",2,1), ("nightstand",1,1),
                ("plant",1,1), ("rug",2,2), ("lamp",1,1), ("mirror",1,1)],
    "kitchen": [("counter",3,1), ("fridge",1,2), ("stove",1,1), ("sink",1,1),
                ("dining_table",2,2), ("chair",1,1), ("chair",1,1), ("plant",1,1)],
    "bathroom":[("bathtub",2,1), ("toilet",1,1), ("sink",1,1),
                ("mirror",1,1), ("plant",1,1)],
    "laundry": [("washer",1,1), ("dryer",1,1), ("shelf",2,1),
                ("basket",1,1), ("plant",1,1)],
}

# Đồ vật trang trí nhỏ (luôn cố thêm vào để lấp khoảng trống)
DECOR_ITEMS = ["plant", "lamp", "rug", "armchair", "mirror", "basket"]


def generate_map(rows=GRID_ROWS, cols=GRID_COLS, seed=None):
    if seed is not None:
        random.seed(seed)
    for attempt in range(30):
        grid, room_info, furniture_map, door_info = _build_rooms(rows, cols)
        dock = _find_dock(grid, rows, cols)
        grid[dock[0]][dock[1]] = DOCK

        floors = [(r, c) for r in range(rows) for c in range(cols)
                  if grid[r][c] == FLOOR]
        if len(floors) < DUST_COUNT + 5:
            continue

        dust_cells = random.sample(floors, DUST_COUNT)
        for r, c in dust_cells:
            grid[r][c] = DUST

        if _all_reachable(grid, dock, dust_cells, rows, cols):
            return (grid, dock, list(dust_cells), room_info,
                    furniture_map, door_info)

    return _simple_fallback(rows, cols)


def generate_map_dual(rows=GRID_ROWS, cols=GRID_COLS, seed=None):
    """Như generate_map nhưng đặt nhiều bụi hơn (DUST_COUNT * 2)
    để đủ cho 2 máy hút bụi chạy song song (Complex Environment)."""
    if seed is not None:
        random.seed(seed)
    for attempt in range(30):
        grid, room_info, furniture_map, door_info = _build_rooms(rows, cols)
        dock1 = _find_dock(grid, rows, cols)
        grid[dock1[0]][dock1[1]] = DOCK
        
        dock2 = _find_dock2(grid, rows, cols, dock1)
        grid[dock2[0]][dock2[1]] = DOCK2

        floors = [(r, c) for r in range(rows) for c in range(cols)
                  if grid[r][c] == FLOOR]
        if len(floors) < DUST_COUNT * 2 + 5:
            continue

        dust_cells_all = random.sample(floors, DUST_COUNT * 2)
        dust1 = dust_cells_all[:DUST_COUNT]
        dust2 = dust_cells_all[DUST_COUNT:]
        for r, c in dust1:
            grid[r][c] = DUST
        for r, c in dust2:
            grid[r][c] = DUST2

        if _all_reachable(grid, dock1, dust_cells_all, rows, cols) and _all_reachable(grid, dock2, dust_cells_all, rows, cols):
            return (grid, (dock1, dock2), (list(dust1), list(dust2)), room_info,
                    furniture_map, door_info)

    grid, dock1, dust_cells, room_info, furniture_map, door_info = _simple_fallback(rows, cols)
    dock2 = _find_dock2(grid, rows, cols, dock1)
    grid[dock2[0]][dock2[1]] = DOCK2
    half = len(dust_cells) // 2
    dust1 = dust_cells[:half]
    dust2 = dust_cells[half:]
    for r, c in dust2:
        grid[r][c] = DUST2
    return grid, (dock1, dock2), (list(dust1), list(dust2)), room_info, furniture_map, door_info

def _find_dock(grid, rows, cols):
    for r in range(1, rows):
        for c in range(1, cols):
            if grid[r][c] == FLOOR:
                return (r, c)
    return (1, 1)

def _find_dock2(grid, rows, cols, dock1):
    for r in range(rows-2, 0, -1):
        for c in range(cols-2, 0, -1):
            if grid[r][c] == FLOOR and (r, c) != dock1:
                return (r, c)
    return dock1


def _build_rooms(rows, cols):
    grid = [[WALL]*cols for _ in range(rows)]
    room_info     = []
    furniture_map = {}   # (r,c) -> (name, anchor_r, anchor_c, w, h)

    rooms = _make_room_layout(rows, cols)

    for i, (r1, c1, r2, c2) in enumerate(rooms):
        rtype = ROOM_TYPES[i % len(ROOM_TYPES)]
        color = ROOM_COLORS[rtype]
        room_info.append((rtype, r1, c1, r2, c2, color))
        for r in range(r1+1, r2):
            for c in range(c1+1, c2):
                grid[r][c] = FLOOR
        _place_furniture(grid, rtype, r1, c1, r2, c2, furniture_map)

    door_info = _place_doors(grid, rooms, rows, cols)
    return grid, room_info, furniture_map, door_info


def _make_room_layout(rows, cols):
    R, C = rows - 1, cols - 1
    n    = random.randint(4, 6)

    # Đảm bảo mid_r / mid_c chia 2 phần đều đủ lớn (>=6 ô mỗi bên)
    # để không phòng nào bị loại vì quá nhỏ, tránh để trống map.
    min_half_r = 6
    min_half_c = 7
    if R - 2*min_half_r < 1:
        mid_r = R // 2
    else:
        mid_r = random.randint(min_half_r, R - min_half_r)
    if C - 2*min_half_c < 1:
        mid_c = C // 2
    else:
        mid_c = random.randint(min_half_c, C - min_half_c)

    if n <= 4:
        rooms = [
            (0, 0, mid_r, mid_c),
            (0, mid_c, mid_r, C),
            (mid_r, 0, R, mid_c),
            (mid_r, mid_c, R, C),
        ]
    elif n == 5:
        # mid_c2 phải chừa đủ chỗ cho cả 2 bên (>=5 ô)
        lo = mid_c + 5
        hi = C - 5
        mid_c2 = random.randint(lo, hi) if hi > lo else (mid_c + (C-mid_c)//2)
        rooms = [
            (0, 0, mid_r, mid_c),
            (0, mid_c, mid_r, mid_c2),
            (0, mid_c2, mid_r, C),
            (mid_r, 0, R, mid_c),
            (mid_r, mid_c, R, C),
        ]
    else:
        lo_c = mid_c + 5
        hi_c = C - 5
        mid_c2 = random.randint(lo_c, hi_c) if hi_c > lo_c else (mid_c + (C-mid_c)//2)
        lo_r = mid_r + 5
        hi_r = R - 4
        mid_r2 = random.randint(lo_r, hi_r) if hi_r > lo_r else (mid_r + (R-mid_r)//2)
        rooms = [
            (0, 0, mid_r, mid_c),
            (0, mid_c, mid_r, C),
            (mid_r, 0, mid_r2, mid_c),
            (mid_r, mid_c, mid_r2, C),
            (mid_r2, 0, R, mid_c2),
            (mid_r2, mid_c2, R, C),
        ]

    valid = [(r1,c1,r2,c2) for r1,c1,r2,c2 in rooms
             if (r2-r1) >= 5 and (c2-c1) >= 5]

    # Fallback an toàn: nếu vẫn có phòng bị loại (hiếm), dùng layout 4 phòng cố định
    # chia đúng giữa map để đảm bảo phủ kín toàn bộ diện tích.
    if len(valid) < n:
        safe_mid_r = R // 2
        safe_mid_c = C // 2
        valid = [
            (0, 0, safe_mid_r, safe_mid_c),
            (0, safe_mid_c, safe_mid_r, C),
            (safe_mid_r, 0, R, safe_mid_c),
            (safe_mid_r, safe_mid_c, R, C),
        ]

    return valid


def _place_furniture(grid, rtype, r1, c1, r2, c2, furniture_map):
    """Bố trí đồ vật theo logic thực tế cho từng loại phòng, thay vì random
    hoàn toàn. Mỗi loại phòng có 'kịch bản' sắp đặt riêng:
    - Phòng khách: sofa dựa 1 cạnh tường, bàn cà phê ngay trước sofa, TV ở
      tường đối diện sofa (để sofa "nhìn" về phía TV).
    - Phòng ngủ: giường luôn dựa sát 1 cạnh tường (đầu giường áp tường),
      tủ quần áo đặt ở góc phòng, bàn làm việc dựa tường còn lại.
    - Phòng bếp: quầy bếp + bếp nấu + tủ lạnh dọc theo 1 cạnh tường (bố cục
      bếp chữ I), bàn ăn đặt giữa phòng với ghế quanh.
    - Phòng tắm: bồn tắm dựa tường dài nhất, bồn cầu + bồn rửa ở góc còn lại.
    - Phòng giặt: máy giặt/sấy đặt cạnh nhau sát tường.
    Sau kịch bản chính, các món trang trí nhỏ (cây, đèn, thảm...) được rải
    bổ sung vào khoảng trống còn lại, tránh chắn lối đi.
    """
    room_h = r2 - r1 - 1
    room_w = c2 - c1 - 1
    if room_h < 3 or room_w < 3:
        return

    dispatch = {
        "living":   _layout_living,
        "bedroom":  _layout_bedroom,
        "kitchen":  _layout_kitchen,
        "bathroom": _layout_bathroom,
        "laundry":  _layout_laundry,
    }
    layout_fn = dispatch.get(rtype)
    if layout_fn:
        layout_fn(grid, r1, c1, r2, c2, furniture_map)

    room_area = room_h * room_w
    _place_decor_filler(grid, r1, c1, r2, c2, furniture_map, room_area)


def _can_place(grid, fr, fc, fw, fh, r2, c2):
    return (fr+fh-1 < r2 and fc+fw-1 < c2 and
            all(grid[r][c] == FLOOR
                for r in range(fr, fr+fh)
                for c in range(fc, fc+fw)))


def _put(grid, furniture_map, name, fr, fc, fw, fh):
    for r in range(fr, fr+fh):
        for c in range(fc, fc+fw):
            grid[r][c] = FURNITURE
            furniture_map[(r, c)] = (name, fr, fc, fw, fh)


def _pick_wall_side(room_h, room_w):
    """Chọn ngẫu nhiên 1 trong 4 cạnh tường để làm 'cạnh chính' bố trí đồ
    lớn — mô phỏng việc mỗi phòng thật có 1 hướng kê đồ chủ đạo."""
    return random.choice(["top", "bottom", "left", "right"])


def _layout_living(grid, r1, c1, r2, c2, furniture_map):
    """Sofa dựa 1 cạnh tường, bàn cà phê ngay phía trước sofa,
    TV đặt ở cạnh tường đối diện — để sofa hướng mặt vào TV."""
    room_h, room_w = r2-r1-1, c2-c1-1
    side = _pick_wall_side(room_h, room_w)
    opposite = {"top":"bottom", "bottom":"top", "left":"right", "right":"left"}[side]

    sofa_len = min(3, room_w if side in ("top","bottom") else room_h)
    sofa_len = max(2, sofa_len)

    # Đặt sofa dựa cạnh `side`, nằm ngang nếu top/bottom, dọc nếu left/right
    if side == "top":
        fr, fc = r1+1, random.randint(c1+1, max(c1+1, c2-sofa_len))
        fw, fh = sofa_len, 1
    elif side == "bottom":
        fr, fc = r2-1, random.randint(c1+1, max(c1+1, c2-sofa_len))
        fw, fh = sofa_len, 1
    elif side == "left":
        fr, fc = random.randint(r1+1, max(r1+1, r2-sofa_len)), c1+1
        fw, fh = 1, sofa_len
    else:
        fr, fc = random.randint(r1+1, max(r1+1, r2-sofa_len)), c2-1
        fw, fh = 1, sofa_len

    if _can_place(grid, fr, fc, fw, fh, r2, c2):
        _put(grid, furniture_map, "sofa", fr, fc, fw, fh)

        # Bàn cà phê ngay phía trước sofa (cách 1 ô để chừa lối đi)
        if side == "top":
            tfr, tfc = fr+2, fc
            tfw, tfh = min(2, fw), 1
        elif side == "bottom":
            tfr, tfc = fr-2, fc
            tfw, tfh = min(2, fw), 1
        elif side == "left":
            tfr, tfc = fr, fc+2
            tfw, tfh = 1, min(2, fh)
        else:
            tfr, tfc = fr, fc-2
            tfw, tfh = 1, min(2, fh)

        if _can_place(grid, tfr, tfc, tfw, tfh, r2, c2):
            _put(grid, furniture_map, "coffee_table", tfr, tfc, tfw, tfh)

        # TV ở cạnh đối diện sofa — sofa "nhìn" về phía TV
        tv_len = min(2, room_w if opposite in ("top","bottom") else room_h)
        tv_len = max(1, tv_len)
        if opposite == "top":
            vfr, vfc = r1+1, fc
            vfw, vfh = tv_len, 1
        elif opposite == "bottom":
            vfr, vfc = r2-1, fc
            vfw, vfh = tv_len, 1
        elif opposite == "left":
            vfr, vfc = fr, c1+1
            vfw, vfh = 1, tv_len
        else:
            vfr, vfc = fr, c2-1
            vfw, vfh = 1, tv_len

        if _can_place(grid, vfr, vfc, vfw, vfh, r2, c2):
            _put(grid, furniture_map, "tv", vfr, vfc, vfw, vfh)

    # Kệ sách đặt ở 1 góc còn trống
    _try_place_in_corner(grid, r1, c1, r2, c2, furniture_map, "bookshelf", 1, 2)


def _layout_bedroom(grid, r1, c1, r2, c2, furniture_map):
    """Giường luôn dựa sát 1 cạnh tường (đầu giường áp tường),
    tủ quần áo đặt ở góc phòng, bàn làm việc dựa tường còn lại."""
    room_h, room_w = r2-r1-1, c2-c1-1
    side = _pick_wall_side(room_h, room_w)

    bed_w, bed_h = 2, 3
    if side in ("top", "bottom"):
        bed_w, bed_h = bed_h, bed_w  # xoay giường nằm ngang nếu áp tường trên/dưới

    if side == "top":
        fr, fc = r1+1, random.randint(c1+1, max(c1+1, c2-bed_w))
    elif side == "bottom":
        fr, fc = max(r1+1, r2-bed_h), random.randint(c1+1, max(c1+1, c2-bed_w))
    elif side == "left":
        fr, fc = random.randint(r1+1, max(r1+1, r2-bed_h)), c1+1
    else:
        fr, fc = random.randint(r1+1, max(r1+1, r2-bed_h)), max(c1+1, c2-bed_w)

    if room_w >= bed_w and room_h >= bed_h and _can_place(grid, fr, fc, bed_w, bed_h, r2, c2):
        _put(grid, furniture_map, "bed", fr, fc, bed_w, bed_h)
        # Bàn đầu giường ngay cạnh giường
        if side in ("left", "right"):
            nfr, nfc = fr, (fc+bed_w if side=="left" else fc-1)
        else:
            nfr, nfc = (fr+bed_h if side=="top" else fr-1), fc
        if _can_place(grid, nfr, nfc, 1, 1, r2, c2):
            _put(grid, furniture_map, "nightstand", nfr, nfc, 1, 1)

    # Tủ quần áo luôn đặt sát góc phòng (mô phỏng thực tế)
    _try_place_in_corner(grid, r1, c1, r2, c2, furniture_map, "wardrobe", 1, 2,
                         avoid_side=side)

    # Bàn làm việc dựa 1 cạnh tường khác (không trùng cạnh giường)
    other_sides = [s for s in ["top","bottom","left","right"] if s != side]
    desk_side = random.choice(other_sides)
    _try_place_on_side(grid, r1, c1, r2, c2, furniture_map, "desk", 2, 1, desk_side)


def _layout_kitchen(grid, r1, c1, r2, c2, furniture_map):
    """Bếp chữ I: quầy bếp - bếp nấu - tủ lạnh dọc theo 1 cạnh tường.
    Bàn ăn đặt giữa phòng với ghế quanh nếu đủ chỗ."""
    room_h, room_w = r2-r1-1, c2-c1-1
    side = _pick_wall_side(room_h, room_w)

    # Đặt cụm bếp dọc theo cạnh `side`: counter, stove, fridge nối tiếp nhau
    cluster = [("counter", 2, 1), ("stove", 1, 1), ("fridge", 1, 2)]
    if side in ("top", "bottom"):
        pos = c1 + 1
        fr = r1+1 if side == "top" else r2-2
        for name, fw, fh in cluster:
            if side == "bottom":
                fr = r2 - fh
            if pos + fw <= c2 and _can_place(grid, fr, pos, fw, fh, r2, c2):
                _put(grid, furniture_map, name, fr, pos, fw, fh)
                pos += fw + 1  # chừa khe nhỏ giữa các món
    else:
        pos = r1 + 1
        fc = c1+1 if side == "left" else c2-2
        for name, fw, fh in cluster:
            # đổi w/h vì đặt dọc tường trái/phải
            fw2, fh2 = fh, fw
            if side == "right":
                fc = c2 - fw2
            if pos + fh2 <= r2 and _can_place(grid, pos, fc, fw2, fh2, r2, c2):
                _put(grid, furniture_map, name, pos, fc, fw2, fh2)
                pos += fh2 + 1

    # Bàn ăn ở giữa phòng nếu đủ rộng
    if room_h >= 5 and room_w >= 5:
        tw, th = 2, 2
        tfr = r1 + 1 + (room_h - th) // 2
        tfc = c1 + 1 + (room_w - tw) // 2
        if _can_place(grid, tfr, tfc, tw, th, r2, c2):
            _put(grid, furniture_map, "dining_table", tfr, tfc, tw, th)
            # Ghế quanh bàn (trái và phải)
            for cfc, cfr in [(tfc-1, tfr), (tfc+tw, tfr)]:
                if c1 < cfc < c2 and _can_place(grid, cfr, cfc, 1, 1, r2, c2):
                    _put(grid, furniture_map, "chair", cfr, cfc, 1, 1)


def _layout_bathroom(grid, r1, c1, r2, c2, furniture_map):
    """Bồn tắm dựa cạnh tường dài nhất, bồn cầu + bồn rửa ở góc còn lại."""
    room_h, room_w = r2-r1-1, c2-c1-1
    side = "top" if room_w >= room_h else "left"

    if side == "top":
        bw = min(2, room_w)
        fr, fc = r1+1, c1+1
        if _can_place(grid, fr, fc, bw, 1, r2, c2):
            _put(grid, furniture_map, "bathtub", fr, fc, bw, 1)
    else:
        bh = min(2, room_h)
        fr, fc = r1+1, c1+1
        if _can_place(grid, fr, fc, 1, bh, r2, c2):
            _put(grid, furniture_map, "bathtub", fr, fc, 1, bh)

    # Bồn cầu và bồn rửa ở góc đối diện
    _try_place_in_corner(grid, r1, c1, r2, c2, furniture_map, "toilet", 1, 1,
                         prefer_corner="bottom_right")
    _try_place_in_corner(grid, r1, c1, r2, c2, furniture_map, "sink", 1, 1,
                         prefer_corner="bottom_left")


def _layout_laundry(grid, r1, c1, r2, c2, furniture_map):
    """Máy giặt và máy sấy đặt sát cạnh nhau dựa 1 cạnh tường (set chuẩn)."""
    room_h, room_w = r2-r1-1, c2-c1-1
    side = _pick_wall_side(room_h, room_w)

    if side in ("top", "bottom"):
        fr = r1+1 if side == "top" else r2-1
        fc = c1+1
        for name in ["washer", "dryer"]:
            if _can_place(grid, fr, fc, 1, 1, r2, c2):
                _put(grid, furniture_map, name, fr, fc, 1, 1)
                fc += 1
        shelf_fc = fc + 1
        if _can_place(grid, fr, shelf_fc, 2, 1, r2, c2):
            _put(grid, furniture_map, "shelf", fr, shelf_fc, 2, 1)
    else:
        fc = c1+1 if side == "left" else c2-1
        fr = r1+1
        for name in ["washer", "dryer"]:
            if _can_place(grid, fr, fc, 1, 1, r2, c2):
                _put(grid, furniture_map, name, fr, fc, 1, 1)
                fr += 1
        if _can_place(grid, fr+1, fc, 1, 2, r2, c2):
            _put(grid, furniture_map, "shelf", fr+1, fc, 1, 2)


def _try_place_in_corner(grid, r1, c1, r2, c2, furniture_map, name, fw, fh,
                         avoid_side=None, prefer_corner=None):
    """Thử đặt đồ vật sát 1 trong 4 góc phòng (mô phỏng tủ/kệ luôn ở góc)."""
    corners = {
        "top_left":     (r1+1, c1+1),
        "top_right":    (r1+1, max(c1+1, c2-fw)),
        "bottom_left":  (max(r1+1, r2-fh), c1+1),
        "bottom_right": (max(r1+1, r2-fh), max(c1+1, c2-fw)),
    }
    order = list(corners.keys())
    if prefer_corner and prefer_corner in corners:
        order.remove(prefer_corner)
        order.insert(0, prefer_corner)
    else:
        random.shuffle(order)

    for key in order:
        fr, fc = corners[key]
        if _can_place(grid, fr, fc, fw, fh, r2, c2):
            _put(grid, furniture_map, name, fr, fc, fw, fh)
            return True
    return False


def _try_place_on_side(grid, r1, c1, r2, c2, furniture_map, name, fw, fh, side):
    """Thử đặt đồ vật dựa sát 1 cạnh tường cụ thể."""
    room_w = c2 - c1 - 1
    room_h = r2 - r1 - 1
    if side in ("top", "bottom") and fw > room_w:
        fw, fh = fh, fw  # xoay nếu không vừa
    if side in ("left", "right") and fh > room_h:
        fw, fh = fh, fw

    if side == "top":
        fr, fc = r1+1, random.randint(c1+1, max(c1+1, c2-fw))
    elif side == "bottom":
        fr, fc = max(r1+1, r2-fh), random.randint(c1+1, max(c1+1, c2-fw))
    elif side == "left":
        fr, fc = random.randint(r1+1, max(r1+1, r2-fh)), c1+1
    else:
        fr, fc = random.randint(r1+1, max(r1+1, r2-fh)), max(c1+1, c2-fw)

    if _can_place(grid, fr, fc, fw, fh, r2, c2):
        _put(grid, furniture_map, name, fr, fc, fw, fh)
        return True
    return False


def _place_decor_filler(grid, r1, c1, r2, c2, furniture_map, room_area):
    """Rải thêm vài món đồ trang trí 1x1 vào ô sàn trống còn lại."""
    n_decor = max(1, room_area // 18)
    attempts = 0
    placed = 0
    while placed < n_decor and attempts < 40:
        attempts += 1
        fr = random.randint(r1+1, r2-1)
        fc = random.randint(c1+1, c2-1)
        if grid[fr][fc] == FLOOR:
            # Tránh đặt sát giữa lối đi chính: chỉ đặt nếu có >=2 neighbor sàn trống
            free_neighbors = sum(
                1 for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]
                if 0 <= fr+dr < len(grid) and 0 <= fc+dc < len(grid[0])
                and grid[fr+dr][fc+dc] == FLOOR
            )
            if free_neighbors >= 3:
                name = random.choice(DECOR_ITEMS)
                grid[fr][fc] = FURNITURE
                furniture_map[(fr, fc)] = (name, fr, fc, 1, 1)
                placed += 1


def _place_doors(grid, rooms, rows, cols):
    """Trả về door_info: list of (r, c, orientation) — orientation 'h' hoặc 'v'."""
    door_info = []
    for i in range(len(rooms)):
        for j in range(i+1, len(rooms)):
            r1a,c1a,r2a,c2a = rooms[i]
            r1b,c1b,r2b,c2b = rooms[j]

            if r2a == r1b:
                overlap_c = [c for c in range(max(c1a,c1b)+1, min(c2a,c2b))
                             if 0 < c < cols-1]
                if overlap_c:
                    mc = overlap_c[len(overlap_c)//2]
                    grid[r2a][mc] = DOOR
                    door_info.append((r2a, mc, 'h'))

            elif r2b == r1a:
                overlap_c = [c for c in range(max(c1a,c1b)+1, min(c2a,c2b))
                             if 0 < c < cols-1]
                if overlap_c:
                    mc = overlap_c[len(overlap_c)//2]
                    grid[r1a][mc] = DOOR
                    door_info.append((r1a, mc, 'h'))

            if c2a == c1b:
                overlap_r = [r for r in range(max(r1a,r1b)+1, min(r2a,r2b))
                             if 0 < r < rows-1]
                if overlap_r:
                    mr = overlap_r[len(overlap_r)//2]
                    grid[mr][c2a] = DOOR
                    door_info.append((mr, c2a, 'v'))

            elif c2b == c1a:
                overlap_r = [r for r in range(max(r1a,r1b)+1, min(r2a,r2b))
                             if 0 < r < rows-1]
                if overlap_r:
                    mr = overlap_r[len(overlap_r)//2]
                    grid[mr][c1a] = DOOR
                    door_info.append((mr, c1a, 'v'))
    return door_info


def _simple_fallback(rows, cols):
    grid = [[WALL]*cols for _ in range(rows)]
    mid_r, mid_c = rows//2, cols//2
    rooms_fb = [(0,0,mid_r,mid_c),(0,mid_c,mid_r,cols-1),
                (mid_r,0,rows-1,mid_c),(mid_r,mid_c,rows-1,cols-1)]
    room_info = []
    furniture_map = {}
    for i,(r1,c1,r2,c2) in enumerate(rooms_fb):
        rtype = ROOM_TYPES[i % len(ROOM_TYPES)]
        room_info.append((rtype,r1,c1,r2,c2,ROOM_COLORS[rtype]))
        for r in range(r1+1,r2):
            for c in range(c1+1,c2):
                grid[r][c] = FLOOR
        _place_furniture(grid, rtype, r1, c1, r2, c2, furniture_map)
    door_info = _place_doors(grid, rooms_fb, rows, cols)
    dock = (1,1)
    grid[dock[0]][dock[1]] = DOCK
    floors = [(r,c) for r in range(rows) for c in range(cols)
              if grid[r][c] == FLOOR]
    dust_cells = random.sample(floors, min(DUST_COUNT, len(floors)))
    for r,c in dust_cells:
        grid[r][c] = DUST
    return grid, dock, dust_cells, room_info, furniture_map, door_info


def _all_reachable(grid, dock, dust_cells, rows, cols):
    passable = {FLOOR, DUST, DUST2, DOCK, DOCK2, DOOR}
    visited  = set()
    q = deque([dock])
    visited.add(dock)
    while q:
        r,c = q.popleft()
        for dr,dc in [(-1,0),(1,0),(0,-1),(0,1)]:
            nr,nc = r+dr,c+dc
            if 0<=nr<rows and 0<=nc<cols and (nr,nc) not in visited:
                if grid[nr][nc] in passable:
                    visited.add((nr,nc))
                    q.append((nr,nc))
    return all(d in visited for d in dust_cells)


def get_neighbors(grid, r, c, rows, cols):
    passable = {FLOOR, DUST, DUST2, DOCK, DOCK2, DOOR}
    result   = []
    for dr,dc in [(-1,0),(1,0),(0,-1),(0,1)]:
        nr,nc = r+dr,c+dc
        if 0<=nr<rows and 0<=nc<cols and grid[nr][nc] in passable:
            result.append((nr,nc))
    return result

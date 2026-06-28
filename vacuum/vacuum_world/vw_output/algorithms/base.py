"""
Lớp base cho tất cả thuật toán vacuum.
Mỗi thuật toán override plan_next_move().
"""
import copy
from map_generator import DUST, DOCK, BATTERY_MAX, get_neighbors, GRID_ROWS, GRID_COLS

MAX_CHARGES = 10   # Số lần sạc tối đa mỗi lần chạy. Vượt quá → status "failed"


class VacuumBase:
    def __init__(self, grid, dock, dust_cells, rows=GRID_ROWS, cols=GRID_COLS):
        self.grid       = [row[:] for row in grid]
        self.dock       = dock
        self.dust_remaining = set(dust_cells)
        self.rows       = rows
        self.cols       = cols
        self.pos        = dock
        self.battery    = BATTERY_MAX
        self.steps      = 0
        self.charges    = 0
        self.dust_collected = 0
        self.total_dust = len(dust_cells)
        self.move_log   = []   # list of (pos, event)
        self.done       = False
        self.status     = "running"  # running / finished / dead / failed
        self._silent_search = False

    def log_algo(self, msg):
        if not self._silent_search:
            self.move_log.append((None, f"ALGO:{msg}"))

    def get_nb(self, r, c):
        return get_neighbors(self.grid, r, c, self.rows, self.cols)

    def step(self):
        """Thực hiện 1 bước. Trả về False nếu kết thúc."""
        if self.done:
            return False

        # Hết bụi → về dock
        if not self.dust_remaining:
            if self.pos == self.dock:
                self.done = True
                self.status = "finished"
                self.move_log.append((self.pos, "finished"))
                return False
            path = self._path_to(self.dock)
            if not path or len(path) < 2:
                self.done = True
                self.status = "finished"
                return False
            return self._move_to(path[1])

        # Hết pin
        if self.battery <= 0:
            self.done = True
            self.status = "dead"
            self.move_log.append((self.pos, "dead"))
            return False

        # Cần về dock sạc không?
        if self._need_charge():
            if self.pos == self.dock:
                self._charge()
                return not self.done  # False nếu _charge() set failed
            path = self._path_to(self.dock)
            if path and len(path) >= 2:
                # Robot bị buộc rẽ hướng để về sạc giữa chừng — mọi
                # path/target đã lập kế hoạch từ trước (lưu trong thuật
                # toán con) không còn hợp lệ nữa, phải xoá để tránh việc
                # sau khi sạc xong, thuật toán con lấy lại bước cũ ở xa
                # (gây 'teleport' nhìn như robot nhảy vị trí).
                self._on_reroute_to_charge()
                return self._move_to(path[1])

        # Lấy bước tiếp theo từ thuật toán con
        next_pos = self.plan_next_move()
        if next_pos is None:
            self.done = True
            self.status = "finished"
            return False
        return self._move_to(next_pos)

    def _move_to(self, pos):
        if self.battery <= 0:
            self.done = True
            self.status = "dead"
            return False
        self.pos = pos
        self.battery -= 1
        self.steps += 1
        event = "move"
        if pos in self.dust_remaining:
            self.dust_remaining.discard(pos)
            self.grid[pos[0]][pos[1]] = 0  # floor
            self.dust_collected += 1
            event = "vacuum"
        elif pos == self.dock and self.battery < BATTERY_MAX:
            self._charge()
            if self.done:                # vượt MAX_CHARGES → failed
                return False
            event = "charge"
        self.move_log.append((pos, event))
        return True

    def _charge(self):
        if self.charges >= MAX_CHARGES:
            # Đã dùng hết số lần sạc cho phép → dừng lại, báo thất bại.
            # Robot không được sạc thêm dù vẫn còn bụi và chưa hết pin.
            self.done   = True
            self.status = "failed"
            self.move_log.append((self.pos, "failed"))
            return
        self.battery = BATTERY_MAX
        self.charges += 1

    def _need_charge(self):
        """Về dock trước khi hết pin: ước lượng bước về dock.
        Dùng grid mà agent thực sự biết (known_grid nếu có, else grid thật).
        Margin an toàn nhỏ vừa đủ (+5) để không sạc quá sớm/lãng phí,
        kết hợp với việc step() chỉ kiểm tra điều kiện này khi thuật toán
        con KHÔNG có sẵn 1 path đang đi dở (xem step() trong lớp này) —
        nhờ đó tránh được hiện tượng dao động liên tục giữa 'đi tới
        target' và 'quay về sạc' khi robot đang xa dock."""
        from algorithms.pathfinder import bfs_path
        nav_grid = getattr(self, 'known_grid', None)
        if nav_grid is not None:
            path, cost = self._bfs_on_known(self.pos, self.dock)
        else:
            path, cost = bfs_path(self.grid, self.pos, self.dock, get_neighbors)
            if not path:
                return False  # không tính được đường thật -> để thuật toán con tự xử lý
        if not path:
            return False  # chưa biết đường về dock -> đừng ép buộc charge sai
        return self.battery <= cost + 5

    def _bfs_on_known(self, start, goal):
        """BFS trên known_grid (dùng method _known_neighbors nếu agent định nghĩa)."""
        from collections import deque
        if hasattr(self, '_known_neighbors'):
            get_nb = self._known_neighbors
        else:
            return [], 0
        if start == goal:
            return [start], 0
        queue = deque([start])
        parent = {start: None}
        while queue:
            node = queue.popleft()
            for nb in get_nb(node):
                if nb not in parent:
                    parent[nb] = node
                    if nb == goal:
                        path, n = [], goal
                        while n is not None:
                            path.append(n)
                            n = parent[n]
                        path = list(reversed(path))
                        return path, len(path) - 1
                    queue.append(nb)
        return [], 0

    def _path_to(self, target):
        nav_grid = getattr(self, 'known_grid', None)
        if nav_grid is not None and hasattr(self, '_known_neighbors'):
            path, _ = self._bfs_on_known(self.pos, target)
            return path
        from algorithms.pathfinder import bfs_path
        path, _ = bfs_path(self.grid, self.pos, target, get_neighbors)
        return path

    def plan_next_move(self):
        """Override trong từng thuật toán. Trả về (r,c) bước tiếp theo."""
        raise NotImplementedError

    def _on_reroute_to_charge(self):
        """Hook được gọi khi robot bị buộc đổi hướng giữa chừng để về dock
        sạc pin. Thuật toán con có cache đường đi/target riêng (vd:
        self._current_path, self._current_target) NÊN override hàm này để
        xoá cache đó — nếu không, sau khi sạc xong robot có thể lấy lại
        bước đi cũ đã lập kế hoạch từ vị trí xa trước đó, gây hiện tượng
        nhảy vị trí bất thường (teleport). Mặc định không làm gì."""
        pass

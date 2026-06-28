"""
Unknown Environment: chỉ giữ lại BFS Unknown.
Map dần lộ ra khi robot đi đến (reveal ô hiện tại + 4 ô kề).
Chiến lược: nếu thấy bụi đã biết -> đi lấy.
Nếu không -> tìm frontier cell (ô đã biết kề ô UNKNOWN) gần nhất và đi đến đó theo BFS.
"""
import random
from collections import deque
from algorithms.base import VacuumBase
from map_generator import WALL, FURNITURE, DUST, DUST2, DOCK, DOCK2, FLOOR, DOOR

UNKNOWN = -1


class UnknownBase(VacuumBase):
    def __init__(self, grid, dock, dust_cells, rows, cols, target_dust_val=None):
        super().__init__(grid, dock, dust_cells, rows, cols)
        from map_generator import DUST
        self.target_dust_val = target_dust_val if target_dust_val is not None else DUST
        self.known_grid = [[UNKNOWN]*cols for _ in range(rows)]
        self.known_grid[dock[0]][dock[1]] = DOCK
        self._reveal_around(dock)

    def set_start_pos(self, pos):
        """Đặt robot vào vị trí ban đầu khác dock (dùng cho dual mode).
        Reveal xung quanh vị trí mới để có thể bắt đầu di chuyển."""
        self.pos = pos
        self._reveal_around(pos)

    def _reveal_around(self, pos):
        """
        Khám phá ô robot đang đứng + 4 ô kề:
        - Ô robot đang đứng: LUÔN cập nhật (kể cả ô đã biết trước,
          để sync khi bụi bị hút: DUST → FLOOR).
        - 4 ô kề: chỉ reveal nếu còn UNKNOWN.
        - Bụi thuộc loại khác (không phải target_dust_val của robot này)
          được ghi là FLOOR để robot không nhận thấy và không cố dọn.
        """
        from map_generator import DUST, DUST2
        _all_dust = {DUST, DUST2}
        r, c = pos
        # Ô robot đang đứng: luôn sync với grid thật
        self.known_grid[r][c] = self.grid[r][c]
        # 4 ô kề: chỉ reveal lần đầu
        for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
            nr, nc = r+dr, c+dc
            if 0 <= nr < self.rows and 0 <= nc < self.cols:
                if self.known_grid[nr][nc] == UNKNOWN:
                    self.known_grid[nr][nc] = self.grid[nr][nc]

    def _known_neighbors(self, pos):
        r, c = pos
        result = []
        passable = {FLOOR, DUST, DUST2, DOCK, DOCK2, DOOR}
        for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
            nr, nc = r+dr, c+dc
            if 0 <= nr < self.rows and 0 <= nc < self.cols:
                if self.known_grid[nr][nc] in passable:
                    result.append((nr, nc))
        return result

    def _frontier_cells(self):
        passable = {FLOOR, DUST, DUST2, DOCK, DOCK2, DOOR}
        result = []
        for r in range(self.rows):
            for c in range(self.cols):
                if self.known_grid[r][c] in passable:
                    for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
                        nr, nc = r+dr, c+dc
                        if 0 <= nr < self.rows and 0 <= nc < self.cols:
                            if self.known_grid[nr][nc] == UNKNOWN:
                                result.append((r, c))
                                break
        return result

    def _path_on_known(self, start, goal):
        if start == goal:
            return [start]
        queue = deque([start])
        parent = {start: None}
        while queue:
            node = queue.popleft()
            for nb in self._known_neighbors(node):
                if nb not in parent:
                    parent[nb] = node
                    if nb == goal:
                        path, n = [], goal
                        while n is not None:
                            path.append(n)
                            n = parent[n]
                        return list(reversed(path))
                    queue.append(nb)
        return []

    def step(self):
        result = super().step()
        self._reveal_around(self.pos)
        return result

    def _go_to_known_dust(self):
        known_dust = [d for d in self.dust_remaining
                      if self.known_grid[d[0]][d[1]] == self.target_dust_val]
        if not known_dust:
            return None
        dust_sorted = sorted(
            known_dust,
            key=lambda d: abs(d[0]-self.pos[0])+abs(d[1]-self.pos[1]))
        for target in dust_sorted:
            path = self._path_on_known(self.pos, target)
            if len(path) > 1:
                self.log_algo(f"[Môi trường Chưa Biết - Unknown BFS]: Phát hiện hạt bụi tại {target} trong vùng đã khám phá. Đi tới hút ngay.")
                return path[1]
        return None

    def _need_charge(self):
        """Về dock trước khi hết pin. Override base.py để đảm bảo an toàn tuyệt đối.
        Nếu known_grid chưa tìm ra đường về dock (ví dụ robot 2 sinh ra ở xa),
        bắt buộc dùng grid thật để ước lượng chi phí, tránh bị chết giữa đường."""
        from algorithms.pathfinder import bfs_path
        from map_generator import get_neighbors
        path, cost = self._bfs_on_known(self.pos, self.dock)
        if not path:
            # Fallback sang grid thật
            path, cost = bfs_path(self.grid, self.pos, self.dock, get_neighbors)
            if not path:
                return False
        return self.battery <= cost + 5

class BFSUnknown(UnknownBase):
    def plan_next_move(self):
        nxt = self._go_to_known_dust()
        if nxt is not None:
            return nxt
        frontiers = self._frontier_cells()
        if frontiers:
            queue = deque([self.pos])
            parent = {self.pos: None}
            frontiers_set = set(frontiers)
            found_target = None
            while queue:
                node = queue.popleft()
                if node in frontiers_set:
                    found_target = node
                    break
                for nb in self._known_neighbors(node):
                    if nb not in parent:
                        parent[nb] = node
                        queue.append(nb)
            if found_target:
                path, n = [], found_target
                while n is not None:
                    path.append(n)
                    n = parent[n]
                path = list(reversed(path))
                if len(path) > 1:
                    self.log_algo(f"[Môi trường Chưa Biết]: Đang an toàn trong vùng đã quét. Hướng tới vùng đen gần nhất (Frontier) tại {found_target} để mở bản đồ.")
                    return path[1]
        nbs = self._known_neighbors(self.pos)
        self.log_algo("[Môi trường Chưa Biết]: Đi lạc / không tìm được đường. Di chuyển ngẫu nhiên để thoát kẹt.")
        return random.choice(nbs) if nbs else None

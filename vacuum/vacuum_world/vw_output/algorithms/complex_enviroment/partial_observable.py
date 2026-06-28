"""
Partial Observable Environment:
Máy chỉ thấy trong bán kính R=2 ô xung quanh.
Dùng A* trên vùng đã biết, ưu tiên bụi trong tầm nhìn.
"""
import random
from collections import deque
from algorithms.base import VacuumBase
from map_generator import DUST, DUST2, FLOOR, DOCK, DOCK2, WALL, FURNITURE, DOOR
from map_generator import PARTIAL_RADIUS

UNKNOWN = -1


class PartialVacuum(VacuumBase):
    def __init__(self, grid, dock, dust_cells, rows, cols, target_dust_val=None):
        super().__init__(grid, dock, dust_cells, rows, cols)
        from map_generator import DUST
        self.target_dust_val = target_dust_val if target_dust_val is not None else DUST
        self.radius = PARTIAL_RADIUS
        self.known_grid = [[UNKNOWN]*cols for _ in range(rows)]
        self._reveal(dock)
        self._current_path = []
        self._explore_target = None

    def set_start_pos(self, pos):
        """Đặt robot vào vị trí ban đầu khác dock (dùng cho dual mode)."""
        self.pos = pos
        self._reveal(pos)

    def _on_reroute_to_charge(self):
        """Xoá cache path/target khi bị buộc rẽ hướng về sạc giữa chừng."""
        self._current_path   = []
        self._explore_target = None

    def _reveal(self, pos):
        """
        Loộ tất cả ô trong bán kính R:
        - Ô robot đang đứng (dr=dc=0): LUÔN cập nhật (sync DUST→FLOOR).
        - Các ô khác trong bán kính: chỉ reveal nếu còn UNKNOWN.
        - Bụi thuộc loại khác (không phải target_dust_val của robot này)
          được ghi là FLOOR để robot không nhận thấy và không cố dọn.
        """
        from map_generator import DUST, DUST2
        _all_dust = {DUST, DUST2}
        r, c = pos
        # Ô robot đang đứng: luôn sync, khong loc bụi
        self.known_grid[r][c] = self.grid[r][c]
        # Các ô trong bán kính: chỉ reveal lần đầu
        for dr in range(-self.radius, self.radius+1):
            for dc in range(-self.radius, self.radius+1):
                if dr == 0 and dc == 0:
                    continue   # đã xử lý ở trên
                nr, nc = r+dr, c+dc
                if 0 <= nr < self.rows and 0 <= nc < self.cols:
                    if self.known_grid[nr][nc] == UNKNOWN:
                        self.known_grid[nr][nc] = self.grid[nr][nc]

    def _passable(self, r, c):
        cell = self.known_grid[r][c]
        return cell in {FLOOR, DUST, DUST2, DOCK, DOCK2, DOOR}

    def _known_neighbors(self, pos):
        r, c = pos
        result = []
        for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
            nr, nc = r+dr, c+dc
            if 0 <= nr < self.rows and 0 <= nc < self.cols:
                if self._passable(nr, nc):
                    result.append((nr, nc))
        return result

    def _astar_known(self, start, goal):
        import heapq
        def h(a): return abs(a[0]-goal[0]) + abs(a[1]-goal[1])
        heap = [(h(start), 0, start)]
        parent = {start: None}
        g = {start: 0}
        visited = set()
        while heap:
            _, cost, node = heapq.heappop(heap)
            if node in visited:
                continue
            visited.add(node)
            if node == goal:
                path, n = [], goal
                while n is not None:
                    path.append(n)
                    n = parent[n]
                return list(reversed(path))
            for nb in self._known_neighbors(node):
                ng = g[node] + 1
                if nb not in g or ng < g[nb]:
                    g[nb] = ng
                    parent[nb] = node
                    heapq.heappush(heap, (ng + h(nb), ng, nb))
        return []

    def _frontier_cells(self):
        """Ô đã biết kề ô chưa biết → biên khám phá."""
        result = []
        for r in range(self.rows):
            for c in range(self.cols):
                if self.known_grid[r][c] not in (UNKNOWN, WALL, FURNITURE):
                    for dr,dc in [(-1,0),(1,0),(0,-1),(0,1)]:
                        nr,nc = r+dr,c+dc
                        if (0<=nr<self.rows and 0<=nc<self.cols and
                                self.known_grid[nr][nc] == UNKNOWN):
                            result.append((r,c))
                            break
        return result

    def step(self):
        result = super().step()
        self._reveal(self.pos)
        return result

    def _need_charge(self):
        """Về dock trước khi hết pin. Override base.py để đảm bảo an toàn tuyệt đối.
        Nếu known_grid chưa tìm ra đường về dock (ví dụ robot 2 sinh ra ở xa),
        bắt buộc dùng grid thật để ước lượng chi phí, tránh bị chết giữa đường."""
        from algorithms.pathfinder import bfs_path
        from map_generator import get_neighbors
        path = self._astar_known(self.pos, self.dock)
        if not path:
            # Fallback sang grid thật
            path, cost = bfs_path(self.grid, self.pos, self.dock, get_neighbors)
            if not path:
                return False
            return self.battery <= cost + 5
        return self.battery <= len(path) + 5

    def plan_next_move(self):
        # Bụi trong tầm nhìn đã biết
        visible_dust = [d for d in self.dust_remaining
                        if self.known_grid[d[0]][d[1]] == self.target_dust_val]
        if visible_dust:
            dust_sorted = sorted(
                visible_dust,
                key=lambda d: abs(d[0]-self.pos[0])+abs(d[1]-self.pos[1]))
            for target in dust_sorted:
                path = self._astar_known(self.pos, target)
                if len(path) > 1:
                    self._explore_target = None  # ưu tiên bụi, huỷ target khám phá
                    self._current_path = path
                    self.log_algo(f"[Môi trường Mù - Partial Observable]: Thấy bụi tại {target} trong tầm nhìn (bán kính {self.radius}). Chạy thẳng tới hút!")
                    return path[1]

        # Không thấy bụi → giữ nguyên explore target đã chọn nếu còn hợp lệ.
        if self._explore_target is not None:
            if self.pos == self._explore_target:
                self._explore_target = None
            else:
                path = self._astar_known(self.pos, self._explore_target)
                if len(path) > 1:
                    return path[1]
                self._explore_target = None  # không còn đường đến -> chọn lại

        # Chọn frontier mới và CAM KẾT theo đuổi đến khi xong.
        frontiers = self._frontier_cells()
        if frontiers:
            from collections import deque
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
                self._explore_target = found_target
                path, n = [], found_target
                while n is not None:
                    path.append(n)
                    n = parent[n]
                path = list(reversed(path))
                if len(path) > 1:
                    self.log_algo(f"[Môi trường Mù]: Không thấy bụi. Tìm vùng sương mù gần nhất (Frontier) tại {found_target} để mở đường.")
                    return path[1]
            
            # Không có frontier nào đến được từ vị trí hiện tại
            self._explore_target = None

        # Random fallback
        nbs = self._known_neighbors(self.pos)
        self.log_algo("[Môi trường Mù]: Đi lạc / không tìm được đường. Di chuyển ngẫu nhiên để thoát kẹt.")
        return random.choice(nbs) if nbs else None

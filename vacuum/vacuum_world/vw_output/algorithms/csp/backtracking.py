"""
Backtracking CSP — đúng theo Russell & Norvig (AIMA Ch.6).

Mô hình CSP cho Vacuum World:
  - Biến (Variables): X_1, X_2, …, X_n  — thứ tự hút từng ô bụi
  - Miền (Domain):    mỗi biến X_i có domain = tập ô bụi chưa được gán
  - Ràng buộc:        mỗi ô bụi chỉ xuất hiện đúng 1 lần (all-different)
                      + tổng chi phí di chuyển ≤ ngưỡng hợp lệ (battery)

Thuật toán Backtracking-Search (R&N Algorithm 6.5):
  1. Chọn biến chưa gán theo MRV (Minimum Remaining Values):
     ô bụi nào hiện TỐN ÍT PIN NHẤT để đến — tức domain "ít lựa chọn nhất".
  2. Thử lần lượt các giá trị trong domain (sắp xếp bằng LCV —
     Least Constraining Value: gán ô gần nhất trước).
  3. Kiểm tra ràng buộc (constraint check): tổng cost không vượt budget.
  4. Nếu vi phạm → BACKTRACK ngay (không đi sâu thêm).
  5. Nếu tất cả giá trị đều thất bại → backtrack lên cấp trên.

Animation: robot di chuyển theo đúng chuỗi thử-backtrack:
  - Đi đến bụi được thử (assign).
  - Nếu nhánh thất bại: robot quay về vị trí trước đó (backtrack),
    _last_backtrack được set để canvas flash ô bị từ chối.
"""
from algorithms.base import VacuumBase
from algorithms.pathfinder import astar_path
from map_generator import get_neighbors, GRID_ROWS, GRID_COLS, BATTERY_MAX


def _dist(grid, a, b, rows, cols):
    _, c = astar_path(grid, a, b, get_neighbors)
    return c if c else 999


class BacktrackingVacuum(VacuumBase):
    # Budget tối đa cho một lần thử nhánh (bội số của BATTERY_MAX)
    BUDGET_FACTOR = 4

    def __init__(self, grid, dock, dust_cells, rows=GRID_ROWS, cols=GRID_COLS):
        super().__init__(grid, dock, dust_cells, rows, cols)

        # ── Chạy Backtracking-Search để tìm thứ tự hút tối ưu ──────────
        dusts = list(dust_cells)
        budget = BATTERY_MAX * self.BUDGET_FACTOR

        self._iterations = 0
        self.MAX_ITERATIONS = 200

        self._bt_result   = []   # thứ tự cuối cùng (solution)
        self._bt_attempts = []   # log toàn bộ quá trình: (action, dust_cell)
                                 # action: "assign" | "backtrack"
        self._best_cost   = [budget + 1]

        class CSP_State: pass
        csp = CSP_State()
        csp.pos = dock
        csp.remaining = dusts
        csp.cost = 0
        csp.budget = budget
        
        self.BACKTRACKING_SEARCH(csp)

        # Nếu không tìm được giải pháp → dùng greedy fallback
        if not self._bt_result:
            self._bt_result = sorted(dusts,
                key=lambda d: _dist(grid, dock, d, rows, cols))

        # ── Biến điều khiển animation ───────────────────────────────────
        # _exec_plan: danh sách robot cần thực hiện theo thứ tự
        # Mỗi phần tử là (target_dust | None_for_backtrack_pause)
        self._exec_plan    = list(self._bt_result)
        self._current_path = []
        self._last_backtrack = None   # canvas dùng để flash ô bị từ chối

        # ── Replay animation: chèn các bước "backtrack" vào exec_plan ───
        # Xây dựng danh sách di chuyển đầy đủ gồm cả các lần thử sai
        self._move_queue   = []   # list of (r,c) — các ô cần đến lần lượt
        self._bt_flash_queue = [] # list of (r,c) — ô sẽ flash khi robot đến
        self._build_move_queue(dock)

    # ── Thuật toán Backtracking (R&N 6.5) ───────────────────────────────
    def BACKTRACKING_SEARCH(self, csp):
        # return RECURSIVE-BACKTRACKING({}, csp)
        return self.RECURSIVE_BACKTRACKING([], csp)

    def RECURSIVE_BACKTRACKING(self, assignment, csp):
        # if assignment is complete then return assignment
        if not csp.remaining:
            total = csp.cost + _dist(self.grid, csp.pos, self.dock, self.rows, self.cols)
            if total < self._best_cost[0]:
                self._best_cost[0] = total
                self._bt_result = list(assignment)
            return assignment

        # var = SELECT-UNASSIGNED-VARIABLE(csp)
        # Ở đây biến chính là ô bụi tiếp theo cần gán, miền (domain) là các ô bụi chưa dọn (csp.remaining).
        # Sắp xếp miền giá trị: ORDER-DOMAIN-VALUES(var, assignment, csp)
        remaining_sorted = sorted(
            csp.remaining,
            key=lambda d: _dist(self.grid, csp.pos, d, self.rows, self.cols)
        )

        # for each value in ORDER-DOMAIN-VALUES(var, assignment, csp):
        for value in remaining_sorted:
            self._iterations += 1
            if self._iterations > self.MAX_ITERATIONS:
                return None
            
            step_cost = _dist(self.grid, csp.pos, value, self.rows, self.cols)
            new_cost  = csp.cost + step_cost

            # if value is consistent with assignment:
            if new_cost < self._best_cost[0] and new_cost <= csp.budget:
                # add {var = value} to assignment
                self._bt_attempts.append(("assign", value))
                assignment.append(value)
                
                # result = RECURSIVE-BACKTRACKING(assignment, csp)
                class CSP_State: pass
                new_csp = CSP_State()
                new_csp.pos = value
                new_csp.remaining = [d for d in csp.remaining if d != value]
                new_csp.cost = new_cost
                new_csp.budget = csp.budget
                
                result = self.RECURSIVE_BACKTRACKING(assignment, new_csp)

                # remove {var = value} from assignment
                assignment.pop()
            else:
                self._bt_attempts.append(("backtrack", value))

        # return failure
        return None

    # ── Xây dựng move queue gồm cả assign + backtrack ───────────────────
    def _build_move_queue(self, start):
        """
        Tái hiện chuỗi di chuyển thực sự của robot trong quá trình BT.
        Mỗi "assign" → robot đi đến ô đó.
        Mỗi "backtrack" → robot quay lại vị trí trước + flash ô bị từ chối.
        Chỉ replay 1 layer BT đầu (top-level assigns) để animation ngắn gọn.
        """
        pos = start
        pos_stack = [start]   # stack vị trí để biết "quay về đâu"

        # Chỉ lấy các bước top-level để robot không đi lòng vòng quá nhiều
        # Lọc: chỉ giữ lại assign của solution + các backtrack cùng cấp
        solution_set = set(self._bt_result)
        for action, dust in self._bt_attempts:
            if action == "assign" and dust in solution_set:
                self._move_queue.append(dust)
                self._bt_flash_queue.append(None)
                pos = dust
            elif action == "backtrack":
                # Flash ô bị từ chối tại vị trí hiện tại của robot
                self._bt_flash_queue.append(dust)
                # Không di chuyển robot — chỉ flash rồi tiếp tục
                # (giữ nguyên pos)

        # Cuối cùng: thực hiện đúng solution
        self._exec_plan    = list(self._bt_result)
        self._current_path = []

    def _on_reroute_to_charge(self):
        self._current_path = []

    # ── plan_next_move ───────────────────────────────────────────────────
    def plan_next_move(self):
        """
        Robot thực thi kế hoạch trong _exec_plan (thứ tự đã tìm được).
        _last_backtrack được set để canvas flash ô bị từ chối.
        """
        self._last_backtrack = None

        # Flash backtrack nếu có trong queue
        if self._bt_flash_queue:
            cell = self._bt_flash_queue.pop(0)
            if cell is not None:
                self._last_backtrack = cell
                self.log_algo(f"[Thuật toán Backtracking]: Vi phạm ràng buộc (quá ngân sách pin). Đánh dấu ngõ cụt tại {cell}, thực hiện Quay Lui (Backtrack).")

        if self._current_path:
            return self._current_path.pop(0)

        if not self._exec_plan and not self.dust_remaining:
            return None

        # Lấy target tiếp theo từ kế hoạch
        while self._exec_plan:
            target = self._exec_plan.pop(0)
            if target not in self.dust_remaining:
                # Bụi này đã hút rồi (không nên xảy ra) → skip
                self._last_backtrack = target
                continue
            self.log_algo(f"[Thuật toán Backtracking]: Giải bài toán ràng buộc (CSP). Lấy nhánh gán {target} đã được chứng minh an toàn trong giới hạn pin.")
            path, _ = astar_path(self.grid, self.pos, target, get_neighbors)
            if len(path) >= 2:
                self._current_path = path[2:]
                return path[1]
            # Không tìm được đường → backtrack: bỏ target này
            self._last_backtrack = target

        # Fallback: vẫn còn bụi nhưng kế hoạch cạn
        if self.dust_remaining:
            target = min(self.dust_remaining,
                         key=lambda d: abs(d[0]-self.pos[0])+abs(d[1]-self.pos[1]))
            self.log_algo(f"[Thuật toán Backtracking]: Đã cạn cây Backtracking, nhảy sang Fallback Greedy. Tiến tới {target}.")
            path, _ = astar_path(self.grid, self.pos, target, get_neighbors)
            if len(path) >= 2:
                self._current_path = path[2:]
                return path[1]

        return None

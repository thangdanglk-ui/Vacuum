"""
Forward Checking CSP — đúng theo Russell & Norvig (AIMA Ch.6).

Forward Checking mở rộng Backtracking bằng cách:
  Sau mỗi lần gán biến X_i = v, kiểm tra trước (look-ahead) domain của
  tất cả các biến chưa gán X_j: loại bỏ khỏi domain(X_j) mọi giá trị
  vi phạm ràng buộc với giá trị vừa gán.
  → Nếu domain(X_j) = ∅ → BACKTRACK ngay (không cần thử sâu hơn).

Mô hình CSP cho Vacuum World:
  - Biến:      thứ tự hút bụi (X_1, X_2, …, X_n)
  - Domain:    tập ô bụi còn lại
  - Ràng buộc: (a) all-different (mỗi bụi hút đúng 1 lần)
               (b) reachability: từ pos hiện tại đến bụi X_j rồi về dock
                   phải nằm trong budget pin còn lại

Forward Checking sau mỗi bước gán X_i = dust_k:
  Với mỗi bụi d còn lại: kiểm tra cost(current→d→dock) ≤ budget_remaining
  Nếu d KHÔNG thỏa → xóa d khỏi domain hiệu lực.
  Domain rỗng → backtrack.

Animation: robot thực sự di chuyển theo chuỗi thử→fail→backtrack→thử khác.
  _last_backtrack: ô bị cắt khỏi domain (canvas flash đỏ).
"""
from algorithms.base import VacuumBase
from algorithms.pathfinder import astar_path
from map_generator import get_neighbors, GRID_ROWS, GRID_COLS, BATTERY_MAX


def _dist(grid, a, b, rows, cols):
    _, c = astar_path(grid, a, b, get_neighbors)
    return c if c else 999


class ForwardCheckingVacuum(VacuumBase):
    BUDGET_FACTOR = 4

    def __init__(self, grid, dock, dust_cells, rows=GRID_ROWS, cols=GRID_COLS):
        super().__init__(grid, dock, dust_cells, rows, cols)

        dusts  = list(dust_cells)
        budget = BATTERY_MAX * self.BUDGET_FACTOR

        self._iterations = 0
        self.MAX_ITERATIONS = 200

        self._fc_result   = []
        self._fc_attempts = []   # log: ("assign"|"prune"|"backtrack", dust)
        self._best_cost   = [budget + 1]

        class CSP_State: pass
        csp = CSP_State()
        csp.pos = dock
        csp.domain = dusts
        csp.cost = 0
        csp.budget = budget
        csp.budget_max = budget
        
        self.FORWARD_CHECKING_SEARCH(csp)

        if not self._fc_result:
            self._fc_result = sorted(dusts,
                key=lambda d: _dist(grid, dock, d, rows, cols))

        self._exec_plan      = list(self._fc_result)
        self._current_path   = []
        self._last_backtrack = None
        # Queue flash cho animation
        self._flash_queue    = []
        self._build_flash_queue()

    # ── Forward Checking Search ──────────────────────────────────────────
    def FORWARD_CHECKING_SEARCH(self, csp):
        # return FORWARD-CHECK({}, csp)
        return self.FORWARD_CHECK([], csp)

    def FORWARD_CHECKING_UPDATE(self, csp, var, value):
        removed = []
        new_domain = []
        step_cost = _dist(self.grid, csp.pos, value, self.rows, self.cols)
        # Prune using Branch and Bound limit (self._best_cost[0])
        remaining_budget = min(csp.budget - step_cost, self._best_cost[0] - csp.cost - step_cost)

        for d in csp.domain:
            if d == value:
                continue
            cost_d_to_d  = _dist(self.grid, value, d, self.rows, self.cols)
            cost_d_dock  = _dist(self.grid, d, self.dock, self.rows, self.cols)
            if cost_d_to_d + cost_d_dock <= remaining_budget:
                new_domain.append(d)
            else:
                removed.append(d)
                self._fc_attempts.append(("prune", d))
        
        # In TSP, all nodes must be visited. If ANY node becomes unreachable, this branch is dead.
        if removed:
            new_domain = []
            
        return removed, new_domain

    def FORWARD_CHECK(self, assignment, csp):
        # if assignment is complete then return assignment
        if not csp.domain:
            total = csp.cost + _dist(self.grid, csp.pos, self.dock, self.rows, self.cols)
            if total < self._best_cost[0]:
                self._best_cost[0] = total
                self._fc_result = list(assignment)
            return assignment

        # var = SELECT-UNASSIGNED-VARIABLE(csp)
        # for each value in ORDER-DOMAIN-VALUES(var, assignment, csp):
        domain_sorted = sorted(
            csp.domain,
            key=lambda d: _dist(self.grid, csp.pos, d, self.rows, self.cols)
        )

        for value in domain_sorted:
            self._iterations += 1
            if self._iterations > self.MAX_ITERATIONS:
                return None
                
            step_cost = _dist(self.grid, csp.pos, value, self.rows, self.cols)
            new_cost  = csp.cost + step_cost

            # if value is consistent with assignment:
            if new_cost < self._best_cost[0] and new_cost <= csp.budget_max:
                # add {var = value} to assignment
                self._fc_attempts.append(("assign", value))
                assignment.append(value)

                # removed <- FORWARD-CHECKING(csp, var, value)
                removed, new_domain = self.FORWARD_CHECKING_UPDATE(csp, None, value)

                # if no domain in csp is empty:
                if new_domain or len(csp.domain) == 1:
                    class CSP_State: pass
                    new_csp = CSP_State()
                    new_csp.pos = value
                    new_csp.domain = new_domain
                    new_csp.cost = new_cost
                    new_csp.budget = csp.budget - step_cost
                    new_csp.budget_max = csp.budget_max
                    
                    # result = FORWARD-CHECK(assignment, csp)
                    result = self.FORWARD_CHECK(assignment, new_csp)

                else:
                    self._fc_attempts.append(("backtrack", value))
                    for d in removed:
                        self._fc_attempts.append(("restore", d))

                # remove {var = value} from assignment
                assignment.pop()
                # restore domains using removed
                for d in removed:
                    self._fc_attempts.append(("restore", d))
            else:
                self._fc_attempts.append(("backtrack", value))

        # return failure
        return None

    # ── Xây dựng flash queue để animation thấy pruning + backtrack ───────
    def _build_flash_queue(self):
        """
        Chuyển _fc_attempts thành danh sách flash:
        "prune"     → flash vàng (bị cắt domain)
        "backtrack" → flash đỏ (nhánh thất bại)
        """
        solution_set = set(self._fc_result)
        for action, dust in self._fc_attempts:
            if action == "prune":
                self._flash_queue.append(("prune", dust))
            elif action == "backtrack" and dust not in solution_set:
                self._flash_queue.append(("backtrack", dust))

    def _on_reroute_to_charge(self):
        self._current_path = []

    # ── plan_next_move ───────────────────────────────────────────────────
    def plan_next_move(self):
        """
        Thực thi kế hoạch đã tìm được. Xen kẽ flash prune/backtrack.
        _last_backtrack: được set để canvas biết ô nào cần flash.
        """
        self._last_backtrack = None

        # Phát flash từ queue (không làm robot dừng lại)
        if self._flash_queue:
            action, cell = self._flash_queue.pop(0)
            self._last_backtrack = cell   # canvas flash tất cả → không phân biệt loại
            if action == "prune":
                self.log_algo(f"[Thuật toán Forward Checking]: Phát hiện {cell} vi phạm ràng buộc sớm (look-ahead). Cắt tỉa (Prune) khỏi miền giá trị.")
            elif action == "backtrack":
                self.log_algo(f"[Thuật toán Forward Checking]: Miền giá trị rỗng tại {cell}, gây bế tắc. Tiến hành Quay Lui (Backtrack).")

        if self._current_path:
            return self._current_path.pop(0)

        while self._exec_plan:
            target = self._exec_plan.pop(0)
            if target not in self.dust_remaining:
                self._last_backtrack = target
                continue
            self.log_algo(f"[Thuật toán Forward Checking]: Lấy nhánh gán an toàn {target} (đã vượt qua bộ lọc look-ahead).")
            path, _ = astar_path(self.grid, self.pos, target, get_neighbors)
            if len(path) >= 2:
                self._current_path = path[2:]
                return path[1]
            # Không tìm được đường → backtrack
            self._last_backtrack = target

        # Fallback
        if self.dust_remaining:
            target = min(self.dust_remaining,
                         key=lambda d: abs(d[0]-self.pos[0])+abs(d[1]-self.pos[1]))
            self.log_algo(f"[Thuật toán Forward Checking]: Đã cạn kế hoạch CSP, dùng tham lam dự phòng tới {target}.")
            path, _ = astar_path(self.grid, self.pos, target, get_neighbors)
            if len(path) >= 2:
                self._current_path = path[2:]
                return path[1]

        return None

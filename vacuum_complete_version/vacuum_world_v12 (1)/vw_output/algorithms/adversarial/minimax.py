"""
Adversarial Search — Minimax & base class.
Pet (MIN) liên tục di chuyển để chặn đường robot (MAX).
"""
import random
from collections import deque
from algorithms.base import VacuumBase
from algorithms.pathfinder import astar_path
from map_generator import get_neighbors, GRID_ROWS, GRID_COLS, BATTERY_MAX, FLOOR


def _h(a, b):
    return abs(a[0]-b[0]) + abs(a[1]-b[1])


def _passable(grid, pos, rows, cols):
    return get_neighbors(grid, pos[0], pos[1], rows, cols)


def _evaluate(robot_pos, pet_pos, dust_remaining, battery):
    if robot_pos == pet_pos:
        return -999999  # Tử thần: Tránh tuyệt đối ô của Pet

    dust_left = len(dust_remaining)
    nearest   = min((_h(robot_pos, d) for d in dust_remaining), default=0)
    pet_dist  = _h(robot_pos, pet_pos)
    return -dust_left * 80 - nearest * 5 + battery // 4 + pet_dist * 2


def _robot_path_to_dust(robot_pos, dust_remaining, dock, grid):
    """
    Trả về full A* path của robot đến bụi gần nhất.
    Dùng để pet tính điểm đứng chặn TRƯỚC robot.
    """
    if not dust_remaining:
        path, _ = astar_path(grid, robot_pos, dock, get_neighbors)
        return path
    nearest = min(dust_remaining, key=lambda d: _h(robot_pos, d))
    path, _ = astar_path(grid, robot_pos, nearest, get_neighbors)
    return path


class _AdversarialBase(VacuumBase):
    DEPTH = 3

    def __init__(self, grid, dock, dust_cells, rows=GRID_ROWS, cols=GRID_COLS):
        super().__init__(grid, dock, dust_cells, rows, cols)
        self._current_path    = []
        self._current_target  = None
        self._replan_count    = 0
        self._visited_targets = set()
        self._stuck_counter   = 0
        self._last_dust_collected = 0
        self._pet_freeze_steps = 0
        self._pet_history = deque(maxlen=8)

        # ── Khởi tạo pet: trong cùng connected component với dock ──────
        from collections import deque as _dq
        reachable = set()
        _q = _dq([dock])
        reachable.add(dock)
        while _q:
            _p = _q.popleft()
            for _nb in get_neighbors(grid, _p[0], _p[1], rows, cols):
                if _nb not in reachable:
                    reachable.add(_nb)
                    _q.append(_nb)

        candidates = [p for p in reachable
                      if p != dock and grid[p[0]][p[1]] == FLOOR]
        open_cands = [p for p in candidates
                      if len(get_neighbors(grid, p[0], p[1], rows, cols)) >= 2]
        pool = open_cands if open_cands else candidates
        self.pet_pos    = max(pool, key=lambda p: _h(p, dock)) if pool else dock
        self.pet_symbol = "cat"

    def _on_reroute_to_charge(self):
        self._current_path   = []
        self._current_target = None
        self._stuck_counter  = 0

    # ── Minimax search (subclass override) ──────────────────────────
    def _search(self, robot_pos, pet_pos, dust_set, battery, depth, is_max,
                alpha=-999999, beta=999999):
        raise NotImplementedError

    # ── Pet movement ─────────────────────────────────────────────────
    def _move_pet(self):
        raise NotImplementedError

    def _pet_step_toward(self, goal):
        """
        Bước 1 ô A* về phía goal.
        - Né ô robot CHỈ KHI goal không phải ô robot (tránh block chính goal)
        - Luôn di chuyển: nếu anti-oscillation không có alt, chọn freq thấp nhất
        """
        robot_pos = self.pos
        blocked = {robot_pos} if goal != robot_pos else None

        path, _ = astar_path(self.grid, self.pet_pos, goal,
                              get_neighbors, blocked=blocked)
        if len(path) < 2:
            path, _ = astar_path(self.grid, self.pet_pos, goal, get_neighbors)

        nbs = _passable(self.grid, self.pet_pos, self.rows, self.cols)
        safe_nbs = [nb for nb in nbs if nb != robot_pos] or nbs

        if len(path) < 2:
            nxt = min(safe_nbs, key=lambda nb: _h(nb, goal)) if safe_nbs else self.pet_pos
            self.pet_pos = nxt
            self._pet_history.append(nxt)
            return

        nxt = path[1]

        # Anti-oscillation
        freq = {}
        for p in self._pet_history:
            freq[p] = freq.get(p, 0) + 1

        if freq.get(nxt, 0) >= 2:
            alt = [nb for nb in safe_nbs
                   if freq.get(nb, 0) < 2
                   and len(_passable(self.grid, nb, self.rows, self.cols)) > 1]
            if alt:
                nxt = min(alt, key=lambda nb: _h(nb, goal))
            else:
                # Vẫn phải di chuyển: chọn freq thấp nhất
                nxt = min(safe_nbs, key=lambda nb: (freq.get(nb, 0), _h(nb, goal)))

        self.pet_pos = nxt
        self._pet_history.append(nxt)

    def _displace_to(self, pos):
        self.pos = pos
        if pos in self.dust_remaining:
            self.dust_remaining.discard(pos)
            self.grid[pos[0]][pos[1]] = 0
            self.dust_collected += 1
        elif pos == self.dock and self.battery < BATTERY_MAX:
            self._charge()

    def step(self):
        pos_before = self.pos
        result = super().step()

        if self._pet_freeze_steps > 0:
            self._pet_freeze_steps -= 1
        else:
            self._move_pet()

        # Va chạm pet–robot
        if self.pet_pos == self.pos and not self.done:
            nbs = [nb for nb in _passable(self.grid, self.pos, self.rows, self.cols)
                   if nb != self.pet_pos]
            if pos_before in nbs and len(nbs) > 1:
                alt = [nb for nb in nbs if nb != pos_before]
                new_pos = min(alt, key=lambda nb: _h(nb, self.dock)) if alt else pos_before
            elif nbs:
                new_pos = min(nbs, key=lambda nb: _h(nb, self.dock))
            else:
                new_pos = self.pos
            self._displace_to(new_pos)
            self.battery = max(0, self.battery - 1)
            self.steps  += 1
            self._current_path   = []
            self._current_target = None

        if self.dust_collected == self._last_dust_collected:
            self._stuck_counter += 1
        else:
            self._stuck_counter = 0
        self._last_dust_collected = self.dust_collected
        return result

    def plan_next_move(self):
        if not self.dust_remaining:
            return None

        # ── 1. Global A* Navigation (Tìm rác tốt nhất bỏ qua Pet) ──
        # Tối ưu: Chỉ thử A* cho 3 cục rác gần nhất theo đường chim bay
        candidates = sorted(self.dust_remaining, key=lambda d: _h(self.pos, d))[:3]
        
        best_path = None
        for dust in candidates:
            path, _ = astar_path(self.grid, self.pos, dust, get_neighbors)
            if path and (best_path is None or len(path) < len(best_path)):
                best_path = path

        if not best_path or len(best_path) < 2:
            return self.pos

        # ── 2. Đánh giá rủi ro (Pet có đang uy hiếp không?) ──
        # Bị uy hiếp nếu Pet ở cách 3 bước, hoặc Pet nằm chắn ngay trên đoạn đường 4 bước tới
        pet = self.pet_pos
        is_threatened = (_h(self.pos, pet) <= 3) or (pet in best_path[:4])

        # ── 3. Chế độ Hòa Bình (Peace Mode) ──
        if not is_threatened:
            self.log_algo("[Thuật toán Đối kháng]: Chế độ Hòa Bình. Dùng A* tiến về rác.")
            self._current_target = best_path[-1]
            return best_path[1]

        # ── 4. Chế độ Chiến Đấu (Combat Mode) ──
        # Bật Game Tree để tìm bước lách né an toàn nhất
        best_val = -999999
        best_move = self.pos
        moves = _passable(self.grid, self.pos, self.rows, self.cols)
        
        for nb in moves:
            new_dust = set(self.dust_remaining)
            new_dust.discard(nb)
            # Bước tiếp theo là lượt của Pet (is_max = False)
            val = self._search(nb, pet, new_dust, self.battery - 1, self.DEPTH, False)
            
            if val > best_val:
                best_val = val
                best_move = nb

        self.log_algo(f"[Thuật toán Đối kháng]: Bị uy hiếp! Bật Game Tree lách né tới {best_move}.")
        self._current_target = best_path[-1]
        return best_move

# ─── Minimax ────────────────────────────────────────────────────────
class MinimaxVacuum(_AdversarialBase):
    DEPTH = 4

    def _search(self, robot_pos, pet_pos, dust_set, battery,
                depth, is_max, alpha=-999999, beta=999999):
        if depth == 0 or not dust_set or battery <= 0:
            return _evaluate(robot_pos, pet_pos, dust_set, battery)

        if is_max:
            best = -999999
            for nb in _passable(self.grid, robot_pos, self.rows, self.cols):
                new_dust = set(dust_set); new_dust.discard(nb)
                val = self._search(nb, pet_pos, new_dust, battery-1, depth-1, False)
                best = max(best, val)
            return best if best != -999999 else _evaluate(robot_pos, pet_pos, dust_set, battery)
        else:
            worst = 999999
            for nb in _passable(self.grid, pet_pos, self.rows, self.cols):
                val = self._search(robot_pos, nb, dust_set, battery, depth-1, True)
                worst = min(worst, val)
            return worst if worst != 999999 else _evaluate(robot_pos, pet_pos, dust_set, battery)

    def _move_pet(self):
        """
        Pet luôn chặn target robot đang hướng đến:
        1. Tính path robot→target_bụi_hiện_tại
        2. Tìm ô xa nhất pet đến trước robot → đứng đó chặn
        3. Khi robot đổi target → pet tính lại ngay
        """
        if not self.dust_remaining:
            self._pet_step_toward(self.dock)
            return

        # Lấy target robot đang nhắm (từ _current_target nếu có, không thì tính lại)
        robot_target = getattr(self, '_current_target', None)
        if robot_target is None or robot_target not in self.dust_remaining:
            robot_target = min(self.dust_remaining, key=lambda d: _h(self.pos, d))

        # Path robot → target của nó
        path_r, _ = astar_path(self.grid, self.pos, robot_target, get_neighbors)

        if len(path_r) < 2:
            self._pet_step_toward(robot_target)
            return

        # Tìm ô xa nhất trên path robot mà pet đến TRƯỚC robot
        best_block = path_r[-1]  # fallback: đứng ngay ở bụi
        for step, candidate in enumerate(path_r[1:], 1):
            if _h(self.pet_pos, candidate) <= step:
                best_block = candidate   # lấy ô xa nhất (gần bụi nhất)

        self._pet_step_toward(best_block)

"""
Local Search — Simple Hill Climbing

Pseudocode:
    function Simple_Hill_Climbing(Start):
        1. current = Start, evaluate Value(current)
        2. WHILE true:
            a. Generate neighbors of current
            b. FOR EACH neighbor next:
               IF Value(next) > Value(current): current = next; continue
            c. IF no neighbor better: STOP (local max)
        3. RETURN current
"""
import random
from collections import deque
from algorithms.base import VacuumBase
from algorithms.pathfinder import astar_path
from map_generator import get_neighbors


def _h(a, b):
    return abs(a[0]-b[0]) + abs(a[1]-b[1])


class _EscapePathCacheMixin:
    def _on_reroute_to_charge(self):
        self._escape_path = []


class HillClimbingVacuum(_EscapePathCacheMixin, VacuumBase):
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self._stuck_count = 0
        self._escape_path = []
        self._recent = deque(maxlen=6)

    def Simple_Hill_Climbing(self, Start, Goal):
        path = [Start]
        # 1. Initialize current state Current_State = Start.
        Current_State = Start
        # Evaluate the value of Current_State.
        def Value(state):
            return -_h(state, Goal) # maximize negative distance
            
        # 2. WHILE (true):
        while True:
            better_found = False
            # a. Generate successive neighbor states of Current_State.
            neighbors = get_neighbors(self.grid, Current_State[0], Current_State[1], self.rows, self.cols)
            # Sắp xếp ngẫu nhiên để tránh loop cố định nếu có nhiều ô cùng Value
            random.shuffle(neighbors)
            # b. FOR EACH neighbor state Next_State:
            for Next_State in neighbors:
                # i. Evaluate the value of Next_State.
                # ii. IF Value(Next_State) > Value(Current_State)
                if Value(Next_State) > Value(Current_State):
                    # Current_State = Next_State.
                    Current_State = Next_State
                    path.append(Current_State)
                    better_found = True
                    # Move to the next iteration.
                    break
                    
            # c. IF no neighbor state is better:
            if not better_found:
                # Stop because local maximum has been reached.
                break
                
        # 3. RETURN Current_State.
        return Current_State, path

    def plan_next_move(self):
        if not self.dust_remaining:
            if self.pos == self.dock:
                self.done = True
                self.log_algo("Hoàn thành dọn dẹp và về đích.")
                self.move_log.append((self.pos, "finished"))
                return None
            else:
                target = self.dock
        else:
            target = min(self.dust_remaining, key=lambda d: _h(self.pos, d))
            
        if self._escape_path:
            return self._escape_path.pop(0)
        
        # Chỉ chạy mô phỏng 1 bước của Hill Climbing để kiểm soát UI từng bước
        _, path = self.Simple_Hill_Climbing(self.pos, target)
        
        if len(path) > 1:
            best = path[1] # Bước tiếp theo tốt hơn
            # Bỏ log mỗi bước thành công để tránh lag UI do in quá nhiều text
            self._stuck_count = 0
            self._recent.append(self.pos)
            return best
            
        # Nếu path <= 1 -> Stop because local maximum has been reached.
        self._stuck_count += 1
        if self._stuck_count >= 3:
            apath, _ = astar_path(self.grid, self.pos, target, get_neighbors)
            if len(apath) > 1:
                self._stuck_count = 0
                self._recent.clear()
                self._escape_path = apath[2:]
                self.log_algo(f"[Thuật toán Leo Đồi]: Bị kẹt tại Local Maximum. Kích hoạt Fallback A* để thoát kẹt tới {target}.")
                return apath[1]
                
        self._recent.append(self.pos)
        self.log_algo("[Thuật toán Leo Đồi]: Không có bước tiến nào tốt hơn (chạm đỉnh cục bộ). Đi ngẫu nhiên ngang hàng (Shoulder/Plateau).")
        neighbors = get_neighbors(self.grid, self.pos[0], self.pos[1], self.rows, self.cols)
        candidates = [nb for nb in neighbors if nb not in self._recent] or neighbors
        return random.choice(candidates)

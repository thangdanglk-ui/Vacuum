"""
Local Search — Simulated Annealing

Pseudocode:
    SimulatedAnnealing(start, goal):
        current = start; T = T0
        while T > Tmin:
            if current == goal: return current
            next = RandomNeighbor(current)
            delta = h(next) - h(current)
            if delta < 0: current = next
            else:
                p = exp(-delta / T)
                if Random(0,1) < p: current = next
            T = alpha * T
        return current

Implementation note:
  SA làm local search thuần — chấp nhận bước xấu theo xác suất.
  Khi T giảm dần (cooling), thuật toán hội tụ về greedy.
  Escape path dùng A* khi bị kẹt quá lâu để đảm bảo hoàn thành.
"""
import random, math
from collections import deque
from algorithms.base import VacuumBase
from algorithms.pathfinder import astar_path
from map_generator import get_neighbors


def _h(a, b):
    return abs(a[0]-b[0]) + abs(a[1]-b[1])


class _EscapePathCacheMixin:
    def _on_reroute_to_charge(self):
        self._escape_path = []


class SimAnnealVacuum(_EscapePathCacheMixin, VacuumBase):
    # Increase max charges for SA since it's a stochastic explorer
    MAX_CHARGES_OVERRIDE = 25

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.T           = 8.0     # Higher T0: more exploration early on
        self.alpha       = 0.992   # Slower cooling: more time to escape locals
        self.T_min       = 0.05
        self._stuck_count= 0
        self._escape_path= []
        self._recent     = deque(maxlen=8)
        # Override max charges for this stochastic algorithm
        from algorithms import base as _base
        self._sa_max_charges = self.MAX_CHARGES_OVERRIDE

    def _charge(self):
        """Override to allow more charges for SA's random walk nature."""
        if self.charges >= self._sa_max_charges:
            self.done   = True
            self.status = "failed"
            self.move_log.append((self.pos, "failed"))
            return
        from map_generator import BATTERY_MAX
        self.battery = BATTERY_MAX
        self.charges += 1

    def SimulatedAnnealing(self, start, goal):
        path = [start]
        # current state = start
        current_state = start
        # T = T0
        T = self.T
        Tmin = self.T_min
        alpha = self.alpha
        
        # while T > Tmin:
        while T > Tmin:
            # if current state == goal:
            if current_state == goal:
                # return current state
                return current_state, path
                
            # next state = RandomNeighbor(current state)
            neighbors = get_neighbors(self.grid, current_state[0], current_state[1], self.rows, self.cols)
            if not neighbors:
                break
            next_state = random.choice(neighbors)
            
            # Δ = h(next state) - h(current state)
            delta = _h(next_state, goal) - _h(current_state, goal)
            
            # if Δ < 0:
            if delta < 0:
                # current state = next state
                current_state = next_state
                path.append(current_state)
            # else:
            else:
                # p = exp(-Δ / T)
                p = math.exp(-delta / T)
                # if Random(0,1) < p:
                if random.random() < p:
                    # current state = next state
                    current_state = next_state
                    path.append(current_state)
                    
            # T = α * T
            T = alpha * T
            
        # return current state
        return current_state, path

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

        # Mô phỏng 1 bước Annealing để lấy Next State
        current_state = self.pos
        neighbors = get_neighbors(self.grid, current_state[0], current_state[1], self.rows, self.cols)
        if not neighbors:
            return None
            
        # Lấy random neighbor
        candidates = [nb for nb in neighbors if nb not in self._recent]
        if not candidates:
            candidates = neighbors
        next_state = random.choice(candidates)
        
        # Δ = h(next state) - h(current state)
        delta = _h(next_state, target) - _h(current_state, target)
        accept = False
        
        # if Δ < 0:
        if delta < 0:
            accept = True
            self.log_algo(f"[Luyện Kim - Simulated Annealing]: Nhánh {next_state} tốt hơn (delta < 0). Chấp nhận ngay. (Nhiệt độ T={self.T:.2f})")
        # else:
        else:
            # p = exp(-Δ / T)
            p = math.exp(-delta / self.T)
            # if Random(0,1) < p:
            if random.random() < p:
                accept = True
                self.log_algo(f"[Luyện Kim]: Nhánh {next_state} TỆ HƠN, nhưng do Nhiệt độ T={self.T:.2f} cao nên vẫn CHẤP NHẬN rủi ro (xác suất {p:.2%}).")
            else:
                self.log_algo(f"[Luyện Kim]: Nhánh {next_state} tệ hơn, từ chối rủi ro (xác suất {p:.2%}).")
                
        # T = α * T
        self.T = max(self.T * self.alpha, self.T_min)

        if accept:
            self._recent.append(self.pos)
            self._stuck_count = 0
            return next_state
            
        self._stuck_count += 1
        if self._stuck_count >= 15:
            path, _ = astar_path(self.grid, self.pos, target, get_neighbors)
            if len(path) > 1:
                self._stuck_count = 0
                self._escape_path = path[2:]
                self.log_algo(f"[Luyện Kim]: Kẹt quá lâu (15 lượt). Nhiệt độ đã nguội. Kích hoạt Fallback A* tới {target}.")
                return path[1]

        self.log_algo("[Luyện Kim]: Bước đi bị từ chối. Đứng yên tại chỗ chờ lượt sau.")
        return self.pos

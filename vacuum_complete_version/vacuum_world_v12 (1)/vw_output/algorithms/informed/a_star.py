"""
Informed Search — A* Search

Pseudocode:
    function A*(Start, Goal):
        1. FRONTIER = {Start}, f(Start) = 0 + h(Start)
        2. REACHED = {}
        3. WHILE FRONTIER not empty:
            a. Select n with lowest f(n)
            b. IF n == Goal: RETURN success + path
            c. Remove n from FRONTIER, add to REACHED
            d. FOR EACH neighbor m of n:
               g_new = g(n) + cost(n,m)
               if m in REACHED and g_new >= g(m): skip
               else if m in FRONTIER and g_new < g(m): update
               else: add fresh to FRONTIER
        4. RETURN Failure
"""
import heapq
from algorithms.base import VacuumBase
from map_generator import get_neighbors


def _h(a, b):
    return abs(a[0]-b[0]) + abs(a[1]-b[1])


class _PathCacheMixin:
    def _on_reroute_to_charge(self):
        self._current_path = []


class AStarVacuum(_PathCacheMixin, VacuumBase):
    """A*: tim duong ngan nhat toi uu bang f = g + h."""
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self._current_path = []

    def A_Star(self, Start, Goal, blocked=None):
        if blocked is None:
            blocked = set()
            
        # 1. Initialize FRONTIER = {Start} with f(Start) = g(Start) + h(Start) = 0 + h(Start)
        g = {Start: 0}
        parent = {Start: None}
        f_Start = 0 + _h(Start, Goal)
        FRONTIER = [(f_Start, 0, Start)]
        FRONTIER_SET = {Start}
        
        # 2. Initialize REACHED = {}
        REACHED = set()
        
        # 3. WHILE (FRONTIER is not empty):
        while FRONTIER:
            # a. Select node n from FRONTIER with the lowest f(n) value.
            _, _, n = heapq.heappop(FRONTIER)
            FRONTIER_SET.discard(n)
            
            # b. IF n == Goal: RETURN "Success" and reconstruct the path from Start to n.
            if n == Goal:
                path, node = [], Goal
                while node is not None:
                    path.append(node)
                    node = parent[node]
                return list(reversed(path))
                
            # c. Remove n from FRONTIER and add n to REACHED.
            REACHED.add(n)
            
            # d. FOR EACH neighbor state m of n:
            for m in get_neighbors(self.grid, n[0], n[1], self.rows, self.cols):
                if m in blocked and m != Goal:
                    continue
                    
                # i. Calculate new path cost: g_new(m) = g(n) + cost(n, m)
                g_new = g[n] + 1
                
                # ii. IF m is already in REACHED:
                if m in REACHED:
                    # IF g_new(m) >= g(m) currently: Skip state m (worse path).
                    if g_new >= g.get(m, float("inf")):
                        continue
                    # ELSE: Remove m from REACHED and update g(m) = g_new(m).
                    else:
                        REACHED.discard(m)
                        g[m] = g_new
                        parent[m] = n
                        
                # iii. IF m is already in FRONTIER:
                elif m in FRONTIER_SET:
                    # IF g_new(m) < g(m) currently:
                    if g_new < g.get(m, float("inf")):
                        # Update g(m) = g_new(m) and f(m) = g(m) + h(m). Update parent of m to n.
                        g[m] = g_new
                        parent[m] = n
                        f_m = g[m] + _h(m, Goal)
                        heapq.heappush(FRONTIER, (f_m, g_new, m))
                        
                # iv. IF m is not present in FRONTIER and REACHED:
                else:
                    # Set g(m) = g_new(m). Compute f(m) = g(m) + h(m). Set parent of m to n. Add m to FRONTIER.
                    g[m] = g_new
                    f_m = g[m] + _h(m, Goal)
                    parent[m] = n
                    heapq.heappush(FRONTIER, (f_m, g_new, m))
                    FRONTIER_SET.add(m)
                    
        # 4. RETURN "Failure" (Path to destination not found).
        return []

    def plan_next_move(self):
        if self._current_path:
            return self._current_path.pop(0)
        if not self.dust_remaining:
            return None
        self._silent_search = True
        target = min(self.dust_remaining, key=lambda d: _h(self.pos, d))
        self._silent_search = False

        path = self.A_Star(self.pos, target)
        self.log_algo(f"[Thuật toán A*]: Tính f(n) = g(n) + h(n) với heuristic Manhattan. Tìm được đường tối ưu nhất đến {target} (cách {len(path)-1} bước).")
        
        if len(path) > 1:
            self._current_path = path[2:]
            return path[1]
        return None

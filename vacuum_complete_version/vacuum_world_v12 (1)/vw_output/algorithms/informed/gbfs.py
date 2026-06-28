"""
Informed Search — Greedy Best-First Search (GBFS)

Pseudocode:
    function Greedy_Search(Start, Goal):
        1. FRONTIER = {Start}, evaluate h(Start)
        2. REACHED = {}
        3. WHILE FRONTIER not empty:
            a. Select n with lowest h(n)
            b. IF n == Goal: RETURN success + path
            c. Remove n from FRONTIER, add to REACHED
            d. FOR EACH neighbor m of n:
               IF m not in FRONTIER and not in REACHED: add m to FRONTIER
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


class GBFSVacuum(_PathCacheMixin, VacuumBase):
    """Greedy BFS: chon buoc theo h nho nhat (Manhattan distance)."""
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self._current_path = []

    def Greedy_Search(self, Start, Goal):
        # 1. Initialize FRONTIER = {Start}
        #    Evaluate heuristic function for Start: h(Start)
        FRONTIER = [(_h(Start, Goal), Start)]
        FRONTIER_SET = {Start}
        parent = {Start: None}
        
        # 2. Initialize REACHED = {}
        REACHED = set()
        
        # 3. WHILE (FRONTIER is not empty):
        while FRONTIER:
            # a. Select node n from FRONTIER with the lowest h(n).
            # c. Remove n from FRONTIER and add n to REACHED.
            _, n = heapq.heappop(FRONTIER)
            FRONTIER_SET.discard(n)
            
            # b. IF n == Goal:
            #    RETURN "Success" and reconstruct the path from Start to n.
            if n == Goal:
                path, node = [], Goal
                while node is not None:
                    path.append(node)
                    node = parent[node]
                return list(reversed(path))
                
            REACHED.add(n)
            
            # d. FOR EACH neighbor state m of n:
            for m in get_neighbors(self.grid, n[0], n[1], self.rows, self.cols):
                # i. IF m is not in both FRONTIER and REACHED:
                if m not in FRONTIER_SET and m not in REACHED:
                    # Set parent of m to n.
                    parent[m] = n
                    # Evaluate heuristic value h(m). Add m to FRONTIER.
                    heapq.heappush(FRONTIER, (_h(m, Goal), m))
                    FRONTIER_SET.add(m)
                # ii. IF m is already in FRONTIER or REACHED:
                else:
                    # Skip m.
                    continue
                    
        # 4. RETURN "Failure" (Path not found).
        return []

    def plan_next_move(self):
        if self._current_path:
            return self._current_path.pop(0)
            
        if not self.dust_remaining:
            if self.pos == self.dock:
                self.done = True
                self.log_algo("Hoàn thành dọn dẹp và về đích.")
                self.move_log.append((self.pos, "finished"))
                return None
            else:
                target = self.dock
        else:
            self._silent_search = True
            target = min(self.dust_remaining, key=lambda d: _h(self.pos, d))
            self._silent_search = False

        path = self.Greedy_Search(self.pos, target)
        self.log_algo(f"[Thuật toán Tham Lam - Greedy]: Luôn đi theo hướng có Heuristic h(n) nhỏ nhất. Chọn đích là {target}.")
        
        if len(path) > 1:
            self._current_path = path[2:]
            return path[1]
        return None

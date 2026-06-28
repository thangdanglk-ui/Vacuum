"""
Uninformed Search — Depth-First Search (DFS)

Pseudocode (AIMA):
    function DEPTH-FIRST-SEARCH(problem) returns a solution or failure
        node <- NODE(problem.INITIAL)
        if problem.GOAL-TEST(node.STATE) then return SOLUTION(node)
        frontier <- LIFO-STACK()
        frontier.INSERT(node)
        explored <- empty-set
        while not EMPTY?(frontier) do
            node <- frontier.REMOVE()
            explored <- explored U {node.STATE}
            for each action in problem.ACTIONS(node.STATE) do
                child <- CHILD-NODE(problem, node, action)
                if child.STATE not in explored and child not in frontier then
                    if problem.GOAL-TEST(child.STATE) then return SOLUTION(child)
                    frontier.INSERT(child)
        return failure
"""
from algorithms.base import VacuumBase
from algorithms.pathfinder import astar_path
from map_generator import get_neighbors, BATTERY_MAX


def _h(a, b):
    return abs(a[0]-b[0]) + abs(a[1]-b[1])


class _PathCacheMixin:
    def _on_reroute_to_charge(self):
        self._current_path = []
        self._current_target = None


class DFSVacuum(_PathCacheMixin, VacuumBase):
    """DFS: di sau theo LIFO stack, uu tien neighbor gan goal."""
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self._current_path = []
        self._current_target = None

    def DEPTH_FIRST_SEARCH(self, problem):
        class Node:
            def __init__(self, state, path):
                self.STATE = state
                self.path = path

        def CHILD_NODE(prob, parent_node, action):
            return Node(action, parent_node.path + [action])

        node = Node(problem.INITIAL, [problem.INITIAL])
        if problem.GOAL_TEST(node.STATE):
            return node.path
            
        frontier = []  # LIFO-STACK()
        frontier.append(node) # frontier.INSERT(node)
        explored = set()      # empty-set
        
        while frontier:       # not EMPTY?(frontier)
            node = frontier.pop()     # frontier.REMOVE()
            explored.add(node.STATE)  # explored U {node.STATE}
            
            for action in problem.ACTIONS(node.STATE):
                child = CHILD_NODE(problem, node, action)
                in_frontier = any(n.STATE == child.STATE for n in frontier)
                
                if child.STATE not in explored and not in_frontier:
                    if problem.GOAL_TEST(child.STATE):
                        return child.path
                    frontier.append(child) # frontier.INSERT(child)
                    
        return [] # failure

    def _create_problem(self, start, goal):
        class Problem:
            def __init__(self, start, goal, grid, rows, cols):
                self.INITIAL = start
                self.goal = goal
                self.grid = grid
                self.rows = rows
                self.cols = cols
            def GOAL_TEST(self, state):
                return state == self.goal
            def ACTIONS(self, state):
                # Để ưu tiên đi về hướng goal trong DFS, ta sort các neighbor
                nbs = get_neighbors(self.grid, state[0], state[1], self.rows, self.cols)
                # Sắp xếp để những ô gần goal nhất được đưa vào stack sau cùng -> LIFO sẽ lấy ra trước
                nbs.sort(key=lambda nb: -abs(nb[0]-self.goal[0]) - abs(nb[1]-self.goal[1]))
                return nbs
        return Problem(start, goal, self.grid, self.rows, self.cols)

    def plan_next_move(self):
        if self._current_path:
            return self._current_path.pop(0)
        if not self.dust_remaining:
            return None
        candidates = sorted(self.dust_remaining, key=lambda d: _h(self.pos, d))[:4]
        best_path, best_target = None, None
        for d in candidates:
            path = self.DEPTH_FIRST_SEARCH(self._create_problem(self.pos, d))
            if path and (best_path is None or len(path) < len(best_path)):
                best_path, best_target = path, d
        if best_path and len(best_path) - 1 >= BATTERY_MAX - 30:
            apath, _ = astar_path(self.grid, self.pos, best_target, get_neighbors)
            if apath and len(apath) > 1:
                best_path = apath
        if not best_path or len(best_path) <= 1:
            return None
        self._current_target = best_target
        self.log_algo(f"[Thuật toán DFS]: Duyệt sâu (LIFO) ưu tiên rẽ vào nhánh gần đích. Đã tìm ra đường đi đến bụi tại {best_target} (cách {len(best_path)-1} bước).")
        self._current_path = best_path[2:]
        return best_path[1]

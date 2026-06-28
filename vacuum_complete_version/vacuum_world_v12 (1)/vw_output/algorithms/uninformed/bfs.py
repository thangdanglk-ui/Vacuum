"""
Uninformed Search — Breadth-First Search (BFS)

Pseudocode (AIMA):
    function BREADTH-FIRST-SEARCH(problem) returns a solution or failure
        node <- NODE(problem.INITIAL)
        if problem.GOAL-TEST(node.STATE) then return SOLUTION(node)
        frontier <- FIFO-QUEUE()
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
from collections import deque
import heapq
from algorithms.base import VacuumBase
from algorithms.pathfinder import bfs_path
from map_generator import get_neighbors


def _h(a, b):
    return abs(a[0]-b[0]) + abs(a[1]-b[1])


class _PathCacheMixin:
    def _on_reroute_to_charge(self):
        self._current_path = []


class BFSVacuum(_PathCacheMixin, VacuumBase):
    """BFS: tim duong ngan nhat den bui gan nhat (FIFO frontier)."""
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self._current_path = []

    def BREADTH_FIRST_SEARCH(self, problem):
        class Node:
            def __init__(self, state, path):
                self.STATE = state
                self.path = path

        def CHILD_NODE(prob, parent_node, action):
            return Node(action, parent_node.path + [action])

        node = Node(problem.INITIAL, [problem.INITIAL])
        if problem.GOAL_TEST(node.STATE):
            return node.path
            
        frontier = deque()  # FIFO-QUEUE()
        frontier.append(node)
        explored = set()    # empty-set
        
        while frontier:     # not EMPTY?(frontier)
            node = frontier.popleft() # frontier.REMOVE()
            explored.add(node.STATE)  # explored U {node.STATE}
            
            for action in problem.ACTIONS(node.STATE):
                child = CHILD_NODE(problem, node, action)
                in_frontier = any(n.STATE == child.STATE for n in frontier)
                
                if child.STATE not in explored and not in_frontier:
                    if problem.GOAL_TEST(child.STATE):
                        return child.path
                    frontier.append(child)
                    
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
                return get_neighbors(self.grid, state[0], state[1], self.rows, self.cols)
        return Problem(start, goal, self.grid, self.rows, self.cols)

    def plan_next_move(self):
        if self._current_path:
            return self._current_path.pop(0)
        if not self.dust_remaining:
            return None
        self._silent_search = True
        target = min(self.dust_remaining,
                     key=lambda d: len(self.BREADTH_FIRST_SEARCH(self._create_problem(self.pos, d))))
        self._silent_search = False
        
        path = self.BREADTH_FIRST_SEARCH(self._create_problem(self.pos, target))
        self.log_algo(f"[Thuật toán BFS]: Duyệt theo chiều rộng (FIFO) tìm hạt bụi gần nhất -> Chốt mục tiêu tại {target} (cách {len(path)-1} bước).")
        
        if len(path) > 1:
            self._current_path = path[2:]
            return path[1]
        return None

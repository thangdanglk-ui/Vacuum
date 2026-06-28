"""
Các hàm tìm đường ngắn nhất dùng chung cho các thuật toán.
Trả về (path, cost) hoặc ([], 0) nếu không tìm được.
"""
import heapq
from collections import deque


def bfs_path(grid, start, goal, get_neighbors):
    if start == goal:
        return [start], 0
    queue = deque([start])
    parent = {start: None}
    while queue:
        node = queue.popleft()
        for nb in get_neighbors(grid, node[0], node[1],
                                len(grid), len(grid[0])):
            if nb not in parent:
                parent[nb] = node
                if nb == goal:
                    return _reconstruct(parent, goal), _path_cost(parent, goal)
                queue.append(nb)
    return [], 0


def astar_path(grid, start, goal, get_neighbors, blocked=None):
    """Tìm đường ngắn nhất bằng A*. `blocked` (tùy chọn): tập các ô coi
    như vật cản tạm thời (vd vị trí hiện tại của 1 đối tượng động như
    pet) — không đi qua các ô này dù bản thân ô đó là FLOOR hợp lệ trên
    bản đồ tĩnh. Không ảnh hưởng các lệnh gọi cũ không truyền tham số
    này (mặc định None = không có vật cản tạm thời nào)."""
    if blocked is None:
        blocked = set()
    if start == goal:
        return [start], 0
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
            return _reconstruct(parent, goal), g[goal]
        for nb in get_neighbors(grid, node[0], node[1],
                                len(grid), len(grid[0])):
            if nb in blocked and nb != goal:
                continue  # vật cản tạm thời -> bỏ qua (trừ khi nó CHÍNH LÀ đích)
            ng = g[node] + 1
            if nb not in g or ng < g[nb]:
                g[nb] = ng
                parent[nb] = node
                heapq.heappush(heap, (ng + h(nb), ng, nb))
    return [], 0


def _reconstruct(parent, goal):
    path, node = [], goal
    while node is not None:
        path.append(node)
        node = parent[node]
    return list(reversed(path))


def _path_cost(parent, goal):
    cost, node = 0, goal
    while parent[node] is not None:
        cost += 1
        node = parent[node]
    return cost

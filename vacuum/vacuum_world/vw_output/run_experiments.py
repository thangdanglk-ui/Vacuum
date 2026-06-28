import sys, json, time
import copy
sys.path.append('.')

from map_generator import generate_map, GRID_ROWS, GRID_COLS
from algorithms import ALGORITHMS

groups = {
    "Uninformed Search": ["BFS", "DFS"],
    "Informed Search": ["GBFS (Greedy)", "A*"],
    "Local Search": ["Hill Climbing", "Simulated Annealing"],
    "CSP": ["Backtracking", "Forward Checking"],
    "Adversarial Search": ["Minimax", "Alpha-Beta"]
}

NUM_RUNS = 30
MAX_STEPS = 2000

results = {
    "Uninformed Search": {},
    "Informed Search": {},
    "Local Search": {},
    "CSP": {},
    "Adversarial Search": {}
}

# Khởi tạo dict chứa kết quả cho mỗi thuật toán
for group_name, algos in groups.items():
    for algo_name in algos:
        results[group_name][algo_name] = []

for run_id in range(NUM_RUNS):
    # Dùng seed cố định cho mỗi run để so sánh công bằng giữa các thuật toán
    seed = 1000 + run_id
    map_data = generate_map(seed=seed)
    # generate_map trả về (grid, dock, dust_cells, room_info, furniture_map, door_info)
    original_grid = map_data[0]
    dock = map_data[1]
    original_dust_cells = map_data[2]
    
    for group_name, algos in groups.items():
        for algo_name in algos:
            algo_class = ALGORITHMS.get(algo_name)
            if not algo_class:
                print(f"Không tìm thấy thuật toán {algo_name}")
                continue
                
            # Tạo bản sao của grid và dust_cells để tránh thuật toán này thay đổi dữ liệu của thuật toán khác
            grid_copy = [row[:] for row in original_grid]
            dust_copy = list(original_dust_cells)
            
            agent = algo_class(grid_copy, dock, dust_copy, GRID_ROWS, GRID_COLS)
            
            start_time = time.perf_counter()
            steps_taken = 0
            
            while not agent.done and steps_taken < MAX_STEPS:
                # Bắt exception trong trường hợp thuật toán bị lỗi (như đệ quy quá sâu)
                try:
                    agent.step()
                except Exception as e:
                    agent.status = "failed"
                    agent.done = True
                    break
                steps_taken += 1
                
            end_time = time.perf_counter()
            
            # Thu thập kết quả
            run_result = {
                "run_id": run_id + 1,
                "seed": seed,
                "steps": agent.steps,
                "dust_collected": agent.dust_collected,
                "total_dust": agent.total_dust,
                "status": agent.status,
                "time_ms": (end_time - start_time) * 1000,
                "battery_left": agent.battery
            }
            
            results[group_name][algo_name].append(run_result)
            print(f"Run {run_id+1}/{NUM_RUNS} | {algo_name}: status={agent.status}, steps={agent.steps}, dust={agent.dust_collected}/{agent.total_dust}, time={run_result['time_ms']:.2f}ms")

output_file = "experiment_results.json"
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=4)
print(f"Saved results to file {output_file}")

import sys, json, time
import copy
import os

sys.path.append('.')

from map_generator import generate_map, GRID_ROWS, GRID_COLS
from algorithms import ALGORITHMS

groups = {
    "Adversarial Search": ["Minimax", "Alpha-Beta"]
}

NUM_RUNS = 30
MAX_STEPS = 2000

results = {
    "Adversarial Search": {}
}

for group_name, algos in groups.items():
    for algo_name in algos:
        results[group_name][algo_name] = []

print("Bắt đầu chạy benchmark cho nhóm Adversarial Search (30 maps)...")
for run_id in range(NUM_RUNS):
    seed = 1000 + run_id
    map_data = generate_map(seed=seed)
    original_grid = map_data[0]
    dock = map_data[1]
    original_dust_cells = map_data[2]
    
    for group_name, algos in groups.items():
        for algo_name in algos:
            algo_class = ALGORITHMS.get(algo_name)
            if not algo_class:
                print(f"Không tìm thấy thuật toán {algo_name}")
                continue
                
            grid_copy = [row[:] for row in original_grid]
            dust_copy = list(original_dust_cells)
            
            agent = algo_class(grid_copy, dock, dust_copy, GRID_ROWS, GRID_COLS)
            
            start_time = time.perf_counter()
            steps_taken = 0
            
            while not agent.done and steps_taken < MAX_STEPS:
                try:
                    agent.step()
                except Exception as e:
                    agent.status = "failed"
                    agent.done = True
                    break
                steps_taken += 1
                
            end_time = time.perf_counter()
            
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

# Generate summary
summary = {}
for algo, runs in results["Adversarial Search"].items():
    success_runs = [r for r in runs if r["status"] == "finished"]
    avg_steps = sum(r["steps"] for r in success_runs) / len(success_runs) if success_runs else 0
    success_rate = (len(success_runs) / NUM_RUNS) * 100
    avg_completion = sum((r["dust_collected"] / r["total_dust"]) * 100 for r in runs) / NUM_RUNS
    avg_time = sum(r["time_ms"] for r in runs) / NUM_RUNS
    
    summary[algo] = {
        "Số bước TB (chỉ tính pass)": round(avg_steps, 1),
        "Tỉ lệ thành công (%)": round(success_rate, 1),
        "Hoàn thành TB (%)": round(avg_completion, 1),
        "Thời gian chạy TB (ms)": round(avg_time, 3)
    }

final_output = {
    "Adversarial_Search_Summary": summary,
    "Detailed_Runs": results["Adversarial Search"]
}

output_file = r"C:\Users\T14 GEN2\Downloads\adversarial_benchmark.json"
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(final_output, f, ensure_ascii=False, indent=4)
print(f"\nĐã lưu file thành công tại: {output_file}")

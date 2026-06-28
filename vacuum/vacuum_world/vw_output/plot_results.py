import json
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import os

def plot_results(json_file):
    if not os.path.exists(json_file):
        print(f"Không tìm thấy file {json_file}")
        return

    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    algorithms = []
    avg_times = []
    avg_steps = []
    success_rates = []
    groups = []
    
    for group, algos in data.items():
        for algo, runs in algos.items():
            if not runs:
                continue
            
            algorithms.append(algo)
            groups.append(group)
            
            times = [r['time_ms'] for r in runs]
            steps = [r['steps'] for r in runs]
            success = [1 if r['status'] == 'finished' else 0 for r in runs]
            
            avg_times.append(np.mean(times))
            avg_steps.append(np.mean(steps))
            success_rates.append(np.mean(success) * 100)
    
    # Thiết lập style
    sns.set_theme(style="whitegrid")
    
    # 1. Biểu đồ Thời gian
    plt.figure(figsize=(14, 7))
    sns.barplot(x=algorithms, y=avg_times, hue=groups, dodge=False)
    plt.title('Thời gian xử lý trung bình của các thuật toán (ms)', fontsize=14)
    plt.ylabel('Thời gian (ms)')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig('chart_time.png')
    
    # 2. Biểu đồ Số bước
    plt.figure(figsize=(14, 7))
    sns.barplot(x=algorithms, y=avg_steps, hue=groups, dodge=False)
    plt.title('Số bước chân trung bình của các thuật toán', fontsize=14)
    plt.ylabel('Số bước')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig('chart_steps.png')
    
    # 3. Biểu đồ Tỷ lệ hoàn thành
    plt.figure(figsize=(14, 7))
    sns.barplot(x=algorithms, y=success_rates, hue=groups, dodge=False)
    plt.title('Tỷ lệ dọn sạch 100% bụi thành công (%)', fontsize=14)
    plt.ylabel('Tỷ lệ (%)')
    plt.ylim(0, 105)
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig('chart_success.png')

    print("Đã tạo xong biểu đồ và lưu thành các file:")
    print("- chart_time.png")
    print("- chart_steps.png")
    print("- chart_success.png")

if __name__ == '__main__':
    plot_results('experiment_results.json')

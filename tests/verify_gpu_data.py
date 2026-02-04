import subprocess
import psutil
import csv
import io

def get_gpu_processes():
    try:
        # nvidia-smi を実行してプロセス情報を取得
        result = subprocess.run(
            ["nvidia-smi", "--query-compute-apps=pid,process_name,used_memory", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            check=True
        )
        
        processes = []
        for line in result.stdout.strip().split('\n'):
            parts = [p.strip() for p in line.split(',')]
            if len(parts) >= 3:
                try:
                    pid_str = parts[0]
                    # PIDが数字でない場合はスキップ
                    if not pid_str.isdigit():
                        continue
                    pid = int(pid_str)
                    
                    # メモリ使用量が[N/A]などの場合は0とする
                    mem_str = parts[2]
                    used_mem = int(mem_str) if mem_str.isdigit() else 0
                    
                    try:
                        p = psutil.Process(pid)
                        name = p.name()
                        exe = p.exe()
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        name = parts[1]
                        exe = "N/A"
                    
                    processes.append({
                        "pid": pid,
                        "name": name,
                        "exe": exe,
                        "memory": used_mem
                    })
                except Exception as ex:
                    print(f"Skipping line due to error: {line} -> {ex}")
        return processes
    except Exception as e:
        print(f"Error fetching GPU processes: {e}")
        return []

if __name__ == "__main__":
    print("Fetching GPU processes...")
    procs = get_gpu_processes()
    if not procs:
        print("No GPU processes found or error occurred.")
    else:
        print(f"{'PID':<10} {'Memory (MB)':<12} {'Process Name'}")
        print("-" * 40)
        for p in procs:
            print(f"{p['pid']:<10} {p['memory']:<12} {p['name']}")
            print(f"  Path: {p['exe']}")

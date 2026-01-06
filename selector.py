import math
import time
import os
import subprocess
import psutil

# Default baselines
PERF_LOOKUP = {
    "7zip": {"ratio_factor": 0.35, "speed_mbps": 10.0},
    "zstd": {"ratio_factor": 0.55, "speed_mbps": 70.0},
    "paq":  {"ratio_factor": 0.15, "speed_mbps": 0.4}
}

DYNAMIC_PERF = PERF_LOOKUP.copy()

def get_system_ram_safety():
    """Returns available RAM in GB."""
    return psutil.virtual_memory().available / (1024 ** 3)

def calibrate_speeds(bin_paths):
    """Benchmarks hardware to update speed assumptions."""
    global DYNAMIC_PERF
    test_file = "calib_test.tmp"
    test_out = "calib_test.out"
    
    # Create ~2MB of dummy data
    with open(test_file, "wb") as f:
        f.write(os.urandom(1024 * 1024) + b"A" * (1024 * 1024))

    for tool, path in bin_paths.items():
        if not os.path.exists(path): continue
        
        # Build test command
        cmd = [path, "a", test_out, test_file] if "7za" in path else [path, test_file, "-o", test_out]
        
        start = time.time()
        try:
            # 0x08000000 is CREATE_NO_WINDOW for Windows
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, 
                           creationflags=0x08000000, timeout=5)
            duration = time.time() - start
            DYNAMIC_PERF[tool]["speed_mbps"] = 2.0 / max(duration, 0.001)
        except:
            pass 

    for f in [test_file, test_out]:
        if os.path.exists(f): os.remove(f)

def score_algo(features, perf_estimate, constraints):
    size = features.get('size_bytes', 0)
    if size <= 0 or not perf_estimate: return -99999

    compression_gain = (size - perf_estimate['expected_size']) / size
    max_t = constraints.get('max_time', 60)
    time_ratio = perf_estimate['expected_time'] / (max_t if max_t > 0 else 1)
    
    priority = constraints.get('priority', 'balanced')
    if priority == 'size':
        w_gain, w_time = 25.0, 0.5  
    elif priority == 'speed':
        w_gain, w_time = 1.0, 20.0
    else:
        w_gain, w_time = 8.0, 4.0

    score = (w_gain * compression_gain) - (w_time * time_ratio)
    
    if perf_estimate['expected_time'] > max_t:
        score -= 500 
        
    return score

def get_best_tool(features, constraints):
    """
    Final decision engine with Memory Guard.
    """
    if not features: return "zstd"

    # --- MEMORY GUARD ---
    available_ram = get_system_ram_safety()
    # PAQ is extremely RAM hungry. If RAM < 3GB, we force-disable PAQ.
    ram_restricted = []
    if available_ram < 3.0:
        ram_restricted.append("paq")

    best_tool = "zstd"
    best_score = -float('inf')
    
    entropy = features.get('entropy', 0)
    repetition = features.get('repetition', 0)
    size_mb = features.get('size_bytes', 0) / (1024 * 1024)

    # Bypass if data is uncompressible
    if entropy >= 7.98 and repetition < 0.005:
        return "SKIP"

    for tool, stats in DYNAMIC_PERF.items():
        # Skip tools that would crash the PC
        if tool in ram_restricted:
            continue

        predicted_ratio = max(stats['ratio_factor'], entropy / 8.0)
        if repetition > 0.2:
            predicted_ratio -= (repetition * 0.12)

        predicted_ratio = max(0.01, min(predicted_ratio, 1.01))
        
        estimate = {
            'expected_size': features['size_bytes'] * predicted_ratio,
            'expected_time': size_mb / stats['speed_mbps']
        }
        
        score = score_algo(features, estimate, constraints)
        
        if score > best_score:
            best_score = score
            best_tool = tool
            
    return best_tool
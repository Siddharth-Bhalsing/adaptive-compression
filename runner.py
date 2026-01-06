import subprocess
import time
import os

def verify_integrity(tool_cmd_base, archive_path):
    """
    Checks if an ARCHIVE is valid.
    """
    if not os.path.exists(archive_path):
        return (False, "File missing.")
        
    # Only test files that look like archives
    ext = os.path.splitext(archive_path)[1].lower()
    if ext not in ['.7z', '.adapt', '.zpaq', '.paq', '.zst']:
        return (True, "Skip: Not an archive format.")

    test_flag = "t" if "7za" in tool_cmd_base.lower() or "zpaq" in tool_cmd_base.lower() else "-t"
    test_cmd = f'"{tool_cmd_base}" {test_flag} "{archive_path}"'
    
    try:
        result = subprocess.run(
            test_cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            text=True,
            timeout=30,
            cwd=os.path.dirname(tool_cmd_base),
            shell=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        return (result.returncode == 0, result.stderr.strip() or result.stdout.strip())
    except:
        return (False, "Integrity check crashed.")

def run_compressor(cmd, input_path, output_path, timeout=60):
    """
    FINAL ROBUST VERSION:
    1. Trusts Engine Exit Code 0.
    2. Discovers output if 7-zip changes the filename.
    3. Only verifies integrity on COMPRESSION tasks.
    """
    start_time = time.time()
    
    # 1. Shell-safe String Reconstruction
    if isinstance(cmd, list):
        binary_path = cmd[0]
        cmd_str = ' '.join([f'"{arg}"' if (not arg.startswith('-') or os.path.isabs(arg)) else arg for arg in cmd])
    else:
        cmd_str = cmd
        binary_path = cmd.split()[0].replace('"', '')

    try:
        out_dir = os.path.dirname(os.path.abspath(output_path))
        os.makedirs(out_dir, exist_ok=True)

        # 2. Execution
        process = subprocess.run(
            cmd_str, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            text=True, 
            timeout=timeout,
            cwd=os.path.dirname(binary_path), 
            shell=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        
        # 3. Trust the Engine Exit Code
        if process.returncode == 0:
            time.sleep(0.6) # Critical: Let Windows finish the disk IO
            
            # DISCOVERY: Find the file actually created
            actual_file = output_path
            if not os.path.exists(output_path):
                files = [os.path.join(out_dir, f) for f in os.listdir(out_dir)]
                if files:
                    # Pick the file modified in the last 2 seconds
                    actual_file = max(files, key=os.path.getmtime)

            # 4. Context-Aware Validation
            # ONLY run 'test' if we were ADDING (compressing) to an archive
            if " a " in cmd_str or " add " in cmd_str:
                success, msg = verify_integrity(binary_path, actual_file)
                if not success:
                    return {"success": False, "error": f"Integrity Fail: {msg}"}

            if os.path.exists(actual_file):
                return {
                    "success": True,
                    "time": time.time() - start_time,
                    "output_size": os.path.getsize(actual_file),
                    "final_path": actual_file
                }

        # 5. Failure Diagnostics
        err_log = (process.stderr or "" + process.stdout or "").strip()
        print(f"\n[DEBUG] Engine Output: {err_log}")
        
        return {"success": False, "error": f"Engine Error: {err_log[:100]}" if err_log else "Engine wrote no file."}
            
    except Exception as e:
        return {"success": False, "error": f"Runner System Error: {str(e)}"}
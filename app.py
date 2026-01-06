import customtkinter as ctk
from tkinter import filedialog, messagebox
import os
import threading
import time
import sys
import winreg as reg 
import random 
import psutil  # RAM Safety check

# Import your custom modules
import analyzer
import selector
import compressor_manager
import runner

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class AdaptiveCompressUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # --- PATH FIX: Get the folder where the script lives ---
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        
        self.install_portable_linker()
        self.manager = compressor_manager.CompressorManager()
        
        # --- Run Engine Validation ---
        self.validate_engines()
        
        threading.Thread(target=selector.calibrate_speeds, 
                         args=({"zstd": os.path.join(self.manager.bin, "zstd.exe")},), 
                         daemon=True).start()

        # --- Window Setup ---
        self.title("Adaptive Engine | 2026 Eco-Ready")
        self.base_height = 600
        self.width = 480
        self.center_window(self.base_height)
        self.resizable(False, False)
        self.configure(fg_color="#1C1C1E")

        self.is_processing = False 

        # --- UI Construction ---
        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.pack(fill="both", expand=True, padx=25, pady=20)
        
        self.header = ctk.CTkLabel(self.container, text="Adaptive Engine", font=("SF Pro Display", 24, "bold"))
        self.header.pack(anchor="w", pady=(0, 15))

        # 1. File Selection Card
        self.file_card = ctk.CTkFrame(self.container, corner_radius=12, fg_color="#2C2C2E")
        self.file_card.pack(fill="x", pady=10)
        
        self.target_path = ctk.StringVar()
        self.entry = ctk.CTkEntry(self.file_card, placeholder_text="Select a file or folder...", 
                                 textvariable=self.target_path, border_width=0, height=35)
        self.entry.pack(fill="x", padx=15, pady=(15, 5))
        
        self.sel_btn_frame = ctk.CTkFrame(self.file_card, fg_color="transparent")
        self.sel_btn_frame.pack(fill="x", padx=15, pady=(0, 15))
        self.file_btn = ctk.CTkButton(self.sel_btn_frame, text="File", width=90, height=30, command=self.browse_file)
        self.file_btn.pack(side="left", padx=(0, 5))
        self.folder_btn = ctk.CTkButton(self.sel_btn_frame, text="Folder", width=90, height=30, command=self.browse_folder)
        self.folder_btn.pack(side="left")

        # 2. Configuration Card
        self.settings_card = ctk.CTkFrame(self.container, corner_radius=12, fg_color="#2C2C2E")
        self.settings_card.pack(fill="x", pady=10)
        
        self.mode = ctk.StringVar(value="balanced")
        self.seg_button = ctk.CTkSegmentedButton(self.settings_card, values=["speed", "balanced", "size"], 
                                                 variable=self.mode, command=lambda _: self.update_prediction())
        self.seg_button.pack(fill="x", padx=15, pady=(15, 10))

        self.force_tool = ctk.StringVar(value="Auto (Heuristic)")
        self.tool_dropdown = ctk.CTkOptionMenu(self.settings_card, values=["Auto (Heuristic)", "zstd", "7zip", "paq"],
                                               variable=self.force_tool, command=lambda _: self.update_prediction())
        self.tool_dropdown.pack(fill="x", padx=15, pady=(0, 10))

        self.net_aware = ctk.BooleanVar(value=False)
        self.net_switch = ctk.CTkSwitch(self.settings_card, text="Network-Aware Throttling", variable=self.net_aware)
        self.net_switch.pack(pady=(0, 5), padx=15, anchor="w")

        self.max_time = self.create_slider(self.settings_card, "Time Budget (s)", 10, 600, self.on_time_scroll)
        self.target_size = self.create_slider(self.settings_card, "Predicted Gain (%)", 30, 100, self.on_ratio_scroll)

        self.predict_label = ctk.CTkLabel(self.settings_card, text="Prediction: Ready", 
                                          font=("SF Pro Display", 12, "italic"), text_color="#007AFF")
        self.predict_label.pack(pady=(0, 10))

        # 3. Action Buttons
        self.btn_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        self.btn_frame.pack(fill="x", pady=(15, 10))
        self.start_btn = ctk.CTkButton(self.btn_frame, text="Start Engine", fg_color="#34C759", height=45, 
                                      font=("SF Pro Display", 14, "bold"), command=self.start_process_thread)
        self.start_btn.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.reset_btn = ctk.CTkButton(self.btn_frame, text="Reset", fg_color="#FF3B30", width=80, height=45, command=self.reset_ui)
        self.reset_btn.pack(side="right", padx=(5, 0))

        self.log_area = ctk.CTkTextbox(self.container, height=0, fg_color="#000000", text_color="#A1A1A6", font=("Consolas", 11))

    # --- Utilities ---
    def validate_engines(self):
        """Check if engines exist in the bin folder on startup."""
        bin_dir = os.path.join(self.script_dir, "bin")
        required = ["7za.exe", "zstd.exe"]
        missing = [exe for exe in required if not os.path.exists(os.path.join(bin_dir, exe))]
        if missing:
            messagebox.showwarning("Missing Engines", f"The following engines are missing in {bin_dir}:\n" + "\n".join(missing))

    def get_simulated_latency(self): return random.randint(20, 350)
    
    def install_portable_linker(self):
        try:
            python_exe = sys.executable.replace("python.exe", "pythonw.exe")
            script_path = os.path.abspath(sys.argv[0])
            cmd_value = f'"{python_exe}" "{script_path}" "%1"'
            with reg.CreateKey(reg.HKEY_CLASSES_ROOT, r"*\shell\AdaptiveEngine\command") as key:
                reg.SetValue(key, "", reg.REG_SZ, cmd_value)
        except: pass

    def create_slider(self, master, label, from_val, to_val, cmd):
        lbl = ctk.CTkLabel(master, text=label, font=("SF Pro Display", 11))
        lbl.pack(anchor="w", padx=15)
        slider = ctk.CTkSlider(master, from_=from_val, to=to_val, command=cmd)
        slider.pack(fill="x", padx=15, pady=(0, 12))
        return slider

    def center_window(self, h):
        x = (self.winfo_screenwidth()/2) - (self.width/2)
        y = (self.winfo_screenheight()/2) - (h/2)
        self.geometry(f'{self.width}x{int(h)}+{int(x)}+{int(y)}')

    def on_time_scroll(self, val): 
        self.target_size.set(int(100 - ((float(val)/600)*60)))
        self.update_prediction()

    def on_ratio_scroll(self, val): 
        self.max_time.set(int(((100-float(val))/60)*600))
        self.update_prediction()
    
    def reset_ui(self):
        self.target_path.set(""); self.log_area.pack_forget(); self.center_window(self.base_height)
        self.predict_label.configure(text="Prediction: Ready", text_color="#007AFF")
        self.force_tool.set("Auto (Heuristic)")

    def browse_file(self):
        p = filedialog.askopenfilename()
        if p: self.target_path.set(p); self.update_prediction()

    def browse_folder(self):
        p = filedialog.askdirectory()
        if p: self.target_path.set(p); self.update_prediction()

    def update_prediction(self):
        path = self.target_path.get()
        if not path or not os.path.exists(path): return
        available_ram = psutil.virtual_memory().available / (1024**3)
        target = [os.path.join(path, f) for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))][0] if os.path.isdir(path) else path
        stats = analyzer.sample_features(target)
        if not stats: return
        choice = self.force_tool.get()
        best_tool = selector.get_best_tool(stats, {'priority': self.mode.get(), 'max_time': self.max_time.get()}) if choice == "Auto (Heuristic)" else choice
        self.predict_label.configure(text=f"AI Suggests: {best_tool.upper()}", text_color="#34C759")

    def log(self, msg):
        self.log_area.insert("end", f"› {msg}\n"); self.log_area.see("end")

    def start_process_thread(self):
        p = self.target_path.get()
        if not p or not os.path.exists(p): return
        self.is_processing = True
        self.start_btn.configure(state="disabled")
        self.log_area.pack(fill="both", pady=(10,0)); self.log_area.configure(height=160)
        self.center_window(self.base_height + 180); self.log_area.delete("1.0", "end")
        threading.Thread(target=self.run_pipeline, args=(p,), daemon=True).start()

    # --- PIPELINE ---
    def run_pipeline(self, path):
        try:
            targets = [os.path.join(path, f) for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))] if os.path.isdir(path) else [path]

            for item in targets:
                filename = os.path.basename(item)
                ext = item.lower().split('.')[-1]
                
                # --- DECOMPRESSION LOGIC ---
                # --- DECOMPRESSION LOGIC (The Clean Slate Fix) ---
                if ext in ['adapt', '7z', 'zst', 'paq', 'zpaq']:
                    self.log(f"Decompressing: {filename}")
                    
                    output_folder = os.path.abspath(os.path.dirname(item))
                    # We want to end up with "siddharth2020.docx"
                    final_name = filename.rsplit('.', 1)[0] 
                    final_out = os.path.join(output_folder, final_name)

                    # 1. DELETE OLD FILE: Ensure we aren't looking at ghosts
                    if os.path.exists(final_out):
                        try:
                            os.remove(final_out)
                            self.log("› Removed old version for fresh start.")
                        except Exception as e:
                            self.log(f"› System Lock: Close {final_name} first!")
                            continue

                    # 2. RUN ENGINE: Direct to folder
                    # We use 'e' (extract) instead of 'x' to flatten paths
                    cmd = [self.manager.bins["7zip"], "e", item, f"-o{output_folder}", "-aoa", "-y"]
                    
                    result = runner.run_compressor(cmd, item, final_out)
                    
                    # 3. VERIFICATION
                    time.sleep(0.8) # Wait for disk sync
                    if os.path.exists(final_out):
                        self.log(f"› SUCCESS: {final_name} restored.")
                        os.system(f'explorer /select,"{os.path.normpath(final_out)}"')
                    else:
                        # DEBUG: Look for what actually happened
                        actual_files = os.listdir(output_folder)
                        self.log("› ERROR: Expected file missing.")
                        self.log(f"› Found instead: {actual_files[:3]}...") 
                    continue

                # --- COMPRESSION LOGIC ---
                self.log(f"Analyzing: {filename}")
                stats = analyzer.sample_features(item)
                
                # Determine tool
                choice = self.force_tool.get()
                best_tool = selector.get_best_tool(stats, {'priority': self.mode.get()}) if choice == "Auto (Heuristic)" else choice
                
                output_archive = item + (".adapt" if best_tool != "paq" else ".zpaq")
                comp_cmd = self.manager.get_command(best_tool, item, output_archive, level=self.mode.get())
                
                comp_result = runner.run_compressor(comp_cmd, item, output_archive)
                
                if comp_result.get("success"):
                    self.log(f"› Done: {best_tool.upper()} ({comp_result['output_size']//1024} KB)")
                else:
                    self.log(f"› Fail: {comp_result.get('error')}")

            self.log("Pipeline Finished.")
        except Exception as e: 
            self.log(f"Critical Pipeline Error: {str(e)}")
        finally:
            self.is_processing = False
            self.start_btn.configure(state="normal")

if __name__ == "__main__":
    app = AdaptiveCompressUI()
    app.mainloop()
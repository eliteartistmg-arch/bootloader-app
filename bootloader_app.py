#!/usr/bin/env python3
"""
Motorola Bootloader Utility Pro – with expanded exploit support
"""

import os
import sys
import subprocess
import threading
import time
import re
import json
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox


class MotorolaBootloaderUtility:
    def __init__(self, root):
        self.root = root
        self.root.title("Motorola Bootloader Utility Pro")
        self.root.geometry("1050x780")
        self.root.resizable(True, True)

        # State
        self.device_serial = None
        self.device_info = {}
        self.fastboot_path = self._find_fastboot()
        self.running = False
        self.edl_tool = self._find_edl_tool()
        self.magisk_tool = self._find_magisk_tool()
        self.mtk_client = self._find_mtkclient()
        self.blankflash_tool = self._find_blankflash()

        self._setup_ui()
        self._log("Motorola Bootloader Utility Pro initialized")
        self._log(f"Fastboot: {self.fastboot_path}")
        self._log(f"EDL tool: {self.edl_tool or 'Not found'}")
        self._log(f"Magisk: {self.magisk_tool or 'Not found'}")
        self._log(f"mtkclient: {self.mtk_client or 'Not found'}")
        self._log(f"Blankflash: {self.blankflash_tool or 'Not found'}")

    # -------------------- Tool Detection --------------------
    def _find_fastboot(self):
        import shutil
        return shutil.which("fastboot") or "fastboot"

    def _find_edl_tool(self):
        import shutil
        return shutil.which("edl") or None

    def _find_magisk_tool(self):
        import shutil
        return shutil.which("magiskboot") or shutil.which("magisk") or None

    def _find_mtkclient(self):
        import shutil
        return shutil.which("mtk") or None

    def _find_blankflash(self):
        """Find blankflash tool (common names)"""
        import shutil
        for name in ["blankflash", "blankflash.bat", "blankflash.sh"]:
            path = shutil.which(name)
            if path:
                return path
        common_dirs = [os.path.expanduser("~/blankflash"), "/tmp/blankflash"]
        for d in common_dirs:
            if os.path.isdir(d):
                for f in os.listdir(d):
                    if "blankflash" in f.lower() and os.access(os.path.join(d, f), os.X_OK):
                        return os.path.join(d, f)
        return None

    # -------------------- UI Setup --------------------
    def _setup_ui(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        toolbar1 = ttk.Frame(main_frame)
        toolbar1.pack(fill=tk.X, pady=(0, 5))
        for text, cmd in [
            ("🔍 Refresh", self._refresh_devices),
            ("ℹ️ Info", self._get_device_info),
            ("🔓 Unlock", self._unlock_bootloader),
            ("🔒 Lock", self._lock_bootloader),
            ("📦 Flash", self._flash_firmware),
            ("💾 Backup", self._backup_partition),
            ("🔄 Reboot", self._reboot_device),
        ]:
            ttk.Button(toolbar1, text=text, command=cmd).pack(side=tk.LEFT, padx=2)

        toolbar2 = ttk.Frame(main_frame)
        toolbar2.pack(fill=tk.X, pady=(0, 10))

        edl_frame = ttk.LabelFrame(toolbar2, text="EDL", padding=2)
        edl_frame.pack(side=tk.LEFT, padx=5)
        ttk.Button(edl_frame, text="Reboot to EDL", command=self._reboot_edl).pack(side=tk.LEFT, padx=2)
        ttk.Button(edl_frame, text="EDL Info", command=self._edl_info).pack(side=tk.LEFT, padx=2)
        ttk.Button(edl_frame, text="Flash via EDL", command=self._edl_flash).pack(side=tk.LEFT, padx=2)

        root_frame = ttk.LabelFrame(toolbar2, text="Root", padding=2)
        root_frame.pack(side=tk.LEFT, padx=5)
        ttk.Button(root_frame, text="Patch Boot for Root", command=self._patch_boot).pack(side=tk.LEFT, padx=2)

        exploit_frame = ttk.LabelFrame(toolbar2, text="Exploit", padding=2)
        exploit_frame.pack(side=tk.LEFT, padx=5)

        self.exploit_var = tk.StringVar(value="MTK Unlock")
        self.exploit_options = [
            "MTK Unlock",
            "Motorola RSA Bypass",
            "Motorola Unlock (oem unlock)",
            "Motorola Unlock (flashing unlock)",
            "Motorola Blankflash (EDL revive)",
            "Motorola G4/G5 Exploit",
            "Custom Exploit",
        ]
        ttk.Combobox(
            exploit_frame,
            textvariable=self.exploit_var,
            values=self.exploit_options,
            width=22,
            state="readonly",
        ).pack(side=tk.LEFT, padx=2)
        ttk.Button(exploit_frame, text="Run Exploit", command=self._run_exploit).pack(side=tk.LEFT, padx=2)

        self.exploit_desc_var = tk.StringVar()
        self.exploit_desc_var.set(self._get_exploit_description("MTK Unlock"))
        desc_label = ttk.Label(exploit_frame, textvariable=self.exploit_desc_var, font=("", 8), foreground="gray")
        desc_label.pack(side=tk.LEFT, padx=5)
        self.exploit_var.trace_add("write", lambda *a: self.exploit_desc_var.set(self._get_exploit_description(self.exploit_var.get())))

        info_frame = ttk.LabelFrame(main_frame, text="Device Information", padding="5")
        info_frame.pack(fill=tk.X, pady=(0, 10))
        self.info_text = tk.Text(info_frame, height=6, font=("Consolas", 9), wrap=tk.WORD, relief=tk.FLAT, bg="#f5f5f5")
        self.info_text.pack(fill=tk.X)

        control_frame = ttk.LabelFrame(main_frame, text="Operations", padding="5")
        control_frame.pack(fill=tk.X, pady=(0, 10))
        row1 = ttk.Frame(control_frame)
        row1.pack(fill=tk.X, pady=2)
        ttk.Label(row1, text="Unlock Key:").pack(side=tk.LEFT)
        self.unlock_key_var = tk.StringVar()
        ttk.Entry(row1, textvariable=self.unlock_key_var, width=40).pack(side=tk.LEFT, padx=5)
        ttk.Button(row1, text="Get Unlock Data", command=self._get_unlock_data).pack(side=tk.LEFT, padx=2)

        row2 = ttk.Frame(control_frame)
        row2.pack(fill=tk.X, pady=2)
        ttk.Label(row2, text="Partition:").pack(side=tk.LEFT)
        self.partition_var = tk.StringVar(value="boot")
        partitions = ["boot", "recovery", "system", "vendor", "vbmeta", "bootloader", "radio", "persist", "userdata", "cache", "dtbo", "logo"]
        ttk.Combobox(row2, textvariable=self.partition_var, values=partitions, width=15, state="readonly").pack(side=tk.LEFT, padx=5)
        ttk.Label(row2, text="Image File:").pack(side=tk.LEFT, padx=(10, 0))
        self.image_path_var = tk.StringVar()
        ttk.Entry(row2, textvariable=self.image_path_var, width=30).pack(side=tk.LEFT, padx=5)
        ttk.Button(row2, text="Browse...", command=self._browse_image).pack(side=tk.LEFT)

        console_frame = ttk.LabelFrame(main_frame, text="Console Output", padding="5")
        console_frame.pack(fill=tk.BOTH, expand=True)
        self.console = scrolledtext.ScrolledText(console_frame, font=("Consolas", 9), wrap=tk.WORD, bg="#1e1e1e", fg="#d4d4d4")
        self.console.pack(fill=tk.BOTH, expand=True)
        self._setup_console_menu()

        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(fill=tk.X, pady=(5, 0))

    def _get_exploit_description(self, exploit_name):
        descriptions = {
            "MTK Unlock": "Unlock MediaTek bootloader using mtkclient (requires BROM mode).",
            "Motorola RSA Bypass": "Exploit to bypass RSA signature check (CVE-2020-XXXX). Needs external script.",
            "Motorola Unlock (oem unlock)": "Run 'fastboot oem unlock' without key – may work on older devices.",
            "Motorola Unlock (flashing unlock)": "Run 'fastboot flashing unlock' – standard AOSP command.",
            "Motorola Blankflash (EDL revive)": "Flash blankflash to recover hard‑bricked Qualcomm devices.",
            "Motorola G4/G5 Exploit": "Device‑specific vulnerability for G4/G5 series (requires exploit script).",
            "Custom Exploit": "Run a user‑provided Python script as exploit.",
        }
        return descriptions.get(exploit_name, "")

    # -------------------- Logging & Utilities --------------------
    def _log(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        color_map = {"INFO": "#4ec9b0", "WARNING": "#dcdcaa", "ERROR": "#f48771", "SUCCESS": "#6a9955", "COMMAND": "#569cd6"}
        color = color_map.get(level, "#d4d4d4")
        self.console.insert(tk.END, f"[{timestamp}] ", "#569cd6")
        self.console.insert(tk.END, f"[{level}] ", color)
        self.console.insert(tk.END, f"{message}\n", "#d4d4d4")
        self.console.see(tk.END)
        self.root.update_idletasks()

    def _set_status(self, message, is_error=False):
        self.status_var.set(message)
        self._log(message, "ERROR" if is_error else "INFO")

    def _run_generic_cmd(self, cmd, timeout=120, shell=False, cwd=None):
        """Run external command and return (output, returncode)"""
        display_cmd = cmd if isinstance(cmd, str) else " ".join(cmd)
        self._log(f"Running: {display_cmd}", "COMMAND")
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                shell=shell,
                cwd=cwd,
                encoding="utf-8",
                errors="replace",
            )
            output = result.stdout + result.stderr
            if result.returncode == 0:
                self._log("Command succeeded", "SUCCESS")
            else:
                self._log(f"Command failed (code {result.returncode})", "ERROR")
            return output, result.returncode
        except Exception as e:
            self._log(f"Error: {e}", "ERROR")
            return "", -1

    def _run_fastboot(self, args, timeout=60):
        cmd = [self.fastboot_path] + args
        self._log(f"Running: {' '.join(cmd)}", "COMMAND")
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, encoding="utf-8", errors="replace")
            output = result.stdout + result.stderr
            if result.returncode != 0:
                self._log(f"Command failed (code {result.returncode}): {output[:200]}", "ERROR")
            else:
                self._log("Command completed successfully", "SUCCESS")
            return output, result.returncode
        except Exception as e:
            self._log(f"Error: {e}", "ERROR")
            return "", -1

    def _run_fastboot_async(self, args, callback=None, timeout=60):
        def target():
            self.running = True
            try:
                output, code = self._run_fastboot(args, timeout)
                if callback:
                    self.root.after(0, lambda: callback(output, code))
            finally:
                self.running = False

        threading.Thread(target=target, daemon=True).start()

    # -------------------- Fastboot Operations (existing) --------------------
    def _refresh_devices(self):
        self._log("Refreshing devices...")
        output, _ = self._run_fastboot(["devices"])
        devices = []
        for line in output.strip().split("\n"):
            if line.strip() and "\t" in line:
                serial, state = line.split("\t")
                devices.append((serial, state))
        self.info_text.delete(1.0, tk.END)
        if devices:
            self.info_text.insert(tk.END, "Connected Devices:\n")
            for serial, state in devices:
                self.info_text.insert(tk.END, f"  • {serial} - {state}\n")
            self.device_serial = devices[0][0]
            self._log(f"Found {len(devices)} device(s)", "SUCCESS")
        else:
            self.info_text.insert(tk.END, "No devices found in fastboot mode.\n")
            self.device_serial = None
            self._log("No devices found", "WARNING")

    def _get_device_info(self):
        if not self._check_device():
            return
        self._log("Retrieving device info...")
        output, _ = self._run_fastboot(["getvar", "all"])
        self.info_text.delete(1.0, tk.END)
        self.info_text.insert(tk.END, "=== DEVICE INFORMATION ===\n\n")
        for line in output.split("\n"):
            line = line.strip()
            if ":" in line:
                key, value = line.split(":", 1)
                key = key.strip()
                value = value.strip()
                self.info_text.insert(tk.END, f"{key}: {value}\n")
        self._log("Device info retrieved", "SUCCESS")

    def _get_unlock_data(self):
        if not self._check_device():
            return
        self._log("Retrieving unlock data...")
        output, code = self._run_fastboot(["oem", "get_unlock_data"])
        if code == 0:
            data_lines = []
            for line in output.split("\n"):
                if "Unlock data:" in line or "(bootloader)" in line:
                    parts = line.split(":", 1)
                    if len(parts) > 1:
                        d = parts[1].strip()
                        if d and len(d) > 10:
                            data_lines.append(d)
            if data_lines:
                full_data = "".join(data_lines)
                self._log(f"Unlock Data: {full_data}", "SUCCESS")
                messagebox.showinfo("Unlock Data", f"Copy this data to Motorola's unlock website:\n\n{full_data}\n\nVisit: https://motorola-global-portal.custhelp.com/app/standalone/bootloader/unlock-your-device-b")
            else:
                self._log("Could not parse unlock data", "WARNING")
                messagebox.showwarning("No Data", "Could not retrieve unlock data.")

    def _unlock_bootloader(self):
        if not self._check_device():
            return
        if not messagebox.askyesno("Warning", "⚠️ UNLOCKING WILL ERASE DATA. Continue?"):
            return
        key = self.unlock_key_var.get().strip()
        if key:
            self._log(f"Unlocking with key: {key[:8]}...", "INFO")
            self._run_fastboot_async(["oem", "unlock", key], self._unlock_callback)
        else:
            self._log("Attempting standard unlock (no key)...", "WARNING")
            if messagebox.askyesno("No Key", "Try 'fastboot oem unlock' without key?"):
                self._run_fastboot_async(["oem", "unlock"], self._unlock_callback)

    def _unlock_callback(self, output, code):
        if code == 0:
            self._log("Bootloader unlocked!", "SUCCESS")
            messagebox.showinfo("Success", "Bootloader unlocked successfully!")
        else:
            self._log("Unlock failed", "ERROR")
            messagebox.showerror("Failed", f"Unlock failed.\n\n{output[:200]}")

    def _lock_bootloader(self):
        if not self._check_device():
            return
        if not messagebox.askyesno("Warning", "⚠️ LOCKING WILL ERASE DATA. Continue?"):
            return
        self._log("Locking bootloader...", "WARNING")
        self._run_fastboot_async(["oem", "lock"], self._lock_callback)

    def _lock_callback(self, output, code):
        if code == 0:
            self._log("Bootloader locked!", "SUCCESS")
            messagebox.showinfo("Success", "Bootloader locked successfully!")
        else:
            self._log("Lock failed", "ERROR")
            messagebox.showerror("Failed", f"Lock failed.\n\n{output[:200]}")

    def _flash_firmware(self):
        if not self._check_device():
            return
        partition = self.partition_var.get()
        image_path = self.image_path_var.get()
        if not image_path or not os.path.exists(image_path):
            messagebox.showerror("Error", "Please select a valid image file.")
            return
        if not messagebox.askyesno("Confirm", f"Flash '{image_path}' to '{partition}'?"):
            return
        self._log(f"Flashing {image_path} to {partition}...", "INFO")
        self._run_fastboot_async(["flash", partition, image_path], self._flash_callback)

    def _flash_callback(self, output, code):
        if code == 0:
            self._log("Flash completed!", "SUCCESS")
            messagebox.showinfo("Success", "Partition flashed successfully!")
        else:
            self._log("Flash failed", "ERROR")
            messagebox.showerror("Failed", f"Flash failed.\n\n{output[:200]}")

    def _backup_partition(self):
        if not self._check_device():
            return
        partition = self.partition_var.get()
        default_name = f"{partition}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.img"
        file_path = filedialog.asksaveasfilename(defaultextension=".img", initialfile=default_name, filetypes=[("Image files", "*.img"), ("All files", "*.*")])
        if not file_path:
            return
        self._log(f"Backing up {partition} to {file_path}...", "INFO")
        self._run_fastboot_async(["save", partition, file_path], self._backup_callback)

    def _backup_callback(self, output, code):
        if code == 0:
            self._log("Backup completed!", "SUCCESS")
            messagebox.showinfo("Success", "Partition backup completed!")
        else:
            self._log("Backup failed", "ERROR")
            messagebox.showerror("Failed", f"Backup failed.\n\n{output[:200]}")

    def _reboot_device(self):
        if not self._check_device():
            return
        self._log("Rebooting device...", "INFO")
        self._run_fastboot_async(["reboot"], lambda o, c: self._log("Reboot command sent", "SUCCESS"))

    def _browse_image(self):
        file_path = filedialog.askopenfilename(title="Select firmware image", filetypes=[("Image files", "*.img"), ("All files", "*.*")])
        if file_path:
            self.image_path_var.set(file_path)

    def _check_device(self):
        if not self.device_serial:
            messagebox.showwarning("No Device", "No device detected in fastboot mode.")
            return False
        return True

    # -------------------- EDL Support --------------------
    def _reboot_edl(self):
        if self.device_serial:
            self._log("Using fastboot to reboot to EDL...", "INFO")
            self._run_fastboot_async(["oem", "edl"], lambda o, c: self._log("Reboot to EDL command sent" if c == 0 else "Failed", "SUCCESS" if c == 0 else "ERROR"))
        else:
            self._log("Attempting ADB reboot edl...", "INFO")
            self._run_generic_cmd(["adb", "reboot", "edl"])

    def _edl_info(self):
        if not self.edl_tool:
            messagebox.showerror("Tool Missing", "Install 'edl' from https://github.com/bkerler/edl")
            return
        self._log("Getting EDL info...", "INFO")
        output, code = self._run_generic_cmd([self.edl_tool, "info"])
        if code == 0:
            messagebox.showinfo("EDL Info", output[:1000])
        else:
            messagebox.showerror("EDL Info", f"Failed.\n\n{output[:200]}")

    def _edl_flash(self):
        if not self.edl_tool:
            messagebox.showerror("Tool Missing", "Install 'edl' tool")
            return
        partition = self.partition_var.get()
        image_path = self.image_path_var.get()
        if not image_path or not os.path.exists(image_path):
            messagebox.showerror("Error", "Select a valid image file.")
            return
        if not messagebox.askyesno("Confirm EDL Flash", f"Flash '{image_path}' to '{partition}' via EDL?"):
            return
        self._log(f"EDL flashing {image_path} to {partition}...", "INFO")
        self._run_generic_cmd([self.edl_tool, "w", partition, image_path], timeout=300)
        messagebox.showinfo("EDL Flash", "Flash command executed. Check console for details.")

    # -------------------- Root Patching --------------------
    def _patch_boot(self):
        if not self.magisk_tool:
            messagebox.showerror("Tool Missing", "Install Magisk (magiskboot or magisk binary)")
            return
        boot_img = filedialog.askopenfilename(title="Select boot.img", filetypes=[("Image files", "*.img"), ("All", "*.*")])
        if not boot_img:
            return
        out_img = filedialog.asksaveasfilename(defaultextension=".img", initialfile="patched_boot.img", title="Save patched image")
        if not out_img:
            return
        self._log(f"Patching {boot_img} with Magisk to {out_img}...", "INFO")
        cmd = [self.magisk_tool, "--patch", boot_img, out_img] if "magisk" in os.path.basename(self.magisk_tool).lower() else [self.magisk_tool, "patch", boot_img, out_img]

        def patch_thread():
            output, code = self._run_generic_cmd(cmd, timeout=120)
            self.root.after(0, lambda: self._patch_callback(output, code, out_img))

        threading.Thread(target=patch_thread, daemon=True).start()

    def _patch_callback(self, output, code, out_img):
        if code == 0:
            self._log(f"Patched boot image saved: {out_img}", "SUCCESS")
            messagebox.showinfo("Root Patching", f"Patched image saved to:\n{out_img}\nFlash it to boot partition.")
        else:
            self._log("Patching failed", "ERROR")
            messagebox.showerror("Patching Failed", f"Failed.\n\n{output[:200]}")

    # -------------------- Exploit Handlers (new) --------------------
    def _run_exploit(self):
        exploit = self.exploit_var.get()
        self._log(f"Running exploit: {exploit}", "INFO")
        if exploit == "MTK Unlock":
            self._mtk_unlock()
        elif exploit == "Motorola RSA Bypass":
            self._motorola_rsa_bypass()
        elif exploit == "Motorola Unlock (oem unlock)":
            self._exploit_oem_unlock()
        elif exploit == "Motorola Unlock (flashing unlock)":
            self._exploit_flashing_unlock()
        elif exploit == "Motorola Blankflash (EDL revive)":
            self._exploit_blankflash()
        elif exploit == "Motorola G4/G5 Exploit":
            self._exploit_g4g5()
        elif exploit == "Custom Exploit":
            self._custom_exploit()
        else:
            messagebox.showinfo("Exploit", "Selected exploit not implemented.")

    def _mtk_unlock(self):
        if not self.mtk_client:
            messagebox.showerror("Tool Missing", "Install mtkclient from https://github.com/bkerler/mtkclient")
            return
        if not messagebox.askyesno("MTK Unlock", "Device must be in BROM/preloader mode. Continue?"):
            return
        self._log("Running mtkclient unlock...", "INFO")
        cmd = [self.mtk_client, "da", "seccfg", "unlock"]

        def thread():
            o, c = self._run_generic_cmd(cmd, timeout=180)
            self.root.after(0, lambda: self._exploit_callback(o, c, "MTK Unlock"))

        threading.Thread(target=thread, daemon=True).start()

    def _motorola_rsa_bypass(self):
        script = filedialog.askopenfilename(title="Select RSA bypass script (optional)", filetypes=[("Python", "*.py"), ("All", "*.*")])
        if script:
            self._log(f"Running RSA bypass script: {script}", "INFO")

            def thread():
                o, c = self._run_generic_cmd([sys.executable, script], timeout=120)
                self.root.after(0, lambda: self._exploit_callback(o, c, "Motorola RSA Bypass"))

            threading.Thread(target=thread, daemon=True).start()
        else:
            messagebox.showinfo("RSA Bypass", "This exploit requires a Python script.\nSelect one now or implement your own.")

    def _exploit_oem_unlock(self):
        if not self._check_device():
            messagebox.showwarning("No Device", "Device must be in fastboot mode.")
            return
        if not messagebox.askyesno("OEM Unlock", "Attempt 'fastboot oem unlock'? This may erase data."):
            return
        self._log("Running fastboot oem unlock (no key)...", "INFO")
        self._run_fastboot_async(["oem", "unlock"], self._exploit_callback_fastboot)

    def _exploit_flashing_unlock(self):
        if not self._check_device():
            messagebox.showwarning("No Device", "Device must be in fastboot mode.")
            return
        if not messagebox.askyesno("Flashing Unlock", "Attempt 'fastboot flashing unlock'? This may erase data."):
            return
        self._log("Running fastboot flashing unlock...", "INFO")
        self._run_fastboot_async(["flashing", "unlock"], self._exploit_callback_fastboot)

    def _exploit_blankflash(self):
        if not self.blankflash_tool:
            messagebox.showerror("Tool Missing", "Blankflash tool not found. Place it in PATH or select manually.")
            tool = filedialog.askopenfilename(title="Select blankflash executable", filetypes=[("Executable", "*"), ("All", "*.*")])
            if not tool:
                return
            self.blankflash_tool = tool
        cwd = os.path.dirname(self.blankflash_tool)
        if not messagebox.askyesno("Blankflash", "This will flash blankflash to the device.\nEnsure device is in EDL mode.\nContinue?"):
            return
        self._log(f"Running blankflash from {cwd}...", "INFO")

        def thread():
            o, c = self._run_generic_cmd(self.blankflash_tool, timeout=300, shell=True, cwd=cwd)
            self.root.after(0, lambda: self._exploit_callback(o, c, "Blankflash"))

        threading.Thread(target=thread, daemon=True).start()

    def _exploit_g4g5(self):
        messagebox.showinfo("G4/G5 Exploit", "This is a placeholder for device-specific vulnerabilities.\nYou can integrate a Python script or tool for Motorola G4/G5 series.")
        script = filedialog.askopenfilename(title="Select G4/G5 exploit script", filetypes=[("Python", "*.py"), ("All", "*.*")])
        if script:
            self._log(f"Running G4/G5 exploit script: {script}", "INFO")

            def thread():
                o, c = self._run_generic_cmd([sys.executable, script], timeout=120)
                self.root.after(0, lambda: self._exploit_callback(o, c, "G4/G5 Exploit"))

            threading.Thread(target=thread, daemon=True).start()

    def _custom_exploit(self):
        script = filedialog.askopenfilename(title="Select exploit script", filetypes=[("Python", "*.py"), ("All", "*.*")])
        if not script:
            return
        if not messagebox.askyesno("Custom Exploit", f"Run {script}?"):
            return
        self._log(f"Running custom exploit: {script}", "INFO")

        def thread():
            o, c = self._run_generic_cmd([sys.executable, script], timeout=300)
            self.root.after(0, lambda: self._exploit_callback(o, c, "Custom Exploit"))

        threading.Thread(target=thread, daemon=True).start()

    def _exploit_callback(self, output, code, exploit_name):
        if code == 0:
            self._log(f"{exploit_name} completed successfully!", "SUCCESS")
            messagebox.showinfo("Exploit", f"{exploit_name} succeeded!")
        else:
            self._log(f"{exploit_name} failed", "ERROR")
            messagebox.showerror("Exploit Failed", f"{exploit_name} failed.\n\n{output[:500]}")

    def _exploit_callback_fastboot(self, output, code):
        if code == 0:
            self._log("Fastboot command succeeded!", "SUCCESS")
            messagebox.showinfo("Success", "Fastboot command executed successfully.\nCheck device status.")
        else:
            self._log("Fastboot command failed", "ERROR")
            messagebox.showerror("Failed", f"Command failed.\n\n{output[:200]}")

    # -------------------- Console Menu --------------------
    def _setup_console_menu(self):
        menu = tk.Menu(self.console, tearoff=0)
        menu.add_command(label="Clear", command=lambda: self.console.delete(1.0, tk.END))
        menu.add_command(label="Copy", command=self._copy_console)
        menu.add_command(label="Save Log", command=self._save_log)
        self.console.bind("<Button-3>", lambda e: menu.post(e.x_root, e.y_root))

    def _copy_console(self):
        try:
            selected = self.console.get(tk.SEL_FIRST, tk.SEL_LAST)
            self.root.clipboard_clear()
            self.root.clipboard_append(selected)
        except tk.TclError:
            pass

    def _save_log(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".log", filetypes=[("Log files", "*.log"), ("Text", "*.txt")])
        if file_path:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(self.console.get(1.0, tk.END))
            self._log(f"Log saved to {file_path}")


def main():
    root = tk.Tk()
    app = MotorolaBootloaderUtility(root)
    root.after(500, app._refresh_devices)
    root.mainloop()


if __name__ == "__main__":
    main()

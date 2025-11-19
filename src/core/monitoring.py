import time
import subprocess
from threading import Thread
import socket

class MonitorDaemon:
    def __init__(self, app):
        self.app = app
        self.running = False
        self.thread = None

    def start(self):
        self.running = True
        # Use after() instead of thread to stay in main GUI thread
        self._schedule_check()

    def stop(self):
        self.running = False

    def _schedule_check(self):
        """Schedule the next check using tkinter's after() method"""
        if self.running:
            self.check_device_connectivity()
            self.check_pc_status()
            # Schedule next check in 5 seconds
            self.app.after(5000, self._schedule_check)

    def check_device_connectivity(self):
        try:
            # Use adb to check for connected devices
            result = subprocess.run(["adb", "devices", "-l"], capture_output=True, text=True, check=True)
            lines = result.stdout.strip().split('\n')[1:]
            devices = []
            devices_info = []

            for line in lines:
                if "device" in line and "unauthorized" not in line:
                    parts = line.split()
                    serial = parts[0]

                    # Extract model from the device line
                    model_part = [p for p in parts if p.startswith('model:')]
                    if model_part:
                        model = model_part[0].split(':')[1]
                    else:
                        # Try to get model via getprop
                        model = self.get_device_property(serial, "ro.product.model")

                    devices.append(f"{model} ({serial})")
                    devices_info.append({
                        'serial': serial,
                        'model': model,
                        'display_name': f"{model} ({serial})"
                    })

            if devices:
                status_text = f"{len(devices)} Connected" if len(devices) > 1 else "1 Connected"
                self.app.device_status_label.config(text=status_text)
                self.app.device_status_indicator.config(fg=self.app.colors['status_connected'])
                self.app.update_device_dropdowns(devices)
                self.app.update_device_list(devices_info)
                # Update flash device dropdown
                self.app.flash_device_dropdown['values'] = devices
                if len(devices) == 1:
                    self.app.flash_device_dropdown.set(devices[0])

            else:
                self.app.device_status_label.config(text="No devices")
                self.app.device_status_indicator.config(fg=self.app.colors['status_disconnected'])
                self.app.update_device_dropdowns([])
                self.app.update_device_list([])
                # Clear flash device dropdown
                self.app.flash_device_dropdown['values'] = []
                self.app.flash_device_dropdown.set('')

        except (subprocess.CalledProcessError, FileNotFoundError):
            self.app.device_status_label.config(text="ADB Not Found")
            self.app.device_status_indicator.config(fg=self.app.colors['warning'])
            self.app.update_device_dropdowns([])
            self.app.update_device_list([])

    def get_device_property(self, serial, prop):
        try:
            result = subprocess.run(["adb", "-s", serial, "shell", "getprop", prop], capture_output=True, text=True, check=True)
            return result.stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            return "N/A"

    def get_pc_ip_address(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            # doesn't even have to be reachable
            s.connect(('10.255.255.255', 1))
            IP = s.getsockname()[0]
        except Exception:
            IP = '127.0.0.1'
        finally:
            s.close()
        return IP

    def check_pc_status(self):
        # For now, we'll just assume the PC is online if the app is running
        self.app.pc_status_label.config(text="Online")
        self.app.pc_status_indicator.config(fg=self.app.colors['status_online'])
        pc_ip = self.get_pc_ip_address()
        self.app.ip_label.config(text=pc_ip)


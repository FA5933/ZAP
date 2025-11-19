import tkinter as tk  # Required for tk.END constant
from tkinter import filedialog
import configparser
from threading import Thread
import os

from gui.main_window import App
from core.monitoring import MonitorDaemon
from core.polarion import PolarionManager
from core.zybot import ZybotExecutor
from core.email_notifier import EmailNotifier
from core.artifactory import ArtifactoryManager
from utils.logger import Logger

class MainApplication:
    def __init__(self):
        self.config = configparser.ConfigParser()
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config.ini')
        self.config.read(config_path)

        self.app = App()
        self.logger = Logger(self.app.log_text)

        self.polarion_manager = PolarionManager(self.config, self.logger)
        self.zybot_executor = ZybotExecutor(self.config, self.logger)
        self.email_notifier = EmailNotifier(self.config, self.logger)
        self.artifactory_manager = ArtifactoryManager(self.config, self.logger)

        self.monitor_daemon = MonitorDaemon(self.app)
        self.monitor_daemon.start()

        self.current_thread = None

        self.setup_callbacks()

    def setup_callbacks(self):
        self.app.download_sttls_button.config(command=self.run_download_sttls)
        self.app.run_zybot_button.config(command=self.run_zybot_tests)

        # JFrog Artifactory callbacks
        self.app.download_build_button.config(command=self.run_download_build)
        self.app.download_flash_button.config(command=self.run_download_and_flash_build)
        self.app.browse_button.config(command=self.browse_local_file)
        self.app.flash_local_button.config(command=self.run_flash_local_build)

        self.app.kill_button.config(command=self.kill_current_process)

        # Add callbacks for device dropdowns to update the command
        for dropdown in self.app.device_dropdowns.values():
            dropdown.bind("<<ComboboxSelected>>", self.update_zybot_command_display)
        self.app.polarion_url_entry.bind("<KeyRelease>", self.update_zybot_command_display)

    def update_zybot_command_display(self, event=None):
        polarion_run_name = self.app.polarion_url_entry.get().split('/')[-1]
        devices = {dut: dropdown.get() for dut, dropdown in self.app.device_dropdowns.items() if dropdown.get()}
        sttls = getattr(self, 'sttls', [])

        command = self.zybot_executor.get_command_string(polarion_run_name, devices, sttls)

        self.app.zybot_command_text.configure(state='normal')
        self.app.zybot_command_text.delete(1.0, tk.END)
        self.app.zybot_command_text.insert(tk.END, command)
        self.app.zybot_command_text.configure(state='disabled')

    def run_download_sttls(self):
        self.current_thread = Thread(target=self._download_sttls_thread)
        self.current_thread.start()

    def _download_sttls_thread(self):
        test_run_url = self.app.polarion_url_entry.get()
        if not test_run_url:
            self.logger.log("Polarion Test Run URL is required.", level='error')
            return
        self.sttls = self.polarion_manager.download_sttls(test_run_url)
        self.update_zybot_command_display()

    def run_zybot_tests(self):
        self.current_thread = Thread(target=self._run_zybot_tests_thread)
        self.current_thread.start()

    def _run_zybot_tests_thread(self):
        polarion_run_name = self.app.polarion_url_entry.get().split('/')[-1]
        devices = {dut: dropdown.get() for dut, dropdown in self.app.device_dropdowns.items()}

        if not hasattr(self, 'sttls') or not self.sttls:
            self.logger.log("No STTLs downloaded. Please download STTLs first.", level='error')
            return

        result = self.zybot_executor.run_tests(polarion_run_name, devices, self.sttls)

        self.polarion_manager.upload_results(self.app.polarion_url_entry.get(), {"result": result})

        subject = f"Test Run {polarion_run_name} Completed"
        body = f"The test run has completed with status: {result}."
        self.email_notifier.send_notification(subject, body)

        self.artifactory_manager.upload_logs(self.logger.log_file)

    def _get_selected_device_serial(self):
        """Extract device serial from the selected flash device dropdown value

        Returns:
            str: Device serial number, or None if no device selected
        """
        selected = self.app.flash_device_dropdown.get()
        if not selected:
            return None
        # Format is "Model (serial)" - extract serial from parentheses
        if '(' in selected and ')' in selected:
            return selected.split('(')[1].split(')')[0]
        return None

    def run_download_build(self):
        """Download build only without flashing"""
        self.current_thread = Thread(target=self._download_build_thread)
        self.current_thread.start()

    def _download_build_thread(self):
        build_link = self.app.jfrog_link_entry.get()
        if not build_link:
            self.logger.log("JFrog build URL is required.", level='error')
            return
        downloaded_file = self.artifactory_manager.download_build(build_link)
        if downloaded_file:
            self.logger.log(f"✅ Download complete. File saved to: {downloaded_file}", level='success')

    def run_download_and_flash_build(self):
        """Download and immediately flash the build"""
        self.current_thread = Thread(target=self._download_and_flash_thread)
        self.current_thread.start()

    def _download_and_flash_thread(self):
        build_link = self.app.jfrog_link_entry.get()
        if not build_link:
            self.logger.log("JFrog build URL is required.", level='error')
            return

        device_serial = self._get_selected_device_serial()
        if not device_serial:
            self.logger.log("Please select a target device.", level='error')
            return

        self.artifactory_manager.download_and_flash_build(build_link, device_serial)

    def browse_local_file(self):
        """Open file browser to select a local build file"""
        file_path = filedialog.askopenfilename(
            title="Select Build File",
            filetypes=[
                ("ZIP files", "*.zip"),
                ("All files", "*.*")
            ],
            initialdir=os.path.join(os.getcwd(), "builds")
        )
        if file_path:
            self.app.local_file_entry.delete(0, tk.END)
            self.app.local_file_entry.insert(0, file_path)

    def run_flash_local_build(self):
        """Flash an existing local build file"""
        self.current_thread = Thread(target=self._flash_local_thread)
        self.current_thread.start()

    def _flash_local_thread(self):
        file_path = self.app.local_file_entry.get()
        if not file_path:
            self.logger.log("Please select a local build file.", level='error')
            return

        device_serial = self._get_selected_device_serial()
        if not device_serial:
            self.logger.log("Please select a target device.", level='error')
            return

        self.artifactory_manager.flash_build(file_path, device_serial)

    def kill_current_process(self):
        if self.current_thread and self.current_thread.is_alive():
            # This is a bit of a hack. In a real application, you'd want a more graceful
            # way to stop the thread, e.g., by using a shared flag.
            # For now, we can't directly kill a thread in Python, so we'll just log it.
            self.logger.log("Termination request received. Note: Cannot forcefully kill a running thread.", level='error')
            # In a more complex app, you might try to raise an exception in the thread
            # or use other mechanisms to signal it to stop.

    def run(self):
        self.app.mainloop()
        self.monitor_daemon.stop()

if __name__ == "__main__":
    main_app = MainApplication()
    main_app.run()


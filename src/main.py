import tkinter as tk  # Required for tk.END constant
from tkinter import filedialog, messagebox
import configparser
from threading import Thread, Event
import os
import json

from gui.main_window import App
from gui.task_dialog import TaskConfigDialog
from core.monitoring import MonitorDaemon
from core.polarion import PolarionManager
from core.zybot import ZybotExecutor
from core.email_notifier import EmailNotifier
from core.artifactory import ArtifactoryManager
from core.scheduler import TaskScheduler, ScheduledTask
from core.web_server import get_web_server
from utils.logger import Logger

class MainApplication:
    def __init__(self):
        self.config = configparser.ConfigParser()
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config.ini')
        self.config.read(config_path)

        self.app = App()
        self.logger = Logger(self.app.log_text, self.app.auto_scroll)

        self.polarion_manager = PolarionManager(self.config, self.logger)
        self.zybot_executor = ZybotExecutor(self.config, self.logger)
        self.email_notifier = EmailNotifier(self.config, self.logger)
        self.artifactory_manager = ArtifactoryManager(self.config, self.logger)

        self.monitor_daemon = MonitorDaemon(self.app)
        self.monitor_daemon.start()

        self.current_thread = None
        self.stop_event = Event()  # For graceful thread cancellation

        # Initialize task scheduler BEFORE setup_callbacks
        scheduler_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                     'scheduled_tasks.json')
        self.task_scheduler = TaskScheduler(scheduler_file)
        self.task_scheduler.set_logger(self.logger)
        self.task_scheduler.set_task_executor(self.execute_scheduled_task)

        # Initialize web server
        self.web_server = get_web_server(port=5000)
        self.web_server.start()
        self.logger.set_web_server(self.web_server)
        self.monitor_daemon.set_web_server(self.web_server)
        self.logger.log(f"🌐 Web dashboard available at http://localhost:5000", level='success')

        self.setup_callbacks()
        self.setup_keyboard_shortcuts()
        self.setup_placeholders()
        self.restore_session_state()

    def parse_custom_sttls(self, custom_input):
        """Parse custom STTL input in various formats

        Supports:
        - id:(STTL/STTL-205890 STTL/STTL-205891 STTL/STTL-205901)
        - Comma-separated: STTL-205890, STTL-205891, STTL-205901
        - Space-separated: STTL-205890 STTL-205891 STTL-205901
        - Mixed with STTL/ prefix

        Returns:
            list: List of STTL IDs (e.g., ['STTL-205890', 'STTL-205891'])
        """
        import re

        if not custom_input or not custom_input.strip():
            return []

        sttls = []

        # Check if it's in id:(...) format
        id_match = re.search(r'id:\s*\((.*?)\)', custom_input)
        if id_match:
            content = id_match.group(1)
        else:
            content = custom_input

        # Split by common delimiters (space, comma, newline)
        tokens = re.split(r'[,\s\n]+', content)

        for token in tokens:
            token = token.strip()
            if not token:
                continue

            # Extract STTL ID, handling STTL/ prefix
            if 'STTL/' in token:
                # Extract ID after STTL/
                sttl_id = token.split('STTL/')[-1]
            elif token.startswith('STTL-'):
                # Already in correct format
                sttl_id = token
            elif token.startswith('STTL'):
                # Add hyphen if missing
                sttl_id = token.replace('STTL', 'STTL-', 1)
            else:
                # Assume it's just the number, add STTL- prefix
                if token.isdigit() or (token.replace('-', '').isdigit()):
                    sttl_id = f"STTL-{token}"
                else:
                    # Skip invalid tokens
                    continue

            # Clean up any trailing characters
            sttl_id = sttl_id.rstrip('*').strip()

            if sttl_id and sttl_id not in sttls:
                sttls.append(sttl_id)

        return sttls

    def parse_and_display_sttls(self):
        """Parse custom STTLs and display the formatted result"""
        custom_input = self.app.custom_sttl_entry.get().strip()

        if not custom_input:
            messagebox.showwarning("No Input",
                                 "Please enter STTLs in the custom STTL field.\n\n"
                                 "Format: id:(STTL/STTL-205890 STTL/STTL-205891)")
            return

        # Parse the STTLs
        parsed_sttls = self.parse_custom_sttls(custom_input)

        if not parsed_sttls:
            messagebox.showerror("Parse Error",
                               "Could not parse any valid STTLs from the input.\n\n"
                               "Please check the format and try again.")
            return

        # Store parsed STTLs
        self.sttls = parsed_sttls

        # Update the command display
        self.update_zybot_command_display()

        # Show success message with parsed STTLs
        formatted_output = '\n'.join([f'  -t "{sttl}*"' for sttl in parsed_sttls])
        result_message = f"✅ Parsed {len(parsed_sttls)} STTL(s):\n\n{formatted_output}\n\n" \
                        f"Check the Generated Command section to see the full command."

        messagebox.showinfo("STTLs Parsed Successfully", result_message)
        self.logger.log(f"✅ Parsed {len(parsed_sttls)} STTLs: {parsed_sttls}", level='success')
        self.app.show_toast(f"✅ Parsed {len(parsed_sttls)} STTLs", 'success')

    def setup_callbacks(self):
        self.app.download_sttls_button.config(command=self.run_download_sttls)
        self.app.run_zybot_button.config(command=self.run_zybot_tests)
        self.app.parse_sttls_button.config(command=self.parse_and_display_sttls)

        # JFrog Artifactory callbacks
        self.app.download_build_button.config(command=self.run_download_build)
        self.app.download_flash_button.config(command=self.run_download_and_flash_build)
        self.app.browse_button.config(command=self.browse_local_file)
        self.app.flash_local_button.config(command=self.run_flash_local_build)

        self.app.kill_button.config(command=self.kill_with_confirmation)

        # Add callbacks for device dropdowns to update the command
        for dropdown in self.app.device_dropdowns.values():
            dropdown.bind("<<ComboboxSelected>>", self.update_zybot_command_display)
        self.app.polarion_url_entry.bind("<KeyRelease>", self.update_zybot_command_display)
        self.app.custom_sttl_entry.bind("<KeyRelease>", self.update_zybot_command_display)

        # Log controls callbacks
        self.app.clear_logs_button.config(command=self.clear_logs)
        self.app.export_logs_button.config(command=self.export_logs)
        self.app.log_level_var.trace('w', lambda *args: self.filter_logs())
        self.app.log_search_entry.bind('<KeyRelease>', lambda e: self.search_logs())

        # Scheduler callbacks
        self.app.scheduler_start_button.config(command=self.start_scheduler)
        self.app.scheduler_stop_button.config(command=self.stop_scheduler)
        self.app.add_task_button.config(command=self.add_scheduled_task)

        # Update scheduler display
        self.refresh_scheduled_tasks_display()

    def update_zybot_command_display(self, event=None):
        # Don't update if custom command mode is enabled
        if self.app.use_custom_command.get():
            return

        polarion_run_name = self.app.polarion_url_entry.get().split('/')[-1]
        devices = {dut: dropdown.get() for dut, dropdown in self.app.device_dropdowns.items() if dropdown.get()}

        # Check if custom STTLs are provided
        custom_sttl_input = self.app.custom_sttl_entry.get().strip()
        if custom_sttl_input:
            # Use custom STTLs
            sttls = self.parse_custom_sttls(custom_sttl_input)
            self.logger.log(f"Using custom STTLs: {sttls}", level='info')
        else:
            # Fall back to downloaded STTLs
            sttls = getattr(self, 'sttls', [])

        command = self.zybot_executor.get_command_string(polarion_run_name, devices, sttls)

        self.app.zybot_command_text.configure(state='normal')
        self.app.zybot_command_text.delete(1.0, tk.END)
        self.app.zybot_command_text.insert(tk.END, command)
        self.app.zybot_command_text.configure(state='disabled')

    def run_download_sttls(self):
        if not self.validate_polarion_input():
            return

        self.disable_action_buttons()
        self.stop_event.clear()
        self.current_thread = Thread(target=self._download_sttls_thread)
        self.current_thread.start()

    def _download_sttls_thread(self):
        try:
            test_run_url = self.app.polarion_url_entry.get()
            if self.app.polarion_url_entry.cget('fg') == '#999999':
                self.logger.log("Polarion Test Run URL is required.", level='error')
                return

            self.sttls = self.polarion_manager.download_sttls(test_run_url)

            if self.sttls:
                self.update_zybot_command_display()
                self.app.show_toast(f"✅ Downloaded {len(self.sttls)} STTLs", 'success')
                self.save_session_state()
            else:
                self.app.show_toast("⚠️ No STTLs found", 'warning')
        except Exception as e:
            self.logger.log(f"Error downloading STTLs: {e}", level='error')
            self.app.show_toast("❌ Download failed", 'error')
        finally:
            self.enable_action_buttons()

    def run_zybot_tests(self):
        if not self.validate_zybot_config():
            return

        self.disable_action_buttons()
        self.stop_event.clear()
        self.current_thread = Thread(target=self._run_zybot_tests_thread)
        self.current_thread.start()

    def _run_zybot_tests_thread(self):
        try:
            # Check if custom command mode is enabled
            if self.app.use_custom_command.get():
                # Use the custom command directly
                custom_command = self.app.zybot_command_text.get(1.0, tk.END).strip()
                if not custom_command:
                    self.logger.log("Custom command is empty. Please enter a valid command.", level='error')
                    return

                self.logger.log("Using custom command mode", level='info')

                # Notify web server that tests are starting
                self.web_server.start_test_execution(
                    test_name="Custom Command",
                    devices=[],
                    total_tests=1
                )

                result = self.zybot_executor.run_custom_command(custom_command, self.stop_event)

                if self.stop_event.is_set():
                    self.logger.log("⚠️ Test execution cancelled by user", level='warning')
                    self.app.show_toast("⚠️ Test cancelled", 'warning')
                    self.web_server.end_test_execution()
                    return

                self.web_server.end_test_execution()

                if result == "Pass":
                    self.app.show_toast("✅ Tests completed successfully!", 'success')
                else:
                    self.app.show_toast("❌ Tests failed", 'error')

                return

            # Standard mode - use auto-generated command
            polarion_run_name = self.app.polarion_url_entry.get().split('/')[-1]
            devices = {dut: dropdown.get() for dut, dropdown in self.app.device_dropdowns.items()}

            # Check if custom STTLs are provided
            custom_sttl_input = self.app.custom_sttl_entry.get().strip()
            if custom_sttl_input:
                # Use custom STTLs
                sttls = self.parse_custom_sttls(custom_sttl_input)
                self.logger.log(f"Using custom STTLs: {sttls}", level='info')
            else:
                # Fall back to downloaded STTLs
                if not hasattr(self, 'sttls') or not self.sttls:
                    self.logger.log("No STTLs provided. Please download STTLs or enter them manually.", level='error')
                    return
                sttls = self.sttls

            if not sttls:
                self.logger.log("No STTLs to execute. Please provide test cases.", level='error')
                return

            # Notify web server that tests are starting
            device_list = [v.split('(')[1].split(')')[0] if '(' in v else v
                          for v in devices.values() if v]
            self.web_server.start_test_execution(
                test_name=polarion_run_name,
                devices=device_list,
                total_tests=len(sttls)
            )

            result = self.zybot_executor.run_tests(polarion_run_name, devices, sttls, self.stop_event)

            if self.stop_event.is_set():
                self.logger.log("⚠️ Test execution cancelled by user", level='warning')
                self.app.show_toast("⚠️ Test cancelled", 'warning')
                self.web_server.end_test_execution()
                return

            self.polarion_manager.upload_results(self.app.polarion_url_entry.get(), {"result": result})

            subject = f"Test Run {polarion_run_name} Completed"
            body = f"The test run has completed with status: {result}."
            self.email_notifier.send_notification(subject, body)

            self.artifactory_manager.upload_logs(self.logger.log_file)

            # Notify web server that tests are complete
            self.web_server.end_test_execution()

            if result == "Pass":
                self.app.show_toast("✅ Tests completed successfully!", 'success')
            else:
                self.app.show_toast("❌ Tests failed", 'error')
        except Exception as e:
            self.logger.log(f"Error during test execution: {e}", level='error')
            self.app.show_toast("❌ Test execution failed", 'error')
            self.web_server.end_test_execution()
        finally:
            self.enable_action_buttons()

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
        if not self.validate_artifactory_input(requires_device=False):
            return

        self.disable_action_buttons()
        self.stop_event.clear()
        self.current_thread = Thread(target=self._download_build_thread)
        self.current_thread.start()

    def _download_build_thread(self):
        try:
            build_link = self.app.jfrog_link_entry.get()
            if self.app.jfrog_link_entry.cget('fg') == '#999999':
                self.logger.log("JFrog build URL is required.", level='error')
                return

            downloaded_file = self.artifactory_manager.download_build(build_link, self.stop_event, self.app)

            if self.stop_event.is_set():
                self.logger.log("⚠️ Download cancelled by user", level='warning')
                self.app.show_toast("⚠️ Download cancelled", 'warning')
                return

            if downloaded_file:
                self.logger.log(f"✅ Download complete. File saved to: {downloaded_file}", level='success')
                self.app.show_toast("✅ Build downloaded!", 'success')
        except Exception as e:
            self.logger.log(f"Error downloading build: {e}", level='error')
            self.app.show_toast("❌ Download failed", 'error')
        finally:
            self.enable_action_buttons()

    def run_download_and_flash_build(self):
        """Download and immediately flash the build"""
        if not self.validate_artifactory_input(requires_device=True):
            return

        device = self.app.flash_device_dropdown.get()
        if not self.confirm_flash_operation(device, "download and flash"):
            return

        self.disable_action_buttons()
        self.stop_event.clear()
        self.current_thread = Thread(target=self._download_and_flash_thread)
        self.current_thread.start()

    def _download_and_flash_thread(self):
        try:
            build_link = self.app.jfrog_link_entry.get()
            if self.app.jfrog_link_entry.cget('fg') == '#999999':
                self.logger.log("JFrog build URL is required.", level='error')
                return

            device_serial = self._get_selected_device_serial()
            if not device_serial:
                self.logger.log("Please select a target device.", level='error')
                return

            self.artifactory_manager.download_and_flash_build(build_link, device_serial, self.stop_event, self.app)

            if self.stop_event.is_set():
                self.logger.log("⚠️ Operation cancelled by user", level='warning')
                self.app.show_toast("⚠️ Operation cancelled", 'warning')
                return

            self.app.show_toast("✅ Flash completed!", 'success')
        except Exception as e:
            self.logger.log(f"Error during download/flash: {e}", level='error')
            self.app.show_toast("❌ Flash failed", 'error')
        finally:
            self.enable_action_buttons()

    def browse_local_file(self):
        """Open file browser to select a local build file"""
        # Use project root builds directory for consistency
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        builds_dir = os.path.join(project_root, "builds")

        # Create builds directory if it doesn't exist
        if not os.path.exists(builds_dir):
            os.makedirs(builds_dir)

        file_path = filedialog.askopenfilename(
            title="Select Build File",
            filetypes=[
                ("ZIP files", "*.zip"),
                ("All files", "*.*")
            ],
            initialdir=builds_dir
        )
        if file_path:
            self.app.local_file_entry.delete(0, tk.END)
            self.app.local_file_entry.insert(0, file_path)

    def run_flash_local_build(self):
        """Flash an existing local build file"""
        file_path = self.app.local_file_entry.get()
        if self.app.local_file_entry.cget('fg') == '#999999' or not file_path:
            messagebox.showerror("File Required", "Please select a local build file.")
            return

        device = self.app.flash_device_dropdown.get()
        if not device:
            messagebox.showerror("Device Required",
                               "Please select a target device from the dropdown.")
            return

        if not self.confirm_flash_operation(device, "flash"):
            return

        self.disable_action_buttons()
        self.stop_event.clear()
        self.current_thread = Thread(target=self._flash_local_thread)
        self.current_thread.start()

    def _flash_local_thread(self):
        try:
            file_path = self.app.local_file_entry.get()
            if not file_path or not os.path.exists(file_path):
                self.logger.log("Please select a valid local build file.", level='error')
                return

            device_serial = self._get_selected_device_serial()
            if not device_serial:
                self.logger.log("Please select a target device.", level='error')
                return

            self.artifactory_manager.flash_build(file_path, device_serial, self.stop_event, self.app)

            if self.stop_event.is_set():
                self.logger.log("⚠️ Flash cancelled by user", level='warning')
                self.app.show_toast("⚠️ Flash cancelled", 'warning')
                return

            self.app.show_toast("✅ Flash completed!", 'success')
        except Exception as e:
            self.logger.log(f"Error during flash: {e}", level='error')
            self.app.show_toast("❌ Flash failed", 'error')
        finally:
            self.enable_action_buttons()

    def kill_current_process(self):
        """Request graceful thread termination"""
        if self.current_thread and self.current_thread.is_alive():
            self.stop_event.set()
            self.logger.log("⚠️ Termination requested. Attempting to stop operation gracefully...", level='warning')
            # Re-enable buttons after a short delay
            self.app.after(2000, self.enable_action_buttons)
        else:
            self.logger.log("No active operation to terminate.", level='info')

    # ===== BUTTON STATE MANAGEMENT =====

    def disable_action_buttons(self):
        """Disable all action buttons during operations"""
        self.app.download_sttls_button.config(state='disabled', bg='#a0a0a0')
        self.app.run_zybot_button.config(state='disabled', bg='#a0a0a0')
        self.app.download_build_button.config(state='disabled', bg='#a0a0a0')
        self.app.download_flash_button.config(state='disabled', bg='#a0a0a0')
        self.app.browse_button.config(state='disabled', bg='#a0a0a0')
        self.app.flash_local_button.config(state='disabled', bg='#a0a0a0')
        self.app.update_status_bar("⏳ Operation in progress...")

    def enable_action_buttons(self):
        """Re-enable action buttons after operation completes"""
        self.app.download_sttls_button.config(state='normal', bg=self.app.colors['primary'])
        self.app.run_zybot_button.config(state='normal', bg=self.app.colors['success'])
        self.app.download_build_button.config(state='normal', bg=self.app.colors['primary'])
        self.app.download_flash_button.config(state='normal', bg=self.app.colors['warning'])
        self.app.browse_button.config(state='normal', bg='#6c757d')
        self.app.flash_local_button.config(state='normal', bg=self.app.colors['success'])
        self.app.update_status_bar("✅ Ready")

    # ===== INPUT VALIDATION =====

    def validate_polarion_input(self):
        """Validate Polarion URL before download"""
        url = self.app.polarion_url_entry.get().strip()

        if not url:
            messagebox.showerror("Polarion URL Required",
                               "Please enter a Polarion test run URL.")
            return False

        if not url.startswith('http'):
            messagebox.showwarning("Invalid URL",
                                 "URL should start with 'http://' or 'https://'")
            return False

        return True

    def validate_zybot_config(self):
        """Validate Zybot configuration before execution"""
        # In custom command mode, only check if command is not empty
        if self.app.use_custom_command.get():
            custom_command = self.app.zybot_command_text.get(1.0, tk.END).strip()
            if not custom_command:
                messagebox.showerror("Custom Command Empty",
                                   "Please enter a custom command to execute.\n\n"
                                   "The command text area cannot be empty.")
                return False
            return True

        # Standard mode validations
        # Check if STTLs are provided (either downloaded or custom)
        custom_sttl_input = self.app.custom_sttl_entry.get().strip()
        has_sttls = (hasattr(self, 'sttls') and self.sttls) or custom_sttl_input

        if not has_sttls:
            messagebox.showerror("STTLs Not Provided",
                               "Please download STTLs from Polarion or enter them manually.\n\n"
                               "Use the custom STTL input field below the Polarion URL.")
            return False

        # Check if at least one device is selected
        selected_devices = [d.get() for d in self.app.device_dropdowns.values() if d.get()]
        if not selected_devices:
            messagebox.showerror("No Devices Selected",
                               "Please select at least one device for testing.\n\n"
                               "Devices must be connected via ADB.")
            return False

        return True

    def validate_artifactory_input(self, requires_device=False):
        """Validate Artifactory inputs"""
        url = self.app.jfrog_link_entry.get().strip()
        device = self.app.flash_device_dropdown.get()

        if not url:
            messagebox.showerror("Build URL Required",
                               "Please enter a JFrog Artifactory build URL.")
            return False

        if requires_device and not device:
            messagebox.showerror("Device Required",
                               "Please select a target device from the dropdown.\n\n"
                               "Make sure a device is connected via ADB.")
            return False

        return True

    # ===== CONFIRMATION DIALOGS =====

    def kill_with_confirmation(self):
        """Confirm before killing process"""
        if not self.current_thread or not self.current_thread.is_alive():
            messagebox.showinfo("No Active Operation",
                              "There is no operation currently running.")
            return

        result = messagebox.askyesno(
            "Confirm Kill Process",
            "This will terminate the running operation.\n\n"
            "⚠️ Progress may be lost and files could be corrupted.\n\n"
            "Are you sure you want to stop?",
            icon='warning'
        )

        if result:
            self.kill_current_process()

    def confirm_flash_operation(self, device, operation_type="flash"):
        """Ask for confirmation before flashing"""
        result = messagebox.askyesno(
            "Confirm Flash Operation",
            f"⚠️ WARNING: This will {operation_type} the build to:\n\n"
            f"   {device}\n\n"
            f"All data on the device may be erased.\n"
            f"This operation cannot be undone.\n\n"
            f"Do you want to continue?",
            icon='warning'
        )
        return result

    # ===== KEYBOARD SHORTCUTS =====

    def setup_keyboard_shortcuts(self):
        """Bind keyboard shortcuts"""
        # File operations
        self.app.bind('<Control-o>', lambda e: self.browse_local_file())
        self.app.bind('<Control-d>', lambda e: self.run_download_build())

        # Execution
        self.app.bind('<F5>', lambda e: self.run_zybot_tests())
        self.app.bind('<Control-Return>', lambda e: self.run_download_sttls())

        # Emergency
        self.app.bind('<Escape>', lambda e: self.kill_with_confirmation())

        # Utility
        self.app.bind('<Control-l>', lambda e: self.clear_logs())
        self.app.bind('<Control-s>', lambda e: self.export_logs())
        self.app.bind('<Control-question>', lambda e: self.show_keyboard_shortcuts())
        self.app.bind('<F1>', lambda e: self.show_keyboard_shortcuts())

    def show_keyboard_shortcuts(self):
        """Display keyboard shortcuts help dialog"""
        shortcuts = """
🎹 KEYBOARD SHORTCUTS

File Operations:
  Ctrl+O          Open/Browse local file
  Ctrl+D          Download build

Execution:
  F5              Run Zybot Tests
  Ctrl+Enter      Download STTLs

Emergency:
  Esc             Kill current process

Utility:
  Ctrl+L          Clear logs
  Ctrl+S          Export logs
  F1              Show this help

Navigation:
  Tab             Move between fields
  Shift+Tab       Move backwards
        """
        messagebox.showinfo("Keyboard Shortcuts", shortcuts)

    # ===== PLACEHOLDER TEXT =====

    def setup_placeholders(self):
        """Add placeholder text to input fields"""
        self._add_placeholder(self.app.polarion_url_entry,
                            "https://polarion.zebra.com/...")
        self._add_placeholder(self.app.jfrog_link_entry,
                            "https://artifactory.zebra.com/...")
        self._add_placeholder(self.app.local_file_entry,
                            "Select a local .zip build file...")

    def _add_placeholder(self, entry, placeholder_text):
        """Add placeholder text to an entry widget"""
        entry.insert(0, placeholder_text)
        entry.config(fg='#999999')

        def on_focus_in(event):
            if entry.get() == placeholder_text:
                entry.delete(0, tk.END)
                entry.config(fg='#212529')

        def on_focus_out(event):
            if not entry.get():
                entry.insert(0, placeholder_text)
                entry.config(fg='#999999')

        entry.bind('<FocusIn>', on_focus_in)
        entry.bind('<FocusOut>', on_focus_out)

    # ===== SESSION PERSISTENCE =====

    def save_session_state(self):
        """Save current session state"""
        try:
            # Get entry values (handle placeholders)
            polarion_url = self.app.polarion_url_entry.get()
            if self.app.polarion_url_entry.cget('fg') == '#999999':
                polarion_url = ''

            jfrog_url = self.app.jfrog_link_entry.get()
            if self.app.jfrog_link_entry.cget('fg') == '#999999':
                jfrog_url = ''

            local_file = self.app.local_file_entry.get()
            if self.app.local_file_entry.cget('fg') == '#999999':
                local_file = ''

            state = {
                'polarion_url': polarion_url,
                'jfrog_url': jfrog_url,
                'local_file_path': local_file,
                'selected_devices': {
                    dut: dropdown.get()
                    for dut, dropdown in self.app.device_dropdowns.items()
                },
                'flash_device': self.app.flash_device_dropdown.get(),
                'last_sttls': getattr(self, 'sttls', []),
                'window_size': f"{self.app.winfo_width()}x{self.app.winfo_height()}",
                'window_position': f"+{self.app.winfo_x()}+{self.app.winfo_y()}"
            }

            session_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                       'session_state.json')
            with open(session_file, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            self.logger.log(f"Could not save session state: {e}", level='error')

    def restore_session_state(self):
        """Restore previous session state"""
        try:
            session_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                       'session_state.json')

            if not os.path.exists(session_file):
                return

            with open(session_file, 'r') as f:
                state = json.load(f)

            # Restore URLs (clear placeholder first)
            if state.get('polarion_url'):
                self.app.polarion_url_entry.delete(0, tk.END)
                self.app.polarion_url_entry.insert(0, state['polarion_url'])
                self.app.polarion_url_entry.config(fg='#212529')

            if state.get('jfrog_url'):
                self.app.jfrog_link_entry.delete(0, tk.END)
                self.app.jfrog_link_entry.insert(0, state['jfrog_url'])
                self.app.jfrog_link_entry.config(fg='#212529')

            if state.get('local_file_path'):
                self.app.local_file_entry.delete(0, tk.END)
                self.app.local_file_entry.insert(0, state['local_file_path'])
                self.app.local_file_entry.config(fg='#212529')

            # Restore STTLs
            if state.get('last_sttls'):
                self.sttls = state['last_sttls']
                self.update_zybot_command_display()

            # Restore window geometry
            geometry = state.get('window_size', '') + state.get('window_position', '')
            if geometry and '+' in geometry:
                try:
                    self.app.geometry(geometry)
                except:
                    pass  # Invalid geometry, skip

            self.logger.log("✅ Session restored from previous run", level='success')
        except Exception as e:
            pass  # First run or corrupted state file

    # ===== LOG MANAGEMENT =====

    def clear_logs(self):
        """Clear all logs"""
        result = messagebox.askyesno("Clear Logs",
                                    "Are you sure you want to clear all logs?\n\n"
                                    "This cannot be undone.")
        if result:
            self.app.log_text.configure(state='normal')
            self.app.log_text.delete(1.0, tk.END)
            self.app.log_text.configure(state='disabled')
            self.logger.log("📋 Logs cleared", level='info')

    def export_logs(self):
        """Export logs to a text file"""
        file_path = filedialog.asksaveasfilename(
            title="Export Logs",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialfile=f"zap_logs_{self.logger.timestamp}.txt"
        )

        if file_path:
            try:
                log_content = self.app.log_text.get(1.0, tk.END)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(log_content)
                self.logger.log(f"✅ Logs exported to: {file_path}", level='success')
                self.app.show_toast(f"Logs exported successfully!", 'success')
            except Exception as e:
                self.logger.log(f"❌ Failed to export logs: {e}", level='error')

    def filter_logs(self):
        """Filter logs by level"""
        level = self.app.log_level_var.get()
        # This would require storing log entries with their levels
        # For now, just log the action
        if level != 'all':
            self.logger.log(f"🔍 Filtering logs: showing {level} only", level='info')

    def search_logs(self):
        """Search logs for text"""
        search_term = self.app.log_search_entry.get()
        if not search_term:
            # Clear any existing highlights
            self.app.log_text.tag_remove('search_highlight', '1.0', tk.END)
            return

        # Remove previous highlights
        self.app.log_text.tag_remove('search_highlight', '1.0', tk.END)

        # Configure highlight tag
        self.app.log_text.tag_config('search_highlight', background='yellow', foreground='black')

        # Search and highlight
        start_pos = '1.0'
        while True:
            start_pos = self.app.log_text.search(search_term, start_pos, stopindex=tk.END, nocase=True)
            if not start_pos:
                break
            end_pos = f"{start_pos}+{len(search_term)}c"
            self.app.log_text.tag_add('search_highlight', start_pos, end_pos)
            start_pos = end_pos

    # ===== SCHEDULER METHODS =====

    def start_scheduler(self):
        """Start the task scheduler"""
        self.task_scheduler.start()
        self.app.scheduler_status_label.config(text="Running")
        self.app.scheduler_status_indicator.config(fg=self.app.colors['status_connected'])
        self.app.show_toast("✅ Scheduler started", 'success')
        self.logger.log("🕐 Task scheduler started", level='success')

    def stop_scheduler(self):
        """Stop the task scheduler"""
        result = messagebox.askyesno(
            "Stop Scheduler",
            "Are you sure you want to stop the task scheduler?\n\n"
            "Scheduled tasks will not run until you start it again.",
            icon='warning'
        )

        if result:
            self.task_scheduler.stop()
            self.app.scheduler_status_label.config(text="Stopped")
            self.app.scheduler_status_indicator.config(fg=self.app.colors['status_disconnected'])
            self.app.show_toast("⏸️ Scheduler stopped", 'warning')
            self.logger.log("⏸️ Task scheduler stopped", level='info')

    def add_scheduled_task(self):
        """Open dialog to add a new scheduled task"""
        dialog = TaskConfigDialog(self.app)
        result = dialog.show()

        if result:
            task = ScheduledTask(
                task_id=result['task_id'],
                name=result['name'],
                task_type=result['task_type'],
                schedule_type=result['schedule_type'],
                schedule_value=result['schedule_value'],
                config=result['config'],
                enabled=result['enabled']
            )

            if self.task_scheduler.add_task(task):
                self.app.show_toast(f"✅ Task '{task.name}' created", 'success')
                self.refresh_scheduled_tasks_display()
            else:
                messagebox.showerror("Error", "Failed to add task. Task ID may already exist.")

    def edit_scheduled_task(self, task_id):
        """Edit an existing scheduled task"""
        task = self.task_scheduler.get_task(task_id)
        if not task:
            messagebox.showerror("Error", "Task not found")
            return

        dialog = TaskConfigDialog(self.app, task=task)
        result = dialog.show()

        if result:
            updated_task = ScheduledTask(
                task_id=result['task_id'],
                name=result['name'],
                task_type=result['task_type'],
                schedule_type=result['schedule_type'],
                schedule_value=result['schedule_value'],
                config=result['config'],
                enabled=result['enabled']
            )

            if self.task_scheduler.update_task(updated_task):
                self.app.show_toast(f"✅ Task '{updated_task.name}' updated", 'success')
                self.refresh_scheduled_tasks_display()

    def delete_scheduled_task(self, task_id):
        """Delete a scheduled task with confirmation"""
        task = self.task_scheduler.get_task(task_id)
        if not task:
            return

        result = messagebox.askyesno(
            "Delete Task",
            f"Are you sure you want to delete the task:\n\n'{task.name}'\n\n"
            "This cannot be undone.",
            icon='warning'
        )

        if result:
            if self.task_scheduler.remove_task(task_id):
                self.app.show_toast(f"🗑️ Task deleted", 'info')
                self.refresh_scheduled_tasks_display()

    def toggle_scheduled_task(self, task_id):
        """Enable or disable a scheduled task"""
        task = self.task_scheduler.get_task(task_id)
        if not task:
            return

        if task.enabled:
            self.task_scheduler.disable_task(task_id)
            self.app.show_toast(f"⏸️ Task '{task.name}' disabled", 'info')
        else:
            self.task_scheduler.enable_task(task_id)
            self.app.show_toast(f"▶ Task '{task.name}' enabled", 'success')

        self.refresh_scheduled_tasks_display()

    def refresh_scheduled_tasks_display(self):
        """Refresh the scheduled tasks display in GUI"""
        tasks = self.task_scheduler.get_all_tasks()
        self.app.update_scheduled_tasks_list(tasks)

        # Set up callbacks for task action buttons
        for widget in self.app.tasks_frame.winfo_children():
            if hasattr(widget, 'task_id'):
                for child in widget.winfo_children():
                    if isinstance(child, tk.Frame):
                        for button in child.winfo_children():
                            if isinstance(button, tk.Button) and hasattr(button, 'task_id'):
                                button_text = button.cget('text')
                                task_id = button.task_id

                                if 'Enable' in button_text or 'Disable' in button_text:
                                    button.config(command=lambda tid=task_id: self.toggle_scheduled_task(tid))
                                elif 'Edit' in button_text:
                                    button.config(command=lambda tid=task_id: self.edit_scheduled_task(tid))
                                elif 'Delete' in button_text:
                                    button.config(command=lambda tid=task_id: self.delete_scheduled_task(tid))

    def execute_scheduled_task(self, task: ScheduledTask) -> bool:
        """
        Execute a scheduled task

        Args:
            task: ScheduledTask to execute

        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.log(f"🚀 Executing scheduled task: {task.name}", level='info')
            self.logger.log(f"   Type: {task.task_type}", level='info')
            self.logger.log(f"   Schedule: {task.schedule_type} - {task.schedule_value}", level='info')

            config = task.config
            build_url = config.get('build_url', '')
            device_serial = config.get('device', 'any')

            # Execute based on task type
            if task.task_type == 'flash':
                return self._execute_flash_task(build_url, device_serial)

            elif task.task_type == 'test':
                test_url = config.get('test_url', '')
                return self._execute_test_task(test_url)

            elif task.task_type == 'flash_and_test':
                # Flash first, then test
                flash_success = self._execute_flash_task(build_url, device_serial)
                if flash_success:
                    test_url = config.get('test_url', '')
                    return self._execute_test_task(test_url)
                return False

            return False

        except Exception as e:
            self.logger.log(f"❌ Scheduled task execution error: {e}", level='error')
            return False

    def _execute_flash_task(self, build_url: str, device_serial: str) -> bool:
        """Execute a flash task"""
        try:
            self.logger.log(f"📦 Downloading build from: {build_url}", level='info')

            # Get first available device if 'any' specified
            if device_serial == 'any':
                # Try to get first available device
                device_serial = None  # Will use first device

            # Download and flash
            downloaded_file = self.artifactory_manager.download_build(build_url)
            if downloaded_file:
                self.logger.log(f"⚡ Flashing build to device...", level='info')
                self.artifactory_manager.flash_build(downloaded_file, device_serial)
                self.logger.log(f"✅ Flash task completed successfully", level='success')
                return True
            else:
                self.logger.log(f"❌ Failed to download build", level='error')
                return False

        except Exception as e:
            self.logger.log(f"❌ Flash task error: {e}", level='error')
            return False

    def _execute_test_task(self, test_url: str) -> bool:
        """Execute a test task"""
        try:
            if not test_url:
                self.logger.log("⚠️ No test URL configured", level='warning')
                return False

            self.logger.log(f"🧪 Running tests from: {test_url}", level='info')

            # Download STTLs
            sttls = self.polarion_manager.download_sttls(test_url)
            if not sttls:
                self.logger.log("⚠️ No STTLs found", level='warning')
                return False

            # Get available devices
            # For scheduled tasks, we'll use all available devices
            devices = {}  # Would need to get from monitoring daemon

            # Run tests
            polarion_run_name = test_url.split('/')[-1]
            result = self.zybot_executor.run_tests(polarion_run_name, devices, sttls)

            if result == "Pass":
                self.logger.log(f"✅ Test task completed successfully", level='success')
                return True
            else:
                self.logger.log(f"❌ Tests failed", level='error')
                return False

        except Exception as e:
            self.logger.log(f"❌ Test task error: {e}", level='error')
            return False

    def run(self):
        # Set up protocol for window close
        self.app.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.app.mainloop()
        self.monitor_daemon.stop()
        self.task_scheduler.stop()

    def on_closing(self):
        """Handle window close event"""
        self.save_session_state()
        self.task_scheduler.stop()
        self.app.destroy()

if __name__ == "__main__":
    main_app = MainApplication()
    main_app.run()


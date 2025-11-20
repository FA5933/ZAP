"""
Task configuration dialog for scheduled tasks
"""
import tkinter as tk
from tkinter import ttk, messagebox
import uuid


class TaskConfigDialog(tk.Toplevel):
    """Dialog for creating or editing scheduled tasks"""

    def __init__(self, parent, task=None, available_products=None):
        """
        Initialize task configuration dialog

        Args:
            parent: Parent window
            task: ScheduledTask to edit (None for new task)
            available_products: List of available product build URLs
        """
        super().__init__(parent)

        self.task = task
        self.result = None
        self.available_products = available_products or []

        # Configure window
        self.title("Configure Scheduled Task" if not task else f"Edit Task: {task.name}")
        self.geometry("600x800")
        self.resizable(False, False)

        # Make dialog modal
        self.transient(parent)
        self.grab_set()

        # Center on parent
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

        self.create_widgets()

        # Load existing task data if editing
        if task:
            self.load_task_data()

    def create_widgets(self):
        """Create dialog widgets"""
        # Main container with canvas for scrolling
        main_frame = tk.Frame(self, bg='#f5f5f5')
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Create canvas and scrollbar for scrollable content
        canvas = tk.Canvas(main_frame, bg='#f5f5f5', highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_frame, orient='vertical', command=canvas.yview)

        # Scrollable container
        container = tk.Frame(canvas, bg='#f5f5f5', padx=20, pady=20)

        # Configure canvas
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Create window in canvas
        canvas_window = canvas.create_window((0, 0), window=container, anchor='nw')

        # Configure scroll region when container changes size
        def configure_scroll_region(event=None):
            canvas.configure(scrollregion=canvas.bbox('all'))

        container.bind('<Configure>', configure_scroll_region)

        # Make canvas expand to window width
        def configure_canvas_width(event):
            canvas.itemconfig(canvas_window, width=event.width)

        canvas.bind('<Configure>', configure_canvas_width)

        # Bind mousewheel for scrolling
        def on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")

        canvas.bind_all("<MouseWheel>", on_mousewheel)

        # Task Name
        name_frame = tk.LabelFrame(container, text="Task Name", bg='white', padx=10, pady=10)
        name_frame.pack(fill=tk.X, pady=(0, 10))

        self.name_var = tk.StringVar()
        name_entry = tk.Entry(name_frame, textvariable=self.name_var, font=('Segoe UI', 10))
        name_entry.pack(fill=tk.X)
        tk.Label(name_frame, text="Give your task a descriptive name",
                font=('Segoe UI', 8), fg='#6c757d', bg='white').pack(anchor='w', pady=(2, 0))

        # Task Type
        type_frame = tk.LabelFrame(container, text="Task Type", bg='white', padx=10, pady=10)
        type_frame.pack(fill=tk.X, pady=(0, 10))

        self.task_type_var = tk.StringVar(value='flash_and_test')

        tk.Radiobutton(type_frame, text="Flash Build Only", variable=self.task_type_var,
                      value='flash', bg='white', font=('Segoe UI', 9)).pack(anchor='w')
        tk.Radiobutton(type_frame, text="Run Tests Only", variable=self.task_type_var,
                      value='test', bg='white', font=('Segoe UI', 9)).pack(anchor='w')
        tk.Radiobutton(type_frame, text="Flash Build and Run Tests", variable=self.task_type_var,
                      value='flash_and_test', bg='white', font=('Segoe UI', 9)).pack(anchor='w')

        # Schedule Configuration
        schedule_frame = tk.LabelFrame(container, text="Schedule", bg='white', padx=10, pady=10)
        schedule_frame.pack(fill=tk.X, pady=(0, 10))

        self.schedule_type_var = tk.StringVar(value='weekly')

        # Schedule type selection
        schedule_type_frame = tk.Frame(schedule_frame, bg='white')
        schedule_type_frame.pack(fill=tk.X, pady=(0, 10))

        tk.Radiobutton(schedule_type_frame, text="Daily", variable=self.schedule_type_var,
                      value='daily', command=self.update_schedule_inputs,
                      bg='white', font=('Segoe UI', 9)).pack(side=tk.LEFT, padx=(0, 10))
        tk.Radiobutton(schedule_type_frame, text="Weekly", variable=self.schedule_type_var,
                      value='weekly', command=self.update_schedule_inputs,
                      bg='white', font=('Segoe UI', 9)).pack(side=tk.LEFT, padx=(0, 10))
        tk.Radiobutton(schedule_type_frame, text="Interval", variable=self.schedule_type_var,
                      value='interval', command=self.update_schedule_inputs,
                      bg='white', font=('Segoe UI', 9)).pack(side=tk.LEFT)

        # Schedule configuration container (changes based on type)
        self.schedule_config_frame = tk.Frame(schedule_frame, bg='white')
        self.schedule_config_frame.pack(fill=tk.X)

        self.update_schedule_inputs()

        # Build Configuration
        build_frame = tk.LabelFrame(container, text="Build Configuration", bg='white', padx=10, pady=10)
        build_frame.pack(fill=tk.X, pady=(0, 10))

        tk.Label(build_frame, text="Build URL or Product Path:", font=('Segoe UI', 9),
                bg='white').pack(anchor='w', pady=(0, 5))

        self.build_url_var = tk.StringVar()
        build_entry = tk.Entry(build_frame, textvariable=self.build_url_var, font=('Segoe UI', 9))
        build_entry.pack(fill=tk.X)

        tk.Label(build_frame, text="Use 'latest' in URL to automatically get the newest build",
                font=('Segoe UI', 8), fg='#6c757d', bg='white').pack(anchor='w', pady=(2, 0))

        # Test Configuration (optional)
        test_frame = tk.LabelFrame(container, text="Test Configuration (Optional)", bg='white', padx=10, pady=10)
        test_frame.pack(fill=tk.X, pady=(0, 10))

        tk.Label(test_frame, text="Polarion Test Run URL:", font=('Segoe UI', 9),
                bg='white').pack(anchor='w', pady=(0, 5))

        self.test_url_var = tk.StringVar()
        test_entry = tk.Entry(test_frame, textvariable=self.test_url_var, font=('Segoe UI', 9))
        test_entry.pack(fill=tk.X, pady=(0, 5))

        tk.Label(test_frame, text="Test Suite Name:", font=('Segoe UI', 9),
                bg='white').pack(anchor='w', pady=(5, 5))

        self.test_suite_var = tk.StringVar()
        test_suite_entry = tk.Entry(test_frame, textvariable=self.test_suite_var, font=('Segoe UI', 9))
        test_suite_entry.pack(fill=tk.X)

        # Device Configuration
        device_frame = tk.LabelFrame(container, text="Device Configuration", bg='white', padx=10, pady=10)
        device_frame.pack(fill=tk.X, pady=(0, 10))

        tk.Label(device_frame, text="Target Device (serial or 'any'):", font=('Segoe UI', 9),
                bg='white').pack(anchor='w', pady=(0, 5))

        self.device_var = tk.StringVar(value='any')
        device_entry = tk.Entry(device_frame, textvariable=self.device_var, font=('Segoe UI', 9))
        device_entry.pack(fill=tk.X)

        # Buttons in a fixed footer (outside scrollable area)
        button_frame = tk.Frame(self, bg='#e9ecef', relief='flat', bd=1)
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=0, pady=0)

        # Inner frame for padding
        button_inner = tk.Frame(button_frame, bg='#e9ecef')
        button_inner.pack(fill=tk.X, padx=20, pady=15)

        cancel_btn = tk.Button(button_inner, text="✖ Cancel", command=self.cancel,
                              font=('Segoe UI', 10), bg='#6c757d', fg='white',
                              padx=25, pady=10, relief='flat', cursor='hand2',
                              activebackground='#5a6268')
        cancel_btn.pack(side=tk.RIGHT, padx=(5, 0))

        save_btn = tk.Button(button_inner, text="✓ Save Task", command=self.save_task,
                            font=('Segoe UI', 10, 'bold'), bg='#0066cc', fg='white',
                            padx=25, pady=10, relief='flat', cursor='hand2',
                            activebackground='#0052a3')
        save_btn.pack(side=tk.RIGHT)

    def update_schedule_inputs(self):
        """Update schedule input fields based on selected schedule type"""
        # Clear existing widgets
        for widget in self.schedule_config_frame.winfo_children():
            widget.destroy()

        schedule_type = self.schedule_type_var.get()

        if schedule_type == 'daily':
            # Time input for daily schedule
            tk.Label(self.schedule_config_frame, text="Time (HH:MM):", font=('Segoe UI', 9),
                    bg='white').pack(anchor='w', pady=(5, 5))

            time_frame = tk.Frame(self.schedule_config_frame, bg='white')
            time_frame.pack(anchor='w')

            self.hour_var = tk.StringVar(value='14')
            self.minute_var = tk.StringVar(value='00')

            tk.Spinbox(time_frame, from_=0, to=23, textvariable=self.hour_var,
                      width=5, font=('Segoe UI', 10)).pack(side=tk.LEFT)
            tk.Label(time_frame, text=":", font=('Segoe UI', 12), bg='white').pack(side=tk.LEFT, padx=2)
            tk.Spinbox(time_frame, from_=0, to=59, textvariable=self.minute_var,
                      width=5, font=('Segoe UI', 10)).pack(side=tk.LEFT)

        elif schedule_type == 'weekly':
            # Day and time input for weekly schedule
            tk.Label(self.schedule_config_frame, text="Day of Week:", font=('Segoe UI', 9),
                    bg='white').pack(anchor='w', pady=(5, 5))

            self.day_var = tk.StringVar(value='Wednesday')
            day_combo = ttk.Combobox(self.schedule_config_frame, textvariable=self.day_var,
                                    values=['Monday', 'Tuesday', 'Wednesday', 'Thursday',
                                           'Friday', 'Saturday', 'Sunday'],
                                    state='readonly', width=15)
            day_combo.pack(anchor='w', pady=(0, 10))

            tk.Label(self.schedule_config_frame, text="Time (HH:MM):", font=('Segoe UI', 9),
                    bg='white').pack(anchor='w', pady=(5, 5))

            time_frame = tk.Frame(self.schedule_config_frame, bg='white')
            time_frame.pack(anchor='w')

            self.hour_var = tk.StringVar(value='14')
            self.minute_var = tk.StringVar(value='00')

            tk.Spinbox(time_frame, from_=0, to=23, textvariable=self.hour_var,
                      width=5, font=('Segoe UI', 10)).pack(side=tk.LEFT)
            tk.Label(time_frame, text=":", font=('Segoe UI', 12), bg='white').pack(side=tk.LEFT, padx=2)
            tk.Spinbox(time_frame, from_=0, to=59, textvariable=self.minute_var,
                      width=5, font=('Segoe UI', 10)).pack(side=tk.LEFT)

        elif schedule_type == 'interval':
            # Interval input
            tk.Label(self.schedule_config_frame, text="Run every:", font=('Segoe UI', 9),
                    bg='white').pack(anchor='w', pady=(5, 5))

            interval_frame = tk.Frame(self.schedule_config_frame, bg='white')
            interval_frame.pack(anchor='w')

            self.interval_value_var = tk.StringVar(value='6')
            self.interval_unit_var = tk.StringVar(value='h')

            tk.Spinbox(interval_frame, from_=1, to=999, textvariable=self.interval_value_var,
                      width=5, font=('Segoe UI', 10)).pack(side=tk.LEFT, padx=(0, 5))

            ttk.Combobox(interval_frame, textvariable=self.interval_unit_var,
                        values=[('m', 'Minutes'), ('h', 'Hours'), ('d', 'Days')],
                        state='readonly', width=10).pack(side=tk.LEFT)

            tk.Label(self.schedule_config_frame, text="(m=minutes, h=hours, d=days)",
                    font=('Segoe UI', 8), fg='#6c757d', bg='white').pack(anchor='w', pady=(2, 0))

    def load_task_data(self):
        """Load existing task data into form"""
        if not self.task:
            return

        self.name_var.set(self.task.name)
        self.task_type_var.set(self.task.task_type)
        self.schedule_type_var.set(self.task.schedule_type)

        # Load schedule values
        if self.task.schedule_type == 'daily':
            parts = self.task.schedule_value.split(':')
            if len(parts) == 2:
                self.hour_var.set(parts[0])
                self.minute_var.set(parts[1])
        elif self.task.schedule_type == 'weekly':
            parts = self.task.schedule_value.split()
            if len(parts) >= 1:
                self.day_var.set(parts[0])
            if len(parts) >= 2:
                time_parts = parts[1].split(':')
                if len(time_parts) == 2:
                    self.hour_var.set(time_parts[0])
                    self.minute_var.set(time_parts[1])
        elif self.task.schedule_type == 'interval':
            value = self.task.schedule_value[:-1]
            unit = self.task.schedule_value[-1]
            self.interval_value_var.set(value)
            self.interval_unit_var.set(unit)

        # Load configuration
        config = self.task.config
        self.build_url_var.set(config.get('build_url', ''))
        self.test_url_var.set(config.get('test_url', ''))
        self.test_suite_var.set(config.get('test_suite', ''))
        self.device_var.set(config.get('device', 'any'))

        self.update_schedule_inputs()

    def save_task(self):
        """Validate and save task configuration"""
        # Validate required fields
        name = self.name_var.get().strip()
        if not name:
            messagebox.showerror("Validation Error", "Task name is required")
            return

        build_url = self.build_url_var.get().strip()
        if not build_url:
            messagebox.showerror("Validation Error", "Build URL is required")
            return

        # Build schedule value
        schedule_type = self.schedule_type_var.get()
        schedule_value = ''

        try:
            if schedule_type == 'daily':
                hour = int(self.hour_var.get())
                minute = int(self.minute_var.get())
                schedule_value = f"{hour:02d}:{minute:02d}"
            elif schedule_type == 'weekly':
                day = self.day_var.get()
                hour = int(self.hour_var.get())
                minute = int(self.minute_var.get())
                schedule_value = f"{day} {hour:02d}:{minute:02d}"
            elif schedule_type == 'interval':
                value = int(self.interval_value_var.get())
                unit = self.interval_unit_var.get()
                schedule_value = f"{value}{unit}"
        except ValueError:
            messagebox.showerror("Validation Error", "Invalid schedule configuration")
            return

        # Build configuration dict
        config = {
            'build_url': build_url,
            'test_url': self.test_url_var.get().strip(),
            'test_suite': self.test_suite_var.get().strip(),
            'device': self.device_var.get().strip()
        }

        # Create result dict
        self.result = {
            'task_id': self.task.task_id if self.task else str(uuid.uuid4()),
            'name': name,
            'task_type': self.task_type_var.get(),
            'schedule_type': schedule_type,
            'schedule_value': schedule_value,
            'config': config,
            'enabled': self.task.enabled if self.task else True
        }

        self.destroy()

    def cancel(self):
        """Cancel dialog"""
        self.result = None
        self.destroy()

    def show(self):
        """Show dialog and wait for result"""
        self.wait_window()
        return self.result


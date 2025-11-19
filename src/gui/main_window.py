import tkinter as tk
from tkinter import ttk, scrolledtext, font

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ZAP - Zebra Automation Platform")
        self.geometry("1100x800")
        self.minsize(1000, 700)

        # Configure modern color scheme
        self.colors = {
            'bg': '#f5f5f5',
            'card_bg': '#ffffff',
            'primary': '#0066cc',
            'primary_hover': '#0052a3',
            'success': '#28a745',
            'danger': '#dc3545',
            'warning': '#ffc107',
            'text': '#212529',
            'text_light': '#6c757d',
            'border': '#dee2e6',
            'status_connected': '#28a745',
            'status_disconnected': '#dc3545',
            'status_online': '#17a2b8'
        }

        self.configure(bg=self.colors['bg'])
        self._setup_styles()
        self.create_widgets()

    def _setup_styles(self):
        """Configure modern ttk styles"""
        style = ttk.Style()

        # Try to use a modern theme
        try:
            style.theme_use('clam')
        except:
            pass

        # Configure frame styles
        style.configure('Card.TFrame', background=self.colors['card_bg'], relief='flat', borderwidth=1)
        style.configure('Main.TFrame', background=self.colors['bg'])

        # Configure label frame styles
        style.configure('Card.TLabelframe', background=self.colors['card_bg'], relief='solid', borderwidth=1, bordercolor=self.colors['border'])
        style.configure('Card.TLabelframe.Label', background=self.colors['card_bg'], foreground=self.colors['text'], font=('Segoe UI', 10, 'bold'))

        # Configure label styles
        style.configure('TLabel', background=self.colors['card_bg'], foreground=self.colors['text'], font=('Segoe UI', 9))
        style.configure('Header.TLabel', font=('Segoe UI', 11, 'bold'), foreground=self.colors['text'])
        style.configure('Status.TLabel', font=('Segoe UI', 9, 'bold'))

        # Configure button styles
        style.configure('Primary.TButton', font=('Segoe UI', 9, 'bold'), padding=8)
        style.map('Primary.TButton',
                  foreground=[('active', 'white'), ('!active', 'white')],
                  background=[('active', self.colors['primary_hover']), ('!active', self.colors['primary'])])

        style.configure('Danger.TButton', font=('Segoe UI', 9, 'bold'), padding=8)
        style.map('Danger.TButton',
                  foreground=[('active', 'white')],
                  background=[('active', '#c82333'), ('!active', self.colors['danger'])])

        style.configure('Success.TButton', font=('Segoe UI', 9, 'bold'), padding=8)

        # Configure entry styles
        style.configure('TEntry', fieldbackground='white', padding=6)

        # Configure combobox styles
        style.configure('TCombobox', padding=6)

    def create_widgets(self):
        # Main container
        main_container = tk.Frame(self, bg=self.colors['bg'])
        main_container.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

        # Header Section
        header_frame = tk.Frame(main_container, bg=self.colors['card_bg'], relief='flat', bd=1,
                               highlightbackground=self.colors['border'], highlightthickness=1)
        header_frame.pack(fill=tk.X, pady=(0, 15))

        title_label = tk.Label(header_frame, text="🦓 ZAP - Zebra Automation Platform",
                               font=('Segoe UI', 16, 'bold'), bg=self.colors['card_bg'],
                               fg=self.colors['primary'], pady=15, padx=20)
        title_label.pack(side=tk.LEFT)

        # Content frame with two columns
        content_frame = tk.Frame(main_container, bg=self.colors['bg'])
        content_frame.pack(fill=tk.BOTH, expand=True)

        # Right column (monitoring section - fixed width)
        right_column = tk.Frame(content_frame, bg=self.colors['bg'], width=320)
        right_column.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(8, 0))
        right_column.pack_propagate(False)  # Maintain the width

        # Device Monitoring Section (Right Column)
        self._create_monitoring_section(right_column)

        # Left column with scrollable canvas
        left_column_container = tk.Frame(content_frame, bg=self.colors['bg'])
        left_column_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8))

        # Create canvas and scrollbar for left column
        left_canvas = tk.Canvas(left_column_container, bg=self.colors['bg'],
                               highlightthickness=0)
        left_scrollbar = ttk.Scrollbar(left_column_container, orient='vertical',
                                      command=left_canvas.yview)

        # Scrollable frame inside canvas
        left_column = tk.Frame(left_canvas, bg=self.colors['bg'])

        # Configure canvas scrolling
        def _configure_scroll_region(event=None):
            left_canvas.configure(scrollregion=left_canvas.bbox('all'))

        left_column.bind('<Configure>', _configure_scroll_region)

        # Create canvas window for left_column
        canvas_window = left_canvas.create_window((0, 0), window=left_column, anchor='nw')

        # Make the frame expand to canvas width
        def _configure_canvas_width(event):
            canvas_width = event.width
            left_canvas.itemconfig(canvas_window, width=canvas_width)

        left_canvas.bind('<Configure>', _configure_canvas_width)
        left_canvas.configure(yscrollcommand=left_scrollbar.set)

        # Pack canvas and scrollbar
        left_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        left_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Bind mousewheel to canvas for scrolling
        def _on_mousewheel(event):
            left_canvas.yview_scroll(int(-1*(event.delta/120)), "units")

        left_canvas.bind_all("<MouseWheel>", _on_mousewheel)

        # Polarion Section (Left Column)
        self._create_polarion_section(left_column)

        # Zybot Execution Section (Left Column)
        self._create_zybot_section(left_column)

        # Generated Command Section (Left Column)
        self._create_command_section(left_column)

        # JFrog Artifactory Section (Left Column)
        self._create_jfrog_section(left_column)

        # Log Display (Left Column)
        self._create_log_section(left_column)

    def _create_monitoring_section(self, parent):
        """Create the device monitoring panel"""
        monitor_frame = tk.LabelFrame(parent, text="📊 System Status", bg=self.colors['card_bg'],
                                      fg=self.colors['text'], font=('Segoe UI', 10, 'bold'),
                                      relief='solid', bd=1, padx=15, pady=10)
        monitor_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

        # Device Status Header with colored indicator
        device_header = tk.Frame(monitor_frame, bg=self.colors['card_bg'])
        device_header.pack(fill=tk.X, pady=(0, 8))

        tk.Label(device_header, text="Connected Devices:", font=('Segoe UI', 9),
                bg=self.colors['card_bg'], fg=self.colors['text_light']).pack(anchor='w')

        status_row = tk.Frame(device_header, bg=self.colors['card_bg'])
        status_row.pack(fill=tk.X, pady=(4, 0))

        self.device_status_indicator = tk.Label(status_row, text="●", font=('Segoe UI', 14),
                                               bg=self.colors['card_bg'], fg=self.colors['status_disconnected'])
        self.device_status_indicator.pack(side=tk.LEFT, padx=(0, 5))

        self.device_status_label = tk.Label(status_row, text="No devices",
                                           font=('Segoe UI', 9, 'bold'),
                                           bg=self.colors['card_bg'], fg=self.colors['text'])
        self.device_status_label.pack(side=tk.LEFT)

        # Scrollable Device List Frame
        devices_container = tk.Frame(monitor_frame, bg=self.colors['card_bg'])
        devices_container.pack(fill=tk.BOTH, expand=True, pady=(8, 10))

        # Create a canvas with scrollbar for devices
        canvas = tk.Canvas(devices_container, bg='#f8f9fa', relief='solid', bd=1,
                          highlightthickness=0, height=200)
        scrollbar = ttk.Scrollbar(devices_container, orient='vertical', command=canvas.yview)
        self.devices_frame = tk.Frame(canvas, bg='#f8f9fa')

        self.devices_frame.bind('<Configure>',
                               lambda e: canvas.configure(scrollregion=canvas.bbox('all')))

        canvas.create_window((0, 0), window=self.devices_frame, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Store canvas for later reference
        self.devices_canvas = canvas

        # Initial empty state message
        self.no_devices_label = tk.Label(self.devices_frame,
                                         text="No devices connected\n\nConnect a device via ADB to see it here",
                                         font=('Segoe UI', 9), bg='#f8f9fa',
                                         fg=self.colors['text_light'], pady=40)
        self.no_devices_label.pack()

        # Separator
        ttk.Separator(monitor_frame, orient='horizontal').pack(fill=tk.X, pady=10)

        # PC Status with colored indicator
        pc_container = tk.Frame(monitor_frame, bg=self.colors['card_bg'])
        pc_container.pack(fill=tk.X, pady=8)

        tk.Label(pc_container, text="PC Status:", font=('Segoe UI', 9),
                bg=self.colors['card_bg'], fg=self.colors['text_light']).pack(anchor='w')

        pc_status_row = tk.Frame(pc_container, bg=self.colors['card_bg'])
        pc_status_row.pack(fill=tk.X, pady=(4, 0))

        self.pc_status_indicator = tk.Label(pc_status_row, text="●", font=('Segoe UI', 14),
                                           bg=self.colors['card_bg'], fg=self.colors['status_online'])
        self.pc_status_indicator.pack(side=tk.LEFT, padx=(0, 5))

        self.pc_status_label = tk.Label(pc_status_row, text="Online",
                                       font=('Segoe UI', 9, 'bold'),
                                       bg=self.colors['card_bg'], fg=self.colors['text'])
        self.pc_status_label.pack(side=tk.LEFT)

        # PC IP
        self.ip_label = self._create_info_label(pc_container, "PC IP:", "N/A")

        # Kill Process Button
        kill_btn_frame = tk.Frame(monitor_frame, bg=self.colors['card_bg'])
        kill_btn_frame.pack(fill=tk.X, pady=(15, 5))

        self.kill_button = tk.Button(kill_btn_frame, text="⚠ Kill Process",
                                     font=('Segoe UI', 9, 'bold'),
                                     bg=self.colors['danger'], fg='white',
                                     relief='flat', cursor='hand2', pady=8,
                                     activebackground='#c82333', activeforeground='white')
        self.kill_button.pack(fill=tk.X)

    def update_device_list(self, devices_info):
        """Update the device list display with detailed information

        Args:
            devices_info: List of dicts with keys: 'serial', 'model', 'display_name'
        """
        # Clear existing device widgets
        for widget in self.devices_frame.winfo_children():
            widget.destroy()

        if not devices_info:
            # Show empty state
            self.no_devices_label = tk.Label(self.devices_frame,
                                             text="No devices connected\n\nConnect a device via ADB to see it here",
                                             font=('Segoe UI', 9), bg='#f8f9fa',
                                             fg=self.colors['text_light'], pady=40)
            self.no_devices_label.pack()
        else:
            # Create a card for each device
            for idx, device in enumerate(devices_info):
                device_card = tk.Frame(self.devices_frame, bg='white', relief='solid',
                                      bd=1, padx=12, pady=10)
                device_card.pack(fill=tk.X, padx=8, pady=6)

                # Device number/icon
                header_frame = tk.Frame(device_card, bg='white')
                header_frame.pack(fill=tk.X)

                tk.Label(header_frame, text=f"📱 Device {idx + 1}",
                        font=('Segoe UI', 9, 'bold'), bg='white',
                        fg=self.colors['primary']).pack(side=tk.LEFT)

                # Model
                model_frame = tk.Frame(device_card, bg='white')
                model_frame.pack(fill=tk.X, pady=(6, 2))
                tk.Label(model_frame, text="Model:", font=('Segoe UI', 8),
                        bg='white', fg=self.colors['text_light']).pack(side=tk.LEFT)
                tk.Label(model_frame, text=device.get('model', 'N/A'),
                        font=('Segoe UI', 8, 'bold'), bg='white',
                        fg=self.colors['text']).pack(side=tk.LEFT, padx=(5, 0))

                # Serial
                serial_frame = tk.Frame(device_card, bg='white')
                serial_frame.pack(fill=tk.X, pady=2)
                tk.Label(serial_frame, text="Serial:", font=('Segoe UI', 8),
                        bg='white', fg=self.colors['text_light']).pack(side=tk.LEFT)
                tk.Label(serial_frame, text=device.get('serial', 'N/A'),
                        font=('Consolas', 8), bg='white',
                        fg=self.colors['text']).pack(side=tk.LEFT, padx=(5, 0))

    def _create_info_label(self, parent, label_text, value_text):
        """Helper to create consistent info labels"""
        container = tk.Frame(parent, bg=self.colors['card_bg'])
        container.pack(fill=tk.X, pady=4)

        tk.Label(container, text=label_text, font=('Segoe UI', 9),
                bg=self.colors['card_bg'], fg=self.colors['text_light']).pack(anchor='w')

        value_label = tk.Label(container, text=value_text, font=('Segoe UI', 9, 'bold'),
                              bg=self.colors['card_bg'], fg=self.colors['text'])
        value_label.pack(anchor='w', padx=(10, 0))

        return value_label

    def _create_polarion_section(self, parent):
        """Create the Polarion test run section"""
        polarion_frame = tk.LabelFrame(parent, text="🎯 Polarion Test Run", bg=self.colors['card_bg'],
                                      fg=self.colors['text'], font=('Segoe UI', 10, 'bold'),
                                      relief='solid', bd=1, padx=15, pady=10)
        polarion_frame.pack(fill=tk.X, pady=(0, 15))

        input_frame = tk.Frame(polarion_frame, bg=self.colors['card_bg'])
        input_frame.pack(fill=tk.X, pady=5)

        tk.Label(input_frame, text="Test Run URL:", font=('Segoe UI', 9),
                bg=self.colors['card_bg'], fg=self.colors['text']).pack(side=tk.LEFT, padx=(0, 10))

        self.polarion_url_entry = tk.Entry(input_frame, font=('Segoe UI', 9),
                                           relief='solid', bd=1, bg='white')
        self.polarion_url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=4, padx=(0, 10))

        self.download_sttls_button = tk.Button(input_frame, text="📥 Download STTLs",
                                              font=('Segoe UI', 9, 'bold'),
                                              bg=self.colors['primary'], fg='white',
                                              relief='flat', cursor='hand2', padx=15, pady=6,
                                              activebackground=self.colors['primary_hover'])
        self.download_sttls_button.pack(side=tk.LEFT)

    def _create_zybot_section(self, parent):
        """Create the Zybot execution section"""
        zybot_frame = tk.LabelFrame(parent, text="🤖 Zybot Test Execution", bg=self.colors['card_bg'],
                                   fg=self.colors['text'], font=('Segoe UI', 10, 'bold'),
                                   relief='solid', bd=1, padx=15, pady=10)
        zybot_frame.pack(fill=tk.X, pady=(0, 15))

        # Device selection in a 2x2 grid
        device_grid = tk.Frame(zybot_frame, bg=self.colors['card_bg'])
        device_grid.pack(fill=tk.X, pady=5)

        self.device_dropdowns = {}
        for i in range(1, 5):
            row = (i - 1) // 2
            col = (i - 1) % 2

            device_container = tk.Frame(device_grid, bg=self.colors['card_bg'])
            device_container.grid(row=row, column=col, padx=8, pady=6, sticky='ew')

            tk.Label(device_container, text=f"DUT{i}:", font=('Segoe UI', 9),
                    bg=self.colors['card_bg'], fg=self.colors['text'], width=6, anchor='w').pack(side=tk.LEFT)

            device_dropdown = ttk.Combobox(device_container, width=22, font=('Segoe UI', 9))
            device_dropdown.pack(side=tk.LEFT, fill=tk.X, expand=True)
            self.device_dropdowns[f"DUT{i}"] = device_dropdown

        device_grid.columnconfigure(0, weight=1)
        device_grid.columnconfigure(1, weight=1)

        # Run button
        btn_frame = tk.Frame(zybot_frame, bg=self.colors['card_bg'])
        btn_frame.pack(fill=tk.X, pady=(10, 5))

        self.run_zybot_button = tk.Button(btn_frame, text="▶ Run Zybot Tests",
                                         font=('Segoe UI', 10, 'bold'),
                                         bg=self.colors['success'], fg='white',
                                         relief='flat', cursor='hand2', pady=10,
                                         activebackground='#218838', activeforeground='white')
        self.run_zybot_button.pack(fill=tk.X)

    def _create_command_section(self, parent):
        """Create the generated command display section"""
        command_frame = tk.LabelFrame(parent, text="💻 Generated Zybot Command", bg=self.colors['card_bg'],
                                     fg=self.colors['text'], font=('Segoe UI', 10, 'bold'),
                                     relief='solid', bd=1, padx=15, pady=10)
        command_frame.pack(fill=tk.X, pady=(0, 15))

        self.zybot_command_text = scrolledtext.ScrolledText(command_frame, wrap=tk.WORD, height=4,
                                                            font=('Consolas', 9), bg='#f8f9fa',
                                                            relief='solid', bd=1, padx=8, pady=8)
        self.zybot_command_text.pack(fill=tk.X, expand=True)
        self.zybot_command_text.configure(state='disabled')

    def _create_jfrog_section(self, parent):
        """Create the JFrog Artifactory section"""
        jfrog_frame = tk.LabelFrame(parent, text="📦 JFrog Artifactory", bg=self.colors['card_bg'],
                                   fg=self.colors['text'], font=('Segoe UI', 10, 'bold'),
                                   relief='solid', bd=1, padx=15, pady=10)
        jfrog_frame.pack(fill=tk.X, pady=(0, 15))

        # Device Selection
        device_selection_frame = tk.Frame(jfrog_frame, bg=self.colors['card_bg'])
        device_selection_frame.pack(fill=tk.X, pady=(5, 10))

        tk.Label(device_selection_frame, text="Target Device:", font=('Segoe UI', 9),
                bg=self.colors['card_bg'], fg=self.colors['text']).pack(side=tk.LEFT, padx=(0, 10))

        self.flash_device_dropdown = ttk.Combobox(device_selection_frame, width=30,
                                                  font=('Segoe UI', 9), state='readonly')
        self.flash_device_dropdown.pack(side=tk.LEFT, ipady=2)
        self.flash_device_dropdown['values'] = ['']  # Will be updated by monitoring daemon

        # Build URL input section
        url_input_frame = tk.Frame(jfrog_frame, bg=self.colors['card_bg'])
        url_input_frame.pack(fill=tk.X, pady=(5, 10))

        tk.Label(url_input_frame, text="Build URL:", font=('Segoe UI', 9),
                bg=self.colors['card_bg'], fg=self.colors['text']).pack(anchor='w', pady=(0, 5))

        self.jfrog_link_entry = tk.Entry(url_input_frame, font=('Segoe UI', 9),
                                         relief='solid', bd=1, bg='white')
        self.jfrog_link_entry.pack(fill=tk.X, ipady=4)

        # Build URL action buttons
        url_buttons_frame = tk.Frame(jfrog_frame, bg=self.colors['card_bg'])
        url_buttons_frame.pack(fill=tk.X, pady=(5, 10))

        self.download_build_button = tk.Button(url_buttons_frame, text="📥 Download Only",
                                              font=('Segoe UI', 9, 'bold'),
                                              bg=self.colors['primary'], fg='white',
                                              relief='flat', cursor='hand2', padx=12, pady=6,
                                              activebackground=self.colors['primary_hover'])
        self.download_build_button.pack(side=tk.LEFT, padx=(0, 8))

        self.download_flash_button = tk.Button(url_buttons_frame, text="⚡ Download & Flash",
                                              font=('Segoe UI', 9, 'bold'),
                                              bg=self.colors['warning'], fg='#212529',
                                              relief='flat', cursor='hand2', padx=12, pady=6,
                                              activebackground='#e0a800')
        self.download_flash_button.pack(side=tk.LEFT)

        # Separator
        ttk.Separator(jfrog_frame, orient='horizontal').pack(fill=tk.X, pady=10)

        # Local file flash section
        local_file_frame = tk.Frame(jfrog_frame, bg=self.colors['card_bg'])
        local_file_frame.pack(fill=tk.X, pady=5)

        tk.Label(local_file_frame, text="Local Build File:", font=('Segoe UI', 9),
                bg=self.colors['card_bg'], fg=self.colors['text']).pack(anchor='w', pady=(0, 5))

        file_input_row = tk.Frame(local_file_frame, bg=self.colors['card_bg'])
        file_input_row.pack(fill=tk.X)

        self.local_file_entry = tk.Entry(file_input_row, font=('Segoe UI', 9),
                                         relief='solid', bd=1, bg='white')
        self.local_file_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=4, padx=(0, 8))

        self.browse_button = tk.Button(file_input_row, text="📁 Browse",
                                       font=('Segoe UI', 9),
                                       bg='#6c757d', fg='white',
                                       relief='flat', cursor='hand2', padx=12, pady=6,
                                       activebackground='#5a6268')
        self.browse_button.pack(side=tk.LEFT, padx=(0, 8))

        self.flash_local_button = tk.Button(file_input_row, text="⚡ Flash",
                                           font=('Segoe UI', 9, 'bold'),
                                           bg=self.colors['success'], fg='white',
                                           relief='flat', cursor='hand2', padx=12, pady=6,
                                           activebackground='#218838')
        self.flash_local_button.pack(side=tk.LEFT)

    def _create_log_section(self, parent):
        """Create the log display section"""
        log_frame = tk.LabelFrame(parent, text="📋 System Logs", bg=self.colors['card_bg'],
                                 fg=self.colors['text'], font=('Segoe UI', 10, 'bold'),
                                 relief='solid', bd=1, padx=15, pady=10)
        log_frame.pack(fill=tk.X, pady=(0, 15))

        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, height=12,
                                                  font=('Consolas', 9), bg='#ffffff', fg='#212529',
                                                  relief='solid', bd=1, padx=8, pady=8,
                                                  insertbackground='#212529')
        self.log_text.pack(fill=tk.BOTH, expand=True)

    def update_device_dropdowns(self, devices):
        """Update the device dropdown options"""
        device_list = [""] + devices
        for dropdown in self.device_dropdowns.values():
            dropdown['values'] = device_list

if __name__ == "__main__":
    app = App()
    app.mainloop()

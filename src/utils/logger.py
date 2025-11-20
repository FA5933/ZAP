import logging
import datetime
import tkinter as tk

class Logger:
    def __init__(self, log_text_widget, auto_scroll_var=None, web_server=None):
        self.log_text_widget = log_text_widget
        self.auto_scroll_var = auto_scroll_var
        self.web_server = web_server
        self.timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        self.log_file = f"zap_log_{self.timestamp}.txt"

        # Configure tags for colors
        self.log_text_widget.tag_config('info', foreground='black')
        self.log_text_widget.tag_config('success', foreground='green')
        self.log_text_widget.tag_config('error', foreground='red')
        self.log_text_widget.tag_config('warning', foreground='#ff8800')

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.log_file),
                logging.StreamHandler()
            ]
        )

    def set_web_server(self, web_server):
        """Set the web server instance for pushing logs to dashboard"""
        self.web_server = web_server

    def log(self, message, level='info'):
        """Logs a message to the GUI and file. Level can be 'info', 'success', 'error', or 'warning'."""
        if level == 'error':
            logging.error(message)
        elif level == 'warning':
            logging.warning(message)
        else:
            logging.info(message)
        
        self.log_text_widget.configure(state='normal')
        timestamp = datetime.datetime.now().strftime('%H:%M:%S')
        self.log_text_widget.insert(tk.END, f"[{timestamp}] {message}\n", (level,))
        self.log_text_widget.configure(state='disabled')

        # Auto-scroll if enabled
        if self.auto_scroll_var is None or self.auto_scroll_var.get():
            self.log_text_widget.see(tk.END)

        # Push log to web server
        if self.web_server:
            try:
                self.web_server.add_log(message, level=level, source='ZAP')
            except:
                pass  # Don't let web server errors break logging


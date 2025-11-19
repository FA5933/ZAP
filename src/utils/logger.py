import logging
import datetime
import tkinter as tk

class Logger:
    def __init__(self, log_text_widget):
        self.log_text_widget = log_text_widget
        self.log_file = f"zap_log_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        # Configure tags for colors
        self.log_text_widget.tag_config('info', foreground='black')
        self.log_text_widget.tag_config('success', foreground='green')
        self.log_text_widget.tag_config('error', foreground='red')

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.log_file),
                logging.StreamHandler()
            ]
        )

    def log(self, message, level='info'):
        """Logs a message to the GUI and file. Level can be 'info', 'success', or 'error'."""
        if level == 'error':
            logging.error(message)
        else:
            logging.info(message)
        
        self.log_text_widget.configure(state='normal')
        self.log_text_widget.insert(tk.END, f"{message}\n", (level,))
        self.log_text_widget.configure(state='disabled')
        self.log_text_widget.see(tk.END)


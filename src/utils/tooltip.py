"""
Tooltip utility for displaying helpful hints on hover
"""
import tkinter as tk


class ToolTip:
    """Create a tooltip for a given widget"""

    def __init__(self, widget, text, delay=500):
        """
        Initialize tooltip

        Args:
            widget: Widget to attach tooltip to
            text: Tooltip text to display
            delay: Delay in milliseconds before showing tooltip
        """
        self.widget = widget
        self.text = text
        self.delay = delay
        self.tooltip = None
        self.id = None
        self.scheduled_id = None

        self.widget.bind('<Enter>', self.schedule_show, add='+')
        self.widget.bind('<Leave>', self.hide, add='+')
        self.widget.bind('<Button>', self.hide, add='+')
        self.widget.bind('<Motion>', self.on_motion, add='+')

    def on_motion(self, event=None):
        """Handle mouse motion - update tooltip position"""
        # If tooltip is showing, update its position
        if self.tooltip:
            try:
                x = self.widget.winfo_rootx() + 25
                y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
                self.tooltip.wm_geometry(f"+{x}+{y}")
            except:
                pass  # Widget might be destroyed

    def schedule_show(self, event=None):
        """Schedule tooltip to show after delay"""
        self.hide()  # Hide any existing tooltip first
        self.scheduled_id = self.widget.after(self.delay, self.show)

    def show(self, event=None):
        """Display the tooltip"""
        if self.tooltip:
            return

        try:
            # Make sure widget is mapped and visible
            if not self.widget.winfo_viewable():
                return

            # Get widget position
            x = self.widget.winfo_rootx() + 25
            y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5

            # Create tooltip window
            self.tooltip = tk.Toplevel(self.widget)
            self.tooltip.wm_overrideredirect(True)
            self.tooltip.wm_attributes('-topmost', True)  # Always on top

            # Try to make it transparent on Windows (optional)
            try:
                self.tooltip.attributes('-alpha', 0.95)
            except:
                pass

            self.tooltip.wm_geometry(f"+{x}+{y}")

            # Create tooltip content
            frame = tk.Frame(
                self.tooltip,
                background="#ffffe0",
                relief='solid',
                borderwidth=1
            )
            frame.pack()

            label = tk.Label(
                frame,
                text=self.text,
                background="#ffffe0",
                foreground="#000000",
                font=('Segoe UI', 9),
                padx=10,
                pady=5,
                justify='left'
            )
            label.pack()

            # Store the ID
            self.id = id(self.tooltip)

        except Exception as e:
            print(f"Error creating tooltip: {e}")
            self.tooltip = None

    def hide(self, event=None):
        """Hide the tooltip"""
        # Cancel scheduled show
        if self.scheduled_id:
            try:
                self.widget.after_cancel(self.scheduled_id)
            except:
                pass
            self.scheduled_id = None

        # Destroy tooltip window
        if self.tooltip:
            try:
                self.tooltip.destroy()
            except:
                pass
            self.tooltip = None
            self.id = None


def add_tooltip(widget, text, delay=500):
    """
    Convenience function to add a tooltip to a widget

    Args:
        widget: Widget to attach tooltip to
        text: Tooltip text
        delay: Delay before showing (ms)

    Returns:
        ToolTip instance
    """
    return ToolTip(widget, text, delay)


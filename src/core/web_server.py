"""
ZAP Web Server - Test Bed Status Dashboard
Displays real-time information about test beds, devices, test execution, and logs
"""
from flask import Flask, render_template, jsonify, request
from datetime import datetime
import threading
import os
import json
from typing import Dict, List, Optional
import socket


class ZAPWebServer:
    """Web server for displaying ZAP test bed status and information"""

    def __init__(self, port: int = 5000):
        """
        Initialize the ZAP web server

        Args:
            port: Port number to run the server on (default: 5000)
        """
        self.port = port
        self.app = Flask(__name__,
                        template_folder=os.path.join(os.path.dirname(__file__), '../web/templates'),
                        static_folder=os.path.join(os.path.dirname(__file__), '../web/static'))
        self.server_thread = None
        self.running = False

        # Data storage
        self.test_bed_status = {
            'online': True,
            'ip_address': self._get_local_ip(),
            'hostname': socket.gethostname(),
            'last_updated': datetime.now().isoformat(),
            'zap_version': '2.0.0'
        }

        self.devices_status = []
        self.test_execution_status = {
            'in_progress': False,
            'test_name': None,
            'start_time': None,
            'devices_in_use': [],
            'current_test': None,
            'total_tests': 0,
            'passed': 0,
            'failed': 0
        }

        self.logs = []
        self.max_logs = 1000  # Keep last 1000 log entries

        self._setup_routes()

    def _get_local_ip(self) -> str:
        """Get the local IP address of this machine"""
        try:
            # Create a socket connection to determine local IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    def _setup_routes(self):
        """Setup Flask routes"""

        @self.app.route('/')
        def index():
            """Main dashboard page"""
            return render_template('dashboard.html')

        @self.app.route('/api/testbed')
        def get_testbed_status():
            """API endpoint for test bed status"""
            return jsonify(self.test_bed_status)

        @self.app.route('/api/devices')
        def get_devices():
            """API endpoint for device status"""
            return jsonify({
                'devices': self.devices_status,
                'count': len(self.devices_status)
            })

        @self.app.route('/api/test-execution')
        def get_test_execution():
            """API endpoint for test execution status"""
            return jsonify(self.test_execution_status)

        @self.app.route('/api/logs')
        def get_logs():
            """API endpoint for logs"""
            limit = request.args.get('limit', 100, type=int)
            level = request.args.get('level', 'all')

            filtered_logs = self.logs
            if level != 'all':
                filtered_logs = [log for log in self.logs if log.get('level') == level]

            return jsonify({
                'logs': filtered_logs[-limit:],
                'total': len(filtered_logs)
            })

        @self.app.route('/api/logs/download')
        def download_logs():
            """API endpoint to download logs as JSON"""
            return jsonify({
                'logs': self.logs,
                'exported_at': datetime.now().isoformat(),
                'test_bed': self.test_bed_status
            })

    def update_testbed_status(self, online: bool = True, **kwargs):
        """
        Update test bed status

        Args:
            online: Whether test bed is online
            **kwargs: Additional status fields to update
        """
        self.test_bed_status['online'] = online
        self.test_bed_status['last_updated'] = datetime.now().isoformat()

        for key, value in kwargs.items():
            self.test_bed_status[key] = value

    def update_devices(self, devices: List[Dict]):
        """
        Update connected devices list

        Args:
            devices: List of device dictionaries with model, serial, status, etc.
        """
        self.devices_status = devices
        self.test_bed_status['last_updated'] = datetime.now().isoformat()

    def start_test_execution(self, test_name: str, devices: List[str], total_tests: int = 0):
        """
        Mark test execution as started

        Args:
            test_name: Name of the test being executed
            devices: List of device serials being used
            total_tests: Total number of tests to run
        """
        self.test_execution_status = {
            'in_progress': True,
            'test_name': test_name,
            'start_time': datetime.now().isoformat(),
            'devices_in_use': devices,
            'current_test': None,
            'total_tests': total_tests,
            'passed': 0,
            'failed': 0
        }

    def update_test_progress(self, current_test: str = None, passed: int = None, failed: int = None):
        """
        Update test execution progress

        Args:
            current_test: Name of currently executing test
            passed: Number of passed tests
            failed: Number of failed tests
        """
        if current_test is not None:
            self.test_execution_status['current_test'] = current_test
        if passed is not None:
            self.test_execution_status['passed'] = passed
        if failed is not None:
            self.test_execution_status['failed'] = failed

    def end_test_execution(self):
        """Mark test execution as complete"""
        self.test_execution_status['in_progress'] = False
        self.test_execution_status['end_time'] = datetime.now().isoformat()

    def add_log(self, message: str, level: str = 'info', source: str = 'ZAP'):
        """
        Add a log entry

        Args:
            message: Log message
            level: Log level (info, success, warning, error)
            source: Source of the log (ZAP, Zybot, Polarion, etc.)
        """
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'level': level,
            'message': message,
            'source': source
        }

        self.logs.append(log_entry)

        # Trim logs if exceeding max
        if len(self.logs) > self.max_logs:
            self.logs = self.logs[-self.max_logs:]

    def clear_logs(self):
        """Clear all stored logs"""
        self.logs = []

    def start(self):
        """Start the web server in a background thread"""
        if self.running:
            return

        self.running = True
        self.server_thread = threading.Thread(target=self._run_server, daemon=True)
        self.server_thread.start()

        print(f"🌐 ZAP Web Server started at http://{self.test_bed_status['ip_address']}:{self.port}")
        print(f"   Also accessible at http://localhost:{self.port}")

    def _run_server(self):
        """Run the Flask server"""
        self.app.run(host='0.0.0.0', port=self.port, debug=False, use_reloader=False)

    def stop(self):
        """Stop the web server"""
        self.running = False
        # Note: Flask doesn't have a clean shutdown method
        # The thread will terminate when the main application exits


# Singleton instance
_web_server_instance = None


def get_web_server(port: int = 5000) -> ZAPWebServer:
    """
    Get or create the web server singleton instance

    Args:
        port: Port number for the server

    Returns:
        ZAPWebServer instance
    """
    global _web_server_instance
    if _web_server_instance is None:
        _web_server_instance = ZAPWebServer(port=port)
    return _web_server_instance


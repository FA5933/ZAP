import subprocess
import os

class ZybotExecutor:
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger

    def run_custom_command(self, command, stop_event=None):
        """Execute a custom Zybot command

        Args:
            command: Custom command string to execute
            stop_event: Threading event for cancellation

        Returns:
            str: Result status ("Pass", "Fail", or "Cancelled")
        """
        self.logger.log(f"Executing custom Zybot command: {command}")

        try:
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True, text=True)

            for line in iter(process.stdout.readline, ''):
                if stop_event and stop_event.is_set():
                    process.terminate()
                    self.logger.log("⚠️ Zybot execution cancelled by user", level='warning')
                    return "Cancelled"

                self.logger.log(line.strip())

            process.stdout.close()
            return_code = process.wait()

            if return_code == 0:
                self.logger.log("Zybot execution completed successfully.", level='success')
                return "Pass"
            else:
                self.logger.log(f"Zybot execution failed with return code {return_code}.", level='error')
                return "Fail"
        except Exception as e:
            self.logger.log(f"An error occurred during Zybot execution: {e}", level='error')
            return "Fail"

    def run_tests(self, polarion_run_name, devices, sttls, stop_event=None):
        command = self.get_command_string(polarion_run_name, devices, sttls)

        self.logger.log(f"Executing Zybot command: {command}")

        try:
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True, text=True)

            for line in iter(process.stdout.readline, ''):
                if stop_event and stop_event.is_set():
                    process.terminate()
                    self.logger.log("⚠️ Zybot execution cancelled by user", level='warning')
                    return "Cancelled"

                self.logger.log(line.strip())

            process.stdout.close()
            return_code = process.wait()

            if return_code == 0:
                self.logger.log("Zybot execution completed successfully.", level='success')
                return "Pass"
            else:
                self.logger.log(f"Zybot execution failed with return code {return_code}.", level='error')
                return "Fail"
        except Exception as e:
            self.logger.log(f"An error occurred during Zybot execution: {e}", level='error')
            return "Fail"

    def get_command_string(self, polarion_run_name, devices, sttls):
        zybot_path = self.config.get('Zybot', 'path')
        command = f'"{zybot_path}" -d "{polarion_run_name}"'
        for dut, device_id in devices.items():
            command += f' -v {dut}:{device_id}'
        for sttl in sttls:
            command += f' -t "{sttl}"'
        command += " /TS/" # Placeholder for the test suite path
        return command

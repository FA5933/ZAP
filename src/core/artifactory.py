import requests
import os
import subprocess
import time
import re
from bs4 import BeautifulSoup

class ArtifactoryManager:
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        # Get credentials from config
        self.username = self.config.get('JFrog', 'username', fallback=None)
        self.password = self.config.get('JFrog', 'password', fallback=None)
        self.api_key = self.config.get('JFrog', 'api_key', fallback=None)

        # Set up authentication
        self.auth = None
        self.headers = {}

        if self.username and self.password:
            self.auth = (self.username, self.password)
            self.logger.log(f"Using Basic Authentication with username: {self.username}")
        elif self.api_key:
            self.headers['X-JFrog-Art-Api'] = self.api_key
            self.logger.log("Using API Key authentication")
        else:
            self.logger.log("JFrog credentials not found in config.ini. Downloads will likely fail.", level='error')

    def _find_build_file_in_directory(self, dir_url):
        """
        Recursively search for build file in directory
        Looks specifically in user/gms/ subdirectory structure

        Args:
            dir_url (str): Directory URL to search

        Returns:
            str: URL of the build file
        """
        self.logger.log(f"Searching for build files in: {dir_url}")

        response = requests.get(
            dir_url,
            auth=self.auth,
            headers=self.headers,
            timeout=30
        )
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        links = soup.find_all('a')

        # Collect all files and directories
        zip_files = []
        subdirectories = []

        for link in links:
            href = link.get('href', '')
            if href and not href.startswith('/') and not href.startswith('..'):
                if href.endswith('.zip'):
                    zip_files.append(href)
                    self.logger.log(f"Found zip file: {href}")
                elif href.endswith('/'):
                    subdirectories.append(href)
                    self.logger.log(f"Found subdirectory: {href}")

        # Priority: Look for user/ or gms/ directories first
        if 'user/' in subdirectories:
            self.logger.log("Found user/ directory, navigating into it...")
            return self._find_build_file_in_directory(dir_url.rstrip('/') + '/user/')

        if 'gms/' in subdirectories:
            self.logger.log("Found gms/ directory, navigating into it...")
            return self._find_build_file_in_directory(dir_url.rstrip('/') + '/gms/')

        # Priority 1: Look for FULL_UPDATE packages (for sideload)
        for zip_file in zip_files:
            if 'FULL_UPDATE' in zip_file.upper() or 'FULL-UPDATE' in zip_file.upper():
                self.logger.log(f"Found FULL_UPDATE package: {zip_file}")
                return dir_url.rstrip('/') + '/' + zip_file

        # Priority 2: Look for FULL packages
        for zip_file in zip_files:
            if 'FULL' in zip_file.upper():
                self.logger.log(f"Found FULL package: {zip_file}")
                return dir_url.rstrip('/') + '/' + zip_file

        # Priority 3: Look for any .zip file with common update keywords
        update_keywords = ['UPDATE', 'PACKAGE', 'BUILD', 'RELEASE', 'OTA']
        for zip_file in zip_files:
            if any(keyword in zip_file.upper() for keyword in update_keywords):
                self.logger.log(f"Found update package: {zip_file}")
                return dir_url.rstrip('/') + '/' + zip_file

        # Priority 4: Take any .zip file
        if zip_files:
            selected_zip = sorted(zip_files, reverse=True)[0]
            self.logger.log(f"Using zip file: {selected_zip}")
            return dir_url.rstrip('/') + '/' + selected_zip

        # Priority 5: Look in other subdirectories
        remaining_subdirs = [s for s in subdirectories if s not in ['user/', 'gms/']]
        if remaining_subdirs:
            self.logger.log(f"Searching {len(remaining_subdirs)} other subdirectories...")
            for subdir in remaining_subdirs:
                try:
                    return self._find_build_file_in_directory(dir_url.rstrip('/') + '/' + subdir)
                except Exception as e:
                    self.logger.log(f"No build in {subdir}: {e}")
                    continue

        # Nothing found
        error_msg = f"No build file found in {dir_url}"
        raise Exception(error_msg)

    def download_build(self, build_link, download_dir="builds", max_retries=3):
        """Download a build from JFrog Artifactory

        Args:
            build_link: URL to the build artifact or directory
            download_dir: Directory to save the downloaded file
            max_retries: Maximum retry attempts

        Returns:
            str: Path to the downloaded file, or None if download failed
        """
        self.logger.log(f"Downloading build from {build_link}")

        if not self.auth and not self.api_key:
            self.logger.log("Cannot download build: JFrog credentials are missing.", level='error')
            return None

        try:
            # Create download directory if it doesn't exist
            if not os.path.exists(download_dir):
                os.makedirs(download_dir)
                self.logger.log(f"Created download directory: {download_dir}")

            # Check if this is a directory URL or direct file URL
            is_directory = build_link.endswith('/') or '.' not in build_link.split('/')[-1]

            actual_file_url = build_link
            file_name = None

            if is_directory:
                self.logger.log("Detected directory URL, searching for build files...")
                # Navigate directory structure to find actual build file
                list_url = build_link if build_link.endswith('/') else build_link + '/'
                actual_file_url = self._find_build_file_in_directory(list_url)
                file_name = os.path.basename(actual_file_url)
                self.logger.log(f"Found build file: {file_name}")
            else:
                # Direct file URL
                file_name = build_link.split('/')[-1]
                if not file_name:
                    file_name = "build.zip"

            file_path = os.path.join(download_dir, file_name)

            # Check if partial download exists
            resume_byte_pos = 0
            if os.path.exists(file_path):
                resume_byte_pos = os.path.getsize(file_path)
                self.logger.log(f"Resuming download from byte position: {resume_byte_pos}")

            # Download with retries
            for attempt in range(max_retries):
                try:
                    # Set up headers for resume if needed
                    headers = dict(self.headers)  # Copy existing headers
                    if resume_byte_pos > 0:
                        headers['Range'] = f'bytes={resume_byte_pos}-'

                    self.logger.log(f"Downloading from: {actual_file_url}")
                    response = requests.get(
                        actual_file_url,
                        auth=self.auth,
                        headers=headers,
                        stream=True,
                        timeout=None  # No timeout for large files
                    )
                    response.raise_for_status()

                    # Get file size for progress tracking
                    if 'content-range' in response.headers:
                        # Resume case
                        content_range = response.headers['content-range']
                        total_size = int(content_range.split('/')[-1])
                    else:
                        # Fresh download
                        total_size = int(response.headers.get('content-length', 0))

                    downloaded = resume_byte_pos
                    mode = 'ab' if resume_byte_pos > 0 else 'wb'

                    self.logger.log(f"File size: {total_size / (1024**2):.2f} MB")
                    if resume_byte_pos > 0:
                        self.logger.log(f"Already downloaded: {resume_byte_pos / (1024**2):.2f} MB")

                    # Use larger chunk size for faster downloads
                    chunk_size = 1024 * 1024  # 1 MB chunks

                    with open(file_path, mode) as f:
                        last_print_time = time.time()
                        for chunk in response.iter_content(chunk_size=chunk_size):
                            if chunk:
                                f.write(chunk)
                                downloaded += len(chunk)

                                # Update progress every 2 seconds
                                current_time = time.time()
                                if total_size > 0 and (current_time - last_print_time >= 2):
                                    percent = (downloaded / total_size) * 100
                                    self.logger.log(f"Download progress: {percent:.1f}%")
                                    last_print_time = current_time

                    self.logger.log(f"Build downloaded successfully: {file_path}", level='success')
                    return file_path

                except (requests.exceptions.ChunkedEncodingError,
                        requests.exceptions.ConnectionError) as e:

                    if attempt < max_retries - 1:
                        # Update resume position
                        if os.path.exists(file_path):
                            resume_byte_pos = os.path.getsize(file_path)

                        self.logger.log(f"Download interrupted at {resume_byte_pos / (1024**2):.0f} MB: {e}", level='error')
                        self.logger.log(f"Retrying download (attempt {attempt + 2}/{max_retries})...")
                        time.sleep(5)
                        continue
                    else:
                        self.logger.log(f"Failed to download build after {max_retries} attempts", level='error')
                        raise

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                self.logger.log("Authentication failed (401). Please verify your JFrog credentials in config.ini.", level='error')
            else:
                self.logger.log(f"HTTP Error downloading build: {e}", level='error')
            return None
        except Exception as e:
            self.logger.log(f"Unexpected error during download: {e}", level='error')
            import traceback
            self.logger.log(f"Traceback: {traceback.format_exc()}")
            return None

    def download_and_flash_build(self, build_link, device_serial=None):
        """Download and immediately flash a build

        Args:
            build_link: URL to the build artifact
            device_serial: Serial number of device to flash (None for first device)
        """
        file_path = self.download_build(build_link)
        if file_path:
            self.flash_build(file_path, device_serial)

    def flash_build(self, file_path, device_serial=None, stop_event=None, app=None):
        """Flash a build file to connected device

        Args:
            file_path: Path to the build file (can be relative or absolute)
            device_serial: Serial number of device to flash (None for first device)
            stop_event: Threading event for cancellation
            app: App instance for progress updates
        """
        if not os.path.exists(file_path):
            self.logger.log(f"Build file not found: {file_path}", level='error')
            return

        self.logger.log(f"Flashing build: {file_path}")

        if device_serial:
            self.logger.log(f"Target device: {device_serial}")
        else:
            self.logger.log("Target device: First available device")

        # Actual flashing logic using adb sideload
        try:
            # First, reboot to recovery
            self.logger.log("Rebooting device to recovery mode...")
            cmd = ["adb"]
            if device_serial:
                cmd.extend(["-s", device_serial])
            cmd.extend(["reboot", "recovery"])

            subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=30)

            # Wait for device to enter recovery
            self.logger.log("Waiting for device to enter recovery mode...")
            time.sleep(15)

            # Check for cancellation
            if stop_event and stop_event.is_set():
                self.logger.log("⚠️ Flash cancelled by user", level='warning')
                return

            # Start sideload
            self.logger.log("Starting sideload...")
            if app:
                app.update_progress(0, 100, "Flashing")

            cmd = ["adb"]
            if device_serial:
                cmd.extend(["-s", device_serial])
            cmd.extend(["sideload", file_path])

            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                     text=True, bufsize=1)

            # Monitor process output
            for line in iter(process.stdout.readline, ''):
                if stop_event and stop_event.is_set():
                    process.terminate()
                    self.logger.log("⚠️ Flash cancelled by user", level='warning')
                    return

                line = line.strip()
                if line:
                    self.logger.log(f"Flash: {line}")

                    # Try to parse progress from output
                    if '%' in line:
                        try:
                            percent_str = line.split('%')[0].split()[-1]
                            percent = float(percent_str)
                            if app:
                                app.update_progress(percent, 100, "Flashing")
                        except:
                            pass

            return_code = process.wait()

            if app:
                app.hide_progress()

            if return_code == 0:
                self.logger.log("✅ Build flashed successfully!", level='success')
            else:
                self.logger.log(f"⚠️ Flash completed with return code {return_code}", level='warning')

        except subprocess.TimeoutExpired:
            self.logger.log("⚠️ Reboot to recovery timed out", level='error')
        except subprocess.CalledProcessError as e:
            self.logger.log(f"❌ Flash failed: {e.stderr if e.stderr else str(e)}", level='error')
            if app:
                app.hide_progress()
        except Exception as e:
            self.logger.log(f"❌ Unexpected error during flash: {e}", level='error')
            if app:
                app.hide_progress()

    def upload_logs(self, log_file_path):
        self.logger.log(f"Uploading logs to webpage from {log_file_path}")
        webpage_url = self.config.get('Webpage', 'url')
        try:
            with open(log_file_path, 'rb') as f:
                files = {'file': (os.path.basename(log_file_path), f)}
                response = requests.post(webpage_url, files=files)
                response.raise_for_status()
            self.logger.log("Logs uploaded successfully.")
        except Exception as e:
            self.logger.log(f"Failed to upload logs: {e}", level='error')


# 🦓 ZAP - Zebra Automation Platform

**Version:** 1.0  
**Last Updated:** November 19, 2025  
**Author:** Zebra Technologies

## 📋 Overview

ZAP (Zebra Automation Platform) is a comprehensive GUI-based automation tool designed to streamline the testing and deployment workflow for Zebra Android devices. It provides an intuitive interface for downloading builds from JFrog Artifactory, flashing devices, managing Polarion test runs, and executing Zybot test scripts.

## ✨ Key Features

### 🎨 Modern GUI Interface
- **Sleek, professional design** with color-coded sections
- **Responsive layout** that works at any window size
- **Scrollable content** for easy navigation
- **Real-time device monitoring** with detailed information cards
- **Live system logs** with color-coded messages

### 📦 JFrog Artifactory Integration
- **Three operation modes:**
  - 📥 **Download Only** - Save builds for later use
  - ⚡ **Download & Flash** - One-click download and flash
  - 📁 **Flash Local** - Flash previously downloaded builds
- **Smart directory navigation** - Automatically finds builds in complex folder structures
- **Resume capability** - Interrupted downloads automatically resume
- **Progress tracking** - Real-time download progress with file size information
- **Priority-based file selection** - Finds FULL_UPDATE, OTA, and other package types

### 📱 Device Management
- **Real-time ADB monitoring** - Auto-detects connected devices every 5 seconds
- **Device selection dropdown** - Choose target device for flashing
- **Detailed device cards** - Shows model, serial number, and status
- **Multi-device support** - Manage multiple devices simultaneously
- **PC status monitoring** - Shows host machine information

### 🎯 Polarion Integration
- **Test run management** - Download STTLs from Polarion test runs
- **API integration** - Fetch test cases automatically
- **Result uploading** - Post test results back to Polarion

### 🤖 Zybot Execution
- **Four DUT slots** - Configure up to 4 devices under test
- **STTL-based testing** - Execute tests from Polarion STTLs
- **Command preview** - See the generated Zybot command before execution
- **Flexible test suite paths** - Configure test locations

### 📧 Email Notifications
- **Automated alerts** - Send test results and logs via email
- **SMTP configuration** - Supports Office 365 and other SMTP servers
- **Attachment support** - Include logs and execution results

### 🛠️ Kill Process Control
- **Emergency stop** - Terminate running operations
- **Process management** - Clean shutdown of background tasks

## 🏗️ Architecture

```
ZAP_ZebraAutomationPlatform/
├── config.ini              # Configuration file
├── requirements.txt        # Python dependencies
├── README.md              # This file
│
├── src/
│   ├── main.py            # Application entry point
│   │
│   ├── gui/
│   │   └── main_window.py # GUI implementation
│   │
│   ├── core/
│   │   ├── artifactory.py    # JFrog Artifactory integration
│   │   ├── monitoring.py     # Device monitoring daemon
│   │   ├── polarion.py       # Polarion API integration
│   │   ├── zybot.py          # Zybot execution
│   │   └── email_notifier.py # Email notifications
│   │
│   ├── utils/
│   │   └── logger.py      # Logging system
│   │
│   └── builds/            # Downloaded builds storage
│
└── logs/                  # Application logs (auto-generated)
```

## 🚀 Installation

### Prerequisites

1. **Python 3.8 or higher**
   ```bash
   python --version
   ```

2. **ADB (Android Debug Bridge)**
   - Download from: https://developer.android.com/studio/releases/platform-tools
   - Add to system PATH
   - Verify installation:
     ```bash
     adb --version
     ```

3. **Git** (optional, for version control)

### Setup Steps

1. **Clone or download the repository**
   ```bash
   cd C:\Users\YourUsername\PycharmProjects
   git clone <repository-url> ZAP_or_ZyButler_Gemini
   ```

2. **Navigate to project directory**
   ```bash
   cd ZAP_or_ZyButler_Gemini\ZAP_ZebraAutomationPlatform
   ```

3. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure the application**
   - Edit `config.ini` with your credentials and settings
   - See [Configuration](#-configuration) section below

5. **Run the application**
   ```bash
   cd src
   python main.py
   ```

## ⚙️ Configuration

Edit the `config.ini` file to configure ZAP for your environment:

### JFrog Artifactory
```ini
[JFrog]
url = https://artifactory-us.zebra.com/artifactory/
username = your_username
password = your_password
api_key = your_api_key_optional
```
**Note:** The application prefers Basic Authentication (username + password) but can fall back to API Key.

### Polarion
```ini
[Polarion]
url = https://polarion.zebra.com
user = your_username
token = your_polarion_token
```

### Email Notifications
```ini
[Email]
smtp_server = smtp.office365.com
smtp_port = 587
sender_email = your_email@zebra.com
sender_password = your_email_password
recipient_email = recipient@zebra.com
```

### Zybot
```ini
[Zybot]
path = C:/path/to/zybot.exe
```

### Webpage (Log Upload)
```ini
[Webpage]
url = https://your-log-server.com/logs
```

## 📖 Usage Guide

### Downloading Builds

1. **Select Target Device**
   - Choose device from the "Target Device" dropdown
   - Device list updates automatically every 5 seconds

2. **Enter Build URL**
   - Paste JFrog Artifactory URL in "Build URL" field
   - Example: `https://artifactory-us.zebra.com/.../daily/2025-11-19-01-01/user/`

3. **Choose Operation**
   - **📥 Download Only** - Downloads to `src/builds/` folder
   - **⚡ Download & Flash** - Downloads and immediately flashes device
   - **📁 Browse + Flash** - Select local build file and flash

4. **Monitor Progress**
   - Watch logs for download progress
   - File size and percentage shown in real-time
   - Downloads resume automatically if interrupted

### Managing Polarion Test Runs

1. **Enter Test Run URL**
   - Paste Polarion test run link in "Test Run URL" field

2. **Download STTLs**
   - Click "📥 Download STTLs" button
   - STTLs are fetched from Polarion API
   - Review in the command preview section

### Executing Zybot Tests

1. **Configure Devices**
   - Select devices for each DUT slot (DUT1-DUT4)
   - Devices must be connected via ADB

2. **Ensure STTLs are Downloaded**
   - STTLs must be fetched from Polarion first

3. **Run Tests**
   - Click "▶ Run Zybot Tests" button
   - Monitor execution in system logs
   - Test results logged automatically

### Monitoring Devices

The right panel shows:
- **Device Status** - Connected device count with color indicator
  - 🟢 Green = Devices connected
  - 🔴 Red = No devices
  - 🟠 Orange = ADB not found

- **Device Cards** - Individual cards for each device showing:
  - Device number (Device 1, Device 2, etc.)
  - Model name
  - Serial number

- **PC Status** - Host machine information and IP address

### Emergency Stop

Click the **"🛑 Kill Process"** button to terminate any running operation.

## 🎨 GUI Layout

```
┌─────────────────────────────────────────────────────────────────┐
│  🦓 ZAP - Zebra Automation Platform                            │
├────────────────────────────────┬────────────────────────────────┤
│  Left Panel (Scrollable)       │  Right Panel (Fixed)           │
│  ┌──────────────────────────┐  │  ┌──────────────────────────┐ │
│  │ 🎯 Polarion Test Run     │  │  │ 📊 System Status         │ │
│  │   URL: [____________]    │  │  │   Devices: 🟢 2 Connected│ │
│  │   [📥 Download STTLs]    │  │  │                          │ │
│  └──────────────────────────┘  │  │   📱 Device 1            │ │
│                                 │  │   Model: TC21            │ │
│  ┌──────────────────────────┐  │  │   Serial: ABC123456      │ │
│  │ 🤖 Zybot Test Execution  │  │  │                          │ │
│  │   DUT1: [TC21 ▼]         │  │  │   📱 Device 2            │ │
│  │   DUT2: [____]           │  │  │   Model: TC27            │ │
│  │   [▶ Run Zybot Tests]    │  │  │   Serial: DEF789012      │ │
│  └──────────────────────────┘  │  │                          │ │
│                                 │  │   💻 PC Status           │ │
│  ┌──────────────────────────┐  │  │   IP: 192.168.1.100     │ │
│  │ 📜 Generated Command     │  │  │                          │ │
│  │   zybot -v DUT1:ABC...   │  │  │   [🛑 Kill Process]      │ │
│  └──────────────────────────┘  │  └──────────────────────────┘ │
│                                 │                                │
│  ┌──────────────────────────┐  │                                │
│  │ 📦 JFrog Artifactory     │  │                                │
│  │   Target Device: [▼]     │  │                                │
│  │   URL: [____________]    │  │                                │
│  │   [📥 Download Only]     │  │                                │
│  │   [⚡ Download & Flash]   │  │                                │
│  │   ───────────────────    │  │                                │
│  │   Local: [___] [📁] [⚡] │  │                                │
│  └──────────────────────────┘  │                                │
│                                 │                                │
│  ┌──────────────────────────┐  │                                │
│  │ 📋 System Logs           │  │                                │
│  │   [INFO] Device connected│  │                                │
│  │   [SUCCESS] Downloaded   │  │                                │
│  └──────────────────────────┘  │                                │
└────────────────────────────────┴────────────────────────────────┘
```

## 🐛 Troubleshooting

### ADB Not Found
**Issue:** "ADB Not Found" warning in device status

**Solution:**
1. Install Android Platform Tools
2. Add ADB to system PATH
3. Restart application
4. Verify with: `adb devices`

### Authentication Failed (401)
**Issue:** Cannot download from Artifactory

**Solution:**
1. Check `config.ini` credentials
2. Verify username and password are correct
3. Ensure you have access to the repository
4. Try regenerating API key if using token authentication

### No Devices Detected
**Issue:** Devices not showing in monitoring panel

**Solution:**
1. Ensure device is connected via USB
2. Enable USB debugging on device
3. Accept ADB authorization on device screen
4. Check cable connection
5. Try: `adb kill-server && adb start-server`

### Download Interrupted
**Issue:** Large file download stops mid-way

**Solution:**
- No action needed! The application automatically resumes downloads
- Retry button will continue from last position
- Check network connection if repeatedly failing

### Polarion API Errors
**Issue:** Cannot fetch STTLs from Polarion

**Solution:**
1. Verify Polarion URL in config
2. Check API token is valid
3. Ensure you have access to the test run
4. Try manual STTL input if API fails

## 📊 System Requirements

### Minimum Requirements
- **OS:** Windows 10 or higher
- **Python:** 3.8+
- **RAM:** 4 GB
- **Disk Space:** 10 GB (for builds storage)
- **Network:** Stable internet connection for downloads

### Recommended Requirements
- **OS:** Windows 11
- **Python:** 3.12+
- **RAM:** 8 GB or higher
- **Disk Space:** 50 GB SSD
- **Network:** High-speed connection (downloads can be 1GB+)

## 📦 Dependencies

All dependencies are listed in `requirements.txt`:

```
requests>=2.31.0        # HTTP requests for API calls
beautifulsoup4>=4.12.0  # HTML parsing for directory listings
watchdog>=3.0.0         # File system monitoring
pyinstaller>=6.0.0      # Build executable (optional)
```

**Built-in Python Modules:**
- tkinter (GUI framework)
- threading (multi-threading)
- configparser (config file parsing)
- os, subprocess, time, re (system utilities)
- smtplib, email (email notifications)

## 🔐 Security Notes

- **Credentials Storage:** All credentials stored in `config.ini`
- **Keep config.ini secure** - Never commit to version control
- **Use strong passwords** for all accounts
- **API tokens** recommended over passwords when available
- **Network security** - Ensure secure connection to Artifactory

## 📝 Logging

### Log Files
- **Location:** `src/` directory
- **Format:** `zap_log_YYYYMMDD_HHMMSS.txt`
- **Retention:** Manual cleanup required
- **Content:** All operations, errors, and status messages

### Log Levels
- 🔵 **INFO** - Normal operations (black text)
- 🟢 **SUCCESS** - Successful operations (green text)
- 🔴 **ERROR** - Errors and failures (red text)
- 🟠 **WARNING** - Warnings and alerts (orange text)

## 🤝 Contributing

To contribute to ZAP:

1. Follow Python PEP 8 style guidelines
2. Add docstrings to all functions
3. Test thoroughly before committing
4. Update README for new features
5. Keep config.ini template updated

## 📄 License

**Proprietary Software**  
© 2025 Zebra Technologies Corporation  
All rights reserved.

This software is the property of Zebra Technologies and is intended for internal use only.

## 📞 Support

For issues, questions, or feature requests:

- **Email:** automation-support@zebra.com
- **Internal Wiki:** [Link to internal documentation]
- **Issue Tracker:** [Link to issue tracker]

## 🎯 Roadmap

### Planned Features
- [ ] Batch device flashing
- [ ] Scheduled test execution
- [ ] Enhanced reporting dashboard
- [ ] Test result visualization
- [ ] Custom test suite builder
- [ ] Remote device management
- [ ] Build comparison tool
- [ ] Automated regression testing

## 🙏 Acknowledgments

- **Development Team:** Zebra Automation Team
- **Testing:** QA Engineering Team
- **UI/UX Design:** Product Design Team
- **Documentation:** Technical Writing Team

---

**Version History:**
- **v1.0** (Nov 2025) - Initial release with core functionality
  - JFrog Artifactory integration
  - Device monitoring and flashing
  - Polarion integration
  - Zybot execution
  - Modern GUI interface

---

Made with ❤️ by Zebra Technologies | 🦓 Empowering the frontline workforce


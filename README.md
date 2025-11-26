This is a fork of JCOvergaar’s excellent [CPAP-data-from-EZShare-SD tool](https://github.com/JCOvergaar/CPAP-data-from-EZShare-SD) for gathering CPAP data wirelessly from ResMed machines. It does so by using a WiFi-enabled SD card by ez Share (these can be found relatively inexpensively on sites like Ali Express).

Like that original tool, the program assists in copying the data from the SD card in the CPAP device to a local directory. Then (optionally) that data can be automatically uploaded to a [SleepHQ](https://sleephq.com) Pro account. It is compatible with most ResMed devices from version 9 and up. The program runs on Python 3, and requires dependencies to be installed.

> [!NOTE]
> I am absolutely not a programmer by trade, and much of the SleepHQ integration was completed with help from LLM coding assistants (but this documentation was written by hand). Please feel free to create issues or open PRs if the code or docs can be improved in any way!

## Setup

This explanation is fairly detailed in order to be useful to less technically-inclined users.

I find a [Raspberry Pi](https://www.raspberrypi.com/) to be a good conduit for this system, as it can be left on all the time and has WiFi built in. This guide is written for Raspberry Pi/Linux. However, it will work on Mac and Windows as well (there is even a `.bat` installer for Windows).

### Installation and first run

#### 0. Prerequisites

Make sure [Git](https://en.wikipedia.org/wiki/Git) and [Python 3](https://www.python.org/downloads/) are both installed. In your terminal:

```bash
sudo apt update
sudo apt install git
sudo apt install -y python3-pip
```

#### 1. Clone the repository

Navigate to a directory you wish to keep the project in and clone this repo to it.

```bash
cd /path/to/anywhere
git clone https://github.com/johnlago/EZShareToSleepHQ
```

#### 2. Install
Navigate to the project directory and install the program and its dependencies.

```bash
cd EZShareToSleepHQ
./install_ezshare.sh
```

The program, `ezshare_resmed`, is installed in `$HOME/.local/bin`. If that location is not already in the `$PATH`, run one of the following depending on your [shell](https://learn.microsoft.com/en-us/powershell/scripting/what-is-a-command-shell?view=powershell-7.5).

bash:

```bash
 echo 'export PATH="\$HOME/.local/bin:\$PATH"' >> ~/.bashrc && source ~/.bashrc
 ```

zhs:

```bash
echo 'export PATH="\$HOME/.local/bin:\$PATH"' >> ~/.zshrc && source ~/.zshrc
```

#### 3. Set up the config file

In a text editor, copy the following template to create a config file, which will save your settings. Save it in one of these locations:

- `./ezshare_resmed.ini` - In the same directory as the **installed** script
- `./config.ini` - In the same directory as the **installed** script
- `~/.config/ezshare_resmed.ini`
- `~/.config/ezshare_resmed/ezshare_resmed.ini`
- `~/.config/ezshare_resmed/config.ini`

```ini
[ezshare_resmed]

# Path where your CPAP data will be saved
path = ~/Documents/CPAP_Data/SD_card

# URL of the ez Share card's web UI. If you don't know, leave this as is.
url = http://192.168.4.1/dir?dir=A:

# SSID of the ez Share card. If you don't know, leave this as is.
ssid = ez Share

# Wifi password of the ez Share card. If you don't know, leave this as is.
psk = 88888888

# Earliest date (YYYYMMDD) for data to be considered for transfer (this will override day_count if set). Comment or delete the following line to unset.
start_from = 20251110

# Number of days to transfer. (If both start_from and day_count are unset, all files will be considered for transfer.) Comment or delete the following line to unset.
day_count = 0

# Show progress when run from the command line
show_progress = True

# Show verbose messages when run from the command line
verbose = False

# Force overwriting existing files
overwrite = False

# Do not overwrite existing files even if a newer version is available
keep_old = False

# Case-insensitive comma separated list (no spaces) of files to ignore
ignore = JOURNAL.JNL,ezshare.cfg,System Volume Information

# Number of times to retry if transfer fails
retries = 5


[sleephq]

# Enable or disable upload to SleepHQ
enabled = True

# Your SleepHQ client ID
client_id = your_sleephq_client_id

# Your SleepHQ client secret
client_secret = your_sleephq_client_secret

```

In order to get your SleepHQ client ID and secret, you must be a [Pro plan subscriber](https://www.sleephq.com/#pricing). Once logged in, click “Account Settings.” In the “API Keys” section, click “Add API Key.” A new row should appear, with buttons to copy each value.

![The API Key section of SleepHQ settings](docs/sleephq_api_keys.jpg)

#### 4. Run the program manually from the terminal

```bash
ezshare_resmed
```

If it’s installed and configured correctly, it will connect to the SD card’s WiFi network, find new data files, and transfer them to the location you specified in the config file. Next, it will prompt you for your SleepHQ username and password. If it’s successful, it will show feedback about the data as it bundles, uploads, and triggers processing of that data.

### Automate the transfers

After the first run, you should not need to provide the username/password again. Therefore, we can use [cron](https://en.wikipedia.org/wiki/Cron) (or anything else that can trigger the program) to schedule periodic automatic transfers and uploads.

In your terminal, open the crontab editor.

```bash
crontab -e
```

You could add the following line to run every 6 hours:

```bash
0 */6 * * * /path/to/ezshare_resmed
```

Or specify a config file:

```bash
0 */6 * * * /path/to/ezshare_resmed --config /path/to/config.ini
```

I have mine run every 15 minutes between the hours of 7am and 11am (to grab data no matter when I wake up!), with logs being written to a specific file:

```
0,15,30,45 7-11 * * * /home/pi/.local/bin/ezshare_resmed >> /home/pi/cron.log 2>&1
```
> [!NOTE]
> Cron requires the full path to the script, so `ezshare_resmed` alone will not work as it does on the terminal.

The script is smart enough to detect and transfer only data that is new on each run, and SleepHQ also deduplicates redundant data. Therefore, it’s safe to run this script at a regular interval — _even while your ResMed machine is in use_ — without bloating your local storage or creating very large SleepHQ uploads.

## Command line usage

The script may be run directly from the terminal with optional flags, rather than a config file. These are the options:

| Argument                                | Description                                                                                                                              |
| --------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| `-h`, `--help`                          | Show this help message and exit                                                                                                          |
| `--path PATH`                           | Path where your CPAP data will be saved. Defaults to `$HOME/Documents/CPAP_Data/SD_card`                                                 |
| `--url URL`                             | URL of the ez Share card’s web UI. Defaults to `http://192.168.4.1/dir?dir=A:`                                                            |
| `--start_from START_FROM`               | Earliest date (YYYYMMDD) for data to be considered for transfer (this will override `day_count` if set).                                 |
| `--day_count DAY_COUNT`, `-n DAY_COUNT` | Number of days to transfer. If both `start_from` and `day_count` are unset, all files will be considered for transfer. Defaults to None. |
| `--show_progress`                       | Show progress. Defaults to True.                                                                                                         |
| `--verbose`, `-v`                       | Verbose output. Defaults to False.                                                                                                       |
| `--overwrite`                           | Force overwriting existing files. Defaults to False.                                                                                     |
| `--keep_old`                            | Do not overwrite even if newer version is available. Defaults to False.                                                                  |
| `--ignore IGNORE`                       | Case-insensitive comma separated list (no spaces) of files to ignore. Defaults to `JOURNAL.JNL,ezshare.cfg,System Volume Information`.   |
| `--ssid SSID`                           | SSID of the ez Share card. WiFi connection will be attempted if set. Defaults to `ez Share`.                                              |
| `--psk PSK`                             | Wifi password of the ez Share card. Defaults to `88888888`.                                                                               |
| `--retries RETRIES`                     | Number of times to retry if transfer fails. Defaults to 5.                                                                               |
| `--upload-to-sleephq`                   | Upload data to a SleepHQ account. Defaults to False.                                                                                     |
| `--sleephq-client-id`                   | SleepHQ client ID. Can be generated at sleephq.com.                                                                                      |
| `--sleephq-client-secret`               | SleepHQ client secret. Can be generated at sleephq.com.                                                                                  |
| `--force-sleephq-upload`                | Force upload of all files to SleepHQ, bypassing the upload tracker                                                                       |
| `--version`                             | Show program’s version number and exit                                                                                                   |

**Example:**

```bash
ezshare_resmed --ssid ezshare --psk 88888888 --show_progress
```

## Miscellany

### Default Data Save Location

- Windows: `C:\Users\<USERNAME>\Documents\CPAP_Data`
- macOS: `/Users/<USERNAME>/Documents/CPAP_Data`
- Linux: `/home/<USERNAME>/Documents/CPAP_Data`

### Re-authenticating with SleepHQ

To re-authenticate (e.g., after changing your password), delete your token file at:

- macOS/Linux: `~/.config/ezshare_resmed/sleephq_token.json`
- Windows: `%APPDATA%\ezshare_resmed\sleephq_token.json`

### Installing Python 3

#### Windows

1. Open a command window. Run `winget install -e --id Python.Python.3.12`
2. Once Python is installed, you should be able to open a command window, type `python`, hit ENTER, and see a Python prompt opened. Type `quit()` to exit it. You should also be able to run the command `pip` and see its options. If both of these work, then you are ready to go.
	- If you cannot run `python` or `pip` from a command prompt, you may need to add the Python installation directory path to the Windows PATH variable
		- The easiest way to do this is to find the new shortcut for Python in your start menu, right-click on the shortcut, and find the folder path for the `python.exe` file
			- For Python3, this will likely be something like `C:\Users\<USERNAME>\AppData\Local\Programs\Python\Python312`
		- Open your Advanced System Settings window, navigate to the “Advanced” tab, and click the “Environment Variables” button
		- Create a new system variable:
			- Variable name: `PYTHON_HOME`
			- Variable value: <your_python_installation_directory>
		- Now modify the PATH system variable by appending the text `;%PYTHON_HOME%\;%PYTHON_HOME%;%PYTHON_HOME%\Scripts\` to the end of it.
		- Close out your windows, open a command window and make sure you can run the commands `python` and `pip`

#### macOS

macOS comes with a native version of Python but it is not recommended to use the native Python in order to not alter the system environment. There are a couple of ways we can install Python3, but this script is only tested using Homebrew.

[Homebrew](https://brew.sh/) is a MacOS Linux-like package manager. Walk through the below steps to install Homebrew and an updated Python interpreter along with it.

1. Open your **Terminal** application and run: `xcode-select --install`. This will open a window. Click **‘Get Xcode’** and install it from the app store.
2. Install Homebrew. Run: `/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"`
	 - You can also find this command on the [Homebrew website](https://brew.sh/)
3. Install latest Python3 with `brew install python`
4. Once Python is installed, you should be able to open your **Terminal** application, type `python3`, hit ENTER, and see a Python 3.X.X prompt opened. Type `quit()` to exit it. You should also be able to run the command `pip3` and see its options. If both of these work, then you are ready to go.
	- Here are some additional resources on [Installing Python 3 on Mac OS X](https://docs.python-guide.org/starting/install3/osx/)

#### Linux

- **Raspberry Pi OS** may need Python and PIP
	- Install them: `sudo apt install -y python3-pip`
- **Debian (Ubuntu)** distributions may need Python and PIP
	- Update the list of available APT repos with `sudo apt update`
	- Install Python and PIP: `sudo apt install -y python3-pip`
- **RHEL (CentOS)** distributions usually need PIP
	- Install the EPEL package: `sudo yum install -y epel-release`
	- Install PIP: `sudo yum install -y python3-pip`
- **Arch** may need Python and PIP
	- Refresh pacman database and update system: `sudo pacman -Syu`
	- Install PIP: `sudo pacman -S python python-pip`
# Zabbix Host Disabler Script

This script connects to a Zabbix server via the Zabbix API and **disables all hosts** that have had the problem "Zabbix agent is not available" for more than a specified number of days (default: 11). It is useful for cleaning up hosts that have been unreachable for an extended period.

## Features

- Authenticates with Zabbix API using username and password.
- Searches for hosts with the "Zabbix agent is not available" problem older than a configurable threshold.
- Optionally disables those hosts (with a dry-run mode for safety).
- Prints a summary of affected hosts and actions taken.

## Requirements

- Python 3.x
- `requests` library

Install dependencies with:
```
pip install requests
```

## Usage

1. **Edit the script configuration:**
   - Set your Zabbix API URL, username, and password at the top of the script:
     ```python
     ZABBIX_URL = "https://your-zabbix-server/api_jsonrpc.php"
     USERNAME = "your_zabbix_username"
     PASSWORD = "your_zabbix_password"
     DAYS_THRESHOLD = 11  # or your preferred threshold
     DRY_RUN = True       # Set to False to actually disable hosts
     ```

2. **Run the script:**
   ```
   python disablehosts.py
   ```

3. **Review the output:**
   - In DRY RUN mode, the script will only show which hosts would be disabled.
   - Set `DRY_RUN = False` and re-run to actually disable the hosts (you will be prompted for confirmation).

## Script Flow

1. **Authenticate** to the Zabbix API.
2. **Query** for problems matching "Zabbix agent is not available" older than the threshold.
3. **List** all affected hosts.
4. **(Optional)** Disable those hosts via the API.

## Safety

- The script defaults to DRY RUN mode. No changes are made unless you set `DRY_RUN = False` and confirm the action.
- Each host disable action is performed individually, with error handling and a summary at the end.

## Disclaimer

- Use with caution! Disabling hosts in Zabbix will stop monitoring and alerting for those hosts.

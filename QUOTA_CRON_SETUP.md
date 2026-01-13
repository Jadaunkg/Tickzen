# Monthly Quota Reset - Cron Job Setup

## Overview

This guide explains how to set up automatic monthly quota resets for the TickZen quota system using cron jobs (Linux/macOS) or Windows Task Scheduler.

---

## Linux / macOS Setup

### Quick Setup (Automated)

The easiest way to set up the cron job is using the provided script:

```bash
# Navigate to project directory
cd /path/to/tickzen2/tickzen2

# Make script executable
chmod +x scripts/setup_quota_cron.sh

# Run setup (may require sudo)
sudo ./scripts/setup_quota_cron.sh
```

### Manual Setup

If you prefer to set it up manually:

1. **Open crontab editor:**
   ```bash
   crontab -e
   ```

2. **Add the following line:**
   ```cron
   # Reset TickZen user quotas on 1st of every month at 12:01 AM
   1 0 1 * * cd /path/to/tickzen2/tickzen2 && python3 scripts/reset_monthly_quotas.py >> logs/quota_reset.log 2>&1
   ```

3. **Save and exit**
   - In vim: Press `ESC`, then `:wq`
   - In nano: Press `Ctrl+X`, then `Y`, then `Enter`

### Cron Schedule Explanation

```
1 0 1 * *
│ │ │ │ │
│ │ │ │ └─── Day of week (0-7) (Sunday=0 or 7) - * means any
│ │ │ └───── Month (1-12) - * means any
│ │ └─────── Day of month (1-31) - 1 means 1st day
│ └───────── Hour (0-23) - 0 means midnight
└─────────── Minute (0-59) - 1 means :01
```

So `1 0 1 * *` means: **1st day of every month at 12:01 AM**

### Verify Cron Job

```bash
# List all cron jobs
crontab -l

# Check logs
tail -f /path/to/tickzen2/tickzen2/logs/quota_reset.log
```

### Test Cron Job Manually

```bash
cd /path/to/tickzen2/tickzen2
python3 scripts/reset_monthly_quotas.py
```

---

## Windows Setup

For Windows servers, use Windows Task Scheduler:

### Method 1: Task Scheduler GUI

1. **Open Task Scheduler**
   - Press `Win + R`
   - Type `taskschd.msc`
   - Press Enter

2. **Create New Task**
   - Click "Create Task" (not "Create Basic Task")
   - Name: `TickZen-MonthlyQuotaReset`
   - Description: `Resets user quotas on the 1st of every month`
   - Select "Run whether user is logged on or not"
   - Check "Run with highest privileges"

3. **Configure Trigger**
   - Go to "Triggers" tab
   - Click "New..."
   - Begin the task: "On a schedule"
   - Settings: "Monthly"
   - Day: 1
   - Time: 12:01 AM
   - Click "OK"

4. **Configure Action**
   - Go to "Actions" tab
   - Click "New..."
   - Action: "Start a program"
   - Program/script: `python`
   - Add arguments: `scripts\reset_monthly_quotas.py`
   - Start in: `C:\path\to\tickzen2\tickzen2`
   - Click "OK"

5. **Configure Settings**
   - Go to "Settings" tab
   - Check "Allow task to be run on demand"
   - Check "Run task as soon as possible after a scheduled start is missed"
   - If the task fails, restart every: 5 minutes
   - Attempt to restart up to: 3 times
   - Click "OK"

### Method 2: PowerShell Command

```powershell
# Run PowerShell as Administrator
$Action = New-ScheduledTaskAction -Execute "python" `
    -Argument "scripts\reset_monthly_quotas.py" `
    -WorkingDirectory "C:\path\to\tickzen2\tickzen2"

$Trigger = New-ScheduledTaskTrigger -Daily -At "12:01AM"

$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries -WakeToRun -StartWhenAvailable

Register-ScheduledTask -TaskName "TickZen-MonthlyQuotaReset" `
    -Action $Action -Trigger $Trigger -Settings $Settings `
    -RunLevel Highest `
    -Description "Resets TickZen user quotas on the 1st of every month"

# Modify trigger to monthly
$Task = Get-ScheduledTask -TaskName "TickZen-MonthlyQuotaReset"
$Task.Triggers[0].Repetition.Interval = "P1M"
Set-ScheduledTask -InputObject $Task
```

### Verify Windows Task

```powershell
# View task
Get-ScheduledTask -TaskName "TickZen-MonthlyQuotaReset"

# Test run
Start-ScheduledTask -TaskName "TickZen-MonthlyQuotaReset"

# Check last run result
Get-ScheduledTask -TaskName "TickZen-MonthlyQuotaReset" | Get-ScheduledTaskInfo
```

---

## Cloud Platform Setup

### Azure App Service

Use Azure Functions with a timer trigger:

**function.json:**
```json
{
  "bindings": [
    {
      "name": "myTimer",
      "type": "timerTrigger",
      "direction": "in",
      "schedule": "0 1 0 1 * *"
    }
  ]
}
```

**__init__.py:**
```python
import logging
import azure.functions as func
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scripts.reset_monthly_quotas import reset_all_user_quotas

def main(myTimer: func.TimerRequest) -> None:
    logging.info('Python timer trigger function started')
    
    try:
        reset_all_user_quotas()
        logging.info('Quota reset completed successfully')
    except Exception as e:
        logging.error(f'Quota reset failed: {e}')
        raise
```

### AWS Lambda

Use AWS EventBridge (CloudWatch Events) with a cron expression:

**Cron expression for EventBridge:**
```
cron(1 0 1 * ? *)
```

**Lambda function:**
```python
import json
import sys
import os

# Add your project path
sys.path.insert(0, '/opt/python/lib/python3.9/site-packages')

from scripts.reset_monthly_quotas import reset_all_user_quotas

def lambda_handler(event, context):
    try:
        reset_all_user_quotas()
        return {
            'statusCode': 200,
            'body': json.dumps('Quota reset completed')
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps(f'Error: {str(e)}')
        }
```

### Google Cloud Functions

Use Cloud Scheduler with Cloud Functions:

**Cloud Scheduler:**
- Schedule: `1 0 1 * *`
- Target: Cloud Function
- HTTP method: POST

**main.py:**
```python
import functions_framework
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from scripts.reset_monthly_quotas import reset_all_user_quotas

@functions_framework.http
def quota_reset(request):
    try:
        reset_all_user_quotas()
        return 'Quota reset completed', 200
    except Exception as e:
        return f'Error: {str(e)}', 500
```

---

## Monitoring & Alerts

### Log Monitoring

**Check logs regularly:**
```bash
# View last 50 lines
tail -50 logs/quota_reset.log

# Watch logs in real-time
tail -f logs/quota_reset.log

# Search for errors
grep -i error logs/quota_reset.log
```

### Email Notifications

Add email notification to the reset script:

```python
# At the end of reset_monthly_quotas.py

def send_notification_email(success_count, error_count):
    """Send email notification after quota reset"""
    import smtplib
    from email.mime.text import MIMEText
    
    subject = f"Quota Reset Complete: {success_count} users reset"
    body = f"""
    Monthly quota reset completed.
    
    Successfully reset: {success_count} users
    Errors: {error_count}
    
    Check logs for details: logs/quota_reset.log
    """
    
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = 'noreply@tickzen.com'
    msg['To'] = 'admin@tickzen.com'
    
    # Configure your SMTP settings
    with smtplib.SMTP('smtp.gmail.com', 587) as server:
        server.starttls()
        server.login('your-email@gmail.com', 'your-app-password')
        server.send_message(msg)
```

### Slack Notifications

```python
def send_slack_notification(success_count, error_count):
    """Send Slack notification after quota reset"""
    import requests
    
    webhook_url = "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
    
    message = {
        "text": f"✅ Monthly quota reset completed",
        "attachments": [{
            "color": "good" if error_count == 0 else "warning",
            "fields": [
                {"title": "Successfully Reset", "value": str(success_count), "short": True},
                {"title": "Errors", "value": str(error_count), "short": True}
            ]
        }]
    }
    
    requests.post(webhook_url, json=message)
```

---

## Troubleshooting

### Cron Job Not Running

**Check cron service:**
```bash
# Linux
sudo service cron status

# macOS
sudo launchctl list | grep cron
```

**Check cron logs:**
```bash
# Ubuntu/Debian
grep CRON /var/log/syslog

# CentOS/RHEL
grep CRON /var/log/cron
```

**Common issues:**
1. **Permissions**: Make sure the script has execute permissions
   ```bash
   chmod +x scripts/reset_monthly_quotas.py
   ```

2. **Python path**: Use absolute path to Python
   ```bash
   which python3  # Get the full path
   ```

3. **Environment variables**: Cron doesn't load your shell environment
   ```cron
   # Add environment variables to crontab
   FIREBASE_PROJECT_ID=your-project-id
   1 0 1 * * cd /path/to/project && python3 scripts/reset_monthly_quotas.py
   ```

### Script Errors

**Test the script directly:**
```bash
cd /path/to/tickzen2/tickzen2
python3 scripts/reset_monthly_quotas.py --dry-run
```

**Check Python dependencies:**
```bash
pip install -r requirements.txt
```

**Check Firebase credentials:**
```bash
# Verify service account file exists
ls -l config/firebase-service-account-key.json
```

---

## Best Practices

1. **Always test first**
   ```bash
   python3 scripts/reset_monthly_quotas.py --dry-run
   ```

2. **Monitor the first few runs**
   - Check logs after the first automated run
   - Verify quota values in Firestore

3. **Set up notifications**
   - Email or Slack alerts for failures
   - Daily/weekly quota usage reports

4. **Keep logs**
   - Rotate log files to prevent disk space issues
   - Archive old logs

5. **Have a backup**
   - Document manual reset procedure
   - Keep backup of quota data

---

## Manual Reset Procedure

If automated reset fails, you can run it manually:

```bash
# Navigate to project
cd /path/to/tickzen2/tickzen2

# Activate virtual environment (if using one)
source venv/bin/activate

# Run reset script
python3 scripts/reset_monthly_quotas.py

# Verify results
python3 scripts/migrate_user_quotas.py --verify
```

---

## Security Considerations

1. **Protect credentials**
   - Never commit service account keys to git
   - Use environment variables or secret managers

2. **Limit permissions**
   - Run cron job with minimal required permissions
   - Use service accounts with least privilege

3. **Audit logs**
   - Regularly review quota reset logs
   - Monitor for unusual patterns

4. **Backup before reset**
   - Consider taking Firestore backup before reset
   - Keep historical quota data

---

## Support

If you encounter issues with the cron setup:

1. Check the logs: `logs/quota_reset.log`
2. Test the script manually
3. Verify Firebase connection
4. Check cron service status
5. Contact system administrator

---

**Last Updated**: January 13, 2026  
**Version**: 1.0

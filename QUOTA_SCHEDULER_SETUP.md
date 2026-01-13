# Monthly Quota Reset Setup Instructions

## Windows Task Scheduler Setup (Manual)

Since creating scheduled tasks requires administrator privileges, follow these steps to set up monthly quota reset:

### Option 1: Using Task Scheduler GUI (Recommended)

1. **Open Task Scheduler**
   - Press `Win + R`, type `taskschd.msc`, and press Enter
   - Or search for "Task Scheduler" in the Start menu

2. **Create a New Task**
   - Click "Create Task" (not "Create Basic Task") in the right panel
   - Name: `TickZen-MonthlyQuotaReset`
   - Description: `Resets TickZen user quotas on the 1st of every month`
   - Select "Run whether user is logged on or not"
   - Check "Run with highest privileges"

3. **Configure the Trigger**
   - Go to the "Triggers" tab
   - Click "New..."
   - Begin the task: "On a schedule"
   - Settings: Monthly
   - Day: 1
   - Time: 12:01 AM
   - Click "OK"

4. **Configure the Action**
   - Go to the "Actions" tab
   - Click "New..."
   - Action: "Start a program"
   - Program/script: `python` (or full path: `C:\Users\visha\AppData\Local\Programs\Python\Python311\python.exe`)
   - Add arguments: `scripts\reset_monthly_quotas.py`
   - Start in: `C:\Users\visha\OneDrive\Desktop\tickzen2\tickzen2`
   - Click "OK"

5. **Configure Settings**
   - Go to the "Settings" tab
   - Check "Allow task to be run on demand"
   - Check "Run task as soon as possible after a scheduled start is missed"
   - If the task fails, restart every: 5 minutes
   - Attempt to restart up to: 3 times
   - Click "OK"

6. **Test the Task**
   - Right-click on the task and select "Run"
   - Check the "Last Run Result" column (should be 0x0 for success)

### Option 2: Using Command Prompt (Administrator)

Open **Command Prompt as Administrator** and run:

```batch
schtasks /Create /TN "TickZen-MonthlyQuotaReset" /TR "python C:\Users\visha\OneDrive\Desktop\tickzen2\tickzen2\scripts\reset_monthly_quotas.py" /SC MONTHLY /D 1 /ST 00:01 /RL HIGHEST /F
```

### Option 3: Using PowerShell (Administrator)

Open **PowerShell as Administrator** and run:

```powershell
$Action = New-ScheduledTaskAction -Execute "python" -Argument "C:\Users\visha\OneDrive\Desktop\tickzen2\tickzen2\scripts\reset_monthly_quotas.py" -WorkingDirectory "C:\Users\visha\OneDrive\Desktop\tickzen2\tickzen2"
$Trigger = New-ScheduledTaskTrigger -Daily -At "12:01AM"
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -WakeToRun -StartWhenAvailable
Register-ScheduledTask -TaskName "TickZen-MonthlyQuotaReset" -Action $Action -Trigger $Trigger -Settings $Settings -RunLevel Highest -Description "Resets TickZen user quotas on the 1st of every month"
```

Then modify the trigger to monthly:
```powershell
$Task = Get-ScheduledTask -TaskName "TickZen-MonthlyQuotaReset"
$Task.Triggers[0].Repetition.Interval = "P1M"  # Monthly
Set-ScheduledTask -InputObject $Task
```

## Manual Quota Reset

If you need to reset quotas manually (without waiting for the scheduled task):

```bash
python scripts/reset_monthly_quotas.py
```

## Verify Task Setup

Check if the task is created:
```powershell
Get-ScheduledTask -TaskName "TickZen-MonthlyQuotaReset"
```

Run the task manually:
```powershell
Start-ScheduledTask -TaskName "TickZen-MonthlyQuotaReset"
```

Check task history:
```powershell
Get-ScheduledTask -TaskName "TickZen-MonthlyQuotaReset" | Get-ScheduledTaskInfo
```

## Linux/macOS Cron Setup

For production deployment on Linux/macOS, add this to crontab:

```cron
# Run quota reset on 1st of every month at 12:01 AM
1 0 1 * * cd /path/to/tickzen2 && python scripts/reset_monthly_quotas.py >> logs/quota_reset.log 2>&1
```

Edit crontab:
```bash
crontab -e
```

## Azure/Cloud Scheduler

For cloud deployment, consider using:
- **Azure Functions** with a timer trigger (cron: `0 1 0 1 * *`)
- **Google Cloud Scheduler** with Cloud Functions
- **AWS EventBridge** with Lambda

Example Azure Function timer trigger:
```json
{
  "schedule": "0 1 0 1 * *",
  "runOnStartup": false,
  "useMonitor": true
}
```

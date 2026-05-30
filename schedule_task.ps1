# schedule_task.ps1
# Run this ONCE to register the Trading Agent as a daily Windows scheduled task.
# Usage:  Right-click → Run with PowerShell
#         Or in PowerShell:  .\schedule_task.ps1
#         Or with custom time: .\schedule_task.ps1 -Hour 9 -Minute 0

param(
    [int]$Hour   = 9,     # Hour to run (24h format, local time). Default: 9 AM
    [int]$Minute = 0      # Minute to run. Default: :00
)

$TaskName   = "Trading Agent Daily"
$ScriptPath = Join-Path $PSScriptRoot "start_auto.bat"
$WorkingDir = $PSScriptRoot

Write-Host ""
Write-Host "  Setting up Trading Agent daily task..." -ForegroundColor Cyan
Write-Host "  Script : $ScriptPath"
Write-Host "  Time   : $Hour`:$('{0:D2}' -f $Minute) (local time, Mon-Fri)"
Write-Host ""

# Remove existing task if it exists
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue

# Create action
$action = New-ScheduledTaskAction `
    -Execute   "cmd.exe" `
    -Argument  "/c `"$ScriptPath`"" `
    -WorkingDirectory $WorkingDir

# Create trigger: weekdays at specified time
$trigger = New-ScheduledTaskTrigger `
    -Weekly `
    -DaysOfWeek Monday, Tuesday, Wednesday, Thursday, Friday `
    -At "$Hour`:$('{0:D2}' -f $Minute)"

# Settings: allow running when on battery, don't stop if on battery
$settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit  (New-TimeSpan -Hours 2) `
    -StartWhenAvailable  `
    -DisallowStartIfOnBatteries $false `
    -StopIfGoingOnBatteries     $false

# Register the task (runs as current logged-in user so it can open GUI windows)
Register-ScheduledTask `
    -TaskName $TaskName `
    -Action   $action `
    -Trigger  $trigger `
    -Settings $settings `
    -RunLevel Highest `
    -Force | Out-Null

Write-Host "  Task registered successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "  The Trading Agent will start automatically at $Hour`:$('{0:D2}' -f $Minute) every weekday." -ForegroundColor White
Write-Host "  You'll receive an email at trader.mo143@gmail.com with the URL." -ForegroundColor White
Write-Host ""
Write-Host "  To change the time, run:" -ForegroundColor Gray
Write-Host "    .\schedule_task.ps1 -Hour 8 -Minute 30    # for 8:30 AM" -ForegroundColor Gray
Write-Host ""
Write-Host "  To remove the task, run:" -ForegroundColor Gray
Write-Host "    Unregister-ScheduledTask -TaskName '$TaskName' -Confirm:`$false" -ForegroundColor Gray
Write-Host ""

# Test: show the registered task
Get-ScheduledTask -TaskName $TaskName | Select-Object TaskName, State |
    Format-Table -AutoSize

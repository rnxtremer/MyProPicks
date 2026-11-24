# Registers a Windows scheduled task that runs the MyProPicks review at 08:00 on the 1st of every month.
# If the PC is off at that time, it runs as soon as possible after the next start-up.
# Run once from PowerShell:  powershell -ExecutionPolicy Bypass -File scripts\install_monthly_task.ps1

$ErrorActionPreference = "Stop"
$project = Split-Path -Parent $PSScriptRoot
$python  = Join-Path $project ".venv\Scripts\python.exe"
$log     = Join-Path $project "data\reviews\run.log"
New-Item -ItemType Directory -Force (Split-Path $log) | Out-Null

$runner = Join-Path $project "scripts\run_review.ps1"
@"
`$ErrorActionPreference = 'Continue'
Set-Location '$project'
"=== `$(Get-Date -Format s) ===" | Out-File -Append -Encoding utf8 '$log'
& '$python' -m mypropicks review *>> '$log'
`$ok = (`$LASTEXITCODE -eq 0)
try {
    [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
    `$xml = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
    `$t = `$xml.GetElementsByTagName('text')
    `$t.Item(0).AppendChild(`$xml.CreateTextNode('MyProPicks')) | Out-Null
    `$msg = if (`$ok) { 'Monthly review is ready. Open the dashboard to see what to buy and sell.' } else { 'Monthly review failed. See data\reviews\run.log.' }
    `$t.Item(1).AppendChild(`$xml.CreateTextNode(`$msg)) | Out-Null
    [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('MyProPicks').Show([Windows.UI.Notifications.ToastNotification]::new(`$xml))
} catch { }
"@ | Set-Content -Encoding utf8 $runner

$action   = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$runner`"" -WorkingDirectory $project
# Monthly triggers aren't exposed by New-ScheduledTaskTrigger, so build one through CIM.
$class    = Get-CimClass -Namespace Root/Microsoft/Windows/TaskScheduler -ClassName MSFT_TaskMonthlyTrigger
$monthly  = New-CimInstance -CimClass $class -ClientOnly
$monthly.DaysOfMonth  = 1
$monthly.MonthsOfYear = 4095   # all 12 months
$monthly.StartBoundary = (Get-Date -Day 1 -Hour 8 -Minute 0 -Second 0).ToString("s")
$monthly.Enabled = $true
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 2)

Register-ScheduledTask -TaskName "MyProPicks Monthly Review" -Action $action -Trigger $monthly -Settings $settings -Description "Runs the MyProPicks monthly stock review." -Force | Out-Null
Write-Host "Scheduled: 'MyProPicks Monthly Review' runs at 08:00 on the 1st of every month."
Write-Host "Log file: $log"

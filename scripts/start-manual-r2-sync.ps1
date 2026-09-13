<#
Purpose: Start the existing combined Expenses and Cockpit R2 backup on demand.
The scheduled task owns concurrency, credentials and logs; its daily schedule stays unchanged.
#>
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Windows.Forms
try {
    $task = Get-ScheduledTask -TaskName 'ACM-Bookkeeping-Expense-R2-Sync'
    if ($task.State -eq 'Running') {
        [Windows.Forms.MessageBox]::Show('R2 backup is already running. Refresh Scene library when it finishes.', 'ACM R2 backup') | Out-Null
    } else {
        Start-ScheduledTask -TaskName $task.TaskName
        [Windows.Forms.MessageBox]::Show('Expenses and Cockpit3D-Files backup started. Large files can take several minutes. Refresh the Workshop Scene library afterwards. Logs are in ACM-Pipeline/deployment/artifacts/r2-sync-logs.', 'ACM R2 backup') | Out-Null
    }
} catch {
    [Windows.Forms.MessageBox]::Show('Could not start R2 backup: ' + $_.Exception.Message, 'ACM R2 backup') | Out-Null
    exit 1
}

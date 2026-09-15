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
        [Windows.Forms.MessageBox]::Show('Expenses, Cockpit3D-Files and Income sync started. New ACM invoices are saved to bookkeeping R2 and downloaded to local Income. Bank PDFs in Income sales-day settlement folders are uploaded too. Large files can take several minutes. Logs are in ACM-Web-Workshop/deployment/artifacts/r2-sync-logs.', 'ACM R2 backup') | Out-Null
    }
} catch {
    [Windows.Forms.MessageBox]::Show('Could not start R2 backup: ' + $_.Exception.Message, 'ACM R2 backup') | Out-Null
    exit 1
}

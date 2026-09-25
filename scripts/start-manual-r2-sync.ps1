<#
Purpose: Start the existing combined Expenses and Cockpit R2 backup on demand.
The scheduled task owns concurrency, credentials and logs; its daily schedule stays unchanged.
#>
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Windows.Forms
try {
    $task = Get-ScheduledTask -TaskName 'ACM-Bookkeeping-Expense-R2-Sync'
    if ($task.State -eq 'Running') {
        [Windows.Forms.MessageBox]::Show('R2 backup is already running. Refresh Scene library when it finishes.', 'CCM R2 backup') | Out-Null
    } else {
        Start-ScheduledTask -TaskName $task.TaskName
        [Windows.Forms.MessageBox]::Show('Expenses, Cockpit3D-Files, Claude Design and Income sync started. New CCM invoices are saved to bookkeeping R2 and downloaded to local Income. Bank PDFs in Income sales-day settlement folders are uploaded too. The Claude Design tree is mirrored to the acm-workshop bucket, which is what the Animations page on workshop.ccm.is plays from. Large files can take several minutes. Logs are in CCM-Web-Workshop/deployment/artifacts/r2-sync-logs.', 'CCM R2 backup') | Out-Null
    }
} catch {
    [Windows.Forms.MessageBox]::Show('Could not start R2 backup: ' + $_.Exception.Message, 'CCM R2 backup') | Out-Null
    exit 1
}

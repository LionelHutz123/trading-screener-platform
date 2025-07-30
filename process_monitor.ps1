# Process Monitor for Trading Screener
# Detects hung processes and provides monitoring capabilities

param(
    [string]$ConfigFile = "monitor_config.json",
    [int]$CheckInterval = 30,
    [int]$HungThreshold = 300,
    [int]$CpuThreshold = 90,
    [int]$MemoryThreshold = 85
)

# Configuration
$Config = @{
    CheckInterval = $CheckInterval
    HungThreshold = $HungThreshold
    CpuThreshold = $CpuThreshold
    MemoryThreshold = $MemoryThreshold
    ProcessesToMonitor = @("python", "docker", "trading-screener", "grafana", "main")
    SshServer = "root@159.203.131.140"
    SshPassphrase = "mcoveney@gmail.com"
}

# Process history to track changes
$ProcessHistory = @{}

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logMessage = "$timestamp - $Level - $Message"
    Write-Host $logMessage
    Add-Content -Path "process_monitor.log" -Value $logMessage
}

function Get-ProcessInfo {
    param([int]$ProcessId)
    
    try {
        $process = Get-Process -Id $ProcessId -ErrorAction Stop
        $cpu = $process.CPU
        $memory = $process.WorkingSet64
        
        return @{
            PID = $ProcessId
            Name = $process.ProcessName
            CPU = $cpu
            Memory = $memory
            Status = $process.Responding
            StartTime = $process.StartTime
            Threads = $process.Threads.Count
            Handles = $process.HandleCount
        }
    }
    catch {
        return $null
    }
}

function Test-HungProcess {
    param([hashtable]$ProcessInfo)
    
    $hungIndicators = @()
    $currentTime = Get-Date
    
    # Check if this is a process we want to monitor
    $shouldMonitor = $false
    foreach ($monitorName in $Config.ProcessesToMonitor) {
        if ($ProcessInfo.Name -like "*$monitorName*") {
            $shouldMonitor = $true
            break
        }
    }
    
    if (-not $shouldMonitor) {
        return $null
    }
    
    # Check for hung indicators
    if ($ProcessInfo.CPU -gt $Config.CpuThreshold) {
        $hungIndicators += "High CPU: $($ProcessInfo.CPU)%"
    }
    
    if ($ProcessInfo.Memory -gt $Config.MemoryThreshold) {
        $hungIndicators += "High Memory: $($ProcessInfo.Memory)MB"
    }
    
    # Check if process is not responding
    if (-not $ProcessInfo.Status) {
        $hungIndicators += "Not responding"
    }
    
    # Check if process has been stuck
    if ($ProcessHistory.ContainsKey($ProcessInfo.PID)) {
        $lastCheck = $ProcessHistory[$ProcessInfo.PID]
        $timeDiff = ($currentTime - $lastCheck.Timestamp).TotalSeconds
        
        if ($timeDiff -gt $Config.HungThreshold) {
            # Check if process hasn't changed significantly
            if ([Math]::Abs($ProcessInfo.CPU - $lastCheck.CPU) -lt 1) {
                $hungIndicators += "Stuck for $([Math]::Round($timeDiff))s"
            }
        }
    }
    
    # Update process history
    $ProcessHistory[$ProcessInfo.PID] = @{
        Timestamp = $currentTime
        CPU = $ProcessInfo.CPU
        Memory = $ProcessInfo.Memory
    }
    
    if ($hungIndicators.Count -gt 0) {
        return @{
            PID = $ProcessInfo.PID
            Name = $ProcessInfo.Name
            Indicators = $hungIndicators
            CPU = $ProcessInfo.CPU
            Memory = $ProcessInfo.Memory
            Status = $ProcessInfo.Status
            DetectedAt = $currentTime.ToString("yyyy-MM-dd HH:mm:ss")
        }
    }
    
    return $null
}

function Test-RemoteProcesses {
    $remoteHung = @()
    
    try {
        # Check Docker containers on remote server
        $sshCmd = "ssh $($Config.SshServer) 'docker ps --format \"table {{.Names}}\t{{.Status}}\t{{.Ports}}\"'"
        $result = Invoke-Expression $sshCmd 2>$null
        
        if ($LASTEXITCODE -eq 0) {
            $lines = $result -split "`n" | Select-Object -Skip 1
            foreach ($line in $lines) {
                if ($line.Trim()) {
                    $parts = $line -split "`t"
                    if ($parts.Count -ge 2) {
                        $containerName = $parts[0]
                        $status = $parts[1]
                        
                        # Check for hung indicators in container status
                        if ($status -match "restarting|exited|dead") {
                            $remoteHung += @{
                                Type = "docker_container"
                                Name = $containerName
                                Status = $status
                                DetectedAt = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
                            }
                        }
                    }
                }
            }
        }
        
        # Check system processes on remote server
        $sshCmd = "ssh $($Config.SshServer) 'ps aux | grep -E \"(python|docker|trading)\" | grep -v grep'"
        $result = Invoke-Expression $sshCmd 2>$null
        
        if ($LASTEXITCODE -eq 0) {
            $lines = $result -split "`n"
            foreach ($line in $lines) {
                if ($line.Trim()) {
                    $parts = $line -split '\s+'
                    if ($parts.Count -ge 3) {
                        $cpuPercent = [double]$parts[2]
                        if ($cpuPercent -gt $Config.CpuThreshold) {
                            $remoteHung += @{
                                Type = "system_process"
                                PID = $parts[1]
                                CpuPercent = $cpuPercent
                                Command = ($parts[10..($parts.Count-1)] -join " ")
                                DetectedAt = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
                            }
                        }
                    }
                }
            }
        }
    }
    catch {
        Write-Log "Error checking remote processes: $($_.Exception.Message)" "ERROR"
    }
    
    return $remoteHung
}

function Get-SystemInfo {
    $cpu = (Get-Counter "\Processor(_Total)\% Processor Time").CounterSamples[0].CookedValue
    $memory = (Get-Counter "\Memory\% Committed Bytes In Use").CounterSamples[0].CookedValue
    $disk = (Get-Counter "\LogicalDisk(_Total)\% Free Space").CounterSamples[0].CookedValue
    
    return @{
        CpuPercent = [Math]::Round($cpu, 1)
        MemoryPercent = [Math]::Round($memory, 1)
        DiskFreePercent = [Math]::Round($disk, 1)
    }
}

function Generate-Report {
    $localHung = @()
    $remoteHung = @()
    
    # Check local processes
    $processes = Get-Process | Where-Object { $_.ProcessName -ne "Idle" }
    foreach ($proc in $processes) {
        $procInfo = Get-ProcessInfo -ProcessId $proc.Id
        if ($procInfo) {
            $hungProcess = Test-HungProcess -ProcessInfo $procInfo
            if ($hungProcess) {
                $localHung += $hungProcess
            }
        }
    }
    
    # Check remote processes
    $remoteHung = Test-RemoteProcesses
    
    # Get system info
    $sysInfo = Get-SystemInfo
    
    $report = @{
        Timestamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
        LocalHungProcesses = $localHung
        RemoteHungProcesses = $remoteHung
        TotalHungProcesses = $localHung.Count + $remoteHung.Count
        SystemInfo = $sysInfo
    }
    
    return $report
}

function Write-Report {
    param([hashtable]$Report)
    
    if ($Report.TotalHungProcesses -gt 0) {
        Write-Log "Found $($Report.TotalHungProcesses) hung processes!" "WARNING"
        
        foreach ($proc in $Report.LocalHungProcesses) {
            Write-Log "Local hung process: $($proc.Name) (PID: $($proc.PID)) - $($proc.Indicators -join ', ')" "WARNING"
        }
        
        foreach ($proc in $Report.RemoteHungProcesses) {
            Write-Log "Remote hung process: $($proc)" "WARNING"
        }
    }
    else {
        Write-Log "No hung processes detected" "INFO"
    }
    
    # Log system info
    $sysInfo = $Report.SystemInfo
    Write-Log "System: CPU $($sysInfo.CpuPercent)%, Memory $($sysInfo.MemoryPercent)%, Disk Free $($sysInfo.DiskFreePercent)%" "INFO"
}

function Start-MonitoringLoop {
    Write-Log "Starting process monitor..."
    
    try {
        while ($true) {
            $report = Generate-Report
            Write-Report -Report $report
            
            # Save report to file
            $report | ConvertTo-Json -Depth 10 | Out-File -FilePath "process_monitor_report.json" -Encoding UTF8
            
            Start-Sleep -Seconds $Config.CheckInterval
        }
    }
    catch {
        Write-Log "Error in monitoring loop: $($_.Exception.Message)" "ERROR"
    }
}

# Main execution
if ($args[0] -eq "--report") {
    # Generate one-time report
    $report = Generate-Report
    $report | ConvertTo-Json -Depth 10
}
else {
    # Run continuous monitoring
    Start-MonitoringLoop
} 
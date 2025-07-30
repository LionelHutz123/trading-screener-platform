# Quick Hang Detector for Trading Screener
# Simple script to detect hung processes

Write-Host "🔍 QUICK HANG DETECTOR" -ForegroundColor Green
Write-Host "=====================" -ForegroundColor Green
Write-Host ""

$hungProcesses = @()
$problematicContainers = @()

# Check for hung Python processes
Write-Host "📊 Checking Python processes..." -ForegroundColor Yellow
$pythonProcesses = Get-Process python -ErrorAction SilentlyContinue
foreach ($proc in $pythonProcesses) {
    $cpu = $proc.CPU
    $memory = $proc.WorkingSet64 / 1MB
    
    if ($cpu -gt 90 -or $memory -gt 1000 -or -not $proc.Responding) {
        $hungProcesses += @{
            Name = "python"
            PID = $proc.Id
            CPU = $cpu
            Memory = [Math]::Round($memory, 1)
            Responding = $proc.Responding
        }
    }
}

# Check for hung Docker processes
Write-Host "🐳 Checking Docker processes..." -ForegroundColor Yellow
$dockerProcesses = Get-Process docker* -ErrorAction SilentlyContinue
foreach ($proc in $dockerProcesses) {
    $cpu = $proc.CPU
    $memory = $proc.WorkingSet64 / 1MB
    
    if ($cpu -gt 90 -or $memory -gt 2000 -or -not $proc.Responding) {
        $hungProcesses += @{
            Name = $proc.ProcessName
            PID = $proc.Id
            CPU = $cpu
            Memory = [Math]::Round($memory, 1)
            Responding = $proc.Responding
        }
    }
}

# Check Docker containers
Write-Host "📦 Checking Docker containers..." -ForegroundColor Yellow
try {
    $containers = docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" 2>$null
    if ($LASTEXITCODE -eq 0) {
        $lines = $containers -split "`n" | Select-Object -Skip 1
        foreach ($line in $lines) {
            if ($line.Trim()) {
                $parts = $line -split "`t"
                if ($parts.Count -ge 2) {
                    $containerName = $parts[0]
                    $status = $parts[1]
                    
                    if ($status -match "restarting|exited|dead|unhealthy") {
                        $problematicContainers += @{
                            Name = $containerName
                            Status = $status
                        }
                    }
                }
            }
        }
    }
} catch {
    Write-Host "❌ Docker not available or not running" -ForegroundColor Red
}

# Display results
Write-Host "`n📋 RESULTS:" -ForegroundColor Cyan
Write-Host "===========" -ForegroundColor Cyan

if ($hungProcesses.Count -gt 0) {
    Write-Host "❌ Found hung processes:" -ForegroundColor Red
    foreach ($proc in $hungProcesses) {
        Write-Host "  - $($proc.Name) (PID: $($proc.PID))" -ForegroundColor White
        Write-Host "    CPU: $($proc.CPU)%, Memory: $($proc.Memory)MB, Responding: $($proc.Responding)" -ForegroundColor Gray
    }
} else {
    Write-Host "✅ No hung processes detected" -ForegroundColor Green
}

if ($problematicContainers.Count -gt 0) {
    Write-Host "`n❌ Found problematic containers:" -ForegroundColor Red
    foreach ($container in $problematicContainers) {
        Write-Host "  - $($container.Name): $($container.Status)" -ForegroundColor White
    }
} else {
    Write-Host "`n✅ No problematic containers detected" -ForegroundColor Green
}

# System info
Write-Host "`n💻 System Information:" -ForegroundColor Cyan
$cpu = (Get-Counter "\Processor(_Total)\% Processor Time").CounterSamples[0].CookedValue
$memory = (Get-Counter "\Memory\% Committed Bytes In Use").CounterSamples[0].CookedValue
Write-Host "  CPU: $([Math]::Round($cpu, 1))%" -ForegroundColor White
Write-Host "  Memory: $([Math]::Round($memory, 1))%" -ForegroundColor White

# Recommendations
$totalIssues = $hungProcesses.Count + $problematicContainers.Count
if ($totalIssues -gt 0) {
    Write-Host "`n🔧 RECOMMENDED ACTIONS:" -ForegroundColor Yellow
    if ($hungProcesses.Count -gt 0) {
        Write-Host "1. Kill hung processes:" -ForegroundColor White
        foreach ($proc in $hungProcesses) {
            Write-Host "   Stop-Process -Id $($proc.PID) -Force" -ForegroundColor Gray
        }
    }
    
    if ($problematicContainers.Count -gt 0) {
        Write-Host "`n2. Restart problematic containers:" -ForegroundColor White
        foreach ($container in $problematicContainers) {
            Write-Host "   docker restart $($container.Name)" -ForegroundColor Gray
        }
    }
    
    Write-Host "`n3. Check remote server:" -ForegroundColor White
    Write-Host "   ssh root@159.203.131.140" -ForegroundColor Gray
    Write-Host "   docker-compose restart" -ForegroundColor Gray
} else {
    Write-Host "`n✅ All systems appear to be running normally!" -ForegroundColor Green
}

Write-Host "Scan completed at: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Gray 
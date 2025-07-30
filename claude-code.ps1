# Claude Code CLI Wrapper
# This script runs the Claude Code CLI tool

param(
    [Parameter(ValueFromRemainingArguments=$true)]
    [string[]]$Arguments
)

$cliPath = "C:\Users\python\AppData\Roaming\npm\node_modules\@anthropic-ai\claude-code\cli.js"

if (Test-Path $cliPath) {
    node $cliPath @Arguments
} else {
    Write-Host "❌ Claude Code CLI not found at: $cliPath" -ForegroundColor Red
    Write-Host "Try running: npm install -g @anthropic-ai/claude-code" -ForegroundColor Yellow
} 
param(
    [Parameter(Mandatory = $true)][string]$SnapshotPath,
    [string]$StatePath = "$PSScriptRoot\..\.local\usage-state.json"
)
# Snapshot must come from the authenticated Codex get_usage_limits tool.
# Never scrape tokens, browser profiles or another app's private storage.
$ErrorActionPreference = 'Stop'
$snapshotFile = (Resolve-Path -LiteralPath $SnapshotPath).Path
Get-Content -LiteralPath $snapshotFile -Raw | python "$PSScriptRoot\usage_guard.py" --state $StatePath
exit $LASTEXITCODE

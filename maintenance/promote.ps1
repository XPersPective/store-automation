param(
    [Parameter(Mandatory=$true)][string]$Repository,
    [Parameter(Mandatory=$true)][string]$Backup,
    [switch]$Apply
)
$ErrorActionPreference = 'Stop'
$repoPath = (Resolve-Path -LiteralPath $Repository).Path
$candidatePath = Join-Path $repoPath 'store-automation-next'
$backupPath = [IO.Path]::GetFullPath($Backup)
if (-not (Test-Path -LiteralPath (Join-Path $repoPath '.git')) -or
    -not (Test-Path -LiteralPath (Join-Path $candidatePath 'store.py')) -or
    -not (Test-Path -LiteralPath (Join-Path $candidatePath 'SKILL.md'))) { throw 'Expected repository/candidate missing' }
if ($backupPath.StartsWith($repoPath + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase) -or
    $backupPath -eq $repoPath -or (Test-Path -LiteralPath $backupPath)) { throw 'Backup must be a new location outside repository' }
foreach ($path in @($repoPath, $candidatePath, (Split-Path -Parent $backupPath))) {
    $entry = Get-Item -LiteralPath $path -Force
    while ($null -ne $entry) {
        if ($entry.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw "Linked path refused: $($entry.FullName)" }
        $entry = $entry.Parent
    }
}
$old = @(Get-ChildItem -LiteralPath $repoPath -Force | Where-Object { $_.Name -notin @('.git', 'store-automation-next') })
$new = @(Get-ChildItem -LiteralPath $candidatePath -Force)
foreach ($entry in @($old) + @($new)) {
    $expectedParent = if ($entry.FullName.StartsWith($candidatePath + '\', [StringComparison]::OrdinalIgnoreCase)) { $candidatePath } else { $repoPath }
    if ($entry.DirectoryName -and -not $entry.PSIsContainer) { $actualParent = $entry.DirectoryName } else { $actualParent = $entry.Parent.FullName }
    if ($actualParent -ne $expectedParent -or ($entry.Attributes -band [IO.FileAttributes]::ReparsePoint) -or $entry.Name -eq '.git') { throw 'Unexpected or linked top-level entry' }
}
$state = [ordered]@{ repository=$repoPath; candidate=$candidatePath; backup=$backupPath; phase='PREPARED'; old=@($old.Name); new=@($new.Name); archived=@(); promoted=@() }
if (-not $Apply) { $state | ConvertTo-Json -Depth 5; exit 0 }
New-Item -ItemType Directory -Path $backupPath | Out-Null
$archivePath = Join-Path $backupPath 'repository'
New-Item -ItemType Directory -Path $archivePath | Out-Null
$journal = Join-Path $backupPath 'migration.json'
function Save-State { $state | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $journal -Encoding utf8 }
Save-State
foreach ($entry in $old) {
    Move-Item -LiteralPath $entry.FullName -Destination (Join-Path $archivePath $entry.Name)
    $state.archived += $entry.Name
    Save-State
}
$state.phase = 'ARCHIVED'; Save-State
foreach ($entry in $new) {
    Move-Item -LiteralPath $entry.FullName -Destination (Join-Path $repoPath $entry.Name)
    $state.promoted += $entry.Name
    Save-State
}
# Only remove the verified empty, exact candidate directory; never recursively delete.
if (@(Get-ChildItem -LiteralPath $candidatePath -Force).Count -ne 0) { throw 'Candidate not empty; preserve it' }
Remove-Item -LiteralPath $candidatePath
$state.phase = 'PROMOTED'; Save-State
$state | ConvertTo-Json -Depth 5

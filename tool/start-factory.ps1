$ErrorActionPreference = 'Stop'
$factoryRoot = Split-Path -Parent $PSScriptRoot
$factoryRuntime = Join-Path $env:USERPROFILE '.local\share\ai-app-factory\runtime-1.18.0\node_modules\opencode-ai\bin\opencode.exe'
if (-not (Test-Path -LiteralPath $factoryRuntime)) {
    throw 'Factory runtime missing; install opencode-ai@1.18.0 using README.md.'
}
Set-Location -LiteralPath $factoryRoot
$factoryEnvironment = @{}
try {
    Get-ChildItem Env: | Where-Object { $_.Name -match '^(OPENCODE_CONFIG|OPENCODE_MODEL|OPENAI|ANTHROPIC|AZURE|GEMINI|GOOGLE_API_KEY)' } | ForEach-Object {
        $factoryEnvironment[$_.Name] = $_.Value
        Remove-Item -LiteralPath ("Env:" + $_.Name)
    }
    & $factoryRuntime --pure --agent factory $factoryRoot @args
    $factoryExitCode = $LASTEXITCODE
} finally {
    foreach ($factoryName in $factoryEnvironment.Keys) {
        Set-Item -LiteralPath ("Env:" + $factoryName) -Value $factoryEnvironment[$factoryName]
    }
}
exit $factoryExitCode

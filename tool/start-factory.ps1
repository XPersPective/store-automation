$ErrorActionPreference = 'Stop'
# Launch in the caller's selected project; never switch to the tool repository.
& python (Join-Path $PSScriptRoot 'factory.py') open
exit $LASTEXITCODE

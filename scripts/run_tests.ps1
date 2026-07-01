$venvPython = Join-Path $PSScriptRoot "..\.venv\Scripts\python.exe"
$runnerPath = Join-Path $PSScriptRoot "run_tests.py"

if (Test-Path $venvPython) {
    & $venvPython $runnerPath @args
    exit $LASTEXITCODE
}

& python $runnerPath @args
exit $LASTEXITCODE

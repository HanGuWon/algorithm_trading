param(
    [string]$VenvPath = ".venv-freqtrade",
    [string]$FreqtradeVersion = "2026.2"
)

$ErrorActionPreference = "Stop"

if (-not (Get-Command python -ErrorAction SilentlyContinue) -and -not (Get-Command py -ErrorAction SilentlyContinue)) {
    throw "Python is required to bootstrap the local Freqtrade environment."
}

if (-not (Test-Path $VenvPath)) {
    if (Get-Command python -ErrorAction SilentlyContinue) {
        python -m venv $VenvPath
    }
    else {
        py -m venv $VenvPath
    }
}

$pythonExe = Join-Path $VenvPath "Scripts\\python.exe"
if (-not (Test-Path $pythonExe)) {
    throw "Expected python executable was not found at $pythonExe"
}

& $pythonExe -m pip install --upgrade pip setuptools wheel
& $pythonExe -m pip install "freqtrade==$FreqtradeVersion"
& $pythonExe -m pip install filelock optuna

if ($IsWindows) {
    & $pythonExe -m pip uninstall -y aiodns pycares | Out-Null
}

& $pythonExe -m freqtrade --version

[CmdletBinding()]
param(
  [Parameter(ValueFromRemainingArguments = $true)]
  [string[]]$ComposeArgs
)

$ErrorActionPreference = 'Stop'
# Set-StrictMode -Version Latest
Set-Location -LiteralPath $PSScriptRoot

function Test-Command {
  param([string]$Name)
  return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

function Ensure-PodmanSocket {
  param([string]$SocketPath)

  if (Test-Path -LiteralPath $SocketPath) {
    return $true
  }

  if ($IsLinux -and (Test-Command 'systemctl')) {
    & systemctl --user start podman.socket | Out-Null
    for ($i = 0; $i -lt 5; $i++) {
      if (Test-Path -LiteralPath $SocketPath) {
        return $true
      }
      Start-Sleep -Seconds 1
    }
  }

  return (Test-Path -LiteralPath $SocketPath)
}

$Action = 'up'
$RemainingArgs = @($ComposeArgs)
if (@($ComposeArgs).Count -gt 0 -and $ComposeArgs[0] -in @('up', 'down')) {
  $Action = $ComposeArgs[0]
  if (@($ComposeArgs).Count -gt 1) {
    $RemainingArgs = @($ComposeArgs[1..(@($ComposeArgs).Count - 1)])
  } else {
    $RemainingArgs = @()
  }
}

$ComposeFileArgs = @('-f', 'docker-compose.yml')
if ($IsLinux -and (Test-Path -LiteralPath (Join-Path $PSScriptRoot 'docker-compose.linux.yml'))) {
  $ComposeFileArgs += @('-f', 'docker-compose.linux.yml')
}

if (Test-Command 'docker') {
  if (-not $env:HOST_SOCKET_PATH) {
    $env:HOST_SOCKET_PATH = '/var/run/docker.sock'
  }

  if ($Action -eq 'up') {
    & docker compose @ComposeFileArgs up --build @RemainingArgs
  } else {
    & docker compose @ComposeFileArgs down @RemainingArgs
  }
  exit $LASTEXITCODE
}

if (Test-Command 'podman') {
  if (-not $env:HOST_SOCKET_PATH) {
    try {
      $socketPath = (& podman info --format '{{.Host.RemoteSocket.Path}}' 2>$null | Select-Object -First 1).Trim()
      if ($socketPath) {
        $env:HOST_SOCKET_PATH = $socketPath
      }
    } catch {
      $null = $null
    }
  }

  if (-not $env:HOST_SOCKET_PATH) {
    throw 'Set HOST_SOCKET_PATH to your Podman socket path before running this script.'
  }

  if (-not (Ensure-PodmanSocket -SocketPath $env:HOST_SOCKET_PATH)) {
    throw "Podman socket unavailable at $($env:HOST_SOCKET_PATH). Start it or set HOST_SOCKET_PATH to a valid socket."
  }

  if (Test-Path -LiteralPath (Join-Path $PSScriptRoot 'docker-compose.podman.yml')) {
    $ComposeFileArgs += @('-f', 'docker-compose.podman.yml')
  }

  try {
    podman info | Out-Null
  } catch {
    throw 'Podman is installed, but the Podman service is not available.'
  }

  if (Test-Command 'podman-compose') {
    if ($Action -eq 'up') {
      & podman-compose @ComposeFileArgs up --build @RemainingArgs
    } else {
      & podman-compose @ComposeFileArgs down @RemainingArgs
    }
    exit $LASTEXITCODE
  }

  if ($Action -eq 'up') {
    & podman compose @ComposeFileArgs up --build @RemainingArgs
  } else {
    & podman compose @ComposeFileArgs down @RemainingArgs
  }
  exit $LASTEXITCODE
}

throw 'No Docker or Podman compose runtime found.'

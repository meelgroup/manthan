param(
  [switch]$Build,
  [switch]$Force,
  [string]$Repo
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$depsDir = Join-Path $root "dependencies"

function Get-RepoName {
  if ($Repo -and $Repo.Trim().Length -gt 0) { return $Repo }
  if ($env:MANTHAN_REPO -and $env:MANTHAN_REPO.Trim().Length -gt 0) { return $env:MANTHAN_REPO }

  $origin = (git -C $root config --get remote.origin.url 2>$null)
  if (-not $origin) { return "" }

  if ($origin -match "^git@github.com:([^/]+/[^.]+)(\.git)?$") { return $Matches[1] }
  if ($origin -match "^https://github.com/([^/]+/[^.]+)(\.git)?$") { return $Matches[1] }
  return ""
}

function Update-ItpPath {
  $cfgPath = Join-Path $root "manthan_dependencies.cfg"
  if (-not (Test-Path $cfgPath)) { return }

  $lines = Get-Content $cfgPath
  $out = @()
  $inSection = $false
  $updated = $false

  foreach ($line in $lines) {
    if ($line -match "^\s*\[ITP-Path\]\s*$") {
      $inSection = $true
      $out += $line
      continue
    }
    if ($line -match "^\s*\[.*\]\s*$") {
      if ($inSection -and -not $updated) {
        $out += "itp_path = dependencies/unique/build/interpolatingsolver/src"
        $updated = $true
      }
      $inSection = $false
      $out += $line
      continue
    }
    if ($inSection -and $line -match "^\s*itp_path\s*=") {
      $out += "itp_path = dependencies/unique/build/interpolatingsolver/src"
      $updated = $true
      continue
    }
    $out += $line
  }

  if (-not $inSection -and -not ($lines | Select-String -Quiet -Pattern "^\s*\[ITP-Path\]\s*$")) {
    $out += ""
    $out += "[ITP-Path]"
    $out += "itp_path = dependencies/unique/build/interpolatingsolver/src"
    $updated = $true
  } elseif ($inSection -and -not $updated) {
    $out += "itp_path = dependencies/unique/build/interpolatingsolver/src"
  }

  Set-Content -Path $cfgPath -Value $out
}

function Download-Release {
  param([string]$OsSlug)

  $repoName = Get-RepoName
  if (-not $repoName) {
    Write-Error "Unable to determine GitHub repo. Use -Repo owner/name or set MANTHAN_REPO."
  }

  $assetName = "manthan-deps-$OsSlug.tar.gz"
  $apiUrl = "https://api.github.com/repos/$repoName/releases/latest"

  $release = Invoke-RestMethod -Uri $apiUrl -Headers @{ "User-Agent" = "manthan-setup" }
  $asset = $release.assets | Where-Object { $_.name -eq $assetName } | Select-Object -First 1
  if (-not $asset) {
    Write-Error "No release asset named $assetName found in $repoName."
  }

  $tmp = New-TemporaryFile
  Write-Host "Downloading $assetName from $repoName..."
  Invoke-WebRequest -Uri $asset.browser_download_url -OutFile $tmp
  tar -xzf $tmp -C $root
  Remove-Item $tmp -Force
}

function Build-FromSource {
  & "$root/scripts/clone_dependencies.sh"
  & "$root/scripts/build_dependencies_windows.sh"
}

$osSlug = "windows"

if (-not $Build) {
  $staticBin = Join-Path $depsDir "static_bin"
  if ((Test-Path $staticBin) -and (-not $Force)) {
    Write-Host "dependencies/static_bin already exists; use -Force to re-download or -Build to rebuild."
  } else {
    try {
      Download-Release -OsSlug $osSlug
    } catch {
      Write-Warning "Download failed; falling back to build from source."
      $Build = $true
    }
  }
}

if ($Build) {
  Build-FromSource
}

Update-ItpPath
Write-Host "Setup complete."

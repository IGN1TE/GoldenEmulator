$ErrorActionPreference = 'Stop'
$installer = Join-Path $PWD 'installer-dist\GoldenEmulator-Setup-0.8.0.exe'
$installDir = Join-Path $env:RUNNER_TEMP 'Golden Emulator Install Test'
$env:LOCALAPPDATA = Join-Path $env:RUNNER_TEMP 'GoldenEmulator-Test-Profile'
$dataDir = Join-Path $env:LOCALAPPDATA 'GoldenEmulator'
New-Item -ItemType Directory -Path $dataDir -Force | Out-Null
$library = '{"version":2,"games":[{"id":"legacy","title":"Saved game","system":"PlayStation 2","path":"Games/test.iso","favorite":true,"notes":"Preserve this","cover":"data:image/png;base64,YQ=="}]}'
Set-Content (Join-Path $dataDir 'library.json') $library -Encoding utf8NoBOM
$config = '{"PlayStation 2":"C:\\Emulators\\pcsx2.exe"}'
Set-Content (Join-Path $dataDir 'emulators.json') $config -Encoding utf8NoBOM
function Run-Checked($file, $arguments) {
  $p = Start-Process -FilePath $file -ArgumentList $arguments -PassThru
  if (!$p.WaitForExit(60000)) { $p.Kill(); throw "Timed out: $file" }
  if ($p.ExitCode -ne 0) { throw "Nonzero exit: $file ($($p.ExitCode))" }
}
Run-Checked $installer @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART',"/DIR=`"$installDir`"")
$exe = Join-Path $installDir 'GoldenEmulator.exe'
if (!(Test-Path $exe)) { throw 'Installed EXE missing' }
$info = (Get-Item $exe).VersionInfo
if ($info.CompanyName -ne 'IGN1TE' -or $info.FileVersion -ne '0.8.0.0') { throw 'EXE branding metadata missing' }
Add-Type -AssemblyName System.Drawing
$icon = [System.Drawing.Icon]::ExtractAssociatedIcon($exe)
if (!$icon) { throw 'EXE icon missing' }
$icon.Dispose()
$report = Join-Path $env:RUNNER_TEMP 'installed-self-test.json'
Run-Checked $exe @('--self-test',"`"$report`"")
if (!(Get-Content $report | ConvertFrom-Json).ok) { throw 'Installed EXE failed self-test' }
function Start-Launcher {
  $p = Start-Process -FilePath $exe -ArgumentList '--no-browser' -PassThru
  $runtime = Join-Path $dataDir 'runtime.json'
  for ($i=0; $i -lt 200; $i++) {
    if (Test-Path $runtime) {
      try {
        $token = (Get-Content $runtime | ConvertFrom-Json).token
        $status = Invoke-RestMethod 'http://127.0.0.1:48761/api/status' -Headers @{'X-GoldenEmulator-Token'=$token}
        if ($status.desktopReady) { return $p }
      } catch { }
    }
    if ($p.HasExited) { throw 'Launcher exited before ready' }
    Start-Sleep -Milliseconds 200
  }
  $p.Kill(); throw 'Launcher did not become ready'
}
$p = Start-Launcher
# A second invocation must exit cleanly instead of presenting an already-running error.
Run-Checked $exe @('--no-browser')
Run-Checked $exe @('--stop')
if (!$p.WaitForExit(15000)) { $p.Kill(); throw 'Stop shortcut did not exit launcher' }
if (Test-Path (Join-Path $dataDir 'runtime.json')) { throw 'Runtime record not cleaned' }
# Verify the visible window's close button also stops the one-file child process.
$p = Start-Launcher
$closed = $false
for ($i=0; $i -lt 50; $i++) {
  $windows = Get-Process GoldenEmulator -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowTitle -like 'GoldenEmulator*' }
  foreach ($window in $windows) { if ($window.CloseMainWindow()) { $closed = $true } }
  if ($closed) { break }
  Start-Sleep -Milliseconds 200
}
if (!$closed) { $p.Kill(); throw 'Launcher control window was not found' }
if (!$p.WaitForExit(15000)) { $p.Kill(); throw 'Window close did not stop launcher' }
# Upgrade/reinstall and uninstall must preserve user data outside the install directory.
Run-Checked $installer @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART',"/DIR=`"$installDir`"")
if ((Get-Content (Join-Path $dataDir 'library.json') -Raw).Trim() -ne $library) { throw 'Reinstall changed library' }
# Exercise the automatic updater's install-and-reopen contract.
Run-Checked $installer @('/SILENT','/SP-','/NORESTART','/RESTARTAPP=1',"/DIR=`"$installDir`"")
$reopened = $false
for ($i=0; $i -lt 200; $i++) {
  try {
    $token = (Get-Content (Join-Path $dataDir 'runtime.json') -ErrorAction Stop | ConvertFrom-Json).token
    $status = Invoke-RestMethod 'http://127.0.0.1:48761/api/status' -Headers @{'X-GoldenEmulator-Token'=$token}
    if ($status.desktopReady) { $reopened = $true; break }
  } catch { }
  Start-Sleep -Milliseconds 200
}
if (!$reopened) { throw 'Update installer did not reopen the desktop app' }
Run-Checked $exe @('--stop')
for ($i=0; $i -lt 100 -and (Test-Path (Join-Path $dataDir 'runtime.json')); $i++) { Start-Sleep -Milliseconds 200 }

Run-Checked (Join-Path $installDir 'unins000.exe') @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART')
if (Test-Path $exe) { throw 'Uninstall left installed EXE' }
if ((Get-Content (Join-Path $dataDir 'library.json') -Raw).Trim() -ne $library) { throw 'Uninstall changed library' }
if ((Get-Content (Join-Path $dataDir 'emulators.json') -Raw).Trim() -ne $config) { throw 'Emulator configuration changed' }
Write-Output 'PASS: desktop UI rendered with ten console cards and Gamepad API; installation, installed runtime, second launch, stop command, window close, reinstall and uninstall; library preserved.'

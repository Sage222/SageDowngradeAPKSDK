# APK minSdkVersion Patcher
# Requirements: patch_manifest.py (same folder), uber-apk-signer.jar, Python 3, Java

param(
    [Parameter(Mandatory=$true)]
    [string]$ApkPath,
    [int]$MinSdk = 30,
    [string]$SignerJar = "$PSScriptRoot\uber-apk-signer.jar",
    [string]$JavaExe  = ""
)

$ErrorActionPreference = "Stop"

# Auto-detect Java
if ($JavaExe -eq "") {
    $candidates = @(
        "C:\Program Files\Android\Android Studio\jbr\bin\java.exe",
        "C:\Program Files\Android\Android Studio\jre\bin\java.exe",
        "C:\Program Files\Eclipse Adoptium\jdk-21\bin\java.exe",
        "C:\Program Files\Microsoft\jdk-21\bin\java.exe",
        "C:\Program Files\Java\jdk-21\bin\java.exe"
    )
    if ($env:JAVA_HOME) { $candidates = @("$env:JAVA_HOME\bin\java.exe") + $candidates }
    foreach ($c in $candidates) {
        if (Test-Path $c) { $JavaExe = $c; break }
    }
    if ($JavaExe -eq "") {
        $found = Get-ChildItem "C:\Program Files" -Recurse -Filter "java.exe" -ErrorAction SilentlyContinue |
                 Where-Object { $_.FullName -notmatch "javapath|java8path" } |
                 Select-Object -First 1
        if ($found) { $JavaExe = $found.FullName }
    }
    if ($JavaExe -eq "") { Write-Error "Could not find java.exe. Pass -JavaExe explicitly." }
}
Write-Host "[OK] Java: $JavaExe"

$pyScript = Join-Path $PSScriptRoot "patch_manifest.py"
if (-not (Test-Path $pyScript))  { Write-Error "patch_manifest.py not found next to the script at: $pyScript" }
if (-not (Test-Path $SignerJar)) { Write-Error "uber-apk-signer not found at: $SignerJar" }

$ApkPath    = (Resolve-Path $ApkPath).Path
$apkDir     = Split-Path $ApkPath
$apkBase    = [System.IO.Path]::GetFileNameWithoutExtension($ApkPath)
$patchedApk = Join-Path $apkDir ($apkBase + "_unsigned.apk")
$finalApk   = Join-Path $apkDir ($apkBase + "_patched.apk")

if (Test-Path $patchedApk) { Remove-Item $patchedApk -Force }
if (Test-Path $finalApk)   { Remove-Item $finalApk   -Force }

Write-Host ""
Write-Host ">>> Patching binary AndroidManifest.xml (minSdkVersion -> $MinSdk)"
python $pyScript $ApkPath $patchedApk $MinSdk
if ($LASTEXITCODE -ne 0) { Write-Error "Python manifest patch failed." }

Write-Host ""
Write-Host ">>> Signing patched APK"
& $JavaExe -jar $SignerJar --apks $patchedApk --out $apkDir --allowResign
if ($LASTEXITCODE -ne 0) { Write-Error "Signing failed." }

$signedApk = Join-Path $apkDir ($apkBase + "_unsigned-aligned-signed.apk")
if (Test-Path $signedApk) {
    Move-Item $signedApk $finalApk -Force
} else {
    $found = Get-ChildItem $apkDir -Filter "*unsigned*signed*.apk" | Select-Object -First 1
    if ($found) { Move-Item $found.FullName $finalApk -Force }
    else { Write-Warning "Could not locate signed APK in $apkDir" }
}

Remove-Item $patchedApk -Force -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "[DONE] $finalApk"
Write-Host "Install with:"
Write-Host "  adb install -r $finalApk"

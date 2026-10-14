<#
    CascadePic (流瀑看图) - 卸载 Windows Explorer 右键菜单集成

    用法：
      .\uninstall_context_menu.ps1
#>
[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

$VerbKey          = "CascadePic"
$FolderVerbKey    = "CascadePicFolder"
$AppKey           = "HKCU:\Software\Classes\Applications\CascadePic.exe"

$MediaExtensions = @(
    ".jpg", ".jpeg", ".jfif", ".png", ".bmp", ".gif", ".webp", ".tif", ".tiff", ".ico",
    ".mp4", ".mkv", ".webm", ".mov", ".avi", ".wmv", ".m4v"
)

function Remove-MenuVerb {
    param([Parameter(Mandatory = $true)][string]$BaseKey, [string]$KeyName = $VerbKey)

    $key = Join-Path $BaseKey $KeyName
    if (Test-Path -LiteralPath $key) {
        Remove-Item -LiteralPath $key -Recurse -Force
        return $true
    }
    return $false
}

$removed = 0
foreach ($base in @(
    "HKCU:\Software\Classes\Directory\shell",
    "HKCU:\Software\Classes\Directory\Background\shell",
    "HKCU:\Software\Classes\DesktopBackground\shell",
    "HKCU:\Software\Classes\LibraryFolder\Background\shell",
    "HKCU:\Software\Classes\Drive\shell"
)) {
    if (Remove-MenuVerb -BaseKey $base -KeyName $FolderVerbKey) { $removed++ }
    if (Remove-MenuVerb -BaseKey $base -KeyName $VerbKey) { $removed++ }
}

foreach ($extension in $MediaExtensions) {
    if (Remove-MenuVerb -BaseKey "HKCU:\Software\Classes\SystemFileAssociations\$extension\shell" -KeyName $VerbKey) {
        $removed++
    }
    if (Remove-MenuVerb -BaseKey "HKCU:\Software\Classes\SystemFileAssociations\$extension\shell" -KeyName $FolderVerbKey) {
        $removed++
    }
}

# 移除 ProgID 下的 Verb
$progids = @{}
foreach ($extension in $MediaExtensions) {
    $uc = Get-ItemProperty "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts\$extension\UserChoice" -ErrorAction SilentlyContinue
    if ($uc -and $uc.ProgId) {
        $progids[$uc.ProgId] = $true
    }
}
foreach ($progid in $progids.Keys) {
    if (Remove-MenuVerb -BaseKey "HKCU:\Software\Classes\$progid\shell" -KeyName $VerbKey) {
        $removed++
    }
    if (Remove-MenuVerb -BaseKey "HKCU:\Software\Classes\$progid\shell" -KeyName $FolderVerbKey) {
        $removed++
    }
}

if (Test-Path -LiteralPath $AppKey) {
    Remove-Item -LiteralPath $AppKey -Recurse -Force
    $removed++
}

try {
    Add-Type -Namespace CascadePic -Name Shell -MemberDefinition @'
[DllImport("shell32.dll", CharSet = CharSet.Auto)]
public static extern void SHChangeNotify(int wEventId, uint uFlags, IntPtr dwItem1, IntPtr dwItem2);
'@ -ErrorAction Stop
    [CascadePic.Shell]::SHChangeNotify(0x08000000, 0x0000, [IntPtr]::Zero, [IntPtr]::Zero)
} catch {}

Write-Host ""
Write-Host ("右键菜单已卸载，共清理 {0} 处注册项。" -f $removed) -ForegroundColor Green

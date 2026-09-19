<#
    CascadePic (流瀑看图) - 卸载 Windows Explorer 右键菜单集成

    用法：
      .\uninstall_context_menu.ps1
#>
[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

$VerbKey = "CascadePic"
$AppKey  = "HKCU:\Software\Classes\Applications\CascadePic.exe"

$MediaExtensions = @(
    ".jpg", ".jpeg", ".jfif", ".png", ".bmp", ".gif", ".webp", ".tif", ".tiff", ".ico",
    ".mp4", ".mkv", ".webm", ".mov", ".avi", ".wmv", ".m4v"
)

function Remove-MenuVerb {
    param([Parameter(Mandatory = $true)][string]$BaseKey)

    $key = Join-Path $BaseKey $VerbKey
    if (Test-Path -LiteralPath $key) {
        Remove-Item -LiteralPath $key -Recurse -Force
        return $true
    }
    return $false
}

$removed = 0
if (Remove-MenuVerb -BaseKey "HKCU:\Software\Classes\Directory\shell") { $removed++ }
if (Remove-MenuVerb -BaseKey "HKCU:\Software\Classes\Directory\Background\shell") { $removed++ }

foreach ($extension in $MediaExtensions) {
    if (Remove-MenuVerb -BaseKey "HKCU:\Software\Classes\SystemFileAssociations\$extension\shell") {
        $removed++
    }
}

if (Test-Path -LiteralPath $AppKey) {
    Remove-Item -LiteralPath $AppKey -Recurse -Force
    $removed++
}

# 清理可能产生的空壳键
foreach ($baseKey in @(
    "HKCU:\Software\Classes\Directory\Background\shell",
    "HKCU:\Software\Classes\Directory\Background",
    "HKCU:\Software\Classes\Directory\shell",
    "HKCU:\Software\Classes\Applications"
)) {
    if (Test-Path -LiteralPath $baseKey) {
        $children = Get-ChildItem -LiteralPath $baseKey -ErrorAction SilentlyContinue
        $values = (Get-Item -LiteralPath $baseKey).Property
        if (-not $children -and $values.Count -eq 0) {
            Remove-Item -LiteralPath $baseKey -Force -ErrorAction SilentlyContinue
        }
    }
}

try {
    Add-Type -Namespace CascadePic -Name Shell -MemberDefinition @'
[DllImport("shell32.dll", CharSet = CharSet.Auto)]
public static extern void SHChangeNotify(int wEventId, uint uFlags, IntPtr dwItem1, IntPtr dwItem2);
'@ -ErrorAction Stop
    [CascadePic.Shell]::SHChangeNotify(0x08000000, 0x0000, [IntPtr]::Zero, [IntPtr]::Zero)
} catch {
    # 忽略
}

Write-Host ""
Write-Host ("右键菜单已卸载，共清理 {0} 处注册项。" -f $removed) -ForegroundColor Green

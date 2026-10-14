<#
    CascadePic (流瀑看图) - Windows Explorer 右键菜单集成

    用途：
      在文件夹、文件夹空白处以及常见图片/视频文件上添加
      右键菜单项。

    特点：
      * 只写入 HKEY_CURRENT_USER，不需要管理员权限，不会弹 UAC。
      * 卸载脚本可完整还原，不留残余。

    用法：
      .\install_context_menu.ps1
      .\install_context_menu.ps1 -ExePath "D:\tools\CascadePic\CascadePic.exe"
#>
[CmdletBinding()]
param(
    [string]$ExePath = ""
)

$ErrorActionPreference = "Stop"

$VerbKey            = "CascadePic"
$VerbLabel          = "用流瀑看图打开"
$FolderVerbKey      = "CascadePicFolder"
$FolderVerbLabel    = "用流瀑看图浏览此文件夹"
$FriendlyName       = "CascadePic 流瀑看图"
$AppKey             = "HKCU:\Software\Classes\Applications\CascadePic.exe"

$MediaExtensions = @(
    ".jpg", ".jpeg", ".jfif", ".png", ".bmp", ".gif", ".webp", ".tif", ".tiff", ".ico",
    ".mp4", ".mkv", ".webm", ".mov", ".avi", ".wmv", ".m4v"
)

function Resolve-CascadeExe {
    param([string]$Candidate)

    if ($Candidate) {
        if (-not (Test-Path -LiteralPath $Candidate)) {
            throw "找不到可执行文件：$Candidate"
        }
        return (Resolve-Path -LiteralPath $Candidate).Path
    }

    $local = Join-Path $PSScriptRoot "CascadePic.exe"
    if (Test-Path -LiteralPath $local) {
        return (Resolve-Path -LiteralPath $local).Path
    }

    $repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
    $repoExe = Join-Path $repoRoot "dist\CascadePic\CascadePic.exe"
    if (Test-Path -LiteralPath $repoExe) {
        return (Resolve-Path -LiteralPath $repoExe).Path
    }

    throw "未找到 CascadePic.exe。请先运行 build.ps1 打包，或用 -ExePath 手动指定路径。"
}

function New-MenuVerb {
    param(
        [Parameter(Mandatory = $true)][string]$BaseKey,
        [Parameter(Mandatory = $true)][string]$ArgumentToken,
        [string]$KeyName = $VerbKey,
        [string]$Label = $VerbLabel,
        [switch]$IsFile
    )

    $key = Join-Path $BaseKey $KeyName
    New-Item -Path $key -Force | Out-Null
    Set-Item -Path $key -Value $Label
    New-ItemProperty -Path $key -Name "Icon" -Value "$script:ResolvedExe,0" `
        -PropertyType String -Force | Out-Null
    if ($IsFile) {
        New-ItemProperty -Path $key -Name "MultiSelectModel" -Value "Single" `
            -PropertyType String -Force | Out-Null
    } else {
        Remove-ItemProperty -Path $key -Name "MultiSelectModel" -ErrorAction SilentlyContinue
    }

    $commandKey = Join-Path $key "command"
    New-Item -Path $commandKey -Force | Out-Null
    Set-Item -Path $commandKey -Value "`"$script:ResolvedExe`" `"$ArgumentToken`""
}

function Update-ShellAssociations {
    try {
        Add-Type -Namespace CascadePic -Name Shell -MemberDefinition @'
[DllImport("shell32.dll", CharSet = CharSet.Auto)]
public static extern void SHChangeNotify(int wEventId, uint uFlags, IntPtr dwItem1, IntPtr dwItem2);
'@ -ErrorAction Stop
        [CascadePic.Shell]::SHChangeNotify(0x08000000, 0x0000, [IntPtr]::Zero, [IntPtr]::Zero)
    } catch {}
}

$script:ResolvedExe = Resolve-CascadeExe -Candidate $ExePath

Write-Host "CascadePic 可执行文件：$script:ResolvedExe"

# 1) 文件夹右键（选中文件夹时）
New-MenuVerb -BaseKey "HKCU:\Software\Classes\Directory\shell" -ArgumentToken "%1" -KeyName $FolderVerbKey -Label $FolderVerbLabel
Write-Host "  [√] 已注册：文件夹右键菜单"

# 2) 文件夹空白处右键
New-MenuVerb -BaseKey "HKCU:\Software\Classes\Directory\Background\shell" -ArgumentToken "%V" -KeyName $FolderVerbKey -Label $FolderVerbLabel
Write-Host "  [√] 已注册：文件夹空白处右键菜单"

# 3) 桌面空白处右键
New-MenuVerb -BaseKey "HKCU:\Software\Classes\DesktopBackground\shell" -ArgumentToken "%V" -KeyName $FolderVerbKey -Label $FolderVerbLabel
Write-Host "  [√] 已注册：桌面空白处右键菜单"

# 4) 库文件夹空白处右键（图片库、视频库等）
New-MenuVerb -BaseKey "HKCU:\Software\Classes\LibraryFolder\Background\shell" -ArgumentToken "%V" -KeyName $FolderVerbKey -Label $FolderVerbLabel
Write-Host "  [√] 已注册：媒体库空白处右键菜单"

# 5) 磁盘盘符右键
New-MenuVerb -BaseKey "HKCU:\Software\Classes\Drive\shell" -ArgumentToken "%1" -KeyName $FolderVerbKey -Label $FolderVerbLabel
Write-Host "  [√] 已注册：磁盘盘符右键菜单"

# 6) 常见图片 / 视频文件右键
foreach ($extension in $MediaExtensions) {
    $baseKey = "HKCU:\Software\Classes\SystemFileAssociations\$extension\shell"
    New-MenuVerb -BaseKey $baseKey -ArgumentToken "%1" -KeyName $VerbKey -Label $VerbLabel -IsFile
}
Write-Host ("  [√] 已注册：{0} 种媒体文件右键菜单" -f $MediaExtensions.Count)

# 7) 注册用户 ProgID 关联层（与 Honeyview 同级，直接显示在一级菜单）
$progids = @{}
foreach ($extension in $MediaExtensions) {
    $uc = Get-ItemProperty "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts\$extension\UserChoice" -ErrorAction SilentlyContinue
    if ($uc -and $uc.ProgId) {
        $progid = $uc.ProgId
        if (Test-Path "HKCU:\Software\Classes\$progid") {
            $progids[$progid] = $true
        }
    }
}
foreach ($progid in $progids.Keys) {
    New-MenuVerb -BaseKey "HKCU:\Software\Classes\$progid\shell" -ArgumentToken "%1" -KeyName $VerbKey -Label $VerbLabel -IsFile
}
if ($progids.Count -gt 0) {
    Write-Host ("  [√] 已注册：{0} 个当前文件关联 ProgID 层" -f $progids.Count)
}

# 8) “打开方式”候选程序
New-Item -Path "$AppKey\shell\open\command" -Force | Out-Null
Set-Item -Path "$AppKey\shell\open\command" -Value "`"$script:ResolvedExe`" `"%1`""
New-ItemProperty -Path $AppKey -Name "FriendlyAppName" -Value $FriendlyName `
    -PropertyType String -Force | Out-Null
New-ItemProperty -Path $AppKey -Name "DefaultIcon" -Value "$script:ResolvedExe,0" `
    -PropertyType String -Force | Out-Null
New-Item -Path "$AppKey\SupportedTypes" -Force | Out-Null
foreach ($extension in $MediaExtensions) {
    New-ItemProperty -Path "$AppKey\SupportedTypes" -Name $extension -Value "" `
        -PropertyType String -Force | Out-Null
}
Write-Host "  [√] 已注册：加入「打开方式」候选列表"

Update-ShellAssociations

Write-Host ""
Write-Host "右键菜单安装完成！" -ForegroundColor Green
Write-Host "现在可以在文件夹、文件夹空白处、桌面空白处、磁盘盘符或图片上点右键，"
Write-Host "选择「用流瀑看图浏览此文件夹」或「用流瀑看图打开」。"
Write-Host "如需移除，请运行 卸载右键菜单.cmd"

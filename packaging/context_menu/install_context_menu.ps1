<#
    CascadePic (流瀑看图) - Windows Explorer 右键菜单集成

    用途：
      在文件夹、文件夹空白处以及常见图片/视频文件上添加
      “用流瀑看图打开” 右键菜单项。

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

$VerbKey      = "CascadePic"
$VerbLabel    = "用流瀑看图打开"
$FriendlyName = "CascadePic 流瀑看图"
$AppKey       = "HKCU:\Software\Classes\Applications\CascadePic.exe"

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
        [Parameter(Mandatory = $true)][string]$ArgumentToken
    )

    $key = Join-Path $BaseKey $VerbKey
    New-Item -Path $key -Force | Out-Null
    Set-Item -Path $key -Value $VerbLabel
    New-ItemProperty -Path $key -Name "Icon" -Value "$script:ResolvedExe,0" `
        -PropertyType String -Force | Out-Null
    # 允许多选时只处理一个目标，避免一次性弹出大量窗口。
    New-ItemProperty -Path $key -Name "MultiSelectModel" -Value "Single" `
        -PropertyType String -Force | Out-Null

    $commandKey = Join-Path $key "command"
    New-Item -Path $commandKey -Force | Out-Null
    Set-Item -Path $commandKey -Value "`"$script:ResolvedExe`" `"$ArgumentToken`""
}

function Remove-MenuVerb {
    param([Parameter(Mandatory = $true)][string]$BaseKey)

    $key = Join-Path $BaseKey $VerbKey
    if (Test-Path -LiteralPath $key) {
        Remove-Item -LiteralPath $key -Recurse -Force
    }
}

function Update-ShellAssociations {
    try {
        Add-Type -Namespace CascadePic -Name Shell -MemberDefinition @'
[DllImport("shell32.dll", CharSet = CharSet.Auto)]
public static extern void SHChangeNotify(int wEventId, uint uFlags, IntPtr dwItem1, IntPtr dwItem2);
'@ -ErrorAction Stop
        [CascadePic.Shell]::SHChangeNotify(0x08000000, 0x0000, [IntPtr]::Zero, [IntPtr]::Zero)
    } catch {
        # 通知失败不影响注册结果，资源管理器稍后也会自动刷新。
    }
}

$script:ResolvedExe = Resolve-CascadeExe -Candidate $ExePath

Write-Host "CascadePic 可执行文件：$script:ResolvedExe"

# 1) 文件夹右键（选中文件夹时）
New-MenuVerb -BaseKey "HKCU:\Software\Classes\Directory\shell" -ArgumentToken "%1"
Write-Host "  [√] 已注册：文件夹右键菜单"

# 2) 文件夹空白处右键
New-MenuVerb -BaseKey "HKCU:\Software\Classes\Directory\Background\shell" -ArgumentToken "%V"
Write-Host "  [√] 已注册：文件夹背景右键菜单"

# 3) 常见图片 / 视频文件右键
foreach ($extension in $MediaExtensions) {
    $baseKey = "HKCU:\Software\Classes\SystemFileAssociations\$extension\shell"
    New-MenuVerb -BaseKey $baseKey -ArgumentToken "%1"
}
Write-Host ("  [√] 已注册：{0} 种媒体文件右键菜单" -f $MediaExtensions.Count)

# 4) “打开方式”候选程序
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
Write-Host "现在可以在文件夹或图片上点右键，选择「用流瀑看图打开」。"
Write-Host "如需移除，请运行 卸载右键菜单.cmd"

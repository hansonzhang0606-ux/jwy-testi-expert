# 泾渭云测试专家 - 一键安装脚本
# 用途：将本专家包注册到本地 WorkBuddy 的 my-experts 市场
# 使用方法：右键本文件 →"使用 PowerShell 运行"
# 前提：已安装 WorkBuddy 并至少打开过一次

$ErrorActionPreference = "Stop"

$expertId = "jingweiyun-testing-expert"
$skillId = "jwy-testing-expert-skill"
$bizLine = "泾渭云"

Write-Host ""
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "  泾渭云测试专家 - 本地安装注册" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

# 1. 定位 WorkBuddy 主目录
$wbHome = Join-Path $env:USERPROFILE ".workbuddy"
if (-not (Test-Path $wbHome)) {
    Write-Host "[X] 未找到 WorkBuddy 目录: $wbHome" -ForegroundColor Red
    Write-Host "请确认 WorkBuddy 已安装并至少打开过一次。" -ForegroundColor Yellow
    Read-Host "按回车键退出"
    exit 1
}
Write-Host "[1/6] WorkBuddy 目录: $wbHome" -ForegroundColor Green

# 2. 获取用户 ID
$userId = $null
$sessionsPath = Join-Path $wbHome "app\sessions.json"
if (Test-Path $sessionsPath) {
    try {
        $sessions = Get-Content $sessionsPath -Encoding UTF8 -Raw | ConvertFrom-Json
        if ($sessions.sessions -and $sessions.sessions.Count -gt 0) {
            foreach ($s in $sessions.sessions) {
                if ($s.userId) { $userId = $s.userId; break }
            }
        }
    } catch {
        Write-Host "[!] sessions.json 解析失败，尝试其他方式..." -ForegroundColor Yellow
    }
}
if (-not $userId) {
    $customBase = Join-Path $wbHome "experts\custom"
    if (Test-Path $customBase) {
        $userDirs = Get-ChildItem $customBase -Directory -ErrorAction SilentlyContinue
        if ($userDirs -and $userDirs.Count -gt 0) { $userId = $userDirs[0].Name }
    }
}
if (-not $userId) {
    Write-Host "[X] 无法自动获取用户 ID。" -ForegroundColor Red
    Write-Host "请先在 WorkBuddy 中发起一个对话，完全退出后重新运行本脚本。" -ForegroundColor Yellow
    Read-Host "按回车键退出"
    exit 1
}
Write-Host "[2/6] 用户 ID: $userId" -ForegroundColor Green

# 3. 确定专家包源目录（脚本所在目录，即专家包根目录）
$sourceDir = Split-Path -Parent $PSCommandPath
if (-not (Test-Path (Join-Path $sourceDir ".codebuddy-plugin\plugin.json"))) {
    Write-Host "[X] 未在脚本所在目录找到专家包结构。" -ForegroundColor Red
    Write-Host "    请确认 install.ps1 位于 jingweiyun-testing-expert 专家包根目录。" -ForegroundColor Yellow
    Read-Host "按回车键退出"
    exit 1
}
Write-Host "[3/6] 专家包源目录: $sourceDir" -ForegroundColor Green

# 4. 复制专家包到 my-experts 市场（持久路径，避免 cache 升级后失效）
$marketplacesDir = Join-Path $wbHome "plugins\marketplaces"
$myExpertsDir = Join-Path $marketplacesDir "my-experts"
$destDir = Join-Path $myExpertsDir "plugins\$expertId"
$destManifestDir = Join-Path $myExpertsDir ".codebuddy-plugin"
$destManifestPath = Join-Path $destManifestDir "marketplace.json"

if (Test-Path $destDir) {
    Write-Host "[4/6] 清理旧版 my-experts 中的专家包..." -ForegroundColor White
    Remove-Item $destDir -Recurse -Force
}
New-Item -ItemType Directory -Path $destDir -Force | Out-Null

$excludeDirs = @(".git", ".workbuddy", "__pycache__")
$sourceItems = Get-ChildItem $sourceDir -Recurse -Force
foreach ($item in $sourceItems) {
    $relativePath = $item.FullName.Substring($sourceDir.Length + 1)
    $skip = $false
    foreach ($ex in $excludeDirs) {
        if ($relativePath -like "*\$ex\*" -or $relativePath -like "$ex\*") { $skip = $true; break }
    }
    if ($skip) { continue }

    $destPath = Join-Path $destDir $relativePath
    if ($item.PSIsContainer) {
        if (-not (Test-Path $destPath)) { New-Item -ItemType Directory -Path $destPath -Force | Out-Null }
    } else {
        $parentDir = Split-Path $destPath -Parent
        if (-not (Test-Path $parentDir)) { New-Item -ItemType Directory -Path $parentDir -Force | Out-Null }
        Copy-Item $item.FullName $destPath -Force
    }
}
Write-Host "[4/6] 专家包已复制到 my-experts 持久路径" -ForegroundColor Green
Write-Host "      $destDir" -ForegroundColor DarkGray

# 5. 创建/更新 marketplace.json
$needManifest = $true
if (Test-Path $destManifestPath) {
    try {
        $existingManifest = Get-Content $destManifestPath -Encoding UTF8 -Raw | ConvertFrom-Json
        $found = $false
        foreach ($p in $existingManifest.plugins) { if ($p.name -eq $expertId) { $found = $true; break } }
        if ($found) { $needManifest = $false }
    } catch {}
}
if ($needManifest) {
    if (-not (Test-Path $destManifestDir)) { New-Item -ItemType Directory -Path $destManifestDir -Force | Out-Null }
    $pluginJsonPath = Join-Path $destDir ".codebuddy-plugin\plugin.json"
    $pluginDesc = "Jingweiyun Testing Expert"
    if (Test-Path $pluginJsonPath) {
        try {
            $pj = Get-Content $pluginJsonPath -Encoding UTF8 -Raw | ConvertFrom-Json
            if ($pj.description) { $pluginDesc = $pj.description }
        } catch {}
    }
    $pluginEntry = @{
        name = $expertId
        source = "./plugins/$expertId"
        description = $pluginDesc
    }
    if (Test-Path $destManifestPath) {
        try {
            $manifest = Get-Content $destManifestPath -Encoding UTF8 -Raw | ConvertFrom-Json
            $manifest.plugins = @($manifest.plugins) + @($pluginEntry)
        } catch {
            $manifest = @{ name = "my-experts"; description = "my-experts marketplace (auto-generated)"; plugins = @($pluginEntry) }
        }
    } else {
        $manifest = @{ name = "my-experts"; description = "my-experts marketplace (auto-generated)"; plugins = @($pluginEntry) }
    }
    $manifestJson = $manifest | ConvertTo-Json -Depth 5
    [System.IO.File]::WriteAllText($destManifestPath, $manifestJson, [System.Text.UTF8Encoding]::new($false))
    Write-Host "      marketplace.json 已创建/更新" -ForegroundColor DarkGray
}

# 6. 写入专家注册表
$customDir = Join-Path $wbHome "experts\custom\$userId"
$expertsJsonPath = Join-Path $customDir "experts.json"
$alreadyRegistered = $false
if (Test-Path $expertsJsonPath) {
    try {
        $existing = Get-Content $expertsJsonPath -Encoding UTF8 -Raw | ConvertFrom-Json
        if ($existing -is [string]) { $existing = @($existing) }
        if ($existing -contains $expertId) { $alreadyRegistered = $true }
    } catch {}
}
if ($alreadyRegistered) {
    Write-Host "[5/6] 专家已注册，无需重复操作。" -ForegroundColor Green
} else {
    if (-not (Test-Path $customDir)) { New-Item -ItemType Directory -Path $customDir -Force | Out-Null }
    $expertList = @($expertId)
    if (Test-Path $expertsJsonPath) {
        try {
            $existingList = Get-Content $expertsJsonPath -Encoding UTF8 -Raw | ConvertFrom-Json
            if ($existingList -is [string]) { $existingList = @($existingList) }
            if ($existingList -and $existingList -notcontains $expertId) {
                $expertList = @($existingList) + @($expertId)
            }
        } catch {}
    }
    if ($expertList.Count -eq 1) {
        $jsonContent = "[`n  `"$expertId`"`n]"
    } else {
        $jsonContent = $expertList | ConvertTo-Json -Depth 5
    }
    [System.IO.File]::WriteAllText($expertsJsonPath, $jsonContent, [System.Text.UTF8Encoding]::new($false))
    Write-Host "[5/6] 专家注册成功！" -ForegroundColor Green
}

# 7. 可选：注册定时同步任务（指向持久路径，避免 cache 版本升级后假死）
$batPath = Join-Path $destDir "skills\$skillId\time-tracking\scripts\sync_task.bat"
$registerPyPath = Join-Path $destDir "skills\$skillId\time-tracking\scripts\register_sync_tasks.py"
if ((Test-Path $batPath) -and (Test-Path $registerPyPath)) {
    Write-Host "[6/6] 正在注册/校验定时同步任务（指向持久路径）..." -ForegroundColor White
    try {
        $pyCmd = "python"
        $pyResult = & $pyCmd $registerPyPath --biz-line $bizLine 2>&1
        $pyResult | ForEach-Object { Write-Host "      $_" -ForegroundColor DarkGray }
    } catch {
        Write-Host "[!] 定时任务注册失败（通常因权限不足）：$_" -ForegroundColor Yellow
        Write-Host "    可后续以管理员身份手动运行：" -ForegroundColor Yellow
        Write-Host "    python `"$registerPyPath`" --biz-line $bizLine" -ForegroundColor Yellow
    }
} else {
    Write-Host "[6/6] 未找到定时任务脚本，跳过。" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "  安装完成！" -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "下一步操作：" -ForegroundColor White
Write-Host "  1. 完全退出 WorkBuddy（托盘图标右键 -> 退出）" -ForegroundColor White
Write-Host "  2. 重新打开 WorkBuddy" -ForegroundColor White
Write-Host "  3. 进入 [专家] -> 右上角 [我的专家]" -ForegroundColor White
Write-Host "  4. 应该能看到 [泾渭云测试专家]" -ForegroundColor White
Write-Host ""
Read-Host "按回车键退出"

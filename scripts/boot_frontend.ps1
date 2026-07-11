$projectRoot = "F:\JOB\GenAI Fund - HACKATHON\P3_TRACK-DETAIL-AND-HOSPILALITY"
$frontendDir = Join-Path $projectRoot "frontend"
$logPath = Join-Path $projectRoot "frontend_service.log"

Set-Location $frontendDir
& npm.cmd run dev -- --host 127.0.0.1 --port 3000 *> $logPath

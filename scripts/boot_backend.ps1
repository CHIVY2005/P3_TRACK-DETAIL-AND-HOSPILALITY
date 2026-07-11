$projectRoot = "F:\JOB\GenAI Fund - HACKATHON\P3_TRACK-DETAIL-AND-HOSPILALITY"
$backendDir = Join-Path $projectRoot "backend"
$logPath = Join-Path $projectRoot "backend_service.log"

Set-Location $backendDir
& "..\.venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload *> $logPath

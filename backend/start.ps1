Write-Host "Starting GeoAI Flood API..." -ForegroundColor Green

& ".\.venv\Scripts\python.exe" -m uvicorn app.main:app --reload --port 8000
# Start PromiseOps locally: landing page on http://127.0.0.1:8000, the tool on /app
python -m pip install -q -r requirements.txt
python -m uvicorn --app-dir src promiseops.web.app:app --port 8000

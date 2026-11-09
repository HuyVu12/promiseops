# Start PromiseOps locally on http://127.0.0.1:8000
python -m pip install -q -r requirements.txt
python -m uvicorn app.main:app --port 8000

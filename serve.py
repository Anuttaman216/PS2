"""Start the FreightSaarthi web app:  python serve.py  ->  http://localhost:8000  (override with PORT=xxxx)"""
import os

import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"FreightSaarthi running at http://localhost:{port}  (cockpit: /app, API: /api, docs: /docs)")
    uvicorn.run("webapp.server:app", host="0.0.0.0", port=port, reload=False)

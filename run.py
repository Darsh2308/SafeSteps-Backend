import uvicorn
from app.utils.logger import Logger

if __name__ == "__main__":
    Logger.info("Starting Safe Steps AI V2 Backend server on http://0.0.0.0:8000")
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

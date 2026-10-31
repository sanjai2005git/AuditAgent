import uvicorn
from auditagent.api.server import app

if __name__ == "__main__":
    uvicorn.run("auditagent.api.server:app", host="127.0.0.1", port=8000, reload=False)

import uvicorn
from query import app

if __name__ == "__main__":
    uvicorn.run("query:app", host="0.0.0.0", port=8000, reload=True)
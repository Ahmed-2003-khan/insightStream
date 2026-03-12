import os
from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader
from dotenv import load_dotenv

load_dotenv()

# Define the expected header for the API key
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def get_api_key(api_key_header: str = Security(api_key_header)) -> str:
    """
    Validates the X-API-Key header against the API_SECRET_KEY in the environment.
    Raises a 403 Forbidden error if the key is missing or invalid.
    """
    secret_key = os.getenv("API_SECRET_KEY")
    if not secret_key:
        raise HTTPException(status_code=500, detail="API_SECRET_KEY is not set in the environment")
        
    if not api_key_header or api_key_header != secret_key:
        raise HTTPException(status_code=403, detail="Invalid or missing API key")
        
    return api_key_header

"""
Utility functions for serverless API
"""
import json
import io
import pandas as pd
from http.server import BaseHTTPRequestHandler
from typing import Dict, Any, Optional

def success_response(data: Any) -> Dict[str, Any]:
    """
    Create standardized success response.

    Args:
        data: Response data

    Returns:
        Standardized response object
    """
    return {
        "data": data,
        "error": None
    }


def error_response(message: str, code: str = "ERROR") -> Dict[str, Any]:
    """
    Create standardized error response.

    Args:
        message: Error message
        code: Error code

    Returns:
        Standardized error response object
    """
    return {
        "data": None,
        "error": {
            "message": message,
            "code": code
        }
    }


def send_json_response(handler: BaseHTTPRequestHandler, status: int, data: Dict[str, Any]):
    """
    Send JSON response with proper headers.

    Args:
        handler: HTTP request handler
        status: HTTP status code
        data: Response data
    """
    handler.send_response(status)
    handler.send_header("Content-type", "application/json")
    handler.end_headers()
    handler.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))


def parse_csv(file_contents: bytes, encoding: str = "utf-8") -> pd.DataFrame:
    """
    Parse CSV file contents with fallback encoding.

    Args:
        file_contents: Raw file bytes
        encoding: Primary encoding (default: utf-8)

    Returns:
        Pandas DataFrame

    Raises:
        Exception: If parsing fails with both encodings
    """
    try:
        df = pd.read_csv(io.BytesIO(file_contents), encoding=encoding)
    except UnicodeDecodeError:
        # Fallback to cp949 for Korean files
        df = pd.read_csv(io.BytesIO(file_contents), encoding="cp949")

    # Strip whitespace from column names
    df.columns = df.columns.str.strip()

    return df


def clean_numeric_column(df: pd.DataFrame, column: str) -> pd.DataFrame:
    """
    Clean numeric column by removing commas and converting to numeric.

    Args:
        df: DataFrame
        column: Column name to clean

    Returns:
        DataFrame with cleaned column
    """
    if column in df.columns:
        df[column] = df[column].astype(str).str.replace(",", "").str.strip()
        df[column] = pd.to_numeric(df[column], errors="coerce").fillna(0)

    return df


def parse_multipart_form(handler: BaseHTTPRequestHandler) -> Dict[str, Any]:
    """
    Parse multipart form data from request.

    Args:
        handler: HTTP request handler

    Returns:
        Dictionary with form fields and files
    """
    # This is a simplified version. For production, use a proper multipart parser
    # or rely on the framework's built-in parsing.
    content_type = handler.headers.get("Content-Type", "")
    content_length = int(handler.headers.get("Content-Length", 0))

    if not content_type.startswith("multipart/form-data"):
        return {}

    # Read the request body
    body = handler.rfile.read(content_length)

    # For Vercel Python, we can use cgi module or rely on external libraries
    # This is a placeholder - actual implementation would need proper multipart parsing
    return {"raw_body": body}

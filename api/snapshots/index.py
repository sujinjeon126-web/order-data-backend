"""
GET /api/snapshots - Retrieve all snapshots
"""
from http.server import BaseHTTPRequestHandler
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from _lib.supabase import get_supabase_client
from _lib.auth import require_auth
from _lib.utils import success_response, error_response, send_json_response


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """
        Get all snapshots ordered by creation date (newest first).

        Returns:
            List of snapshot objects with id, created_at, description, created_by
        """
        try:
            supabase = get_supabase_client()

            # Query snapshots table
            response = supabase.table("snapshots") \
                .select("*") \
                .order("id", desc=True) \
                .execute()

            snapshots = response.data if response.data else []

            send_json_response(self, 200, success_response(snapshots))

        except Exception as e:
            send_json_response(
                self,
                500,
                error_response(str(e), "INTERNAL_ERROR")
            )

    def do_OPTIONS(self):
        """Handle CORS preflight"""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
        self.end_headers()

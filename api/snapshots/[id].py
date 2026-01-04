"""
/api/snapshots/[id] - Get, update, or delete a specific snapshot
GET - Retrieve snapshot by ID (requires auth)
PATCH - Update snapshot (requires admin)
DELETE - Delete snapshot (requires admin)
"""
from http.server import BaseHTTPRequestHandler
import sys
import os
import json
import urllib.parse

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from _lib.supabase import get_supabase_client
from _lib.auth import require_auth, require_admin
from _lib.utils import success_response, error_response, send_json_response


def get_snapshot_id_from_path(path: str) -> int:
    """Extract snapshot ID from URL path"""
    # Parse path like /api/snapshots/123
    parts = path.strip("/").split("/")
    if len(parts) >= 3:
        try:
            return int(parts[-1])
        except ValueError:
            raise ValueError("Invalid snapshot ID")
    raise ValueError("Snapshot ID not found in path")


class handler(BaseHTTPRequestHandler):
    @require_auth
    def do_GET(self, user):
        """
        Get a specific snapshot with all related data.

        Returns:
            Object containing snapshot and all related table data
        """
        try:
            snapshot_id = get_snapshot_id_from_path(self.path)
            supabase = get_supabase_client()

            # Get snapshot
            snapshot_response = supabase.table("snapshots") \
                .select("*") \
                .eq("id", snapshot_id) \
                .execute()

            if not snapshot_response.data or len(snapshot_response.data) == 0:
                send_json_response(
                    self,
                    404,
                    error_response("Snapshot not found", "NOT_FOUND")
                )
                return

            snapshot = snapshot_response.data[0]

            # Fetch all related data
            result = {
                "snapshot": snapshot
            }

            # Fetch order_data
            order_data = supabase.table("order_data") \
                .select("*") \
                .eq("snapshot_id", snapshot_id) \
                .execute()
            result["order_data"] = order_data.data if order_data.data else []

            # Fetch price_table
            price_table = supabase.table("price_table") \
                .select("*") \
                .eq("snapshot_id", snapshot_id) \
                .execute()
            result["price_table"] = price_table.data if price_table.data else []

            # Fetch plan_customer
            plan_customer = supabase.table("plan_customer") \
                .select("*") \
                .eq("snapshot_id", snapshot_id) \
                .execute()
            result["plan_customer"] = plan_customer.data if plan_customer.data else []

            # Fetch expect_customer
            expect_customer = supabase.table("expect_customer") \
                .select("*") \
                .eq("snapshot_id", snapshot_id) \
                .execute()
            result["expect_customer"] = expect_customer.data if expect_customer.data else []

            # Fetch plan_category
            plan_category = supabase.table("plan_category") \
                .select("*") \
                .eq("snapshot_id", snapshot_id) \
                .execute()
            result["plan_category"] = plan_category.data if plan_category.data else []

            # Fetch actual_sales
            actual_sales = supabase.table("actual_sales") \
                .select("*") \
                .eq("snapshot_id", snapshot_id) \
                .execute()
            result["actual_sales"] = actual_sales.data if actual_sales.data else []

            send_json_response(self, 200, success_response(result))

        except ValueError as e:
            send_json_response(
                self,
                400,
                error_response(str(e), "INVALID_REQUEST")
            )
        except Exception as e:
            send_json_response(
                self,
                500,
                error_response(str(e), "INTERNAL_ERROR")
            )

    @require_admin
    def do_PATCH(self, user):
        """
        Update snapshot description.

        Request body:
            {
                "description": "Updated description"
            }
        """
        try:
            snapshot_id = get_snapshot_id_from_path(self.path)
            supabase = get_supabase_client()

            # Read request body
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            data = json.loads(body.decode("utf-8"))

            # Validate request
            if "description" not in data:
                send_json_response(
                    self,
                    400,
                    error_response("description field is required", "INVALID_REQUEST")
                )
                return

            # Check if snapshot exists
            snapshot_response = supabase.table("snapshots") \
                .select("id") \
                .eq("id", snapshot_id) \
                .execute()

            if not snapshot_response.data or len(snapshot_response.data) == 0:
                send_json_response(
                    self,
                    404,
                    error_response("Snapshot not found", "NOT_FOUND")
                )
                return

            # Update snapshot
            update_response = supabase.table("snapshots") \
                .update({"description": data["description"]}) \
                .eq("id", snapshot_id) \
                .execute()

            updated_snapshot = update_response.data[0] if update_response.data else None

            send_json_response(
                self,
                200,
                success_response(updated_snapshot)
            )

        except ValueError as e:
            send_json_response(
                self,
                400,
                error_response(str(e), "INVALID_REQUEST")
            )
        except Exception as e:
            send_json_response(
                self,
                500,
                error_response(str(e), "INTERNAL_ERROR")
            )

    @require_admin
    def do_DELETE(self, user):
        """
        Delete a snapshot and all related data.

        Note: Foreign key constraints will cascade delete all related records.
        """
        try:
            snapshot_id = get_snapshot_id_from_path(self.path)
            supabase = get_supabase_client()

            # Check if snapshot exists
            snapshot_response = supabase.table("snapshots") \
                .select("id") \
                .eq("id", snapshot_id) \
                .execute()

            if not snapshot_response.data or len(snapshot_response.data) == 0:
                send_json_response(
                    self,
                    404,
                    error_response("Snapshot not found", "NOT_FOUND")
                )
                return

            # Delete related data first (in case cascade is not set up)
            supabase.table("order_data").delete().eq("snapshot_id", snapshot_id).execute()
            supabase.table("price_table").delete().eq("snapshot_id", snapshot_id).execute()
            supabase.table("plan_customer").delete().eq("snapshot_id", snapshot_id).execute()
            supabase.table("expect_customer").delete().eq("snapshot_id", snapshot_id).execute()
            supabase.table("plan_category").delete().eq("snapshot_id", snapshot_id).execute()
            supabase.table("actual_sales").delete().eq("snapshot_id", snapshot_id).execute()

            # Delete snapshot
            supabase.table("snapshots").delete().eq("id", snapshot_id).execute()

            send_json_response(
                self,
                200,
                success_response({"message": "Snapshot deleted successfully", "id": snapshot_id})
            )

        except ValueError as e:
            send_json_response(
                self,
                400,
                error_response(str(e), "INVALID_REQUEST")
            )
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
        self.send_header("Access-Control-Allow-Methods", "GET, PATCH, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
        self.end_headers()

"""
GET /api/snapshots/latest - Retrieve latest snapshot with all related data
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
    @require_auth
    def do_GET(self, user):
        """
        Get the latest snapshot with all related data.

        Returns:
            Object containing:
            - snapshot: Snapshot metadata
            - order_data: List of order records
            - price_table: List of price records
            - plan_customer: List of customer plan records
            - expect_customer: List of customer expectation records
            - plan_category: List of category plan records
            - actual_sales: List of actual sales records
        """
        try:
            supabase = get_supabase_client()

            # Get latest snapshot
            snapshot_response = supabase.table("snapshots") \
                .select("*") \
                .order("id", desc=True) \
                .limit(1) \
                .execute()

            if not snapshot_response.data or len(snapshot_response.data) == 0:
                # No snapshots exist
                result = {
                    "snapshot": None,
                    "order_data": [],
                    "price_table": [],
                    "plan_customer": [],
                    "expect_customer": [],
                    "plan_category": [],
                    "actual_sales": []
                }
                send_json_response(self, 200, success_response(result))
                return

            snapshot = snapshot_response.data[0]
            snapshot_id = snapshot["id"]

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

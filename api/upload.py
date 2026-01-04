"""
POST /api/upload - Upload 6 CSV files and create a new snapshot
Requires admin role
"""
from http.server import BaseHTTPRequestHandler
import sys
import os
import cgi
import io
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from _lib.supabase import get_supabase_client
from _lib.auth import require_admin
from _lib.utils import success_response, error_response, send_json_response, parse_csv, clean_numeric_column


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        """
        Create a new snapshot from 6 CSV files.

        Expected multipart/form-data fields:
        - description: Optional snapshot description
        - order_file: Order data CSV
        - price_file: Price table CSV
        - plan_customer_file: Customer plan CSV
        - expect_customer_file: Customer expectation CSV
        - plan_category_file: Category plan CSV
        - actual_sales_file: Actual sales CSV
        """
        try:
            supabase = get_supabase_client()

            # Parse multipart form data
            content_type = self.headers.get("Content-Type")
            if not content_type or not content_type.startswith("multipart/form-data"):
                send_json_response(
                    self,
                    400,
                    error_response("Content-Type must be multipart/form-data", "INVALID_REQUEST")
                )
                return

            # Parse the multipart form
            form = cgi.FieldStorage(
                fp=self.rfile,
                headers=self.headers,
                environ={
                    "REQUEST_METHOD": "POST",
                    "CONTENT_TYPE": content_type,
                }
            )

            # Get description
            description = form.getvalue("description", "")

            # Create snapshot record
            snapshot_data = {
                "created_at": datetime.now().isoformat(),
                "description": description,
                "created_by": user.get("sub")  # User ID from JWT
            }

            snapshot_response = supabase.table("snapshots").insert(snapshot_data).execute()

            if not snapshot_response.data or len(snapshot_response.data) == 0:
                raise Exception("Failed to create snapshot")

            snapshot_id = snapshot_response.data[0]["id"]
            total_rows = 0

            # Process each CSV file
            try:
                # 1. Order Data
                if "order_file" in form:
                    order_file = form["order_file"]
                    if order_file.file:
                        file_contents = order_file.file.read()
                        df = parse_csv(file_contents)

                        # Map Korean column names to English
                        column_mapping = {
                            "생성일": "creation_date",
                            "고객약호": "customer_code",
                            "영업팀명": "sales_team",
                            "자재": "material_code",
                            "중분류명": "category_name",
                            "미납잔량": "backlog_qty",
                            "단가": "unit_price",
                            "변경납기일": "delivery_date"
                        }
                        df = df.rename(columns=column_mapping)

                        # Clean numeric columns
                        df = clean_numeric_column(df, "backlog_qty")
                        df = clean_numeric_column(df, "unit_price")

                        # Add snapshot_id
                        df["snapshot_id"] = snapshot_id

                        # Insert into database
                        records = df.to_dict("records")
                        if records:
                            supabase.table("order_data").insert(records).execute()
                            total_rows += len(records)

                # 2. Price Table
                if "price_file" in form:
                    price_file = form["price_file"]
                    if price_file.file:
                        file_contents = price_file.file.read()
                        df = parse_csv(file_contents)

                        column_mapping = {
                            "관리유형코드(중)": "category_code",
                            "중분류": "category_code",
                            "평균단가": "average_price"
                        }
                        df = df.rename(columns=column_mapping)
                        df = clean_numeric_column(df, "average_price")
                        df["snapshot_id"] = snapshot_id

                        records = df.to_dict("records")
                        if records:
                            supabase.table("price_table").insert(records).execute()
                            total_rows += len(records)

                # 3. Plan Customer
                if "plan_customer_file" in form:
                    plan_customer_file = form["plan_customer_file"]
                    if plan_customer_file.file:
                        file_contents = plan_customer_file.file.read()
                        df = parse_csv(file_contents)

                        column_mapping = {
                            "고객사": "customer",
                            "2025년": "year_total",
                            "1월": "month_01", "2월": "month_02", "3월": "month_03",
                            "4월": "month_04", "5월": "month_05", "6월": "month_06",
                            "7월": "month_07", "8월": "month_08", "9월": "month_09",
                            "10월": "month_10", "11월": "month_11", "12월": "month_12"
                        }
                        df = df.rename(columns=column_mapping)

                        # Clean numeric columns
                        numeric_cols = ["year_total"] + [f"month_{i:02d}" for i in range(1, 13)]
                        for col in numeric_cols:
                            df = clean_numeric_column(df, col)

                        df["snapshot_id"] = snapshot_id
                        records = df.to_dict("records")
                        if records:
                            supabase.table("plan_customer").insert(records).execute()
                            total_rows += len(records)

                # 4. Expect Customer
                if "expect_customer_file" in form:
                    expect_customer_file = form["expect_customer_file"]
                    if expect_customer_file.file:
                        file_contents = expect_customer_file.file.read()
                        df = parse_csv(file_contents)

                        column_mapping = {
                            "고객사": "customer",
                            "2025년": "year_total",
                            "1월": "month_01", "2월": "month_02", "3월": "month_03",
                            "4월": "month_04", "5월": "month_05", "6월": "month_06",
                            "7월": "month_07", "8월": "month_08", "9월": "month_09",
                            "10월": "month_10", "11월": "month_11", "12월": "month_12"
                        }
                        df = df.rename(columns=column_mapping)

                        numeric_cols = ["year_total"] + [f"month_{i:02d}" for i in range(1, 13)]
                        for col in numeric_cols:
                            df = clean_numeric_column(df, col)

                        df["snapshot_id"] = snapshot_id
                        records = df.to_dict("records")
                        if records:
                            supabase.table("expect_customer").insert(records).execute()
                            total_rows += len(records)

                # 5. Plan Category
                if "plan_category_file" in form:
                    plan_category_file = form["plan_category_file"]
                    if plan_category_file.file:
                        file_contents = plan_category_file.file.read()
                        df = parse_csv(file_contents)

                        column_mapping = {
                            "중분류": "category",
                            "중분류명": "category",
                            "2025년": "year_total",
                            "1월": "month_01", "2월": "month_02", "3월": "month_03",
                            "4월": "month_04", "5월": "month_05", "6월": "month_06",
                            "7월": "month_07", "8월": "month_08", "9월": "month_09",
                            "10월": "month_10", "11월": "month_11", "12월": "month_12"
                        }
                        df = df.rename(columns=column_mapping)

                        numeric_cols = ["year_total"] + [f"month_{i:02d}" for i in range(1, 13)]
                        for col in numeric_cols:
                            df = clean_numeric_column(df, col)

                        df["snapshot_id"] = snapshot_id
                        records = df.to_dict("records")
                        if records:
                            supabase.table("plan_category").insert(records).execute()
                            total_rows += len(records)

                # 6. Actual Sales
                if "actual_sales_file" in form:
                    actual_sales_file = form["actual_sales_file"]
                    if actual_sales_file.file:
                        file_contents = actual_sales_file.file.read()
                        df = parse_csv(file_contents)

                        column_mapping = {
                            "고객약호": "customer_code",
                            "중분류명": "category_name",
                            "매출": "sales_amount",
                            "대금청구일": "invoice_date"
                        }
                        df = df.rename(columns=column_mapping)
                        df = clean_numeric_column(df, "sales_amount")
                        df["snapshot_id"] = snapshot_id

                        records = df.to_dict("records")
                        if records:
                            supabase.table("actual_sales").insert(records).execute()
                            total_rows += len(records)

                # Success response
                send_json_response(
                    self,
                    201,
                    success_response({
                        "message": "Snapshot created successfully",
                        "snapshot_id": snapshot_id,
                        "rows_saved": total_rows
                    })
                )

            except Exception as e:
                # If any file processing fails, delete the snapshot
                supabase.table("snapshots").delete().eq("id", snapshot_id).execute()
                raise e

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
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
        self.end_headers()

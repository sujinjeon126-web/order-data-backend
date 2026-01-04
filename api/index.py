"""
Order Data Backend API - FastAPI with Vercel
"""
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
import io
import csv
from typing import Optional
from supabase import create_client

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_supabase():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise HTTPException(status_code=500, detail="Supabase not configured")
    return create_client(url, key)


def parse_csv_content(content: bytes) -> list:
    """Parse CSV content with encoding detection"""
    try:
        text = content.decode('utf-8-sig')
    except:
        try:
            text = content.decode('cp949')
        except:
            text = content.decode('utf-8', errors='ignore')

    reader = csv.DictReader(io.StringIO(text))
    return list(reader)


def clean_numeric(value):
    """Clean numeric value"""
    if value is None or value == '':
        return 0
    if isinstance(value, (int, float)):
        return value
    try:
        return float(str(value).replace(',', '').strip())
    except:
        return 0


@app.get("/api")
def root():
    return {"message": "Order Data API is running"}


@app.get("/api/snapshots")
def get_snapshots():
    """Get all snapshots"""
    try:
        supabase = get_supabase()
        response = supabase.table("snapshots").select("*").order("id", desc=True).execute()
        return {"data": response.data or [], "error": None}
    except Exception as e:
        return {"data": None, "error": {"message": str(e), "code": "ERROR"}}


@app.get("/api/snapshots/latest")
def get_latest_snapshot():
    """Get latest snapshot with all data"""
    try:
        supabase = get_supabase()

        # Get latest snapshot
        snap_resp = supabase.table("snapshots").select("*").order("id", desc=True).limit(1).execute()

        if not snap_resp.data:
            return {"data": {
                "snapshot": None,
                "order_data": [],
                "price_table": [],
                "plan_customer": [],
                "expect_customer": [],
                "plan_category": [],
                "actual_sales": []
            }, "error": None}

        snapshot = snap_resp.data[0]
        snapshot_id = snapshot["id"]

        # Fetch all related data
        order_data = supabase.table("order_data").select("*").eq("snapshot_id", snapshot_id).execute()
        price_table = supabase.table("price_table").select("*").eq("snapshot_id", snapshot_id).execute()
        plan_customer = supabase.table("plan_customer").select("*").eq("snapshot_id", snapshot_id).execute()
        expect_customer = supabase.table("expect_customer").select("*").eq("snapshot_id", snapshot_id).execute()
        plan_category = supabase.table("plan_category").select("*").eq("snapshot_id", snapshot_id).execute()
        actual_sales = supabase.table("actual_sales").select("*").eq("snapshot_id", snapshot_id).execute()

        return {"data": {
            "snapshot": snapshot,
            "order_data": order_data.data or [],
            "price_table": price_table.data or [],
            "plan_customer": plan_customer.data or [],
            "expect_customer": expect_customer.data or [],
            "plan_category": plan_category.data or [],
            "actual_sales": actual_sales.data or []
        }, "error": None}
    except Exception as e:
        return {"data": None, "error": {"message": str(e), "code": "ERROR"}}


@app.get("/api/snapshots/{snapshot_id}")
def get_snapshot(snapshot_id: int):
    """Get specific snapshot"""
    try:
        supabase = get_supabase()

        snap_resp = supabase.table("snapshots").select("*").eq("id", snapshot_id).execute()

        if not snap_resp.data:
            raise HTTPException(status_code=404, detail="Snapshot not found")

        snapshot = snap_resp.data[0]

        order_data = supabase.table("order_data").select("*").eq("snapshot_id", snapshot_id).execute()
        price_table = supabase.table("price_table").select("*").eq("snapshot_id", snapshot_id).execute()
        plan_customer = supabase.table("plan_customer").select("*").eq("snapshot_id", snapshot_id).execute()
        expect_customer = supabase.table("expect_customer").select("*").eq("snapshot_id", snapshot_id).execute()
        plan_category = supabase.table("plan_category").select("*").eq("snapshot_id", snapshot_id).execute()
        actual_sales = supabase.table("actual_sales").select("*").eq("snapshot_id", snapshot_id).execute()

        return {"data": {
            "snapshot": snapshot,
            "order_data": order_data.data or [],
            "price_table": price_table.data or [],
            "plan_customer": plan_customer.data or [],
            "expect_customer": expect_customer.data or [],
            "plan_category": plan_category.data or [],
            "actual_sales": actual_sales.data or []
        }, "error": None}
    except HTTPException:
        raise
    except Exception as e:
        return {"data": None, "error": {"message": str(e), "code": "ERROR"}}


@app.post("/api/upload")
async def upload_files(
    description: Optional[str] = Form(None),
    order_file: Optional[UploadFile] = File(None),
    price_file: Optional[UploadFile] = File(None),
    plan_customer_file: Optional[UploadFile] = File(None),
    expect_customer_file: Optional[UploadFile] = File(None),
    plan_category_file: Optional[UploadFile] = File(None),
    actual_sales_file: Optional[UploadFile] = File(None)
):
    """Upload CSV files and create snapshot"""
    try:
        supabase = get_supabase()

        # Create snapshot
        snap_resp = supabase.table("snapshots").insert({
            "description": description or "New snapshot"
        }).execute()

        if not snap_resp.data:
            raise HTTPException(status_code=500, detail="Failed to create snapshot")

        snapshot_id = snap_resp.data[0]["id"]
        rows_saved = 0

        # Process order_file
        if order_file:
            content = await order_file.read()
            rows = parse_csv_content(content)
            for row in rows:
                supabase.table("order_data").insert({
                    "snapshot_id": snapshot_id,
                    "creation_date": row.get("생성일", row.get("creation_date", "")),
                    "customer_code": row.get("고객약호", row.get("customer_code", "")),
                    "sales_team": row.get("영업팀명", row.get("sales_team", "")),
                    "material_code": row.get("자재", row.get("material_code", "")),
                    "category_name": row.get("중분류명", row.get("category_name", "")),
                    "backlog_qty": clean_numeric(row.get("미납잔량", row.get("backlog_qty", 0))),
                    "unit_price": clean_numeric(row.get("단가", row.get("unit_price", 0))),
                    "delivery_date": row.get("변경납기일", row.get("delivery_date", ""))
                }).execute()
                rows_saved += 1

        # Process price_file
        if price_file:
            content = await price_file.read()
            rows = parse_csv_content(content)
            for row in rows:
                supabase.table("price_table").insert({
                    "snapshot_id": snapshot_id,
                    "category_code": row.get("관리유형코드(중)", row.get("category_code", "")),
                    "average_price": clean_numeric(row.get("평균단가", row.get("average_price", 0)))
                }).execute()
                rows_saved += 1

        # Process plan_customer_file
        if plan_customer_file:
            content = await plan_customer_file.read()
            rows = parse_csv_content(content)
            for row in rows:
                supabase.table("plan_customer").insert({
                    "snapshot_id": snapshot_id,
                    "customer": row.get("고객사", row.get("customer", "")),
                    "year_total": clean_numeric(row.get("2025년", row.get("year_total", 0))),
                    "month_01": clean_numeric(row.get("1월", row.get("month_01", 0))),
                    "month_02": clean_numeric(row.get("2월", row.get("month_02", 0))),
                    "month_03": clean_numeric(row.get("3월", row.get("month_03", 0))),
                    "month_04": clean_numeric(row.get("4월", row.get("month_04", 0))),
                    "month_05": clean_numeric(row.get("5월", row.get("month_05", 0))),
                    "month_06": clean_numeric(row.get("6월", row.get("month_06", 0))),
                    "month_07": clean_numeric(row.get("7월", row.get("month_07", 0))),
                    "month_08": clean_numeric(row.get("8월", row.get("month_08", 0))),
                    "month_09": clean_numeric(row.get("9월", row.get("month_09", 0))),
                    "month_10": clean_numeric(row.get("10월", row.get("month_10", 0))),
                    "month_11": clean_numeric(row.get("11월", row.get("month_11", 0))),
                    "month_12": clean_numeric(row.get("12월", row.get("month_12", 0)))
                }).execute()
                rows_saved += 1

        # Process expect_customer_file
        if expect_customer_file:
            content = await expect_customer_file.read()
            rows = parse_csv_content(content)
            for row in rows:
                supabase.table("expect_customer").insert({
                    "snapshot_id": snapshot_id,
                    "customer": row.get("고객사", row.get("customer", "")),
                    "year_total": clean_numeric(row.get("2025년", row.get("year_total", 0))),
                    "month_01": clean_numeric(row.get("1월", row.get("month_01", 0))),
                    "month_02": clean_numeric(row.get("2월", row.get("month_02", 0))),
                    "month_03": clean_numeric(row.get("3월", row.get("month_03", 0))),
                    "month_04": clean_numeric(row.get("4월", row.get("month_04", 0))),
                    "month_05": clean_numeric(row.get("5월", row.get("month_05", 0))),
                    "month_06": clean_numeric(row.get("6월", row.get("month_06", 0))),
                    "month_07": clean_numeric(row.get("7월", row.get("month_07", 0))),
                    "month_08": clean_numeric(row.get("8월", row.get("month_08", 0))),
                    "month_09": clean_numeric(row.get("9월", row.get("month_09", 0))),
                    "month_10": clean_numeric(row.get("10월", row.get("month_10", 0))),
                    "month_11": clean_numeric(row.get("11월", row.get("month_11", 0))),
                    "month_12": clean_numeric(row.get("12월", row.get("month_12", 0)))
                }).execute()
                rows_saved += 1

        # Process plan_category_file
        if plan_category_file:
            content = await plan_category_file.read()
            rows = parse_csv_content(content)
            for row in rows:
                supabase.table("plan_category").insert({
                    "snapshot_id": snapshot_id,
                    "category": row.get("중분류", row.get("category", "")),
                    "year_total": clean_numeric(row.get("2025년", row.get("year_total", 0))),
                    "month_01": clean_numeric(row.get("1월", row.get("month_01", 0))),
                    "month_02": clean_numeric(row.get("2월", row.get("month_02", 0))),
                    "month_03": clean_numeric(row.get("3월", row.get("month_03", 0))),
                    "month_04": clean_numeric(row.get("4월", row.get("month_04", 0))),
                    "month_05": clean_numeric(row.get("5월", row.get("month_05", 0))),
                    "month_06": clean_numeric(row.get("6월", row.get("month_06", 0))),
                    "month_07": clean_numeric(row.get("7월", row.get("month_07", 0))),
                    "month_08": clean_numeric(row.get("8월", row.get("month_08", 0))),
                    "month_09": clean_numeric(row.get("9월", row.get("month_09", 0))),
                    "month_10": clean_numeric(row.get("10월", row.get("month_10", 0))),
                    "month_11": clean_numeric(row.get("11월", row.get("month_11", 0))),
                    "month_12": clean_numeric(row.get("12월", row.get("month_12", 0)))
                }).execute()
                rows_saved += 1

        # Process actual_sales_file
        if actual_sales_file:
            content = await actual_sales_file.read()
            rows = parse_csv_content(content)
            for row in rows:
                supabase.table("actual_sales").insert({
                    "snapshot_id": snapshot_id,
                    "customer_code": row.get("고객약호", row.get("customer_code", "")),
                    "category_name": row.get("중분류명", row.get("category_name", "")),
                    "sales_amount": clean_numeric(row.get("매출", row.get("sales_amount", 0))),
                    "invoice_date": row.get("대금청구일", row.get("invoice_date", ""))
                }).execute()
                rows_saved += 1

        return {
            "data": {
                "message": "Snapshot created successfully",
                "snapshot_id": snapshot_id,
                "rows_saved": rows_saved
            },
            "error": None
        }
    except HTTPException:
        raise
    except Exception as e:
        return {"data": None, "error": {"message": str(e), "code": "ERROR"}}

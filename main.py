from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Union
from datetime import date, datetime
import pandas as pd
import numpy as np
import io
from sqlalchemy import create_engine, Column, Integer, String, Float, Text, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base

# --- SQLite 데이터베이스 설정 ---
DATABASE_URL = "sqlite:///./data.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# --- 데이터베이스 모델 ---
class Snapshot(Base):
    __tablename__ = "snapshots"
    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(Text)
    description = Column(Text)


class OrderData(Base):
    __tablename__ = "order_data"
    id = Column(Integer, primary_key=True, autoincrement=True)
    snapshot_id = Column(Integer, ForeignKey("snapshots.id"))
    creation_date = Column(Text)
    customer_code = Column(Text)
    sales_team = Column(Text)
    material_code = Column(Text)
    category_name = Column(Text)
    backlog_qty = Column(Integer)
    unit_price = Column(Float)
    delivery_date = Column(Text)


class PriceTable(Base):
    __tablename__ = "price_table"
    id = Column(Integer, primary_key=True, autoincrement=True)
    snapshot_id = Column(Integer, ForeignKey("snapshots.id"))
    category_code = Column(Text)
    average_price = Column(Float)


class PlanCustomer(Base):
    __tablename__ = "plan_customer"
    id = Column(Integer, primary_key=True, autoincrement=True)
    snapshot_id = Column(Integer, ForeignKey("snapshots.id"))
    customer = Column(Text)
    year_total = Column(Float)
    month_01 = Column(Float)
    month_02 = Column(Float)
    month_03 = Column(Float)
    month_04 = Column(Float)
    month_05 = Column(Float)
    month_06 = Column(Float)
    month_07 = Column(Float)
    month_08 = Column(Float)
    month_09 = Column(Float)
    month_10 = Column(Float)
    month_11 = Column(Float)
    month_12 = Column(Float)


class ExpectCustomer(Base):
    __tablename__ = "expect_customer"
    id = Column(Integer, primary_key=True, autoincrement=True)
    snapshot_id = Column(Integer, ForeignKey("snapshots.id"))
    customer = Column(Text)
    year_total = Column(Float)
    month_01 = Column(Float)
    month_02 = Column(Float)
    month_03 = Column(Float)
    month_04 = Column(Float)
    month_05 = Column(Float)
    month_06 = Column(Float)
    month_07 = Column(Float)
    month_08 = Column(Float)
    month_09 = Column(Float)
    month_10 = Column(Float)
    month_11 = Column(Float)
    month_12 = Column(Float)


class PlanCategory(Base):
    __tablename__ = "plan_category"
    id = Column(Integer, primary_key=True, autoincrement=True)
    snapshot_id = Column(Integer, ForeignKey("snapshots.id"))
    category = Column(Text)
    year_total = Column(Float)
    month_01 = Column(Float)
    month_02 = Column(Float)
    month_03 = Column(Float)
    month_04 = Column(Float)
    month_05 = Column(Float)
    month_06 = Column(Float)
    month_07 = Column(Float)
    month_08 = Column(Float)
    month_09 = Column(Float)
    month_10 = Column(Float)
    month_11 = Column(Float)
    month_12 = Column(Float)


class ActualSales(Base):
    __tablename__ = "actual_sales"
    id = Column(Integer, primary_key=True, autoincrement=True)
    snapshot_id = Column(Integer, ForeignKey("snapshots.id"))
    customer_code = Column(Text)
    category_name = Column(Text)
    sales_amount = Column(Float)
    invoice_date = Column(Text)


# 테이블 생성
Base.metadata.create_all(bind=engine)

# --- Pydantic 모델 ---
class DashboardFilter(BaseModel):
    start_date: date
    end_date: date
    customers: Optional[List[str]] = None
    categories: Optional[List[str]] = None

class MonthlyBacklog(BaseModel):
    month: str
    amount: float
    is_special: bool

class CustomerBacklog(BaseModel):
    customer: str
    amount: float

class CategoryBacklog(BaseModel):
    category: str
    amount: float
    percentage: float

class DashboardData(BaseModel):
    monthly_backlog: List[MonthlyBacklog]
    customer_backlog: List[CustomerBacklog]
    category_backlog: List[CategoryBacklog]


# --- FastAPI 앱 설정 ---
app = FastAPI()
origins = ["http://localhost:5173", "http://localhost:3000"]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# --- 데이터 처리 함수 ---
def get_processed_data():
    # 이 함수는 앱 실행 시 한 번만 데이터를 로드하고 전처리하면 더 효율적입니다.
    # 여기서는 간단하게 요청 시마다 로드하도록 구현합니다.
    try:
        df_order = pd.read_csv(r"C:\Users\sujin.jeon\Downloads\order data.csv", encoding='cp949', low_memory=False)
        df_price = pd.read_csv(r"C:\Users\sujin.jeon\Downloads\price table.csv", encoding='cp949', low_memory=False)
        df_actual_sales = pd.read_csv(r"C:\Users\sujin.jeon\Downloads\12m actual_sales.csv", encoding='cp949', low_memory=False)
    except FileNotFoundError as e:
        # 실제 운영환경에서는 더 정교한 에러 처리가 필요합니다.
        raise RuntimeError(f"데이터 파일 로딩 실패: {e}")

    # 전처리
    df_order_processed = df_order.copy()
    df_order_processed = df_order_processed[df_order_processed['자재'].astype(str).str.startswith('9')]
    df_order_processed = df_order_processed[df_order_processed['일정라인범주'] != 'MRP(MRP Close)']
    
    df_price_processed = df_price.copy()
    df_price_processed['평균단가'] = df_price_processed['평균단가'].astype(str).str.replace(',', '').str.strip()
    df_price_processed['평균단가'] = pd.to_numeric(df_price_processed['평균단가'], errors='coerce').fillna(0)

    # 단가 보정
    price_dict = df_price_processed.set_index('중분류')['평균단가'].to_dict()
    def correct_price(row):
        if row['단가'] == 0:
            if row['총본품수량'] == 0: return 200
            else: return price_dict.get(row['중분류'], 0)
        else: return row['단가']
    df_order_processed['보정단가'] = df_order_processed.apply(correct_price, axis=1)
    df_order_processed['보정수주액'] = df_order_processed['보정단가'] * df_order_processed['수량']
    
    # 날짜 변환 및 12월 특별 로직
    df_order_processed['납기요청일'] = pd.to_datetime(df_order_processed['납기요청일'], errors='coerce')
    df_order_processed.dropna(subset=['납기요청일'], inplace=True)
    
    base_monthly_backlog = df_order_processed.groupby(df_order_processed['납기요청일'].dt.to_period('M'))['보정수주액'].sum()
    carry_over = base_monthly_backlog[base_monthly_backlog.index < '2025-12'].sum()
    actual_sales = df_actual_sales['매출액'].sum()
    dec_special_value = carry_over + actual_sales
    
    df_dec_special = pd.DataFrame([{'납기요청일': datetime(2025, 12, 1), '고객사': '12월 예측조정', '중분류': '12월 예측조정', '보정수주액': dec_special_value}])
    
    df_final = pd.concat([df_order_processed, df_dec_special], ignore_index=True)
    df_final['납기요청월'] = pd.to_datetime(df_final['납기요청일']).dt.to_period('M')

    return df_final

# --- API 엔드포인트 ---
@app.get("/")
def read_root():
    return {"message": "Order Data Analysis API is running."}

@app.post("/api/v1/dashboard", response_model=DashboardData)
def get_dashboard_data_endpoint(filters: DashboardFilter):
    df_final = get_processed_data()

    # 필터링
    filtered_df = df_final[
        (pd.to_datetime(df_final['납기요청일']).dt.date >= filters.start_date) &
        (pd.to_datetime(df_final['납기요청일']).dt.date <= filters.end_date) &
        (df_final['고객사'].isin(filters.customers if filters.customers else df_final['고객사'].unique())) &
        (df_final['중분류'].isin(filters.categories if filters.categories else df_final['중분류'].unique()))
    ]

    # 1. 월별 데이터 계산
    monthly_backlog_series = filtered_df.groupby('납기요청월')['보정수주액'].sum()
    monthly_result = []
    for month, amount in monthly_backlog_series.items():
        is_special = str(month) == '2025-12'
        monthly_result.append(MonthlyBacklog(month=str(month), amount=round(amount / 1e8, 2), is_special=is_special))

    # 2. 고객사 데이터 계산
    customer_backlog_series = filtered_df.groupby('고객사')['보정수주액'].sum().nlargest(50)
    customer_result = [CustomerBacklog(customer=customer, amount=round(amount / 1e8, 2)) for customer, amount in customer_backlog_series.items()]

    # 3. 중유형 데이터 계산
    category_backlog_series = filtered_df.groupby('중분류')['보정수주액'].sum()
    total_backlog = category_backlog_series.sum()
    category_result = []
    for cat, amount in category_backlog_series.items():
        percentage = round((amount / total_backlog) * 100, 1) if total_backlog > 0 else 0
        category_result.append(CategoryBacklog(category=cat, amount=round(amount / 1e8, 2), percentage=percentage))
    
    return DashboardData(
        monthly_backlog=monthly_result,
        customer_backlog=customer_result,
        category_backlog=category_result
    )


# --- 스냅샷 저장 엔드포인트 ---
@app.post("/upload")
async def upload_csv(request: Request):
    """6개 CSV 파일을 받아 데이터베이스에 스냅샷으로 저장"""
    try:
        # multipart form 파싱
        form = await request.form()
        description = form.get("description", "")

        # 파일들 가져오기
        order_file = form.get("order_file")
        price_file = form.get("price_file")
        plan_customer_file = form.get("plan_customer_file")
        expect_customer_file = form.get("expect_customer_file")
        plan_category_file = form.get("plan_category_file")
        actual_sales_file = form.get("actual_sales_file")

        # 스냅샷 생성
        db = SessionLocal()
        try:
            # snapshots 테이블에 기록
            new_snapshot = Snapshot(
                created_at=datetime.now().isoformat(),
                description=str(description)
            )
            db.add(new_snapshot)
            db.commit()
            db.refresh(new_snapshot)
            snapshot_id = new_snapshot.id

            total_rows = 0

            # 1. Order Data 처리
            if order_file and hasattr(order_file, 'read'):
                contents = await order_file.read()
                try:
                    df = pd.read_csv(io.BytesIO(contents), encoding='utf-8')
                except UnicodeDecodeError:
                    df = pd.read_csv(io.BytesIO(contents), encoding='cp949')

                df.columns = df.columns.str.strip()
                column_mapping = {
                    '생성일': 'creation_date',
                    '고객약호': 'customer_code',
                    '영업팀명': 'sales_team',
                    '자재': 'material_code',
                    '중분류명': 'category_name',
                    '미납잔량': 'backlog_qty',
                    '단가': 'unit_price',
                    '변경납기일': 'delivery_date'
                }
                df = df.rename(columns=column_mapping)
                target_columns = ['creation_date', 'customer_code', 'sales_team',
                                  'material_code', 'category_name', 'backlog_qty',
                                  'unit_price', 'delivery_date']
                existing_columns = [col for col in target_columns if col in df.columns]
                df = df[existing_columns]

                for col in ['backlog_qty', 'unit_price']:
                    if col in df.columns:
                        df[col] = df[col].astype(str).str.replace(',', '').str.strip()
                        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

                df['snapshot_id'] = snapshot_id
                df.to_sql('order_data', engine, if_exists='append', index=False)
                total_rows += len(df)

            # 2. Price Table 처리
            if price_file and hasattr(price_file, 'read'):
                contents = await price_file.read()
                try:
                    df = pd.read_csv(io.BytesIO(contents), encoding='utf-8')
                except UnicodeDecodeError:
                    df = pd.read_csv(io.BytesIO(contents), encoding='cp949')

                df.columns = df.columns.str.strip()
                column_mapping = {
                    '관리유형코드(중)': 'category_code',
                    '중분류': 'category_code',
                    '평균단가': 'average_price'
                }
                df = df.rename(columns=column_mapping)
                target_columns = ['category_code', 'average_price']
                existing_columns = [col for col in target_columns if col in df.columns]
                df = df[existing_columns]

                if 'average_price' in df.columns:
                    df['average_price'] = df['average_price'].astype(str).str.replace(',', '').str.strip()
                    df['average_price'] = pd.to_numeric(df['average_price'], errors='coerce').fillna(0)

                df['snapshot_id'] = snapshot_id
                df.to_sql('price_table', engine, if_exists='append', index=False)
                total_rows += len(df)

            # 3. Plan Customer 처리
            if plan_customer_file and hasattr(plan_customer_file, 'read'):
                contents = await plan_customer_file.read()
                try:
                    df = pd.read_csv(io.BytesIO(contents), encoding='utf-8')
                except UnicodeDecodeError:
                    df = pd.read_csv(io.BytesIO(contents), encoding='cp949')

                df.columns = df.columns.str.strip()
                column_mapping = {
                    '고객사': 'customer',
                    '2025년': 'year_total',
                    '1월': 'month_01', '2월': 'month_02', '3월': 'month_03',
                    '4월': 'month_04', '5월': 'month_05', '6월': 'month_06',
                    '7월': 'month_07', '8월': 'month_08', '9월': 'month_09',
                    '10월': 'month_10', '11월': 'month_11', '12월': 'month_12'
                }
                df = df.rename(columns=column_mapping)

                numeric_cols = ['year_total'] + [f'month_{i:02d}' for i in range(1, 13)]
                for col in numeric_cols:
                    if col in df.columns:
                        df[col] = df[col].astype(str).str.replace(',', '').str.strip()
                        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

                df['snapshot_id'] = snapshot_id
                df.to_sql('plan_customer', engine, if_exists='append', index=False)
                total_rows += len(df)

            # 4. Expect Customer 처리
            if expect_customer_file and hasattr(expect_customer_file, 'read'):
                contents = await expect_customer_file.read()
                try:
                    df = pd.read_csv(io.BytesIO(contents), encoding='utf-8')
                except UnicodeDecodeError:
                    df = pd.read_csv(io.BytesIO(contents), encoding='cp949')

                df.columns = df.columns.str.strip()
                column_mapping = {
                    '고객사': 'customer',
                    '2025년': 'year_total',
                    '1월': 'month_01', '2월': 'month_02', '3월': 'month_03',
                    '4월': 'month_04', '5월': 'month_05', '6월': 'month_06',
                    '7월': 'month_07', '8월': 'month_08', '9월': 'month_09',
                    '10월': 'month_10', '11월': 'month_11', '12월': 'month_12'
                }
                df = df.rename(columns=column_mapping)

                numeric_cols = ['year_total'] + [f'month_{i:02d}' for i in range(1, 13)]
                for col in numeric_cols:
                    if col in df.columns:
                        df[col] = df[col].astype(str).str.replace(',', '').str.strip()
                        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

                df['snapshot_id'] = snapshot_id
                df.to_sql('expect_customer', engine, if_exists='append', index=False)
                total_rows += len(df)

            # 5. Plan Category 처리
            if plan_category_file and hasattr(plan_category_file, 'read'):
                contents = await plan_category_file.read()
                try:
                    df = pd.read_csv(io.BytesIO(contents), encoding='utf-8')
                except UnicodeDecodeError:
                    df = pd.read_csv(io.BytesIO(contents), encoding='cp949')

                df.columns = df.columns.str.strip()
                column_mapping = {
                    '중분류': 'category',
                    '중분류명': 'category',
                    '2025년': 'year_total',
                    '1월': 'month_01', '2월': 'month_02', '3월': 'month_03',
                    '4월': 'month_04', '5월': 'month_05', '6월': 'month_06',
                    '7월': 'month_07', '8월': 'month_08', '9월': 'month_09',
                    '10월': 'month_10', '11월': 'month_11', '12월': 'month_12'
                }
                df = df.rename(columns=column_mapping)

                numeric_cols = ['year_total'] + [f'month_{i:02d}' for i in range(1, 13)]
                for col in numeric_cols:
                    if col in df.columns:
                        df[col] = df[col].astype(str).str.replace(',', '').str.strip()
                        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

                df['snapshot_id'] = snapshot_id
                df.to_sql('plan_category', engine, if_exists='append', index=False)
                total_rows += len(df)

            # 6. Actual Sales 처리
            if actual_sales_file and hasattr(actual_sales_file, 'read'):
                contents = await actual_sales_file.read()
                try:
                    df = pd.read_csv(io.BytesIO(contents), encoding='utf-8')
                except UnicodeDecodeError:
                    df = pd.read_csv(io.BytesIO(contents), encoding='cp949')

                df.columns = df.columns.str.strip()
                column_mapping = {
                    '고객약호': 'customer_code',
                    '중분류명': 'category_name',
                    '매출': 'sales_amount',
                    '대금청구일': 'invoice_date'
                }
                df = df.rename(columns=column_mapping)
                target_columns = ['customer_code', 'category_name', 'sales_amount', 'invoice_date']
                existing_columns = [col for col in target_columns if col in df.columns]
                df = df[existing_columns]

                if 'sales_amount' in df.columns:
                    df['sales_amount'] = df['sales_amount'].astype(str).str.replace(',', '').str.strip()
                    df['sales_amount'] = pd.to_numeric(df['sales_amount'], errors='coerce').fillna(0)

                df['snapshot_id'] = snapshot_id
                df.to_sql('actual_sales', engine, if_exists='append', index=False)
                total_rows += len(df)

            return {
                "message": "Snapshot created successfully",
                "snapshot_id": snapshot_id,
                "rows_saved": total_rows
            }
        finally:
            db.close()

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- 스냅샷 목록 조회 ---
@app.get("/snapshots")
def get_snapshots():
    """모든 스냅샷 목록 조회"""
    db = SessionLocal()
    try:
        snapshots = db.query(Snapshot).order_by(Snapshot.id.desc()).all()
        return [
            {
                "id": s.id,
                "created_at": s.created_at,
                "description": s.description
            }
            for s in snapshots
        ]
    finally:
        db.close()


# --- 최신 스냅샷 데이터 조회 ---
@app.get("/snapshots/latest")
def get_latest_snapshot():
    """최신 스냅샷의 모든 데이터 조회"""
    db = SessionLocal()
    try:
        # 최신 스냅샷 조회
        latest = db.query(Snapshot).order_by(Snapshot.id.desc()).first()
        if not latest:
            return {
                "snapshot": None,
                "order_data": [],
                "price_table": [],
                "plan_customer": [],
                "expect_customer": [],
                "plan_category": [],
                "actual_sales": []
            }

        result = {
            "snapshot": {
                "id": latest.id,
                "created_at": latest.created_at,
                "description": latest.description
            }
        }

        # 1. Order Data 조회
        query = f"SELECT * FROM order_data WHERE snapshot_id = {latest.id}"
        df = pd.read_sql(query, engine)
        if not df.empty:
            column_mapping = {
                'creation_date': '생성일',
                'customer_code': '고객약호',
                'sales_team': '영업팀명',
                'material_code': '자재',
                'category_name': '중분류명',
                'backlog_qty': '미납잔량',
                'unit_price': '단가',
                'delivery_date': '변경납기일'
            }
            df = df.rename(columns=column_mapping)
            df = df.drop(columns=['id', 'snapshot_id'], errors='ignore')
        result["order_data"] = df.to_dict(orient='records')

        # 2. Price Table 조회
        query = f"SELECT * FROM price_table WHERE snapshot_id = {latest.id}"
        df = pd.read_sql(query, engine)
        if not df.empty:
            column_mapping = {
                'category_code': '중분류',
                'average_price': '평균단가'
            }
            df = df.rename(columns=column_mapping)
            df = df.drop(columns=['id', 'snapshot_id'], errors='ignore')
        result["price_table"] = df.to_dict(orient='records')

        # 3. Plan Customer 조회
        query = f"SELECT * FROM plan_customer WHERE snapshot_id = {latest.id}"
        df = pd.read_sql(query, engine)
        if not df.empty:
            column_mapping = {
                'customer': '고객사',
                'year_total': '2025년',
                'month_01': '1월', 'month_02': '2월', 'month_03': '3월',
                'month_04': '4월', 'month_05': '5월', 'month_06': '6월',
                'month_07': '7월', 'month_08': '8월', 'month_09': '9월',
                'month_10': '10월', 'month_11': '11월', 'month_12': '12월'
            }
            df = df.rename(columns=column_mapping)
            df = df.drop(columns=['id', 'snapshot_id'], errors='ignore')
        result["plan_customer"] = df.to_dict(orient='records')

        # 4. Expect Customer 조회
        query = f"SELECT * FROM expect_customer WHERE snapshot_id = {latest.id}"
        df = pd.read_sql(query, engine)
        if not df.empty:
            column_mapping = {
                'customer': '고객사',
                'year_total': '2025년',
                'month_01': '1월', 'month_02': '2월', 'month_03': '3월',
                'month_04': '4월', 'month_05': '5월', 'month_06': '6월',
                'month_07': '7월', 'month_08': '8월', 'month_09': '9월',
                'month_10': '10월', 'month_11': '11월', 'month_12': '12월'
            }
            df = df.rename(columns=column_mapping)
            df = df.drop(columns=['id', 'snapshot_id'], errors='ignore')
        result["expect_customer"] = df.to_dict(orient='records')

        # 5. Plan Category 조회
        query = f"SELECT * FROM plan_category WHERE snapshot_id = {latest.id}"
        df = pd.read_sql(query, engine)
        if not df.empty:
            column_mapping = {
                'category': '중분류',
                'year_total': '2025년',
                'month_01': '1월', 'month_02': '2월', 'month_03': '3월',
                'month_04': '4월', 'month_05': '5월', 'month_06': '6월',
                'month_07': '7월', 'month_08': '8월', 'month_09': '9월',
                'month_10': '10월', 'month_11': '11월', 'month_12': '12월'
            }
            df = df.rename(columns=column_mapping)
            df = df.drop(columns=['id', 'snapshot_id'], errors='ignore')
        result["plan_category"] = df.to_dict(orient='records')

        # 6. Actual Sales 조회
        query = f"SELECT * FROM actual_sales WHERE snapshot_id = {latest.id}"
        df = pd.read_sql(query, engine)
        if not df.empty:
            column_mapping = {
                'customer_code': '고객약호',
                'category_name': '중분류명',
                'sales_amount': '매출',
                'invoice_date': '대금청구일'
            }
            df = df.rename(columns=column_mapping)
            df = df.drop(columns=['id', 'snapshot_id'], errors='ignore')
        result["actual_sales"] = df.to_dict(orient='records')

        return result
    finally:
        db.close()


# --- 특정 스냅샷 데이터 조회 ---
@app.get("/snapshots/{snapshot_id}")
def get_snapshot(snapshot_id: int):
    """특정 스냅샷의 모든 데이터 조회"""
    db = SessionLocal()
    try:
        snapshot = db.query(Snapshot).filter(Snapshot.id == snapshot_id).first()
        if not snapshot:
            raise HTTPException(status_code=404, detail="Snapshot not found")

        result = {
            "snapshot": {
                "id": snapshot.id,
                "created_at": snapshot.created_at,
                "description": snapshot.description
            }
        }

        # 1. Order Data 조회
        query = f"SELECT * FROM order_data WHERE snapshot_id = {snapshot_id}"
        df = pd.read_sql(query, engine)
        if not df.empty:
            column_mapping = {
                'creation_date': '생성일',
                'customer_code': '고객약호',
                'sales_team': '영업팀명',
                'material_code': '자재',
                'category_name': '중분류명',
                'backlog_qty': '미납잔량',
                'unit_price': '단가',
                'delivery_date': '변경납기일'
            }
            df = df.rename(columns=column_mapping)
            df = df.drop(columns=['id', 'snapshot_id'], errors='ignore')
        result["order_data"] = df.to_dict(orient='records')

        # 2. Price Table 조회
        query = f"SELECT * FROM price_table WHERE snapshot_id = {snapshot_id}"
        df = pd.read_sql(query, engine)
        if not df.empty:
            column_mapping = {
                'category_code': '중분류',
                'average_price': '평균단가'
            }
            df = df.rename(columns=column_mapping)
            df = df.drop(columns=['id', 'snapshot_id'], errors='ignore')
        result["price_table"] = df.to_dict(orient='records')

        # 3. Plan Customer 조회
        query = f"SELECT * FROM plan_customer WHERE snapshot_id = {snapshot_id}"
        df = pd.read_sql(query, engine)
        if not df.empty:
            column_mapping = {
                'customer': '고객사',
                'year_total': '2025년',
                'month_01': '1월', 'month_02': '2월', 'month_03': '3월',
                'month_04': '4월', 'month_05': '5월', 'month_06': '6월',
                'month_07': '7월', 'month_08': '8월', 'month_09': '9월',
                'month_10': '10월', 'month_11': '11월', 'month_12': '12월'
            }
            df = df.rename(columns=column_mapping)
            df = df.drop(columns=['id', 'snapshot_id'], errors='ignore')
        result["plan_customer"] = df.to_dict(orient='records')

        # 4. Expect Customer 조회
        query = f"SELECT * FROM expect_customer WHERE snapshot_id = {snapshot_id}"
        df = pd.read_sql(query, engine)
        if not df.empty:
            column_mapping = {
                'customer': '고객사',
                'year_total': '2025년',
                'month_01': '1월', 'month_02': '2월', 'month_03': '3월',
                'month_04': '4월', 'month_05': '5월', 'month_06': '6월',
                'month_07': '7월', 'month_08': '8월', 'month_09': '9월',
                'month_10': '10월', 'month_11': '11월', 'month_12': '12월'
            }
            df = df.rename(columns=column_mapping)
            df = df.drop(columns=['id', 'snapshot_id'], errors='ignore')
        result["expect_customer"] = df.to_dict(orient='records')

        # 5. Plan Category 조회
        query = f"SELECT * FROM plan_category WHERE snapshot_id = {snapshot_id}"
        df = pd.read_sql(query, engine)
        if not df.empty:
            column_mapping = {
                'category': '중분류',
                'year_total': '2025년',
                'month_01': '1월', 'month_02': '2월', 'month_03': '3월',
                'month_04': '4월', 'month_05': '5월', 'month_06': '6월',
                'month_07': '7월', 'month_08': '8월', 'month_09': '9월',
                'month_10': '10월', 'month_11': '11월', 'month_12': '12월'
            }
            df = df.rename(columns=column_mapping)
            df = df.drop(columns=['id', 'snapshot_id'], errors='ignore')
        result["plan_category"] = df.to_dict(orient='records')

        # 6. Actual Sales 조회
        query = f"SELECT * FROM actual_sales WHERE snapshot_id = {snapshot_id}"
        df = pd.read_sql(query, engine)
        if not df.empty:
            column_mapping = {
                'customer_code': '고객약호',
                'category_name': '중분류명',
                'sales_amount': '매출',
                'invoice_date': '대금청구일'
            }
            df = df.rename(columns=column_mapping)
            df = df.drop(columns=['id', 'snapshot_id'], errors='ignore')
        result["actual_sales"] = df.to_dict(orient='records')

        return result
    finally:
        db.close()


# --- 스냅샷 업데이트 엔드포인트 ---
@app.patch("/snapshots/{snapshot_id}")
async def update_snapshot(snapshot_id: int, request: Request):
    """기존 스냅샷의 특정 테이블만 업데이트 (부분 업데이트)"""
    db = SessionLocal()
    try:
        # 1. 스냅샷 존재 확인
        snapshot = db.query(Snapshot).filter(Snapshot.id == snapshot_id).first()
        if not snapshot:
            raise HTTPException(status_code=404, detail="Snapshot not found")

        # 2. multipart form 파싱
        form = await request.form()

        # 파일들 가져오기
        order_file = form.get("order_file")
        price_file = form.get("price_file")
        plan_customer_file = form.get("plan_customer_file")
        expect_customer_file = form.get("expect_customer_file")
        plan_category_file = form.get("plan_category_file")
        actual_sales_file = form.get("actual_sales_file")

        updated_tables = []
        total_rows = 0

        # 3. 각 파일 처리 (트랜잭션)

        # 3-1. Order Data 처리
        if order_file and hasattr(order_file, 'read'):
            # 기존 데이터 삭제
            db.query(OrderData).filter(OrderData.snapshot_id == snapshot_id).delete()

            # 파일 파싱 및 삽입
            contents = await order_file.read()
            try:
                df = pd.read_csv(io.BytesIO(contents), encoding='utf-8')
            except UnicodeDecodeError:
                df = pd.read_csv(io.BytesIO(contents), encoding='cp949')

            df.columns = df.columns.str.strip()
            column_mapping = {
                '생성일': 'creation_date',
                '고객약호': 'customer_code',
                '영업팀명': 'sales_team',
                '자재': 'material_code',
                '중분류명': 'category_name',
                '미납잔량': 'backlog_qty',
                '단가': 'unit_price',
                '변경납기일': 'delivery_date'
            }
            df = df.rename(columns=column_mapping)
            target_columns = ['creation_date', 'customer_code', 'sales_team',
                              'material_code', 'category_name', 'backlog_qty',
                              'unit_price', 'delivery_date']
            existing_columns = [col for col in target_columns if col in df.columns]
            df = df[existing_columns]

            for col in ['backlog_qty', 'unit_price']:
                if col in df.columns:
                    df[col] = df[col].astype(str).str.replace(',', '').str.strip()
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

            df['snapshot_id'] = snapshot_id
            df.to_sql('order_data', engine, if_exists='append', index=False)
            updated_tables.append('order_data')
            total_rows += len(df)

        # 3-2. Price Table 처리
        if price_file and hasattr(price_file, 'read'):
            # 기존 데이터 삭제
            db.query(PriceTable).filter(PriceTable.snapshot_id == snapshot_id).delete()

            # 파일 파싱 및 삽입
            contents = await price_file.read()
            try:
                df = pd.read_csv(io.BytesIO(contents), encoding='utf-8')
            except UnicodeDecodeError:
                df = pd.read_csv(io.BytesIO(contents), encoding='cp949')

            df.columns = df.columns.str.strip()
            column_mapping = {
                '관리유형코드(중)': 'category_code',
                '중분류': 'category_code',
                '평균단가': 'average_price'
            }
            df = df.rename(columns=column_mapping)
            target_columns = ['category_code', 'average_price']
            existing_columns = [col for col in target_columns if col in df.columns]
            df = df[existing_columns]

            if 'average_price' in df.columns:
                df['average_price'] = df['average_price'].astype(str).str.replace(',', '').str.strip()
                df['average_price'] = pd.to_numeric(df['average_price'], errors='coerce').fillna(0)

            df['snapshot_id'] = snapshot_id
            df.to_sql('price_table', engine, if_exists='append', index=False)
            updated_tables.append('price_table')
            total_rows += len(df)

        # 3-3. Plan Customer 처리
        if plan_customer_file and hasattr(plan_customer_file, 'read'):
            # 기존 데이터 삭제
            db.query(PlanCustomer).filter(PlanCustomer.snapshot_id == snapshot_id).delete()

            # 파일 파싱 및 삽입
            contents = await plan_customer_file.read()
            try:
                df = pd.read_csv(io.BytesIO(contents), encoding='utf-8')
            except UnicodeDecodeError:
                df = pd.read_csv(io.BytesIO(contents), encoding='cp949')

            df.columns = df.columns.str.strip()
            column_mapping = {
                '고객사': 'customer',
                '2025년': 'year_total',
                '1월': 'month_01', '2월': 'month_02', '3월': 'month_03',
                '4월': 'month_04', '5월': 'month_05', '6월': 'month_06',
                '7월': 'month_07', '8월': 'month_08', '9월': 'month_09',
                '10월': 'month_10', '11월': 'month_11', '12월': 'month_12'
            }
            df = df.rename(columns=column_mapping)

            numeric_cols = ['year_total'] + [f'month_{i:02d}' for i in range(1, 13)]
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = df[col].astype(str).str.replace(',', '').str.strip()
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

            df['snapshot_id'] = snapshot_id
            df.to_sql('plan_customer', engine, if_exists='append', index=False)
            updated_tables.append('plan_customer')
            total_rows += len(df)

        # 3-4. Expect Customer 처리
        if expect_customer_file and hasattr(expect_customer_file, 'read'):
            # 기존 데이터 삭제
            db.query(ExpectCustomer).filter(ExpectCustomer.snapshot_id == snapshot_id).delete()

            # 파일 파싱 및 삽입
            contents = await expect_customer_file.read()
            try:
                df = pd.read_csv(io.BytesIO(contents), encoding='utf-8')
            except UnicodeDecodeError:
                df = pd.read_csv(io.BytesIO(contents), encoding='cp949')

            df.columns = df.columns.str.strip()
            column_mapping = {
                '고객사': 'customer',
                '2025년': 'year_total',
                '1월': 'month_01', '2월': 'month_02', '3월': 'month_03',
                '4월': 'month_04', '5월': 'month_05', '6월': 'month_06',
                '7월': 'month_07', '8월': 'month_08', '9월': 'month_09',
                '10월': 'month_10', '11월': 'month_11', '12월': 'month_12'
            }
            df = df.rename(columns=column_mapping)

            numeric_cols = ['year_total'] + [f'month_{i:02d}' for i in range(1, 13)]
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = df[col].astype(str).str.replace(',', '').str.strip()
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

            df['snapshot_id'] = snapshot_id
            df.to_sql('expect_customer', engine, if_exists='append', index=False)
            updated_tables.append('expect_customer')
            total_rows += len(df)

        # 3-5. Plan Category 처리
        if plan_category_file and hasattr(plan_category_file, 'read'):
            # 기존 데이터 삭제
            db.query(PlanCategory).filter(PlanCategory.snapshot_id == snapshot_id).delete()

            # 파일 파싱 및 삽입
            contents = await plan_category_file.read()
            try:
                df = pd.read_csv(io.BytesIO(contents), encoding='utf-8')
            except UnicodeDecodeError:
                df = pd.read_csv(io.BytesIO(contents), encoding='cp949')

            df.columns = df.columns.str.strip()
            column_mapping = {
                '중분류': 'category',
                '중분류명': 'category',
                '2025년': 'year_total',
                '1월': 'month_01', '2월': 'month_02', '3월': 'month_03',
                '4월': 'month_04', '5월': 'month_05', '6월': 'month_06',
                '7월': 'month_07', '8월': 'month_08', '9월': 'month_09',
                '10월': 'month_10', '11월': 'month_11', '12월': 'month_12'
            }
            df = df.rename(columns=column_mapping)

            numeric_cols = ['year_total'] + [f'month_{i:02d}' for i in range(1, 13)]
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = df[col].astype(str).str.replace(',', '').str.strip()
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

            df['snapshot_id'] = snapshot_id
            df.to_sql('plan_category', engine, if_exists='append', index=False)
            updated_tables.append('plan_category')
            total_rows += len(df)

        # 3-6. Actual Sales 처리
        if actual_sales_file and hasattr(actual_sales_file, 'read'):
            # 기존 데이터 삭제
            db.query(ActualSales).filter(ActualSales.snapshot_id == snapshot_id).delete()

            # 파일 파싱 및 삽입
            contents = await actual_sales_file.read()
            try:
                df = pd.read_csv(io.BytesIO(contents), encoding='utf-8')
            except UnicodeDecodeError:
                df = pd.read_csv(io.BytesIO(contents), encoding='cp949')

            df.columns = df.columns.str.strip()
            column_mapping = {
                '고객약호': 'customer_code',
                '중분류명': 'category_name',
                '매출': 'sales_amount',
                '대금청구일': 'invoice_date'
            }
            df = df.rename(columns=column_mapping)
            target_columns = ['customer_code', 'category_name', 'sales_amount', 'invoice_date']
            existing_columns = [col for col in target_columns if col in df.columns]
            df = df[existing_columns]

            if 'sales_amount' in df.columns:
                df['sales_amount'] = df['sales_amount'].astype(str).str.replace(',', '').str.strip()
                df['sales_amount'] = pd.to_numeric(df['sales_amount'], errors='coerce').fillna(0)

            df['snapshot_id'] = snapshot_id
            df.to_sql('actual_sales', engine, if_exists='append', index=False)
            updated_tables.append('actual_sales')
            total_rows += len(df)

        # 4. 커밋
        db.commit()

        return {
            "message": "Snapshot updated successfully",
            "snapshot_id": snapshot_id,
            "updated_tables": updated_tables,
            "rows_updated": total_rows
        }

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()
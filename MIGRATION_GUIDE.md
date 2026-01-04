# FastAPI → Vercel Serverless 마이그레이션 가이드

## 주요 변경 사항

### 1. 아키텍처 변경

#### Before (FastAPI)
```python
# main.py
from fastapi import FastAPI

app = FastAPI()

@app.get("/snapshots")
def get_snapshots():
    return {...}
```

#### After (Vercel Serverless)
```python
# api/snapshots/index.py
from http.server import BaseHTTPRequestHandler

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # 로직
        pass
```

### 2. 데이터베이스 변경

#### Before: SQLite (로컬 파일)
```python
DATABASE_URL = "sqlite:///./data.db"
engine = create_engine(DATABASE_URL)
```

#### After: Supabase (PostgreSQL)
```python
from _lib.supabase import get_supabase_client

supabase = get_supabase_client()
response = supabase.table("snapshots").select("*").execute()
```

### 3. 인증 시스템

#### Before: 없음
- 인증 로직 없이 모든 엔드포인트 공개

#### After: Supabase JWT
```python
from _lib.auth import require_auth, require_admin

class handler(BaseHTTPRequestHandler):
    @require_auth
    def do_GET(self, user):
        # user에 JWT 정보 포함
        pass
```

### 4. 파일 업로드 처리

#### Before: FastAPI의 UploadFile
```python
async def upload_csv(order_file: UploadFile = File(...)):
    contents = await order_file.read()
```

#### After: cgi.FieldStorage
```python
form = cgi.FieldStorage(fp=self.rfile, headers=self.headers, ...)
order_file = form["order_file"]
file_contents = order_file.file.read()
```

## 마이그레이션 체크리스트

### 1. Supabase 설정

- [ ] Supabase 프로젝트 생성
- [ ] 데이터베이스 스키마 생성 (8개 테이블)
  - [ ] users
  - [ ] snapshots
  - [ ] order_data
  - [ ] price_table
  - [ ] plan_customer
  - [ ] expect_customer
  - [ ] plan_category
  - [ ] actual_sales
- [ ] RLS (Row Level Security) 정책 설정
- [ ] 환경변수 확인
  - [ ] SUPABASE_URL
  - [ ] SUPABASE_SERVICE_ROLE_KEY
  - [ ] SUPABASE_JWT_SECRET

### 2. Vercel 배포

- [ ] Vercel 프로젝트 생성
- [ ] GitHub 저장소 연결
- [ ] 환경변수 설정 (위의 3개)
- [ ] 첫 배포 확인

### 3. 프론트엔드 업데이트

- [ ] API_URL 환경변수 업데이트
  ```
  VITE_API_URL=https://your-vercel-app.vercel.app/api
  ```
- [ ] 인증 토큰 헤더 추가
  ```typescript
  headers: {
    'Authorization': `Bearer ${token}`
  }
  ```
- [ ] 응답 형식 변경 처리
  ```typescript
  // Before: response.data
  // After: response.data.data (표준화된 응답)
  ```

## 데이터베이스 스키마

### Supabase 테이블 생성 SQL

```sql
-- 1. users (Supabase Auth와 연동)
create table users (
  id uuid primary key references auth.users(id),
  email text not null,
  role text default 'user' check (role in ('admin', 'user')),
  is_active boolean default true,
  created_at timestamp with time zone default now(),
  updated_at timestamp with time zone default now()
);

-- 2. snapshots
create table snapshots (
  id serial primary key,
  created_at timestamp with time zone default now(),
  description text,
  created_by uuid references users(id)
);

-- 3. order_data
create table order_data (
  id serial primary key,
  snapshot_id integer references snapshots(id) on delete cascade,
  creation_date text,
  customer_code text,
  sales_team text,
  material_code text,
  category_name text,
  backlog_qty numeric,
  unit_price numeric,
  delivery_date text
);

-- 4. price_table
create table price_table (
  id serial primary key,
  snapshot_id integer references snapshots(id) on delete cascade,
  category_code text,
  average_price numeric
);

-- 5. plan_customer
create table plan_customer (
  id serial primary key,
  snapshot_id integer references snapshots(id) on delete cascade,
  customer text,
  year_total numeric,
  month_01 numeric,
  month_02 numeric,
  month_03 numeric,
  month_04 numeric,
  month_05 numeric,
  month_06 numeric,
  month_07 numeric,
  month_08 numeric,
  month_09 numeric,
  month_10 numeric,
  month_11 numeric,
  month_12 numeric
);

-- 6. expect_customer (plan_customer와 동일 구조)
create table expect_customer (
  id serial primary key,
  snapshot_id integer references snapshots(id) on delete cascade,
  customer text,
  year_total numeric,
  month_01 numeric,
  month_02 numeric,
  month_03 numeric,
  month_04 numeric,
  month_05 numeric,
  month_06 numeric,
  month_07 numeric,
  month_08 numeric,
  month_09 numeric,
  month_10 numeric,
  month_11 numeric,
  month_12 numeric
);

-- 7. plan_category
create table plan_category (
  id serial primary key,
  snapshot_id integer references snapshots(id) on delete cascade,
  category text,
  year_total numeric,
  month_01 numeric,
  month_02 numeric,
  month_03 numeric,
  month_04 numeric,
  month_05 numeric,
  month_06 numeric,
  month_07 numeric,
  month_08 numeric,
  month_09 numeric,
  month_10 numeric,
  month_11 numeric,
  month_12 numeric
);

-- 8. actual_sales
create table actual_sales (
  id serial primary key,
  snapshot_id integer references snapshots(id) on delete cascade,
  customer_code text,
  category_name text,
  sales_amount numeric,
  invoice_date text
);

-- 인덱스 생성 (성능 최적화)
create index idx_order_data_snapshot on order_data(snapshot_id);
create index idx_price_table_snapshot on price_table(snapshot_id);
create index idx_plan_customer_snapshot on plan_customer(snapshot_id);
create index idx_expect_customer_snapshot on expect_customer(snapshot_id);
create index idx_plan_category_snapshot on plan_category(snapshot_id);
create index idx_actual_sales_snapshot on actual_sales(snapshot_id);
```

## API 엔드포인트 매핑

| FastAPI | Vercel Serverless | 파일 위치 |
|---------|-------------------|----------|
| `GET /snapshots` | `GET /api/snapshots` | `api/snapshots/index.py` |
| `GET /snapshots/latest` | `GET /api/snapshots/latest` | `api/snapshots/latest.py` |
| `GET /snapshots/{id}` | `GET /api/snapshots/{id}` | `api/snapshots/[id].py` |
| `PATCH /snapshots/{id}` | `PATCH /api/snapshots/{id}` | `api/snapshots/[id].py` |
| `DELETE /snapshots/{id}` (신규) | `DELETE /api/snapshots/{id}` | `api/snapshots/[id].py` |
| `POST /upload` | `POST /api/upload` | `api/upload.py` |

## 테스트 방법

### 1. 로컬 테스트

```bash
# Vercel CLI로 로컬 개발 서버
vercel dev

# 엔드포인트 테스트
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:3000/api/snapshots
```

### 2. Postman/Thunder Client 테스트

#### 인증 토큰 발급
1. Supabase 대시보드 > Authentication > Users
2. 테스트 사용자 생성
3. 프론트엔드에서 로그인하여 토큰 획득
4. 또는 Supabase API로 직접 로그인:
   ```bash
   curl -X POST 'https://YOUR_PROJECT.supabase.co/auth/v1/token?grant_type=password' \
   -H "apikey: YOUR_ANON_KEY" \
   -H "Content-Type: application/json" \
   -d '{"email": "user@example.com", "password": "password"}'
   ```

#### API 테스트
```bash
# 스냅샷 목록 조회
curl -H "Authorization: Bearer YOUR_TOKEN" \
  https://your-app.vercel.app/api/snapshots

# 파일 업로드
curl -X POST https://your-app.vercel.app/api/upload \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "description=Test snapshot" \
  -F "order_file=@order_data.csv" \
  -F "price_file=@price_table.csv" \
  # ... 나머지 파일들
```

## 문제 해결

### 1. 401 Unauthorized
- JWT 토큰이 만료되었거나 유효하지 않음
- `SUPABASE_JWT_SECRET`이 올바르게 설정되었는지 확인

### 2. 403 Forbidden
- Admin 권한이 필요한 엔드포인트
- Supabase에서 사용자 메타데이터에 `role: "admin"` 추가

### 3. 500 Internal Server Error
- Vercel 로그 확인: `vercel logs`
- Supabase 환경변수 확인
- 데이터베이스 스키마 확인

### 4. CORS 오류
- `vercel.json`의 CORS 헤더 설정 확인
- OPTIONS 메서드 핸들러 확인

## 성능 최적화

### 1. Cold Start 최소화
- 불필요한 import 제거
- 전역 변수로 Supabase 클라이언트 캐싱

### 2. 데이터베이스 쿼리 최적화
- 인덱스 활용
- 필요한 컬럼만 select
- 페이지네이션 구현

### 3. 파일 업로드 최적화
- 대용량 파일은 청크로 분할
- 압축 사용 고려

## 다음 단계

1. [ ] 프론트엔드 연동 테스트
2. [ ] 에러 로깅 시스템 추가 (Sentry 등)
3. [ ] 모니터링 설정
4. [ ] 백업 전략 수립
5. [ ] API 문서 자동 생성 (OpenAPI)

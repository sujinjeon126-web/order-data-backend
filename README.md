# Order Data Backend - Vercel Serverless

Vercel Serverless 함수로 구현된 Order Data 백엔드 API

## 프로젝트 구조

```
order-data-backend/
├── api/
│   ├── _lib/                      # 공유 모듈
│   │   ├── auth.py                # 인증 미들웨어 (JWT 검증)
│   │   ├── supabase.py            # Supabase 클라이언트
│   │   └── utils.py               # 유틸리티 함수
│   ├── snapshots/
│   │   ├── index.py               # GET /api/snapshots (전체 목록)
│   │   ├── latest.py              # GET /api/snapshots/latest (최신 스냅샷)
│   │   └── [id].py                # GET/PATCH/DELETE /api/snapshots/{id}
│   └── upload.py                  # POST /api/upload (스냅샷 생성)
├── vercel.json                    # Vercel 배포 설정
├── requirements.txt               # Python 의존성
├── .env.example                   # 환경변수 예시
└── README.md                      # 문서
```

## API 엔드포인트

### 인증
모든 엔드포인트는 `Authorization: Bearer {token}` 헤더가 필요합니다.

| 엔드포인트 | 메서드 | 권한 | 설명 |
|-----------|--------|------|------|
| `/api/snapshots` | GET | user | 스냅샷 목록 조회 |
| `/api/snapshots/latest` | GET | user | 최신 스냅샷 조회 |
| `/api/snapshots/{id}` | GET | user | 특정 스냅샷 조회 |
| `/api/snapshots/{id}` | PATCH | admin | 스냅샷 수정 |
| `/api/snapshots/{id}` | DELETE | admin | 스냅샷 삭제 |
| `/api/upload` | POST | admin | 스냅샷 생성 |

### 응답 형식

#### 성공
```json
{
  "data": { ... },
  "error": null
}
```

#### 실패
```json
{
  "data": null,
  "error": {
    "message": "오류 메시지",
    "code": "ERROR_CODE"
  }
}
```

## 환경 설정

### 1. 환경변수 설정

`.env.example`을 복사하여 `.env` 파일 생성:

```bash
cp .env.example .env
```

`.env` 파일에 실제 값 입력:

```env
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key_here
SUPABASE_JWT_SECRET=your_jwt_secret_here
```

### 2. Vercel 환경변수 설정

Vercel 대시보드에서 환경변수 추가:

1. Vercel 프로젝트 설정 > Environment Variables
2. 위의 3개 환경변수 추가
3. Production, Preview, Development 모두 체크

## 배포

### Vercel CLI 사용

```bash
# Vercel CLI 설치
npm i -g vercel

# 로그인
vercel login

# 배포
vercel

# 프로덕션 배포
vercel --prod
```

### Git 연동 자동 배포

1. Vercel 대시보드에서 "New Project"
2. GitHub 저장소 연결
3. 환경변수 설정
4. Deploy 클릭

## 로컬 개발

Vercel CLI로 로컬 개발 서버 실행:

```bash
# 환경변수 다운로드
vercel env pull .env.local

# 개발 서버 실행
vercel dev
```

## 의존성

- `pandas`: CSV 파싱 및 데이터 처리
- `openpyxl`: Excel 파일 지원
- `supabase`: Supabase Python 클라이언트
- `PyJWT`: JWT 토큰 검증

## 주요 기능

### 인증 시스템
- Supabase JWT 토큰 검증
- `require_auth`: 일반 사용자 인증
- `require_admin`: 관리자 권한 확인

### 파일 업로드
6개 CSV 파일 처리:
1. Order Data (주문 데이터)
2. Price Table (단가 테이블)
3. Plan Customer (고객별 계획)
4. Expect Customer (고객별 예상)
5. Plan Category (카테고리별 계획)
6. Actual Sales (실제 매출)

### 데이터 처리
- UTF-8/CP949 자동 인코딩 감지
- 숫자 컬럼 자동 정리 (쉼표 제거)
- 한글 컬럼명 자동 변환

## 참고 문서

- [CONVENTIONS.md](C:\Users\sujin.jeon\projects\order-data\docs\CONVENTIONS.md) - 프로젝트 컨벤션
- [Vercel Python Runtime](https://vercel.com/docs/runtimes#official-runtimes/python)
- [Supabase Python Client](https://supabase.com/docs/reference/python/introduction)

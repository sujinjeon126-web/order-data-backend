# Vercel 배포 가이드

## 사전 준비

### 1. Supabase 프로젝트 설정

#### 1.1 프로젝트 생성
1. https://supabase.com 접속
2. "New Project" 클릭
3. 프로젝트명, 비밀번호, 리전(Seoul) 설정

#### 1.2 데이터베이스 스키마 생성
1. SQL Editor 열기
2. `MIGRATION_GUIDE.md`의 SQL 스크립트 실행
3. 모든 테이블이 생성되었는지 확인

#### 1.3 인증 설정
1. Authentication > Settings
2. Email 인증 활성화
3. 테스트 사용자 생성:
   - Authentication > Users > "Add user"
   - Email: admin@example.com
   - Password: (강력한 비밀번호)
   - User Metadata에 추가:
     ```json
     {
       "role": "admin"
     }
     ```

#### 1.4 환경변수 확인
프로젝트 Settings > API에서 확인:
- `SUPABASE_URL`: Project URL
- `SUPABASE_SERVICE_ROLE_KEY`: service_role key (Secret!)
- `SUPABASE_JWT_SECRET`: JWT Settings > JWT Secret

### 2. Vercel 계정 설정

1. https://vercel.com 가입/로그인
2. GitHub 계정 연동

## 배포 방법

### 방법 1: Vercel CLI (권장)

#### 1단계: CLI 설치
```bash
npm install -g vercel
```

#### 2단계: 로그인
```bash
vercel login
```

#### 3단계: 프로젝트 연결
```bash
cd C:\Users\sujin.jeon\projects\order-data-backend
vercel
```

프롬프트에 답변:
- Set up and deploy? **Y**
- Which scope? (본인 계정 선택)
- Link to existing project? **N**
- What's your project's name? **order-data-backend**
- In which directory is your code located? **./** (현재 디렉토리)

#### 4단계: 환경변수 설정
```bash
# Production 환경변수 추가
vercel env add SUPABASE_URL production
# 프롬프트에 값 입력

vercel env add SUPABASE_SERVICE_ROLE_KEY production
# 프롬프트에 값 입력

vercel env add SUPABASE_JWT_SECRET production
# 프롬프트에 값 입력

# Preview와 Development 환경에도 동일하게 추가
vercel env add SUPABASE_URL preview
vercel env add SUPABASE_SERVICE_ROLE_KEY preview
vercel env add SUPABASE_JWT_SECRET preview

vercel env add SUPABASE_URL development
vercel env add SUPABASE_SERVICE_ROLE_KEY development
vercel env add SUPABASE_JWT_SECRET development
```

#### 5단계: 프로덕션 배포
```bash
vercel --prod
```

배포 완료 후 URL 확인:
```
✅ Production: https://order-data-backend.vercel.app
```

### 방법 2: Git 연동 자동 배포

#### 1단계: GitHub 저장소 생성
```bash
cd C:\Users\sujin.jeon\projects\order-data-backend
git init
git add .
git commit -m "Initial commit: Vercel serverless backend"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/order-data-backend.git
git push -u origin main
```

#### 2단계: Vercel에서 Import
1. Vercel 대시보드 > "Add New..." > "Project"
2. "Import Git Repository"
3. GitHub에서 저장소 선택
4. Configure Project:
   - Framework Preset: **Other**
   - Root Directory: `./`
   - Build Command: (비워둠)
   - Output Directory: (비워둠)

#### 3단계: 환경변수 설정
1. "Environment Variables" 섹션에서 추가:
   - `SUPABASE_URL`
   - `SUPABASE_SERVICE_ROLE_KEY`
   - `SUPABASE_JWT_SECRET`
2. 각 변수에 대해 Production/Preview/Development 모두 체크

#### 4단계: Deploy
"Deploy" 버튼 클릭

## 배포 후 확인

### 1. 헬스체크
```bash
# 스냅샷 목록 조회 (인증 필요)
curl -H "Authorization: Bearer YOUR_TOKEN" \
  https://order-data-backend.vercel.app/api/snapshots
```

### 2. 로그 확인
```bash
# Vercel CLI로 실시간 로그 확인
vercel logs --follow
```

또는 Vercel 대시보드:
1. 프로젝트 선택
2. "Logs" 탭

### 3. 에러 발생 시
```bash
# 최근 배포 로그 확인
vercel logs

# 특정 배포 로그 확인
vercel logs [deployment-url]
```

## 프론트엔드 연동

### 1. 환경변수 업데이트
`order-data` 프론트엔드 프로젝트의 `.env.local`:
```env
VITE_API_URL=https://order-data-backend.vercel.app/api
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your_anon_key
```

### 2. API 클라이언트 테스트
```typescript
// src/lib/api.ts에서
const API_URL = import.meta.env.VITE_API_URL;

// 스냅샷 목록 조회
const snapshots = await api.get('/snapshots');
console.log(snapshots.data); // { data: [...], error: null }
```

## 업데이트 및 재배포

### CLI 사용 시
```bash
# 코드 수정 후
vercel --prod
```

### Git 연동 시
```bash
git add .
git commit -m "Update: 변경사항 설명"
git push origin main
# 자동으로 Vercel이 배포 시작
```

## 환경별 설정

### Development (로컬)
```bash
# .env 파일 생성 (로컬 개발용)
cp .env.example .env

# Vercel Dev 서버 실행
vercel dev
```

### Preview (PR/Branch)
- GitHub PR 생성 시 자동으로 Preview 배포 생성
- 각 PR마다 고유한 URL 제공
- 예: `https://order-data-backend-git-feature-xyz.vercel.app`

### Production (main branch)
- `main` 브랜치에 push 시 자동 배포
- 또는 `vercel --prod` 명령어로 수동 배포

## 도메인 설정 (선택사항)

### 1. 커스텀 도메인 추가
1. Vercel 프로젝트 > Settings > Domains
2. 도메인 입력 (예: api.yourcompany.com)
3. DNS 레코드 추가 안내 따라하기

### 2. DNS 설정
도메인 제공업체에서:
```
Type: CNAME
Name: api
Value: cname.vercel-dns.com
```

## 모니터링 및 유지보수

### 1. Vercel Analytics
1. 프로젝트 > Analytics 탭
2. 요청 수, 응답 시간, 에러율 확인

### 2. 알림 설정
1. 프로젝트 > Settings > Notifications
2. 배포 실패 시 이메일 알림 설정

### 3. 사용량 확인
1. Account > Usage
2. Serverless 함수 실행 시간 확인
3. 무료 플랜: 100GB-Hours/월

## 문제 해결

### Function Timeout
기본 10초, Pro 플랜에서 최대 60초
```json
// vercel.json
{
  "functions": {
    "api/**/*.py": {
      "maxDuration": 30
    }
  }
}
```

### Cold Start 느림
- 함수 크기 줄이기
- 불필요한 import 제거
- Supabase 클라이언트 캐싱 (이미 구현됨)

### 환경변수 변경 안 됨
```bash
# 환경변수 재배포
vercel env pull .env.production
vercel --prod
```

### CORS 오류
`vercel.json`의 headers 섹션 확인

## 보안 체크리스트

- [ ] `.env` 파일이 `.gitignore`에 포함되어 있는지 확인
- [ ] `SUPABASE_SERVICE_ROLE_KEY`를 절대 프론트엔드에 노출하지 않기
- [ ] Supabase RLS (Row Level Security) 정책 설정
- [ ] Admin 사용자 권한 관리
- [ ] HTTPS만 사용 (Vercel 기본)
- [ ] Rate limiting 고려 (추후 구현)

## 백업 전략

### 1. 코드 백업
- GitHub에 자동 백업됨

### 2. 데이터베이스 백업
Supabase 대시보드:
1. Database > Backups
2. 자동 일일 백업 (Pro 플랜)
3. 수동 백업: "Backup now"

### 3. 환경변수 백업
```bash
# 로컬에 백업
vercel env pull .env.backup
```

## 비용 예상

### Vercel (Hobby - 무료)
- 100GB-Hours/월 함수 실행
- 100GB 대역폭
- 무제한 요청

### Supabase (Free)
- 500MB 데이터베이스
- 1GB 파일 저장소
- 50,000 월간 활성 사용자

업그레이드 필요 시:
- Vercel Pro: $20/월
- Supabase Pro: $25/월

## 참고 링크

- [Vercel Python Runtime](https://vercel.com/docs/runtimes#official-runtimes/python)
- [Vercel CLI Reference](https://vercel.com/docs/cli)
- [Supabase Documentation](https://supabase.com/docs)
- [프로젝트 컨벤션](C:\Users\sujin.jeon\projects\order-data\docs\CONVENTIONS.md)

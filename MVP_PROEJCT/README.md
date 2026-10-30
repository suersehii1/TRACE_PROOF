# TraceProof MVP

장비 소프트웨어 변경 전후의 데이터와 승인 기준을 대조하고, 원본 근거·담당자 검토가 남는 보고서를 만드는 실행 가능한 MVP입니다.

사용자가 지정한 폴더명 **MVP_PROEJCT**를 그대로 사용했습니다. 상위의 빈 `MVP_PROJECT` 폴더와 구분하세요.

## 빠른 실행

Docker Desktop을 **Linux 컨테이너 모드**로 켜고 이 폴더에서 실행합니다. PC에 Node·Python·PostgreSQL을 따로 설치할 필요가 없습니다. 최초 빌드는 Docker 이미지와 패키지를 내려받으므로 인터넷이 필요합니다. 빌드 후 화면·검사·보고서에 외부 AI/API/CDN은 필요하지 않습니다.

```powershell
cd MVP_PROEJCT
docker compose -p traceproof_mvp up -d --build
docker compose -p traceproof_mvp ps
```

- 화면: [http://localhost:8088](http://localhost:8088)
- API 문서: [http://localhost:8088/docs](http://localhost:8088/docs)
- 상태: [http://localhost:8088/api/health](http://localhost:8088/api/health)

또는 이 폴더의 `start.ps1`을 실행하세요. Docker 접속 권한이 없으면 Docker Desktop의 사용자 권한 설정을 확인하고 권한이 있는 터미널에서 실행합니다.

초기 실행 때 모의 장비가 RAW_DATA의 기준·결함·정상 파일을 HTTP로 자동 전송합니다. 데이터가 아직 보이지 않으면 잠시 후 새로고침하거나 장비 데이터 메뉴에서 전송하세요.

## 첫 시연

1. **변경 검증**에서 기준 `v1.0.0`, 비교 `v1.1.0`을 선택하고 검증 실행.
2. 단위·유량 누락·중복 시각·작업 번호·시험 버전 오류와 판단불가 확인.
3. 원본 확인 → 검토자와 의견 입력 → 보류 기록.
4. 비교 버전을 `v1.1.1`로 바꾸고 새로 검증 → 필수 검사 통과 후 검토 승인.
5. 보고서 열기 → 브라우저 인쇄 → PDF 저장. CSV·원본 JSON도 다운로드 가능.

## 구성

```text
휴대폰 / PC
    │ HTTP :8088
    ▼
frontend  Vue 3 → 정적 배포 Nginx
    │ /api (동일 출처 프록시)
    ▼
backend   FastAPI → 규칙 검사 → PostgreSQL
    ▲
    │ HTTP + 장비 전송 토큰
simulator 모의 장비 어댑터 ← RAW_DATA 원본 파일
```

| 경로 | 역할 |
|---|---|
| `compose.yaml` | 4개 컨테이너, 의존 순서, 상태 확인, DB 볼륨 |
| `backend/app/validation.py` | 핵심 검사·승인 가능 여부. 한국어 설명 포함 |
| `backend/app/main.py` | API·원본 수신·검증 실행·검토 저장 |
| `backend/app/database.py` | PostgreSQL 테이블·세션 |
| `backend/app/reports.py` | HTML·CSV 보고서, 출력 문자열 이스케이프 |
| `frontend/src/App.vue` | Vue 3 업무 화면 |
| `frontend/src/components/` | 판정 배지·변경 전후 그래프 |
| `simulator/device.py` | RAW_DATA를 읽어 실제 HTTP 전송 |
| `RAW_DATA/` | 생성기·기준표·데모 원시 JSON |
| `docs/USER_MANUAL.md` | 기능별 사용자 매뉴얼 |
| `docs/SALES_DEMO.md` | 고객 세일즈 시연 순서·설명·질문 |
| `docs/TraceProof_고객시연_여성내레이션.mp4` | 실제 화면·여성 내레이션·한국어 자막의 고객 시연 영상 |
| `docs/DEVELOPER_GUIDE.md` | 데이터 계약·검사 규칙·확장·API |
| `docs/VERIFICATION.md` | 실제 확인한 테스트와 제한 |

## 휴대폰에서 접속

PC와 휴대폰을 같은 신뢰할 수 있는 Wi-Fi/LAN에 연결하세요. PC에서 `ipconfig`로 확인한 IPv4를 사용해 `http://PC주소:8088`로 접속합니다. 휴대폰의 localhost는 PC가 아닙니다. Windows 방화벽이 차단하면 조직 정책에 맞게 개인 네트워크의 8088 접근을 허용해야 합니다. 앱이 방화벽 설정을 자동 변경하지 않습니다.

## 설정과 종료

포트·데모 비밀번호를 바꾸려면 `.env.example`을 `.env`로 복사하고 편집합니다. DB 비밀번호는 이 예제 URL에서 영문·숫자·밑줄·하이픈만 사용하세요. DB 볼륨을 만든 뒤 환경변수만 바꾸면 기존 DB 사용자 비밀번호는 자동 변경되지 않습니다.

```powershell
Copy-Item .env.example .env
docker compose -p traceproof_mvp up -d --build
docker compose -p traceproof_mvp logs --tail 80 backend simulator
docker compose -p traceproof_mvp down
```

`down`은 컨테이너와 네트워크를 중지·제거하지만 DB 볼륨을 유지합니다. `down -v`는 검증·원본·검토 이력을 모두 삭제하므로 데모 초기화를 의도할 때만 사용하세요. 생성기가 RAW_DATA 파일을 다시 만들어도 이미 DB에 저장된 원본이나 기준표는 바뀌지 않습니다.

## 자동 검사

실행 중인 컨테이너에서 단위·통합 테스트를 수행합니다. 통합 시험은 PostgreSQL 트랜잭션으로 시험 변경을 되돌립니다.

```powershell
docker compose -p traceproof_mvp exec -T backend python -m pytest -q -p no:cacheprovider
```

브라우저 테스트 스크립트는 `scripts/ui_smoke.cjs`입니다. 별도의 Node/Playwright·Chrome이 있는 개발 환경에서 실행하며 Docker 실행의 필수 조건이 아닙니다. 사용법은 개발자 가이드를 참고하세요.

## MVP 범위

실제 동작: 원본 수신·업로드, 해시 기반 중복 방지, 기준/수정 비교, 검사 근거, 정상/결함 판정, 보류/승인, 검토 이력, HTML·CSV 보고서, 원본 보존, 모바일 화면.

아직 없음: 실제 SECS/GEM·EDA 드라이버, 사용자 로그인·역할별 권한·전자서명, 다고객 격리, 운영 TLS, 기준표 편집·승인, 대용량 비동기 처리, DB 스키마 마이그레이션, AI 원인 분석, 고객 인수 인증. 현재는 신뢰하는 로컬/LAN에서 사용하는 시연용이며 인터넷 공개·실제 생산 판정용으로 배포하지 않습니다.

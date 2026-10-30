# 개발자 가이드

## 기술 선택

Vue 3 + Vite 정적 화면, FastAPI + SQLAlchemy + psycopg, PostgreSQL 16, Python 표준 라이브러리 기반 장비 시뮬레이터를 사용합니다. 이 업무는 규칙 기반 수치·문맥 대조와 API 중심이라 FastAPI가 적합합니다. 처음부터 LLM·분산 큐·별도 시계열 DB를 넣지 않았습니다.

## 데이터 흐름과 경계

`RAW_DATA/*.json → simulator/device.py → POST /api/device/releases → PostgreSQL releases → POST /api/validations → 검증 스냅샷 → review/report`

화면의 장비 전송 버튼은 backend에서 simulator 내부 HTTP를 호출하고, simulator가 다시 장비 수신 API로 파일을 보냅니다. 장비 토큰은 브라우저에 전달하지 않습니다. 파일 업로드는 같은 저장 로직을 사용하지만 source가 UPLOAD입니다.

수신 시 JSON 형식은 Pydantic으로 검증합니다. 시차 누락·단위 누락·값 없음처럼 품질 검사에 필요한 결함은 무조건 삭제하지 않고 보존한 뒤 판단불가로 표시합니다. NaN·Infinity는 거부합니다. 원본 문자열과 SHA-256을 함께 저장하고 같은 해시를 unique 제약으로 중복 방지합니다.

## 테이블

| 테이블 | 주요 데이터 |
|---|---|
| equipment | 장비 식별과 모델·위치 |
| profiles | 승인 항목표 JSON, 식별자 |
| releases | 원본 문자열·구조화 측정값·버전·해시·전송 경로 |
| validations | 기준/비교 ID·기준표 스냅샷·판정·검토 이력 |

원본과 검증 결과를 수정하는 API는 없습니다. 검토는 기존 이벤트에 append하는 방식이며 PostgreSQL의 행 잠금으로 동시 검토 시 이력 소실을 막습니다. DB 관리자가 직접 수정하는 것까지 방지하는 불변 감사 저장소는 아닙니다.

## 핵심 검사 설계

`validation.py`는 DB·HTTP와 분리된 순수 함수입니다. `inspect_release()`로 각 버전을 검사하고 `compare_releases()`로 동일 장비·시나리오인지 확인합니다. 기준 데이터도 검사하여 잘못된 기준을 정상으로 믿지 않습니다.

- 검사 하나에 항목 ID·규칙·상태·기대 기준·관측 결과·원본 행·필수 여부를 남깁니다.
- 모든 필수 검사가 PASS이고 기준도 사용 가능해야 approvable=true입니다.
- 결측·시차 없음·모호한 연결은 임의 보정하지 않습니다.
- 시간은 수신 배열의 원래 순서로 비교합니다. 정렬하면 역전·중복이 가려집니다.
- 단위가 다르면 수치 범위 판정은 유보합니다. 자동 단위 변환으로 결함을 숨기지 않습니다.
- 진동처럼 범위를 합의하지 않은 검사는 NOT_TESTED·required=false로 남깁니다.
- 기대 순번·센서 기준이 없는 상태에서 실제 센서 결손·물리 정확도를 확정하지 않습니다.

새 규칙은 독립 함수 또는 검사 블록으로 추가하고 정상·오류·판단불가의 표본과 승인 경계 시험을 함께 추가합니다. 설명만 바꾸지 말고 ENGINE_VERSION을 올려 결과에 남깁니다.

## API

| 메서드·경로 | 설명 |
|---|---|
| GET /api/health | PostgreSQL SELECT 1 포함 상태 |
| GET /api/equipment, /api/profiles | 장비·기준 목록 |
| GET /api/releases | 최근 100개 원본 메타정보 |
| GET /api/releases/{id} | 구조화 원본·메타정보 |
| GET /api/releases/{id}/raw | 보존한 원본 JSON |
| POST /api/releases/upload | multipart file JSON 업로드 |
| POST /api/device/releases | Bearer 장비 토큰 + 원본 JSON 수신 |
| POST /api/demo/send | baseline/faulty/healthy 시나리오 전송 지시 |
| POST /api/validations | baseline_id·candidate_id·profile_id로 비교 |
| GET /api/validations, /{id} | 최근 50개 검증·상세 |
| POST /api/validations/{id}/review | disposition·reviewer·note로 검토 |
| GET /api/validations/{id}/report | HTML 보고서 |
| GET /api/validations/{id}/checks.csv | UTF-8 BOM 검사 CSV |

Swagger UI는 /docs입니다. 기본 FastAPI Swagger 자산은 CDN을 사용하므로 API 문서 화면은 인터넷이 필요할 수 있습니다. 업무용 Vue 화면에는 CDN이 없습니다. 폐쇄망 API 문서가 필요하면 Swagger 자산도 로컬로 묶어야 합니다.

## 실제 장비 통신 확장

실제 어댑터는 장비 로그·SECS/GEM·EDA·수집 API를 읽고 RAW_DATA/README.md의 표준 JSON으로 변환해 `/api/device/releases`에 전송합니다. 현재 구현은 장비 제어 명령을 받지 않습니다. 프로토콜 엔진을 이 검사 모듈에 섞지 마세요.

장비별 인증키, 수집시각/원천시각/순번, 안전한 버퍼링·재전송, 시계 동기화 상태, 원본 파일 보관 계약을 다음 단계에 설계해야 합니다. 현재 5MB/20,000표본 한도를 고속 스트리밍으로 오해하지 않습니다. 대용량은 객체 저장소·분할 수신·백그라운드 작업·작업 상태 API로 확장할 수 있으나 별도 부하 시험이 필요합니다.

## 기준표 변경

`profile.json`은 DB 최초 생성 시 한 번 등록합니다. 파일만 편집하고 재기동해도 기존 기준은 바뀌지 않습니다. 이는 이전 기준의 무단 변경을 피하기 위한 동작입니다. MVP에는 새 기준을 등록·승인하는 API가 없습니다. 개발 중에는 별도의 테스트 DB로 새 기준을 검증하고, 운영 기능으로 확장할 때 새 ID/버전·승인 이력·적용일을 추가하세요. 검증 결과에는 당시 profile_snapshot이 보존됩니다.

## 테스트

```powershell
docker compose -p traceproof_mvp exec -T backend python -m pytest -q -p no:cacheprovider
```

선택적인 브라우저 시험은 Node 22 이상·Playwright·Chrome이 있는 개발 PC에서 가능합니다. playwright 모듈 경로가 프로젝트 모듈 검색 경로에 없으면 환경변수로 지정합니다. 브라우저가 없으면 먼저 설치해야 하며, 앱 실행에는 필요하지 않습니다.

```powershell
$env:PLAYWRIGHT_MODULE='설치된 playwright 모듈의 절대 경로'
$env:UI_BROWSER='Chrome 실행 파일의 절대 경로'
$env:BASE_URL='http://localhost:8088'
node scripts/ui_smoke.cjs
```

스크립트는 실제 DB에 데모 검증·검토 기록을 추가하고 docs/screenshots에 화면을 저장합니다. 단위/API 테스트는 외부 PostgreSQL 트랜잭션으로 시험 데이터를 되돌립니다.

## 운영 확장 시 주의할 경계

검토자 이름은 직접 입력값이며 인증 계정이 아닙니다. 사용자 로그인·역할 권한·고객별 격리·TLS·키 회전·전자서명·감사 로그 외부 보관·Alembic 마이그레이션·백업 복구를 운영 범위에서 설계하세요. 이 MVP는 기본 예제 토큰과 비밀번호를 사용하며 생산망 직접 연결을 하지 않습니다. 장비 토큰은 원본 수신 API만 보호하고 화면용 API에 사용자 인증은 없습니다.

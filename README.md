# TraceProof

반도체·OLED 제조 장비의 소프트웨어 변경 전후 데이터를 승인 기준과 대조하고, 원본 근거와 담당자 검토를 남기는 MVP입니다.

프로젝트 소스와 자료는 **[MVP_PROEJCT](MVP_PROEJCT/README.md)** 아래에 있습니다. 폴더명은 프로젝트에서 사용한 표기를 유지했습니다.

## 실행

Docker Desktop을 Linux 컨테이너 모드로 시작한 뒤 실행합니다.

```bash
git clone https://github.com/suersehii1/TRACE_PROOF.git
cd TRACE_PROOF/MVP_PROEJCT
docker compose -p traceproof_mvp up -d --build
```

화면: **http://localhost:8088** · API 문서: http://localhost:8088/docs

Vue 3·Nginx, FastAPI, PostgreSQL, RAW_DATA 기반 모의 장비가 각각 컨테이너로 실행됩니다. 처음 시작하면 모의 장비가 기준·결함·정상 수정 데이터 3종을 자동 전송합니다.

## 주요 기능

- JSON 원본 업로드와 모의 장비의 HTTP 전송, SHA-256 중복 방지.
- 버전·표본·단위·수치 범위·시각 간격·작업 번호·챔버 연결 검사.
- 통과·실패·판단불가·미실시 구분, 원본 행과 변경 전후 추이 확인.
- 필수 문제가 남으면 승인 차단, 보류·승인과 검토 이력 저장.
- HTML 보고서, CSV·원본 JSON 다운로드, 브라우저 PDF 저장.
- PC·휴대폰에 대응하는 화면.

## 매뉴얼과 시연 영상

| 자료 | 링크 |
|---|---|
| 실행·설정·종료 | [프로젝트 README](MVP_PROEJCT/README.md) |
| 기능 사용 설명 | [사용자 매뉴얼](MVP_PROEJCT/docs/USER_MANUAL.md) |
| 고객 세일즈 시연 | [시연 대본과 설명](MVP_PROEJCT/docs/SALES_DEMO.md) |
| 시연 동영상 | [MP4 · 약 3분 28초 · 한국어 여성 AI 음성·자막](MVP_PROEJCT/docs/TraceProof_고객시연_여성내레이션.mp4) |
| 영상 장면별 대본 | [영상 대본](MVP_PROEJCT/docs/VIDEO_SCRIPT.md) |
| 구조·API·통신 확장 | [개발자 가이드](MVP_PROEJCT/docs/DEVELOPER_GUIDE.md) |
| 테스트와 한계 | [검증 기록](MVP_PROEJCT/docs/VERIFICATION.md) |

## 테스트

```bash
cd MVP_PROEJCT
docker compose -p traceproof_mvp exec -T backend python -m pytest -q -p no:cacheprovider
```

검사 엔진과 PostgreSQL API 시험 12개, 데스크톱·모바일 에뮬레이션 시연을 확인했습니다. 실제 고객 공정·장비의 성능이나 고주파·대량 데이터 부하를 검증한 결과는 아닙니다.

## 적용 범위

가상 데이터로 기능을 설명하는 로컬 시연용 MVP입니다. 실제 SECS/GEM·EDA 연결은 어댑터 구조까지만 있으며, 사용자 로그인·권한 분리·TLS·운영용 기준표 승인·DB 마이그레이션은 별도 개발 범위입니다. 검토자 이름은 직접 입력값으로 전자서명이 아닙니다. 기본 비밀번호·장비 토큰은 데모 예제 값입니다.

`.env`, DB 데이터, 가상환경, node_modules, 임시 녹화·음성 제작 파일은 저장소에 포함하지 않습니다.

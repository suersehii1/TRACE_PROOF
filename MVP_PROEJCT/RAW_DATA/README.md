# 가상 장비 RAW_DATA

모든 데이터는 소프트웨어로 생성한 데모이며 실제 고객·설비·수율 데이터가 아닙니다.

| 파일 | 설명 |
|---|---|
| `profile.json` | 5개 항목의 단위·표본·간격·범위·작업 및 챔버 기준 |
| `baseline.json` | 기준 v1.0.0, 5개 항목×6표본=30개 |
| `faulty.json` | 결함 v1.1.0, FLOW 6개 누락으로 24표본 |
| `healthy.json` | 정상 수정 v1.1.1, 30표본 |
| `generate_demo.py` | 위 파일을 재생성하는 한국어 주석의 생성기 |

결함 파일에는 온도 단위 F/C 충돌, 압력 중복시각·간격 변화, FLOW 누락, RF 전력 범위·Run ID 오류, 진동 시각의 시차 누락, 이전 SW 버전의 시험 증거가 있습니다. 진동 수치의 허용 범위는 의도적으로 미지정이어서 정상 버전에서도 그 범위 검사는 비필수 미실시입니다.

첫 실행은 simulator가 파일을 읽어 backend로 전송합니다. backend가 직접 원시 JSON을 DB에 몰래 넣는 방식이 아닙니다. profile.json만 최초 기준표로 등록합니다.

장비 메뉴의 JSON 업로드에도 같은 파일을 사용할 수 있습니다. 같은 바이트의 파일은 기존 자료를 반환합니다. 새 데이터로 보려면 파일의 실제 내용·label·버전을 변경하세요. 파일 이름만 바꾸면 같은 원본입니다.

원본은 최대 5MB·20,000개 표본이며 UTF-8 JSON이어야 합니다. CSV 파일 직접 반입은 MVP에 없습니다. 고객 CSV는 추후 어댑터에서 아래 계약으로 변환합니다.

```json
{
  "manifest": {
    "equipment_id": "EQ-DEMO-01",
    "label": "새 수정 버전",
    "software_version": "1.2.0",
    "config_version": "CFG-004",
    "scenario": "NORMAL_RUN",
    "tester_software_version": "1.2.0"
  },
  "measurements": [
    {
      "parameter_id": "TEMP_PV",
      "timestamp": "2026-10-30T09:00:00+09:00",
      "value": 175,
      "unit": "C",
      "run_id": "RUN-001",
      "chamber": "CH-A"
    }
  ]
}
```

위 최소 예시는 형식 설명용입니다. 정상 판정에는 profile.json의 모든 필수 항목과 최소 6개 표본이 필요합니다. timestamp·unit·run_id·chamber가 없으면 임의 추정으로 채우지 않고 검사에서 판단불가로 남깁니다.

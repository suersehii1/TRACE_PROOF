# 이 스크립트가 있는 폴더를 기준으로 실행하므로 한글 경로·공백 경로도 처리한다.
$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
    docker version | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Docker Desktop을 Linux 컨테이너 모드로 시작하고 다시 실행하세요.' }
    docker compose -p traceproof_mvp up -d --build
    if ($LASTEXITCODE -ne 0) { throw '컨테이너 실행에 실패했습니다. 위 로그와 포트 사용 상태를 확인하세요.' }
    docker compose -p traceproof_mvp ps
    Write-Host '기본 접속 주소: http://localhost:8088 (.env에서 WEB_PORT를 바꿨다면 해당 포트 사용)'
    Write-Host '고객 시연: docs/SALES_DEMO.md / 사용자 매뉴얼: docs/USER_MANUAL.md'
} finally {
    Pop-Location
}

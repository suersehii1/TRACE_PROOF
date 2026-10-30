"""FastAPI 진입점. 장비 어댑터는 /api/device/releases 계약만 지키면 교체할 수 있다."""
import hashlib
import json
import os
import secrets
import time
from contextlib import asynccontextmanager
from pathlib import Path
from datetime import datetime, timezone
import httpx
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Request
from fastapi.responses import HTMLResponse, Response
from pydantic import ValidationError
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session
from .database import Base, engine, SessionLocal, get_db, Equipment, Profile, Release, Validation
from .schemas import ReleasePayload, CompareRequest, ReviewRequest, DemoRequest
from .validation import compare_releases
from .reports import html_report, csv_report

MAX_BYTES = 5 * 1024 * 1024
RAW_DATA_DIR = Path(os.getenv('RAW_DATA_DIR', Path(__file__).resolve().parents[2] / 'RAW_DATA'))


@asynccontextmanager
async def lifespan(app):
    # Compose의 healthcheck 외에도 DB 재기동/초기 연결 지연에 짧게 대응한다.
    for attempt in range(30):
        try:
            Base.metadata.create_all(engine)
            break
        except OperationalError:
            if attempt == 29:
                raise
            time.sleep(1)
    with SessionLocal() as db:
        if not db.get(Equipment, 'EQ-DEMO-01'):
            db.add(Equipment(id='EQ-DEMO-01', name='데모 식각 장비', model='TP-ETCH 100', location='가상 출하 검증실'))
        if not db.get(Profile, 'PROFILE-DEMO-V1'):
            db.add(Profile(id='PROFILE-DEMO-V1', document=json.loads((RAW_DATA_DIR / 'profile.json').read_text(encoding='utf-8'))))
        db.commit()
    yield


app = FastAPI(title='TraceProof 장비 데이터 변경 검증', version='1.0.0', lifespan=lifespan,
              description='데모용 파일 기반 검사 API. 실제 장비 제어/SEMI 인증 기능은 포함하지 않습니다.')


def release_info(r):
    return dict(id=r.id, equipment_id=r.equipment_id, label=r.label, software_version=r.software_version,
                config_version=r.payload['manifest']['config_version'], scenario=r.payload['manifest']['scenario'],
                source=r.source, filename=r.filename, sha256=r.sha256, measurement_count=len(r.payload['measurements']), created_at=r.created_at)


def validation_info(v):
    return dict(id=v.id, baseline_id=v.baseline_id, candidate_id=v.candidate_id, profile_id=v.profile_id,
                profile_snapshot=v.profile_snapshot, result=v.result, review_status=v.review_status,
                reviews=v.reviews, created_at=v.created_at)


def must_get(db, model, id):
    result = db.get(model, id)
    if result is None:
        raise HTTPException(404, '요청한 자료를 찾을 수 없습니다.')
    return result


def save_release(raw: bytes, filename: str, source: str, db):
    if len(raw) > MAX_BYTES:
        raise HTTPException(413, '파일은 5MB 이하여야 합니다.')
    try:
        content = raw.decode('utf-8')
        payload = ReleasePayload.model_validate(json.loads(content.lstrip('\ufeff'))).model_dump()
    except (UnicodeDecodeError, json.JSONDecodeError, ValidationError) as exc:
        raise HTTPException(422, 'UTF-8 JSON 형식 또는 필수 필드가 올바르지 않습니다. RAW_DATA 예제를 확인하세요.') from exc
    manifest = payload['manifest']
    if not db.get(Equipment, manifest['equipment_id']):
        raise HTTPException(422, '등록되지 않은 장비입니다. 데모 장비 ID는 EQ-DEMO-01입니다.')
    digest = hashlib.sha256(raw).hexdigest()
    existing = db.scalar(select(Release).where(Release.sha256 == digest))
    if existing:
        return dict(release=release_info(existing), reused=True)
    record = Release(equipment_id=manifest['equipment_id'], label=manifest['label'], software_version=manifest['software_version'],
                     source=source, filename=Path(filename.replace('\\', '/')).name[:200], sha256=digest,
                     raw_content=content, payload=payload)
    db.add(record)
    try:
        db.commit()
    except IntegrityError:
        # 동일 파일을 장비와 사용자가 동시에 전송해도 중복 데이터를 만들지 않는다.
        db.rollback()
        existing = db.scalar(select(Release).where(Release.sha256 == digest))
        if existing:
            return dict(release=release_info(existing), reused=True)
        raise
    db.refresh(record)
    return dict(release=release_info(record), reused=False)


@app.get('/api/health')
def health(db: Session = Depends(get_db)):
    db.execute(text('SELECT 1'))
    return {'status': 'ok', 'database': 'postgresql', 'version': '1.0.0'}


@app.get('/api/equipment')
def equipment(db: Session = Depends(get_db)):
    return [dict(id=e.id, name=e.name, model=e.model, location=e.location) for e in db.scalars(select(Equipment)).all()]


@app.get('/api/profiles')
def profiles(db: Session = Depends(get_db)):
    return [dict(id=p.id, **p.document) for p in db.scalars(select(Profile)).all()]


@app.get('/api/releases')
def releases(db: Session = Depends(get_db)):
    return [release_info(r) for r in db.scalars(select(Release).order_by(Release.id.desc()).limit(100)).all()]


@app.get('/api/releases/{release_id}')
def release_detail(release_id: int, db: Session = Depends(get_db)):
    r = must_get(db, Release, release_id)
    return {**release_info(r), 'payload': r.payload}


@app.get('/api/releases/{release_id}/raw')
def raw_release(release_id: int, db: Session = Depends(get_db)):
    r = must_get(db, Release, release_id)
    return Response(r.raw_content.encode('utf-8'), media_type='application/json',
                    headers={'Content-Disposition': f'attachment; filename="release-{r.id}.json"'})


@app.post('/api/releases/upload')
async def upload(file: UploadFile = File(...), db: Session = Depends(get_db)):
    raw = await file.read(MAX_BYTES + 1)
    return save_release(raw, file.filename or 'upload.json', 'UPLOAD', db)


@app.post('/api/device/releases')
async def ingest(request: Request, db: Session = Depends(get_db)):
    expected = 'Bearer ' + os.getenv('DEVICE_TOKEN', 'traceproof_device_demo_only')
    if not secrets.compare_digest(request.headers.get('Authorization', ''), expected):
        raise HTTPException(401, '장비 전송 인증에 실패했습니다.')
    # Content-Length를 신뢰하지 않고 스트림을 읽는 동안에도 크기를 제한한다.
    parts, total = [], 0
    async for part in request.stream():
        total += len(part)
        if total > MAX_BYTES:
            raise HTTPException(413, '장비 전송은 5MB 이하여야 합니다.')
        parts.append(part)
    return save_release(b''.join(parts), request.headers.get('X-Filename', 'device.json'), 'DEVICE', db)


@app.post('/api/demo/send')
async def demo_send(body: DemoRequest):
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(os.getenv('SIMULATOR_URL', 'http://localhost:8001') + '/send', json=body.model_dump())
        response.raise_for_status()
        return response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(502, '장비 시뮬레이터에 연결할 수 없습니다. simulator 컨테이너 상태를 확인하세요.') from exc


@app.post('/api/validations')
def validate(body: CompareRequest, db: Session = Depends(get_db)):
    if body.baseline_id == body.candidate_id:
        raise HTTPException(422, '기준과 비교 데이터는 서로 달라야 합니다.')
    baseline = must_get(db, Release, body.baseline_id)
    candidate = must_get(db, Release, body.candidate_id)
    profile = must_get(db, Profile, body.profile_id)
    try:
        result = compare_releases(baseline.payload, candidate.payload, profile.document)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    v = Validation(baseline_id=baseline.id, candidate_id=candidate.id, profile_id=profile.id,
                   profile_snapshot=profile.document, result=result, review_status='PENDING', reviews=[])
    db.add(v)
    db.commit()
    db.refresh(v)
    return validation_info(v)


@app.get('/api/validations')
def validations(db: Session = Depends(get_db)):
    return [validation_info(v) for v in db.scalars(select(Validation).order_by(Validation.id.desc()).limit(50)).all()]


@app.get('/api/validations/{validation_id}')
def validation_detail(validation_id: int, db: Session = Depends(get_db)):
    return validation_info(must_get(db, Validation, validation_id))


@app.post('/api/validations/{validation_id}/review')
def review(validation_id: int, body: ReviewRequest, db: Session = Depends(get_db)):
    # 동시에 검토해도 앞선 검토 이력이 사라지지 않도록 행 단위로 잠근다.
    v = db.scalar(select(Validation).where(Validation.id == validation_id).with_for_update())
    if v is None:
        raise HTTPException(404, '검증을 찾을 수 없습니다.')
    if not body.reviewer.strip() or not body.note.strip():
        raise HTTPException(422, '검토자와 검토 의견을 입력하세요.')
    if body.disposition == 'APPROVED' and not v.result['approvable']:
        raise HTTPException(409, '필수 실패·판단불가·미실시 또는 기준 데이터 문제가 있어 승인할 수 없습니다. 수정 후 새 검증을 실행하세요.')
    v.review_status = body.disposition
    v.reviews = [*v.reviews, dict(disposition=body.disposition, reviewer=body.reviewer.strip(),
                                 note=body.note.strip(), at=datetime.now(timezone.utc).isoformat())]
    db.commit()
    return validation_info(v)


@app.get('/api/validations/{validation_id}/report', response_class=HTMLResponse)
def report(validation_id: int, db: Session = Depends(get_db)):
    v = must_get(db, Validation, validation_id)
    return HTMLResponse(html_report(v, must_get(db, Release, v.baseline_id), must_get(db, Release, v.candidate_id)),
                        headers={'Content-Security-Policy': "default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'"})


@app.get('/api/validations/{validation_id}/checks.csv')
def report_csv(validation_id: int, db: Session = Depends(get_db)):
    v = must_get(db, Validation, validation_id)
    return Response(csv_report(v), media_type='text/csv; charset=utf-8',
                    headers={'Content-Disposition': f'attachment; filename="validation-{v.id}.csv"'})

"""RAW_DATA에 있는 가상 장비가 HTTP로 MVP에 자료를 밀어 넣는 어댑터.

실제 SECS/GEM·EDA 수집기는 추후 이 모듈 대신 구현한다. 현재는 원본 JSON을
그대로 전송하며, 서버가 부여한 해시로 재전송 중복을 방지한다.
"""
import json
import logging
import os
import threading
import time
import urllib.request
import urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
BACKEND = os.getenv('BACKEND_URL', 'http://localhost:8000')
RAW = Path(os.getenv('RAW_DATA_DIR', '../RAW_DATA'))
TOKEN = os.getenv('DEVICE_TOKEN', 'traceproof_device_demo_only')
SCENARIOS = {'baseline', 'faulty', 'healthy'}


def send(scenario):
    if scenario not in SCENARIOS:
        raise ValueError('지원하지 않는 데모 시나리오입니다.')
    raw = (RAW / f'{scenario}.json').read_bytes()
    request = urllib.request.Request(BACKEND + '/api/device/releases', data=raw, method='POST', headers={
        'Content-Type': 'application/json', 'Authorization': 'Bearer ' + TOKEN, 'X-Filename': scenario + '.json'})
    with urllib.request.urlopen(request, timeout=15) as response:
        result = json.load(response)
    logging.info('장비 전송 %s → release #%s (중복=%s)', scenario, result['release']['id'], result['reused'])
    return result


class Handler(BaseHTTPRequestHandler):
    def respond(self, code, payload):
        raw = json.dumps(payload, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        self.respond(200, {'status': 'ok', 'mode': 'raw-data-device'}) if self.path == '/health' else self.respond(404, {'error': 'not found'})

    def do_POST(self):
        if self.path != '/send':
            return self.respond(404, {'error': 'not found'})
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if length < 1 or length > 1024:
                return self.respond(413, {'error': 'invalid request size'})
            scenario = json.loads(self.rfile.read(length))['scenario']
            self.respond(200, send(scenario))
        except (ValueError, KeyError, urllib.error.URLError, OSError) as exc:
            logging.exception('장비 전송 실패')
            self.respond(502, {'error': str(exc)})


def initial_send():
    # 시연 시작 시 빈 화면 대신 준비된 장비 데이터 3종이 보이도록 최초 전송한다.
    for attempt in range(15):
        try:
            for scenario in ['baseline', 'faulty', 'healthy']:
                send(scenario)
            return
        except (OSError, ValueError) as exc:
            logging.warning('초기 전송 재시도 %s: %s', attempt + 1, exc)
            time.sleep(2)
    logging.error('초기 전송 미완료. 화면의 장비 전송 버튼으로 다시 시도하세요.')


if __name__ == '__main__':
    if os.getenv('AUTO_SEND', 'true').lower() == 'true':
        threading.Thread(target=initial_send, daemon=True).start()
    ThreadingHTTPServer(('0.0.0.0', 8001), Handler).serve_forever()

/* 실제 실행 중인 MVP를 녹화한다. 시연용 화면 강조만 브라우저에 주입하고 제품 소스는 바꾸지 않는다. */
const fs = require('node:fs')
const path = require('node:path')
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright')
const project = path.resolve(__dirname, '../..')
const work = path.resolve(project, '../tmp/sales_video')
const base = process.env.BASE_URL || 'http://localhost:8088'
const scenes = JSON.parse(fs.readFileSync(path.join(work, 'timing.json'), 'utf8'))
const clips = path.join(work, 'clips')
fs.mkdirSync(clips, { recursive: true })
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms))
const onlyScenes = process.env.ONLY_SCENES?.split(',')
const previousCheck = onlyScenes ? JSON.parse(fs.readFileSync(path.join(work, 'capture-check.json'), 'utf8')) : {}
let browser, faultyId = previousCheck.faultyId, healthyId = previousCheck.healthyId
const errors = []
const recording = onlyScenes ? JSON.parse(fs.readFileSync(path.join(work, 'recordings.json'), 'utf8')).filter(r => !onlyScenes.includes(r.id)) : []

function slide(id) {
  const content = {
    intro: `<div class="eyebrow">EQUIPMENT DATA ASSURANCE</div><h1>장비는 바뀌어도<br>데이터의 기준은<br><em>지켜져야 합니다.</em></h1><p>장비 데이터 변경 검증과 근거가 남는 검토</p><div class="flow"><span>원본 데이터</span><b>→</b><span>변경 검증</span><b>→</b><span>검토 보고서</span></div>`,
    problem: `<div class="eyebrow">고객 업무의 문제</div><h1>통신은 연결됐는데,<br><em>데이터도 그대로일까요?</em></h1><p>로그 · 데이터 항목표 · 시험 결과를 따로 확인할 때</p><div class="cards"><article><small>01</small><h2>단위와 정의의 변화</h2><p>섭씨 기준인데 화씨로 전달</p></article><article><small>02</small><h2>누락과 시간 불일치</h2><p>필수 항목 누락 · 중복 시각</p></article><article><small>03</small><h2>근거 자료의 재요청</h2><p>다른 버전 결과 · 설명 부족</p></article></div><div class="caption">업무 문제를 설명하기 위한 개념 화면</div>`,
    closing: `<div class="eyebrow">장비 한 모델부터 시작하세요</div><h1>반복 확인 업무를 줄이고,<br><em>검토의 근거를 남기세요.</em></h1><p>기존 시험 도구를 유지하면서 데이터 대조와 자료 정리를 보완합니다.</p><div class="cards"><article><small>CHECK</small><h2>확인 범위를 명확하게</h2><p>합의한 기준과 미확인 항목</p></article><article><small>SHARE</small><h2>같은 원본으로 소통</h2><p>기대 기준 · 관측값 · 데이터 행</p></article><article><small>REVIEW</small><h2>조치와 검토를 기록</h2><p>보류 · 재검증 · 보고서</p></article></div><div class="caption">실제 자료로 업무시간과 도입 효과를 확인하는 제한된 실증부터</div>`
  }[id]
  return `<!doctype html><html lang="ko"><meta charset="UTF-8"><style>*{box-sizing:border-box}body{margin:0;font-family:'Malgun Gothic',sans-serif;background:#102c40;color:#fff;width:1600px;height:820px;overflow:hidden}.canvas{position:relative;padding:64px 86px;height:100%;background:radial-gradient(ellipse at 92% 10%,#18586a 0,transparent 55%)}.eyebrow{color:#7cd6c5;font-size:19px;letter-spacing:3px;font-weight:bold}h1{font-size:61px;line-height:1.35;letter-spacing:-2px;margin:24px 0 20px}em{font-style:normal;color:#70d3bd}p{font-size:25px;color:#b4c8d3;line-height:1.6;margin:0}.flow{display:flex;gap:22px;align-items:center;margin-top:38px;font-size:23px}.flow span{border:1px solid #537586;border-radius:12px;padding:17px 25px}.flow b{color:#76cdbb}.cards{display:flex;gap:22px;margin-top:33px}.cards article{background:#1e4053;border:1px solid #365d70;border-radius:14px;padding:27px;width:31.6%}.cards small{color:#7cd6c5;font-size:16px;letter-spacing:2px}.cards h2{font-size:26px;margin:14px 0 9px}.cards p{font-size:20px}.caption{font-size:17px;color:#88a6b8;margin-top:25px}</style><div class="canvas">${content}</div></html>`
}

async function instrument(page) {
  await page.evaluate(() => {
    document.querySelector('#video-cursor')?.remove()
    const cursor = document.createElement('div')
    cursor.id = 'video-cursor'
    cursor.style.cssText = 'position:fixed;left:-80px;top:-80px;width:25px;height:25px;border:3px solid #13a995;border-radius:50%;background:#13a99526;box-shadow:0 0 0 6px #13a99517;pointer-events:none;z-index:2147483647;transition:left .45s ease,top .45s ease,transform .15s ease'
    document.body.appendChild(cursor)
    document.documentElement.style.scrollBehavior = 'smooth'
  })
}

async function point(page, locator, click = false) {
  await locator.scrollIntoViewIfNeeded()
  const box = await locator.boundingBox()
  if (!box) throw new Error('녹화할 대상이 화면에 없습니다.')
  await page.evaluate(({ x, y }) => {
    const cursor = document.querySelector('#video-cursor')
    if (cursor) { cursor.style.left = `${x - 12}px`; cursor.style.top = `${y - 12}px` }
  }, { x: box.x + box.width / 2, y: box.y + box.height / 2 })
  await sleep(550)
  if (click) { await locator.click(); await sleep(450) }
}

async function highlight(locator) {
  await locator.evaluate(el => { el.style.outline = '3px solid #27ae9b'; el.style.outlineOffset = '5px'; el.style.transition = 'outline .3s' })
  await sleep(1400)
  await locator.evaluate(el => { el.style.outline = ''; el.style.outlineOffset = '' })
}

async function ready(page) {
  await page.getByRole('button', { name: '검증 실행', exact: true }).waitFor()
}

async function openValidation(page, id) {
  await page.goto(base)
  await page.getByRole('button', { name: '검증 이력', exact: true }).click()
  const row = page.locator('tr').filter({ has: page.getByText(`#${id}`, { exact: true }) })
  await row.getByRole('button', { name: '결과', exact: true }).click()
  await page.locator('.result-heading').waitFor()
  await ready(page)
  await page.evaluate(() => window.scrollTo(0, 0))
}

async function record(scene, prepare, actions, mobile = false) {
  const viewport = mobile ? { width: 390, height: 844 } : { width: 1600, height: 820 }
  const context = await browser.newContext({ viewport, deviceScaleFactor: 1, ...(mobile ? { isMobile: true, hasTouch: true } : {}),
    recordVideo: { dir: clips, size: viewport } })
  const page = await context.newPage()
  page.on('pageerror', e => errors.push(`${scene.id}: ${e.message}`))
  await prepare(page)
  await instrument(page)
  await sleep(300)
  const started = Date.now()
  await actions(page)
  const remaining = scene.duration * 1000 - (Date.now() - started)
  if (remaining < 0) throw new Error(`${scene.id}: 장면 동작이 내레이션 길이를 초과했습니다.`)
  await sleep(remaining)
  await page.screenshot({ path: path.join(work, `${scene.id}-last.png`) })
  const video = page.video()
  await page.close()
  await context.close()
  const raw = await video.path()
  const target = path.join(clips, scene.id + '.webm')
  fs.renameSync(raw, target)
  recording.push({ id: scene.id, mobile, file: target, duration: scene.duration })
  fs.writeFileSync(path.join(work, 'recordings.json'), JSON.stringify(recording, null, 2))
  console.log(`RECORDED ${scene.id} ${scene.duration}s`)
}

;(async () => {
  browser = await chromium.launch({ headless: true, ...(process.env.UI_BROWSER ? { executablePath: process.env.UI_BROWSER } : { channel: 'chrome' }) })
  for (const scene of scenes) {
    if (onlyScenes && !onlyScenes.includes(scene.id)) continue
    if (['intro', 'problem', 'closing'].includes(scene.id)) {
      await record(scene, p => p.setContent(slide(scene.id)), async () => {})
    } else if (scene.id === 'ingest') {
      await record(scene, async p => { await p.goto(base); await p.getByRole('button', { name: '장비 데이터', exact: true }).click(); await p.locator('.release-card').first().waitFor() }, async p => {
        await sleep(1600)
        await point(p, p.getByRole('button', { name: '장비에서 전송', exact: true }), true)
        await p.getByRole('status').filter({ hasText: '동일한 원본' }).waitFor()
        await sleep(2000)
        await highlight(p.locator('.release-grid'))
        await point(p, p.getByRole('button', { name: 'JSON 파일 업로드', exact: true }))
      })
    } else if (scene.id === 'profile') {
      await record(scene, async p => { await p.goto(base); await p.getByRole('button', { name: '장비 데이터', exact: true }).click(); await p.locator('.release-card').first().waitFor(); await p.getByText('승인 데이터 항목표', { exact: true }).scrollIntoViewIfNeeded() }, async p => {
        await sleep(1700)
        await highlight(p.locator('table').last())
        await point(p, p.getByRole('cell', { name: '1000ms ±20%' }).first())
        await sleep(2000)
        await point(p, p.getByRole('cell', { name: '미설정', exact: true }))
      })
    } else if (scene.id === 'compare') {
      await record(scene, async p => { await p.goto(base); await p.getByLabel('비교 데이터', { exact: true }).waitFor() }, async p => {
        await point(p, p.getByLabel('기준 데이터', { exact: true }))
        await p.getByLabel('기준 데이터', { exact: true }).selectOption({ label: '기준 버전 · v1.0.0' })
        await point(p, p.getByLabel('비교 데이터', { exact: true }))
        await p.getByLabel('비교 데이터', { exact: true }).selectOption({ label: '결함 수정 버전 · v1.1.0' })
        await point(p, p.getByRole('button', { name: '검증 실행', exact: true }), true)
        await p.locator('.result-heading .status.fail').waitFor(); await ready(p)
        faultyId = Number((await p.locator('.result-heading h2 span').innerText()).replace('#', ''))
        await p.locator('.result-heading').scrollIntoViewIfNeeded()
        await highlight(p.locator('.stat-grid'))
      })
    } else if (scene.id === 'results') {
      await record(scene, async p => { await openValidation(p, faultyId); await p.locator('.result-heading').scrollIntoViewIfNeeded() }, async p => {
        await sleep(1600); await highlight(p.locator('.stat-grid'))
        await point(p, p.locator('.filter-tabs').getByRole('button', { name: '실패', exact: true }), true)
        await sleep(2800)
        await p.locator('.checks-card').scrollIntoViewIfNeeded()
        await point(p, p.getByRole('cell', { name: '단위 일치', exact: true }).first())
        await sleep(1800)
        await point(p, p.locator('.filter-tabs').getByRole('button', { name: '판단불가', exact: true }), true)
      })
    } else if (scene.id === 'evidence') {
      await record(scene, async p => { await openValidation(p, faultyId); await p.locator('.filter-tabs').getByRole('button', { name: '실패', exact: true }).click(); await p.locator('.checks-card').scrollIntoViewIfNeeded() }, async p => {
        const row = p.locator('.checks-table tbody tr').filter({ hasText: 'TEMP_PV' }).filter({ hasText: '단위 일치' })
        await point(p, row.getByRole('button', { name: '원본 확인' }), true)
        await p.locator('dialog[open]').waitFor()
        await highlight(p.locator('dialog .evidence-facts'))
        await sleep(2800)
        await point(p, p.locator('dialog pre'))
        // 내레이션이 끝날 때까지 근거 창을 유지해 실제 단위와 원본을 읽을 수 있게 한다.
        await sleep(2800)
      })
    } else if (scene.id === 'hold') {
      await record(scene, async p => { await openValidation(p, faultyId); await p.locator('.review-card').scrollIntoViewIfNeeded() }, async p => {
        await point(p, p.getByPlaceholder('이름 또는 담당자 ID'), true)
        await p.getByPlaceholder('이름 또는 담당자 ID').pressSequentially('품질 검토자', { delay: 100 })
        await p.getByPlaceholder('확인한 내용과 후속 조치를 기록하세요.').fill('단위 충돌·유량 누락·작업 연결 오류 확인. 수정 후 재검증 필요.')
        await point(p, p.getByRole('button', { name: '보류 기록', exact: true }), true)
        await p.locator('.review-card .status.hold').first().waitFor()
        await highlight(p.locator('.audit-list'))
      })
    } else if (scene.id === 'healthy') {
      await record(scene, p => openValidation(p, faultyId), async p => {
        await point(p, p.getByLabel('비교 데이터', { exact: true }))
        await p.getByLabel('비교 데이터', { exact: true }).selectOption({ label: '정상 수정 버전 · v1.1.1' })
        await point(p, p.getByRole('button', { name: '검증 실행', exact: true }), true)
        await p.locator('.result-heading .status.pass').waitFor(); await ready(p)
        healthyId = Number((await p.locator('.result-heading h2 span').innerText()).replace('#', ''))
        await p.locator('.stat-grid').scrollIntoViewIfNeeded(); await highlight(p.locator('.stat-grid')); await sleep(1200)
        await p.locator('.review-card').scrollIntoViewIfNeeded()
        await p.getByPlaceholder('이름 또는 담당자 ID').fill('품질 검토자')
        await p.getByPlaceholder('확인한 내용과 후속 조치를 기록하세요.').fill('필수 검사와 원본 근거 확인. 등록된 검증 범위의 검토 승인.')
        await point(p, p.getByRole('button', { name: '검토 승인', exact: true }), true)
        await p.locator('.review-card .status.approved').first().waitFor()
      })
    } else if (scene.id === 'report') {
      await record(scene, async p => { await openValidation(p, healthyId); await p.locator('.review-card').scrollIntoViewIfNeeded() }, async p => {
        await point(p, p.getByRole('link', { name: /보고서 열기/ }))
        await p.goto(`${base}/api/validations/${healthyId}/report`)
        await sleep(3500)
        await p.getByText('원본 증거', { exact: true }).scrollIntoViewIfNeeded(); await sleep(2500)
        await p.getByText('검토 이력', { exact: true }).scrollIntoViewIfNeeded(); await sleep(2500)
        await p.evaluate(() => window.scrollTo({ top: 0, behavior: 'smooth' }))
      })
    } else if (scene.id === 'mobile') {
      await record(scene, async p => { await p.goto(base); await ready(p) }, async p => {
        await sleep(1500)
        await point(p, p.getByRole('button', { name: '장비 데이터', exact: true }), true)
        await sleep(3000)
        await point(p, p.getByRole('button', { name: '검증 이력', exact: true }), true)
        const row = p.locator('tr').filter({ has: p.getByText(`#${healthyId}`, { exact: true }) })
        await point(p, row.getByRole('button', { name: '결과', exact: true }), true)
        await p.locator('.result-heading .status.pass').waitFor()
        await p.locator('.review-card').scrollIntoViewIfNeeded()
      }, true)
    }
  }
  await browser.close()
  fs.writeFileSync(path.join(work, 'capture-check.json'), JSON.stringify({ errors, faultyId, healthyId, sceneCount: recording.length }, null, 2))
  if (errors.length) throw new Error(JSON.stringify(errors))
  console.log('CAPTURE COMPLETE', JSON.stringify({ faultyId, healthyId, sceneCount: recording.length }))
})().catch(async e => { console.error(e); if (browser) await browser.close(); process.exit(1) })

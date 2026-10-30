/* 브라우저가 완성본의 H.264/AAC를 읽고 재생할 수 있는지 확인한다. */
const fs = require('node:fs')
const path = require('node:path')
const assert = require('node:assert/strict')
const { pathToFileURL } = require('node:url')
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright')
const project = path.resolve(__dirname, '../..')
;(async () => {
  const browser = await chromium.launch({ headless: true, ...(process.env.UI_BROWSER ? { executablePath: process.env.UI_BROWSER } : { channel: 'chrome' }) })
  try {
    const page = await browser.newPage({ viewport: { width: 1500, height: 1000 } })
    await page.goto(pathToFileURL(path.join(project, 'docs', 'TraceProof_고객시연_재생.html')).href)
    await page.waitForFunction(() => document.querySelector('video').readyState >= 2)
    const metadata = await page.locator('video').evaluate(async video => {
      video.muted = true
      await video.play()
      await new Promise(resolve => setTimeout(resolve, 1200))
      video.pause()
      return { width: video.videoWidth, height: video.videoHeight, duration: video.duration,
        currentTime: video.currentTime, readyState: video.readyState, error: video.error?.message || null }
    })
    assert.equal(metadata.width, 1920)
    assert.equal(metadata.height, 1080)
    assert.ok(metadata.duration > 200 && metadata.duration < 220)
    assert.ok(metadata.currentTime > 0)
    assert.equal(metadata.error, null)
    fs.writeFileSync(path.resolve(project, '../tmp/sales_video/browser-playback.json'), JSON.stringify(metadata, null, 2))
    console.log(JSON.stringify({ playback: 'PASS', ...metadata }))
  } finally { await browser.close() }
})().catch(error => { console.error(error); process.exit(1) })

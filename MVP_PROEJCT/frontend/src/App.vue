<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import { ShieldCheck, LayoutDashboard, Database, FileCheck2, BookOpen, ArrowRight, Play, Upload, Radio, RefreshCw, ChevronRight, Download, X, Check, AlertTriangle, Search, Layers, Cpu, ExternalLink } from 'lucide-vue-next'
import { api, jsonPost } from './api'
import StatusBadge from './components/StatusBadge.vue'
import TrendChart from './components/TrendChart.vue'

const tab = ref('workspace')
const navigation = [{ id: 'workspace', name: '변경 검증', icon: LayoutDashboard }, { id: 'data', name: '장비 데이터', icon: Database }, { id: 'reports', name: '검증 이력', icon: FileCheck2 }, { id: 'manual', name: '사용 가이드', icon: BookOpen }]
const releases = ref([]), profiles = ref([]), history = ref([])
const baselineId = ref(''), candidateId = ref(''), profileId = ref('PROFILE-DEMO-V1')
const active = ref(null), baselineData = ref(null), candidateData = ref(null)
const busy = ref(false), online = ref(false), error = ref(''), notice = ref('')
const filter = ref('ALL'), search = ref(''), chartParameter = ref('TEMP_PV')
const demoScenario = ref('faulty'), fileInput = ref(null), dialog = ref(null), selectedCheck = ref(null)
const reviewer = ref(''), reviewNote = ref(''), syncedAt = ref(null)
const selectedProfile = computed(() => active.value?.profile_snapshot || profiles.value.find(p => p.id === profileId.value))
const baseline = computed(() => releases.value.find(r => r.id === Number(baselineId.value)))
const candidate = computed(() => releases.value.find(r => r.id === Number(candidateId.value)))
const currentParam = computed(() => selectedProfile.value?.parameters.find(p => p.id === chartParameter.value))
const counts = computed(() => active.value?.result.summary || { PASS: 0, FAIL: 0, NOT_TESTED: 0, UNDETERMINED: 0 })
const visibleChecks = computed(() => (active.value?.result.checks || []).filter(c => (filter.value === 'ALL' || c.status === filter.value) && `${c.parameter_id} ${c.title} ${c.observed}`.toLowerCase().includes(search.value.toLowerCase())))
const time = (value) => value ? new Date(value).toLocaleString('ko-KR', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }) : '-'
const parameterName = id => selectedProfile.value?.parameters.find(p => p.id === id)?.name || (id === '_manifest' ? '버전 증거' : id === '_scope' ? '검사 범위' : id)

async function perform(action) {
  busy.value = true; error.value = ''; notice.value = ''
  try { await action() } catch (e) { error.value = e.message } finally { busy.value = false }
}
async function refresh() {
  const [health, data, rules, records] = await Promise.all([api('/health'), api('/releases'), api('/profiles'), api('/validations')])
  online.value = health.status === 'ok'; releases.value = data; profiles.value = rules; history.value = records; syncedAt.value = new Date()
  if (!baselineId.value) baselineId.value = data.find(r => r.software_version === '1.0.0')?.id || ''
  if (!candidateId.value) candidateId.value = data.find(r => r.software_version === '1.1.0')?.id || ''
}
async function loadPayloads(before, after) {
  ;[baselineData.value, candidateData.value] = await Promise.all([api(`/releases/${before}`), api(`/releases/${after}`)])
}
async function runValidation() {
  await perform(async () => {
    const result = await api('/validations', jsonPost({ baseline_id: Number(baselineId.value), candidate_id: Number(candidateId.value), profile_id: profileId.value }))
    active.value = result; filter.value = 'ALL'; search.value = ''
    await loadPayloads(result.baseline_id, result.candidate_id); await refresh()
    notice.value = `검증 #${result.id} 완료. 결과를 확인한 뒤 검토 의견을 남겨주세요.`
  })
}
function resetResult() { active.value = null; baselineData.value = null; candidateData.value = null }
async function showValidation(item) {
  await perform(async () => {
    active.value = await api(`/validations/${item.id}`)
    baselineId.value = item.baseline_id; candidateId.value = item.candidate_id; profileId.value = item.profile_id
    await loadPayloads(item.baseline_id, item.candidate_id); filter.value = 'ALL'; search.value = ''; tab.value = 'workspace'
  })
}
async function sendDemo() {
  await perform(async () => {
    const result = await api('/demo/send', jsonPost({ scenario: demoScenario.value }))
    await refresh(); candidateId.value = result.release.id; resetResult()
    notice.value = result.reused ? '동일한 원본이 이미 등록되어 기존 데이터를 사용합니다. 중복 저장하지 않았습니다.' : '모의 장비가 RAW_DATA의 원본을 전송했습니다.'
  })
}
async function upload(event) {
  const file = event.target.files?.[0]
  if (!file) return
  await perform(async () => {
    if (file.size > 5 * 1024 * 1024) throw new Error('5MB 이하의 JSON 파일을 선택하세요.')
    const data = new FormData(); data.append('file', file)
    const result = await api('/releases/upload', { method: 'POST', body: data })
    await refresh(); candidateId.value = result.release.id; resetResult()
    notice.value = result.reused ? '이미 등록된 원본입니다. 기존 자료를 선택했습니다.' : '원본 파일을 등록했습니다. 변경 검증에서 비교할 수 있습니다.'
  })
  event.target.value = ''
}
async function review(disposition) {
  await perform(async () => {
    active.value = await api(`/validations/${active.value.id}/review`, jsonPost({ disposition, reviewer: reviewer.value, note: reviewNote.value }))
    await refresh(); notice.value = '검토 의견과 상태를 저장했습니다.'; reviewNote.value = ''
  })
}
async function evidence(check) { selectedCheck.value = check; await nextTick(); dialog.value.showModal() }
onMounted(() => perform(refresh))
</script>

<template>
  <div class="app-shell">
    <aside class="sidebar">
      <a class="brand" href="#" @click.prevent="tab = 'workspace'"><span class="brand-icon"><ShieldCheck :size="23" /></span><span>TraceProof<small>EQUIPMENT ASSURANCE</small></span></a>
      <div class="workspace-label">WORKSPACE <span>DEMO</span></div>
      <nav aria-label="주 메뉴"><button v-for="item in navigation" :key="item.id" :class="{ selected: tab === item.id }" @click="tab = item.id"><component :is="item.icon" :size="19" /><span>{{ item.name }}</span><ChevronRight v-if="tab === item.id" class="nav-arrow" :size="15" /></button></nav>
      <div class="sidebar-bottom"><span class="tiny-label">CONNECTED EQUIPMENT</span><div class="connected"><span class="led" :class="{ off: !online }"></span><div>EQ-DEMO-01<small>가상 출하 검증실</small></div></div><p>기준이 분명한 검사,<br>근거가 남는 변경 검토.</p><span class="version">MVP v1.0 · 로컬 데모</span></div>
    </aside>

    <main>
      <header class="topbar"><span>출하 검증실 <ChevronRight :size="13" /> {{ navigation.find(n => n.id === tab)?.name }}</span><div><span class="connection"><i :class="{ off: !online }"></i>{{ online ? '시스템 연결됨' : '연결 확인 중' }}</span><span class="avatar">TP</span></div></header>
      <div class="page-content">
        <div class="page-title"><div><div class="eyebrow">EQUIPMENT DATA VALIDATION</div><h1>{{ navigation.find(n => n.id === tab)?.name }}</h1><p>장비 데이터의 변화를 확인하고, 검토의 근거를 남기세요.</p></div><button class="button secondary refresh" :disabled="busy" @click="perform(refresh)"><RefreshCw :size="16" :class="{ spin: busy }" />새로고침</button></div>
        <div v-if="error" class="message error" role="alert"><AlertTriangle :size="18" />{{ error }}<button aria-label="오류 닫기" @click="error = ''"><X :size="16" /></button></div>
        <div v-if="notice" class="message success" role="status"><Check :size="18" />{{ notice }}<button aria-label="알림 닫기" @click="notice = ''"><X :size="16" /></button></div>

        <template v-if="tab === 'workspace'">
          <section class="hero"><div><span class="hero-tag">CHANGE WITH CONFIDENCE</span><h2>변경된 장비 데이터,<br>출하 전에 한 번 더 확인하세요.</h2><p>기준 버전과 수정 버전을 비교해 단위, 수집 간격,<br class="desktop-break">작업 연결과 검증 누락을 확인합니다.</p><div class="hero-meta"><span><Cpu :size="15" /> 장비 1개 모델</span><span><Layers :size="15" /> 승인 기준 v1.0</span></div></div><div class="hero-visual" aria-hidden="true"><div class="visual-node"><Database :size="22" /><span>BASELINE</span><strong>v1.0.0</strong></div><div class="visual-connector"><ArrowRight :size="24" /><small>COMPARE</small></div><div class="visual-node highlighted"><ShieldCheck :size="22" /><span>VALIDATION</span><strong>근거 기반 검토</strong></div></div></section>

          <section class="card compare-card"><div class="section-title"><div><span class="step-number">01</span><h2>비교할 데이터 선택</h2></div><span class="muted">동일 장비 · 동일 운전 조건</span></div><div class="compare-form"><label>기준 데이터<select aria-label="기준 데이터" v-model="baselineId" @change="resetResult"><option value="" disabled>기준 버전을 선택하세요</option><option v-for="r in releases" :key="r.id" :value="r.id">{{ r.label }}</option></select></label><div class="compare-arrow"><ArrowRight :size="20" /></div><label>비교 데이터<select aria-label="비교 데이터" v-model="candidateId" @change="resetResult"><option value="" disabled>수정 버전을 선택하세요</option><option v-for="r in releases" :key="r.id" :value="r.id">{{ r.label }}</option></select></label><button class="button primary run" :disabled="busy || !baselineId || !candidateId || baselineId === candidateId" @click="runValidation"><Play :size="17" />{{ busy ? '처리 중…' : '검증 실행' }}</button></div><div class="compare-foot"><span><span class="led"></span>{{ releases.length }}개 데이터 등록됨</span><span>{{ selectedProfile?.name || '검증 기준을 불러오는 중' }}</span><button @click="tab = 'data'">데이터 등록 <ArrowRight :size="13" /></button></div></section>

          <template v-if="active">
            <div class="result-heading"><div><h2>검증 결과 <span>#{{ active.id }}</span></h2><p>{{ baseline?.software_version }} <ArrowRight :size="13" /> {{ candidate?.software_version }} · {{ time(active.created_at) }}</p></div><StatusBadge :status="active.result.conclusion" /></div>
            <div v-if="!active.result.baseline_usable" class="message error"><AlertTriangle :size="18" />기준 데이터에도 문제가 있습니다. 기준 데이터부터 확인해야 하며 승인할 수 없습니다.</div>
            <div class="stat-grid"><button v-for="(label, status) in { PASS: '통과', FAIL: '실패', UNDETERMINED: '판단불가', NOT_TESTED: '미실시' }" :key="status" class="stat-card" :class="[status.toLowerCase(), { active: filter === status }]" @click="filter = filter === status ? 'ALL' : status"><span>{{ label }}<span class="stat-mark"></span></span><strong>{{ counts[status] }}<small>건</small></strong><span class="stat-caption">{{ status === 'NOT_TESTED' ? '미설정 항목도 분모에 포함' : status === 'UNDETERMINED' ? '추가 자료 확인 필요' : status === 'FAIL' ? '승인 전 조치 필요' : '등록한 검사 기준 만족' }}</span></button></div>
            <section class="card checks-card"><div class="section-title"><div><span class="step-number">02</span><h2>항목별 검사 결과</h2></div><a class="text-link" :href="`/api/validations/${active.id}/checks.csv`"><Download :size="15" />CSV 저장</a></div><div class="table-tools"><div class="filter-tabs"><button v-for="(name, key) in { ALL: '전체', FAIL: '실패', UNDETERMINED: '판단불가', NOT_TESTED: '미실시', PASS: '통과' }" :key="key" :class="{ active: filter === key }" @click="filter = key">{{ name }}</button></div><label class="search"><Search :size="16" /><input v-model="search" aria-label="검사 검색" placeholder="항목 · 검사 검색"></label></div><div class="table-scroll"><table class="checks-table"><thead><tr><th>데이터 항목</th><th>검사</th><th>판정</th><th>관측 결과</th><th>근거</th></tr></thead><tbody><tr v-for="(c, index) in visibleChecks" :key="`${c.parameter_id}-${c.rule}-${index}`"><td><strong>{{ parameterName(c.parameter_id) }}</strong><small>{{ c.parameter_id }}</small></td><td>{{ c.title }}</td><td><StatusBadge :status="c.status" /></td><td class="observed">{{ c.observed }}</td><td><button class="evidence-button" @click="evidence(c)">원본 확인 <ChevronRight :size="14" /></button></td></tr><tr v-if="!visibleChecks.length"><td colspan="5" class="empty-cell">조건에 맞는 검사 결과가 없습니다.</td></tr></tbody></table></div><div class="table-footer">{{ visibleChecks.length }} / {{ active.result.checks.length }}개 검사 · 검사 엔진 {{ active.result.engine_version }}<span>판단불가와 미실시는 통과가 아닙니다.</span></div></section>
            <div class="detail-grid"><section class="card"><div class="section-title"><h2>변경 전후 데이터</h2><select v-model="chartParameter" aria-label="그래프 항목"><option v-for="p in selectedProfile.parameters" :key="p.id" :value="p.id">{{ p.name }}</option></select></div><TrendChart :baseline="baselineData?.payload.measurements" :candidate="candidateData?.payload.measurements" :parameter="currentParam" /></section><section class="card evidence-summary"><div class="section-title"><h2>원본과 버전 증거</h2><ShieldCheck :size="19" /></div><div v-for="(r, i) in [baselineData, candidateData]" :key="r?.id" class="source-record"><span>{{ i === 0 ? '기준' : '비교' }} · {{ r?.filename }}</span><strong>SW {{ r?.software_version }}<small>{{ r?.config_version }}</small></strong><code>SHA-256 {{ r?.sha256 }}</code><a :href="`/api/releases/${r?.id}/raw`" class="text-link"><Download :size="14" />원본 JSON</a></div></section></div>
            <section class="card review-card"><div class="section-title"><div><span class="step-number">03</span><h2>담당자 검토</h2></div><StatusBadge :status="active.review_status" /></div><p class="muted">{{ active.result.approvable ? '필수 검사가 통과했습니다. 원본을 확인한 담당자가 검토를 승인할 수 있습니다.' : '필수 실패·판단불가·미실시 또는 기준 데이터 문제가 있어 보류만 가능합니다.' }}</p><div class="review-form"><label>검토자<input v-model="reviewer" maxlength="80" placeholder="이름 또는 담당자 ID"></label><label>검토 의견<textarea v-model="reviewNote" maxlength="2000" rows="2" placeholder="확인한 내용과 후속 조치를 기록하세요."></textarea></label></div><div class="review-actions"><a :href="`/api/validations/${active.id}/report`" target="_blank" rel="noopener" class="button secondary"><FileCheck2 :size="16" />보고서 열기 <ExternalLink :size="13" /></a><div><button class="button secondary" :disabled="busy || !reviewer.trim() || !reviewNote.trim()" @click="review('HOLD')">보류 기록</button><button class="button primary" :disabled="busy || !active.result.approvable || !reviewer.trim() || !reviewNote.trim()" @click="review('APPROVED')"><Check :size="16" />검토 승인</button></div></div><div v-if="active.reviews.length" class="audit-list"><div v-for="(r, i) in active.reviews" :key="i"><span class="audit-dot"></span><div><strong>{{ r.reviewer }}</strong> · <StatusBadge :status="r.disposition" /><small>{{ time(r.at) }}</small><p>{{ r.note }}</p></div></div></div></section>
          </template>
          <section v-else class="card start-guide"><div class="start-icon"><ShieldCheck :size="29" /></div><h2>첫 변경 검증을 시작하세요</h2><p>기준 v1.0.0과 결함 버전 v1.1.0을 선택한 뒤 검증을 실행하세요.<br>수정된 v1.1.1과 다시 비교하면 정상 결과도 확인할 수 있습니다.</p><div><span>1. 버전 선택</span><ChevronRight :size="14" /><span>2. 차이와 근거 확인</span><ChevronRight :size="14" /><span>3. 검토 기록</span></div><button v-if="!releases.length" class="button secondary" :disabled="busy" @click="perform(refresh)">초기 장비 전송 후 새로고침</button></section>
        </template>

        <template v-if="tab === 'data'">
          <section class="card"><div class="section-title"><div><Radio :size="20" /><h2>가상 장비에서 데이터 전송</h2></div><span class="demo-pill">SIMULATOR</span></div><p class="muted">RAW_DATA의 원본 → 별도 장비 어댑터 → FastAPI → PostgreSQL 경로로 전송합니다.</p><div class="transfer-form"><label>전송 시나리오<select v-model="demoScenario"><option value="baseline">기준 버전 v1.0.0</option><option value="faulty">결함 버전 v1.1.0</option><option value="healthy">정상 수정 버전 v1.1.1</option></select></label><button class="button primary" :disabled="busy" @click="sendDemo"><Radio :size="16" />장비에서 전송</button><span class="or">또는</span><button class="button secondary" :disabled="busy" @click="fileInput.click()"><Upload :size="16" />JSON 파일 업로드</button><input ref="fileInput" class="file-input" type="file" accept=".json,application/json" @change="upload"></div><p class="small-note">UTF-8 JSON · 최대 5MB / 20,000개 표본 · 동일 원본은 SHA-256으로 중복 방지</p></section>
          <section class="card"><div class="section-title"><h2>등록된 원본 데이터</h2><span class="muted">최근 {{ releases.length }}개</span></div><div class="release-grid"><article v-for="r in releases" :key="r.id" class="release-card"><div><span class="file-icon"><Database :size="21" /></span><span class="source-badge">{{ r.source === 'DEVICE' ? '장비 전송' : '파일 업로드' }}</span></div><h3>{{ r.label }}</h3><p>{{ r.equipment_id }} · {{ r.config_version }}</p><dl><div><dt>원본 표본</dt><dd>{{ r.measurement_count }}개</dd></div><div><dt>등록 시각</dt><dd>{{ time(r.created_at) }}</dd></div></dl><code>{{ r.sha256.slice(0, 24) }}…</code><a class="text-link" :href="`/api/releases/${r.id}/raw`"><Download :size="14" />원본 다운로드</a></article><p v-if="!releases.length" class="empty-cell">아직 데이터가 없습니다. 장비에서 전송하거나 JSON을 업로드하세요.</p></div></section>
          <section v-for="p in profiles" :key="p.id" class="card"><div class="section-title"><h2>승인 데이터 항목표</h2><span class="muted">{{ p.name }} · v{{ p.version }}</span></div><p class="muted">데모에서는 기준을 읽기 전용으로 사용합니다. 변경 시 새 기준 버전과 승인 절차가 필요합니다.</p><div class="table-scroll"><table><thead><tr><th>항목 ID</th><th>이름</th><th>단위</th><th>허용 범위</th><th>간격</th><th>최소 표본</th></tr></thead><tbody><tr v-for="s in p.parameters" :key="s.id"><td>{{ s.id }}</td><td>{{ s.name }}</td><td>{{ s.unit }}</td><td>{{ s.minimum == null ? '미설정' : `${s.minimum} ~ ${s.maximum}` }}</td><td>{{ s.interval_ms }}ms ±{{ s.interval_tolerance * 100 }}%</td><td>{{ s.min_samples }}개</td></tr></tbody></table></div></section>
        </template>

        <template v-if="tab === 'reports'">
          <section class="card"><div class="section-title"><h2>검증 및 검토 이력</h2><span class="muted">최근 50건</span></div><div class="table-scroll"><table><thead><tr><th>검증</th><th>검사 결과</th><th>검토 상태</th><th>실행 시각</th><th>열기</th></tr></thead><tbody><tr v-for="v in history" :key="v.id"><td><strong>#{{ v.id }}</strong><small>기준 #{{ v.baseline_id }} → 비교 #{{ v.candidate_id }}</small></td><td><StatusBadge :status="v.result.conclusion" /></td><td><StatusBadge :status="v.review_status" /></td><td>{{ time(v.created_at) }}</td><td><div class="inline-actions"><button class="evidence-button" :disabled="busy" @click="showValidation(v)">결과</button><a :href="`/api/validations/${v.id}/report`" target="_blank" rel="noopener">보고서 <ExternalLink :size="13" /></a></div></td></tr><tr v-if="!history.length"><td colspan="5" class="empty-cell">아직 검증 이력이 없습니다. 변경 검증에서 첫 검사를 실행하세요.</td></tr></tbody></table></div></section>
        </template>

        <template v-if="tab === 'manual'">
          <section class="card manual-intro"><span class="eyebrow">QUICK START</span><h2>5분이면 첫 시연을 할 수 있습니다.</h2><p>실제 고객 데이터가 아닌 가상의 장비 데이터로 기능을 확인합니다.</p><ol><li><strong>데이터 확인</strong><p>장비 데이터 메뉴에서 기준·결함·정상 수정 버전 3개를 확인하세요. 처음 실행하면 모의 장비가 자동 전송합니다.</p></li><li><strong>결함 검증</strong><p>변경 검증에서 v1.0.0과 v1.1.0을 비교하세요. 단위 불일치, 유량 누락, 시간 중복, 작업 번호 오류와 버전 불일치가 표시됩니다.</p></li><li><strong>원본 확인과 보류</strong><p>원본 확인으로 기대 기준과 실제 행을 확인합니다. 검토자와 의견을 입력해 보류를 기록하세요. 문제가 남은 결과는 승인할 수 없습니다.</p></li><li><strong>정상 버전 재검증</strong><p>비교 데이터를 v1.1.1로 바꿔 새 검증을 실행하세요. 진동 범위는 미설정이므로 미실시이지만 비필수 검사입니다. 나머지 필수 검사가 통과하면 검토 승인이 가능합니다.</p></li><li><strong>보고서 공유</strong><p>보고서 열기에서 브라우저 인쇄 → PDF 저장을 사용하세요. CSV와 원본 JSON도 내려받을 수 있습니다.</p></li></ol></section><section class="card"><h2>판정 읽는 방법</h2><div class="definition-grid"><div v-for="(text, state) in { PASS: '합의한 검사 기준을 만족했습니다.', FAIL: '등록된 기준 위반이 확인됐습니다.', UNDETERMINED: '자료나 시차 등 근거가 부족해 판단할 수 없습니다.', NOT_TESTED: '자료나 검사 설정이 없어 해당 검사를 수행하지 않았습니다.' }" :key="state"><StatusBadge :status="state" /><p>{{ text }}</p></div></div><p class="small-note">이 도구는 센서 교정, 공정 수율, SEMI 인증 또는 고객 인수 합격을 보장하지 않습니다. 사용자 로그인·다중 권한 분리는 아직 없는 로컬 시연용 MVP입니다.</p></section>
        </template>

        <footer class="page-footer"><span>TraceProof · 장비 데이터 변경 검증 MVP</span><span>가상 데이터 · {{ syncedAt ? `동기화 ${time(syncedAt)}` : '연결 대기' }}</span></footer>
      </div>
    </main>
    <dialog ref="dialog" class="evidence-dialog" @close="selectedCheck = null"><template v-if="selectedCheck"><div class="dialog-header"><div><span class="eyebrow">SOURCE EVIDENCE</span><h2>{{ selectedCheck.title }}</h2></div><button class="icon-button" aria-label="근거 창 닫기" @click="dialog.close()"><X :size="21" /></button></div><StatusBadge :status="selectedCheck.status" /><dl class="evidence-facts"><div><dt>데이터 항목</dt><dd>{{ parameterName(selectedCheck.parameter_id) }} · {{ selectedCheck.parameter_id }}</dd></div><div><dt>기대 기준</dt><dd>{{ selectedCheck.expected }}</dd></div><div><dt>관측 결과</dt><dd>{{ selectedCheck.observed }}</dd></div></dl><p class="small-note">원본 {{ candidateData?.filename }} · measurements 배열의 1부터 시작하는 번호입니다.</p><pre v-if="selectedCheck.rows.length">{{ JSON.stringify(selectedCheck.rows.map(n => ({ row: n, ...candidateData?.payload.measurements[n - 1] })), null, 2) }}</pre><pre v-else>{{ JSON.stringify(candidateData?.payload.manifest, null, 2) }}</pre><p v-if="!selectedCheck.rows.length" class="small-note">해당 표본이 없거나 버전·범위 검사입니다. 위에는 파일의 manifest를 표시했습니다.</p><a class="button secondary" :href="`/api/releases/${candidateData?.id}/raw`"><Download :size="15" />전체 원본 다운로드</a></template></dialog>
  </div>
</template>

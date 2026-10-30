<script setup>
import { computed } from 'vue'
const props = defineProps({ baseline: Array, candidate: Array, parameter: Object })
const before = computed(() => (props.baseline || []).filter(r => r.parameter_id === props.parameter?.id))
const after = computed(() => (props.candidate || []).filter(r => r.parameter_id === props.parameter?.id))
const differentUnit = computed(() => [...before.value, ...after.value].some(r => r.unit !== props.parameter?.unit))
const values = computed(() => [...before.value, ...after.value].map(r => r.value).filter(v => Number.isFinite(v)))
const minimum = computed(() => values.value.length ? Math.min(...values.value) - 2 : 0)
const maximum = computed(() => values.value.length ? Math.max(...values.value) + 2 : 10)
function line(data) {
  // 가로축은 표본 순서다. 실제 시각 간격의 이상은 별도 TIME 검사에서 확인한다.
  return data.filter(r => Number.isFinite(r.value)).map((r, i) => `${40 + i * 490 / Math.max(data.length - 1, 1)},${150 - (r.value - minimum.value) / (maximum.value - minimum.value) * 115}`).join(' ')
}
</script>
<template>
  <div class="chart-panel">
    <div class="chart-heading"><strong>{{ parameter?.name }} 추이</strong><span>표본 순서 기준 · {{ parameter?.unit }}</span></div>
    <p v-if="differentUnit" class="chart-warning">단위가 달라 그래프를 겹쳐 표시하지 않습니다. 원본과 단위 검사 결과를 확인하세요.</p>
    <template v-else>
      <svg viewBox="0 0 560 185" role="img" :aria-label="`${parameter?.name} 변경 전후 표본 순서 그래프`">
        <g stroke="#e8eef2"><line v-for="y in [35, 73, 111, 150]" :key="y" x1="40" :y1="y" x2="535" :y2="y" /></g>
        <text x="2" y="38">{{ maximum.toFixed(0) }}</text><text x="2" y="153">{{ minimum.toFixed(0) }}</text>
        <polyline :points="line(before)" fill="none" stroke="#a2b2bf" stroke-width="2.5" stroke-dasharray="5 4" />
        <polyline :points="line(after)" fill="none" stroke="#0c8e82" stroke-width="3" />
        <text x="40" y="176">첫 표본</text><text x="490" y="176">마지막 표본</text>
      </svg>
      <div class="legend"><span><i class="before"></i>기준 데이터</span><span><i></i>비교 데이터</span><span v-if="!after.length">비교 데이터 없음</span></div>
    </template>
  </div>
</template>

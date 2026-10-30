<script setup>
defineProps({ status: { type: String, default: 'PENDING' } })
const labels = { PASS: '통과', FAIL: '실패', NOT_TESTED: '미실시', UNDETERMINED: '판단불가', PENDING: '검토 대기', HOLD: '보류', APPROVED: '검토 승인' }
</script>
<template><span class="status" :class="status.toLowerCase()"><i></i>{{ labels[status] || status }}</span></template>

// 화면과 HTTP 처리의 책임을 분리한다. 휴대폰에서도 동일 출처 /api를 사용한다.
export async function api(path, options = {}) {
  const response = await fetch(`/api${path}`, options)
  if (!response.ok) {
    let message = `요청 실패 (${response.status})`
    try {
      const payload = await response.json()
      message = typeof payload.detail === 'string' ? payload.detail : '입력 형식을 확인해주세요.'
    } catch { /* JSON이 아닌 프록시 오류도 사람이 이해할 수 있는 메시지로 표시한다. */ }
    throw new Error(message)
  }
  return response.json()
}
export const jsonPost = (data) => ({ method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) })

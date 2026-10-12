// 后端 API 封装:前端所有和后端的通信都走这里,方便统一管理

// 所有请求都用相对路径 /api/xxx
// 开发时由 vite 代理转发到后端(见 vite.config.js 的 proxy 配置),
// 这样代码里不用写死 http://127.0.0.1:8000,以后部署到同一域名下也不用改。

/**
 * 核心:SSE 流式对话。
 *
 * 为什么不用浏览器的 EventSource?因为它只支持 GET 请求,
 * 而我们的 /api/chat 是 POST(要带消息体)。
 * 所以用 fetch + ReadableStream 手动实现 SSE 解析:
 * fetch 拿到的是"边收边读"的数据流,我们把字节解码成文本,
 * 按 SSE 规范(事件之间以空行分隔)切出一条条事件。
 *
 * handlers 按事件类型回调:
 *   onContent  AI 回复的文字片段(每收到一段就往界面上拼一段)
 *   onError    错误信息
 */
export async function chatStream(message, handlers) {
  const res = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message }),
  })
  if (!res.ok || !res.body) throw new Error('请求失败')

  const reader = res.body.getReader() // 数据流读取器
  const decoder = new TextDecoder() // 字节 -> 文本(UTF-8,中文不乱码)
  let buf = '' // 缓冲区:网络是按包来的,可能半个事件半个事件地到

  while (true) {
    const { done, value } = await reader.read() // 读下一块数据
    if (done) break // 流结束
    buf += decoder.decode(value, { stream: true })

    // 每次尝试从缓冲区切出一个完整事件(SSE 事件以空行 \n\n 结尾)
    let idx
    while ((idx = buf.indexOf('\n\n')) !== -1) {
      const raw = buf.slice(0, idx) // 这个事件的原始文本
      buf = buf.slice(idx + 2) // 剩下的留回缓冲区

      // 解析事件:event: 行和 data: 行
      const parsed = {}
      for (const line of raw.split('\n')) {
        if (line.startsWith('event:')) parsed.event = line.slice(6).trim()
        else if (line.startsWith('data:')) parsed.data = line.slice(5).trim()
      }
      if (parsed.data === '[DONE]') return // 后端发来的结束标记
      if (!parsed.data) continue

      const payload = JSON.parse(parsed.data)
      // 按事件类型分发到对应的回调(没有对应回调就忽略)
      const handler = {
        content: handlers.onContent,
        error: handlers.onError,
      }[parsed.event]
      handler?.(payload)
    }
  }
}

"""智扫通机器人智能客服 —— 后端入口(API 层)

职责:只负责接收 HTTP 请求、返回响应,不写业务逻辑。
业务逻辑在 agent/react_agent.py(ReAct Agent)、rag/(向量检索)。

本文件涉及的概念:
- SSE(Server-Sent Events):服务端主动向浏览器"推送"数据的技术。
  普通 HTTP 是"一问一答",而 AI 生成文字是逐字产生的,
  用 SSE 就能让前端一个字一个字地显示,而不是等 10 秒一次性蹦出来。
- 流式响应(StreamingResponse):FastAPI 里返回 SSE 的方式,
  生成器每 yield 一次,就推送一段数据给前端。
"""
import json
import sys
from pathlib import Path

# 项目根目录加入 sys.path,保证 `from agent.react_agent import ReactAgent` 能正常导入
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from starlette.concurrency import iterate_in_threadpool, run_in_threadpool

from agent.react_agent import ReactAgent

app = FastAPI(title="智扫通机器人智能客服")

# CORS(跨域资源共享):允许浏览器从 5173 端口(Vue 开发服务器)调用 8000 端口的接口。
# 现在前端走的是 vite 代理(见 frontend/vite.config.js),其实不跨域了,但留着双保险。
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str  # 用户这轮说的话


# 懒加载单例:模型初始化较慢,第一次对话时才创建(和 Streamlit 版按需初始化一致)
_agent: ReactAgent | None = None


def get_agent() -> ReactAgent:
    global _agent
    if _agent is None:
        _agent = ReactAgent()
    return _agent


def _sse(event: str, data: dict) -> str:
    """把一段数据包装成 SSE 规范格式。

    SSE 格式要求:
      event: 事件类型(前端按类型分发)
      data: 数据(JSON 字符串;json.dumps 会把内容里的换行转义成 \\n,不会破坏事件分帧)
      最后空一行表示这条事件结束
    """
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


# ---------- 接口 ----------

@app.get("/api/health")
async def health():
    """健康检查:确认后端活着,前端/运维调试用"""
    return {"status": "ok"}


@app.post("/api/chat")
async def chat(req: ChatRequest):
    """核心接口:流式对话。

    前端发送 {message},这里返回一条 SSE 流,事件类型有 2 种:
    - content: AI 回复的文字片段(流式,一段一段来)
    - error:   出错信息

    注意:excute_stream 是同步生成器,全部放到后台线程里跑,
    避免阻塞 FastAPI 的事件循环。
    """

    async def stream():
        try:
            agent = await run_in_threadpool(get_agent)  # 模型初始化慢,放后台线程
            # iterate_in_threadpool 返回异步生成器,必须 async for(同步生成器的迭代发生在后台线程)
            async for chunk in iterate_in_threadpool(agent.excute_stream(req.message)):
                if chunk:  # 跳过空片段
                    yield _sse("content", {"content": chunk})
        except Exception as e:
            yield _sse("error", {"error": str(e)})
        # SSE 的结束标记,前端收到后停止读取
        yield "data: [DONE]\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")

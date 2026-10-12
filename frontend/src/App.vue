<script setup>
// App.vue 是"总控":管理聊天消息状态、调后端流式接口
//
// 两个全局状态:
// - messages  聊天记录 [{role: 'user'|'assistant', content}]
// - streaming 是否正在等 AI 回复(控制发送按钮 loading、禁用输入)
//
// 数据流向:用户输入 -> send() 调后端 -> SSE 流式事件逐步拼到消息上
// -> ChatPanel 通过 props 拿到状态自动渲染(响应式,状态一变界面就变)
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import ChatPanel from './components/ChatPanel.vue'
import { chatStream } from './api'

const messages = ref([])
const streaming = ref(false)

// 发送消息(核心逻辑)
async function send(text) {
  // 先把自己说的话显示出来,并放一个空的 AI 气泡占位(流式往里填)
  messages.value.push({ role: 'user', content: text })
  messages.value.push({ role: 'assistant', content: '' })
  streaming.value = true
  try {
    await chatStream(text, {
      // AI 回复的每个片段:拼到最后一个气泡(也就是刚才的空占位)上
      onContent: ({ content }) => {
        messages.value[messages.value.length - 1].content += content
      },
      onError: ({ error }) => ElMessage.error(error),
    })
  } catch (e) {
    ElMessage.error(e.message || '请求失败,请确认后端已启动')
  } finally {
    streaming.value = false
  }
}
</script>

<template>
  <div class="app">
    <header class="app-header">
      <div class="title">🤖 智扫通机器人智能客服</div>
    </header>

    <main class="app-main">
      <ChatPanel :messages="messages" :streaming="streaming" @send="send" />
    </main>
  </div>
</template>

<style>
/* 全局基础样式 */
* {
  box-sizing: border-box;
}
html,
body,
#app {
  height: 100%;
  margin: 0;
}
.app {
  display: flex;
  flex-direction: column;
  height: 100%;
  font-family: -apple-system, 'PingFang SC', 'Microsoft YaHei', sans-serif;
}
.app-header {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 52px;
  padding: 0 20px;
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  flex-shrink: 0;
}
.app-header .title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}
/* 主体:聊天面板占满;min-height:0 让子元素能正确滚动 */
.app-main {
  display: flex;
  flex: 1;
  min-height: 0;
}
</style>

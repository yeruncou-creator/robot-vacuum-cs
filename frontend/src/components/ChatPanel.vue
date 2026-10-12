<script setup>
// 聊天面板:消息列表 + 输入框
// 自己不管数据,数据由父组件(App.vue)通过 props 传进来,
// 发消息也只是 emit 事件让父组件处理 —— 这就是 Vue 的"单向数据流"
import { nextTick, ref, watch } from 'vue'

const props = defineProps({
  messages: { type: Array, required: true }, // 聊天记录
  streaming: { type: Boolean, default: false }, // 是否正在等 AI 回复
})
const emit = defineEmits(['send'])

const input = ref('')
const listRef = ref(null) // 消息列表 DOM,用来滚到底部

// 轻量 markdown 渲染:AI 回复里带 **加粗** 和换行,
// 这里只处理这两种(完整 markdown 库太重,没必要)
function renderMd(text) {
  return text
    .replace(/\*\*(.+?)\*\*/g, '<b>$1</b>')
    .replace(/\n/g, '<br>')
}

function send() {
  const text = input.value.trim()
  if (!text) return
  emit('send', text)
  input.value = ''
}

// 监听消息内容变化,变化后自动滚动到列表底部
// (watch 的内容拼接成字符串当"指纹",只要有一条消息变了就触发)
watch(
  () => props.messages.map((m) => m.content).join('|'),
  async () => {
    await nextTick() // 等 DOM 更新完再滚,否则还滚不到新消息的位置
    listRef.value?.scrollTo({ top: listRef.value.scrollHeight })
  },
)
</script>

<template>
  <div class="chat-panel">
    <!-- 消息列表 -->
    <div ref="listRef" class="msg-list">
      <!-- 空状态:引导用户说第一句话 -->
      <div v-if="!messages.length" class="empty-tip">
        <div class="empty-title">👋 你好,我是智扫通智能客服</div>
        <p>扫地机器人和扫拖一体机器人的专业客服,选购、使用、保养、故障处理都可以问我。</p>
        <p>例:"机器人回充失败怎么办?"</p>
        <p>例:"帮我生成我的使用报告"</p>
      </div>

      <!-- 每条消息一行:user 靠右蓝色,assistant 靠左灰色 -->
      <div
        v-for="(m, i) in messages"
        :key="i"
        class="msg-row"
        :class="m.role === 'user' ? 'from-user' : 'from-ai'"
      >
        <div class="avatar">{{ m.role === 'user' ? '我' : 'AI' }}</div>
        <!-- v-html 渲染 markdown;AI 空占位时显示省略号表示"正在输入" -->
        <div class="bubble" v-html="renderMd(m.content) || '<i>…</i>'"></div>
      </div>
    </div>

    <!-- 输入区:Enter 发送,Shift+Enter 换行;等 AI 回复时禁用输入 -->
    <div class="input-bar">
      <el-input
        v-model="input"
        type="textarea"
        :rows="2"
        resize="none"
        placeholder="输入你的问题,Enter 发送,Shift+Enter 换行"
        :disabled="streaming"
        @keydown.enter.exact.prevent="send"
      />
      <el-button
        type="primary"
        :loading="streaming"
        :disabled="!input.trim()"
        @click="send"
      >
        发送
      </el-button>
    </div>
  </div>
</template>

<style scoped>
/* scoped:样式只作用于本组件,避免和其他组件互相污染 */
.chat-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  flex: 1; /* 占满父容器(app-main)的剩余宽度 */
  min-width: 0;
}
.msg-list {
  flex: 1; /* 占满剩余高度 */
  overflow-y: auto; /* 消息多了在列表内部滚动 */
  padding: 20px;
}
.empty-tip {
  margin-top: 15vh;
  text-align: center;
  color: #909399;
}
.empty-title {
  font-size: 18px;
  color: #606266;
  margin-bottom: 12px;
}
.msg-row {
  display: flex;
  gap: 10px;
  margin-bottom: 16px;
}
.msg-row.from-user {
  flex-direction: row-reverse; /* 自己的消息头像在右 */
}
.avatar {
  flex-shrink: 0;
  width: 34px;
  height: 34px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  color: #fff;
}
.from-ai .avatar {
  background: #409eff;
}
.from-user .avatar {
  background: #67c23a;
}
.bubble {
  max-width: 78%;
  padding: 10px 14px;
  border-radius: 10px;
  line-height: 1.7;
  white-space: normal;
  word-break: break-word; /* 长内容自动换行,不撑破气泡 */
}
.from-ai .bubble {
  background: #f4f4f5;
  color: #303133;
  border-top-left-radius: 2px; /* 贴头像一侧的圆角收小,更像气泡 */
}
.from-user .bubble {
  background: #409eff;
  color: #fff;
  border-top-right-radius: 2px;
}
.input-bar {
  display: flex;
  gap: 10px;
  padding: 12px 16px;
  border-top: 1px solid #ebeef5;
  align-items: flex-end;
}
/* :deep() 穿透 scoped,改 Element Plus 组件内部的输入框字号 */
.input-bar :deep(.el-textarea__inner) {
  font-size: 14px;
}
</style>

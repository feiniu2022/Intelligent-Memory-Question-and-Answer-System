<template>
  <div class="chat-page">
    <div class="chat-messages" ref="messagesRef">
      <div v-for="(msg, i) in messages" :key="i" :class="['msg-row', msg.role]">
        <div :class="['msg-bubble', msg.role]">
          <div class="msg-content" v-html="renderMarkdown(msg.content)"></div>
          <div class="msg-time">{{ msg.time }}</div>
        </div>
      </div>
      <div v-if="streaming" class="msg-row assistant">
        <div class="msg-bubble assistant typing">
          <div class="msg-content">{{ streamContent }}</div>
        </div>
      </div>
    </div>
    <div class="chat-input">
      <el-input
        v-model="inputText"
        placeholder="输入消息..."
        @keydown.enter="sendMessage"
        :disabled="sending"
      >
        <template #append>
          <el-button :icon="Promotion" @click="sendMessage" :loading="sending" />
        </template>
      </el-input>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick, onMounted } from 'vue'
import { useUserStore } from '../stores/user'
import { chat as chatApi } from '../api/modules'
import { Promotion } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const userStore = useUserStore()
const messages = ref([])
const inputText = ref('')
const sending = ref(false)
const streaming = ref(false)
const streamContent = ref('')
const messagesRef = ref(null)

function getTime() {
  return new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

function renderMarkdown(text) {
  return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/\n/g, '<br>')
}

async function sendMessage() {
  const text = inputText.value.trim()
  if (!text || sending.value) return

  const userId = userStore.isLoggedIn ? userStore.userId : 'default_user'
  messages.value.push({ role: 'user', content: text, time: getTime() })
  inputText.value = ''
  sending.value = true

  try {
    const res = await chatApi.send(text, userId)
    messages.value.push({ role: 'assistant', content: res.data.reply, time: getTime() })
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '发送失败')
  } finally {
    sending.value = false
    await nextTick()
    scrollToBottom()
  }
}

function scrollToBottom() {
  if (messagesRef.value) {
    messagesRef.value.scrollTop = messagesRef.value.scrollHeight
  }
}

onMounted(() => {
  messages.value.push({ role: 'assistant', content: '你好！我是智能记忆问答助手，具有长期记忆和知识库检索能力。请问有什么可以帮你？', time: getTime() })
})
</script>

<style scoped>
.chat-page { display: flex; flex-direction: column; height: calc(100vh - 40px); max-width: 900px; margin: 0 auto; }
.chat-messages { flex: 1; overflow-y: auto; padding: 20px; }
.msg-row { margin-bottom: 16px; display: flex; }
.msg-row.user { justify-content: flex-end; }
.msg-row.assistant { justify-content: flex-start; }
.msg-bubble { max-width: 70%; padding: 12px 16px; border-radius: 12px; line-height: 1.6; font-size: 14px; }
.msg-bubble.user { background: #409eff; color: #fff; border-bottom-right-radius: 4px; }
.msg-bubble.assistant { background: #fff; color: #303133; border-bottom-left-radius: 4px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
.msg-bubble.typing { opacity: 0.7; }
.msg-time { font-size: 11px; color: #909399; margin-top: 4px; text-align: right; }
.msg-bubble.assistant .msg-time { text-align: left; }
.chat-input { padding: 16px 20px; background: #fff; border-top: 1px solid #ebeef5; }
</style>
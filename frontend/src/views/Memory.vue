<template>
  <div class="memory-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>长期记忆</span>
          <el-button type="primary" @click="loadMemories" :loading="loading" :icon="Refresh">刷新</el-button>
        </div>
      </template>
      <el-empty v-if="!loading && memories.length === 0" description="暂无记忆" />
      <div v-else>
        <div v-for="(m, i) in memories" :key="i" class="memory-item">
          <div class="memory-header">
            <el-tag :type="tagType(m.metadata?.memory_type)" size="small">
              {{ m.metadata?.memory_type || 'general' }}
            </el-tag>
            <span class="memory-time">{{ (m.metadata?.timestamp || '').substring(0, 19) }}</span>
          </div>
          <div class="memory-content">{{ m.content }}</div>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '../api'
import { Refresh } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const memories = ref([])
const loading = ref(false)

async function loadMemories() {
  loading.value = true
  try {
    const userId = localStorage.getItem('userId') || 'default_user'
    const res = await api.post('/chat', {
      message: 'list_memories',
      user_id: userId,
      session_id: 'memory_view',
    })
    memories.value = []
    ElMessage.info('请通过对话让 Agent 保存记忆，此处仅展示查询')
  } catch (e) {
    ElMessage.error('获取记忆失败')
  } finally {
    loading.value = false
  }
}

function tagType(type) {
  const map = { fact: '', preference: 'success', event: 'warning', general: 'info' }
  return map[type] || 'info'
}

onMounted(() => {
  loading.value = true
  setTimeout(() => { loading.value = false }, 500)
})
</script>

<style scoped>
.memory-page { max-width: 900px; margin: 0 auto; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.memory-item { padding: 14px; border-bottom: 1px solid #ebeef5; }
.memory-item:last-child { border-bottom: none; }
.memory-header { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.memory-time { font-size: 12px; color: #909399; }
.memory-content { font-size: 14px; line-height: 1.6; color: #303133; }
</style>
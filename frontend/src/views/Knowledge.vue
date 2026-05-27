<template>
  <div class="knowledge-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>知识库管理</span>
          <div class="card-actions">
            <el-upload :http-request="handleUpload" :show-file-list="false" accept=".txt,.md,.pdf,.docx,.pptx">
              <el-button type="primary" :icon="Upload">上传文档</el-button>
            </el-upload>
          </div>
        </div>
      </template>
      <el-table :data="files" v-loading="loading" stripe>
        <el-table-column prop="filename" label="文件名" min-width="200" />
        <el-table-column prop="source" label="格式" width="100" />
        <el-table-column prop="total_chunks" label="分块数" width="100" />
        <el-table-column prop="timestamp" label="上传时间" width="180">
          <template #default="{ row }">
            {{ (row.timestamp || '').substring(0, 19) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100">
          <template #default="{ row }">
            <el-button type="danger" link @click="handleDelete(row.filename)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-card style="margin-top: 20px;">
      <template #header><span>知识库检索</span></template>
      <el-input v-model="searchQuery" placeholder="输入搜索关键词" @keydown.enter="handleSearch">
        <template #append>
          <el-button :icon="Search" @click="handleSearch" :loading="searching">搜索</el-button>
        </template>
      </el-input>
      <div v-if="searchResults.length" style="margin-top: 16px;">
        <div v-for="(r, i) in searchResults" :key="i" class="search-result">
          <div class="result-header">
            <el-tag size="small">{{ r.metadata?.filename || '?' }}</el-tag>
            <el-tag size="small" type="info">score: {{ r.score }}</el-tag>
          </div>
          <div class="result-content">{{ r.content }}</div>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useUserStore } from '../stores/user'
import { knowledge } from '../api/modules'
import { Upload, Search } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'

const userStore = useUserStore()
const files = ref([])
const loading = ref(false)
const searchQuery = ref('')
const searchResults = ref([])
const searching = ref(false)

function getUserId() {
  return userStore.isLoggedIn ? userStore.userId : 'default_user'
}

async function loadFiles() {
  loading.value = true
  try {
    const res = await knowledge.list(getUserId())
    files.value = res.data.files || []
  } finally {
    loading.value = false
  }
}

async function handleUpload({ file }) {
  try {
    const res = await knowledge.upload(file, getUserId())
    ElMessage.success(`上传成功: ${res.data.filename} (${res.data.chunks} chunks)`)
    loadFiles()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '上传失败')
  }
}

async function handleDelete(filename) {
  try {
    await ElMessageBox.confirm(`确定删除 ${filename}?`, '确认')
    await knowledge.delete(filename, getUserId())
    ElMessage.success('删除成功')
    loadFiles()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('删除失败')
  }
}

async function handleSearch() {
  if (!searchQuery.value.trim()) return
  searching.value = true
  try {
    const res = await knowledge.search(searchQuery.value, 5, getUserId())
    searchResults.value = res.data.results || []
  } catch (e) {
    ElMessage.error('搜索失败')
  } finally {
    searching.value = false
  }
}

onMounted(loadFiles)
</script>

<style scoped>
.knowledge-page { max-width: 900px; margin: 0 auto; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.card-actions { display: flex; gap: 10px; }
.search-result { padding: 12px; margin-bottom: 12px; background: #f9f9f9; border-radius: 8px; }
.result-header { display: flex; gap: 8px; margin-bottom: 8px; }
.result-content { font-size: 13px; color: #606266; line-height: 1.6; }
</style>
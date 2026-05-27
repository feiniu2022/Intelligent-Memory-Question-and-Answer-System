<template>
  <div class="login-wrap">
    <el-card class="login-card">
      <h2 class="login-title">智能记忆问答 Agent</h2>
      <el-tabs v-model="activeTab">
        <el-tab-pane label="登录" name="login">
          <el-form :model="loginForm" @submit.prevent="handleLogin">
            <el-form-item>
              <el-input v-model="loginForm.username" placeholder="用户名" :prefix-icon="User" />
            </el-form-item>
            <el-form-item>
              <el-input v-model="loginForm.password" type="password" placeholder="密码" :prefix-icon="Lock" show-password />
            </el-form-item>
            <el-button type="primary" style="width:100%" :loading="loading" native-type="submit">登录</el-button>
          </el-form>
        </el-tab-pane>
        <el-tab-pane label="注册" name="register">
          <el-form :model="regForm" @submit.prevent="handleRegister">
            <el-form-item>
              <el-input v-model="regForm.username" placeholder="用户名（3-32字符）" :prefix-icon="User" />
            </el-form-item>
            <el-form-item>
              <el-input v-model="regForm.password" type="password" placeholder="密码（6-128字符）" :prefix-icon="Lock" show-password />
            </el-form-item>
            <el-button type="success" style="width:100%" :loading="loading" native-type="submit">注册</el-button>
          </el-form>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'
import { useUserStore } from '../stores/user'

const router = useRouter()
const userStore = useUserStore()

const activeTab = ref('login')
const loading = ref(false)
const loginForm = ref({ username: '', password: '' })
const regForm = ref({ username: '', password: '' })

async function handleLogin() {
  if (!loginForm.value.username || !loginForm.value.password) {
    ElMessage.warning('请输入用户名和密码')
    return
  }
  loading.value = true
  try {
    await userStore.login(loginForm.value.username, loginForm.value.password)
    ElMessage.success('登录成功')
    router.push('/')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '登录失败')
  } finally {
    loading.value = false
  }
}

async function handleRegister() {
  if (!regForm.value.username || !regForm.value.password) {
    ElMessage.warning('请输入用户名和密码')
    return
  }
  loading.value = true
  try {
    await userStore.register(regForm.value.username, regForm.value.password)
    ElMessage.success('注册成功')
    router.push('/')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '注册失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-wrap { height: 100vh; display: flex; align-items: center; justify-content: center; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
.login-card { width: 400px; border-radius: 12px; }
.login-title { text-align: center; margin-bottom: 20px; color: #303133; }
</style>
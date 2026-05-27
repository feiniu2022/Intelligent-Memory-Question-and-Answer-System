<template>
  <el-container class="app-container" v-if="isLoggedIn">
    <el-aside width="220px" class="app-aside">
      <div class="logo">
        <el-icon :size="24"><ChatDotRound /></el-icon>
        <span>智能问答</span>
      </div>
      <el-menu :default-active="currentRoute" router class="app-menu">
        <el-menu-item index="/">
          <el-icon><ChatDotRound /></el-icon>
          <span>对话</span>
        </el-menu-item>
        <el-menu-item index="/rag">
          <el-icon><Search /></el-icon>
          <span>RAG 检索</span>
        </el-menu-item>
        <el-menu-item index="/knowledge">
          <el-icon><FolderOpened /></el-icon>
          <span>知识库</span>
        </el-menu-item>
        <el-menu-item index="/memory">
          <el-icon><Collection /></el-icon>
          <span>记忆</span>
        </el-menu-item>
        <el-menu-item index="/audit">
          <el-icon><Document /></el-icon>
          <span>审计日志</span>
        </el-menu-item>
      </el-menu>
      <div class="user-bar">
        <el-icon><User /></el-icon>
        <span>{{ username }}</span>
        <el-button link type="danger" @click="handleLogout">退出</el-button>
      </div>
    </el-aside>
    <el-main class="app-main">
      <router-view />
    </el-main>
  </el-container>
  <router-view v-else />
</template>

<script setup>
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useUserStore } from './stores/user'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

const isLoggedIn = computed(() => userStore.isLoggedIn)
const username = computed(() => userStore.username)
const currentRoute = computed(() => route.path)

function handleLogout() {
  userStore.logout()
  router.push('/login')
}
</script>

<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
html, body, #app { height: 100%; }
.app-container { height: 100vh; }
.app-aside { background: #304156; display: flex; flex-direction: column; }
.logo { height: 60px; display: flex; align-items: center; justify-content: center; gap: 8px; color: #fff; font-size: 18px; font-weight: bold; }
.app-menu { flex: 1; border-right: none; }
.app-menu .el-menu-item { color: #bfcbd9; }
.app-menu .el-menu-item.is-active { background: #263445; color: #409eff; }
.user-bar { padding: 12px 20px; color: #bfcbd9; display: flex; align-items: center; gap: 8px; border-top: 1px solid #3a4a5b; }
.app-main { background: #f5f7fa; padding: 20px; overflow: auto; }
</style>
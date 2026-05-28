<script setup lang="ts">
import {
  Bell,
  DataLine,
  Document,
  FolderOpened,
  Histogram,
  Setting,
} from '@element-plus/icons-vue'
</script>

<template>
  <el-container class="shell">
    <el-aside width="236px" class="sidebar">
      <div class="brand">
        <div class="brand-mark">Q</div>
        <div>
          <div class="brand-title">量化平台</div>
          <div class="brand-subtitle">日线模拟盘 MVP</div>
        </div>
      </div>
      <el-menu router default-active="/portfolios" class="nav">
        <el-menu-item index="/portfolios">
          <el-icon><Histogram /></el-icon>
          <span>组合管理</span>
        </el-menu-item>
        <el-menu-item index="/strategies">
          <el-icon><Document /></el-icon>
          <span>策略管理</span>
        </el-menu-item>
        <el-menu-item index="/market-data/cache">
          <el-icon><FolderOpened /></el-icon>
          <span>行情缓存</span>
        </el-menu-item>
        <el-menu-item index="/settings">
          <el-icon><Setting /></el-icon>
          <span>系统设置</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="topbar">
        <div class="topbar-left">
          <el-icon><DataLine /></el-icon>
          <span>A 股股票与 ETF 策略监控</span>
        </div>
        <el-button :icon="Bell" circle />
      </el-header>
      <el-main class="main">
        <RouterView />
      </el-main>
    </el-container>
  </el-container>
</template>

<style scoped>
.shell {
  min-height: 100vh;
}

.sidebar {
  border-right: 1px solid #dde3ee;
  background: #fff;
}

.brand {
  display: flex;
  gap: 12px;
  align-items: center;
  height: 72px;
  padding: 0 18px;
  border-bottom: 1px solid #edf0f6;
}

.brand-mark {
  display: grid;
  width: 36px;
  height: 36px;
  place-items: center;
  border-radius: 8px;
  color: #fff;
  background: #1f6feb;
  font-weight: 700;
}

.brand-title {
  font-weight: 700;
}

.brand-subtitle {
  margin-top: 2px;
  color: #7b8496;
  font-size: 12px;
}

.nav {
  border-right: 0;
}

.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid #dde3ee;
  background: #fff;
}

.topbar-left {
  display: flex;
  gap: 8px;
  align-items: center;
  color: #475569;
}

.main {
  padding: 20px;
}
</style>

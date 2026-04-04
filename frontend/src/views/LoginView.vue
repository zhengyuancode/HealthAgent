<template>
  <div class="login-container">
    <div class="login-card">
      <div class="logo-area">
        <el-icon class="logo-icon">
          <Plus />
        </el-icon>
        <h2>智能医疗助手</h2>
      </div>

      <el-form
        ref="formRef"
        :model="loginForm"
        :rules="rules"
        @submit.prevent="handleLogin"
      >
        <el-form-item prop="account">
          <el-input
            v-model.trim="loginForm.account"
            placeholder="请输入用户名或手机号"
            :prefix-icon="User"
            clearable
          />
        </el-form-item>

        <el-form-item prop="password">
          <el-input
            v-model="loginForm.password"
            type="password"
            placeholder="请输入密码"
            :prefix-icon="Lock"
            :show-password="true"
            clearable
            @keyup.enter="handleLogin"
          />
        </el-form-item>

        <el-form-item class="slider-form-item">
          <div class="slider-wrapper">
            <LoginSlideVerify
              ref="sliderRef"
              @verify-success="onVerifySuccess"
              @verify-fail="onVerifyFail"
            />
          </div>
        </el-form-item>

        <el-button
          type="primary"
          class="login-button"
          :loading="loading"
          :disabled="!isVerified"
          @click="handleLogin"
        >
          登录
        </el-button>
      </el-form>

      <div class="login-footer">
        <el-link @click="goToRegister">还没有账号？立即注册</el-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { ElMessage } from 'element-plus'
import LoginSlideVerify from '@/components/LoginSlideVerify.vue'
import request from '@/utils/request'
import { User, Lock, Plus } from '@element-plus/icons-vue'

const router = useRouter()
const userStore = useUserStore()

const formRef = ref()
const sliderRef = ref()
const loading = ref(false)
const isVerified = ref(false)

const loginForm = reactive({
  account: '',
  password: ''
})

const rules = {
  account: [
    { required: true, message: '请输入用户名或手机号', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 8, message: '密码至少 8 位', trigger: 'blur' }
  ]
}

const getErrorMessage = (error, fallback = '登录失败，请检查网络或联系管理员') => {
  const detail = error?.response?.data?.detail
  const message = error?.response?.data?.message

  if (typeof detail === 'string' && detail) return detail
  if (Array.isArray(detail) && detail.length > 0) {
    const first = detail[0]
    if (typeof first === 'string') return first
    if (first?.msg) return first.msg
  }
  if (typeof message === 'string' && message) return message

  return fallback
}

const onVerifySuccess = () => {
  isVerified.value = true
}

const onVerifyFail = () => {
  isVerified.value = false
}

const resetSlider = () => {
  isVerified.value = false
  sliderRef.value?.reset?.()
}

const handleLogin = async () => {
  if (!formRef.value) return

  try {
    await formRef.value.validate()
  } catch {
    return
  }

  if (!isVerified.value) {
    ElMessage.error('请完成滑块验证')
    return
  }

  loading.value = true

  try {
    const res = await request.post('/auth/login', {
      account: loginForm.account,
      password: loginForm.password
    })

    userStore.setToken(res.access_token)
    userStore.setUserInfo(res.user)

    ElMessage.success('登录成功')
    router.push('/chat')
  } catch (error) {
    ElMessage.error(getErrorMessage(error))
    console.error('Login error:', error)
    resetSlider()
  } finally {
    loading.value = false
  }
}

const goToRegister = () => {
  router.push('/register')
}
</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background-color: var(--light-gray);
  padding: 20px;
  box-sizing: border-box;
}

.login-card {
  width: 400px;
  max-width: 100%;
  background-color: var(--white);
  border-radius: var(--border-radius);
  box-shadow: var(--box-shadow);
  padding: 40px 30px;
  text-align: center;
  box-sizing: border-box;
}

.logo-area {
  margin-bottom: 30px;
}

.logo-icon {
  font-size: 48px;
  color: var(--primary-green);
  margin-bottom: 10px;
}

.login-card h2 {
  color: var(--dark-text);
  font-weight: 500;
  font-size: 20px;
}

.slider-form-item {
  width: 100%;
}

.slider-wrapper {
  width: 100%;
  overflow: hidden;
  box-sizing: border-box;
}

.login-button {
  width: 100%;
  height: 40px;
  margin-top: 20px;
}

.login-footer {
  margin-top: 20px;
  text-align: center;
}

.login-footer .el-link {
  color: var(--primary-green);
  text-decoration: none;
}

.login-footer .el-link:hover {
  text-decoration: underline;
}
</style>
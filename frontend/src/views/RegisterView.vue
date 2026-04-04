<template>
  <div class="register-container">
    <div class="register-card">
      <div class="logo-area">
        <el-icon class="logo-icon">
          <Plus />
        </el-icon>
        <h2>注册账户</h2>
      </div>

      <el-form
        ref="formRef"
        :model="registerForm"
        :rules="rules"
        @submit.prevent="handleRegister"
      >
        <el-form-item prop="phone">
          <el-input
            v-model.trim="registerForm.phone"
            placeholder="请输入手机号"
            :prefix-icon="Phone"
            clearable
          />
        </el-form-item>

        <el-form-item prop="username">
          <el-input
            v-model.trim="registerForm.username"
            placeholder="请输入用户名"
            :prefix-icon="User"
            clearable
          />
        </el-form-item>

        <el-form-item prop="password">
          <el-input
            v-model="registerForm.password"
            type="password"
            placeholder="请输入密码"
            :prefix-icon="Lock"
            :show-password="true"
            clearable
          />
        </el-form-item>

        <el-form-item prop="confirmPassword">
          <el-input
            v-model="registerForm.confirmPassword"
            type="password"
            placeholder="请确认密码"
            :prefix-icon="Lock"
            :show-password="true"
            clearable
            @keyup.enter="handleRegister"
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
          class="register-button"
          :loading="loading"
          :disabled="!isVerified"
          @click="handleRegister"
        >
          注册
        </el-button>
      </el-form>

      <div class="register-footer">
        <el-link @click="goToLogin">已有账号？立即登录</el-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import LoginSlideVerify from '@/components/LoginSlideVerify.vue'
import request from '@/utils/request'
import { User, Lock, Plus, Phone } from '@element-plus/icons-vue'

const router = useRouter()

const formRef = ref()
const sliderRef = ref()
const loading = ref(false)
const isVerified = ref(false)

const registerForm = reactive({
  phone: '',
  username: '',
  password: '',
  confirmPassword: ''
})

function validatePhone(rule, value, callback) {
  if (!value) {
    callback(new Error('请输入手机号'))
  } else if (!/^\d{6,20}$/.test(value)) {
    callback(new Error('手机号格式不正确'))
  } else {
    callback()
  }
}

function validateUsername(rule, value, callback) {
  if (!value) {
    callback(new Error('请输入用户名'))
  } else if (!/^[A-Za-z0-9_]{3,50}$/.test(value)) {
    callback(new Error('用户名只能包含字母、数字、下划线，长度 3-50 位'))
  } else {
    callback()
  }
}

function validatePassword(rule, value, callback) {
  if (!value) {
    callback(new Error('请输入密码'))
  } else if (value.length < 8) {
    callback(new Error('密码至少 8 位'))
  } else {
    callback()
  }
}

function validateConfirmPassword(rule, value, callback) {
  if (!value) {
    callback(new Error('请确认密码'))
  } else if (value !== registerForm.password) {
    callback(new Error('两次输入密码不一致'))
  } else {
    callback()
  }
}

const rules = {
  phone: [
    { validator: validatePhone, trigger: 'blur' }
  ],
  username: [
    { validator: validateUsername, trigger: 'blur' }
  ],
  password: [
    { validator: validatePassword, trigger: 'blur' }
  ],
  confirmPassword: [
    { validator: validateConfirmPassword, trigger: 'blur' }
  ]
}

const getErrorMessage = (error, fallback = '注册失败，请检查网络或联系管理员') => {
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

const handleRegister = async () => {
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
    const res = await request.post('/auth/register', {
      phone: registerForm.phone,
      username: registerForm.username,
      password: registerForm.password
    })

    ElMessage.success(res.message || '注册成功')
    router.push('/login')
  } catch (error) {
    ElMessage.error(getErrorMessage(error))
    console.error('Register error:', error)
    resetSlider()
  } finally {
    loading.value = false
  }
}

const goToLogin = () => {
  router.push('/login')
}
</script>

<style scoped>
.register-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background-color: var(--light-gray);
  padding: 20px;
  box-sizing: border-box;
}

.register-card {
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

.register-card h2 {
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

.register-button {
  width: 100%;
  height: 40px;
  margin-top: 20px;
}

.register-footer {
  margin-top: 20px;
  text-align: center;
}

.register-footer .el-link {
  color: var(--primary-green);
  text-decoration: none;
}

.register-footer .el-link:hover {
  text-decoration: underline;
}
</style>
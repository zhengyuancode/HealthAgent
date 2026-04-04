<template>
  <div class="login-container">
    <div class="login-card">
      <div class="logo-area">
        <el-icon class="logo-icon">
          <MedicalCare />
        </el-icon>
        <h2>智能医疗助手</h2>
      </div>
      
      <el-form 
        :model="loginForm" 
        :rules="rules" 
        ref="formRef"
        @submit.prevent="handleLogin"
      >
        <el-form-item prop="username">
          <el-input
            v-model="loginForm.username"
            placeholder="请输入用户名"
            :prefix-icon="User"
          />
        </el-form-item>
        
        <el-form-item prop="password">
          <el-input
            v-model="loginForm.password"
            type="password"
            placeholder="请输入密码"
            :prefix-icon="Lock"
            :show-password="true"
          />
        </el-form-item>
        
        <el-form-item>
          <LoginSlideVerify 
            @verify-success="onVerifySuccess"
            @verify-fail="onVerifyFail"
          />
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
import { User, Lock, MedicalCare } from '@element-plus/icons-vue'

const router = useRouter()
const formRef = ref()
const loading = ref(false)
const isVerified = ref(false)

const loginForm = reactive({
  username: '',
  password: ''
})

const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' }
  ]
}

const onVerifySuccess = () => {
  isVerified.value = true
}

const onVerifyFail = () => {
  isVerified.value = false
  ElMessage.error('验证失败，请重试')
}

const handleLogin = async () => {
  if (!isVerified.value) {
    ElMessage.error('请完成滑块验证')
    return
  }

  loading.value = true
  
  try {
    const res = await request.post('/user/login', {
      username: loginForm.username,
      password: loginForm.password
    })
    
    if (res.code === 200) {
      const userStore = useUserStore()
      userStore.setToken(res.data.token)
      userStore.setUserInfo(res.data.user)
      
      ElMessage.success('登录成功')
      router.push('/chat')
    } else {
      ElMessage.error(res.message || '登录失败')
    }
  } catch (error) {
    ElMessage.error('登录失败，请检查网络或联系管理员')
    console.error('Login error:', error)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;
  background-color: var(--light-gray);
}

.login-card {
  width: 400px;
  background-color: var(--white);
  border-radius: var(--border-radius);
  box-shadow: var(--box-shadow);
  padding: 40px 30px;
  text-align: center;
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

.login-button {
  width: 100%;
  height: 40px;
  margin-top: 20px;
}
</style>
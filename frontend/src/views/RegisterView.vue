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
        :model="registerForm" 
        :rules="rules" 
        ref="formRef"
        @submit.prevent="handleRegister"
      >
        <el-form-item prop="username">
          <el-input
            v-model="registerForm.username"
            placeholder="请输入用户名/手机号"
            :prefix-icon="User"
          />
        </el-form-item>
        
        <el-form-item prop="password">
          <el-input
            v-model="registerForm.password"
            type="password"
            placeholder="请输入密码"
            :prefix-icon="Lock"
            :show-password="true"
          />
        </el-form-item>
        
        <el-form-item prop="confirmPassword">
          <el-input
            v-model="registerForm.confirmPassword"
            type="password"
            placeholder="请确认密码"
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
import { useUserStore } from '@/stores/user'
import { ElMessage } from 'element-plus'
import LoginSlideVerify from '@/components/LoginSlideVerify.vue'
import request from '@/utils/request'
import { User, Lock, Plus } from '@element-plus/icons-vue'

const router = useRouter()
const formRef = ref()
const loading = ref(false)
const isVerified = ref(false)

const registerForm = reactive({
  username: '',
  password: '',
  confirmPassword: ''
})

const rules = {
  username: [
    { required: true, message: '请输入用户名/手机号', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码至少6位', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请确认密码', trigger: 'blur' },
    { validator: validatePassword, trigger: 'blur' }
  ]
}

function validatePassword(rule, value, callback) {
  if (value !== registerForm.password) {
    callback(new Error('两次输入密码不一致'))
  } else {
    callback()
  }
}

const onVerifySuccess = () => {
  isVerified.value = true
}

const onVerifyFail = () => {
  isVerified.value = false
  ElMessage.error('验证失败，请重试')
}

const handleRegister = async () => {
  if (!isVerified.value) {
    ElMessage.error('请完成滑块验证')
    return
  }

  loading.value = true
  
  try {
    const res = await request.post('/user/register', {
      username: registerForm.username,
      password: registerForm.password
    })
    
    if (res.code === 200) {
      ElMessage.success('注册成功')
      router.push('/login')
    } else {
      ElMessage.error(res.message || '注册失败')
    }
  } catch (error) {
    ElMessage.error('注册失败，请检查网络或联系管理员')
    console.error('Register error:', error)
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
  height: 100vh;
  background-color: var(--light-gray);
}

.register-card {
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

.register-card h2 {
  color: var(--dark-text);
  font-weight: 500;
  font-size: 20px;
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
import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    redirect: '/chat'
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/LoginView.vue')
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('@/views/RegisterView.vue')
  },
  {
    path: '/chat',
    name: 'Chat',
    component: () => import('@/views/ChatView.vue'),
    meta: { requiresAuth: true }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 全局前置守卫
router.beforeEach((to, from, next) => {
  // 检查本地存储中的token
  const token = localStorage.getItem('token')
  
  // 如果访问需要认证的路由且未登录，则重定向到登录页
  if (to.meta.requiresAuth && !token) {
    next('/login')
  } else if (to.path === '/login' && token) {
    // 如果已经登录却访问登录页，则重定向到聊天页
    next('/chat')
  } else if (to.path === '/register' && token) {
    // 如果已经登录却访问注册页，则重定向到聊天页
    next('/chat')
  } else {
    next()
  }
})

export default router
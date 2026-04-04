<template>
  <div class="slide-verify-container">
    <div class="slide-track" ref="track" @click="handleTrackClick">
      <div class="slide-track-fill" :style="{ width: `${position}%` }"></div>
      <div 
        ref="slider"
        class="slide-slider"
        :style="{ left: `${position}%` }"
        @mousedown="startDrag"
        @touchstart="startDrag"
      >
        <div class="slide-handle"></div>
      </div>
      <div class="slide-tip">{{ tipText }}</div>
    </div>
    <div 
      v-if="isVerified" 
      class="verify-success"
    >
      验证通过
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'

const emit = defineEmits(['verify-success', 'verify-fail'])

const track = ref(null)
const slider = ref(null)
const position = ref(0)
const isDragging = ref(false)
const isVerified = ref(false)
const startX = ref(0)
const startLeft = ref(0)
const trackRect = ref({ left: 0, width: 0 })

const tipText = computed(() => {
  if (isVerified.value) return '验证通过'
  return position.value >= 98 ? '松开验证' : '拖动滑块完成验证'
})

const updateTrackRect = () => {
  if (track.value) {
    trackRect.value = track.value.getBoundingClientRect()
  }
}

const startDrag = (e) => {
  e.preventDefault()
  if (isVerified.value) return
  
  isDragging.value = true
  const clientX = e.type.includes('mouse') ? e.clientX : e.touches[0].clientX
  startX.value = clientX
  startLeft.value = position.value
  
  // 更新滑槽尺寸
  updateTrackRect()
}

const onDrag = (e) => {
  if (!isDragging.value || isVerified.value) return
  
  e.preventDefault()
  const clientX = e.type.includes('mouse') ? e.clientX : e.touches[0].clientX
  const deltaX = clientX - startX.value
  const trackWidth = trackRect.value.width
  const newPosition = Math.max(0, Math.min(100, startLeft.value + (deltaX / trackWidth) * 100))
  
  position.value = newPosition
  
  // 如果滑块到达最右边，验证通过
  if (newPosition >= 98) {
    finishVerification()
  }
}

const finishVerification = () => {
  isDragging.value = false
  isVerified.value = true
  position.value = 100
  emit('verify-success')
}

const stopDrag = () => {
  isDragging.value = false
}

const handleTrackClick = (e) => {
  if (isVerified.value) return
  
  updateTrackRect()
  const rect = trackRect.value
  const clickX = e.clientX - rect.left
  const clickPercent = (clickX / rect.width) * 100
  
  // 限制在有效范围内
  position.value = Math.min(100, Math.max(0, clickPercent))
  
  // 如果接近最右边，直接验证通过
  if (position.value >= 98) {
    finishVerification()
  }
}

onMounted(() => {
  // 确保在组件挂载后获取尺寸
  setTimeout(updateTrackRect, 100)
  
  document.addEventListener('mousemove', onDrag)
  document.addEventListener('touchmove', onDrag)
  document.addEventListener('mouseup', stopDrag)
  document.addEventListener('touchend', stopDrag)
  
  // 监听窗口大小改变
  window.addEventListener('resize', updateTrackRect)
})

onUnmounted(() => {
  document.removeEventListener('mousemove', onDrag)
  document.removeEventListener('touchmove', onDrag)
  document.removeEventListener('mouseup', stopDrag)
  document.removeEventListener('touchend', stopDrag)
  window.removeEventListener('resize', updateTrackRect)
})
</script>

<style scoped>
.slide-verify-container {
  width: 100%;
  margin-top: 20px;
}

.slide-track {
  width: 100%;
  height: 40px;
  background-color: #f0f0f0;
  border-radius: 20px;
  position: relative;
  overflow: hidden;
  cursor: pointer;
  border: 1px solid #ddd;
  user-select: none;
}

.slide-track-fill {
  height: 100%;
  width: 0%;
  background-color: #2E7D32;
  border-radius: 20px;
  transition: width 0.1s ease;
}

.slide-slider {
  width: 40px;
  height: 40px;
  background-color: white;
  border-radius: 50%;
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  cursor: grab;
  box-shadow: 0 2px 10px rgba(0,0,0,0.2);
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid #ddd;
  transition: left 0.1s ease;
  z-index: 10;
}

.slide-slider:active {
  cursor: grabbing;
}

.slide-handle {
  width: 8px;
  height: 8px;
  background-color: #999;
  border-radius: 50%;
}

.slide-tip {
  position: absolute;
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
  font-size: 12px;
  color: #666;
  pointer-events: none;
}

.verify-success {
  margin-top: 10px;
  color: #2E7D32;
  font-weight: bold;
}
</style>
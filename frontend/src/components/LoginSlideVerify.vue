<template>
  <div class="slide-verify-container">
    <div class="slide-track" ref="track" @click="handleTrackClick">
      <div
      class="slide-track-fill"
      :class="{ dragging: isDragging }"
      :style="{ width: `${fillWidth}px` }"
    ></div>

      <div
        ref="slider"
        class="slide-slider"
        :class="{ dragging: isDragging, verified: isVerified }"
        :style="{ left: `${sliderLeft}px` }"
        @mousedown="startDrag"
        @touchstart="startDrag"
      >
        <div class="slide-handle"></div>
      </div>

      <div class="slide-tip">{{ tipText }}</div>
    </div>

    <div v-if="isVerified" class="verify-success">
      验证通过
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'

const emit = defineEmits(['verify-success', 'verify-fail'])

const track = ref(null)
const slider = ref(null)

const isDragging = ref(false)
const isVerified = ref(false)
const startX = ref(0)
const startLeft = ref(0)

const trackWidth = ref(0)
const sliderWidth = ref(40)
const sliderLeft = ref(0)

const maxLeft = computed(() => Math.max(0, trackWidth.value - sliderWidth.value))

const progressPercent = computed(() => {
  if (maxLeft.value <= 0) return 0
  return (sliderLeft.value / maxLeft.value) * 100
})

const fillWidth = computed(() => {
  if (sliderLeft.value <= 0 && !isVerified.value) return 0
  return Math.min(trackWidth.value, sliderLeft.value + sliderWidth.value / 2 + 2)
})

const tipText = computed(() => {
  if (isVerified.value) return '验证通过'
  return progressPercent.value >= 98 ? '松开验证' : '拖动滑块完成验证'
})

const updateTrackRect = () => {
  if (track.value) {
    const rect = track.value.getBoundingClientRect()
    trackWidth.value = rect.width
  }
  if (slider.value) {
    sliderWidth.value = slider.value.offsetWidth || 40
  }

  if (isVerified.value) {
    sliderLeft.value = maxLeft.value
  } else {
    sliderLeft.value = Math.min(sliderLeft.value, maxLeft.value)
  }
}

const reset = async () => {
  isDragging.value = false
  isVerified.value = false
  sliderLeft.value = 0
  await nextTick()
  updateTrackRect()
}

defineExpose({
  reset
})

const finishVerification = () => {
  isDragging.value = false
  isVerified.value = true
  sliderLeft.value = maxLeft.value
  emit('verify-success')
}

const startDrag = (e) => {
  e.preventDefault()
  if (isVerified.value) return

  updateTrackRect()

  isDragging.value = true
  const clientX = e.type.includes('mouse') ? e.clientX : e.touches[0].clientX
  startX.value = clientX
  startLeft.value = sliderLeft.value
}

const onDrag = (e) => {
  if (!isDragging.value || isVerified.value) return

  e.preventDefault()
  const clientX = e.type.includes('mouse') ? e.clientX : e.touches[0].clientX
  const deltaX = clientX - startX.value

  const newLeft = Math.max(0, Math.min(maxLeft.value, startLeft.value + deltaX))
  sliderLeft.value = newLeft

  if (progressPercent.value >= 98) {
    finishVerification()
  }
}

const stopDrag = () => {
  if (!isDragging.value) return

  if (!isVerified.value && progressPercent.value < 98) {
    sliderLeft.value = 0
    emit('verify-fail')
  }

  isDragging.value = false
}

const handleTrackClick = (e) => {
  if (isVerified.value) return

  updateTrackRect()

  const rect = track.value.getBoundingClientRect()
  const clickX = e.clientX - rect.left

  const targetLeft = clickX - sliderWidth.value / 2
  sliderLeft.value = Math.max(0, Math.min(maxLeft.value, targetLeft))

  if (progressPercent.value >= 98) {
    finishVerification()
  }
}

onMounted(() => {
  nextTick(updateTrackRect)

  document.addEventListener('mousemove', onDrag)
  document.addEventListener('touchmove', onDrag, { passive: false })
  document.addEventListener('mouseup', stopDrag)
  document.addEventListener('touchend', stopDrag)
  document.addEventListener('touchcancel', stopDrag)

  window.addEventListener('resize', updateTrackRect)
})

onUnmounted(() => {
  document.removeEventListener('mousemove', onDrag)
  document.removeEventListener('touchmove', onDrag)
  document.removeEventListener('mouseup', stopDrag)
  document.removeEventListener('touchend', stopDrag)
  document.removeEventListener('touchcancel', stopDrag)

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
  box-sizing: border-box;
}

.slide-track-fill {
  position: absolute;
  left: 0;
  top: 0;
  height: 100%;
  background-color: #2e7d32;
  border-radius: 20px;
  transition: width 0.1s ease;
}

.slide-track-fill.dragging {
  transition: none;
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
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.2);
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid #ddd;
  transition: left 0.1s ease;
  z-index: 10;
  box-sizing: border-box;
}

.slide-slider.dragging {
  transition: none;
  cursor: grabbing;
}

.slide-slider.verified {
  border-color: #2e7d32;
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
  white-space: nowrap;
}

.verify-success {
  margin-top: 10px;
  color: #2e7d32;
  font-weight: bold;
}
</style>
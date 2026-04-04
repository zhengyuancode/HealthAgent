<template>
  <div class="slide-verify-container">
    <slide-verify
      :width="300"
      :height="40"
      :success-text="'验证通过'"
      :tip-text="'拖动滑块完成验证'"
      @success="onSuccess"
      @fail="onFail"
    />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { SlideVerify } from 'vue-monoplasty-slide-verify'

const emit = defineEmits(['verify-success', 'verify-fail'])

const onSuccess = () => {
  emit('verify-success')
}

const onFail = () => {
  emit('verify-fail')
}
</script>

<style scoped>
.slide-verify-container {
  width: 100%;
  margin-top: 20px;
}
</style>
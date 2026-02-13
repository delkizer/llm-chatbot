<script setup lang="ts">
import { ref, onMounted } from 'vue'

const token = ref('dev-test-token')
const theme = ref('bwf')
const matchId = ref('test-match-001')
const chatbotRef = ref<HTMLElement | null>(null)

onMounted(() => {
  console.log('chatbot mounted:', chatbotRef.value?.tagName)
})
</script>

<template>
  <div class="sample-page">
    <h1>Vue 3 - spo-chatbot Sample</h1>

    <div class="controls">
      <label>Token:
        <input v-model="token" type="text" placeholder="JWT token" />
      </label>
      <label>Theme:
        <select v-model="theme">
          <option value="default">Default</option>
          <option value="bwf">BWF</option>
          <option value="bxl">BXL</option>
        </select>
      </label>
      <label>Match ID:
        <input v-model="matchId" type="text" placeholder="match ID" />
      </label>
    </div>

    <div class="chatbot-container">
      <spo-chatbot
        ref="chatbotRef"
        api-url="__CHATBOT_API_URL__"
        :token="token"
        :theme="theme"
        context-type="badminton"
        :match-id="matchId">
      </spo-chatbot>
    </div>
  </div>
</template>

<style>
* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}
body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: #f5f5f5;
  color: #333;
}
.sample-page {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 24px;
  min-height: 100vh;
}
h1 {
  font-size: 1.4rem;
  margin-bottom: 16px;
}
.controls {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
  align-items: center;
  margin-bottom: 20px;
  padding: 16px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}
.controls label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.9rem;
  font-weight: 500;
}
.controls input,
.controls select {
  padding: 6px 10px;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  font-size: 0.9rem;
}
.controls input {
  width: 180px;
}
.chatbot-container {
  width: 400px;
  height: 600px;
}
spo-chatbot {
  display: block;
  width: 100%;
  height: 100%;
}
</style>

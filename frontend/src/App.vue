<template>
  <div class="app">
    <nav class="nav">
      <router-link to="/">Panel</router-link>
      <router-link to="/edit">Editor</router-link>
    </nav>
    <main class="main">
      <router-view />
    </main>
  </div>
</template>

<script setup>
</script>

<style>
  * { box-sizing: border-box; }
  body { margin: 0; font-family: system-ui, sans-serif; background: #1a1a1a; color: #e0e0e0; }
  .app { min-height: 100vh; display: flex; flex-direction: column; }
  .nav { display: flex; gap: 1rem; padding: 0.75rem 1rem; background: #252525; border-bottom: 1px solid #333; }
  .nav a { color: #8af; text-decoration: none; }
  .nav a.router-link-active { color: #fff; font-weight: 600; }
  .main { flex: 1; padding: 1rem; }
</style>

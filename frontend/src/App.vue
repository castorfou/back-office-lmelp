<template>
  <div id="app">
    <router-view />
    <PassageDock />
  </div>
</template>

<script>
import PassageDock from './components/PassageDock.vue';

export default {
  name: 'App',
  components: { PassageDock },
};
</script>

<style>
/* Styles globaux importés depuis style.css */
</style>

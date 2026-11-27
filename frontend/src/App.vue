<template>
  <div id="app">
    <router-view />
    <!-- PROTOTYPE JETABLE (#418), jamais fusionné -->
    <PassageDock v-if="$route.query.variant === 'B'" />
    <ProtoBarLecteurs />
  </div>
</template>

<script>
import PassageDock from './components/prototype-lecteurs-passages/PassageDock.vue';
import ProtoBarLecteurs from './components/prototype-lecteurs-passages/ProtoBarLecteurs.vue';
import { charger } from './components/prototype-lecteurs-passages/store.js';

export default {
  name: 'App',
  components: { PassageDock, ProtoBarLecteurs },
  mounted() { charger(); },
};
</script>

<style>
/* Styles globaux importés depuis style.css */
</style>

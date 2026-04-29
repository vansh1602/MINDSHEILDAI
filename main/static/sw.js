<link rel="manifest" href="/manifest.json"> <script>
  if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => { navigator.serviceWorker.register('/sw.js'); });
  }
</script>
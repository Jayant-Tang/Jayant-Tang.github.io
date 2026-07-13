// 站点更新后自动激活新 Service Worker 并刷新页面
(function () {
  if (!('serviceWorker' in navigator)) {
    return;
  }

  var reloading = false;
  navigator.serviceWorker.addEventListener('controllerchange', function () {
    if (reloading) {
      return;
    }
    reloading = true;
    window.location.reload();
  });

  navigator.serviceWorker.register('/service-worker.js').then(function (reg) {
    reg.addEventListener('updatefound', function () {
      var worker = reg.installing;
      if (!worker) {
        return;
      }
      worker.addEventListener('statechange', function () {
        if (worker.state === 'installed' && navigator.serviceWorker.controller) {
          worker.postMessage({ type: 'SKIP_WAITING' });
        }
      });
    });
  }).catch(function (err) {
    console.error('service worker registration failed:', err);
  });
})();

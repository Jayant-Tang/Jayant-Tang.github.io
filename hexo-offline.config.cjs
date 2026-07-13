// hexo-offline / workbox-build 配置
// 新部署后让 Service Worker 尽快接管，避免长期停留在旧缓存页面
module.exports = {
  skipWaiting: true,
  clientsClaim: true,
};

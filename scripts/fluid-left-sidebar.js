'use strict';

const path = require('path');

hexo.extend.filter.register('theme_inject', function(injects) {
  injects.postLeft.file('default', path.join(hexo.base_dir, 'injects/post-left-sidebar.ejs'));
});

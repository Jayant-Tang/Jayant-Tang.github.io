'use strict';

// Override Fluid theme's word count:
// 1. Exclude code blocks
// 2. Count CJK characters individually, English as whole words
// Fluid uses: wordcount / awl → display, wordcount / (awl * wpm) → reading time

hexo.extend.filter.register('after_post_render', (data) => {
  // Remove <pre><code> blocks before counting
  const contentWithoutCode = data.content.replace(/<pre><code[\s\S]*?<\/code><\/pre>/g, '');

  // Strip remaining HTML
  const { stripHTML } = require('hexo-util');
  const text = stripHTML(contentWithoutCode);

  // Count CJK characters (each = 1)
  const cjk = (text.match(/[一-鿿㐀-䶿぀-ゟ゠-ヿ가-힯]/g) || []).length;

  // Count English words (sequences of Latin letters)
  const english = (text.match(/[a-zA-Z]+/g) || []).length;

  // Count digit sequences (e.g. "123" = 1)
  const digits = (text.match(/[0-9]+/g) || []).length;

  data.wordcount = cjk + english + digits;

  return data;
});

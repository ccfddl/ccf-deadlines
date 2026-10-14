/* Load ads only after this page has rendered conference content. */
(() => {
  'use strict';
  const selector = document.currentScript?.getAttribute('data-content-selector');
  if (!selector) return;
  let queued = false;
  let observer;
  const ready = () => !document.getElementById('initial-loading')
    && Boolean(document.querySelector(selector));

  function load() {
    queued = false;
    // Content may have disappeared while waiting for the next paint/idle period.
    if (!ready()) return;
    if (!document.querySelector('script[src^="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js"]')) {
      const script = document.createElement('script');
      script.async = true;
      script.src = 'https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-2114972416819347';
      script.crossOrigin = 'anonymous';
      document.head.appendChild(script);
    }
    observer.disconnect();
  }

  function schedule() {
    if (queued || !ready()) return;
    queued = true;
    window.requestAnimationFrame(() => {
      if (window.requestIdleCallback) window.requestIdleCallback(load, { timeout: 2000 });
      else window.setTimeout(load, 0);
    });
  }

  function watch() {
    observer = new MutationObserver(schedule);
    observer.observe(document.documentElement, {
      subtree: true,
      childList: true,
      attributes: true,
      attributeFilter: ['data-ad-content-ready'],
    });
    schedule();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', watch, { once: true });
  else watch();
})();

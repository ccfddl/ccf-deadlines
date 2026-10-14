/* The standalone policy and dialog share translated content and site language. */
(() => {
  const standalone = document.querySelector('[data-privacy-page]');
  const labels = {
    en: { policy: 'Privacy Policy', tracker: 'Tracker', skip: 'Skip to content', close: 'Close privacy policy', loading: 'Loading privacy policy…', error: 'Unable to load the privacy policy. ', open: 'Open the privacy policy page' },
    zh: { policy: '隐私政策', tracker: '会议追踪', skip: '跳转到正文', close: '关闭隐私政策', loading: '正在加载隐私政策…', error: '隐私政策加载失败。', open: '打开隐私政策页面' },
  };
  let dialog;
  let content;
  let policy;
  let opener;
  let revision = 0;
  const language = () => document.documentElement.lang.toLowerCase().startsWith('zh') ? 'zh' : 'en';

  function preferredLanguage() {
    const explicit = new URLSearchParams(location.search).get('lang');
    if (explicit === 'en' || explicit === 'zh') return explicit;
    try {
      const saved = localStorage.getItem('language_preference');
      if (saved === 'en' || saved === 'zh') return saved;
      if (localStorage.getItem('use_english') === 'true') return 'en';
    } catch (_) { /* The browser language remains available without storage. */ }
    return navigator.language.toLowerCase().startsWith('zh') ? 'zh' : 'en';
  }

  function translatePage() {
    if (!standalone) return;
    const lang = language();
    document.querySelectorAll('[data-privacy-language]').forEach((element) => {
      element.hidden = element.dataset.privacyLanguage !== lang;
    });
    document.querySelectorAll('[data-privacy-label]').forEach((element) => {
      element.textContent = labels[lang][element.dataset.privacyLabel];
    });
    document.title = `${labels[lang].policy} | CCFDDL`;
    document.querySelector('.site-nav')?.setAttribute('aria-label', lang === 'en' ? 'Main navigation' : '主导航');
    document.querySelector('.site-footer nav')?.setAttribute('aria-label', lang === 'en' ? 'Footer navigation' : '页脚导航');
  }

  function translateFooter() {
    document.querySelectorAll('.footer-links a[data-privacy-modal]').forEach((link) => {
      link.textContent = labels[language()].policy;
    });
  }

  function createDialog() {
    dialog = document.createElement('dialog');
    dialog.className = 'site-privacy-dialog';
    dialog.setAttribute('aria-labelledby', 'site-privacy-title');
    const header = document.createElement('div');
    header.className = 'site-privacy-header';
    const title = document.createElement('h2');
    title.id = 'site-privacy-title';
    const close = document.createElement('button');
    close.type = 'button';
    close.className = 'site-privacy-close';
    close.textContent = '×';
    close.autofocus = true;
    close.addEventListener('click', () => dialog.close());
    header.append(title, close);
    content = document.createElement('div');
    content.className = 'site-privacy-content';
    content.tabIndex = 0;
    content.setAttribute('role', 'region');
    content.setAttribute('aria-labelledby', 'site-privacy-title');
    dialog.append(header, content);
    dialog.addEventListener('click', (event) => {
      if (event.target !== dialog) return;
      const rect = dialog.getBoundingClientRect();
      if (event.clientX < rect.left || event.clientX > rect.right
        || event.clientY < rect.top || event.clientY > rect.bottom) dialog.close();
    });
    dialog.addEventListener('close', () => {
      revision += 1;
      content.removeAttribute('aria-busy');
      opener?.focus();
    });
    document.body.append(dialog);
  }

  async function renderPolicy() {
    const current = ++revision;
    const lang = language();
    const text = labels[lang];
    dialog.lang = lang === 'en' ? 'en' : 'zh-CN';
    dialog.querySelector('h2').textContent = text.policy;
    dialog.querySelector('button').setAttribute('aria-label', text.close);
    content.scrollTop = 0;
    if (content.dataset.loaded === lang) return;
    delete content.dataset.loaded;
    content.textContent = text.loading;
    content.setAttribute('aria-busy', 'true');
    try {
      policy ||= fetch('/privacy.html?v=3').then(async (response) => {
        if (!response.ok) throw new Error('Privacy policy unavailable');
        return new DOMParser().parseFromString(await response.text(), 'text/html');
      });
      const page = await policy;
      if (current !== revision || !dialog.open) return;
      const article = page.querySelector(`main [data-privacy-language="${lang}"]`);
      if (!article) throw new Error('Privacy policy translation missing');
      const copy = document.importNode(article, true);
      copy.querySelector('h1')?.remove();
      content.replaceChildren(...copy.childNodes);
      content.dataset.loaded = lang;
    } catch (_) {
      policy = undefined;
      if (current !== revision || !dialog.open) return;
      content.textContent = text.error;
      const fallback = document.createElement('a');
      fallback.href = `/privacy.html?lang=${lang}&v=3`;
      fallback.textContent = text.open;
      content.append(fallback);
    } finally {
      if (current === revision) content.removeAttribute('aria-busy');
    }
  }

  document.addEventListener('click', (event) => {
    const link = event.target.closest?.('a[data-privacy-modal]');
    if (!link || event.button !== 0 || event.metaKey || event.ctrlKey
      || event.shiftKey || event.altKey || typeof HTMLDialogElement === 'undefined'
      || typeof HTMLDialogElement.prototype.showModal !== 'function') return;
    event.preventDefault();
    if (!dialog) createDialog();
    if (dialog.open) return;
    opener = link;
    dialog.showModal();
    renderPolicy();
  });

  if (standalone) {
    document.documentElement.lang = preferredLanguage() === 'en' ? 'en' : 'zh-CN';
    translatePage();
    window.addEventListener('storage', (event) => {
      if (event.key === 'language_preference' || event.key === 'use_english') {
        document.documentElement.lang = preferredLanguage() === 'en' ? 'en' : 'zh-CN';
      }
    });
  }
  translateFooter();
  new MutationObserver(() => {
    translatePage();
    translateFooter();
    if (dialog?.open) renderPolicy();
  }).observe(document.documentElement, { attributes: true, attributeFilter: ['lang'] });
})();

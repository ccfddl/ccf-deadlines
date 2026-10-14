/* Share the published privacy policy with the in-page dialog. */
(() => {
  let dialog;
  let content;
  let policy;
  let opener;

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
    dialog.addEventListener('close', () => opener?.focus());
    document.body.append(dialog);
  }

  document.addEventListener('click', async (event) => {
    const link = event.target.closest?.('a[data-privacy-modal]');
    if (!link || event.button !== 0 || event.metaKey || event.ctrlKey
      || event.shiftKey || event.altKey || typeof HTMLDialogElement === 'undefined'
      || typeof HTMLDialogElement.prototype.showModal !== 'function') return;
    event.preventDefault();
    if (!dialog) createDialog();
    if (dialog.open) return;
    opener = link;
    const english = /^Privacy(?: Policy)?$/i.test(link.textContent.trim());
    dialog.querySelector('h2').textContent = english ? 'Privacy Policy' : '隐私政策';
    dialog.querySelector('button').setAttribute('aria-label', english ? 'Close privacy policy' : '关闭隐私政策');
    dialog.showModal();
    content.scrollTop = 0;
    if (content.dataset.loaded) return;
    content.textContent = english ? 'Loading privacy policy…' : '正在加载隐私政策…';
    content.setAttribute('aria-busy', 'true');
    try {
      policy ||= fetch('/privacy.html').then(async (response) => {
        if (!response.ok) throw new Error('Privacy policy unavailable');
        const page = new DOMParser().parseFromString(await response.text(), 'text/html');
        const main = page.querySelector('main');
        if (!main) throw new Error('Privacy policy content missing');
        main.querySelector('h1')?.remove();
        return main;
      });
      const main = await policy;
      content.replaceChildren(...Array.from(main.childNodes, (node) => document.importNode(node, true)));
      content.dataset.loaded = 'true';
    } catch (_) {
      policy = undefined;
      content.textContent = english ? 'Unable to load the privacy policy. ' : '隐私政策加载失败。';
      const fallback = document.createElement('a');
      fallback.href = '/privacy.html';
      fallback.textContent = english ? 'Open the privacy policy page' : '打开隐私政策页面';
      content.append(fallback);
    } finally {
      content.removeAttribute('aria-busy');
    }
  });
})();

  // Tema claro/oscuro (preferencia guardada solo en este navegador)
  (function () {
    var root = document.documentElement;
    try { var saved = localStorage.getItem('theme'); if (saved) root.setAttribute('data-theme', saved); } catch (e) {}
    document.getElementById('themeToggle').addEventListener('click', function () {
      var current = root.getAttribute('data-theme') ||
        (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
      var next = current === 'dark' ? 'light' : 'dark';
      root.setAttribute('data-theme', next);
      try { localStorage.setItem('theme', next); } catch (e) {}
    });
  })();

  // Filtros de proyectos
  (function () {
    var buttons = document.querySelectorAll('.filters button');
    var cards = document.querySelectorAll('#projectGrid .card');
    buttons.forEach(function (btn) {
      btn.addEventListener('click', function () {
        var f = btn.getAttribute('data-filter');
        buttons.forEach(function (b) { b.setAttribute('aria-pressed', b === btn ? 'true' : 'false'); });
        cards.forEach(function (c) {
          c.hidden = f !== 'all' && c.getAttribute('data-cat').split(' ').indexOf(f) === -1;
        });
      });
    });
  })();

  // Idioma: recordar la elección y sugerir la versión del idioma del navegador
  (function () {
    var page = document.documentElement.getAttribute('data-lang');
    var links = document.querySelectorAll('.lang-switch a');
    var stored = null;
    try { stored = localStorage.getItem('lang'); } catch (e) {}

    links.forEach(function (a) {
      a.addEventListener('click', function () {
        try { localStorage.setItem('lang', a.getAttribute('data-lang')); } catch (e) {}
        if (location.hash) a.setAttribute('href', a.getAttribute('href').split('#')[0] + location.hash);
      });
    });

    if (stored) return;
    var available = {};
    links.forEach(function (a) { available[a.getAttribute('data-lang')] = a; });
    var prefs = navigator.languages && navigator.languages.length ? navigator.languages : [navigator.language || ''];
    for (var i = 0; i < prefs.length; i++) {
      var code = String(prefs[i]).toLowerCase().slice(0, 2);
      if (!available[code]) continue;
      if (code !== page) showBanner(available[code]);
      return;
    }

    function showBanner(target) {
      var bar = document.createElement('div');
      bar.className = 'lang-banner';
      bar.setAttribute('lang', target.getAttribute('hreflang'));
      var text = document.createElement('span');
      text.textContent = target.getAttribute('data-suggest');
      var go = document.createElement('a');
      go.href = target.getAttribute('href');
      go.textContent = target.getAttribute('data-suggest-btn') + ' →';
      go.addEventListener('click', function () {
        try { localStorage.setItem('lang', target.getAttribute('data-lang')); } catch (e) {}
      });
      var close = document.createElement('button');
      close.type = 'button';
      close.setAttribute('aria-label', '×');
      close.textContent = '×';
      close.addEventListener('click', function () {
        try { localStorage.setItem('lang', page); } catch (e) {}
        bar.remove();
      });
      bar.appendChild(text); bar.appendChild(go); bar.appendChild(close);
      document.body.insertBefore(bar, document.querySelector('nav.top'));
    }
  })();

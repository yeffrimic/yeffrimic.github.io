  // Mapa del recorrido: línea entre etapas y un punto por capítulo (Leaflet + OpenStreetMap)
  (function () {
    var el = document.getElementById('routeMap');
    if (!el || !window.L) return;
    var points = [];
    try { points = JSON.parse(el.getAttribute('data-points')) || []; } catch (e) {}

    var map = L.map(el, { scrollWheelZoom: false });
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 18,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
    }).addTo(map);

    if (!points.length) {
      map.setView([12.5, -86.5], 5); // Centroamérica
      return;
    }

    var accent = getComputedStyle(document.documentElement).getPropertyValue('--accent').trim() || '#0f7a4f';
    var latlngs = points.map(function (p) { return [p.lat, p.lng]; });
    L.polyline(latlngs, { color: accent, weight: 4, opacity: 0.85 }).addTo(map);

    // Días en el mismo lugar (p. ej. un día de descanso): un solo punto con un enlace por capítulo
    var groups = {};
    points.forEach(function (p) {
      if (!p.href) return;
      var key = p.lat + ',' + p.lng;
      (groups[key] = groups[key] || []).push(p);
    });

    points.forEach(function (p, i) {
      var last = i === points.length - 1;
      var group = p.href ? groups[p.lat + ',' + p.lng] : null;
      if (group && group.length > 1 && group[group.length - 1] !== p) return; // lo dibuja el último del grupo
      var marker = L.circleMarker([p.lat, p.lng], {
        radius: last ? 9 : p.via ? 4 : 6, color: accent, weight: 2, fillColor: last ? accent : '#fff', fillOpacity: 1
      }).addTo(map);
      var label = document.createElement('div');
      var place = document.createElement('b');
      place.textContent = p.place;
      label.appendChild(place);
      if (group && group.length > 1) {
        group.forEach(function (g) {
          var link = document.createElement('a');
          link.href = g.href;
          link.textContent = g.title + ' →';
          label.appendChild(document.createElement('br'));
          label.appendChild(link);
        });
        marker.bindPopup(label);
      } else if (p.href) {
        // Con capítulo: el clic lleva directo al día; el nombre se ve al pasar el mouse
        label.appendChild(document.createElement('br'));
        label.appendChild(document.createTextNode(p.title));
        var cta = document.createElement('div');
        cta.className = 'cta';
        cta.textContent = (p.cta || '') + ' →';
        label.appendChild(cta);
        marker.bindTooltip(label, { direction: 'top', offset: [0, -8] });
        marker.on('click', function () { window.location.href = p.href; });
      } else {
        marker.bindPopup(label);
      }
    });

    map.fitBounds(L.latLngBounds(latlngs).pad(0.2), { maxZoom: 9 });
  })();

  // Carruseles tipo Instagram: puntos, contador y flechas en compu
  document.querySelectorAll('.carousel-wrap').forEach(function (w) {
    var track = w.querySelector('.carousel');
    var dots = w.querySelectorAll('.dots span');
    var count = w.querySelector('.count');
    var prev = w.querySelector('.nav.prev'), next = w.querySelector('.nav.next');
    var n = dots.length;
    function current() { return Math.round(track.scrollLeft / track.clientWidth); }
    function update() {
      var i = Math.max(0, Math.min(n - 1, current()));
      dots.forEach(function (d, k) { d.classList.toggle('on', k === i); });
      count.textContent = (i + 1) + '/' + n;
      prev.disabled = i === 0; next.disabled = i === n - 1;
    }
    function go(d) { track.scrollTo({ left: (current() + d) * track.clientWidth }); }
    prev.addEventListener('click', function () { go(-1); });
    next.addEventListener('click', function () { go(1); });
    track.addEventListener('scroll', function () { window.requestAnimationFrame(update); }, { passive: true });
    update();
  });

  // Copiar el enlace del capítulo para pegarlo en Facebook, LinkedIn, etc.
  (function () {
    var btn = document.querySelector('.copy-link');
    if (!btn) return;
    var url = btn.closest('.share').getAttribute('data-url');
    var label = btn.textContent;
    btn.addEventListener('click', function () {
      function done() {
        btn.textContent = btn.getAttribute('data-done');
        setTimeout(function () { btn.textContent = label; }, 2000);
      }
      if (navigator.clipboard) navigator.clipboard.writeText(url).then(done, function () { prompt('', url); });
      else prompt('', url);
    });
  })();

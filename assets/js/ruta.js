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

    points.forEach(function (p, i) {
      var last = i === points.length - 1;
      var marker = L.circleMarker([p.lat, p.lng], {
        radius: last ? 9 : p.via ? 4 : 6, color: accent, weight: 2, fillColor: last ? accent : '#fff', fillOpacity: 1
      }).addTo(map);
      var label = document.createElement('div');
      var place = document.createElement('b');
      place.textContent = p.place;
      label.appendChild(place);
      if (p.href) {
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

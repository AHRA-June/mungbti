/**
 * 멍BTI 결과 화면용 "우리 동네 보호견" 카드 위젯
 *
 * 사용법 (멍BTI 결과 페이지에 붙여넣기):
 *   <div id="mungbti-dogs"></div>
 *   <script src="https://ahra-june.github.io/mungbti-shelter/embed/card.js"
 *           data-target="mungbti-dogs"
 *           data-sido="서울특별시"
 *           data-sigungu="동대문구"
 *           data-traits="온순·친화,활발"
 *           data-count="3"><\/script>
 *
 * 원칙: 어떤 오류가 나도 호스트 페이지를 깨지 않는다 — 실패하면 아무것도 그리지 않는다.
 * 성향 표시는 보호소 기재 인용이며, 위젯 하단에 그 문구를 항상 노출한다.
 */
(function () {
  var script = document.currentScript;
  if (!script) return;
  var BASE = script.src.replace(/\/embed\/card\.js.*$/, "");
  var cfg = {
    target: script.getAttribute("data-target") || "mungbti-dogs",
    sido: script.getAttribute("data-sido") || "",
    sigungu: script.getAttribute("data-sigungu") || "",
    traits: (script.getAttribute("data-traits") || "").split(",").map(function (s) { return s.trim(); }).filter(Boolean),
    count: Math.min(parseInt(script.getAttribute("data-count") || "3", 10) || 3, 6),
  };

  function esc(s) { var d = document.createElement("span"); d.textContent = s || ""; return d.innerHTML; }

  function pick(rows) {
    var pool = rows;
    if (cfg.sigungu) {
      var local = rows.filter(function (r) { return (r.org || "").indexOf(cfg.sigungu) >= 0; });
      if (local.length >= cfg.count) pool = local;
      else pool = local.concat(rows.filter(function (r) { return local.indexOf(r) < 0; })); // 부족하면 시도 전체로 보충
    }
    if (cfg.traits.length) {
      pool = pool.slice().sort(function (a, b) {
        var sa = a.traits.filter(function (t) { return cfg.traits.indexOf(t) >= 0; }).length;
        var sb = b.traits.filter(function (t) { return cfg.traits.indexOf(t) >= 0; }).length;
        return sb - sa;
      });
    }
    // 사진 있는 개 우선
    pool = pool.slice().sort(function (a, b) { return (b.img ? 1 : 0) - (a.img ? 1 : 0); });
    return pool.slice(0, cfg.count);
  }

  function render(el, dogs, sidoName) {
    if (!dogs.length) return;
    var css = "" +
      ".mbd-wrap{font-family:'Apple SD Gothic Neo','Malgun Gothic',sans-serif;margin:16px 0}" +
      ".mbd-h{font-size:15px;font-weight:700;color:#245546;margin:0 0 10px}" +
      ".mbd-row{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px}" +
      ".mbd-card{border:1px solid #E6E1D4;border-radius:10px;overflow:hidden;background:#fff;text-decoration:none;color:#262219;display:block}" +
      ".mbd-img{width:100%;aspect-ratio:1/1;object-fit:cover;background:#E3EEE8;display:block}" +
      ".mbd-b{padding:8px 10px 10px;font-size:12px;line-height:1.5}" +
      ".mbd-k{font-weight:700;font-size:13px}" +
      ".mbd-t{display:inline-block;font-size:10.5px;padding:1px 7px;border-radius:999px;background:#E3EEE8;color:#245546;margin:3px 3px 0 0}" +
      ".mbd-t0{background:transparent;border:1px dashed #E6E1D4;color:#97906F}" +
      ".mbd-foot{font-size:10.5px;color:#97906F;margin-top:8px;line-height:1.5}" +
      ".mbd-more{font-size:12px;color:#245546;text-decoration:none;font-weight:700}";
    var style = document.createElement("style");
    style.textContent = css;
    document.head.appendChild(style);

    var pageLink = BASE + "/?sido=" + encodeURIComponent(cfg.sido || sidoName) +
      (cfg.sigungu ? "&sigungu=" + encodeURIComponent(cfg.sigungu) : "");
    var where = cfg.sigungu || sidoName || "우리 동네";
    var html = '<div class="mbd-wrap"><p class="mbd-h">🐕 ' + esc(where) + '에서 가족을 기다리는 아이들</p><div class="mbd-row">';
    dogs.forEach(function (r) {
      var tags = r.traits.length
        ? r.traits.slice(0, 2).map(function (t) { return '<span class="mbd-t">' + esc(t) + "</span>"; }).join("")
        : '<span class="mbd-t mbd-t0">성향 기재 없음</span>';
      html += '<a class="mbd-card" href="' + pageLink + '" target="_blank" rel="noopener">' +
        (r.img ? '<img class="mbd-img" loading="lazy" src="' + esc(r.img) + '" alt="" ' +
          'onerror="this.replaceWith(Object.assign(document.createElement(\'div\'),{className:\'mbd-img\'}))">'
          : '<div class="mbd-img"></div>') +
        '<div class="mbd-b"><div class="mbd-k">' + esc(r.kind || "믹스") + "</div>" +
        esc(r.age) + " · " + esc(r.weight) + "<br>" + tags + "</div></a>";
    });
    html += '</div><p class="mbd-foot">성향 표시는 보호센터 기재를 인용한 것으로, 실제 성격은 만나서 확인해 주세요 · ' +
      '<a class="mbd-more" href="' + pageLink + '" target="_blank" rel="noopener">더 많은 아이들 보기 →</a></p></div>';
    el.innerHTML = html;
  }

  try {
    fetch(BASE + "/data/index.json").then(function (r) { return r.json(); }).then(function (idx) {
      var sido = null;
      if (cfg.sido) sido = idx.sido.filter(function (s) { return s.name.indexOf(cfg.sido) >= 0 || s.code === cfg.sido; })[0];
      if (!sido) sido = idx.sido.slice().sort(function (a, b) { return b.count - a.count; })[0];
      if (!sido || !sido.count) return;
      fetch(BASE + "/data/regions/" + sido.code + ".json").then(function (r) { return r.json(); }).then(function (rows) {
        var el = document.getElementById(cfg.target);
        if (el) render(el, pick(rows), sido.name);
      }).catch(function () {});
    }).catch(function () {});
  } catch (e) { /* 위젯은 조용히 실패한다 */ }
})();

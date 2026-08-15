/* ============================================================
   SeraphIRC docs viewer
   ------------------------------------------------------------
   Turns the single documentation page into a help browser: the
   contents rail on the left picks one topic pane at a time on
   the right, deep links to individual commands still work, and
   the search box filters the whole tree.

   Everything here is progressive. With scripting off, the page
   is one long manual and the rail is <details> plus anchors.
   ============================================================ */
(function () {
  "use strict";

  var content = document.getElementById("docs-content");
  var nav = document.getElementById("docs-nav");
  if (!content || !nav) return;

  var panes = Array.prototype.slice.call(content.querySelectorAll("[data-pane]"));
  if (!panes.length) return;

  var navLinks = Array.prototype.slice.call(nav.querySelectorAll(".pagelist a"));
  var results = document.getElementById("docs-results");
  var search = document.getElementById("docs-search");
  var foot = document.getElementById("pane-foot");
  var rail = document.getElementById("docs-rail");
  var railToggle = document.getElementById("rail-toggle");

  /* id -> pane element, for every pane and every command entry inside one. */
  var owner = Object.create(null);
  panes.forEach(function (pane) {
    owner[pane.id] = pane;
    Array.prototype.forEach.call(pane.querySelectorAll("[id]"), function (node) {
      if (!owner[node.id]) owner[node.id] = pane;
    });
  });

  var linkByHref = Object.create(null);
  navLinks.forEach(function (link) {
    var id = link.getAttribute("href").slice(1);
    if (!linkByHref[id]) linkByHref[id] = link;
  });

  /* The rail's reading order doubles as the previous/next order. */
  var order = navLinks
    .map(function (link) { return link.getAttribute("href").slice(1); })
    .filter(function (id) { return owner[id]; });

  var baseTitle = document.title;
  var currentPane = null;

  function paneTitle(pane) {
    var heading = pane.querySelector("h2");
    return heading ? heading.textContent.trim() : pane.id;
  }

  function linkLabel(id) {
    var link = linkByHref[id];
    if (link) return link.textContent.trim();
    var node = document.getElementById(id);
    var heading = node && node.querySelector("h3, h2");
    return heading ? heading.textContent.replace(/#$/, "").trim() : id;
  }

  function openAncestors(node) {
    var parent = node.parentElement;
    while (parent && parent !== nav) {
      if (parent.tagName === "DETAILS") parent.open = true;
      parent = parent.parentElement;
    }
  }

  function markCurrent(id) {
    navLinks.forEach(function (link) { link.classList.remove("is-current"); });
    var link = linkByHref[id];
    if (!link) return;
    link.classList.add("is-current");
    openAncestors(link);
    /* Keep the highlighted row visible without yanking the whole page. */
    if (link.scrollIntoView) {
      var railBox = nav.getBoundingClientRect();
      var linkBox = link.getBoundingClientRect();
      if (linkBox.top < railBox.top || linkBox.bottom > railBox.bottom) {
        link.scrollIntoView({ block: "nearest" });
      }
    }
  }

  function renderFoot(id) {
    if (!foot) return;
    foot.innerHTML = "";
    var at = order.indexOf(id);
    if (at === -1) return;
    if (at > 0) foot.appendChild(footLink(order[at - 1], "Previous", "foot-prev"));
    if (at < order.length - 1) {
      foot.appendChild(footLink(order[at + 1], "Next", "foot-next"));
    }
  }

  function footLink(id, direction, css) {
    var link = document.createElement("a");
    link.className = css;
    link.href = "#" + id;
    var label = document.createElement("span");
    label.className = "foot-dir";
    label.textContent = direction;
    link.appendChild(label);
    link.appendChild(document.createTextNode(linkLabel(id)));
    return link;
  }

  function show(id, scroll) {
    var pane = owner[id];
    if (!pane) {
      pane = panes[0];
      id = pane.id;
    }

    if (pane !== currentPane) {
      panes.forEach(function (other) { other.classList.remove("is-active"); });
      pane.classList.add("is-active");
      currentPane = pane;
      document.title = paneTitle(pane) + " - " + baseTitle;
    }

    markCurrent(id);
    renderFoot(order.indexOf(id) === -1 ? pane.id : id);

    if (scroll === false) return;
    var anchor = id === pane.id ? null : document.getElementById(id);
    if (anchor) {
      anchor.scrollIntoView({ block: "start" });
    } else {
      var top = content.getBoundingClientRect().top + window.pageYOffset - 176;
      window.scrollTo(0, Math.max(top, 0));
    }
  }

  function currentId() {
    return decodeURIComponent(location.hash.replace(/^#/, ""));
  }

  window.addEventListener("hashchange", function () {
    show(currentId(), true);
    closeRailOnNarrow();
  });

  /* ── Contents search ─────────────────────────────────────── */

  var haystack = navLinks.map(function (link) {
    var id = link.getAttribute("href").slice(1);
    var node = document.getElementById(id);
    var summary = node ? node.querySelector(".entry-summary, .pane-lead") : null;
    var book = link.closest("details.chapter, details.book");
    var where = book ? book.querySelector("summary") : null;
    return {
      id: id,
      label: link.textContent.trim(),
      where: where ? where.textContent.replace(/\d+$/, "").trim() : "",
      text: (
        link.textContent + " " + (summary ? summary.textContent : "")
      ).toLowerCase(),
    };
  });

  function runSearch(term) {
    var query = term.trim().toLowerCase();
    if (!query) {
      nav.classList.remove("is-searching");
      results.innerHTML = "";
      return;
    }

    var hits = haystack.filter(function (item) {
      return item.text.indexOf(query) !== -1;
    });

    nav.classList.add("is-searching");
    results.innerHTML = "";
    if (!hits.length) {
      var empty = document.createElement("li");
      empty.className = "docs-empty";
      empty.textContent = 'Nothing matches "' + term.trim() + '"';
      results.appendChild(empty);
      return;
    }

    hits.slice(0, 60).forEach(function (item) {
      var row = document.createElement("li");
      var link = document.createElement("a");
      link.href = "#" + item.id;
      var name = document.createElement("code");
      name.textContent = item.label;
      link.appendChild(name);
      if (item.where) {
        var where = document.createElement("span");
        where.className = "res-where";
        where.textContent = item.where;
        link.appendChild(where);
      }
      row.appendChild(link);
      results.appendChild(row);
    });
  }

  if (search && results) {
    search.addEventListener("input", function () { runSearch(search.value); });
    search.addEventListener("keydown", function (event) {
      if (event.key !== "Enter") return;
      var first = results.querySelector("a");
      if (first) {
        event.preventDefault();
        first.click();
      }
    });
    /* Escape clears the box and puts the tree back. */
    search.addEventListener("keyup", function (event) {
      if (event.key === "Escape") {
        search.value = "";
        runSearch("");
      }
    });
  }

  /* ── Narrow screens: the rail collapses behind a button ──── */

  function isNarrow() {
    return window.matchMedia("(max-width: 960px)").matches;
  }

  function closeRailOnNarrow() {
    if (rail && railToggle && isNarrow()) {
      rail.hidden = true;
      railToggle.setAttribute("aria-expanded", "false");
    }
  }

  if (rail && railToggle) {
    railToggle.addEventListener("click", function () {
      var open = rail.hidden;
      rail.hidden = !open;
      railToggle.setAttribute("aria-expanded", open ? "true" : "false");
    });
    nav.addEventListener("click", function (event) {
      if (event.target.closest("a")) closeRailOnNarrow();
    });
    window.addEventListener("resize", function () {
      if (!isNarrow()) rail.hidden = false;
    });
    if (isNarrow()) closeRailOnNarrow();
  }

  /* ── Printing: open the whole contents tree ──────────────── */

  /* A closed <details> hides its content through the UA's own slot
     rendering, so no rule on the light-DOM children reaches it. The print
     stylesheet cannot expand the tree on its own, and a contents page with
     five empty headings on it is worse than none. Open every book for the
     duration of the print job, then put back exactly the ones that were
     shut, so the reader's rail looks untouched afterwards. */
  var reopenedForPrint = [];

  function expandForPrint() {
    if (reopenedForPrint.length) return; // already expanded for this job
    Array.prototype.forEach.call(nav.querySelectorAll("details:not([open])"), function (book) {
      reopenedForPrint.push(book);
      book.open = true;
    });
  }

  function collapseAfterPrint() {
    reopenedForPrint.forEach(function (book) { book.open = false; });
    reopenedForPrint = [];
  }

  window.addEventListener("beforeprint", expandForPrint);
  window.addEventListener("afterprint", collapseAfterPrint);

  /* Safari fired neither event until 13, and some engines only emit the
     media change. Listening to both is harmless: expandForPrint is
     idempotent and collapseAfterPrint is a no-op when nothing was opened. */
  if (window.matchMedia) {
    var printQuery = window.matchMedia("print");
    var onPrintChange = function (event) {
      if (event.matches) expandForPrint();
      else collapseAfterPrint();
    };
    if (printQuery.addEventListener) printQuery.addEventListener("change", onPrintChange);
    else if (printQuery.addListener) printQuery.addListener(onPrintChange);
  }

  /* Download as PDF. A page cannot write a file to disk on its own, so this
     hands over the print dialog, where "Save as PDF" is the destination. The
     print stylesheet lays the manual out one topic page to a sheet in
     whatever theme is selected, and expanding here rather than relying on
     beforeprint alone means the tree is already open if an engine paints its
     preview first. */
  var pdfButton = document.getElementById("docs-pdf");
  if (pdfButton) {
    pdfButton.addEventListener("click", function () {
      expandForPrint();
      var stamp = document.getElementById("docs-print-date");
      if (stamp) {
        try {
          stamp.textContent = new Date().toLocaleDateString(undefined, {
            year: "numeric", month: "long", day: "numeric"
          });
        } catch (e) {
          stamp.textContent = "";
        }
      }
      window.print();
    });
  }

  /* ── Scroll spy inside the active pane ───────────────────── */

  if ("IntersectionObserver" in window) {
    var spy = new IntersectionObserver(
      function (entries) {
        var visible = entries
          .filter(function (entry) { return entry.isIntersecting; })
          .sort(function (a, b) {
            return a.boundingClientRect.top - b.boundingClientRect.top;
          })[0];
        if (visible && linkByHref[visible.target.id]) {
          markCurrent(visible.target.id);
        }
      },
      { rootMargin: "-180px 0px -70% 0px", threshold: 0 }
    );
    panes.forEach(function (pane) {
      Array.prototype.forEach.call(pane.querySelectorAll(".docs-entry[id]"), function (entry) {
        spy.observe(entry);
      });
    });
  }

  show(currentId(), Boolean(location.hash));
})();

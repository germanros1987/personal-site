(function () {
  "use strict";

  function textElement(tag, className, text) {
    var element = document.createElement(tag);
    element.className = className;
    element.textContent = text;
    return element;
  }

  function publicationItem(publication) {
    var url = new URL(publication.url);
    if (url.protocol !== "https:" || url.hostname !== "scholar.google.co.jp" ||
        !url.searchParams.has("citation_for_view") ||
        typeof publication.title !== "string" || !publication.title.trim()) {
      throw new Error("Invalid publication");
    }
    var item = textElement("li", "scholar-publications__item", "");
    var heading = document.createElement("h3");
    var link = textElement("a", "", publication.title);
    link.href = url.href;
    heading.appendChild(link);
    item.appendChild(heading);
    if (publication.authors) {
      item.appendChild(textElement("p", "scholar-publications__authors", publication.authors));
    }
    var details = [publication.venue, publication.year].filter(Boolean).join(" · ");
    if (details) {
      item.appendChild(textElement("p", "scholar-publications__details", details));
    }
    return item;
  }

  document.querySelectorAll("[data-scholar-widget]").forEach(function (widget) {
    var list = widget.querySelector("[data-scholar-list]");
    var status = widget.querySelector("[data-scholar-status]");
    var controller = new AbortController();
    var timeout = setTimeout(function () { controller.abort(); }, 10000);

    fetch(widget.dataset.source, { signal: controller.signal })
      .then(function (response) {
        if (!response.ok) throw new Error("Publication feed unavailable");
        return response.json();
      })
      .then(function (data) {
        if (!Array.isArray(data.publications) || !data.publications.length) {
          throw new Error("Publication feed empty");
        }
        var fragment = document.createDocumentFragment();
        data.publications.slice(0, 10).forEach(function (publication) {
          fragment.appendChild(publicationItem(publication));
        });
        list.replaceChildren(fragment);
        status.hidden = true;
        var updated = new Date(data.updated_at);
        if (data.updated_at && !isNaN(updated.getTime())) {
          widget.querySelector("[data-scholar-updated]").textContent = "Updated " +
            updated.toLocaleDateString("en", { month: "long", day: "numeric", year: "numeric", timeZone: "UTC" });
        }
      })
      .catch(function () {
        // Preserve the rendered cache if Scholar or the feed cannot be reached.
        status.hidden = list.children.length > 0;
      })
      .finally(function () { clearTimeout(timeout); });
  });
}());

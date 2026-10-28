/* Apply the same self-hosted font to same-origin rich-text editor documents. */
(function () {
  "use strict";
  var current = document.currentScript;
  var cssURL = new URL("../css/tppc-vazirmatn.css", current.src).href;
  var selector = "iframe.tox-edit-area__iframe,iframe[id$='_ifr']";
  function apply(frame) {
    if (!frame.matches(selector)) return;
    try {
      var doc = frame.contentDocument;
      if (!doc || !doc.head || doc.getElementById("tppc-editor-font")) return;
      var link = doc.createElement("link");
      link.id = "tppc-editor-font";
      link.rel = "stylesheet";
      link.href = cssURL;
      doc.head.appendChild(link);
    } catch (error) { /* Cross-origin frames are outside the editor scope. */ }
  }
  document.addEventListener("load", function (event) {
    if (event.target && event.target.tagName === "IFRAME") apply(event.target);
  }, true);
  function scan() { document.querySelectorAll(selector).forEach(apply); }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", scan);
  else scan();
  new MutationObserver(function (records) {
    records.forEach(function (record) {
      record.addedNodes.forEach(function (node) {
        if (node.nodeType !== 1) return;
        if (node.tagName === "IFRAME") apply(node);
        node.querySelectorAll(selector).forEach(apply);
      });
    });
  }).observe(document.documentElement, {childList:true,subtree:true});
}());

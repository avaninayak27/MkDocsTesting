// Wait for Material theme to finish its own DOM setup, then move the version bar
// Using setTimeout ensures we run AFTER Material's JS has mounted
setTimeout(function () {
  var announce = document.querySelector("[data-md-component='announce']");
  var header   = document.querySelector(".md-header");
  if (announce && header && header.parentNode) {
    // Move the announce bar to immediately after the header element
    header.parentNode.insertBefore(announce, header.nextSibling);
    // Make sure it's visible (Material sometimes hides it)
    announce.style.display = "block";
    announce.removeAttribute("hidden");
  }
}, 100);

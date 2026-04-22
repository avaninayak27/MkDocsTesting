// Wait for Material theme to finish DOM setup
setTimeout(function () {
  var wrapper = document.getElementById("hidden-version-wrapper");
  var headerInner = document.querySelector(".md-header__inner");
  var headerSource = document.querySelector(".md-header__source"); // Repo link

  
  if (wrapper && headerInner) {
    var versionSelector = wrapper.querySelector(".custom-version-selector");
    
    // Attempt to insert right before the repo link, or append to end
    if (headerSource) {
      headerInner.insertBefore(versionSelector, headerSource);
    } else {
      headerInner.appendChild(versionSelector);
    }
  }
}, 100);

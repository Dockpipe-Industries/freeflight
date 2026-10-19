// SPDX-License-Identifier: Apache-2.0
qtLoad({
  qt: {
    entryFunction: window.freeflight_site_entry,
    containerElements: [document.getElementById("screen")],
    onLoaded() { document.getElementById("loading").remove(); },
  },
}).catch(() => {
  document.getElementById("loading").textContent =
    "FreeFlight could not open. Use the HTML view below or reload to retry.";
});

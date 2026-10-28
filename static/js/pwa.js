/* Registers the service worker and powers the "Install app" buttons.
   Any element with [data-pwa-install] stays hidden until the browser says the app is installable. */
(function () {
    if ("serviceWorker" in navigator) {
        window.addEventListener("load", function () {
            navigator.serviceWorker.register("/sw.js", { scope: "/" }).catch(function (err) {
                console.warn("Service worker registration failed:", err);
            });
        });
    }

    var deferredPrompt = null;
    var targets = function () { return document.querySelectorAll("[data-pwa-install]"); };
    var setVisible = function (show) {
        targets().forEach(function (el) { el.hidden = !show; });
    };

    window.addEventListener("beforeinstallprompt", function (e) {
        e.preventDefault();
        deferredPrompt = e;
        setVisible(true);
    });

    window.addEventListener("appinstalled", function () {
        deferredPrompt = null;
        setVisible(false);
    });

    document.addEventListener("click", function (e) {
        var btn = e.target.closest("[data-pwa-install]");
        if (!btn || !deferredPrompt) return;
        e.preventDefault();
        deferredPrompt.prompt();
        deferredPrompt.userChoice.finally(function () {
            deferredPrompt = null;
            setVisible(false);
        });
    });
})();

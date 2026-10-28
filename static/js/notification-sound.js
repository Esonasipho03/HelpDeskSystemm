/*
 * Plays a short chime when the user has new (unread) notifications.
 * Expects the page to define:
 *   window.NOTIF_SOUND_URL  - URL of the sound file
 *   window.NOTIF_UNREAD     - current unread notification count
 */
(function () {
    var STORAGE_KEY = "helpdesk_last_unread_count";
    var unread = parseInt(window.NOTIF_UNREAD, 10) || 0;
    var last = 0;

    try {
        last = parseInt(localStorage.getItem(STORAGE_KEY), 10) || 0;
        localStorage.setItem(STORAGE_KEY, String(unread));
    } catch (e) { /* storage unavailable - sound still plays when unread > 0 */ }

    if (unread <= last || !window.NOTIF_SOUND_URL) return;

    var audio = new Audio(window.NOTIF_SOUND_URL);
    audio.volume = 1.0;

    function playOnNextInteraction() {
        // Browsers block autoplay until the user interacts with the page.
        var once = function () {
            audio.play().catch(function () {});
            ["click", "keydown", "touchstart"].forEach(function (ev) {
                document.removeEventListener(ev, once);
            });
        };
        ["click", "keydown", "touchstart"].forEach(function (ev) {
            document.addEventListener(ev, once);
        });
    }

    var p = audio.play();
    if (p && typeof p.catch === "function") {
        p.catch(playOnNextInteraction);
    }
})();

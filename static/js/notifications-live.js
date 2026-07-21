/**
 * Live notifications: polls the server for anything newer than the last
 * notification already on the page, then:
 *   - plays a sound
 *   - pops a real desktop/browser notification (if permission was granted
 *     and the tab isn't currently focused)
 *   - updates the bell dot / badge / dropdown list in place
 *
 * Needs these data-* attributes on <body>:
 *   data-notif-poll-url   -> notifications_latest URL
 *   data-notif-sound-url  -> static sound file to play
 *   data-notif-icon-url   -> icon shown in the OS notification
 *   data-notif-last-id    -> id of the newest notification already rendered
 */
(function () {
    var body = document.body;
    if (!body || !body.dataset.notifPollUrl) return;

    var pollUrl = body.dataset.notifPollUrl;
    var soundUrl = body.dataset.notifSoundUrl;
    var iconUrl = body.dataset.notifIconUrl || "";
    var lastId = parseInt(body.dataset.notifLastId || "0", 10) || 0;

    var POLL_INTERVAL_MS = 15000;
    var chime = soundUrl ? new Audio(soundUrl) : null;

    // Ask for permission once, on first user interaction (browsers block
    // silent auto-prompts on page load in most cases anyway).
    function ensurePermission() {
        if ("Notification" in window && Notification.permission === "default") {
            Notification.requestPermission();
        }
    }
    document.addEventListener("click", ensurePermission, { once: true });
    ensurePermission();

    function playSound() {
        if (!chime) return;
        try {
            chime.currentTime = 0;
            chime.play().catch(function () {
                /* Browser blocked autoplay before any user interaction — fine,
                   the desktop notification (once permitted) still shows. */
            });
        } catch (err) {
            console.error("Notification sound failed:", err);
        }
    }

    function popDesktopNotification(note) {
        if (!("Notification" in window) || Notification.permission !== "granted") return;
        // Only bother with an OS popup if the user isn't already looking at the tab.
        if (document.hasFocus() && !document.hidden) return;

        var n = new Notification("NKMB Help Desk", {
            body: note.message,
            icon: iconUrl,
            tag: "helpdesk-notif-" + note.id,
        });

        n.onclick = function () {
            window.focus();
            if (note.url) window.location.href = note.url;
            n.close();
        };
    }

    function updateBell(unreadCount) {
        var btn = document.getElementById("notifButton");
        if (!btn) return;

        if (unreadCount > 0 && !btn.querySelector(".notification-dot")) {
            var dot = document.createElement("span");
            dot.className = "notification-dot";
            btn.appendChild(dot);
        }

        var badge = document.querySelector(".notif-unread-badge");
        var header = document.querySelector(".notif-popup-header");
        if (unreadCount > 0) {
            if (!badge && header) {
                badge = document.createElement("span");
                badge.className = "notif-unread-badge";
                header.appendChild(badge);
            }
            if (badge) badge.textContent = unreadCount;
        }
    }

    function prependToList(note) {
        var list = document.querySelector(".notif-list");
        if (!list) return;

        // Remove the "no notifications" empty state if present.
        var empty = list.querySelector(".empty-state");
        if (empty) empty.remove();

        var item = document.createElement("a");
        item.href = note.url || "#";
        item.className = "notif-item unread";

        var iconDiv = document.createElement("div");
        iconDiv.className = "notif-item-icon";

        var textWrap = document.createElement("div");
        var p = document.createElement("p");
        p.textContent = note.message;
        var small = document.createElement("small");
        small.textContent = "just now";
        textWrap.appendChild(p);
        textWrap.appendChild(small);

        item.appendChild(iconDiv);
        item.appendChild(textWrap);

        list.insertBefore(item, list.firstChild);
    }

    function poll() {
        fetch(pollUrl + "?after=" + lastId, { credentials: "same-origin" })
            .then(function (res) {
                if (!res.ok) throw new Error("bad response");
                return res.json();
            })
            .then(function (data) {
                var notes = data.notifications || [];
                if (notes.length === 0) return;

                notes.forEach(function (note) {
                    popDesktopNotification(note);
                    prependToList(note);
                    lastId = Math.max(lastId, note.id);
                });

                playSound();
                updateBell(data.unread_count);
            })
            .catch(function (err) {
                console.error("Notification poll failed:", err);
            });
    }

    setInterval(poll, POLL_INTERVAL_MS);
})();
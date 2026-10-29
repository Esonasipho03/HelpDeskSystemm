/* Light / dark theme toggle.
   The saved choice lives in localStorage ("nkmb-theme"). The attribute is first
   set by includes/theme_init.html before paint; this file wires up the button. */
(function () {
    var KEY = 'nkmb-theme';
    var root = document.documentElement;

    function current() {
        return root.getAttribute('data-theme') === 'dark' ? 'dark' : 'light';
    }

    function sync() {
        var btn = document.getElementById('themeToggle');
        if (!btn) return;
        var dark = current() === 'dark';
        btn.setAttribute('aria-pressed', dark ? 'true' : 'false');
        btn.setAttribute('aria-label', dark ? 'Switch to light mode' : 'Switch to dark mode');
        btn.title = dark ? 'Light mode' : 'Dark mode';
    }

    function set(theme) {
        root.setAttribute('data-theme', theme);
        root.setAttribute('data-bs-theme', theme);   // lets Bootstrap components follow
        sync();
    }

    var calm = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)');

    // Smooth switch. Browsers with the View Transitions API cross-fade the whole
    // page (gradients included). Others fall back to a short colour transition.
    function apply(theme, animate) {
        if (!animate || (calm && calm.matches)) { set(theme); return; }
        if (document.startViewTransition) {
            document.startViewTransition(function () { set(theme); });
            return;
        }
        root.classList.add('theme-fading');
        set(theme);
        setTimeout(function () { root.classList.remove('theme-fading'); }, 450);
    }

    document.addEventListener('DOMContentLoaded', function () {
        sync();
        var btn = document.getElementById('themeToggle');
        if (!btn) return;
        btn.addEventListener('click', function () {
            var next = current() === 'dark' ? 'light' : 'dark';
            try { localStorage.setItem(KEY, next); } catch (e) {}
            apply(next, true);
        });
    });

    // Keep other open tabs in step
    window.addEventListener('storage', function (e) {
        if (e.key === KEY) apply(e.newValue === 'dark' ? 'dark' : 'light', false);
    });
})();

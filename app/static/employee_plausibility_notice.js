(function () {
    fetch('/api/me/plausibility-summary', {cache: 'no-store', credentials: 'same-origin'})
        .then(function (response) { return response.ok ? response.json() : null; })
        .then(function (data) {
            if (!data || !data.authenticated || !Number(data.open)) return;
            if (window.location.pathname === '/me/plausibility') return;
            var container = document.querySelector('main.container');
            if (!container || document.getElementById('employeePlausibilityNotice')) return;
            var notice = document.createElement('div');
            notice.id = 'employeePlausibilityNotice';
            notice.className = Number(data.critical) > 0 ? 'error-box' : 'warning-box';
            notice.style.marginBottom = '1rem';
            notice.innerHTML = '<strong>Eigene Plausibilitätsfälle:</strong> ' +
                Number(data.open) + ' offene Auffälligkeit' + (Number(data.open) === 1 ? '' : 'en') +
                '. <a class="button small" style="margin-left:.6rem" href="' + (data.url || '/me/plausibility') + '">Jetzt prüfen</a>';
            container.insertBefore(notice, container.firstChild);
        })
        .catch(function () {});
})();

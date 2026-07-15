(function () {
    const adminMatch = window.location.pathname.match(/^\/admin\/employees\/(\d+)\/edit$/);
    if (adminMatch) {
        const employeeId = adminMatch[1];
        const mainSection = document.querySelector('main .card');
        if (mainSection) {
            const section = document.createElement('section');
            section.className = 'card settings-card';
            section.innerHTML = `
                <h2>Dashboard-Buchung</h2>
                <p class="help-text">Hier legst du für diesen Mitarbeiter fest, ob er nach der Anmeldung ohne erneute Passworteingabe Kommen, Gehen, Pausen und freigegebene Stempelgründe buchen darf.</p>
                <form action="/admin/employees/${employeeId}/self-booking" method="post" class="settings-form">
                    <div class="form-field checkbox-field">
                        <label><input id="employeeSelfBookingEnabled" type="checkbox" name="enabled" value="1"> Eigene Dashboard-Buchung ohne erneute Passworteingabe erlauben</label>
                    </div>
                    <div class="form-actions"><button type="submit">Freigabe speichern</button></div>
                </form>`;
            mainSection.insertAdjacentElement('afterend', section);

            fetch(`/api/admin/employees/${employeeId}/self-booking`, {cache: 'no-store', credentials: 'same-origin'})
                .then(response => response.ok ? response.json() : {enabled: false})
                .then(data => {
                    const checkbox = document.getElementById('employeeSelfBookingEnabled');
                    if (checkbox) checkbox.checked = data.enabled === true;
                })
                .catch(() => {});
        }
        return;
    }

    if (window.location.pathname !== '/' && window.location.pathname !== '/dashboard') return;

    function extendDashboardBooking() {
        const card = document.getElementById('selfBookingCard');
        if (!card || card.dataset.extendedBooking === '1') return;
        const form = card.querySelector('form[action="/dashboard/self-book"]');
        const grid = form ? form.querySelector('.button-grid') : null;
        if (!form || !grid) return;

        card.dataset.extendedBooking = '1';

        const pauseStart = document.createElement('button');
        pauseStart.type = 'submit';
        pauseStart.name = 'entry_type';
        pauseStart.value = 'pause_start';
        pauseStart.textContent = 'Pause Start';
        grid.appendChild(pauseStart);

        const pauseEnd = document.createElement('button');
        pauseEnd.type = 'submit';
        pauseEnd.name = 'entry_type';
        pauseEnd.value = 'pause_ende';
        pauseEnd.className = 'warn';
        pauseEnd.textContent = 'Pause Ende';
        grid.appendChild(pauseEnd);

        fetch('/api/stamp-reasons', {cache: 'no-store', credentials: 'same-origin'})
            .then(response => response.ok ? response.json() : {enabled: false, reasons: []})
            .then(data => {
                if (data.enabled !== true || !Array.isArray(data.reasons) || data.reasons.length === 0) return;

                const reasonForm = document.createElement('form');
                reasonForm.action = '/dashboard/self-book';
                reasonForm.method = 'post';
                reasonForm.style.marginTop = '1rem';

                const label = document.createElement('label');
                label.htmlFor = 'dashboardReasonSelect';
                label.textContent = 'Stempelgrund';

                const wrapper = document.createElement('div');
                wrapper.className = 'settings-grid';

                const select = document.createElement('select');
                select.name = 'reason_id';
                select.id = 'dashboardReasonSelect';
                select.required = true;

                const empty = document.createElement('option');
                empty.value = '';
                empty.textContent = 'Bitte auswählen';
                select.appendChild(empty);

                data.reasons.forEach(reason => {
                    const option = document.createElement('option');
                    option.value = String(reason.id);
                    option.textContent = reason.name;
                    select.appendChild(option);
                });

                const button = document.createElement('button');
                button.type = 'submit';
                button.textContent = 'Stempelgrund buchen';

                const help = document.createElement('p');
                help.className = 'help-text';
                help.textContent = 'Der ausgewählte Grund bestimmt, ob Kommen, Gehen, Pause oder nur ein Personenstatus gebucht wird.';

                wrapper.appendChild(select);
                wrapper.appendChild(button);
                reasonForm.appendChild(label);
                reasonForm.appendChild(wrapper);
                reasonForm.appendChild(help);
                card.appendChild(reasonForm);
            })
            .catch(() => {});
    }

    const observer = new MutationObserver(extendDashboardBooking);
    observer.observe(document.documentElement, {subtree: true, childList: true, attributes: true, attributeFilter: ['hidden']});
    extendDashboardBooking();
    window.setTimeout(extendDashboardBooking, 500);
})();

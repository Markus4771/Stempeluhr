(function () {
    const match = window.location.pathname.match(/^\/admin\/employees\/(\d+)\/edit$/);
    if (!match) return;
    const employeeId = match[1];
    const mainSection = document.querySelector('main .card');
    if (!mainSection) return;

    const section = document.createElement('section');
    section.className = 'card settings-card';
    section.innerHTML = `
        <h2>Dashboard-Buchung</h2>
        <p class="help-text">Hier legst du für diesen Mitarbeiter fest, ob er nach der Anmeldung ohne erneute Passworteingabe Kommen und Gehen buchen darf.</p>
        <form action="/admin/employees/${employeeId}/self-booking" method="post" class="settings-form">
            <div class="form-field checkbox-field">
                <label><input id="employeeSelfBookingEnabled" type="checkbox" name="enabled" value="1"> Kommen und Gehen im Dashboard ohne erneute Passworteingabe erlauben</label>
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
})();

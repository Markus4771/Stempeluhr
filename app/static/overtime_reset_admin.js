(function () {
  if (window.location.pathname !== '/admin') return;

  const style = document.createElement('style');
  style.textContent = `
    .overtime-modal-backdrop{position:fixed;inset:0;background:rgba(15,23,42,.55);display:none;align-items:center;justify-content:center;padding:1rem;z-index:9999}
    .overtime-modal-backdrop.is-open{display:flex}
    .overtime-modal{width:min(560px,100%);background:#fff;border-radius:16px;box-shadow:0 24px 70px rgba(15,23,42,.28);overflow:hidden}
    .overtime-modal-head{display:flex;justify-content:space-between;gap:1rem;align-items:flex-start;padding:1.25rem 1.4rem;border-bottom:1px solid #e2e8f0}
    .overtime-modal-head h2{margin:0;font-size:1.25rem}
    .overtime-modal-close{border:0;background:transparent;font-size:1.5rem;line-height:1;cursor:pointer;color:#64748b;padding:.1rem .35rem}
    .overtime-modal-body{padding:1.3rem 1.4rem}
    .overtime-modal-info{background:#eff6ff;border:1px solid #bfdbfe;border-radius:10px;padding:.9rem 1rem;margin-bottom:1rem}
    .overtime-modal-body label{display:block;font-weight:700;margin-bottom:.35rem}
    .overtime-modal-body textarea{width:100%;min-height:110px;resize:vertical;box-sizing:border-box}
    .overtime-modal-help{font-size:.86rem;color:#64748b;margin-top:.45rem}
    .overtime-modal-error{display:none;margin-top:.6rem;color:#b42318;font-weight:700}
    .overtime-modal-error.is-visible{display:block}
    .overtime-modal-actions{display:flex;justify-content:flex-end;gap:.7rem;padding:1rem 1.4rem;border-top:1px solid #e2e8f0;background:#f8fafc}
    .overtime-modal-actions button{min-width:120px}
    body.overtime-modal-open{overflow:hidden}
  `;
  document.head.appendChild(style);

  const backdrop = document.createElement('div');
  backdrop.className = 'overtime-modal-backdrop';
  backdrop.setAttribute('role', 'dialog');
  backdrop.setAttribute('aria-modal', 'true');
  backdrop.setAttribute('aria-labelledby', 'overtimeModalTitle');
  backdrop.innerHTML = `
    <div class="overtime-modal">
      <div class="overtime-modal-head">
        <div>
          <h2 id="overtimeModalTitle">Überstunden zurücksetzen</h2>
          <div id="overtimeEmployeeName" class="muted-small"></div>
        </div>
        <button type="button" class="overtime-modal-close" aria-label="Dialog schließen">×</button>
      </div>
      <div class="overtime-modal-body">
        <div class="overtime-modal-info">
          Der Mitarbeiter erhält eine Bestätigungs-E-Mail. Das Überstundenkonto wird erst nach seiner Zustimmung auf 0,00 Stunden gesetzt.
        </div>
        <label for="overtimeResetReason">Begründung *</label>
        <textarea id="overtimeResetReason" maxlength="1000" required placeholder="Zum Beispiel: Auszahlung, Jahresabschluss oder gemeinsamer Ausgleich."></textarea>
        <div class="overtime-modal-help">Die Begründung wird dem Mitarbeiter in der E-Mail angezeigt und im Audit-Protokoll gespeichert.</div>
        <div id="overtimeResetError" class="overtime-modal-error">Bitte eine Begründung eingeben.</div>
      </div>
      <div class="overtime-modal-actions">
        <button type="button" class="button secondary" id="overtimeResetCancel">Abbrechen</button>
        <button type="button" class="button" id="overtimeResetSend">Bestätigungs-E-Mail senden</button>
      </div>
    </div>
  `;
  document.body.appendChild(backdrop);

  const reasonField = backdrop.querySelector('#overtimeResetReason');
  const errorBox = backdrop.querySelector('#overtimeResetError');
  const employeeName = backdrop.querySelector('#overtimeEmployeeName');
  let activeForm = null;

  function closeModal() {
    backdrop.classList.remove('is-open');
    document.body.classList.remove('overtime-modal-open');
    activeForm = null;
    reasonField.value = '';
    errorBox.classList.remove('is-visible');
  }

  function openModal(form, name) {
    activeForm = form;
    employeeName.textContent = name || '';
    reasonField.value = '';
    errorBox.classList.remove('is-visible');
    backdrop.classList.add('is-open');
    document.body.classList.add('overtime-modal-open');
    window.setTimeout(function () { reasonField.focus(); }, 50);
  }

  backdrop.querySelector('.overtime-modal-close').addEventListener('click', closeModal);
  backdrop.querySelector('#overtimeResetCancel').addEventListener('click', closeModal);
  backdrop.addEventListener('click', function (event) {
    if (event.target === backdrop) closeModal();
  });
  document.addEventListener('keydown', function (event) {
    if (event.key === 'Escape' && backdrop.classList.contains('is-open')) closeModal();
  });

  backdrop.querySelector('#overtimeResetSend').addEventListener('click', function () {
    const reason = reasonField.value.trim();
    if (!reason) {
      errorBox.classList.add('is-visible');
      reasonField.focus();
      return;
    }
    if (!activeForm) return;

    let noteInput = activeForm.querySelector('input[name="note"]');
    if (!noteInput) {
      noteInput = document.createElement('input');
      noteInput.type = 'hidden';
      noteInput.name = 'note';
      activeForm.appendChild(noteInput);
    }
    noteInput.value = reason;

    const formToSubmit = activeForm;
    closeModal();
    formToSubmit.submit();
  });

  document.querySelectorAll('a[href^="/admin/employees/"][href$="/edit"]').forEach(function (editLink) {
    const match = editLink.getAttribute('href').match(/\/admin\/employees\/(\d+)\/edit$/);
    if (!match) return;
    const employeeId = match[1];
    const actionRow = editLink.closest('.admin-action-row');
    if (!actionRow || actionRow.querySelector('[data-overtime-reset]')) return;

    const row = editLink.closest('tr');
    const nameElement = row ? row.querySelector('.employee-name') : null;
    const displayName = nameElement ? nameElement.textContent.trim() : 'Mitarbeiter';

    const form = document.createElement('form');
    form.method = 'post';
    form.action = '/admin/employees/' + employeeId + '/overtime-reset/request';
    form.className = 'inline-toggle-form';
    form.dataset.overtimeReset = '1';
    form.addEventListener('submit', function (event) {
      event.preventDefault();
      openModal(form, displayName);
    });

    const button = document.createElement('button');
    button.type = 'submit';
    button.className = 'small-button';
    button.textContent = 'Überstunden zurücksetzen';
    button.title = 'Sendet eine Bestätigungs-E-Mail. Ohne Zustimmung des Mitarbeiters wird nichts geändert.';
    form.appendChild(button);
    actionRow.appendChild(form);
  });
})();

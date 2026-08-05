(function () {
  if (window.location.pathname !== '/admin') return;
  document.querySelectorAll('a[href^="/admin/employees/"][href$="/edit"]').forEach(function (editLink) {
    var match = editLink.getAttribute('href').match(/\/admin\/employees\/(\d+)\/edit$/);
    if (!match) return;
    var employeeId = match[1];
    var actionRow = editLink.closest('.admin-action-row');
    if (!actionRow || actionRow.querySelector('[data-overtime-reset]')) return;

    var form = document.createElement('form');
    form.method = 'post';
    form.action = '/admin/employees/' + employeeId + '/overtime-reset/request';
    form.className = 'inline-toggle-form';
    form.dataset.overtimeReset = '1';
    form.addEventListener('submit', function (event) {
      var reason = window.prompt('Begründung für den Überstunden-Reset. Der Mitarbeiter muss anschließend per E-Mail bestätigen:', 'Überstundenkonto wird nach gemeinsamer Abstimmung zurückgesetzt.');
      if (reason === null) {
        event.preventDefault();
        return;
      }
      var input = document.createElement('input');
      input.type = 'hidden';
      input.name = 'note';
      input.value = reason;
      form.appendChild(input);
      if (!window.confirm('Bestätigungs-E-Mail an den Mitarbeiter senden? Der Reset erfolgt erst nach seiner Zustimmung.')) {
        event.preventDefault();
      }
    });

    var button = document.createElement('button');
    button.type = 'submit';
    button.className = 'small-button';
    button.textContent = 'Überstunden zurücksetzen';
    button.title = 'Sendet eine Bestätigungs-E-Mail. Ohne Zustimmung des Mitarbeiters wird nichts geändert.';
    form.appendChild(button);
    actionRow.appendChild(form);
  });
})();

document.addEventListener('DOMContentLoaded', function () {
  if (!window.location.pathname.replace(/\/$/, '').endsWith('/reports')) return;

  const section = Array.from(document.querySelectorAll('section')).find((item) => {
    const heading = item.querySelector('h2');
    return heading && heading.textContent.trim().toLowerCase().includes('stempelzeiten');
  });
  if (!section) return;

  const employeeSelect = document.querySelector('select[name="employee_id"]');
  const fromInput = document.querySelector('input[name="date_from"]');
  const toInput = document.querySelector('input[name="date_to"]');
  const params = new URLSearchParams(window.location.search);
  const frameParams = new URLSearchParams({
    employee_id: params.get('employee_id') || (employeeSelect ? employeeSelect.value : '0'),
    date_from: params.get('date_from') || (fromInput ? fromInput.value : ''),
    date_to: params.get('date_to') || (toInput ? toInput.value : '')
  });

  section.innerHTML = '<h2>Stempelzeiten im gewählten Zeitraum</h2>' +
    '<p class="help-text">Kommen- und Gehen-Buchungen werden serverseitig nach Berechtigung, Mitarbeiter und Zeitraum gefiltert.</p>';

  const frame = document.createElement('iframe');
  frame.src = '/reports/stamps?' + frameParams.toString();
  frame.title = 'Kommen- und Gehen-Buchungen';
  frame.style.width = '100%';
  frame.style.minHeight = '420px';
  frame.style.border = '0';
  frame.addEventListener('error', function () {
    section.insertAdjacentHTML('beforeend', '<div class="error-box">Stempelzeiten konnten nicht geladen werden.</div>');
  });
  section.appendChild(frame);
});

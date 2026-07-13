document.addEventListener('DOMContentLoaded', function () {
  if (window.location.pathname !== '/reports') return;

  const headings = Array.from(document.querySelectorAll('h2'));
  const heading = headings.find((item) => item.textContent.trim() === 'Stempelzeiten im gewählten Zeitraum');
  if (!heading) return;

  const section = heading.closest('section');
  if (!section) return;

  const params = new URLSearchParams(window.location.search);
  const employeeSelect = document.querySelector('select[name="employee_id"]');
  const fromInput = document.querySelector('input[name="date_from"]');
  const toInput = document.querySelector('input[name="date_to"]');

  const employeeId = params.get('employee_id') || (employeeSelect ? employeeSelect.value : '0');
  const dateFrom = params.get('date_from') || (fromInput ? fromInput.value : '');
  const dateTo = params.get('date_to') || (toInput ? toInput.value : '');

  const frameParams = new URLSearchParams({
    employee_id: employeeId || '0',
    date_from: dateFrom || '',
    date_to: dateTo || ''
  });

  section.innerHTML = '';
  const newHeading = document.createElement('h2');
  newHeading.textContent = 'Stempelzeiten im gewählten Zeitraum';
  section.appendChild(newHeading);

  const help = document.createElement('p');
  help.className = 'help-text';
  help.textContent = 'Kommen- und Gehen-Buchungen werden serverseitig nach Berechtigung, Mitarbeiter und Zeitraum gefiltert.';
  section.appendChild(help);

  const frame = document.createElement('iframe');
  frame.src = '/reports/stamps?' + frameParams.toString();
  frame.title = 'Kommen- und Gehen-Buchungen';
  frame.style.width = '100%';
  frame.style.minHeight = '360px';
  frame.style.border = '0';
  frame.style.background = 'transparent';
  section.appendChild(frame);
});

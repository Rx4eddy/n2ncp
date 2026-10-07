/* Progressive enhancements only: all core workflows work without JavaScript. */
'use strict';
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('form[data-confirm]').forEach(form => {
    form.addEventListener('submit', event => {
      if (!window.confirm(form.dataset.confirm)) event.preventDefault();
    });
  });
  const data = document.getElementById('topic-data');
  const canvas = document.getElementById('topic-chart');
  if (data && canvas && window.Chart) {
    const counts = JSON.parse(data.textContent);
    new window.Chart(canvas, {
      type: 'bar', data: {labels: Object.keys(counts), datasets: [{data: Object.values(counts), backgroundColor: '#20796b', borderRadius: 5}]},
      options: {indexAxis: 'y', responsive: true, maintainAspectRatio: false, plugins: {legend: {display: false}}, scales: {x: {beginAtZero: true, ticks: {precision: 0}, grid: {color: '#edf0ed'}}, y: {grid: {display: false}}}}
    });
  }
});

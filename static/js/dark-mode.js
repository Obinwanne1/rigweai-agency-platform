(function() {
  if (localStorage.getItem('dark') === '1') {
    document.documentElement.classList.add('dark-init');
    document.addEventListener('DOMContentLoaded', () => {
      document.body.classList.add('dark');
      const btn = document.getElementById('dark-toggle');
      if (btn) btn.textContent = '☀️';
    });
  }
})();

function toggleDark() {
  const isDark = document.body.classList.toggle('dark');
  localStorage.setItem('dark', isDark ? '1' : '0');
  document.getElementById('dark-toggle').textContent = isDark ? '☀️' : '🌙';
}

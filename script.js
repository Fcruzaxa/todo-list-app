function toggleRepeatOptions() {
  const isChecked = document.getElementById('repeat-check').checked;
  document.getElementById('repeat-options').style.display = isChecked ? 'block' : 'none';
}

// On page load
window.onload = () => {
  const savedTheme = localStorage.getItem('theme') || 'dark';
  document.body.classList.add(savedTheme);
  toggleRepeatOptions();
};

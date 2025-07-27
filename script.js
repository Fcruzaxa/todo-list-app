function toggleTheme() {
  const body = document.body;
  if (body.classList.contains("theme-light")) {
    body.classList.remove("theme-light");
    body.classList.add("theme-dark");
    localStorage.setItem("theme", "dark");
  } else {
    body.classList.remove("theme-dark");
    body.classList.add("theme-light");
    localStorage.setItem("theme", "light");
  }
}

// Load saved theme
window.onload = () => {
  const theme = localStorage.getItem("theme");
  if (theme === "dark") {
    document.body.classList.remove("theme-light");
    document.body.classList.add("theme-dark");
  }
};

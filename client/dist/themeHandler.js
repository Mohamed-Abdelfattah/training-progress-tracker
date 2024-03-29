// to cover EPFL's requirements of the project here I'm using javascript manipulate the local storage and to use addEventListener, knowing that the way to achieve the same result in react is by adding onEventTrigger(like onChange) to the jsx element

const lightThemeInput = document.getElementById("light-theme-input");
const darkThemeInput = document.getElementById("dark-theme-input");
const nordThemeInput = document.getElementById("nord-theme-input");

// get the theme from local storage (could be null)
let savedTheme = localStorage.getItem("theme");

// set the current theme to the saved one by checking the corresponding input value (will default be light)
if (savedTheme === "dark") {
  darkThemeInput.checked = true;
} else if (savedTheme === "nord") {
  nordThemeInput.checked = true;
} else {
  lightThemeInput.checked = true;
}

// update the local storage when user selects a theme
lightThemeInput.addEventListener("input", (e) => {
  savedTheme = e.target.value;
  localStorage.setItem("theme", savedTheme);
});

darkThemeInput.addEventListener("input", (e) => {
  savedTheme = e.target.value;
  localStorage.setItem("theme", savedTheme);
});

nordThemeInput.addEventListener("input", (e) => {
  savedTheme = e.target.value;
  localStorage.setItem("theme", savedTheme);
});

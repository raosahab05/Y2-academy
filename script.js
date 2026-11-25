const menuToggle = document.querySelector(".menu-toggle");
const mainNav = document.querySelector(".main-nav");

// Mobile navigation
if (menuToggle && mainNav) {
  menuToggle.addEventListener("click", () => {
    const isOpen = mainNav.classList.toggle("open");

    menuToggle.setAttribute("aria-expanded", String(isOpen));
    menuToggle.setAttribute(
      "aria-label",
      isOpen ? "Close navigation" : "Open navigation"
    );
  });

  mainNav.querySelectorAll("a").forEach((link) => {
    link.addEventListener("click", () => {
      mainNav.classList.remove("open");
      menuToggle.setAttribute("aria-expanded", "false");
      menuToggle.setAttribute("aria-label", "Open navigation");
    });
  });
}


// Automatic active navigation link
const currentPage = decodeURIComponent(
  window.location.pathname.split("/").pop() || "index.html"
).toLowerCase();

document.querySelectorAll(".main-nav .nav-link").forEach((link) => {
  const linkPage = decodeURIComponent(
    new URL(link.href, window.location.href).pathname.split("/").pop()
  ).toLowerCase();

  const isActive = linkPage === currentPage;

  link.classList.toggle("active", isActive);

  if (isActive) {
    link.setAttribute("aria-current", "page");
  } else {
    link.removeAttribute("aria-current");
  }
});


// Contact form - Formspree integration
const contactForm = document.querySelector("#contactForm");
const formMessage = document.querySelector("#formMessage");

if (contactForm && formMessage) {
  contactForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    if (!contactForm.checkValidity()) {
      contactForm.reportValidity();
      return;
    }

    const submitButton = contactForm.querySelector(
      'button[type="submit"]'
    );

    const originalButtonText = submitButton
      ? submitButton.innerHTML
      : "";

    formMessage.textContent = "";

    if (submitButton) {
      submitButton.disabled = true;
      submitButton.textContent = "Sending...";
    }

    try {
      const response = await fetch(contactForm.action, {
        method: "POST",
        body: new FormData(contactForm),
        headers: {
          Accept: "application/json"
        }
      });

      if (response.ok) {
        formMessage.textContent =
          "Thank you! Your enquiry has been sent successfully.";

        contactForm.reset();
      } else {
        let errorMessage =
          "We couldn't send your enquiry. Please try again.";

        try {
          const result = await response.json();

          if (result.errors && result.errors.length > 0) {
            errorMessage = result.errors
              .map((error) => error.message)
              .join(" ");
          }
        } catch {
          // Use the default error message if no JSON response is available.
        }

        formMessage.textContent = errorMessage;
      }
    } catch (error) {
      formMessage.textContent =
        "Network error. Please check your internet connection and try again.";
    } finally {
      if (submitButton) {
        submitButton.disabled = false;
        submitButton.innerHTML = originalButtonText;
      }
    }
  });
}

// Automatic copyright year
const year = document.querySelector("#year");

if (year) {
  year.textContent = new Date().getFullYear();
}


/* ===== Y2 ACADEMY THEME SWITCHER ===== */

const themeToggle = document.querySelector("#themeToggle");

const themeModes = ["system", "light", "dark"];

const savedTheme = localStorage.getItem("y2-theme") || "system";

let currentTheme = themeModes.includes(savedTheme)
  ? savedTheme
  : "system";

function applyTheme(theme) {
  currentTheme = theme;

  const root = document.documentElement;

  if (theme === "system") {
    const prefersDark = window.matchMedia(
      "(prefers-color-scheme: dark)"
    ).matches;

    root.setAttribute(
      "data-theme",
      prefersDark ? "dark" : "light"
    );
  } else {
    root.setAttribute("data-theme", theme);
  }

  localStorage.setItem("y2-theme", theme);

  updateThemeIcon();
}

function updateThemeIcon() {
  if (!themeToggle) return;

  const icons = {
    system: `<svg viewBox="0 0 24 24" fill="none">
      <rect x="3" y="4" width="18" height="13" rx="2"
        stroke="currentColor" stroke-width="1.7"/>
      <path d="M8 21h8M12 17v4"
        stroke="currentColor" stroke-width="1.7"
        stroke-linecap="round"/>
    </svg>`,

    light: `<svg viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="12" r="4"
        stroke="currentColor" stroke-width="1.7"/>
      <path d="M12 2v2M12 20v2M4.93 4.93l1.42 1.42
        M17.65 17.65l1.42 1.42M2 12h2M20 12h2
        M4.93 19.07l1.42-1.42M17.65 6.35l1.42-1.42"
        stroke="currentColor" stroke-width="1.7"
        stroke-linecap="round"/>
    </svg>`,

    dark: `<svg viewBox="0 0 24 24" fill="none">
      <path d="M20.5 15.5A8.5 8.5 0 0 1 8.5 3.5
        8.7 8.7 0 1 0 20.5 15.5Z"
        stroke="currentColor" stroke-width="1.7"
        stroke-linecap="round" stroke-linejoin="round"/>
    </svg>`
  };

  themeToggle.innerHTML = icons[currentTheme];

  themeToggle.setAttribute(
    "aria-label",
    `Current theme: ${currentTheme}. Click to change theme.`
  );

  themeToggle.setAttribute("title", `Theme: ${currentTheme}`);
}

// Initial theme
applyTheme(currentTheme);

// Cycle theme on every click
if (themeToggle) {
  themeToggle.addEventListener("click", () => {
    const currentIndex = themeModes.indexOf(currentTheme);
    const nextIndex = (currentIndex + 1) % themeModes.length;

    applyTheme(themeModes[nextIndex]);
  });
}

// Follow system changes only when System Default is selected
window.matchMedia("(prefers-color-scheme: dark)")
  .addEventListener("change", () => {
    if (currentTheme === "system") {
      applyTheme("system");
    }
  });

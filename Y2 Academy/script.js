<<<<<<< HEAD
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
=======

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

// Demo contact form
const contactForm = document.querySelector("#contactForm");
const formMessage = document.querySelector("#formMessage");

if (contactForm && formMessage) {
  contactForm.addEventListener("submit", (event) => {
    event.preventDefault();

    if (!contactForm.checkValidity()) {
      contactForm.reportValidity();
      return;
    }

    const nameInput = document.querySelector("#fullName");
    const name = nameInput ? nameInput.value.trim() : "Student";

    formMessage.textContent =
      `Thanks, ${name}! The demo form is working. Connect a backend to receive real enquiries.`;

    contactForm.reset();
  });
}

// Automatic copyright year
const year = document.querySelector("#year");

if (year) {
  year.textContent = new Date().getFullYear();
}
>>>>>>> origin/main

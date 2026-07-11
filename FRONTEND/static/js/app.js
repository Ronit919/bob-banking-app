/**
 * app.js
 * ------
 * Minimal client-side helpers for the Banking Web Application.
 *
 * Contains only UI convenience logic — no business rules.
 * All validation and computation are authoritative on the backend.
 */

/* -------------------------------------------------------------------------
   Password visibility toggle on the login page.
   Finds the toggle button by id and swaps the input type + eye icon.
   ------------------------------------------------------------------------- */
(function () {
  "use strict";

  const toggleBtn = document.getElementById("togglePassword");
  const passwordInput = document.getElementById("password");
  const eyeIcon = document.getElementById("eyeIcon");

  if (toggleBtn && passwordInput && eyeIcon) {
    toggleBtn.addEventListener("click", function () {
      const isPassword = passwordInput.type === "password";
      passwordInput.type = isPassword ? "text" : "password";
      eyeIcon.className = isPassword ? "bi bi-eye-slash" : "bi bi-eye";
    });
  }
})();

/* -------------------------------------------------------------------------
   Prevent double-submission of transaction forms.
   Disables the submit button after the first click so the user cannot
   accidentally submit a deposit or withdrawal twice by clicking rapidly.
   Re-enabled if the user navigates back (browser back-button).
   ------------------------------------------------------------------------- */
(function () {
  "use strict";

  var forms = document.querySelectorAll("#depositForm, #withdrawForm");
  forms.forEach(function (form) {
    form.addEventListener("submit", function (event) {
      var submitBtn = form.querySelector("button[type='submit']");
      if (submitBtn) {
        // Small delay so the form data is captured before the button is
        // disabled (some browsers skip the submit if the button is disabled
        // before the event completes).
        setTimeout(function () {
          submitBtn.disabled = true;
          submitBtn.innerHTML =
            '<span class="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span>Processing…';
        }, 0);
      }
    });
  });
})();

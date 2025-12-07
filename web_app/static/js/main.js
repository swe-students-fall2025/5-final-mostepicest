console.log("PolyPaper frontend loaded");

document.addEventListener("DOMContentLoaded", () => {
  const mockTradeBtn = document.querySelector(".trade-ticket .btn-primary");
  if (mockTradeBtn) {
    mockTradeBtn.addEventListener("click", () => {
      alert("Trading will be enabled once the backend/API is connected.");
    });
  }

  const profileMenu = document.querySelector(".profile-menu");
  const profileTrigger = document.querySelector(".profile-trigger");
  if (profileMenu && profileTrigger) {
    profileTrigger.addEventListener("click", (e) => {
      e.stopPropagation();
      profileMenu.classList.toggle("open");
    });
    document.addEventListener("click", () => {
      profileMenu.classList.remove("open");
    });
  }

  // Settings form: basic validation and "changed" detection to enable the Save button
  const settingsForm = document.getElementById("settings-form");
  if (settingsForm) {
    const usernameInput = settingsForm.querySelector('input[name="username"]');
    const bioInput = settingsForm.querySelector('textarea[name="bio"]');
    const saveBtn = settingsForm.querySelector(".btn-save");
    const toast = document.getElementById("settings-toast");
    const usernameNote = settingsForm.querySelector(
      '.validation-note[data-for="username"]'
    );

    const initialState = {
      username: usernameInput ? usernameInput.value : "",
      bio: bioInput ? bioInput.value : "",
    };

    // Here we validate the username so it must be within 3-24 characters
    const validateUsername = () => {
      if (!usernameInput) return true;
      const val = usernameInput.value.trim();
      let valid = true;
      if (val.length < 3) {
        usernameNote.textContent = "Username must be at least 3 characters.";
        valid = false;
      } else if (val.length > 24) {
        usernameNote.textContent = "Username cannot exceed 24 characters.";
        valid = false;
      } else {
        usernameNote.textContent = "";
      }
      usernameNote.classList.toggle("error", !valid);
      return valid;
    };

    const markChanged = () => {
      const changed =
        (usernameInput && usernameInput.value !== initialState.username) ||
        (bioInput && bioInput.value !== initialState.bio);
      if (saveBtn) {
        saveBtn.disabled = !changed || !validateUsername();
        saveBtn.classList.toggle("disabled", saveBtn.disabled);
      }
    };

    if (usernameInput) {
      usernameInput.addEventListener("input", () => {
        validateUsername();
        markChanged();
      });
    }
    if (bioInput) {
      bioInput.addEventListener("input", markChanged);
    }

    // We will change this later
    settingsForm.addEventListener("submit", (e) => {
      e.preventDefault(); // Prevent real submit until backend is wired.
      if (!validateUsername()) return;
      // Show toast feedback; in future this will reflect real API response.
      if (toast) {
        toast.classList.add("show");
        setTimeout(() => toast.classList.remove("show"), 2500);
      }
      // Reset change tracking.
      initialState.username = usernameInput ? usernameInput.value : "";
      initialState.bio = bioInput ? bioInput.value : "";
      markChanged();
    });

    // Initialize state on load
    markChanged();
  }
});

document.addEventListener("DOMContentLoaded", () => {
  // Elements
  const landingSection = document.getElementById("landingSection");
  const mainDashboard = document.getElementById("mainDashboard");
  const loginSection = document.getElementById("loginSection");
  const registerSection = document.getElementById("registerSection");

  const heroCreateAccountBtn = document.getElementById("heroCreateAccountBtn");
  const heroCreateAccountHeaderBtn = document.getElementById("heroCreateAccountHeaderBtn");
  const heroLoginBtn = document.getElementById("heroLoginBtn");
  const heroLoginHeaderBtn = document.getElementById("heroLoginHeaderBtn");
  const pricingFreeBtn = document.getElementById("pricingFreeBtn");
  const pricingProBtn = document.getElementById("pricingProBtn");

  const backToLandingFromLoginBtn = document.getElementById("backToLandingFromLoginBtn");
  const backToLandingFromRegisterBtn = document.getElementById("backToLandingFromRegisterBtn");
  const switchToRegisterBtn = document.getElementById("switchToRegisterBtn");
  const switchToLoginBtn = document.getElementById("switchToLoginBtn");

  const loginForm = document.getElementById("loginForm");
  const registerForm = document.getElementById("registerForm");
  const loginError = document.getElementById("loginError");
  const registerError = document.getElementById("registerError");
  const registerSuccess = document.getElementById("registerSuccess");
  const logoutBtn = document.getElementById("logoutBtn");
  const loggedInUserDisplay = document.getElementById("loggedInUserDisplay");

  // Session Persistence Check on Page Load
  const activeUser = localStorage.getItem("dah_active_user");
  if (activeUser) {
    showDashboard(activeUser);
  }

  // Navigation UI Toggles
  function showSection(section) {
    landingSection.classList.add("hidden");
    loginSection.classList.add("hidden");
    registerSection.classList.add("hidden");
    mainDashboard.classList.add("hidden");
    mainDashboard.style.display = "none";

    if (section === "landing") landingSection.classList.remove("hidden");
    if (section === "login") loginSection.classList.remove("hidden");
    if (section === "register") registerSection.classList.remove("hidden");
    if (section === "dashboard") {
      mainDashboard.classList.remove("hidden");
      mainDashboard.style.display = "flex";
    }
  }

  function showDashboard(username) {
    loggedInUserDisplay.textContent = username;
    showSection("dashboard");
  }

  // Event Listeners for Navigation
  [heroCreateAccountBtn, heroCreateAccountHeaderBtn, pricingFreeBtn, pricingProBtn].forEach(btn => {
    if (btn) btn.addEventListener("click", () => showSection("register"));
  });

  [heroLoginBtn, heroLoginHeaderBtn].forEach(btn => {
    if (btn) btn.addEventListener("click", () => showSection("login"));
  });

  if (backToLandingFromLoginBtn) backToLandingFromLoginBtn.addEventListener("click", () => showSection("landing"));
  if (backToLandingFromRegisterBtn) backToLandingFromRegisterBtn.addEventListener("click", () => showSection("landing"));
  if (switchToRegisterBtn) switchToRegisterBtn.addEventListener("click", () => showSection("register"));
  if (switchToLoginBtn) switchToLoginBtn.addEventListener("click", () => showSection("login"));

  // Registration Flow Handler
  if (registerForm) {
    registerForm.addEventListener("submit", (e) => {
      e.preventDefault();
      const email = document.getElementById("registerEmail").value.trim();
      const username = document.getElementById("registerUsername").value.trim();
      const password = document.getElementById("registerPassword").value;
      const confirmPassword = document.getElementById("registerConfirmPassword").value;

      registerError.classList.add("hidden");
      registerSuccess.classList.add("hidden");

      if (password !== confirmPassword) {
        registerError.textContent = "Passwords do not match.";
        registerError.classList.remove("hidden");
        return;
      }

      // Retrieve existing users database from localStorage or initialize
      let users = JSON.parse(localStorage.getItem("dah_users") || "[]");
      
      const userExists = users.some(u => u.email === email || u.username === username);
      if (userExists) {
        registerError.textContent = "User with this email or username already exists.";
        registerError.classList.remove("hidden");
        return;
      }

      // Store new user credentials
      users.push({ email, username, password });
      localStorage.setItem("dah_users", JSON.stringify(users));
      
      // Set active session state
      localStorage.setItem("dah_active_user", username);

      registerSuccess.textContent = "Account created successfully! Entering workspace...";
      registerSuccess.classList.remove("hidden");

      setTimeout(() => {
        showDashboard(username);
      }, 1000);
    });
  }

  // Authentication State Management (Login Handler)
  if (loginForm) {
    loginForm.addEventListener("submit", (e) => {
      e.preventDefault();
      const identifier = document.getElementById("loginIdentifier").value.trim();
      const password = document.getElementById("loginPassword").value;

      loginError.classList.add("hidden");

      const users = JSON.parse(localStorage.getItem("dah_users") || "[]");
      
      // Validate credentials against saved records
      const validUser = users.find(u => (u.email === identifier || u.username === identifier) && u.password === password);

      if (validUser) {
        localStorage.setItem("dah_active_user", validUser.username);
        showDashboard(validUser.username);
      } else {
        loginError.textContent = "Invalid credentials or account does not exist.";
        loginError.classList.remove("hidden");
      }
    });
  }

  // Logout Handler
  if (logoutBtn) {
    logoutBtn.addEventListener("click", () => {
      localStorage.removeItem("dah_active_user");
      showSection("landing");
    });
  }
});

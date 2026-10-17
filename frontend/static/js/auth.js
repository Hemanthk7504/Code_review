/**
 * CodeSentinel Authentication UI Controller
 */
const AuthController = {
  switchTab(tab) {
    const tabLogin = document.getElementById('tab-login');
    const tabReg = document.getElementById('tab-register');
    const formLogin = document.getElementById('form-login');
    const formReg = document.getElementById('form-register');
    const heading = document.getElementById('auth-heading');
    const subheading = document.getElementById('auth-subheading');

    if (tab === 'register') {
      tabLogin.classList.remove('active');
      tabReg.classList.add('active');
      formLogin.style.display = 'none';
      formReg.style.display = 'block';
      if (heading) heading.textContent = 'Create an Account';
      if (subheading) subheading.textContent = 'Provision access for your engineering workspace.';
    } else {
      tabReg.classList.remove('active');
      tabLogin.classList.add('active');
      formReg.style.display = 'none';
      formLogin.style.display = 'block';
      if (heading) heading.textContent = 'Welcome to CodeSentinel';
      if (subheading) subheading.textContent = 'Enter your enterprise credentials to access the security console.';
    }
  },

  togglePassword(inputId, btn) {
    const input = document.getElementById(inputId);
    if (!input) return;
    if (input.type === 'password') {
      input.type = 'text';
      btn.innerHTML = `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path><line x1="1" y1="1" x2="23" y2="23"></line></svg>`;
    } else {
      input.type = 'password';
      btn.innerHTML = `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle></svg>`;
    }
  },

  async handleLogin(e) {
    if (e) e.preventDefault();
    const username = document.getElementById('login-username').value.trim();
    const password = document.getElementById('login-password').value;
    const btn = document.getElementById('btn-login-submit');

    if (!username || !password) {
      App.showToast('Please enter both username and password.', 'warning');
      return;
    }

    if (btn) btn.disabled = true;

    try {
      const data = await API.login(username, password);
      App.showToast(`Welcome back, ${data.user.full_name || data.user.username}!`, 'success');
      setTimeout(() => {
        window.location.href = '/dashboard';
      }, 500);
    } catch (err) {
      App.showToast(err.message || 'Authentication failed. Please check credentials.', 'error');
    } finally {
      if (btn) btn.disabled = false;
    }
  },

  async handleRegister(e) {
    if (e) e.preventDefault();
    const username = document.getElementById('reg-username').value.trim();
    const full_name = document.getElementById('reg-fullname').value.trim();
    const email = document.getElementById('reg-email').value.trim();
    const password = document.getElementById('reg-password').value;
    const role = document.getElementById('reg-role').value;
    const btn = document.getElementById('btn-reg-submit');

    if (password.length < 6) {
      App.showToast('Password must be at least 6 characters long.', 'warning');
      return;
    }

    if (btn) btn.disabled = true;

    try {
      const data = await API.register({ username, full_name, email, password, role });
      App.showToast('Account created successfully!', 'success');
      setTimeout(() => {
        window.location.href = '/dashboard';
      }, 500);
    } catch (err) {
      App.showToast(err.message || 'Registration failed.', 'error');
    } finally {
      if (btn) btn.disabled = false;
    }
  },

  quickLogin(username, password) {
    this.switchTab('login');
    document.getElementById('login-username').value = username;
    document.getElementById('login-password').value = password;
    this.handleLogin();
  },

  checkExistingSession() {
    const user = API.getUser();
    const token = API.getToken();
    const banner = document.getElementById('already-logged-in-banner');
    const nameSpan = document.getElementById('logged-in-username');

    if (token && user && banner && nameSpan) {
      nameSpan.textContent = `${user.full_name || user.username} (${user.role})`;
      banner.style.display = 'block';
    }
  }
};

window.addEventListener('DOMContentLoaded', () => {
  AuthController.checkExistingSession();
});

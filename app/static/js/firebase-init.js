// static/js/firebase-init.js
document.addEventListener('DOMContentLoaded', function() {
    try {
        console.log("DOMContentLoaded: Initializing Firebase script...");

        // --- START: Firebase Configuration ---
        // Get Firebase configuration from global window object (set in base template)
    const firebaseConfig = window.firebaseConfig;
        
        // Debug: Log Firebase config details
        console.log("Firebase config debug:", {
            hasWindowConfig: !!window.firebaseConfig,
            apiKey: firebaseConfig.apiKey ? `${firebaseConfig.apiKey.substring(0, 10)}...` : 'MISSING',
            projectId: firebaseConfig.projectId || 'MISSING',
            configSource: window.firebaseConfig ? 'environment' : 'fallback'
        });
        
        // Check if Firebase config is properly set (not empty)
    const hasValidConfig = firebaseConfig && firebaseConfig.apiKey && firebaseConfig.projectId && 
                  firebaseConfig.apiKey !== '' && firebaseConfig.projectId !== '';
        
        // Log configuration source for debugging
        if (window.firebaseConfig && hasValidConfig) {
            console.log("✅ Using Firebase config from environment variables");
        } else if (hasValidConfig) {
            console.warn("⚠️ Using client config from template but verify environment variables are set on server.");
        } else {
            console.error("❌ Firebase configuration is incomplete - authentication will be disabled");
            displayAuthMessage("Firebase configuration incomplete. Authentication features disabled.", "warning", true);
            return; // Exit early if config is incomplete
        }
        // --- END: Firebase Configuration ---

        let app;
        let auth; // Declare here to be accessible throughout the try block

    if (typeof firebase !== 'undefined' && typeof firebase.initializeApp === 'function' && hasValidConfig) {
            app = firebase.initializeApp(firebaseConfig);
            
            if (typeof firebase.auth === 'function') {
                auth = firebase.auth(); // Initialize auth
                console.log("Firebase App and Auth initialized successfully.");
                
                // Hide any existing warning messages since Firebase loaded successfully
                hideGlobalWarningMessage();
                
            } else {
                console.error("Firebase Auth SDK not loaded or firebase.auth is not a function.");
                displayAuthMessage("Firebase Auth services unavailable - using fallback authentication.", "warning", true);
                return; // Stop if auth isn't available
            }
        } else {
            console.error("Firebase SDK not loaded correctly. Check your internet connection and try refreshing.");
            displayAuthMessage("Firebase services unavailable - authentication features disabled.", "warning", true);
            return; 
        }

        if (auth) {
            // Global listener to refresh token and handle sign-out
            auth.onIdTokenChanged(async (user) => {
                if (user) {
                    try {
                        // Force refresh the token to avoid expiry issues
                        await user.getIdToken(true);
                    } catch (err) {
                        console.error('Error refreshing ID token:', err);
                    }
                } else {
                    // User is signed out, optionally clear session or redirect
                    console.log('User is signed out (onIdTokenChanged).');
                    // Optionally, redirect to login or clear UI
                }
            });
        }

        // --- Helper to display messages on auth pages ---
        function displayAuthMessage(message, type = 'error', isGlobal = false) {
            const errorDiv = document.getElementById('auth-error-message');
            const successDiv = document.getElementById('auth-success-message');
            
            if (isGlobal && (!errorDiv || !successDiv)) {
                // If it's a global critical message and specific divs aren't there, show a prominent alert-like div
                const bodyElement = document.body;
                if (bodyElement) {
                    let globalMsgDiv = document.getElementById('firebase-critical-error-global');
                    if (!globalMsgDiv) {
                        globalMsgDiv = document.createElement('div');
                        globalMsgDiv.id = 'firebase-critical-error-global';
                        globalMsgDiv.style.color = 'white';
                        globalMsgDiv.style.backgroundColor = (type === 'error' ? 'red' : 'green');
                        globalMsgDiv.style.border = '1px solid darkred';
                        globalMsgDiv.style.padding = '15px';
                        globalMsgDiv.style.textAlign = 'center';
                        globalMsgDiv.style.position = 'fixed';
                        globalMsgDiv.style.top = '0';
                        globalMsgDiv.style.left = '0';
                        globalMsgDiv.style.width = '100%';
                        globalMsgDiv.style.zIndex = '9999';
                        bodyElement.prepend(globalMsgDiv);
                    }
                    globalMsgDiv.textContent = message;
                    globalMsgDiv.style.display = 'block';
                    if (type !== 'error') {
                        setTimeout(() => { globalMsgDiv.style.display = 'none'; }, 5000); // Hide success after 5s
                    }
                }
                return;
            }

            if (type === 'error') {
                if (errorDiv) { errorDiv.textContent = message; errorDiv.style.display = 'block'; }
                if (successDiv) successDiv.style.display = 'none';
            } else {
                if (successDiv) { successDiv.textContent = message; successDiv.style.display = 'block'; }
                if (errorDiv) errorDiv.style.display = 'none';
            }
        }

        // Function to hide global warning messages when Firebase loads successfully
        function hideGlobalWarningMessage() {
            const globalMsgDiv = document.getElementById('firebase-critical-error-global');
            if (globalMsgDiv) {
                globalMsgDiv.style.display = 'none';
                console.log("Hidden Firebase warning message - services are now available.");
            }
        }

        function clearAuthMessages() {
            const errorDiv = document.getElementById('auth-error-message');
            const successDiv = document.getElementById('auth-success-message');
            if (errorDiv) errorDiv.style.display = 'none';
            if (successDiv) successDiv.style.display = 'none';
        }

        // --- Spinner Control ---
        function showSpinner(spinnerId) {
            const spinner = document.getElementById(spinnerId);
            if (spinner) {
                spinner.style.display = 'inline-block';
                const button = spinner.closest('button'); // Assumes spinner is inside button
                if (button) button.disabled = true;
            }
        }

        function hideSpinner(spinnerId) {
            const spinner = document.getElementById(spinnerId);
            if (spinner) {
                spinner.style.display = 'none';
                const button = spinner.closest('button');
                if (button) button.disabled = false;
            }
        }
        
        // --- Password Visibility Toggle ---
        function togglePasswordVisibility(fieldId, buttonElement) {
            const passwordField = document.getElementById(fieldId);
            if (!passwordField) {
                console.error("Password field with ID '" + fieldId + "' not found for toggle.");
                return;
            }
            const icon = buttonElement.querySelector('i');
            if (passwordField.type === "password") {
                passwordField.type = "text";
                icon.classList.remove('fa-eye');
                icon.classList.add('fa-eye-slash');
            } else {
                passwordField.type = "password";
                icon.classList.remove('fa-eye-slash');
                icon.classList.add('fa-eye');
            }
        }

        // --- Backend Token Verification ---
        async function verifyTokenWithBackend(idToken) {
            // A global spinner might be good here if redirection is slow
            try {
                const response = await fetch('/verify-token', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ idToken: idToken }),
                });
                const data = await response.json();
                if (response.ok) {
                    // Don't display message here, redirect is immediate
                    const nextUrl = data.next_url || new URLSearchParams(window.location.search).get('next') || '/stock-analysis/dashboard';
                    window.location.href = nextUrl;
                } else {
                    const errorMessage = data.email_not_verified 
                        ? "Email not verified. Please check your inbox for a verification link."
                        : data.error || "Token verification failed after successful authentication.";
                    displayAuthMessage(errorMessage);
                    if (auth) await auth.signOut(); 
                }
            } catch (error) {
                console.error("Error verifying token with backend:", error);
                displayAuthMessage("An error occurred communicating with the server. Please try again.");
                if (auth) await auth.signOut();
            }
        }

        // --- Email/Password Registration ---
        async function handleRegister(event) {
            if (event) event.preventDefault();
            clearAuthMessages();
            if (!auth) { displayAuthMessage("Authentication service is not ready. Please refresh."); return; }

            const spinnerId = 'registerSpinner';
            showSpinner(spinnerId);
        
            const usernameInput = document.getElementById('registerUsername');
            const emailInput = document.getElementById('registerEmail');
            const passwordInput = document.getElementById('registerPassword');
            const passwordConfirmInput = document.getElementById('registerPasswordConfirm');

            if (!usernameInput || !emailInput || !passwordInput || !passwordConfirmInput) {
                console.error("One or more registration form fields are missing from the DOM.");
                displayAuthMessage("Registration form error. Please refresh the page.");
                hideSpinner(spinnerId);
                return;
            }

            const username = usernameInput.value.trim();
            const email = emailInput.value.trim();
            const password = passwordInput.value;
            const passwordConfirm = passwordConfirmInput.value;
        
            if (!username) { displayAuthMessage("Username is required."); hideSpinner(spinnerId); return; }
            if (!email) { displayAuthMessage("Email is required."); hideSpinner(spinnerId); return; }
            if (password.length < 6) { displayAuthMessage("Password should be at least 6 characters long."); hideSpinner(spinnerId); return; }
            if (password !== passwordConfirm) { displayAuthMessage("Passwords do not match."); hideSpinner(spinnerId); return; }
        
            try {
                const userCredential = await auth.createUserWithEmailAndPassword(email, password);
                const user = userCredential.user;
        
                await user.updateProfile({ displayName: username });
                await user.sendEmailVerification();
                
                displayAuthMessage("Registration successful! Please check your email (" + email + ") to verify your account, then login.", "success");
                await auth.signOut(); // Sign out until email is verified

                usernameInput.value = '';
                emailInput.value = '';
                passwordInput.value = '';
                passwordConfirmInput.value = '';

            } catch (error) {
                console.error("Registration error:", error);
                displayAuthMessage(error.message || "Registration failed. Please try again.");
            } finally {
                hideSpinner(spinnerId);
            }
        }

        // --- Email/Password Login ---
        async function handleLogin(event) {
            if (event) event.preventDefault();
            clearAuthMessages();
            if (!auth) { displayAuthMessage("Authentication service is not ready. Please refresh."); return; }
            
            const spinnerId = 'loginSpinner';
            showSpinner(spinnerId);
        
            const emailInput = document.getElementById('loginEmail');
            const passwordInput = document.getElementById('loginPassword');

            if(!emailInput || !passwordInput) {
                console.error("Login form fields are missing from the DOM.");
                displayAuthMessage("Login form error. Please refresh the page.");
                hideSpinner(spinnerId);
                return;
            }

            const email = emailInput.value.trim();
            const password = passwordInput.value;

            if (!email || !password) {
                displayAuthMessage("Email and Password are required.");
                hideSpinner(spinnerId);
                return;
            }
        
            try {
                const userCredential = await auth.signInWithEmailAndPassword(email, password);
                const user = userCredential.user;
        
                if (!user.emailVerified) {
                    displayAuthMessage("Please verify your email before logging in. A verification email was sent when you registered. If needed, you can try registering again to receive a new one or use 'Forgot Password' to reset if you've already verified once.");
                    await auth.signOut(); 
                    hideSpinner(spinnerId);
                    return;
                }
        
                const idToken = await user.getIdToken(true);
                await verifyTokenWithBackend(idToken); // This will redirect on success
        
            } catch (error) {
                console.error("Login error:", error);
                displayAuthMessage(error.message || "Login failed. Please check your credentials or verify your email.");
                hideSpinner(spinnerId); // Ensure spinner hidden on login error
            }
            // No finally hideSpinner here because verifyTokenWithBackend redirects.
            // If verifyTokenWithBackend fails client-side or backend returns error, it calls displayAuthMessage,
            // and then the spinner should be hidden if it wasn't handled by button re-enabling or redirect.
        }

        // --- Google Sign-In/Sign-Up ---
        async function signInWithGoogle() {
            clearAuthMessages();
            if (!auth) { displayAuthMessage("Authentication service is not ready for Google Sign-In. Please refresh."); return; }

            let activeSpinnerId = null;
            if (document.getElementById('googleSignInSpinnerLogin')) activeSpinnerId = 'googleSignInSpinnerLogin';
            else if (document.getElementById('googleSignInSpinnerRegister')) activeSpinnerId = 'googleSignInSpinnerRegister';
            
            if(activeSpinnerId) showSpinner(activeSpinnerId);
            else console.warn("Google sign-in spinner element not found.");
        
            const provider = new firebase.auth.GoogleAuthProvider();
            // Ensure we request email and profile and set prompt
            provider.addScope('email');
            provider.addScope('profile');
            provider.setCustomParameters({ prompt: 'select_account' });
            try {
                const result = await auth.signInWithPopup(provider);
                const user = result.user;
                
                console.log("Google Sign-In User:", user);
                // No need to check user.emailVerified for Google, as Firebase handles it.
                // Backend /verify-token will also check if 'email_verified' is true in the token.

                const idToken = await user.getIdToken(true);
                await verifyTokenWithBackend(idToken); // This will redirect on success
            } catch (error) {
                console.error("Google Sign-In error Full:", error); 
                let errorMessage = "Google Sign-In failed. Please try again. Check the browser console for more details.";
                if (error.code) { // More specific error handling
                    switch (error.code) {
                        case 'auth/popup-closed-by-user':
                        case 'auth/cancelled-popup-request':
                        case 'auth/user-cancelled':
                            errorMessage = "Google Sign-In cancelled."; break;
                        case 'auth/account-exists-with-different-credential':
                            errorMessage = "An account already exists with this email, but signed up using a different method (e.g., email/password). Try logging in with that method."; break;
                        case 'auth/popup-blocked':
                            errorMessage = "Google Sign-In popup was blocked. Please disable your popup blocker for this site and try again."; break;
                        case 'auth/operation-not-allowed':
                            errorMessage = "Google Sign-In is not enabled for this app. Please contact support."; break;
                        case 'auth/unauthorized-domain':
                            errorMessage = "This website domain is not authorized for Google Sign-In. Please contact support."; break;
                        default:
                            errorMessage = error.message || errorMessage;
                    }
                }
                displayAuthMessage(errorMessage);
                if(activeSpinnerId) hideSpinner(activeSpinnerId); // Ensure spinner hidden on error
            }
            // No finally hideSpinner here because verifyTokenWithBackend redirects.
        }

        // --- Forgot Password ---
        async function handleForgotPassword(event) {
            if(event) event.preventDefault();
            clearAuthMessages();
            if (!auth) { displayAuthMessage("Authentication service is not ready. Please refresh."); return; }

            const emailInput = document.getElementById('loginEmail'); // Prefer email from login form if present
            let email = emailInput ? emailInput.value.trim() : '';

            if (!email) {
                email = prompt("Please enter your email address to reset your password:");
                if (!email) return; // User cancelled prompt
                email = email.trim();
            }
            
            if(!email){
                displayAuthMessage("Please enter an email address.");
                return;
            }
        
            const spinnerId = 'loginSpinner'; // Reuse login spinner
            showSpinner(spinnerId); 
        
            try {
                await auth.sendPasswordResetEmail(email);
                displayAuthMessage("Password reset email sent to " + email + "! Please check your inbox (and spam folder).", "success");
            } catch (error) {
                console.error("Password reset error:", error);
                displayAuthMessage(error.message || "Failed to send password reset email. Ensure the email address is correct and registered.");
            } finally {
                hideSpinner(spinnerId);
            }
        }
        
        // --- Logout Function ---
        async function handleLogout() {
            try {
                if (auth) {
                    await auth.signOut();
                    console.log("User signed out from Firebase client-side.");
                } else {
                    console.warn("Firebase Auth not available for client-side sign out, redirecting for server logout.");
                }
            } catch (error) {
                console.error("Firebase client logout error:", error);
            } finally {
                window.location.href = '/logout'; // Always redirect to server logout
            }
        }
        
        // --- ATTACH EVENT LISTENERS ---
        // This assumes you REMOVE onsubmit/onclick from your HTML elements and use these JS-driven listeners.

        const loginFormEl = document.getElementById('loginForm');
        if (loginFormEl) loginFormEl.addEventListener('submit', handleLogin);

        const registerFormEl = document.getElementById('registerForm');
        if (registerFormEl) registerFormEl.addEventListener('submit', handleRegister);

        const googleSignInButtonEl = document.getElementById('googleSignInButton');
        if (googleSignInButtonEl) googleSignInButtonEl.addEventListener('click', signInWithGoogle);
        
        const googleSignUpButtonEl = document.getElementById('googleSignUpButton');
        if (googleSignUpButtonEl) googleSignUpButtonEl.addEventListener('click', signInWithGoogle); 
        
        // Forgot password link now navigates to dedicated page
        // No special handling needed since we have a dedicated forgot password page

        document.querySelectorAll('.password-toggle').forEach(button => {
            button.addEventListener('click', function() {
                // Find the input field within the same password-wrapper
                const inputField = this.parentElement.querySelector('input[type="password"], input[type="text"]');
                if (inputField && inputField.id) {
                    togglePasswordVisibility(inputField.id, this);
                } else {
                    // Fallback for different structures (e.g., using a data-target attribute)
                    const targetId = this.dataset.targetId;
                    if (targetId) togglePasswordVisibility(targetId, this);
                    else console.warn("Could not find password field for toggle button:", this);
                }
            });
        });

        // Navbar logout link
        const navLogoutLinkEl = document.getElementById('logoutLinkNav'); // Assumes ID in _base.html nav
        if (navLogoutLinkEl) {
            navLogoutLinkEl.addEventListener('click', function(e) {
                e.preventDefault();
                handleLogout();
            });
        }
        // For profile page logout button
        const pageLogoutButtonEl = document.getElementById('logoutButtonPage');
        if (pageLogoutButtonEl) {
             pageLogoutButtonEl.addEventListener('click', function(e) {
                e.preventDefault();
                handleLogout();
            });
        }
        
        console.log("Firebase-init.js setup complete and event listeners attached.");

    } catch (e) {
        // This outer catch is for truly critical errors during the initial setup.
        console.error("CRITICAL SCRIPT ERROR in firebase-init.js:", e);
        const bodyElement = document.body;
        if (bodyElement) {
            let criticalErrorDiv = document.getElementById('firebase-critical-error-global');
            if (!criticalErrorDiv) {
                criticalErrorDiv = document.createElement('div');
                criticalErrorDiv.id = 'firebase-critical-error-global';
                criticalErrorDiv.style.color = 'white';
                criticalErrorDiv.style.backgroundColor = 'darkred';
                criticalErrorDiv.style.padding = '20px';
                criticalErrorDiv.style.textAlign = 'center';
                criticalErrorDiv.style.position = 'fixed';
                criticalErrorDiv.style.top = '0';
                criticalErrorDiv.style.left = '0';
                criticalErrorDiv.style.width = '100%';
                criticalErrorDiv.style.zIndex = '10000';
                criticalErrorDiv.style.fontSize = '1.2em';
                criticalErrorDiv.style.boxSizing = 'border-box';
                bodyElement.prepend(criticalErrorDiv);
            }
            criticalErrorDiv.textContent = `A critical error occurred loading essential application services: ${e.message}. Authentication may be unavailable. Please refresh or contact support.`;
            criticalErrorDiv.style.display = 'block';
        }
    }
});
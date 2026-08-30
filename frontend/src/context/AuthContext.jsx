import React, { useState, useEffect, useCallback } from 'react';
import { AuthContext } from './authContextInstance';
import { api, tokenStorage } from '../services/api';
import {
  isWebAuthnSupported,
  prepareCreationOptions,
  serializeCreationCredential,
  prepareRequestOptions,
  serializeRequestAssertion,
} from '../services/webauthn';

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [authError, setAuthError] = useState(null);

  const logout = useCallback(() => {
    tokenStorage.clearToken();
    setUser(null);
    setAuthError(null);
  }, []);

  // Restore authenticated session on startup
  useEffect(() => {
    let isMounted = true;

    // Listen for unauthorized 401 triggers
    tokenStorage.onUnauthorized(() => {
      if (isMounted) {
        setUser(null);
      }
    });

    const restoreSession = async () => {
      const existingToken = tokenStorage.getToken();
      if (!existingToken) {
        if (isMounted) {
          setUser(null);
          setIsLoading(false);
        }
        return;
      }

      try {
        const userProfile = await api.getMe();
        if (isMounted) {
          setUser(userProfile);
        }
      } catch (err) {
        console.warn('Session restoration failed:', err.message);
        tokenStorage.clearToken();
        if (isMounted) {
          setUser(null);
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };

    restoreSession();

    return () => {
      isMounted = false;
    };
  }, []);

  /**
   * Password Login
   */
  const login = async (email, password) => {
    setAuthError(null);
    try {
      const tokenResponse = await api.login({ email, password });
      setUser(tokenResponse.user);
      return tokenResponse.user;
    } catch (err) {
      const msg = err.message || 'Login failed.';
      setAuthError(msg);
      throw err;
    }
  };

  /**
   * User Registration (Signup)
   */
  const signup = async ({ name, email, password, accessibility_prefs = null }) => {
    setAuthError(null);
    try {
      // 1. Create user account
      await api.signup({ name, email, password, accessibility_prefs });
      // 2. Automatically log in to establish JWT session
      const tokenResponse = await api.login({ email, password });
      setUser(tokenResponse.user);
      return tokenResponse.user;
    } catch (err) {
      const msg = err.message || 'Signup failed.';
      setAuthError(msg);
      throw err;
    }
  };

  /**
   * Passkey / WebAuthn Sign-In
   */
  const loginWithPasskey = async (email = null) => {
    setAuthError(null);
    if (!isWebAuthnSupported()) {
      const notSupportedMsg = 'Passkey authentication is not supported by this browser or environment.';
      setAuthError(notSupportedMsg);
      throw new Error(notSupportedMsg);
    }

    try {
      // 1. Retrieve authentication options and challenge from backend
      const options = await api.getPasskeyLoginOptions(email);
      const publicKeyOptions = prepareRequestOptions(options);

      // 2. Prompt browser authenticator (Windows Hello, Touch ID, Face ID, etc.)
      const assertion = await navigator.credentials.get({
        publicKey: publicKeyOptions,
      });

      if (!assertion) {
        throw new Error('Passkey authentication was cancelled.');
      }

      // 3. Serialize assertion and verify with backend
      const credentialPayload = serializeRequestAssertion(assertion);
      const tokenResponse = await api.verifyPasskeyLogin({
        credential: credentialPayload,
        challenge: options.challenge,
      });

      setUser(tokenResponse.user);
      return tokenResponse.user;
    } catch (err) {
      const msg = err.message || 'Passkey login failed.';
      setAuthError(msg);
      throw err;
    }
  };

  /**
   * Passkey Registration for Logged-In User
   */
  const registerPasskey = async (nickname = 'My Device Passkey') => {
    setAuthError(null);
    if (!isWebAuthnSupported()) {
      const notSupportedMsg = 'Passkey registration is not supported by this browser or environment.';
      setAuthError(notSupportedMsg);
      throw new Error(notSupportedMsg);
    }

    try {
      // 1. Retrieve registration options and challenge from backend
      const options = await api.getPasskeyRegisterOptions();
      const publicKeyOptions = prepareCreationOptions(options);

      // 2. Prompt browser authenticator to create credential
      const credential = await navigator.credentials.create({
        publicKey: publicKeyOptions,
      });

      if (!credential) {
        throw new Error('Passkey registration was cancelled.');
      }

      // 3. Serialize credential and verify with backend
      const credentialPayload = serializeCreationCredential(credential);
      const verifyResult = await api.verifyPasskeyRegistration({
        credential: credentialPayload,
        challenge: options.challenge,
        nickname,
      });

      // 4. Update user profile to reflect passkey status
      const updatedUser = await api.getMe();
      setUser(updatedUser);

      return verifyResult;
    } catch (err) {
      const msg = err.message || 'Passkey registration failed.';
      setAuthError(msg);
      throw err;
    }
  };

  const clearError = () => setAuthError(null);

  const value = {
    user,
    isAuthenticated: Boolean(user),
    isLoading,
    authError,
    login,
    signup,
    loginWithPasskey,
    registerPasskey,
    logout,
    clearError,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

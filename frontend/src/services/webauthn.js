/**
 * WebAuthn & Passkey Client-Side Cryptographic Utilities.
 *
 * Implements FIDO2 / WebAuthn Level 3 standard encoding and browser APIs
 * using navigator.credentials.create() and navigator.credentials.get().
 *
 * CRITICAL SECURITY & PRIVACY GUARANTEES:
 * 1. Zero raw biometrics (fingerprints, face data) are processed, stored, or transmitted.
 * 2. Only standard WebAuthn public key credential and assertion envelopes are created.
 */

/**
 * Checks whether the browser and environment support WebAuthn / Passkeys.
 */
export function isWebAuthnSupported() {
  return (
    typeof window !== 'undefined' &&
    window.PublicKeyCredential !== undefined &&
    typeof window.PublicKeyCredential === 'function' &&
    typeof navigator !== 'undefined' &&
    navigator.credentials !== undefined &&
    typeof navigator.credentials.create === 'function' &&
    typeof navigator.credentials.get === 'function'
  );
}

/**
 * Converts a base64url string to an ArrayBuffer.
 */
export function base64urlToBuffer(base64url) {
  if (!base64url) return new ArrayBuffer(0);
  const padding = '='.repeat((4 - (base64url.length % 4)) % 4);
  const base64 = (base64url + padding).replace(/-/g, '+').replace(/_/g, '/');
  const rawData = window.atob(base64);
  const outputArray = new Uint8Array(rawData.length);
  for (let i = 0; i < rawData.length; ++i) {
    outputArray[i] = rawData.charCodeAt(i);
  }
  return outputArray.buffer;
}

/**
 * Converts an ArrayBuffer or Uint8Array to a base64url string.
 */
export function bufferToBase64url(buffer) {
  if (!buffer) return '';
  const bytes = buffer instanceof Uint8Array ? buffer : new Uint8Array(buffer);
  let binary = '';
  for (let i = 0; i < bytes.byteLength; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  const base64 = window.btoa(binary);
  return base64.replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, '');
}

/**
 * Prepares server registration options for navigator.credentials.create().
 */
export function prepareCreationOptions(serverOptions) {
  const options = { ...serverOptions };

  // Convert challenge to Uint8Array
  if (typeof options.challenge === 'string') {
    options.challenge = base64urlToBuffer(options.challenge);
  }

  // Convert user.id to Uint8Array
  if (options.user && typeof options.user.id === 'string') {
    options.user = {
      ...options.user,
      id: base64urlToBuffer(options.user.id),
    };
  }

  // Convert excludeCredentials IDs to Uint8Array
  if (Array.isArray(options.excludeCredentials)) {
    options.excludeCredentials = options.excludeCredentials.map((cred) => ({
      ...cred,
      id: typeof cred.id === 'string' ? base64urlToBuffer(cred.id) : cred.id,
    }));
  }

  return options;
}

/**
 * Serializes the PublicKeyCredential returned by navigator.credentials.create().
 */
export function serializeCreationCredential(credential) {
  const response = credential.response;
  const transports = typeof response.getTransports === 'function' ? response.getTransports() : [];

  return {
    id: credential.id,
    rawId: bufferToBase64url(credential.rawId),
    type: credential.type,
    response: {
      clientDataJSON: bufferToBase64url(response.clientDataJSON),
      attestationObject: bufferToBase64url(response.attestationObject),
      transports,
    },
    clientExtensionResults: credential.getClientExtensionResults ? credential.getClientExtensionResults() : {},
  };
}

/**
 * Prepares server authentication options for navigator.credentials.get().
 */
export function prepareRequestOptions(serverOptions) {
  const options = { ...serverOptions };

  // Convert challenge to Uint8Array
  if (typeof options.challenge === 'string') {
    options.challenge = base64urlToBuffer(options.challenge);
  }

  // Convert allowCredentials IDs to Uint8Array
  if (Array.isArray(options.allowCredentials)) {
    options.allowCredentials = options.allowCredentials.map((cred) => ({
      ...cred,
      id: typeof cred.id === 'string' ? base64urlToBuffer(cred.id) : cred.id,
    }));
  }

  return options;
}

/**
 * Serializes the PublicKeyCredential assertion returned by navigator.credentials.get().
 */
export function serializeRequestAssertion(assertion) {
  const response = assertion.response;

  return {
    id: assertion.id,
    rawId: bufferToBase64url(assertion.rawId),
    type: assertion.type,
    response: {
      clientDataJSON: bufferToBase64url(response.clientDataJSON),
      authenticatorData: bufferToBase64url(response.authenticatorData),
      signature: bufferToBase64url(response.signature),
      userHandle: response.userHandle ? bufferToBase64url(response.userHandle) : null,
    },
    clientExtensionResults: assertion.getClientExtensionResults ? assertion.getClientExtensionResults() : {},
  };
}

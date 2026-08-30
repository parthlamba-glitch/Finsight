/**
 * FinSight API Service.
 *
 * Centralized, authenticated API client communicating with the FastAPI backend.
 *
 * ARCHITECTURAL GUARANTEES:
 * 1. Derives identity strictly from JWT Bearer token; frontend does NOT decide user_id.
 * 2. Zero hardcoded LAN IPs or user IDs.
 * 3. Handles 401 Unauthorized responses by clearing session state.
 * 4. Passwords and biometric templates are never stored or exposed.
 */

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
const TOKEN_STORAGE_KEY = 'finsight_access_token';

let unauthorizedHandler = null;

export const tokenStorage = {
  getToken() {
    try {
      return localStorage.getItem(TOKEN_STORAGE_KEY);
    } catch {
      return null;
    }
  },

  setToken(token) {
    try {
      if (token) {
        localStorage.setItem(TOKEN_STORAGE_KEY, token);
      } else {
        localStorage.removeItem(TOKEN_STORAGE_KEY);
      }
    } catch (e) {
      console.error('Failed to access localStorage', e);
    }
  },

  clearToken() {
    try {
      localStorage.removeItem(TOKEN_STORAGE_KEY);
    } catch (e) {
      console.error('Failed to clear localStorage token', e);
    }
  },

  onUnauthorized(handler) {
    unauthorizedHandler = handler;
  },
};

/**
 * Core authenticated HTTP request helper.
 */
async function request(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  };

  const token = tokenStorage.getToken();
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const config = {
    ...options,
    headers,
  };

  let response;
  try {
    response = await fetch(url, config);
  } catch (err) {
    throw new Error(`Unable to connect to the FinSight server (${err.message}). Please verify that the backend is running.`);
  }

  if (response.status === 401) {
    tokenStorage.clearToken();
    if (typeof unauthorizedHandler === 'function') {
      unauthorizedHandler();
    }
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || 'Session expired. Please log in again.');
  }

  if (!response.ok) {
    let errorDetail = 'An unexpected server error occurred.';
    try {
      const errorBody = await response.json();
      if (errorBody.detail) {
        if (Array.isArray(errorBody.detail)) {
          errorDetail = errorBody.detail.map((d) => d.msg || JSON.stringify(d)).join(', ');
        } else {
          errorDetail = String(errorBody.detail);
        }
      }
    } catch {
      errorDetail = `Request failed with status ${response.status}`;
    }
    throw new Error(errorDetail);
  }

  return response.json();
}

export const api = {
  // =========================================================================
  // 1. Authentication & Passkey Endpoints
  // =========================================================================

  /**
   * Registers a new user account with secure password hashing.
   * Backend returns UserResponse (status 201).
   */
  async signup({ name, email, password, accessibility_prefs = null }) {
    return request('/auth/signup', {
      method: 'POST',
      body: JSON.stringify({
        name,
        email,
        password,
        accessibility_prefs,
      }),
    });
  },

  /**
   * Authenticates user via email and password, issuing a JWT access token.
   * Backend returns TokenResponse (status 200).
   */
  async login({ email, password }) {
    const data = await request('/auth/login', {
      method: 'POST',
      body: JSON.stringify({
        email,
        password,
      }),
    });
    if (data.access_token) {
      tokenStorage.setToken(data.access_token);
    }
    return data;
  },

  /**
   * Retrieves profile information for the authenticated user from JWT.
   */
  async getMe() {
    return request('/auth/me', {
      method: 'GET',
    });
  },

  /**
   * Requests WebAuthn registration options for the logged-in user.
   */
  async getPasskeyRegisterOptions() {
    return request('/auth/passkey/register/options', {
      method: 'POST',
    });
  },

  /**
   * Verifies WebAuthn registration credential with backend.
   */
  async verifyPasskeyRegistration({ credential, challenge, nickname = 'My Device Passkey' }) {
    return request('/auth/passkey/register/verify', {
      method: 'POST',
      body: JSON.stringify({
        credential,
        challenge,
        nickname,
      }),
    });
  },

  /**
   * Requests WebAuthn login options for passkey sign-in.
   */
  async getPasskeyLoginOptions(email = null) {
    return request('/auth/passkey/login/options', {
      method: 'POST',
      body: JSON.stringify(email ? { email } : {}),
    });
  },

  /**
   * Verifies WebAuthn login assertion and issues JWT token.
   */
  async verifyPasskeyLogin({ credential, challenge }) {
    const data = await request('/auth/passkey/login/verify', {
      method: 'POST',
      body: JSON.stringify({
        credential,
        challenge,
      }),
    });
    if (data.access_token) {
      tokenStorage.setToken(data.access_token);
    }
    return data;
  },

  /**
   * Lists all passkey credentials registered for the current user.
   */
  async listPasskeys() {
    return request('/auth/passkey/credentials', {
      method: 'GET',
    });
  },

  /**
   * Deletes a registered passkey credential by ID.
   */
  async deletePasskey(id) {
    return request(`/auth/passkey/credentials/${id}`, {
      method: 'DELETE',
    });
  },

  // =========================================================================
  // 2. Financial Overview & Ledger Endpoints
  // =========================================================================

  /**
   * Fetches deterministic dashboard overview for authenticated user.
   */
  async getDashboardOverview() {
    return request('/overview', {
      method: 'GET',
    });
  },

  /**
   * Legacy alias matching dashboard stats contract.
   */
  async getDashboardStats() {
    const data = await this.getDashboardOverview();
    return {
      balance: data.balance,
      spending: data.monthly_spending,
      income: data.monthly_income,
      surplus: data.monthly_surplus,
      savings: data.savings,
      upcomingBills: data.upcoming_bills,
      goals: data.goals || [],
    };
  },

  /**
   * Fetches transaction history for period ('this_month' or 'last_month').
   */
  async getTransactions(period = 'this_month') {
    const data = await request(`/transactions?period=${encodeURIComponent(period)}`, {
      method: 'GET',
    });
    return data.transactions || [];
  },

  /**
   * Adds a development synthetic deposit for the authenticated user (demo mode only).
   */
  async addDemoDeposit({
    amount,
    merchant_name = 'Demo Salary Deposit',
    description = 'Synthetic development deposit',
    category = 'Other',
    account_id = null,
  }) {
    const amountNum = typeof amount === 'number' ? amount : Number(String(amount).replace(/[^0-9.-]+/g, ''));
    return request('/transactions/demo-deposit', {
      method: 'POST',
      body: JSON.stringify({
        amount: amountNum,
        merchant_name,
        description,
        category,
        account_id,
      }),
    });
  },

  /**
   * Fetches user financial goals.
   */
  async getGoals() {
    return request('/goals', {
      method: 'GET',
    });
  },

  /**
   * Creates a new financial goal for the authenticated user.
   */
  async createGoal({ name, target_amount, monthly_contribution, target_date = null }) {
    return request('/goals', {
      method: 'POST',
      body: JSON.stringify({
        name,
        target_amount,
        monthly_contribution,
        target_date,
      }),
    });
  },

  /**
   * Updates a goal's monthly contribution and receives deterministic projection.
   */
  async updateGoalContribution(id, monthly_contribution) {
    return request(`/goals/${id}`, {
      method: 'PATCH',
      body: JSON.stringify({
        monthly_contribution,
      }),
    });
  },

  // =========================================================================
  // 3. Bank & Statement Ingestion Endpoints
  // =========================================================================

  /**
   * Triggers deterministic mock bank synchronization.
   */
  async syncBank(accountId = null) {
    return request('/bank/sync', {
      method: 'POST',
      body: JSON.stringify(accountId ? { account_id: accountId } : {}),
    });
  },

  /**
   * Uploads statement extracted candidates for duplicate evaluation and staging.
   */
  async uploadStatement(filename, candidates, accountId = null) {
    return request('/statements/upload', {
      method: 'POST',
      body: JSON.stringify({
        filename,
        extracted_candidates: candidates,
        account_id: accountId,
      }),
    });
  },

  /**
   * Confirms and persists validated statement candidates into transactions ledger.
   */
  async confirmStatement(candidates, accountId = null, documentId = null) {
    return request('/transactions/confirm', {
      method: 'POST',
      body: JSON.stringify({
        candidates,
        account_id: accountId,
        document_id: documentId,
      }),
    });
  },

  // =========================================================================
  // 4. Payment Preview & Execution Endpoints
  // =========================================================================

  /**
   * Previews a payment deterministically and stages a persistent PendingPayment row.
   */
  async previewPayment(amount, recipient) {
    const amountNum = typeof amount === 'number' ? amount : Number(String(amount).replace(/[^0-9.-]+/g, ''));
    return request('/payments/preview', {
      method: 'POST',
      body: JSON.stringify({
        amount: amountNum,
        recipient_name: recipient,
      }),
    });
  },

  /**
   * Executes a staged PendingPayment upon explicit user authorization.
   */
  async executePayment(pendingPaymentId) {
    return request('/payments/execute', {
      method: 'POST',
      body: JSON.stringify({
        pending_payment_id: Number(pendingPaymentId),
      }),
    });
  },

  // =========================================================================
  // 5. Conversational AI (/ask) & Scam Checker
  // =========================================================================

  /**
   * Dispatches conversational/voice query to the AI copilot.
   */
  async askFinsight(query, conversationId = null, confirmationToken = null, voice = true) {
    return request('/ask', {
      method: 'POST',
      body: JSON.stringify({
        query,
        voice,
        conversation_id: conversationId,
        confirmation_token: confirmationToken ? String(confirmationToken) : null,
      }),
    });
  },

  /**
   * Checks suspicious message/SMS via backend AI Scam Checker (/ask).
   */
  async checkScam(message) {
    const cleanMessage = String(message || '').trim();
    if (!cleanMessage) {
      throw new Error('Please provide a message or SMS to check.');
    }

    const query = `Check if this message is a scam: ${cleanMessage}`;
    const askResponse = await this.askFinsight(query, null, null, false);

    const facts = askResponse.structured_facts || askResponse.structured_data || {};

    return {
      intent: askResponse.intent,
      answer_text: askResponse.answer_text,
      aria_priority: askResponse.aria_priority || 'polite',
      risk_level: facts.risk_level || (facts.looks_suspicious ? 'high' : 'low'),
      looks_suspicious: Boolean(facts.looks_suspicious),
      indicators: Array.isArray(facts.indicators) ? facts.indicators : [],
      explanation: facts.explanation || askResponse.answer_text,
      recommended_actions: Array.isArray(facts.recommended_actions) ? facts.recommended_actions : [],
      limitations: facts.limitations || 'This is an AI pattern-based safety assessment.',
    };
  },
};

// API Base URL (FastAPI Backend)
const API_BASE = 'http://10.69.0.26:8000';
const USER_ID = 1; // Default user for demo

export const api = {
  // Fetch from Real Backend, fallback to mock if offline
  async getDashboardStats() {
    try {
      const response = await fetch(`${API_BASE}/api/v1/dashboard/overview?user_id=${USER_ID}`);
      if (!response.ok) throw new Error('Backend error');
      const data = await response.json();
      
      return {
        balance: data.balance,
        spending: data.monthly_spending,
        goals: data.goals || []
      };
    } catch (err) {
      console.warn("Backend not reachable. Using fallback mock state.");
      return {
        balance: 138372,
        spending: 18200,
        goals: []
      };
    }
  },

  async getTransactions(period = 'this_month') {
    try {
      const response = await fetch(`${API_BASE}/api/v1/transactions?user_id=${USER_ID}&period=${period}`);
      if (!response.ok) throw new Error('Backend error');
      const data = await response.json();
      return data.transactions || [];
    } catch (err) {
      console.warn("Failed to fetch transactions.");
      return [];
    }
  },

  async syncBank(accountId = 1) {
    const response = await fetch(`${API_BASE}/api/v1/bank/sync`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: USER_ID, account_id: accountId })
    });
    if (!response.ok) throw new Error('Failed to sync bank');
    return await response.json();
  },

  async uploadStatement(filename, candidates) {
    const response = await fetch(`${API_BASE}/api/v1/statements/upload`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: USER_ID,
        filename: filename,
        extracted_candidates: candidates
      })
    });
    if (!response.ok) throw new Error('Failed to upload statement');
    return await response.json();
  },

  async confirmStatement(candidates) {
    const response = await fetch(`${API_BASE}/api/v1/transactions/confirm`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: USER_ID,
        candidates: candidates
      })
    });
    if (!response.ok) throw new Error('Failed to confirm statement');
    return await response.json();
  },

  async previewPayment(amount, recipient) {
    const amountNum = Number(amount.replace(/[^0-9.-]+/g, ""));
    const response = await fetch(`${API_BASE}/api/v1/payments/preview`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: USER_ID,
        amount: amountNum,
        recipient_name: recipient
      })
    });
    
    if (!response.ok) {
      const err = await response.json();
      throw new Error(err.detail || "Failed to preview payment");
    }
    
    return await response.json();
  },

  async executePayment(pendingPaymentId) {
    const response = await fetch(`${API_BASE}/api/v1/payments/execute`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: USER_ID,
        pending_payment_id: pendingPaymentId
      })
    });
    
    if (!response.ok) {
      const err = await response.json();
      throw new Error(err.detail || "Failed to execute payment");
    }
    
    return await response.json();
  },

  async askFinsight(query, conversationId = null, confirmationToken = null) {
    try {
      const response = await fetch(`${API_BASE}/api/v1/ask`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: USER_ID,
          query: query,
          voice: true,
          conversation_id: conversationId,
          confirmation_token: confirmationToken
        })
      });
      
      if (!response.ok) {
        throw new Error("Failed to process voice query");
      }
      
      return await response.json();
    } catch (err) {
      console.error(err);
      // Fallback response if the backend is down
      return {
        intent: 'ERROR',
        answer_text: "I'm having trouble connecting to the financial engine.",
        requires_confirmation: false
      };
    }
  },
  
  async checkScam(message) {
    await new Promise(resolve => setTimeout(resolve, 2000));
    return {
      isScam: true,
      warningSigns: [
        {
          title: 'Urgency',
          description: 'The message pressures you to act quickly.'
        },
        {
          title: 'Sensitive information',
          description: 'It asks for account information.'
        },
        {
          title: 'Suspicious payment request',
          description: 'It asks for an unusual payment.'
        }
      ],
      recommendation: 'Do not click links or share sensitive information until you verify the sender.'
    };
  }
};

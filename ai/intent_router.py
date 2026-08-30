"""
FinSight AI Intent Router
=========================

Semantic natural-language understanding layer that maps arbitrary user queries
to exactly ONE deterministic financial-engine operation.

ARCHITECTURAL INVARIANTS:
-------------------------
1. The LLM must NEVER calculate financial values, percentages, or projections.
2. The deterministic financial engine is the ONLY source of financial truth.
3. The LLM's ONLY responsibility is:
   a. Semantic understanding of arbitrary conversational requests.
   b. Selecting exactly ONE approved financial operation.
   c. Extracting raw parameters (e.g. amount, period, goal_name) without arithmetic.
4. The router NEVER accesses databases or raw transactions.
5. The router NEVER invents missing parameters, amounts, goal IDs, or user IDs.
6. The `user_id` is supplied by application context and injected by Python.
"""

from decimal import Decimal
import json
import os
import re
from typing import Any, Dict, Optional
# pyrefly: ignore [missing-import]
from dotenv import load_dotenv
# pyrefly: ignore [missing-import]
from openai import OpenAI

load_dotenv()

# ==============================================================================
# FINANCIAL ENGINE TOOL DEFINITIONS (OpenAI Function Calling Schema)
# ==============================================================================

FINSIGHT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_balance",
            "description": (
                "Fetch current account balance, net worth, remaining money, available funds, or cash on hand. "
                "Select this for any query asking how much money the user has, what's sitting in the account, "
                "what's left, or asking if they are low on money right now."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_spending_summary",
            "description": (
                "Retrieve spending totals, category breakdowns, or where money went over a given time period. "
                "Select this for any query asking how much was spent, where money disappeared/went, "
                "what the user has been spending on, category expenses (e.g. food), or overall spending history."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "period": {
                        "type": "string",
                        "enum": ["this_month", "last_month", "this_week", "last_week", "custom"],
                        "description": "The time period for the spending summary (e.g. 'this_month', 'last_month'). Default to 'this_month' if unspecified.",
                    },
                    "category": {
                        "type": "string",
                        "description": "Optional category filter if mentioned (e.g. 'food', 'groceries', 'shopping', 'transport').",
                    },
                },
                "required": ["period"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_affordability",
            "description": (
                "Evaluate whether the user can safely afford a proposed purchase or spending amount. "
                "MUST ONLY be selected when the user provides an explicit purchase cost or price amount "
                "(e.g. '8k' -> 8000, '20 grand' -> 20000, '15 thousand' -> 15000, '₹12,000' -> 12000). "
                "DO NOT select this tool if no price or amount is mentioned in the query."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "amount": {
                        "type": "number",
                        "description": "The explicit numerical cost or price of the item/purchase. Extract as a positive number.",
                    },
                    "item_description": {
                        "type": "string",
                        "description": "Optional description of the item or purchase (e.g. 'phone', 'laptop', 'headphones', 'shoes').",
                    },
                },
                "required": ["amount"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "project_goal_completion",
            "description": (
                "Estimate target completion timeline, progress, or months remaining for a specific savings goal. "
                "Select this when the user asks when a named savings goal (e.g. 'emergency fund', 'vacation') will be reached "
                "or how adding extra savings would help."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "goal_name_or_id": {
                        "type": "string",
                        "description": "The name of the savings goal mentioned by the user (e.g. 'emergency fund', 'vacation').",
                    },
                    "hypothetical_contribution": {
                        "type": "number",
                        "description": "Optional additional recurring contribution amount proposed by the user.",
                    },
                },
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_insights",
            "description": (
                "Retrieve algorithmic insights explaining WHY spending changed, unusual expenses, spikes, "
                "spending anomalies, recurring patterns, or trends detected from transaction history."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_scam_message",
            "description": (
                "Analyze a supplied SMS, chat, email, or message for potential scam, phishing, or fraud indicators. "
                "Select this whenever the user asks to check if a message/SMS/link is a scam, fake, fraudulent, or suspicious, "
                "or when the user pastes a suspicious message to be analyzed."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "The exact message or SMS text to evaluate for scam and fraud patterns.",
                    },
                },
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "sync_bank",
            "description": (
                "Trigger a bank account synchronization or refresh action to update bank feeds. "
                "Select this when the user asks to sync their bank, refresh accounts, update bank feeds, "
                "or in Hindi/Hinglish (e.g., 'Sync my bank', 'Refresh my account', 'Bank update kar do', 'Bank sync karo', 'Mera bank update karo')."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_recent_transactions",
            "description": (
                "Trigger a UI accessibility action to read aloud or display recent transaction history. "
                "Select this when the user asks to read their transactions, show recent expenses/transactions, "
                "or in Hindi/Hinglish (e.g., 'Read my recent transactions', 'Read my transactions', 'Last transactions kya hai?', 'What did I spend recently?')."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_goals",
            "description": (
                "Trigger a UI accessibility action to read aloud or display active savings goals and target progress. "
                "Select this when the user asks to read their goals, tell them their goals, or in Hindi/Hinglish "
                "(e.g., 'Read my goals', 'Tell me my goals', 'Mera goal progress kya hai?', 'Read my goal progress', 'Goals sunao')."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "upload_document",
            "description": (
                "Trigger a UI action to open the document scanner or upload bank statement files. "
                "Select this when the user asks to upload a document, upload a bank statement, scan statement, "
                "or in Hindi/Hinglish (e.g., 'Upload a document', 'I want to upload my bank statement', 'Bank statement scan karo', 'Upload my statement')."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        },
    },
]

SYSTEM_PROMPT = """You are FinSight's AI Intent Router.
Your role is to understand arbitrary natural language personal finance queries and accessibility commands from users and route them semantically to EXACTLY ONE of the supported operations:

==================================================
FINANCIAL ENGINE OPERATIONS
==================================================

1. get_balance
Meaning: Any inquiry asking how much money the user currently has, remaining account balance, net worth, available funds, cash on hand, or whether they are running low on money.
Examples:
- "What's my balance?"
- "how much money do i have?"
- "bro how much money do i have?"
- "how much is left in my account?"
- "how much have I got left?"
- "what's sitting in my account?"
- "what do I have available right now?"
- "how much money is mine right now?"
- "am I running low on money right now?"

2. get_spending_summary
Meaning: Any inquiry asking how much the user spent, where their money went, category breakdowns, or spending during a specific time period.
Examples:
- "How much did I spend this month?"
- "where did most of my money go this month?"
- "where is all my money disappearing?"
- "what have I been spending on?"
- "what did I spend on food?"
- "how much did I spend last month?"
- "how much have I blown recently?"
Note: Extract the period parameter ('this_month', 'last_month', etc.). Default to 'this_month' if unspecified.

3. check_affordability
Meaning: Any inquiry asking whether the user can afford a purchase or spending amount ONLY WHEN an explicit price or amount is stated.
Extract the numerical amount:
- "8k" -> 8000
- "20 grand" -> 20000
- "12 thousand" / "12k" -> 12000
- "₹10,000" -> 10000
Examples:
- "Can I afford a phone for ₹10,000?"
- "can I buy these headphones for 8k?"
- "would a 20 grand laptop be okay?"
- "I want to spend 12 thousand on shoes, can I?"
- "do you think I can afford this thing for 15k?"
CRITICAL: If the user asks about buying/affordability WITHOUT specifying an amount (e.g. "Can I afford it?", "Should I buy this?", "can I get that laptop?"), DO NOT call check_affordability. Respond with a clarification asking for the price.

4. project_goal_completion
Meaning: Inquiries calculating mathematical projected completion date, months remaining, or timeline calculation for a specific named savings goal.
Examples:
- "when will I reach my emergency fund?"
- "how long until my savings goal is complete?"
- "when will I hit my emergency fund?"
- "when can I finish that emergency fund?"
CRITICAL DISTINCTION:
- If the user asks to read, show, list, or speak their goals (e.g. "Read my goals", "Tell me my goals", "Read my goal progress", "Mera goal progress kya hai?"), DO NOT select project_goal_completion; select read_goals instead.
- If the user asks about saving timeline calculation WITHOUT mentioning which goal (e.g. "How much longer do I need to save?"), DO NOT guess a goal. Respond asking which savings goal they want to check.

5. get_insights
Meaning: Inquiries asking WHY spending changed, anomalies, unusual expenses, patterns, or trends.
Examples:
- "why did I spend more this month?"
- "why am I spending so much?"
- "what's changed with my spending?"
- "anything weird going on with my expenses?"
- "have you noticed any patterns?"
- "are there any spending trends I should know about?"

==================================================
PROTECT / SCAM SAFETY OPERATIONS
==================================================

6. check_scam_message
Meaning: Inquiries asking to evaluate, check, or verify whether a message, SMS, email, link, or notification is a scam, phishing attempt, fraudulent, or suspicious, OR when a user pastes a message for safety analysis.
Examples:
- "Is this a scam?"
- "Can you check if this message is a scam?"
- "Can you check a message for me?"
- "Is this SMS fraudulent?"
- "Check this message for fraud: Your SBI account will be blocked..."
- "Does this look suspicious: Congratulations! You won ₹25,000..."
- "Is this a scam? Send OTP immediately."
- "Check if this link is safe."
Note: Extract the message parameter if present in the user's query. If the user asks to check a message without pasting the message text, call check_scam_message with message omitted or empty.

==================================================
UI CONTROL & ACCESSIBILITY COMMANDS
==================================================

7. sync_bank
Meaning: Voice or natural language commands asking to sync, refresh, or update connected bank accounts or feeds.
Examples:
- "Sync my bank"
- "Refresh my account"
- "Update my bank"
- "Bank update kar do"
- "Mera bank sync karo"
- "Bank refresh karo"

8. read_recent_transactions
Meaning: Voice commands asking the system to read aloud, display, or list recent transactions.
Examples:
- "Read my recent transactions"
- "Read my transactions"
- "Last transactions kya hai?"
- "What did I spend recently?"
- "Recent transactions sunao"
- "Show my recent transactions"

9. read_goals
Meaning: Voice commands asking to read aloud, display, or list active financial goals and progress.
Examples:
- "Read my goals"
- "Tell me my goals"
- "Mera goal progress kya hai?"
- "Read my goal progress"
- "Goals sunao"
- "Show my goals"

10. upload_document
Meaning: Voice commands asking to open document upload, scan bank statements, or import statement files.
Examples:
- "Upload a document"
- "I want to upload my bank statement"
- "Bank statement scan karo"
- "Upload my statement"
- "Statement upload karo"
- "Scan my statement"

==================================================
AMBIGUOUS & NON-FINANCIAL QUERIES
==================================================
- If the user's intent genuinely cannot be determined (e.g. "Is it okay?", "what about that?", "should I do it?"), request clarification.
- If the question is completely unrelated to personal finances, fraud safety, or app navigation (e.g. weather, sports, trivia, programming), politely decline stating FinSight only handles personal finances, scam safety, and financial navigation.
- NEVER invent financial numbers, user IDs, or goal IDs.
"""

SUPPORTED_FUNCTIONS = {
    "get_balance",
    "get_spending_summary",
    "check_affordability",
    "project_goal_completion",
    "get_insights",
    "check_scam_message",
    "sync_bank",
    "read_recent_transactions",
    "read_goals",
    "upload_document",
}



def _parse_amount_value(raw_val: Any) -> Optional[float]:
    """Robustly converts numeric or natural language price strings to positive float amounts."""
    if isinstance(raw_val, (int, float)) and not isinstance(raw_val, bool) and raw_val > 0:
        return float(raw_val)
    if not isinstance(raw_val, str) or not raw_val.strip():
        return None

    cleaned = raw_val.replace(",", "").replace("₹", "").replace("$", "").strip().lower()

    # Direct float conversion
    try:
        val = float(cleaned)
        if val > 0:
            return val
    except ValueError:
        pass

    # Pattern: 8k, 8.5k, 15k
    k_match = re.search(r"\b(\d+(?:\.\d+)?)\s*k\b", cleaned)
    if k_match:
        return float(k_match.group(1)) * 1000

    # Pattern: 20 grand
    grand_match = re.search(r"\b(\d+(?:\.\d+)?)\s*grand\b", cleaned)
    if grand_match:
        return float(grand_match.group(1)) * 1000

    # Pattern: 15 thousand, 12 thousand
    thousand_match = re.search(r"\b(\d+(?:\.\d+)?)\s*thousand\b", cleaned)
    if thousand_match:
        return float(thousand_match.group(1)) * 1000

    # Word numbers with word boundaries
    word_map = {
        "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
        "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
        "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
        "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
        "nineteen": 19, "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50,
    }
    for word, num in word_map.items():
        pattern = rf"\b{word}\s+(?:thousand|grand|k)\b"
        if re.search(pattern, cleaned):
            return float(num * 1000)

    # Embedded digits
    num_match = re.search(r"\b(\d+(?:\.\d+)?)\b", cleaned)
    if num_match:
        try:
            val = float(num_match.group(1))
            if val > 0:
                return val
        except ValueError:
            pass

    return None


def get_llm_client() -> OpenAI:
    """Initialize OpenAI-compatible client from environment variables."""
    api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY") or "dummy_key_for_mocking"
    base_url = os.getenv("LLM_BASE_URL") or None
    return OpenAI(api_key=api_key, base_url=base_url, timeout=30.0)



def route_query(
    query: str,
    user_id: str,
    context: Optional[Dict[str, Any]] = None,
    client: Optional[OpenAI] = None,
    model: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Routes a natural language financial query to exactly one financial-engine function.

    Parameters:
    -----------
    query : str
        The user's natural language input.
    user_id : str
        The application-authenticated user identifier (injected by Python).
    context : dict, optional
        Application context such as active goals mapping: {"goals": {"emergency fund": "goal_123", ...}}
        or {"goal_id": "goal_123"}.
    client : OpenAI, optional
        Custom or mocked OpenAI client.
    model : str, optional
        Model name override. Defaults to LLM_MODEL env var or 'gpt-4o-mini'.

    Returns:
    --------
    dict:
        Success: {"status": "success", "function_name": str, "arguments": dict}
        Clarification: {"status": "clarification_needed", "question": str}
        Error: {"status": "error", "message": str}
    """
    if not query or not query.strip():
        return {
            "status": "clarification_needed",
            "question": "How can I help with your finances today?",
        }

    if not user_id:
        return {
            "status": "error",
            "message": "user_id must be provided by the application context.",
        }

    context = context or {}
    llm_model = model or os.getenv("LLM_MODEL", "gpt-4o-mini")

    # Build messages array with conversational history if present
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if context.get("last_user_query") and context.get("last_clarification_question"):
        messages.append({"role": "user", "content": str(context["last_user_query"])})
        messages.append({"role": "assistant", "content": str(context["last_clarification_question"])})
    messages.append({"role": "user", "content": query})

    try:
        llm_client = client or get_llm_client()
        response = llm_client.chat.completions.create(
            model=llm_model,
            messages=messages,
            tools=FINSIGHT_TOOLS,
            tool_choice="auto",
            temperature=0.0,
        )


        choice = response.choices[0]
        message = choice.message

        # Check if the LLM invoked a function/tool
        if message.tool_calls and len(message.tool_calls) > 0:
            tool_call = message.tool_calls[0]
            func_name = tool_call.function.name

            if func_name not in SUPPORTED_FUNCTIONS:
                return {
                    "status": "error",
                    "message": f"Unsupported function selected by LLM: {func_name}",
                }

            # Parse arguments
            raw_args = tool_call.function.arguments
            if isinstance(raw_args, str):
                try:
                    args = json.loads(raw_args) if raw_args.strip() else {}
                except json.JSONDecodeError:
                    return {
                        "status": "error",
                        "message": f"Failed to parse function arguments JSON: {raw_args}",
                    }
            elif isinstance(raw_args, dict):
                args = raw_args
            else:
                args = {}

            # ==================================================================
            # Parameter Validation & Context Resolution
            # ==================================================================

            # 1. check_affordability validation
            if func_name == "check_affordability":
                raw_amount = args.get("amount")
                amount = _parse_amount_value(raw_amount)
                if amount is None or amount <= 0:
                    item_desc = args.get("item_description") or context.get("parameters", {}).get("item_description")
                    clean_params = {"item_description": item_desc} if item_desc else {}
                    return {
                        "status": "clarification_needed",
                        "question": "How much does the item cost?",
                        "intent": "check_affordability",
                        "extracted_parameters": clean_params,
                        "missing_parameters": ["amount"],
                    }
                args["amount"] = amount
                # Carry forward previous item_description from context if omitted in follow-up
                if not args.get("item_description") and context.get("parameters", {}).get("item_description"):
                    args["item_description"] = context["parameters"]["item_description"]

            # 2. project_goal_completion validation & goal_id resolution
            elif func_name == "project_goal_completion":
                goal_name_or_id = (
                    args.get("goal_name")
                    or args.get("goal_name_or_id")
                    or context.get("parameters", {}).get("goal_name")
                    or ""
                ).strip()

                resolved_goal_id = None

                # Check if goal_id directly exists in context
                if "goal_id" in context and context["goal_id"]:
                    resolved_goal_id = context["goal_id"]
                elif "parameters" in context and context["parameters"].get("goal_id"):
                    resolved_goal_id = context["parameters"]["goal_id"]
                elif "goals" in context and isinstance(context["goals"], dict) and goal_name_or_id:
                    goals_dict = context["goals"]
                    if goal_name_or_id in goals_dict:
                        resolved_goal_id = goals_dict[goal_name_or_id]
                    else:
                        for g_name, g_id in goals_dict.items():
                            if (
                                g_name.lower() in goal_name_or_id.lower()
                                or goal_name_or_id.lower() in g_name.lower()
                            ):
                                resolved_goal_id = g_id
                                break

                # Also accept explicit goal_id in args if provided
                if not resolved_goal_id and "goal_id" in args:
                    resolved_goal_id = args["goal_id"]

                # If no goal could be resolved from context/input, request clarification (never invent one)
                if not resolved_goal_id and not goal_name_or_id:
                    clean_params = {}
                    hypo = args.get("hypothetical_contribution") or context.get("parameters", {}).get("hypothetical_contribution")
                    if hypo:
                        clean_params["hypothetical_contribution"] = hypo
                    return {
                        "status": "clarification_needed",
                        "question": "Which savings goal would you like me to check?",
                        "intent": "project_goal_completion",
                        "extracted_parameters": clean_params,
                        "missing_parameters": ["goal_name_or_id"],
                    }

                # Construct clean arguments
                clean_args: Dict[str, Any] = {}
                if resolved_goal_id:
                    clean_args["goal_id"] = resolved_goal_id
                if goal_name_or_id:
                    clean_args["goal_name"] = goal_name_or_id

                hypo_contrib = args.get("hypothetical_contribution") or context.get("parameters", {}).get("hypothetical_contribution")
                if hypo_contrib is not None:
                    clean_args["hypothetical_contribution"] = hypo_contrib
                args = clean_args


            # 3. get_spending_summary default period handling
            elif func_name == "get_spending_summary":
                if "period" not in args or not args["period"]:
                    args["period"] = "this_month"

            # 4. check_scam_message validation & context resolution
            elif func_name == "check_scam_message":
                msg_text = (args.get("message") or "").strip()
                if not msg_text:
                    # Check if previous context was awaiting scam message clarification
                    if (
                        context.get("status") == "awaiting_clarification"
                        and context.get("intent") == "check_scam_message"
                    ):
                        msg_text = query.strip()
                    else:
                        # Check if the query itself is a message or just a generic inquiry
                        q_lower = query.lower().strip()
                        is_generic_inquiry = q_lower in (
                            "can you check a message for me?",
                            "can you check a message for me",
                            "can you check a message?",
                            "can you check a message",
                            "can you check if a message is a scam?",
                            "can you check if a message is a scam",
                            "can you check if this message is a scam?",
                            "can you check if this message is a scam",
                            "check a message for me",
                            "check a message",
                            "is this a scam?",
                            "is this a scam",
                            "check this message",
                            "check this sms",
                            "does this look suspicious?",
                            "is this suspicious?",
                        )
                        if is_generic_inquiry:
                            return {
                                "status": "clarification_needed",
                                "question": "Sure — please paste the message or SMS you'd like me to check.",
                                "intent": "check_scam_message",
                                "extracted_parameters": {},
                                "missing_parameters": ["message"],
                            }
                        else:
                            # Strip leading command prefixes like "Is this a scam?", "Check this message for fraud:"
                            cleaned_msg = re.sub(
                                r"^(?:is this a scam\??|check this message for fraud:?|check this sms for fraud:?|check this message:?|check this:?|is this suspicious\??)\s*",
                                "",
                                query,
                                flags=re.IGNORECASE,
                            ).strip()
                            msg_text = cleaned_msg if cleaned_msg else query.strip()

                if not msg_text:
                    return {
                        "status": "clarification_needed",
                        "question": "Sure — please paste the message or SMS you'd like me to check.",
                        "intent": "check_scam_message",
                        "extracted_parameters": {},
                        "missing_parameters": ["message"],
                    }

                args["message"] = msg_text

            # Inject user_id into arguments via Python (never generated by LLM)
            args["user_id"] = user_id

            return {
                "status": "success",
                "function_name": func_name,
                "arguments": args,
            }

        # If LLM returned text instead of a tool call (clarification or off-topic)
        content = message.content or ""
        return {
            "status": "clarification_needed",
            "question": content.strip() if content.strip() else "Could you please clarify your request?",
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Intent routing failed: {str(e)}",
        }

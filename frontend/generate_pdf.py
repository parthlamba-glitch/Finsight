from fpdf import FPDF
import os

pdf = FPDF()
pdf.add_page()
pdf.set_font("Arial", size=12)

# Title
pdf.set_font("Arial", 'B', 16)
pdf.cell(200, 10, txt="Backend UI Control Intents for FinSight", ln=True, align='C')
pdf.ln(10)

# Intro
pdf.set_font("Arial", size=12)
intro_text = "To make the FinSight app perfectly accessible for a blind user, the backend AI needs to be able to control the UI. Please add these 4 new Intents to the intent_router.py (Gemini prompts):"
pdf.multi_cell(0, 8, txt=intro_text)
pdf.ln(5)

# Intents
intents = [
    {
        "name": "1. sync_bank",
        "trigger": "When the user says 'Sync my bank', 'Refresh my account', or 'Bank update kar do'.",
        "action": "The AI should just return {\"intent\": \"sync_bank\"}. (The frontend will catch this and automatically click the Sync button for the blind user)."
    },
    {
        "name": "2. read_recent_transactions",
        "trigger": "When the user says 'Read my recent transactions', 'Last transactions kya hai?', or 'What did I spend on recently?'",
        "action": "The AI should return {\"intent\": \"read_recent_transactions\"}. (The frontend will then physically read the screen out loud)."
    },
    {
        "name": "3. read_goals",
        "trigger": "When the user says 'Read my goals', or 'Mera goal progress kya hai?'",
        "action": "The AI should return {\"intent\": \"read_goals\"}. (The frontend will read the goal progress bar out loud)."
    },
    {
        "name": "4. upload_document",
        "trigger": "When the user says 'Upload a document', 'Bank statement scan karo'.",
        "action": "The AI should return {\"intent\": \"upload_document\"}. (The frontend will then guide the blind user on where to physically tap the screen)."
    }
]

for intent in intents:
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 8, txt=intent["name"], ln=True)
    pdf.set_font("Arial", size=11)
    pdf.multi_cell(0, 6, txt=f"Trigger: {intent['trigger']}")
    pdf.multi_cell(0, 6, txt=f"Action: {intent['action']}")
    pdf.ln(5)

# Conclusion
pdf.set_font("Arial", 'B', 12)
pdf.cell(0, 10, txt="Why this is necessary:", ln=True)
pdf.set_font("Arial", size=11)
conc_text = "Right now, the AI only understands financial math. If you add those 4 intents to the Gemini AI router, the AI will become a true Screen Assistant. Even if a blind person speaks in Hindi or uses weird phrasing, the Gemini AI in the backend will smartly understand it, map it to the correct UI intent, and tell the frontend to refresh the screen! This creates the ultimate Voice-First experience."
pdf.multi_cell(0, 6, txt=conc_text)

# Output
pdf_path = os.path.join(r"d:\blind", "Backend_Intents_Guide.pdf")
pdf.output(pdf_path)
print(f"PDF successfully generated at {pdf_path}")

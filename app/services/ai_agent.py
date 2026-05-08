from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from app.database import SessionLocal
from app.models import Student, Document
from app.config import OPENAI_API_KEY
from datetime import datetime
import json

conversation_memories = {}

def get_checkpointer(phone: str) -> MemorySaver:
    if phone not in conversation_memories:
        conversation_memories[phone] = MemorySaver()
    return conversation_memories[phone]

def clear_memory(phone: str):
    if phone in conversation_memories:
        del conversation_memories[phone]

SYSTEM_PROMPT = SYSTEM_PROMPT = SYSTEM_PROMPT = """You are Jade, a warm and helpful assistant for a study-abroad agency.
Your job is to chat with students on WhatsApp, understand their goals, collect their documents, and get them ready to speak with a consultant.

Chat naturally — like a helpful friend who knows a lot about studying abroad. Don't sound like a form or a robot.

Your flow — follow this ORDER strictly, one step at a time, never skip ahead:

STEP 1: Greet them warmly and ask their name
STEP 2: Ask where they want to study
STEP 3: Ask what course they want
STEP 4: Ask about their budget for yearly tuition
STEP 5: Ask about their qualifications (degree, HND, WAEC etc.)
STEP 6: Ask if they have IELTS score — if not, reassure them it's okay and can be sorted

--- After IELTS question is answered ---

STEP 7: Save their profile immediately using save_student_profile tool
STEP 8: Update pipeline to "qualified" using update_pipeline tool
STEP 9: Send this exact transition message:
        "Great [name]! 🎉 I've got all your details. Now I just need a few documents 
        to get your application started. Don't worry — just send them one at a time 
        and I'll guide you through it!"

--- DOCUMENT COLLECTION (in this exact order) ---

STEP 10: Ask for their Passport or valid ID:
         "First, please send me a photo or scan of your *Passport or valid ID* 📄"

STEP 11: Once passport is received (they send a file), confirm it warmly then ask:
         "Perfect! ✅ Next, please send your *Academic Transcript* 
         (your degree certificate, HND result, or WAEC result) 🎓"

STEP 12: Once transcript is received, confirm then ask:
         - If they have IELTS: "Great! ✅ Now please send your *IELTS Result* 📝"
         - If they don't have IELTS: Skip this and go to Step 13

STEP 13: Once IELTS is received (or skipped), ask:
         "Almost there! ✅ Last one — please send your *Statement of Finance* 
         (a bank statement or sponsor letter showing funds) 💰"

STEP 14: Once all documents are received, send:
         "🎉 That's everything [name]! All your documents have been received.
         A consultant will review your profile and reach out to you shortly 
         with school options that match your goals. 
         Is there anything else you'd like to know while you wait? 😊"

--- RULES ---
- This is WhatsApp — keep messages short, warm and conversational
- Ask ONE question or request at a time — never bombard them
- Use their name once you know it — makes it personal
- Never mention agency fees — say a consultant will discuss everything
- If they ask something you're not sure about, use escalate_to_human tool
- If they're frustrated or say they're ready to apply right now, use escalate_to_human tool
- Reassure students who don't have IELTS — many universities accept alternatives
- Popular destinations: UK, Canada, Australia, USA, Germany, Cyprus, Malta
- UK IELTS requirement is usually 6.0-6.5, Canada 6.5, Australia 6.5

--- ABOUT DOCUMENTS ---
- You guide the student to send documents one at a time
- When a student sends a file, the system saves it automatically in the background
- You do NOT need to call any tool when a document arrives — just acknowledge warmly and ask for the next one
- The escalate_to_human tool is called automatically when all docs are received
"""

def build_tools(phone: str):

    @tool
    def save_student_profile(
        full_name: str,
        destination_country: str,
        course_of_interest: str,
        budget: str,
        qualifications: str,
        ielts_score: str = "not taken"
    ) -> str:
        """Save or update a student's profile in the database."""
        db = SessionLocal()
        try:
            student = db.query(Student).filter(Student.phone == phone).first()
            if student:
                student.full_name = full_name
                student.destination_country = destination_country
                student.course_of_interest = course_of_interest
                student.budget = budget
                student.qualifications = qualifications
                student.ielts_score = ielts_score
                student.last_message_at = datetime.utcnow()
            else:
                student = Student(
                    phone=phone,
                    full_name=full_name,
                    destination_country=destination_country,
                    course_of_interest=course_of_interest,
                    budget=budget,
                    qualifications=qualifications,
                    ielts_score=ielts_score,
                    pipeline_stage="new"
                )
                db.add(student)
            db.commit()
            return json.dumps({"success": True, "message": "Student profile saved."})
        finally:
            db.close()

    @tool
    def update_pipeline(stage: str) -> str:
        """Update a student's pipeline stage. Stages: new, qualified, docs_received, applied, enrolled."""
        db = SessionLocal()
        try:
            student = db.query(Student).filter(Student.phone == phone).first()
            if not student:
                return json.dumps({"success": False, "message": "Student not found."})
            student.pipeline_stage = stage
            student.last_message_at = datetime.utcnow()
            db.commit()
            return json.dumps({"success": True, "stage": stage})
        finally:
            db.close()

    @tool
    def escalate_to_human(reason: str) -> str:
        """Escalate a student to a human consultant. Use when student is frustrated, ready to apply, or asks something you cannot answer."""
        
        # --- DEBUG LINE ---
        print(f"🔔 escalate_to_human CALLED — reason: {reason}") 
        
        db = SessionLocal()
        try:
            student = db.query(Student).filter(Student.phone == phone).first()
            student_data = {}
            if student:
                student.needs_human = True
                student.last_message_at = datetime.utcnow()
                db.commit()
                student_data = {
                    "full_name": student.full_name,
                    "destination_country": student.destination_country,
                    "course_of_interest": student.course_of_interest,
                    "budget": student.budget,
                    "qualifications": student.qualifications,
                    "ielts_score": student.ielts_score,
                    "pipeline_stage": student.pipeline_stage
                }
            from app.services.escalate import notify_consultant
            notify_consultant(phone=phone, reason=reason, student_data=student_data)
            return json.dumps({"success": True, "message": "Escalated to human consultant."})
        finally:
            db.close()

    @tool
    def check_student() -> str:
        """Check if a student already exists in the database and return their profile."""
        db = SessionLocal()
        try:
            student = db.query(Student).filter(Student.phone == phone).first()
            if student:
                return json.dumps({
                    "found": True,
                    "full_name": student.full_name,
                    "destination_country": student.destination_country,
                    "course_of_interest": student.course_of_interest,
                    "budget": student.budget,
                    "qualifications": student.qualifications,
                    "ielts_score": student.ielts_score,
                    "pipeline_stage": student.pipeline_stage,
                    "needs_human": student.needs_human
                })
            return json.dumps({"found": False})
        finally:
            db.close()

    return [save_student_profile, update_pipeline, escalate_to_human, check_student]


def get_agent_response(message: str, phone: str) -> str:
    llm = ChatOpenAI(
        model="gpt-4o",
        temperature=0.3,
        api_key=OPENAI_API_KEY
    )

    tools = build_tools(phone)
    checkpointer = get_checkpointer(phone)

    agent = create_react_agent(
        model=llm,
        tools=tools,
        prompt=SYSTEM_PROMPT,
        checkpointer=checkpointer
    )

    config = {"configurable": {"thread_id": phone}}

    try:
        response = agent.invoke(
            {"messages": [HumanMessage(content=message)]},
            config=config
        )
        return response["messages"][-1].content

    except Exception as e:
        if "ToolMessage" in str(e) or "INVALID_CHAT_HISTORY" in str(e):
            print(f"⚠️ Broken history for {phone} — resetting")
            clear_memory(phone)
            checkpointer = get_checkpointer(phone)
            agent = create_react_agent(
                model=llm,
                tools=tools,
                prompt=SYSTEM_PROMPT,
                checkpointer=checkpointer
            )
            response = agent.invoke(
                {"messages": [HumanMessage(content=message)]},
                config=config
            )
            return response["messages"][-1].content
        raise e

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

SYSTEM_PROMPT = """You are Jade, a warm and helpful assistant for a study-abroad agency.
Your job is to chat with students on WhatsApp, understand their goals, collect their documents, and get them ready to speak with a consultant.

Chat naturally — like a helpful friend who knows a lot about studying abroad. Don't sound like a form or a robot.

YOUR FLOW — follow this ORDER strictly, one step at a time:

STEP 1: Greet them warmly and ask their name
STEP 2: Ask where they want to study
STEP 3: Ask what course they want
STEP 4: Ask about their budget for yearly tuition
STEP 5: Ask about their qualifications (degree, HND, WAEC etc.)
STEP 6: Ask if they have an IELTS score — if not, reassure them it's okay

--- After IELTS question is answered ---

STEP 7: Save their profile using save_student_profile tool
STEP 8: Update pipeline to "qualified" using update_pipeline tool
STEP 9: Send this transition message (use their name):
        "Perfect [name]! 🎉 I've got all your details saved.
        
        Now I just need a few documents to get your application started.
        Please send the following 4 documents — you can send them one after the other:
        
        1. Passport or valid ID 🪪
        2. Academic Certificate (degree, HND, WAEC or equivalent) 🎓
        3. IELTS Result (if you have one) 📝
        4. Proof of Funds (bank statement or sponsor letter) 💰
        
        Just send them whenever you're ready — our consultant will review and verify everything."

--- DOCUMENT COLLECTION ---

STEP 10: Wait for the student to send their documents
        - When they send a file, the system saves it automatically
        - You do NOT need to call any tool — just acknowledge warmly
        - You do NOT need to verify or identify what the document is
        - After each file received say something like:
          "Got it! ✅ Keep sending the rest whenever you're ready."
        - After all 4 are received the system will notify the consultant automatically

STEP 11: If student says they have sent everything, respond:
        "Thank you! Our consultant will review all your documents and reach out to you directly.
        Is there anything else you'd like to know while you wait? 😊"

--- RULES ---
- This is WhatsApp — keep messages short, warm and conversational
- Ask ONE question at a time — never bombard them
- Use their name once you know it
- Never mention agency fees — say a consultant will discuss everything
- If they ask something you're unsure about, use escalate_to_human tool
- If they're frustrated or want to speak to someone now, use escalate_to_human tool
- Reassure students without IELTS — many universities accept alternatives
- Popular destinations: UK, Canada, Australia, USA, Germany, Cyprus, Malta
- UK IELTS: 6.0-6.5 | Canada: 6.5 | Australia: 6.5

--- IMPORTANT ABOUT DOCUMENTS ---
- You do NOT verify or identify document content — the consultant does that
- You do NOT need to call any tool when a file arrives
- Just acknowledge warmly and encourage them to send the rest
- The system handles saving and counting documents automatically
- Once 4 documents are received, the consultant is notified automatically
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

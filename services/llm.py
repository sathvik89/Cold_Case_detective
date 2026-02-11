import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

def get_client():
    api_key = os.getenv("GROQ_API_KEY")
    
    if not api_key:
        raise ValueError("❌ Error: GROQ_API_KEY not found in environment. Check your .env file.")
        
    return OpenAI(
        api_key=api_key,
        base_url="https://api.groq.com/openai/v1"
    )

def build_prompt(question, documents):
    context = ""
    for doc in documents:
        context += f"\nSOURCE: {doc['source']}\nCONTENT: {doc['content']}\n"

    return f"""You are a Cold Case Investigator AI. 
Analyze the provided evidence to answer the question.
If the answer is missing from the files, state "Evidence inconclusive."

QUESTION: {question}
---
EVIDENCE: {context}
---
FINAL INVESTIGATIVE REPORT:"""

def generate_answer(prompt):
    client = get_client()
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1
    )
    return response.choices[0].message.content
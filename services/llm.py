import os

from dotenv import load_dotenv

import providers

load_dotenv()


def build_prompt(question, documents):
    context = ""
    for doc in documents:
        context += f"\nSOURCE: {doc['source']}\nCONTENT: {doc['content']}\n"

    return f"""You are a Cold Case Investigator AI. 
Analyze the provided evidence to answer the question.
If the answer is missing from the files, state "Evidence inconclusive."
Write the report in plain text. Do not use markdown or asterisks for emphasis -
the report is shown as plain text and the markup would be visible.

QUESTION: {question}
---
EVIDENCE: {context}
---
FINAL INVESTIGATIVE REPORT:"""


def generate_answer(prompt, provider=None, api_key=None, model=None):
    """
    Send the prompt to whichever provider is configured. The web UI passes the
    provider and key in explicitly; the terminal version falls back to
    AI_PROVIDER / AI_MODEL and the keys in .env.
    """
    provider, key, model = providers.resolve(
        provider or os.getenv("AI_PROVIDER"),
        api_key,
        model or os.getenv("AI_MODEL"),
    )
    completion = providers.client_for(provider, key).chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
    )
    return completion.choices[0].message.content or ""

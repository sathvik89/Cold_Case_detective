import os
import sys
from services.loader import load_documents
from services.embedder import embed_documents, embed_query
from services.retriever import Retriever
from services.llm import build_prompt, generate_answer
#path sttting up
DATA_DIR = "./data"

def run_investigation():
    print("🕵️  Detective AI: Loading and indexing evidence...")
    
    if not os.path.exists(DATA_DIR):
        print(f"❌ Error: {DATA_DIR} directory not found.")
        return

    raw_docs = load_documents(DATA_DIR)
    if not raw_docs:
        print("⚠️  No evidence files found in the data folder. Add some .txt files!")
        return

    embedded_docs = embed_documents(raw_docs)
    
    retriever = Retriever(embedded_docs)
    print("✅ Evidence indexed. Ready for questioning.")
    print("(Type 'exit' or 'quit' to close the case)\n")

#input from the terminal
    while True:

        user_query = input("🔍 Enter your question: ")
        if user_query.lower() in ['exit', 'quit']:
            print("👋 Closing the case file. Goodbye!")
            break
        
        if not user_query.strip():
            continue

        print("🤖 AI is analyzing evidence...")
        
        try:
            # retrieving
            query_vector = embed_query(user_query)
            relevant_docs = retriever.search(query_vector, top_k=2)#top k chunks we retrive from the data 
            
            #giving the LLM question and relevant chunks and generating the answer from it . 
            final_prompt = build_prompt(user_query, relevant_docs)
            answer = generate_answer(final_prompt)
            
            print("\n--- FINAL REPORT ---")
            print(answer)
            print("-" * 20 + "\n")
            
        except Exception as e:
            print(f"❌ An error occurred: {e}")

if __name__ == "__main__":
    run_investigation()
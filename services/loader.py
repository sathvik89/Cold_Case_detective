import os

def load_documents(data_dir):
    """
    Scans the data directory for .txt files and returns a list of 
    dictionaries containing the file content and the filename.
    """
    documents = []
    
    
    if not os.path.exists(data_dir):
        print(f"⚠️  Warning: Folder '{data_dir}' not found. Creating it now...")
        os.makedirs(data_dir)
        return documents

    for filename in os.listdir(data_dir):
        if filename.endswith(".txt"):
            file_path = os.path.join(data_dir, filename)

            with open(file_path, "r", encoding="utf-8") as file:
                content = file.read().strip()
                
                if content: # add if the file not empty
                    documents.append({
                        "content": content,
                        "source": filename
                    })
    
    print(f"✅ Loaded {len(documents)} evidence files from {data_dir}.")
    return documents
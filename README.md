# Cold Case Investigator

A retrieval-augmented investigator over a folder of case files. Ask a question,
it finds the most relevant evidence and writes a report from it, citing the
files it used and how closely each one matched.

Repository: https://github.com/sathvik89/Cold_Case_detective

There are two ways to use it: a web UI (`app.py`) where you can add and remove
evidence from the browser, and a terminal version (`main.py`).

## Setup

```bash
git clone https://github.com/sathvik89/Cold_Case_detective.git
cd Cold_Case_detective

python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

## Running it

```bash
uvicorn app:app --reload
```

Open http://localhost:8000, click Settings, choose a provider and paste your
API key. The key is stored in your browser only.

Terminal version:

```bash
cp .env.example .env            # put a key in it first
python main.py
```

The first question takes a few extra seconds - the embedding model is about
90 MB and downloads once, then it is cached.

## Providers

| Provider | Get a key | Default model |
|---|---|---|
| Groq | https://console.groq.com/keys | `llama-3.3-70b-versatile` |
| Google Gemini | https://aistudio.google.com/apikey | `gemini-flash-latest` |
| OpenAI | https://platform.openai.com/api-keys | `gpt-4o-mini` |

All three speak the same API format, so switching is just a different base URL
and key. The Settings panel can also list the models your key can actually use.

For the terminal version, set one of `GROQ_API_KEY`, `GEMINI_API_KEY` or
`OPENAI_API_KEY` in `.env`, and optionally `AI_PROVIDER` and `AI_MODEL`.

## Evidence

Evidence is any `.txt` file in `data/`. Three sample files ship with the repo.
In the web UI you can drop new files in or remove them, and the index rebuilds
on the next question. In the terminal version, put files in `data/` by hand.

## How it works

Each file is embedded with MiniLM and indexed in FAISS using inner product on
normalised vectors, which is cosine similarity. A question is embedded the same
way, the two closest files are retrieved, and the model writes the report from
them. If the evidence does not cover the question it is told to say so rather
than guess.

Embedding happens locally, so only the retrieved evidence is ever sent to the
provider.

## Layout

```
app.py                  FastAPI server: /api/evidence, /api/ask, /api/providers
providers.py            provider config and client setup
main.py                 terminal version
services/loader.py      reads the .txt files
services/embedder.py    text to vectors
services/retriever.py   FAISS index and search
services/llm.py         prompt building and the provider call
data/                   the evidence files
static/                 the web UI (no build step, plain HTML/CSS/JS)
```

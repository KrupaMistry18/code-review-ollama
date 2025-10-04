# 🧠 GenAI Code Review Assistant (Powered by Ollama + LangChain + FastAPI + Streamlit)

A **local AI-powered code review tool** that analyzes diffs or source code for **security, performance, and style issues** — all running **entirely offline** via [Ollama](https://ollama.com).
No OpenAI API key required, no data leaves your machine. 🚀

---

## ⚙️ Features

* 🔍 **AI Code Reviews** — Analyze code or Git diffs for potential improvements
* 🧠 **Local LLMs via Ollama** — Privacy-preserving, free, and fast
* 🧩 **Modular Design** — FastAPI backend + Streamlit frontend
* 🪶 **Configurable Focus Areas** — Security, performance, or style
* 📦 **JSON API** — Easily integrate with your CI or dev tools
* 🧱 **Ready for Expansion** — Add GitHub PR support or auto-fix routes later

---

## 🏗️ Project Structure

```
code-review-ollama/
├── backend/
│   └── app.py                # FastAPI backend (Ollama-powered reviewer)
├── ui/
│   └── streamlit_app.py      # Streamlit front-end
├── demo/
│   └── sample_diff.patch     # Example diff for testing
├── .env.example              # Template for environment variables
├── requirements.txt
└── README.md
```

---

## 🧰 Prerequisites

* **Python 3.9+**
* **[Ollama](https://ollama.com/download)** (installed locally)
* A pulled LLM model (choose one):

  ```bash
  ollama pull phi3:3.8b
  # or: ollama pull mistral:7b-instruct
  # or: ollama pull llama3.1:8b-instruct
  ```

---

## ⚡ Setup

### 1. Clone the repo

```bash
git clone https://github.com/<your-username>/code-review-ollama.git
cd code-review-ollama
```

### 2. Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate   # macOS/Linux
# or
.venv\Scripts\activate      # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Copy the example file and update it if needed:

```bash
cp .env.example .env
```

Default contents:

```ini
USE_OLLAMA=true
OLLAMA_MODEL=phi3:3.8b
OLLAMA_BASE_URL=http://localhost:11434
```

### 5. Start Ollama

```bash
brew services start ollama   # macOS (Homebrew)
# or
ollama serve
```

### 6. Start the backend (FastAPI)

```bash
uvicorn backend.app:app --reload --log-level debug
```

Backend runs at:
👉 **[http://127.0.0.1:8000](http://127.0.0.1:8000)**

Test it:

```bash
curl http://127.0.0.1:8000/health
```

### 7. Run the Streamlit UI

In a new terminal:

```bash
streamlit run ui/streamlit_app.py
```

Frontend runs at:
👉 **[http://localhost:8501](http://localhost:8501)**

---

## 💡 Usage

### ▶️ From the Web UI

1. Paste a code snippet or Git diff.
2. Select focus areas (Security, Performance, Style).
3. Click **Review**.
4. Get a summary + actionable findings instantly.

### ▶️ From the API

```bash
curl -X POST http://127.0.0.1:8000/review \
  -H "Content-Type: application/json" \
  -d '{"text":"def add(a,b): return a+b","focus":["security","performance","style"]}'
```

Example response:

```json
{
  "summary": "- The function lacks input validation.\n- No error handling for non-numeric inputs.",
  "findings": [
    {"category": "security", "severity": "High", "message": "No input validation for user inputs."},
    {"category": "style", "severity": "Low", "message": "Missing docstring for function."}
  ]
}
```

---

## 🧩 Sample Diff (demo)

```
@@ -1,2 +1,5 @@
- total = a+b
+ # handle None and log
+ total = (a or 0) + (b or 0)
+ if total > 1000:
+     print("Large total:", total)  # TODO: use logger
```

---

## 🧪 Run Both Backend + UI in One Terminal

You can start both together:

```bash
(uvicorn backend.app:app --reload --log-level debug &) && streamlit run ui/streamlit_app.py
```

Or, if you only have one terminal:

* Start backend in background:

  ```bash
  uvicorn backend.app:app --reload --log-level debug &
  ```
* Then run Streamlit normally.

---

## 🚀 Future Enhancements

* 🛠️ `/suggest` endpoint → auto-generate code fixes
* 🔗 GitHub PR integration (fetch + annotate diffs)
* 🧪 Unit tests and CI workflow
* 🐳 Docker support for one-command setup

---

## 👤 Author

**Krupa Mistry**


Feel free to connect or contribute!
📧 [[krupamistry08@gmail.com](mailto:krupamistry08@gmail.com)]
🔗 [LinkedIn](www.linkedin.com/in/krupamistryy)

---

### ⭐ If you found this helpful — consider giving the repo a star!

---

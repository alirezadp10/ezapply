# 🤖 LinkedIn Job Auto Applier Bot (WIP)

An intelligent **LinkedIn automation bot** that automatically searches for jobs and applies using the **Easy Apply** feature.  
It uses **Selenium** for browser automation and **DeepInfra’s AI models** to intelligently answer application form questions.

---

## 🚀 Features

- 🔐 Automatic LinkedIn login
- 🔍 Job search by **keywords, country, and work type**
- 🧠 Smart form completion using **AI (DeepInfra + LLaMA models)**
- 💾 Saves application results in **SQLite**
- 🕹️ Headless mode supported (no GUI browser)
- ⚡ Fast and configurable search frequency


---

## ⚙️ Environment Configuration (`.env`)

Create a `.env` file in the root directory and fill in your own values:

```env
# Database
SQLITE_DB_PATH=sqlite:///./data.db

# Browser
HEADLESS=True
USER_DATA_DIR=/tmp/chrome-user-data
DELAY_TIME=5

# LinkedIn credentials
LINKEDIN_USERNAME=your_email@example.com
LINKEDIN_PASSWORD=your_password

# Job search configuration
USER_INFORMATION="Name: John Doe, Skills: Python, Django, FastAPI, Remote-friendly"
WORK_TYPE=remote
KEYWORDS=python,backend,developer
COUNTRIES=US,CA
JOB_SEARCH_TIME_WINDOW=21600   # 6 hours

# DeepInfra API
DEEPINFRA_API_URL=https://api.deepinfra.com/v1/openai/chat/completions
DEEPINFRA_MODEL_NAME=meta-llama/Meta-Llama-3-8B-Instruct
DEEPINFRA_API_KEY=your_deepinfra_api_key
```

# 📦 Installation, Setup & Workflow

### 🧰 Step 1: Clone the repository
```bash
git clone https://github.com/alirezadp10/ezapply
cd ezapply
```

### 🧱 Step 2: Create and activate a virtual environment (recommended)
```bash
python -m venv .venv
```

##### On macOS/Linux:
```bash
source .venv/bin/activate
```

##### On Windows (PowerShell):
```bash
.venv\Scripts\activate
```

### 🧩 Step 3: Install dependencies
```bash
pip install -r requirements.txt
```

### ⚙️ Step 4: Configure environment
```bash
python main.py
```

## 🧠 How It Works

- Logs in to your LinkedIn account (if not already logged in)

- Searches for job listings based on your defined keywords, countries, and work type

- Identifies job postings with the “Easy Apply” button

- Opens each posting and starts the application process:

- Extracts all unfilled fields from the application modal

- Sends the form questions + your profile data (USER_INFORMATION) to DeepInfra AI

- Receives AI-generated answers and fills them automatically

- Submits the application and logs the result (success or failure)

- Stores all application data in an SQLite database for tracking

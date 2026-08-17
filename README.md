# 🌿 Mood Mentor – Employee Wellness Management Analytics

## 📌 Project Overview

Mood Mentor is an AI-powered Employee Wellness Management System designed to help employees monitor and improve their mental well-being. The platform provides mood tracking, journal analysis, emotion detection, wellness insights, and an AI-powered chatbot for emotional wellness support.

The system also provides secure user authentication and a wellness dashboard for viewing mood history and progress.

---

## ✨ Features

* 🔐 User Authentication – Sign Up, Login, Forgot Password
* 📖 Daily Journal Entry
* 😊 AI-Based Mood & Sentiment Analysis
* 🧠 NLP-Based Emotion Detection
* 📊 Employee Wellness Dashboard
* 🤖 AI Wellness Chatbot
* 📂 Past Journal Entries
* 📈 Wellness Progress Charts
* 🎭 Facial Emotion Detection
* 🌐 Multilingual Text Analysis
* 👤 Employee & Manager Roles
* 📊 Manager Wellness Analytics
* 📄 Mood History Export

---

## 🛠️ Technologies Used

* 🐍 Python
* 🎨 Streamlit
* ⚡ FastAPI
* 🐘 PostgreSQL (Neon DB)
* 🔐 JWT Authentication
* 🔑 bcrypt
* 🧠 NLP
* 🤖 Transformers / PyTorch
* 💬 Groq API / Qwen
* 📷 OpenCV
* 🎭 DeepFace
* 🐼 Pandas
* 📊 Matplotlib
* 🧹 Bleach
* 🧪 Pytest
* 🐳 Docker
* 🌐 ngrok
* ☁️ Google Colab

---

## 🏗️ Project Architecture

```text
┌─────────────────────┐
│  Streamlit Frontend │
│       app.py        │
└──────────┬──────────┘
           │
           │ JWT Authenticated
           ▼
┌─────────────────────┐
│   FastAPI Backend   │
│     backend.py      │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  PostgreSQL / Neon  │
│      Database       │
└─────────────────────┘
           │
           ▼
┌─────────────────────┐
│    NLP / AI / ML    │
│ Sentiment & Emotion │
│   LLM Suggestions   │
└─────────────────────┘
```

---

## 📂 Project Modules

* `app.py` – Streamlit frontend and application interface
* `backend.py` – FastAPI backend and API endpoints
* `db.py` – PostgreSQL database connection and schema
* `auth.py` – JWT authentication and OTP verification
* `security.py` – Input sanitization and security functions
* `email_utils.py` – Email OTP functionality
* `nlp_pipeline.py` – Language detection, translation, sentiment and emotion analysis
* `recommendations.py` – Wellness recommendations
* `test_moodmentor.py` – Unit tests
* `evaluate_model.py` – Emotion model evaluation

---

## 📸 Screenshots

Add application screenshots inside the `screenshots` folder.

### 🏠 Home Page

```text
screenshots/home.png
```

### 🔐 Login Page

```text
screenshots/login.png
```

### 📝 Journal Page

```text
screenshots/journal.png
```

### 📊 Wellness Dashboard

```text
screenshots/dashboard.png
```

### 🤖 Wellness Chat

```text
screenshots/chat.png
```

### 🎭 Face Emotion Detection

```text
screenshots/face_scanner.png
```

### 📈 Manager Analytics Dashboard

```text
screenshots/analytics.png
```

---

## 🚀 Running the Application

### Google Colab

1. Open the project notebook in Google Colab.
2. Add the required secrets.
3. Run the installation and configuration cells.
4. Start the FastAPI backend.
5. Start the Streamlit application.
6. Open the generated ngrok URL.

### Required Environment Variables

```text
DB_HOST
DB_PORT
DB_NAME
DB_USER
DB_PASSWORD

JWT_SECRET

SMTP_EMAIL
SMTP_APP_PASSWORD

NGROK_AUTHTOKEN

GROQ_API_KEY
```

---

## 🧪 Running Tests

Run the following command:

```bash
pytest test_moodmentor.py
```

The tests cover areas such as questionnaire scoring, recommendations, password hashing, and input sanitization.

---

## 🔐 Security

* JWT-based authentication
* bcrypt password hashing
* Email OTP verification
* Input sanitization
* File upload validation
* Role-based access control
* PostgreSQL SSL connection
* Environment-based secrets management
* Protected backend API endpoint
---

## 📜 License

This project is licensed under the **MIT License**.

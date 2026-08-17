%%writefile app.py
"""
MoodMentor - Emotional Wellness Platform
Single-file Streamlit app merging:
  - MoodMentor's UI/branding (hero, feature cards, sidebar, dashboard)
  - A real working auth flow (Register -> OTP verify -> Login -> Dashboard -> Logout)
    implemented in-memory (no external db/email service required), so it
    actually runs end-to-end out of the box.
"""

import re
import random
import streamlit as st

# ==================================================
# PAGE CONFIGURATION
# ==================================================

st.set_page_config(
    page_title="MoodMentor",
    page_icon="😊",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ==================================================
# SESSION STATE
# ==================================================

defaults = {
    "logged_in": False,
    "current_user": None,          # email of logged-in user
    "users": {},                   # email -> {password, verified}
    "pending_email": None,         # email awaiting OTP verification
    "pending_otp": None,           # the OTP code we generated
    "mood_history": [],            # list of {"text":..., "sentiment":...}
}
for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val


# ==================================================
# HELPERS (validation + tiny "auth" logic)
# ==================================================

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def is_valid_email(email: str) -> bool:
    return bool(EMAIL_RE.match(email or ""))


def is_valid_password(pw: str):
    if len(pw) < 8:
        return False, "Password must be at least 8 characters."
    if not re.search(r"[A-Za-z]", pw) or not re.search(r"[0-9]", pw):
        return False, "Password must contain both letters and numbers."
    return True, ""


def generate_otp() -> str:
    return f"{random.randint(0, 999999):06d}"


def fake_sentiment(text: str) -> str:
    text_l = text.lower()
    positive_words = ["happy", "good", "great", "grateful", "excited", "calm", "proud", "love"]
    negative_words = ["sad", "angry", "anxious", "stressed", "tired", "worried", "upset", "bad"]
    score = sum(w in text_l for w in positive_words) - sum(w in text_l for w in negative_words)
    if score > 0:
        return "😊 Positive"
    elif score < 0:
        return "😔 Negative"
    return "😐 Neutral"


# ==================================================
# CUSTOM CSS
# ==================================================

st.markdown("""
<style>

@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Poppins', sans-serif;
}

.stApp {
    background:
        radial-gradient(circle at 10% 10%, rgba(124, 58, 237, 0.20), transparent 30%),
        radial-gradient(circle at 90% 20%, rgba(236, 72, 153, 0.18), transparent 30%),
        radial-gradient(circle at 50% 90%, rgba(14, 165, 233, 0.16), transparent 35%),
        linear-gradient(135deg, #f8f7ff 0%, #fff7fb 50%, #f0f9ff 100%);
}

.block-container {
    padding-top: 2rem;
    padding-bottom: 4rem;
    max-width: 1150px;
}

[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #4c1d95 0%, #6d28d9 45%, #7c3aed 100%);
}
[data-testid="stSidebar"] * { color: white; }
[data-testid="stSidebar"] label { font-weight: 600; }

.hero-container {
    padding: 45px;
    border-radius: 28px;
    background: linear-gradient(135deg, #6d28d9, #9333ea, #ec4899);
    box-shadow: 0px 20px 50px rgba(109, 40, 217, 0.25);
    text-align: center;
    color: white;
    margin-bottom: 30px;
}
.hero-title { font-size: 50px; font-weight: 700; margin-bottom: 5px; }
.hero-subtitle { font-size: 18px; opacity: 0.92; }

.page-title { font-size: 34px; font-weight: 700; color: #4c1d95; margin-bottom: 8px; }
.page-description { color: #64748b; margin-bottom: 25px; }

.glass-card {
    background: rgba(255, 255, 255, 0.78);
    backdrop-filter: blur(14px);
    border: 1px solid rgba(255,255,255,0.75);
    border-radius: 24px;
    padding: 30px;
    box-shadow: 0px 15px 45px rgba(76, 29, 149, 0.10);
    margin-bottom: 25px;
}

.feature-card {
    background: white;
    border-radius: 22px;
    padding: 28px;
    min-height: 210px;
    border: 1px solid #ede9fe;
    box-shadow: 0px 12px 35px rgba(76, 29, 149, 0.08);
    transition: transform 0.3s ease, box-shadow 0.3s ease;
}
.feature-card:hover {
    transform: translateY(-6px);
    box-shadow: 0px 18px 45px rgba(109, 40, 217, 0.16);
}
.feature-icon { font-size: 40px; margin-bottom: 12px; }
.feature-title { font-size: 20px; font-weight: 700; color: #4c1d95; }
.feature-description { color: #64748b; font-size: 14px; margin-top: 10px; }

.stTextInput input, .stTextArea textarea {
    border-radius: 12px;
    border: 1px solid #ddd6fe;
    padding: 12px;
}
.stTextInput input:focus, .stTextArea textarea:focus {
    border-color: #7c3aed;
    box-shadow: 0px 0px 0px 2px rgba(124,58,237,0.15);
}

.stButton > button {
    width: 100%;
    border: none;
    border-radius: 12px;
    padding: 12px 20px;
    font-weight: 600;
    color: white;
    background: linear-gradient(90deg, #7c3aed, #9333ea, #ec4899);
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.stButton > button:hover {
    color: white;
    transform: translateY(-2px);
    box-shadow: 0px 10px 25px rgba(124,58,237,0.30);
}

[data-testid="stMetric"] {
    background: linear-gradient(135deg, #ffffff, #faf5ff);
    border: 1px solid #ede9fe;
    border-radius: 18px;
    padding: 22px;
    box-shadow: 0px 10px 30px rgba(76,29,149,0.08);
}

[data-testid="stAlert"] { border-radius: 14px; }

#MainMenu { visibility: hidden; }
footer { visibility: hidden; }

</style>
""", unsafe_allow_html=True)


# ==================================================
# SIDEBAR
# ==================================================

st.sidebar.markdown("""
<div style="text-align:center; padding:20px 5px 30px 5px;">
<div style="font-size:55px;">😊</div>
<div style="font-size:25px; font-weight:700;">MoodMentor</div>
<div style="font-size:12px; opacity:0.8;">Emotional Wellness Platform</div>
</div>
""", unsafe_allow_html=True)

menu_options = ["Home", "Register", "Login", "Dashboard"]
if st.session_state.logged_in:
    st.sidebar.success(f"✅ Logged in as {st.session_state.current_user}")
    if st.sidebar.button("🚪 Log Out", key="sidebar_logout_button"):
        st.session_state.logged_in = False
        st.session_state.current_user = None
        st.session_state.main_menu = "Home"
        st.rerun()

choice = st.sidebar.selectbox("Explore MoodMentor", menu_options, key="main_menu")

st.sidebar.markdown("---")
st.sidebar.caption("🌿 Understand your emotions. Track your wellness. Feel better.")


# ==================================================
# HOME PAGE
# ==================================================

if choice == "Home":

    st.markdown("""
<div class="hero-container">
<div class="hero-title">😊 MoodMentor</div>
<div class="hero-subtitle">Your AI-Powered Companion for Emotional Wellness</div>
</div>
""", unsafe_allow_html=True)

    st.markdown("""
<div style="text-align:center; font-size:27px; font-weight:700; color:#4c1d95; margin-bottom:25px;">
Your Wellness Journey Starts Here ✨
</div>
""", unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("""
<div class="feature-card">
<div class="feature-icon">🧠</div>
<div class="feature-title">AI Mood Analysis</div>
<div class="feature-description">Share how you're feeling and receive instant emotional sentiment insights.</div>
</div>
""", unsafe_allow_html=True)
    with col2:
        st.markdown("""
<div class="feature-card">
<div class="feature-icon">📊</div>
<div class="feature-title">Track Progress</div>
<div class="feature-description">View your emotional patterns and understand your wellness journey.</div>
</div>
""", unsafe_allow_html=True)
    with col3:
        st.markdown("""
<div class="feature-card">
<div class="feature-icon">🌿</div>
<div class="feature-title">Improve Wellness</div>
<div class="feature-description">Build healthier emotional habits through self-awareness.</div>
</div>
""", unsafe_allow_html=True)


# ==================================================
# REGISTER
# ==================================================

elif choice == "Register":

    st.markdown('<div class="page-title">✨ Create Your Account</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-description">Start your emotional wellness journey today.</div>', unsafe_allow_html=True)

    left, center, right = st.columns([1, 2, 1])

    with center:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)

        email = st.text_input("📧 Email Address", placeholder="Enter your email", key="register_email")
        password = st.text_input("🔒 Password", type="password", placeholder="Create your password", key="register_password")
        confirm_password = st.text_input("🔐 Confirm Password", type="password", placeholder="Confirm your password", key="register_confirm_password")

        if st.button("📨 Send OTP", key="register_send_otp"):
            if not email or not is_valid_email(email):
                st.error("Please enter a valid email.")
            elif email in st.session_state.users and st.session_state.users[email]["verified"]:
                st.error("An account with this email already exists. Please log in.")
            else:
                ok_pw, pw_msg = is_valid_password(password)
                if not ok_pw:
                    st.error(pw_msg)
                elif password != confirm_password:
                    st.error("Passwords do not match.")
                else:
                    st.session_state.users[email] = {"password": password, "verified": False}
                    otp = generate_otp()
                    st.session_state.pending_email = email
                    st.session_state.pending_otp = otp
                    st.success("OTP Sent Successfully!")
                    st.info(f"Demo mode (no email server configured) — your OTP is: **{otp}**")

        otp_input = st.text_input("🔢 Enter OTP", placeholder="Enter verification code", key="register_otp")

        if st.button("✅ Verify OTP", key="register_verify_otp"):
            if not st.session_state.pending_email:
                st.error("Please request an OTP first.")
            elif not otp_input:
                st.error("Please enter OTP.")
            elif otp_input.strip() != st.session_state.pending_otp:
                st.error("Invalid or expired OTP.")
            else:
                st.session_state.users[st.session_state.pending_email]["verified"] = True
                st.success("Email Verified Successfully! You can now log in.")
                st.session_state.pending_email = None
                st.session_state.pending_otp = None

        st.markdown('</div>', unsafe_allow_html=True)


# ==================================================
# LOGIN
# ==================================================

elif choice == "Login":

    st.markdown('<div class="page-title">👋 Welcome Back</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-description">Login to continue your wellness journey.</div>', unsafe_allow_html=True)

    left, center, right = st.columns([1, 2, 1])

    with center:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)

        login_email = st.text_input("📧 Email Address", placeholder="Enter your email", key="login_email")
        login_password = st.text_input("🔒 Password", type="password", placeholder="Enter your password", key="login_password")

        if st.button("🚀 Login", key="login_button"):
            if not login_email or not login_password:
                st.error("Please enter both email and password.")
            else:
                user = st.session_state.users.get(login_email)
                if not user:
                    st.error("No account found with this email. Please register first.")
                elif not user["verified"]:
                    st.warning("This account is not verified yet. Please verify it via the Register page.")
                elif user["password"] != login_password:
                    st.error("Invalid email or password.")
                else:
                    st.session_state.logged_in = True
                    st.session_state.current_user = login_email
                    st.success("Login Successful! 🎉")
                    st.info("Open Dashboard from the sidebar.")

        st.markdown('</div>', unsafe_allow_html=True)


# ==================================================
# DASHBOARD
# ==================================================

elif choice == "Dashboard":

    if st.session_state.logged_in:

        st.markdown('<div class="page-title">📊 Wellness Dashboard</div>', unsafe_allow_html=True)
        st.markdown('<div class="page-description">Understand your emotions and monitor your wellness journey.</div>', unsafe_allow_html=True)

        dashboard_menu = st.sidebar.radio(
            "Dashboard Navigation",
            ["Home", "Analyze", "History", "Profile", "Logout"],
            key="dashboard_navigation"
        )

        # ---- Dashboard Home ----
        if dashboard_menu == "Home":
            st.success("👋 Welcome to MoodMentor!")

            col1, col2, col3 = st.columns(3)
            with col1:
                last_mood = st.session_state.mood_history[-1]["sentiment"] if st.session_state.mood_history else "—"
                st.metric("😊 Current Mood", last_mood)
            with col2:
                st.metric("💚 Total Entries", len(st.session_state.mood_history))
            with col3:
                st.metric("🔥 Wellness Streak", f"{max(len(st.session_state.mood_history), 1)} Day(s)")

            st.markdown("### 🌱 Today's Wellness Tip")
            st.info("Take a few minutes today to pause, reflect on your emotions, and write down one thing you're grateful for.")

        # ---- Analyze ----
        elif dashboard_menu == "Analyze":
            st.markdown("## 🧠 Analyze Your Mood")
            st.write("Share how you are feeling today.")

            mood_text = st.text_area(
                "Your thoughts",
                placeholder="Example: Today I feel happy because I completed my project...",
                height=180,
                key="mood_analysis_text"
            )

            if st.button("✨ Analyze My Mood", key="analyze_mood_button"):
                if mood_text.strip():
                    sentiment = fake_sentiment(mood_text)
                    st.session_state.mood_history.append({"text": mood_text, "sentiment": sentiment})
                    st.success("Mood Analyzed Successfully!")
                    st.metric("Detected Sentiment", sentiment)
                else:
                    st.warning("Please enter how you are feeling.")

        # ---- History ----
        elif dashboard_menu == "History":
            st.markdown("## 📜 Mood History")
            if not st.session_state.mood_history:
                st.info("Your previous mood analyses will appear here.")
            else:
                for i, entry in enumerate(reversed(st.session_state.mood_history), 1):
                    st.markdown(f"**{i}. {entry['sentiment']}** — {entry['text']}")

        # ---- Profile ----
        elif dashboard_menu == "Profile":
            st.markdown("## 👤 My Profile")
            st.write(f"📧 Email: {st.session_state.current_user}")
            st.write("🌿 Wellness Journey: Active")
            last_mood = st.session_state.mood_history[-1]["sentiment"] if st.session_state.mood_history else "Not tracked yet"
            st.write(f"😊 Current Mood: {last_mood}")

        # ---- Logout ----
        elif dashboard_menu == "Logout":
            st.session_state.logged_in = False
            st.session_state.current_user = None
            st.success("Logged Out Successfully 👋")
            st.rerun()

    else:
        st.markdown('<div class="page-title">🔒 Dashboard Locked</div>', unsafe_allow_html=True)
        st.warning("Please login first to access your MoodMentor dashboard.")
        st.info("Select Login from the sidebar.")

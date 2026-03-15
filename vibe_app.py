import streamlit as st
import google.generativeai as genai
from PIL import Image
import re

# --- 1. CONFIGURATION ---
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

st.set_page_config(page_title="VIBE.CAL NUTRITION", layout="centered")
# --- HIDE STREAMLIT BRANDING ---
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

# --- 2. AUTOMATIC MODEL FINDER ---
# This looks into your account and finds the right name automatically
@st.cache_resource
def get_working_model():
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                # Prioritize Flash for speed, but take whatever works
                if 'flash' in m.name:
                    return m.name
        return "gemini-1.5-flash" # Fallback
    except:
        return "gemini-1.5-flash"

WORKING_MODEL = get_working_model()

# --- 3. APP MEMORY ---
if 'total_consumed' not in st.session_state:
    st.session_state.total_consumed = 0
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

# --- 4. SIDEBAR: USER PROFILE & GOALS ---
with st.sidebar:
    st.header("👤 Your Profile")
    age = st.number_input("Age", min_value=10, max_value=100, value=25)
    height = st.number_input("Height (cm)", min_value=100, max_value=250, value=170)
    weight = st.number_input("Current Weight (kg)", min_value=30, max_value=300, value=70)
    
    st.divider()
    
    st.header("Goals")
    weight_goal = st.selectbox("I want to:", ["Lose Weight", "Maintain", "Gain Muscle"])
    speed = st.select_slider("Speed (kg per week):", options=[0.25, 0.5, 0.75, 1.0])
    
    base_calories = (10 * weight) + (6.25 * height) - (5 * age) + 5
    if weight_goal == "Lose Weight":
        daily_goal = base_calories - (speed * 500)
    elif weight_goal == "Gain Muscle":
        daily_goal = base_calories + 300
    else:
        daily_goal = base_calories

    if st.button("Reset Daily Progress"):
        st.session_state.total_consumed = 0
        st.session_state.chat_history = []
        st.rerun()

# --- 5. THE CIRCULAR DASHBOARD ---
st.title("VIBE.CAL NUTRITION")

remaining = daily_goal - st.session_state.total_consumed
progress_percentage = min(st.session_state.total_consumed / daily_goal, 1.0)

st.markdown(f"""
    <div style="display: flex; justify-content: center; align-items: center; flex-direction: column;">
        <div style="position: relative; width: 200px; height: 200px; border-radius: 50%; 
                    background: conic-gradient(#4CAF50 {progress_percentage*360}deg, #333 0deg);
                    display: flex; justify-content: center; align-items: center;">
            <div style="position: absolute; width: 170px; height: 170px; background-color: #0e1117; 
                        border-radius: 50%; display: flex; justify-content: center; align-items: center; flex-direction: column;">
                <h2 style="margin: 0; color: white;">{int(remaining)}</h2>
                <p style="margin: 0; color: #888;">kcal left</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

st.write("") 
col1, col2 = st.columns(2)
with col1:
    st.metric("Daily Target", f"{int(daily_goal)} kcal")
with col2:
    st.metric("Consumed", f"{int(st.session_state.total_consumed)} kcal")

st.divider()

# --- 6. AI MEAL SCANNER ---
st.subheader("AI Meal Scanner")
uploaded_file = st.file_uploader("Upload any photo", type=["jpg", "png", "jpeg", "webp", "heic", "tiff"])

if uploaded_file:
    image = Image.open(uploaded_file)
    st.image(image, caption="Meal Preview", use_container_width=True)
    
    if st.button("Analyze & Subtract Calories"):
        model = genai.GenerativeModel(WORKING_MODEL) 
        prompt = "Analyze this image. 1. List every ingredient & its calories. 2. TOTAL: [number] calories."
        
        with st.spinner("Analyzing ingredients..."):
            try:
                response = model.generate_content([prompt, image])
                st.info(response.text)
                
                calories_found = re.findall(r'TOTAL: (\d+)', response.text)
                if calories_found:
                    meal_cals = int(calories_found[0])
                    st.session_state.total_consumed += meal_cals
                    st.success(f"Added {meal_cals} kcal to your total!")
                    st.rerun()
            except Exception as e:
                st.error(f"Scanner Error: {e}")

st.divider()

# --- 7. NUTRITION AI CHATBOT ---
st.subheader("Health & Weight Loss Coach")
for message in st.session_state.chat_history:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if user_query := st.chat_input("Ask me anything about your diet..."):
    st.session_state.chat_history.append({"role": "user", "content": user_query})
    with st.chat_message("user"):
        st.markdown(user_query)

    model = genai.GenerativeModel(WORKING_MODEL)
    chat_prompt = f"You are a professional nutrition coach. Answer this: {user_query}"
    
    with st.chat_message("assistant"):
        try:
            response = model.generate_content(chat_prompt)
            st.markdown(response.text)
            st.session_state.chat_history.append({"role": "assistant", "content": response.text})
        except Exception as e:
            st.error(f"Chat Error: {e}")

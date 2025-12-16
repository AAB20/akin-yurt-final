import streamlit as st
import requests
import json
import re
from supabase import create_client, Client

# =========================================================
# 1. إعدادات الصفحة واللغات
# =========================================================

st.set_page_config(page_title="Akın Yurt AI (DeepSeek)", page_icon="🧠", layout="centered")

if "language" not in st.session_state:
    st.session_state.language = "TR"

TEXTS = {
    "AR": {
        "dir": "rtl", "align": "right",
        "title": "ذكاء تركمان إيلي (الجيل العميق)",
        "subtitle": "بوابة المعرفة الموثقة - AWS Cloud",
        "user_role": "زائر",
        "input_placeholder": "اسأل أكين يورت عن التاريخ...",
        "thinking": "جاري الاتصال بالسيرفر والتحليل العميق...",
        "thought_label": "📝 مسار التفكير (اضغط للعرض)",
        "server_error": "⚠️ فشل الاتصال بالسيرفر. تأكد من تشغيل Ollama وفتح البورت 11434.",
        "timeout_error": "⚠️ السيرفر يستغرق وقتاً طويلاً جداً (انتهى الوقت).",
        "welcome_msg": "مرحباً. أنا أعمل عبر اتصال مباشر بسيرفر AWS باستخدام DeepSeek-R1. كيف يمكنني مساعدتك؟"
    },
    "TR": {
        "dir": "ltr", "align": "left",
        "title": "Akın Yurt YZ (DeepSeek)",
        "subtitle": "Derin Analiz ve Tarih Portalı - AWS",
        "user_role": "Misafir",
        "input_placeholder": "Akın Yurt'a sor (Tarih, Analiz)...",
        "thinking": "Sunucuyla bağlantı kuruluyor ve düşünülüyor...",
        "thought_label": "📝 Düşünce Süreci (Görmek için tıkla)",
        "server_error": "⚠️ Sunucu hatası. 11434 portunun açık olduğundan emin olun.",
        "timeout_error": "⚠️ Zaman aşımı. Sunucu yanıt vermedi.",
        "welcome_msg": "Merhaba. AWS sunucusu üzerinden DeepSeek-R1 modelini kullanarak hizmet veriyorum.",
    },
    "EN": {
        "dir": "ltr", "align": "left",
        "title": "Turkmeneli AI (DeepSeek)",
        "subtitle": "Deep Reasoning Portal - AWS Direct",
        "user_role": "Guest",
        "input_placeholder": "Ask Akın Yurt...",
        "thinking": "Connecting to AWS and reasoning...",
        "thought_label": "📝 Chain of Thought (Click to view)",
        "server_error": "⚠️ Server connection failed. Check Port 11434.",
        "timeout_error": "⚠️ Server timeout.",
        "welcome_msg": "Hello. Running on AWS Direct Connection with DeepSeek-R1."
    }
}

T = TEXTS[st.session_state.language]

st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;700&family=Roboto:wght@400;700&display=swap');
    html, body, [class*="css"] {{ font-family: 'Roboto', 'Tajawal', sans-serif; }}
    .stApp, .stTextInput, .stButton, .stMarkdown {{ direction: {T['dir']}; text-align: {T['align']}; }}
    .stChatInputContainer textarea {{ direction: {T['dir']}; text-align: {T['align']}; }}
    .streamlit-expanderHeader {{ font-size: 0.9em; color: #555; }}
</style>
""", unsafe_allow_html=True)

# =========================================================
# 2. المحرك والاتصال
# =========================================================

def init_supabase():
    try: return create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])
    except: return None
db = init_supabase()

class PrivateServerEngine:
    def __init__(self):
        try:
            # هنا يتم قراءة الرابط من ملف secrets.toml
            self.api_url = st.secrets["akinyurt_server"]["url"]
            self.model_name = st.secrets["akinyurt_server"]["model_name"]
        except:
            self.api_url = None
            self.model_name = "akinyurt"

    def parse_deepseek_output(self, raw_text):
        thought_match = re.search(r'<think>(.*?)</think>', raw_text, re.DOTALL)
        if thought_match:
            thought = thought_match.group(1).strip()
            answer = re.sub(r'<think>.*?</think>', '', raw_text, flags=re.DOTALL).strip()
            return thought, answer
        else:
            return None, raw_text

    def generate_response(self, query, lang_code):
        if not self.api_url: return None, "Configuration Error: Secrets missing."
        
        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": query}],
            "stream": False,
            "options": {"temperature": 0.6, "num_ctx": 8192}
        }
        
        try:
            # 3 ساعات انتظار
            response = requests.post(f"{self.api_url}/api/chat", json=payload, timeout=10800)
            
            if response.status_code == 200:
                raw_content = response.json()['message']['content']
                thought, clean_answer = self.parse_deepseek_output(raw_content)
                
                if db:
                    try: 
                        db.table("chat_history").insert({
                            "username": "guest", "question": query, "answer": clean_answer, "lang": lang_code
                        }).execute()
                    except: pass
                
                return thought, clean_answer
            else:
                return None, f"Server Error: {response.status_code}"
                
        except requests.exceptions.Timeout:
            return None, TEXTS[lang_code]['timeout_error']
        except requests.exceptions.ConnectionError:
            return None, TEXTS[lang_code]['server_error']
        except Exception as e:
            return None, f"Error: {str(e)}"

# =========================================================
# 3. الواجهة
# =========================================================

def main():
    with st.sidebar:
        st.header(f"🧠 {T['user_role']}")
        lang_options = ["TR", "AR", "EN"]
        selected_lang = st.selectbox("Dil / اللغة", lang_options, index=lang_options.index(st.session_state.language))
        
        if selected_lang != st.session_state.language:
            st.session_state.language = selected_lang
            st.rerun()
            
        st.divider()
        st.info("Connection: **AWS Direct IP**\nModel: **DeepSeek-R1**")
        if st.button("🗑️ Reset"):
            st.session_state.messages = []
            st.rerun()

    st.title(f"🏰 {T['title']}")
    st.caption(T['subtitle'])

    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": T['welcome_msg']}]

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            if "thought" in msg and msg["thought"]:
                with st.expander(f"👁️ {T['thought_label']}"):
                    st.markdown(f"_{msg['thought']}_")
            st.markdown(msg["content"])

    if prompt := st.chat_input(T["input_placeholder"]):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        engine = PrivateServerEngine()
        with st.chat_message("assistant"):
            with st.spinner(T["thinking"]):
                thought, answer = engine.generate_response(prompt, st.session_state.language)
                
                if thought:
                    with st.expander(f"👁️ {T['thought_label']}"):
                        st.markdown(f"_{thought}_")
                
                st.markdown(answer)
                st.session_state.messages.append({"role": "assistant", "content": answer, "thought": thought})

if __name__ == "__main__":
    main()

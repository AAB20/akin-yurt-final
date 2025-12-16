import streamlit as st
import requests
import json
import re
from supabase import create_client, Client

# =========================================================
# 1. إعدادات الصفحة واللغة (Page Configuration)
# =========================================================

st.set_page_config(page_title="Akın Yurt AI (DeepSeek)", page_icon="🧠", layout="centered")

# تهيئة اللغة الافتراضية
if "language" not in st.session_state:
    st.session_state.language = "TR"

# نصوص الواجهة (مترجمة بدقة)
TEXTS = {
    "AR": {
        "dir": "rtl", "align": "right",
        "title": "ذكاء تركمان إيلي (الجيل العميق)",
        "subtitle": "بوابة المعرفة الموثقة - DeepSeek R1",
        "user_role": "زائر",
        "input_placeholder": "اسأل أكين يورت عن التاريخ...",
        "thinking": "جاري التحليل العميق واسترجاع التاريخ...",
        "thought_label": "📝 مسار التفكير (اضغط للعرض)",
        "server_error": "⚠️ السيرفر غير متصل.",
        "timeout_error": "⚠️ السيرفر يستغرق وقتاً طويلاً جداً.",
        "welcome_msg": "مرحباً. أنا أستخدم نموذج التفكير العميق (DeepSeek) لتحليل التاريخ التركماني بدقة. كيف يمكنني مساعدتك؟"
    },
    "TR": {
        "dir": "ltr", "align": "left",
        "title": "Akın Yurt YZ (DeepSeek)",
        "subtitle": "Derin Analiz ve Tarih Portalı",
        "user_role": "Misafir",
        "input_placeholder": "Akın Yurt'a sor (Tarih, Analiz)...",
        "thinking": "Akın Yurt derin düşünüyor...",
        "thought_label": "📝 Düşünce Süreci (Görmek için tıkla)",
        "server_error": "⚠️ Sunucu hatası.",
        "timeout_error": "⚠️ Zaman aşımı. Sunucu yanıt vermedi.",
        "welcome_msg": "Merhaba. Türkmen tarihini en ince ayrıntısına kadar analiz etmek için DeepSeek-R1 modelini kullanıyorum.",
    },
    "EN": {
        "dir": "ltr", "align": "left",
        "title": "Turkmeneli AI (DeepSeek)",
        "subtitle": "Deep Reasoning Historical Portal",
        "user_role": "Guest",
        "input_placeholder": "Ask Akın Yurt...",
        "thinking": "Deep reasoning in progress...",
        "thought_label": "📝 Chain of Thought (Click to view)",
        "server_error": "⚠️ Server connection failed.",
        "timeout_error": "⚠️ Server timeout.",
        "welcome_msg": "Hello. I am running on DeepSeek-R1 to strictly analyze Turkmen history facts."
    }
}

T = TEXTS[st.session_state.language]

# تنسيق CSS (خطوط + اتجاهات)
st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;700&family=Roboto:wght@400;700&display=swap');
    
    html, body, [class*="css"] {{
        font-family: 'Roboto', 'Tajawal', sans-serif;
    }}
    
    .stApp, .stTextInput, .stButton, .stMarkdown {{ 
        direction: {T['dir']}; 
        text-align: {T['align']}; 
    }}
    
    .stChatInputContainer textarea {{ 
        direction: {T['dir']}; 
        text-align: {T['align']}; 
    }}
    
    /* تنسيق صندوق التفكير */
    .streamlit-expanderHeader {{
        font-size: 0.9em;
        color: #555;
    }}
</style>
""", unsafe_allow_html=True)

# =========================================================
# 2. المحرك والاتصال (Engine Logic)
# =========================================================

def init_supabase():
    try:
        return create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])
    except: return None

db = init_supabase()

class PrivateServerEngine:
    def __init__(self):
        try:
            self.api_url = st.secrets["akinyurt_server"]["url"]
            self.model_name = st.secrets["akinyurt_server"]["model_name"]
        except:
            self.api_url = None
            self.model_name = "akinyurt"

    def parse_deepseek_output(self, raw_text):
        """
        وظيفة ذكية لفصل التفكير <think> عن الإجابة النهائية
        """
        # البحث عن محتوى ما بين التاغات
        thought_match = re.search(r'<think>(.*?)</think>', raw_text, re.DOTALL)
        
        if thought_match:
            thought = thought_match.group(1).strip()
            # حذف التاغات وما بينهما للحصول على الإجابة النظيفة
            answer = re.sub(r'<think>.*?</think>', '', raw_text, flags=re.DOTALL).strip()
            return thought, answer
        else:
            # في حال لم يخرج الموديل أي تفكير (نادر الحدوث)
            return None, raw_text

    def generate_response(self, query, lang_code):
        if not self.api_url: return None, "Configuration Error: Secrets missing."
        
        # DeepSeek R1 لا يحتاج System Prompt هنا، لأنه مدمج في الموديل
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "user", "content": query}
            ],
            "stream": False,
            "options": {
                "temperature": 0.6, # حرارة مناسبة للتفكير
                "num_ctx": 8192     # سياق طويل للتفكير العميق
            }
        }
        
        try:
            # 🕒 وقت انتظار 3 ساعات (10800 ثانية)
            response = requests.post(f"{self.api_url}/api/chat", json=payload, timeout=10800)
            
            if response.status_code == 200:
                raw_content = response.json()['message']['content']
                
                # المعالجة والفصل
                thought, clean_answer = self.parse_deepseek_output(raw_content)
                
                # حفظ الإجابة النهائية فقط في قاعدة البيانات
                if db:
                    try: 
                        db.table("chat_history").insert({
                            "username": "guest", 
                            "question": query, 
                            "answer": clean_answer,
                            "lang": lang_code
                        }).execute()
                    except: pass
                
                return thought, clean_answer
            else:
                return None, f"Server Error: {response.status_code}"
                
        except requests.exceptions.Timeout:
            return None, TEXTS[lang_code]['timeout_error']
        except Exception as e:
            return None, f"{TEXTS[lang_code]['server_error']} ({str(e)})"

# =========================================================
# 3. واجهة التطبيق (UI)
# =========================================================

def main():
    # الشريط الجانبي
    with st.sidebar:
        st.header(f"🧠 {T['user_role']}")
        
        # اختيار اللغة
        lang_options = ["TR", "AR", "EN"]
        selected_lang = st.selectbox("Dil / اللغة", lang_options, index=lang_options.index(st.session_state.language))
        
        if selected_lang != st.session_state.language:
            st.session_state.language = selected_lang
            st.rerun()
            
        st.divider()
        st.info("Model: **DeepSeek-R1 (7B)**\nMode: **Historical Reasoning**")
        
        if st.button("🗑️ Reset Chat"):
            st.session_state.messages = []
            st.rerun()

    # العنوان الرئيسي
    st.title(f"🏰 {T['title']}")
    st.caption(T['subtitle'])

    # تهيئة الرسائل
    if "messages" not in st.session_state:
        st.session_state.messages = []
        st.session_state.messages.append({"role": "assistant", "content": T['welcome_msg']})

    # عرض الرسائل
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            # إذا كانت الرسالة تحتوي على "تفكير"، نعرضه في صندوق مغلق
            if "thought" in msg and msg["thought"]:
                with st.expander(f"👁️ {T['thought_label']}"):
                    st.markdown(f"_{msg['thought']}_")
            
            # عرض المحتوى الأساسي
            st.markdown(msg["content"])

    # إدخال المستخدم
    if prompt := st.chat_input(T["input_placeholder"]):
        # إضافة وعرض رسالة المستخدم
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # المعالجة
        engine = PrivateServerEngine()
        with st.chat_message("assistant"):
            with st.spinner(T["thinking"]):
                thought, answer = engine.generate_response(prompt, st.session_state.language)
                
                # عرض التفكير (اختياري)
                if thought:
                    with st.expander(f"👁️ {T['thought_label']}"):
                        st.markdown(f"_{thought}_")
                
                # عرض الإجابة
                st.markdown(answer)
                
                # الحفظ في الجلسة
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": answer, 
                    "thought": thought  # نحفظ التفكير أيضاً لنعرضه إذا صعد المستخدم للأعلى
                })

if __name__ == "__main__":
    main()

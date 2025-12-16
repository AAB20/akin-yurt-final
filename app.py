import streamlit as st
import requests
import json
from supabase import create_client, Client

# =========================================================
# 1. إعدادات الصفحة واللغات (Page & Language Config)
# =========================================================

st.set_page_config(page_title="Akın Yurt AI", page_icon="🏰", layout="centered")

# تعيين اللغة الافتراضية
if "language" not in st.session_state:
    st.session_state.language = "TR"  # الافتراضي تركية

# قاموس النصوص (تمت مراجعته ليكون دقيقاً لغوياً)
TEXTS = {
    "AR": {
        "dir": "rtl", "align": "right",
        "title": "ذكاء تركمان إيلي", 
        "subtitle": "بوابة المعرفة والثقافة التركمانية",
        "user_role": "زائر",
        "input_placeholder": "اسأل أكين يورت عن التاريخ، الثقافة، أو السياسة...",
        "thinking": "جاري صياغة الرد...",
        "server_error": "⚠️ السيرفر غير متصل أو الرابط تغير.",
        "welcome_msg": "مرحباً، أنا أكين يورت. أنا هنا لخدمة القضية التركمانية وحفظ تاريخنا. كيف يمكنني مساعدتك؟",
        "lang_instruction": "Answer in Arabic language only."
    },
    "TR": {
        "dir": "ltr", "align": "left",
        "title": "Akın Yurt YZ", 
        "subtitle": "Türkmen Bilgi ve Kültür Portalı",
        "user_role": "Misafir",
        "input_placeholder": "Akın Yurt'a sor (Tarih, Kültür, Siyaset)...",
        "thinking": "Akın Yurt düşünüyor...",
        "server_error": "⚠️ Sunucuya bağlanılamadı.",
        "welcome_msg": "Merhaba, ben Akın Yurt. Türkmen davasına hizmet etmek ve tarihimizi korumak için buradayım. Size nasıl yardımcı olabilirim?",
        "lang_instruction": "Answer in Turkish language only. Use proper grammar (İstanbul Türkçesi) and correct characters (ç, ğ, ı, ö, ş, ü)."
    },
    "EN": {
        "dir": "ltr", "align": "left",
        "title": "Turkmeneli AI", 
        "subtitle": "Turkmen Knowledge Portal",
        "user_role": "Guest",
        "input_placeholder": "Ask Akın Yurt about history, culture, or politics...",
        "thinking": "Thinking...",
        "server_error": "⚠️ Server connection failed.",
        "welcome_msg": "Hello, I am Akın Yurt. I am here to serve the Turkmen cause and preserve our history. How can I help you?",
        "lang_instruction": "Answer in English language only."
    }
}

# جلب النصوص حسب اللغة المختارة
T = TEXTS[st.session_state.language]

# CSS: تحسين الخطوط ودعم الاتجاهات (RTL/LTR)
st.markdown(f"""
<style>
    /* استيراد خطوط تدعم التركية والعربية بشكل جميل */
    @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;700&family=Roboto:wght@400;700&display=swap');
    
    html, body, [class*="css"] {{
        font-family: 'Roboto', 'Tajawal', sans-serif;
    }}
    
    .stApp, .stTextInput, .stButton, .stMarkdown {{ 
        direction: {T['dir']}; 
        text-align: {T['align']}; 
    }}
    
    /* ضبط اتجاه صندوق الإدخال */
    .stChatInputContainer textarea {{ 
        direction: {T['dir']}; 
        text-align: {T['align']}; 
    }}
    
    /* إخفاء الهوامش الزائدة */
    .block-container {{
        padding-top: 2rem;
    }}
</style>
""", unsafe_allow_html=True)

# =========================================================
# 2. إعداد الاتصالات (Supabase & Private Server)
# =========================================================

# الاتصال بقاعدة البيانات (اختياري - لن يوقف التطبيق إذا فشل)
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

    def generate_response(self, query, lang_code):
        if not self.api_url: return "Configuration Error: Secrets missing."
        
        # تعليمات النظام بناءً على اللغة (لضمان الدقة)
        system_prompt = f"""
        You are "Akın Yurt". 
        CRITICAL: {TEXTS[lang_code]['lang_instruction']}
        Do not hallucinate. If you don't know, say you don't know.
        """

        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ],
            "stream": False,
            "options": {
                "temperature": 0.2, # حرارة منخفضة لتقليل الأخطاء اللغوية
                "num_ctx": 4096
            }
        }
        
        try:
            # الاتصال بالسيرفر
            response = requests.post(f"{self.api_url}/api/chat", json=payload, timeout=90)
            
            if response.status_code == 200:
                ans = response.json()['message']['content']
                
                # حفظ في Supabase (محاولة فقط)
                if db:
                    try: 
                        db.table("chat_history").insert({
                            "username": "guest", 
                            "question": query, 
                            "answer": ans,
                            "lang": lang_code
                        }).execute()
                    except: pass
                
                return ans
            else:
                return f"Server Error: {response.status_code}"
        except Exception as e:
            return f"{TEXTS[lang_code]['server_error']} ({str(e)})"

# =========================================================
# 3. واجهة التطبيق الرئيسية (Main UI)
# =========================================================

def main():
    # الشريط الجانبي (Sidebar)
    with st.sidebar:
        st.header(f"👤 {T['user_role']}")
        
        # قائمة اختيار اللغة
        lang_options = ["TR", "AR", "EN"]
        selected_lang = st.selectbox(
            "Dil / اللغة / Language", 
            lang_options, 
            index=lang_options.index(st.session_state.language)
        )
        
        # إعادة التحميل عند تغيير اللغة لتطبيق الاتجاهات
        if selected_lang != st.session_state.language:
            st.session_state.language = selected_lang
            st.rerun()
            
        st.divider()
        st.caption("Powered by Akın Yurt Server (AWS)")
        
        # زر لمسح المحادثة
        if st.button("🗑️ Temizle / مسح"):
            st.session_state.messages = []
            st.rerun()

    # العنوان
    st.title(f"🏰 {T['title']}")
    st.markdown(f"*{T['subtitle']}*")

    # تهيئة سجل المحادثة
    if "messages" not in st.session_state:
        st.session_state.messages = []
        # رسالة ترحيبية تلقائية
        st.session_state.messages.append({"role": "assistant", "content": T['welcome_msg']})

    # عرض الرسائل القديمة
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # صندوق الإدخال (Input)
    if prompt := st.chat_input(T["input_placeholder"]):
        # 1. عرض رسالة المستخدم
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # 2. الحصول على الرد
        engine = PrivateServerEngine()
        with st.chat_message("assistant"):
            with st.spinner(T["thinking"]):
                response_text = engine.generate_response(prompt, st.session_state.language)
                st.markdown(response_text)
                
                # حفظ الرد في الجلسة
                st.session_state.messages.append({"role": "assistant", "content": response_text})

if __name__ == "__main__":
    main()

import streamlit as st
import datetime
import re
import unicodedata
import requests
import json
import base64
import time
from difflib import SequenceMatcher
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from Crypto.Random import get_random_bytes
from streamlit_oauth import OAuth2Component
from supabase import create_client, Client

# =========================================================
# 1. إعدادات النظام والترجمة (SYSTEM & LOCALIZATION)
# =========================================================

st.set_page_config(page_title="Akın Yurt AI", page_icon="🏰", layout="centered")

# تهيئة اللغة الافتراضية
if "language" not in st.session_state:
    st.session_state.language = "AR"

# قاموس النصوص المترجمة
TEXTS = {
    "AR": {
        "dir": "rtl", "align": "right",
        "title": "ذكاء تركمان إيلي", "subtitle": "بوابة المعرفة التركمانية", 
        "google_btn": "تسجيل الدخول باستخدام Google", "secure_login": "🔒 الدخول بواسطة Google OAuth 2.0",
        "profile": "الملف الشخصي", "user": "المستخدم", "logout": "تسجيل الخروج",
        "status": "متصل: قاعدة بيانات Supabase", "chat_title": "روبوت تركمان إيلي",
        "chat_caption": "نظام ذكي هجين (ذاكرة سحابية + ويكيبيديا + Akın Yurt Private Server)", 
        "input_placeholder": "اسأل عن تاريخ، جغرافية، أو ثقافة تركمان العراق...",
        "searching_db": "جاري البحث في الذاكرة السحابية...", 
        "searching_wiki": "جاري البحث في المصادر المفتوحة...",
        "thinking_ai": "جاري الاتصال بسيرفر Akın Yurt الخاص...", 
        "source": "المصدر", "db_source": "الذاكرة السحابية",
        "welcome": "مرحباً", "error_db": "⚠️ خطأ: قاعدة البيانات غير متصلة.", 
        "error_secrets": "⚠️ ملف الأسرار غير مكتمل.",
        "ai_status": "حالة السيرفر", "ai_ok": "متصل (AWS)", "ai_fail": "غير متصل",
        "persona": """
        أنت مؤرخ وباحث خبير في شؤون "تركمان إيلي" والشرق الأوسط.
        أسلوبك: بشري، قصصي، عميق، وغير نمطي. تجنب القوائم المملة.
        استخدم مفردات غنية (مثل: في غياهب التاريخ، تتجلى، بيد أن).
        """
    },
    "EN": {
        "dir": "ltr", "align": "left",
        "title": "Turkmeneli AI", "subtitle": "Turkmen Knowledge Portal", 
        "google_btn": "Sign in with Google", "secure_login": "🔒 Secured by Google OAuth 2.0",
        "profile": "Profile", "user": "User", "logout": "Logout",
        "status": "Connected: Supabase DB", "chat_title": "Turkmeneli AI Bot",
        "chat_caption": "Hybrid AI System (Cloud Memory + Wikipedia + Akın Yurt Private Server)", 
        "input_placeholder": "Ask about Iraqi Turkmen history, geography, or culture...",
        "searching_db": "Searching cloud memory...", 
        "searching_wiki": "Searching open sources...",
        "thinking_ai": "Connecting to Private Akın Yurt Server...", 
        "source": "Source", "db_source": "Cloud Memory",
        "welcome": "Welcome", "error_db": "⚠️ Error: Database disconnected.", 
        "error_secrets": "⚠️ Secrets file incomplete.",
        "ai_status": "Server Status", "ai_ok": "Online (AWS)", "ai_fail": "Offline",
        "persona": """
        You are an expert historian specializing in 'Turkmeneli' and Middle Eastern affairs.
        Style: Human-like, narrative, deep, and non-robotic. Avoid boring lists.
        Use rich vocabulary and varied sentence structures to sound natural.
        """
    },
    "TR": {
        "dir": "ltr", "align": "left",
        "title": "Türkmeneli YZ", "subtitle": "Türkmen Bilgi Portalı", 
        "google_btn": "Google ile Giriş Yap", "secure_login": "🔒 Google OAuth 2.0 ile korunmaktadır",
        "profile": "Profil", "user": "Kullanıcı", "logout": "Çıkış Yap",
        "status": "Bağlı: Supabase VT", "chat_title": "Türkmeneli YZ Botu",
        "chat_caption": "Hibrit YZ Sistemi (Bulut Bellek + Vikipedi + Akın Yurt Private Server)", 
        "input_placeholder": "Irak Türkmen tarihi, coğrafyası veya kültürü hakkında sorun...",
        "searching_db": "Bulut bellek taranıyor...", 
        "searching_wiki": "Açık kaynaklar aranıyor...",
        "thinking_ai": "Özel Akın Yurt Sunucusuna bağlanılıyor...", 
        "source": "Kaynak", "db_source": "Bulut Bellek",
        "welcome": "Hoşgeldiniz", "error_db": "⚠️ Hata: Veritabanı bağlantısı yok.", 
        "error_secrets": "⚠️ Gizli anahtarlar eksik.",
        "ai_status": "Sunucu Durumu", "ai_ok": "Çevrimiçi (AWS)", "ai_fail": "Çevrimdışı",
        "persona": """
        'Türkmeneli' ve Ortadoğu ilişkileri konusunda uzman bir tarihçi ve araştırmacısın.
        Tarzın: İnsansı, hikaye anlatıcısı gibi, derin ve robotik olmayan. Sıkıcı listelerden kaçın.
        Doğal görünmek için zengin bir kelime dağarcığı kullan.
        """
    }
}

T = TEXTS[st.session_state.language]

# CSS Localization
st.markdown(f"""
<style>
    .stApp, .stMarkdown, .stTextInput, .stButton, .stSelectbox {{
        direction: {T['dir']};
        text-align: {T['align']};
    }}
    section[data-testid="stSidebar"] {{
        direction: {T['dir']};
        text-align: {T['align']};
    }}
    div.stButton > button {{
        width: 100%; border-radius: 10px; font-weight: bold; height: 50px;
    }}
    .stChatInputContainer textarea {{
        direction: {T['dir']}; text-align: {T['align']};
    }}
</style>
""", unsafe_allow_html=True)

class AppConfig:
    TOPICS = {
        "AR": ["كركوك", "التركمان العراقيون", "تركمان ايلي", "قلعة كركوك", "التون كوبري", "الدولة العثمانية", "السلاجقة", "أذربيجان", "طوزخورماتو", "تلعفر", "مجزرة كركوك 1959", "المقام العراقي"],
        "TR": ["Kerkük", "Irak Türkmenleri", "Türkmeneli", "Kerkük Kalesi", "Altunköprü", "Osmanlı İmparatorluğu", "Selçuklu", "Azerbaycan", "Tuzhurmatu", "Telafer", "1959 Kerkük Katliamı", "Hoyrat"],
        "EN": ["Kirkuk", "Iraqi Turkmens", "Turkmeneli", "Kirkuk Citadel", "Altun Kupri", "Ottoman Empire", "Seljuk Empire", "Azerbaijan", "Tuz Khurmatu", "Tal Afar", "1959 Kirkuk massacre", "Iraqi Maqam"]
    }

    @staticmethod
    def init_supabase():
        try:
            return create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])
        except: return None

db: Client = AppConfig.init_supabase()

# =========================================================
# 2. الأمن والتشفير (SECURITY)
# =========================================================

class CryptoManager:
    def __init__(self):
        if "encryption_key" in st.secrets:
            try: self.key = bytes.fromhex(st.secrets["encryption_key"])
            except: self.key = get_random_bytes(32)
        else: self.key = get_random_bytes(32)

    def encrypt(self, raw_text):
        try:
            cipher = AES.new(self.key, AES.MODE_CBC)
            ct_bytes = cipher.encrypt(pad(raw_text.encode('utf-8'), AES.block_size))
            return base64.b64encode(cipher.iv + ct_bytes).decode('utf-8')
        except: return ""

class UserManager:
    def __init__(self):
        self.crypto = CryptoManager()

    def social_login_check(self, email):
        if not db: return False
        try:
            if not db.table("users").select("username").eq("username", email).execute().data:
                dummy = self.crypto.encrypt("GOOG_" + base64.b64encode(get_random_bytes(8)).decode())
                db.table("users").insert({"username": email, "password_hash": dummy}).execute()
            return True
        except: return False

# =========================================================
# 3. محرك الاتصال بالسيرفر الخاص (CUSTOM SERVER ENGINE)
# =========================================================

class HumanizerEngine:
    def __init__(self):
        # هنا نستدعي الرابط الخاص بسيرفرك من ملف الأسرار
        try:
            self.api_url = st.secrets["akinyurt_server"]["url"]
            self.model_name = st.secrets["akinyurt_server"]["model_name"]
        except:
            self.api_url = None
            self.model_name = "akinyurt"

    def normalize_text(self, text):
        return re.sub(r"http\S+|www\.\S+", "", unicodedata.normalize("NFKC", text.strip())).strip()

    def guess_lang(self, text):
        if any('\u0600' <= c <= '\u06FF' for c in text): return "ar"
        if any(c in "çğıöşüÇĞİÖŞÜ" for c in text): return "tr"
        return "en"

    def generate_human_response(self, query, context_text=None, lang="AR"):
        if not self.api_url: return "⚠️ Error: Server URL Missing in secrets.", "System"

        # اختيار الشخصية المناسبة للغة
        persona_prompt = TEXTS[st.session_state.language]["persona"]
        
        # دمج السياق إن وجد
        context_instruction = f"Context from Wikipedia/DB: {context_text}" if context_text else ""
        
        # تجهيز الرسائل للسيرفر
        # نرسل الـ System Prompt هنا لضمان الأسلوب، بالإضافة لما هو موجود في الموديل أصلاً
        messages_payload = [
            {
                "role": "system",
                "content": f"{persona_prompt}\nIMPORTANT: Respond in language code: {lang}"
            },
            {
                "role": "user",
                "content": f"{context_instruction}\n\nUser Question: {query}"
            }
        ]
        
        payload = {
            "model": self.model_name,
            "messages": messages_payload,
            "stream": False,
            "options": {
                "temperature": 0.7 # نعيد الحرارة قليلاً للأسلوب القصسي
            }
        }
        
        try:
            response = requests.post(f"{self.api_url}/api/chat", json=payload, timeout=45)
            if response.status_code == 200:
                result = response.json()
                return result['message']['content'], "Akın Yurt (AWS Server)"
            else:
                return f"Server Error: {response.status_code}", "Error"
        except Exception as e:
            return f"Connection Failed: {e}", "Connection Error"

    def search_db(self, query):
        if not db: return None
        try:
            q_norm = self.normalize_text(query)
            res = db.table("chat_history").select("answer").ilike("question", f"%{q_norm}%").limit(1).execute()
            if res.data: return res.data[0]["answer"]
        except: pass
        return None

    def search_wiki(self, query, lang):
        topics = AppConfig.TOPICS["AR"] if lang == "ar" else AppConfig.TOPICS["TR"] if lang == "tr" else AppConfig.TOPICS["EN"]
        best, score = None, 0
        for t in topics:
            sc = SequenceMatcher(None, query.lower(), t.lower()).ratio()
            if sc > score: best, score = t, sc
        
        if score >= 0.70:
            try:
                wiki_lang = lang
                url = f"https://{wiki_lang}.wikipedia.org/api/rest_v1/page/summary/{best.replace(' ', '%20')}"
                r = requests.get(url, timeout=3)
                if r.status_code == 200: return r.json().get("extract"), f"Wikipedia ({best})"
            except: pass
        return None, None

    def save_log(self, user, q, a, src):
        if db:
            try: db.table("chat_history").insert({"username": user, "question": q, "answer": a, "source": src}).execute()
            except: pass

# =========================================================
# 4. واجهة المستخدم (UI)
# =========================================================

def language_selector():
    c1, c2 = st.columns([4, 1])
    with c2:
        lang = st.selectbox("🌐", ["AR", "EN", "TR"], index=["AR", "EN", "TR"].index(st.session_state.language), label_visibility="collapsed")
        if lang != st.session_state.language:
            st.session_state.language = lang
            st.rerun()

def handle_login():
    if "google" not in st.secrets:
        st.error(T["error_secrets"])
        return

    oauth = OAuth2Component(
        st.secrets["google"]["client_id"], st.secrets["google"]["client_secret"],
        "https://accounts.google.com/o/oauth2/v2/auth", "https://oauth2.googleapis.com/token",
        "https://oauth2.googleapis.com/token", "https://oauth2.googleapis.com/revoke"
    )
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        try:
            res = oauth.authorize_button(T["google_btn"], "https://www.google.com.tw/favicon.ico",
                st.secrets["google"]["redirect_uri"], "email profile", "g_btn", extras_params={"prompt": "select_account"})
        except:
            st.rerun()
            return

    if res:
        try:
            email = json.loads(base64.b64decode(res["token"]["id_token"].split(".")[1]+"==").decode("utf-8")).get("email")
            if email and UserManager().social_login_check(email):
                st.session_state.logged_in = True
                st.session_state.username = email
                st.success(f"{T['welcome']} {email}")
                time.sleep(0.5)
                st.rerun()
        except: st.error("Login Failed")

def main_app():
    with st.sidebar:
        language_selector()
        st.title(f"👤 {T['profile']}")
        st.write(f"**{st.session_state.username}**")
        st.markdown("---")
        st.write(f"**{T['ai_status']}:**")
        if "akinyurt_server" in st.secrets: st.success(T['ai_ok'])
        else: st.error(T['ai_fail'])
        
        if st.button(T['logout']):
            st.session_state.logged_in = False
            st.rerun()
        st.caption(f"🟢 {T['status']}")

    st.title(f"🤖 {T['chat_title']}")
    st.caption(T['chat_caption'])

    engine = HumanizerEngine()

    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])
            if "src" in m: st.caption(f"{T['source']}: {m['src']}")

    if q := st.chat_input(T['input_placeholder']):
        st.session_state.messages.append({"role": "user", "content": q})
        st.chat_message("user").markdown(q)

        ans, src = "", ""
        lang = engine.guess_lang(q)

        # 1. Supabase
        with st.spinner(T['searching_db']):
            db_ans = engine.search_db(q)
            if db_ans: ans, src = db_ans, f"{T['db_source']} (Supabase)"
        
        # 2. Wikipedia + Custom Server
        if not ans:
            with st.spinner(T['searching_wiki']):
                wiki_txt, wiki_src = engine.search_wiki(engine.normalize_text(q), lang)
        
            # 3. Akın Yurt Server (يستخدم الويكي كسياق إذا وجد)
            with st.spinner(T['thinking_ai']):
                # الاتصال بسيرفرك بدلاً من Gemini
                ans, src = engine.generate_human_response(q, context_text=wiki_txt, lang=lang)
                if wiki_txt: src = f"AI Augmented ({wiki_src})"

        engine.save_log(st.session_state.username, q, ans, src)
        st.session_state.messages.append({"role": "assistant", "content": ans, "src": src})
        with st.chat_message("assistant"):
            st.markdown(ans)
            st.caption(f"{T['source']}: {src}")

if __name__ == "__main__":
    if "logged_in" not in st.session_state: st.session_state.logged_in = False
    if "messages" not in st.session_state: st.session_state.messages = []
    
    if st.session_state.logged_in: main_app()
    else:
        language_selector()
        st.title(f"🏰 {T['title']}")
        st.subheader(T['subtitle'])
        if not db: st.error(T['error_db'])
        handle_login()
        st.markdown("---")
        st.caption(T['secure_login'])

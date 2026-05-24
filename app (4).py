import streamlit as st
import pandas as pd
import docx
from PIL import Image
import google.generativeai as genai
import os
import glob
import pdfplumber
from datetime import datetime
import io
import time

# إعدادات الصفحة (محاذاة من اليمين لليسار باستخدام CSS)
st.set_page_config(page_title="مقارن ملصقات المنتجات", page_icon="🔍", layout="wide")
st.markdown("""
    <style>
    /* إجبار محاذاة النصوص الأساسية من اليمين لليسار */
    body, .stApp, .stMarkdown, p, div, h1, h2, h3, h4, h5, h6 {
        direction: rtl;
        text-align: right;
    }
    /* تعديل محاذاة بعض العناصر في القوائم */
    ul, ol {
        padding-right: 2rem;
        padding-left: 0;
    }
    /* ضمان أن الكلمات الإنجليزية تظهر بشكل سليم داخل النص العربي */
    .stMarkdown p, .stMarkdown div {
        unicode-bidi: bidi-override;
    }
    /* تحسين مظهر مربعات المحادثة */
    .chat-message {
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
        direction: rtl;
        text-align: right;
    }
    </style>
""", unsafe_allow_html=True)

# إنشاء ذاكرة التطبيق
if 'history' not in st.session_state:
    st.session_state.history = []

# ذاكرة الشات الخاصة بكل صورة
if 'chat_sessions' not in st.session_state:
    st.session_state.chat_sessions = {}

def read_excel(file_path):
    try:
        df = pd.read_excel(file_path)
        return df.to_string(index=False)
    except Exception as e:
        return f"خطأ في الإكسيل ({file_path}): {e}"

def read_word(file_path):
    try:
        doc = docx.Document(file_path)
        return "\n".join([para.text for para in doc.paragraphs if para.text.strip() != ""])
    except Exception as e:
        return f"خطأ في الوورد ({file_path}): {e}"

def read_pdf_precise(file_path):
    try:
        text = ""
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                extracted = page.extract_text(layout=True)
                if extracted:
                    text += extracted + "\n"
        return text
    except Exception as e:
        return f"خطأ في الـ PDF ({file_path}): {e}"

@st.cache_data
def load_database():
    db_text = ""
    files_found = 0
    file_list = []
    
    for file in glob.glob("*.xlsx"):
        db_text += f"\n--- {file} ---\n" + read_excel(file)
        files_found += 1
        file_list.append(file)
        
    for file in glob.glob("*.docx"):
        db_text += f"\n--- {file} ---\n" + read_word(file)
        files_found += 1
        file_list.append(file)

    for file in glob.glob("*.pdf"):
        db_text += f"\n--- {file} ---\n" + read_pdf_precise(file)
        files_found += 1
        file_list.append(file)
        
    return db_text, files_found, file_list

st.title("🔍 المفتش الذكي لملصقات المنتجات")

tab1, tab2 = st.tabs(["🚀 الفحص والمحادثة", "📂 سجل الفحوصات"])

with tab1:
    api_key = st.sidebar.text_input("مفتاح Google Gemini API:", type="password")
    
    col1, col2 = st.columns([1, 1.2])
    with col1:
        st.header("1️⃣ قاعدة البيانات")
        with st.spinner("جاري التحميل..."):
            db_text, files_count, file_names = load_database()
        if files_count > 0:
            st.success(f"تم تحميل {files_count} ملفات بدقة.")
        else:
            st.warning("⚠️ لا توجد ملفات مرفوعة.")

    with col2:
        st.header("2️⃣ صور الملصقات")
        image_files = st.file_uploader("ارفع صور الملصقات", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)

    st.markdown("---")

    if st.button("🚀 بدء التحليل الدقيق", type="primary"):
        if not api_key or files_count == 0 or not image_files:
            st.error("تأكد من إدخال المفتاح ووجود ملفات وصور.")
        else:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.5-flash')
            
            for idx, image_file in enumerate(image_files):
                st.markdown(f"### 🏷️ تقرير: `{image_file.name}`")
                img_key = f"img_{idx}_{image_file.name}"
                
                # تهيئة جلسة شات خاصة بهذه الصورة إذا لم تكن موجودة
                if img_key not in st.session_state.chat_sessions:
                    try:
                        image = Image.open(image_file)
                        image.thumbnail((1200, 1200))
                        
                        prompt = f"""
                        أنت مفتش جودة صارم. مهمتك تحليل هذه الصورة فقط. اكتب الرد باللغة العربية الواضحة.
                        
                        قاعدة البيانات:
                        {db_text}
                        
                        المطلوب:
                        1. استخرج الباركود (الرقم) من الصورة، وابحث عنه بتركيز شديد في السطر الخاص به في قاعدة البيانات.
                        2. قارن اللغات (عربي، إنجليزي، فرنسي).
                        3. قارن جدول الحقائق التغذوية رقماً برقماً.
                        
                        التنسيق المطلوب:
                        ### 📝 البيانات المستخرجة:
                        ### 🔍 نتيجة البحث والباركود:
                        ### 🟢 المتطابق:
                        ### 🔴 الاختلافات:
                        ### ⚠️ بيانات ناقصة:
                        """
                        
                        with st.spinner(f"جاري الفحص..."):
                            chat = model.start_chat(history=[])
                            response = chat.send_message([prompt, image])
                            result = response.text
                            
                            # حفظ الشات والتقرير في الذاكرة
                            st.session_state.chat_sessions[img_key] = {
                                'chat': chat,
                                'report': result,
                                'image': image,
                                'messages': [{"role": "model", "content": result}]
                            }
                            
                            st.session_state.history.append({
                                "التاريخ": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "الصورة": image_file.name,
                                "النتيجة": result
                            })
                        time.sleep(2)
                    except Exception as e:
                        st.error(f"خطأ في {image_file.name}: {e}")
                        continue
                
                # عرض التقرير الملون مع التنسيق الجديد (يمين لليسار)
                report = st.session_state.chat_sessions[img_key]['report']
                for section in report.split('###'):
                    if not section.strip(): continue
                    if "البيانات المستخرجة" in section: st.info(f"### {section.strip()}")
                    elif "نتيجة البحث" in section: st.write(f"### {section.strip()}")
                    elif "المتطابق" in section: st.success(f"### {section.strip()}")
                    elif "الاختلافات" in section:
                        if "100%" in section or "لا يوجد" in section: st.success(f"### {section.strip()}")
                        else: st.error(f"### {section.strip()}")
                    elif "بيانات ناقصة" in section: st.warning(f"### {section.strip()}")
                
                st.markdown("---")

    # جزء المحادثة المستمر (يظهر بعد الفحص)
    if len(st.session_state.chat_sessions) > 0:
        st.markdown("## 💬 تناقش مع المفتش حول النتائج")
        
        # اختيار الصورة التي تريد التحدث عنها
        chat_options = list(st.session_state.chat_sessions.keys())
        selected_img_key = st.selectbox("اختر الاستيكر الذي تريد النقاش حوله:", chat_options, format_func=lambda x: x.split('_', 2)[2])
        
        current_session = st.session_state.chat_sessions[selected_img_key]
        
        # عرض المحادثات السابقة
        for msg in current_session['messages'][1:]: # نتخطى الرسالة الأولى لأنها التقرير
            if msg['role'] == 'user':
                st.markdown(f"<div class='chat-message' style='background-color: #E3F2FD;'><b>👤 أنت:</b><br>{msg['content']}</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div class='chat-message' style='background-color: #F5F5F5;'><b>🤖 المفتش الذكي:</b><br>{msg['content']}</div>", unsafe_allow_html=True)
        
        # مربع إدخال رسالة جديدة
        user_input = st.text_input("اكتب سؤالك (مثال: هل يمكن التغاضي عن فرق 1 جرام في البروتين؟)", key=f"input_{selected_img_key}")
        if st.button("إرسال السؤال ✉️", key=f"btn_{selected_img_key}"):
            if user_input:
                with st.spinner("جاري التفكير..."):
                    try:
                        # إرسال الرسالة للشات الخاص بهذه الصورة
                        response = current_session['chat'].send_message(user_input)
                        
                        # حفظ الرسائل في واجهة التطبيق
                        current_session['messages'].append({"role": "user", "content": user_input})
                        current_session['messages'].append({"role": "model", "content": response.text})
                        st.rerun()
                    except Exception as e:
                        st.error(f"حدث خطأ أثناء المحادثة: {e}")

with tab2:
    st.header("📂 السجل (لا يتم مسحه إلا إذا أغلقت المتصفح تماماً)")
    if len(st.session_state.history) > 0:
        df = pd.DataFrame(st.session_state.history)
        st.dataframe(df)
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='السجل')
        
        st.download_button("📥 تحميل الإكسيل", data=output.getvalue(), file_name=f"Report_{datetime.now().strftime('%Y%m%d')}.xlsx")
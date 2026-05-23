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

# إعدادات الصفحة
st.set_page_config(page_title="مقارن ملصقات المنتجات", page_icon="🔍", layout="wide")

# إنشاء ذاكرة التطبيق
if 'history' not in st.session_state:
    st.session_state.history = []

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
        # استخدام pdfplumber للحفاظ على التنسيق الدقيق للأسطر (مهم جداً للباركود)
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                extracted = page.extract_text(layout=True) # layout=True يمنع تداخل الأسطر
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

st.title("🔍 نظام تحليل ومقارنة ملصقات المنتجات (النسخة المستقرة)")

tab1, tab2 = st.tabs(["🚀 الفحص والتحليل", "📂 سجل الفحوصات"])

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
        image_files = st.file_uploader("ارفع صور الملصقات (يتم المعالجة واحدة تلو الأخرى لمنع الكراش)", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)

    st.markdown("---")

    if st.button("🚀 بدء التحليل الدقيق", type="primary"):
        if not api_key or files_count == 0 or not image_files:
            st.error("تأكد من إدخال المفتاح ووجود ملفات وصور.")
        else:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.5-flash')
            
            # معالجة الصور بشكل منفصل تماماً ومؤقت زمني لمنع الكراش والتخريف
            for idx, image_file in enumerate(image_files):
                st.markdown(f"### 🏷️ تقرير: `{image_file.name}`")
                
                with st.spinner(f"جاري الفحص..."):
                    try:
                        image = Image.open(image_file)
                        image.thumbnail((1200, 1200)) # ضغط أقوى لحماية الموبايل
                        
                        prompt = f"""
                        أنت مفتش جودة صارم. مهمتك الوحيدة هي تحليل هذه الصورة فقط. لا تقم بالاستنتاج، اعتمد على ما تراه فقط.
                        
                        قاعدة البيانات:
                        {db_text}
                        
                        المطلوب:
                        1. استخرج الباركود (الرقم) من الصورة، وابحث عنه بتركيز شديد في السطر الخاص به في قاعدة البيانات. لا تخلط الأسطر.
                        2. قارن اللغات (عربي، إنجليزي، فرنسي).
                        3. قارن جدول الحقائق التغذوية رقماً برقماً.
                        
                        التنسيق المطلوب (بدون مقدمات):
                        ### 📝 البيانات المستخرجة:
                        (اللغات والباركود وجدول التغذية)
                        ### 🔍 نتيجة البحث والباركود:
                        (هل الباركود في الصورة مطابق للباركود المكتوب بجوار اسم المنتج في القاعدة؟)
                        ### 🟢 المتطابق:
                        ### 🔴 الاختلافات:
                        (اذكر أي اختلاف بوضوح، وإلا اكتب متطابق 100%)
                        ### ⚠️ بيانات ناقصة:
                        """
                        
                        # إرسال طلب منفصل (Isolated) لهذه الصورة فقط
                        response = model.generate_content([prompt, image])
                        result = response.text
                        
                        st.session_state.history.append({
                            "التاريخ": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "الصورة": image_file.name,
                            "النتيجة": result
                        })
                        
                        for section in result.split('###'):
                            if not section.strip(): continue
                            if "البيانات المستخرجة" in section: st.info(f"### {section.strip()}")
                            elif "نتيجة البحث" in section: st.write(f"### {section.strip()}")
                            elif "المتطابق" in section: st.success(f"### {section.strip()}")
                            elif "الاختلافات" in section:
                                if "100%" in section or "لا يوجد" in section: st.success(f"### {section.strip()}")
                                else: st.error(f"### {section.strip()}")
                            elif "بيانات ناقصة" in section: st.warning(f"### {section.strip()}")
                        
                        # إيقاف مؤقت لمدة ثانيتين لتنظيف الذاكرة ومنع الكراش
                        time.sleep(2)
                        
                    except Exception as e:
                        st.error(f"خطأ في {image_file.name}: {e}")
                st.markdown("---")

with tab2:
    st.header("📂 السجل (لا يتم مسحه إلا إذا أغلقت المتصفح تماماً)")
    if len(st.session_state.history) > 0:
        df = pd.DataFrame(st.session_state.history)
        st.dataframe(df)
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='السجل')
        
        st.download_button("📥 تحميل الإكسيل", data=output.getvalue(), file_name=f"Report_{datetime.now().strftime('%Y%m%d')}.xlsx")

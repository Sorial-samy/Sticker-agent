import streamlit as st
import pandas as pd
import docx
from PIL import Image
import google.generativeai as genai
import os
import glob
import json

# إعدادات الصفحة
st.set_page_config(page_title="مقارن ملصقات المنتجات", page_icon="🔍", layout="wide")

# دوال مساعدة لقراءة الملفات
def read_excel(file_path):
    try:
        df = pd.read_excel(file_path)
        return df.to_string(index=False)
    except Exception as e:
        return f"خطأ في قراءة الإكسيل ({file_path}): {e}"

def read_word(file_path):
    try:
        doc = docx.Document(file_path)
        return "\n".join([para.text for para in doc.paragraphs if para.text.strip() != ""])
    except Exception as e:
        return f"خطأ في قراءة الوورد ({file_path}): {e}"

# دالة لقراءة قاعدة البيانات تلقائياً من المجلد
@st.cache_data
def load_database():
    db_text = ""
    files_found = 0
    
    # البحث عن ملفات الإكسيل
    excel_files = glob.glob("*.xlsx")
    for file in excel_files:
        db_text += f"\n--- بيانات من {file} ---\n" + read_excel(file)
        files_found += 1
        
    # البحث عن ملفات الوورد
    word_files = glob.glob("*.docx")
    for file in word_files:
        db_text += f"\n--- بيانات من {file} ---\n" + read_word(file)
        files_found += 1
        
    return db_text, files_found, excel_files + word_files

# واجهة المستخدم
st.title("🔍 نظام تحليل ومقارنة ملصقات المنتجات (AI Agent)")
st.markdown("يقوم هذا التطبيق بقراءة قاعدة البيانات المخزنة معه تلقائياً، ومقارنتها بصورة الملصق (Sticker) المرفوعة لاستخراج أي اختلافات.")

# القائمة الجانبية للإعدادات
st.sidebar.header("⚙️ الإعدادات")
api_key = st.sidebar.text_input("أدخل مفتاح Google Gemini API:", type="password", help="المفتاح المجاني من جوجل")
st.sidebar.markdown("---")

# تقسيم الشاشة إلى عمودين
col1, col2 = st.columns(2)

with col1:
    st.header("1️⃣ قاعدة البيانات (تلقائية)")
    
    with st.spinner("جاري البحث عن ملفات قاعدة البيانات..."):
        db_text, files_count, file_names = load_database()
    
    if files_count > 0:
        st.success(f"تم العثور على {files_count} ملفات بنجاح.")
        st.write("الملفات المقروءة:")
        for name in file_names:
            st.markdown(f"- `{name}`")
            
        with st.expander("عرض محتوى قاعدة البيانات المقروءة (للمراجعة)"):
            st.text(db_text)
    else:
        st.warning("⚠️ لم يتم العثور على أي ملفات Excel (.xlsx) أو Word (.docx) في مجلد التطبيق. يرجى رفع الملفات إلى GitHub.")

with col2:
    st.header("2️⃣ صورة الملصق (Sticker)")
    image_file = st.file_uploader("التقط أو ارفع صورة الملصق", type=['png', 'jpg', 'jpeg'])
    
    if image_file:
        st.image(image_file, caption="صورة الملصق المرفوعة", use_container_width=True)

st.markdown("---")

# زر بدء التحليل
if st.button("🚀 تحليل ومقارنة البيانات", type="primary"):
    if not api_key:
        st.error("يرجى إدخال مفتاح Google Gemini API في القائمة الجانبية أولاً.")
    elif files_count == 0 or db_text == "":
        st.error("لا توجد بيانات مقروءة للمقارنة بها. تأكد من وجود الملفات في السيرفر.")
    elif not image_file:
        st.error("يرجى التقاط أو رفع صورة الملصق (Sticker) أولاً.")
    else:
        with st.spinner("جاري تحليل الصورة ومقارنتها بقاعدة البيانات... يرجى الانتظار."):
            try:
                # إعداد جيميني
                genai.configure(api_key=api_key)
                
                # استخدام أحدث النماذج المتاحة من جوجل والتي تدعم الصور
                model = genai.GenerativeModel('gemini-2.5-flash')
                
                # تجهيز الصورة
                image = Image.open(image_file)
                
                # إعداد موجه الذكاء الاصطناعي (Prompt) ليخرج بنية واضحة
                prompt = f"""
                أنت مساعد ذكي متخصص في مراقبة الجودة.
                
                البيانات التالية هي قاعدة بيانات المنتجات المعتمدة للشركة:
                {db_text}
                
                المطلوب منك تحليل الصورة المرفقة للملصق (Sticker) ومقارنتها بقاعدة البيانات.
                عليك الرد **فقط** باستخدام التنسيق التالي (Markdown) لكي يتم تلوينه بشكل صحيح في التطبيق. لا تضف أي مقدمات أو خاتمات، استخدم فقط هذه الهيكلة:

                ### 📝 البيانات المستخرجة من الملصق:
                (اكتب هنا البيانات في شكل نقاط أو جدول)

                ### 🔍 نتيجة البحث في قاعدة البيانات:
                (اذكر هنا هل تم العثور على المنتج أم لا وبشكل مختصر جداً)

                ### 🟢 البيانات المتطابقة:
                (اذكر هنا الحقول التي تطابقت تماماً بين الملصق وقاعدة البيانات، استخدم نقاط)

                ### 🔴 الاختلافات والملاحظات:
                (إذا كان هناك أي اختلاف، اكتبه بوضوح هنا، مثلاً: "الوزن: في الملصق 500ج بينما في القاعدة 450ج". إذا لم يكن هناك اختلافات اكتب "لا يوجد اختلافات، البيانات متطابقة 100%")

                ### ⚠️ بيانات ناقصة أو غير موجودة:
                (اذكر أي بيانات موجودة في القاعدة ولكنها غائبة في الملصق، أو العكس)
                """
                
                # إرسال الطلب لجوجل جيميني
                response = model.generate_content([prompt, image])
                result_text = response.text
                
                st.success("✅ اكتمل التحليل بنجاح!")
                st.markdown("---")
                st.markdown("<h2 style='text-align: center; color: #1E88E5;'>📊 تقرير الجودة والمطابقة</h2>", unsafe_allow_html=True)
                
                # تقسيم الرد إلى أجزاء لتلوينها
                sections = result_text.split('###')
                
                for section in sections:
                    if not section.strip():
                        continue
                        
                    # تلوين وتنسيق كل قسم بناءً على عنوانه
                    if "البيانات المستخرجة" in section:
                        st.info(f"### {section.strip()}")
                    elif "نتيجة البحث" in section:
                        st.write(f"### {section.strip()}")
                    elif "البيانات المتطابقة" in section:
                        st.success(f"### {section.strip()}")
                    elif "الاختلافات" in section:
                        if "لا يوجد" in section or "متطابقة 100%" in section:
                            st.success(f"### {section.strip()}")
                        else:
                            st.error(f"### {section.strip()}")
                    elif "بيانات ناقصة" in section:
                        st.warning(f"### {section.strip()}")
                    else:
                        st.write(f"### {section.strip()}")
                
            except Exception as e:
                st.error(f"حدث خطأ أثناء الاتصال بالذكاء الاصطناعي: {e}")
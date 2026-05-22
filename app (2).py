import streamlit as st
import pandas as pd
import docx
from PIL import Image
import google.generativeai as genai
import os
import glob

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
                
                # استخدام النموذج المستقر المدعوم من جوجل حالياً
                model = genai.GenerativeModel('gemini-1.5-pro-latest')
                
                # تجهيز الصورة
                image = Image.open(image_file)
                
                # إعداد موجه الذكاء الاصطناعي (Prompt)
                prompt = f"""
                أنت مساعد ذكي متخصص في مراقبة الجودة.
                
                البيانات التالية هي قاعدة بيانات المنتجات المعتمدة للشركة:
                {db_text}
                
                المطلوب منك تحليل الصورة المرفقة للملصق (Sticker) والقيام بالآتي:
                1. استخراج جميع البيانات المكتوبة على الملصق في الصورة (مثل اسم المنتج، الوزن، المكونات، تاريخ الصلاحية، الباركود، إلخ).
                2. البحث عن هذا المنتج في قاعدة البيانات المرفقة أعلاه.
                3. إجراء مقارنة دقيقة بين البيانات الموجودة على الملصق والبيانات الموجودة في قاعدة البيانات.
                4. كتابة تقرير واضح باللغة العربية يوضح:
                   - البيانات التي تم استخراجها من الملصق.
                   - هل تم العثور على المنتج في قاعدة البيانات أم لا.
                   - **الاختلافات (إن وجدت):** اذكر بوضوح أي اختلاف بين الملصق وقاعدة البيانات (مثلاً: الوزن على الملصق 500 جرام بينما في القاعدة 450 جرام).
                   - إذا كانت البيانات متطابقة تماماً، اذكر ذلك بوضوح.
                """
                
                # إرسال الطلب لجوجل جيميني
                response = model.generate_content([prompt, image])
                
                st.success("✅ اكتمل التحليل!")
                st.markdown("### 📊 نتيجة المقارنة والتقرير:")
                st.info(response.text)
                
            except Exception as e:
                st.error(f"حدث خطأ أثناء الاتصال بالذكاء الاصطناعي: {e}")
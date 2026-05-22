import streamlit as st
import pandas as pd
import docx
import base64
from openai import OpenAI
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

def encode_image(image_file):
    return base64.b64encode(image_file.getvalue()).decode('utf-8')

# دالة لقراءة قاعدة البيانات تلقائياً من المجلد
@st.cache_data # نستخدم الكاش لعدم إعادة قراءة الملفات مع كل تفاعل في الصفحة
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
api_key = st.sidebar.text_input("أدخل مفتاح OpenAI API:", type="password", help="مطلوب لاستخدام نموذج الرؤية (GPT-4o)")
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
    # في الموبايل، سيظهر خيار التقاط صورة أو رفعها
    image_file = st.file_uploader("التقط أو ارفع صورة الملصق", type=['png', 'jpg', 'jpeg'])
    
    if image_file:
        st.image(image_file, caption="صورة الملصق المرفوعة", use_container_width=True)

st.markdown("---")

# زر بدء التحليل
if st.button("🚀 تحليل ومقارنة البيانات", type="primary"):
    if not api_key:
        st.error("يرجى إدخال مفتاح OpenAI API في القائمة الجانبية أولاً.")
    elif files_count == 0 or db_text == "":
        st.error("لا توجد بيانات مقروءة للمقارنة بها. تأكد من وجود الملفات في السيرفر.")
    elif not image_file:
        st.error("يرجى التقاط أو رفع صورة الملصق (Sticker) أولاً.")
    else:
        with st.spinner("جاري تحليل الصورة ومقارنتها بقاعدة البيانات... يرجى الانتظار."):
            try:
                client = OpenAI(api_key=api_key)
                base64_image = encode_image(image_file)
                
                # إعداد موجه الذكاء الاصطناعي (Prompt)
                prompt = f"""
                أنت مساعد ذكي متخصص في مراقبة الجودة.
                
                البيانات التالية هي قاعدة بيانات المنتجات المعتمدة للشركة:
                {db_text}
                
                والمرفق هو صورة لملصق (Sticker) منتج تم تصويره.
                
                المطلوب منك:
                1. استخراج جميع البيانات المكتوبة على الملصق في الصورة (مثل اسم المنتج، الوزن، المكونات، تاريخ الصلاحية، الباركود، إلخ).
                2. البحث عن هذا المنتج في قاعدة البيانات المرفقة أعلاه.
                3. إجراء مقارنة دقيقة بين البيانات الموجودة على الملصق والبيانات الموجودة في قاعدة البيانات.
                4. كتابة تقرير واضح باللغة العربية يوضح:
                   - البيانات التي تم استخراجها من الملصق.
                   - هل تم العثور على المنتج في قاعدة البيانات أم لا.
                   - **الاختلافات (إن وجدت):** اذكر بوضوح أي اختلاف بين الملصق وقاعدة البيانات (مثلاً: الوزن على الملصق 500 جرام بينما في القاعدة 450 جرام).
                   - إذا كانت البيانات متطابقة تماماً، اذكر ذلك بوضوح.
                """
                
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{base64_image}"
                                    }
                                }
                            ]
                        }
                    ],
                    max_tokens=1500,
                )
                
                result = response.choices[0].message.content
                
                st.success("✅ اكتمل التحليل!")
                st.markdown("### 📊 نتيجة المقارنة والتقرير:")
                st.info(result)
                
            except Exception as e:
                st.error(f"حدث خطأ أثناء الاتصال بالذكاء الاصطناعي: {e}")
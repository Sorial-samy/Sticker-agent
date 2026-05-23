import streamlit as st
import pandas as pd
import docx
from PIL import Image
import google.generativeai as genai
import os
import glob
import PyPDF2

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

def read_pdf(file_path):
    try:
        text = ""
        with open(file_path, "rb") as file:
            reader = PyPDF2.PdfReader(file)
            for page_num in range(len(reader.pages)):
                page = reader.pages[page_num]
                text += page.extract_text() + "\n"
        return text
    except Exception as e:
        return f"خطأ في قراءة الـ PDF ({file_path}): {e}"

# دالة لقراءة قاعدة البيانات تلقائياً من المجلد
@st.cache_data
def load_database():
    db_text = ""
    files_found = 0
    file_list = []
    
    # البحث عن ملفات الإكسيل
    excel_files = glob.glob("*.xlsx")
    for file in excel_files:
        db_text += f"\n--- بيانات من {file} ---\n" + read_excel(file)
        files_found += 1
        file_list.append(file)
        
    # البحث عن ملفات الوورد
    word_files = glob.glob("*.docx")
    for file in word_files:
        db_text += f"\n--- بيانات من {file} ---\n" + read_word(file)
        files_found += 1
        file_list.append(file)

    # البحث عن ملفات PDF
    pdf_files = glob.glob("*.pdf")
    for file in pdf_files:
        db_text += f"\n--- بيانات من {file} ---\n" + read_pdf(file)
        files_found += 1
        file_list.append(file)
        
    return db_text, files_found, file_list

# واجهة المستخدم
st.title("🔍 نظام تحليل ومقارنة ملصقات المنتجات (AI Agent)")
st.markdown("يقوم هذا التطبيق بقراءة قاعدة البيانات المخزنة معه تلقائياً، ومقارنتها بصور الملصقات (Stickers) المرفوعة لاستخراج أي اختلافات بجميع اللغات وبدقة فائقة.")

# القائمة الجانبية للإعدادات
st.sidebar.header("⚙️ الإعدادات")
api_key = st.sidebar.text_input("أدخل مفتاح Google Gemini API:", type="password", help="المفتاح المجاني من جوجل")
st.sidebar.markdown("---")

# تقسيم الشاشة إلى عمودين
col1, col2 = st.columns([1, 1.2])

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
        st.warning("⚠️ لم يتم العثور على أي ملفات في مجلد التطبيق. يرجى رفع الملفات إلى GitHub.")

with col2:
    st.header("2️⃣ صور الملصقات (Stickers)")
    # تعديل للسماح برفع أكثر من صورة
    image_files = st.file_uploader("التقط أو ارفع صورة/صور الملصقات (يمكنك تحديد أكثر من صورة)", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)
    
    if image_files:
        st.info(f"تم رفع {len(image_files)} صورة/صور جاهزة للتحليل.")
        # عرض الصور المصغرة
        cols = st.columns(min(len(image_files), 3))
        for idx, img in enumerate(image_files):
            cols[idx % 3].image(img, caption=img.name, use_container_width=True)

st.markdown("---")

# زر بدء التحليل
if st.button("🚀 تحليل ومقارنة جميع الملصقات", type="primary"):
    if not api_key:
        st.error("يرجى إدخال مفتاح Google Gemini API في القائمة الجانبية أولاً.")
    elif files_count == 0 or db_text == "":
        st.error("لا توجد بيانات مقروءة للمقارنة بها. تأكد من وجود الملفات في السيرفر.")
    elif not image_files:
        st.error("يرجى التقاط أو رفع صورة واحدة على الأقل للملصق (Sticker) أولاً.")
    else:
        # إعداد جيميني مرة واحدة
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        st.markdown("<h2 style='text-align: center; color: #1E88E5;'>📊 تقارير الجودة والمطابقة</h2>", unsafe_allow_html=True)
        
        # حلقة تكرارية للمرور على كل صورة وتحليلها
        for idx, image_file in enumerate(image_files):
            with st.container():
                st.markdown(f"### 🏷️ تقرير الملصق رقم {idx+1}: `{image_file.name}`")
                
                with st.spinner(f"جاري تحليل الملصق ({image_file.name})... يرجى الانتظار."):
                    try:
                        # تجهيز الصورة
                        image = Image.open(image_file)
                        
                        # إعداد موجه الذكاء الاصطناعي (Prompt) الصارم
                        prompt = f"""
                        أنت مفتش جودة صارم جداً ودقيق للغاية.
                        
                        البيانات التالية هي قاعدة بيانات المنتجات المعتمدة (تحتوي على الإكسيل، الوورد، وقوائم الباركود من الـ PDF):
                        {db_text}
                        
                        المطلوب منك تحليل الصورة المرفقة للملصق (Sticker) والتدقيق فيها بناءً على القواعد التالية:
                        1. **التدقيق متعدد اللغات (هام جداً):** يجب استخراج النصوص ومراجعتها بجميع اللغات الموجودة على الملصق (العربية، الإنجليزية، الفرنسية).
                        2. **أرقام الحقائق التغذوية (Nutritional Facts):** يجب التركيز بشكل قاطع على جدول القيمة الغذائية ومقارنة (السعرات، البروتين، الدهون، الكربوهيدرات، الصوديوم، وأي أرقام أخرى) رقماً برقماً.
                        3. **الباركود:** البحث عن الباركود الموجود في الملصق ومطابقته مع الباركود المذكور في قاعدة البيانات.
                        4. يجب مقارنة اسم المنتج، المكونات، الوزن، وتاريخ الصلاحية.

                        عليك الرد **فقط** باستخدام التنسيق التالي (Markdown). لا تضف أي مقدمات:

                        ### 📝 البيانات المستخرجة من الملصق:
                        (اكتب هنا البيانات المستخرجة مقسمة إلى: عربي، إنجليزي، فرنسي، جدول الحقائق التغذوية، والباركود)

                        ### 🔍 نتيجة البحث في قاعدة البيانات:
                        (هل تم العثور على المنتج في قاعدة البيانات أم لا؟)

                        ### 🟢 البيانات المتطابقة:
                        (اذكر الحقول واللغات وأرقام التغذية التي تطابقت تماماً بين الملصق وقاعدة البيانات)

                        ### 🔴 الاختلافات والملاحظات (مهم جداً):
                        (إذا كان هناك أي اختلاف في أي لغة، أو خطأ في أرقام الحقائق التغذوية، أو اختلاف في الباركود، اكتبه بوضوح هنا. مثلاً: "الترجمة الفرنسية ناقصة"، أو "البروتين في الملصق 5g بينما في القاعدة 6g". إذا لم يكن هناك اختلافات اكتب "لا يوجد اختلافات، جميع اللغات والأرقام متطابقة 100%")

                        ### ⚠️ بيانات ناقصة أو غير موجودة:
                        (هل هناك لغة مفقودة؟ هل جدول التغذية غير مكتمل؟)
                        """
                        
                        # إرسال الطلب
                        response = model.generate_content([prompt, image])
                        result_text = response.text
                        
                        # تقسيم الرد إلى أجزاء لتلوينها
                        sections = result_text.split('###')
                        
                        for section in sections:
                            if not section.strip():
                                continue
                                
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
                        st.error(f"حدث خطأ أثناء تحليل الصورة ({image_file.name}): {e}")
                
                # فاصل بين كل صورة والثانية
                st.markdown("---")

import streamlit as st
import pandas as pd
import docx
from PIL import Image
import google.generativeai as genai
import os
import glob
import PyPDF2
from datetime import datetime
import io

# إعدادات الصفحة
st.set_page_config(page_title="مقارن ملصقات المنتجات", page_icon="🔍", layout="wide")

# إنشاء ذاكرة التطبيق (لحفظ السجل)
if 'history' not in st.session_state:
    st.session_state.history = []

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
    
    excel_files = glob.glob("*.xlsx")
    for file in excel_files:
        db_text += f"\n--- بيانات من {file} ---\n" + read_excel(file)
        files_found += 1
        file_list.append(file)
        
    word_files = glob.glob("*.docx")
    for file in word_files:
        db_text += f"\n--- بيانات من {file} ---\n" + read_word(file)
        files_found += 1
        file_list.append(file)

    pdf_files = glob.glob("*.pdf")
    for file in pdf_files:
        db_text += f"\n--- بيانات من {file} ---\n" + read_pdf(file)
        files_found += 1
        file_list.append(file)
        
    return db_text, files_found, file_list

# واجهة المستخدم
st.title("🔍 نظام تحليل ومقارنة ملصقات المنتجات (AI Agent)")

# تقسيم التطبيق إلى تبويبات (Tabs)
tab1, tab2 = st.tabs(["🚀 الفحص والتحليل", "📂 سجل الفحوصات والتقارير"])

with tab1:
    st.markdown("يقوم هذا التطبيق بقراءة قاعدة البيانات المخزنة معه تلقائياً، ومقارنتها بصور الملصقات المرفوعة لاستخراج أي اختلافات.")

    # القائمة الجانبية للإعدادات
    st.sidebar.header("⚙️ الإعدادات")
    api_key = st.sidebar.text_input("أدخل مفتاح Google Gemini API:", type="password", help="المفتاح المجاني من جوجل")
    st.sidebar.markdown("---")

    col1, col2 = st.columns([1, 1.2])

    with col1:
        st.header("1️⃣ قاعدة البيانات")
        with st.spinner("جاري البحث عن ملفات قاعدة البيانات..."):
            db_text, files_count, file_names = load_database()
        
        if files_count > 0:
            st.success(f"تم العثور على {files_count} ملفات.")
            with st.expander("عرض الملفات المقروءة"):
                for name in file_names:
                    st.markdown(f"- `{name}`")
        else:
            st.warning("⚠️ لم يتم العثور على أي ملفات في مجلد التطبيق. يرجى رفع الملفات إلى GitHub.")

    with col2:
        st.header("2️⃣ صور الملصقات (Stickers)")
        image_files = st.file_uploader("التقط أو ارفع صورة/صور الملصقات", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)
        
        if image_files:
            st.info(f"تم رفع {len(image_files)} صورة/صور جاهزة للتحليل.")

    st.markdown("---")

    # زر بدء التحليل
    if st.button("🚀 تحليل ومقارنة جميع الملصقات", type="primary"):
        if not api_key:
            st.error("يرجى إدخال مفتاح Google Gemini API في القائمة الجانبية أولاً.")
        elif files_count == 0 or db_text == "":
            st.error("لا توجد بيانات للمقارنة بها.")
        elif not image_files:
            st.error("يرجى رفع صورة واحدة على الأقل.")
        else:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.5-flash')
            
            st.markdown("<h2 style='text-align: center; color: #1E88E5;'>📊 تقارير الجودة والمطابقة</h2>", unsafe_allow_html=True)
            
            for idx, image_file in enumerate(image_files):
                with st.container():
                    st.markdown(f"### 🏷️ تقرير الملصق رقم {idx+1}: `{image_file.name}`")
                    
                    with st.spinner(f"جاري تحليل الملصق ({image_file.name})... يرجى الانتظار."):
                        try:
                            # ضغط الصورة لتجنب الكراش
                            image = Image.open(image_file)
                            image.thumbnail((1600, 1600)) # تصغير الحجم للحفاظ على الذاكرة
                            
                            prompt = f"""
                            أنت مفتش جودة صارم جداً ودقيق للغاية.
                            
                            البيانات التالية هي قاعدة بيانات المنتجات المعتمدة:
                            {db_text}
                            
                            المطلوب منك تحليل الصورة المرفقة للملصق والتدقيق فيها:
                            1. **التدقيق متعدد اللغات:** استخراج النصوص ومراجعتها بجميع اللغات الموجودة (العربية، الإنجليزية، الفرنسية).
                            2. **أرقام الحقائق التغذوية:** مقارنة جدول القيمة الغذائية (السعرات، البروتين، الدهون، وغيرها) رقماً برقماً.
                            3. **الباركود:** البحث عن الباركود في الملصق ومطابقته بقاعدة البيانات.
                            4. مقارنة اسم المنتج، المكونات، الوزن، وتاريخ الصلاحية.

                            عليك الرد **فقط** باستخدام التنسيق التالي (Markdown):

                            ### 📝 البيانات المستخرجة:
                            (اكتب البيانات المستخرجة مقسمة إلى: اللغات، جدول الحقائق التغذوية، والباركود)

                            ### 🔍 نتيجة البحث:
                            (هل تم العثور على المنتج في قاعدة البيانات أم لا؟)

                            ### 🟢 المتطابق:
                            (اذكر الحقول التي تطابقت تماماً)

                            ### 🔴 الاختلافات والملاحظات:
                            (إذا كان هناك أي اختلاف في أي لغة، أو خطأ في أرقام الحقائق التغذوية، أو اختلاف في الباركود، اكتبه بوضوح هنا. إذا لم يكن هناك اختلافات اكتب "لا يوجد اختلافات، جميع البيانات متطابقة 100%")

                            ### ⚠️ بيانات ناقصة:
                            (هل هناك لغة أو بيان مفقود؟)
                            """
                            
                            response = model.generate_content([prompt, image])
                            result_text = response.text
                            
                            # حفظ النتيجة في الذاكرة (السجل)
                            st.session_state.history.append({
                                "التاريخ والوقت": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "اسم الملصق": image_file.name,
                                "التقرير والنتيجة": result_text
                            })
                            
                            sections = result_text.split('###')
                            for section in sections:
                                if not section.strip(): continue
                                if "البيانات المستخرجة" in section: st.info(f"### {section.strip()}")
                                elif "نتيجة البحث" in section: st.write(f"### {section.strip()}")
                                elif "المتطابق" in section: st.success(f"### {section.strip()}")
                                elif "الاختلافات" in section:
                                    if "لا يوجد" in section or "متطابقة 100%" in section: st.success(f"### {section.strip()}")
                                    else: st.error(f"### {section.strip()}")
                                elif "بيانات ناقصة" in section: st.warning(f"### {section.strip()}")
                                else: st.write(f"### {section.strip()}")
                            
                        except Exception as e:
                            st.error(f"حدث خطأ أثناء تحليل الصورة ({image_file.name}): {e}")
                    
                    st.markdown("---")

with tab2:
    st.header("📂 سجل الفحوصات والتقارير المحفوظة")
    st.markdown("يتم هنا حفظ جميع الاستيكرات التي تم فحصها خلال هذه الجلسة. يمكنك مراجعتها أو تحميلها كملف إكسيل (Excel).")
    
    if len(st.session_state.history) == 0:
        st.info("السجل فارغ حالياً. قم بفحص بعض الاستيكرات أولاً لتظهر هنا.")
    else:
        # تحويل السجل إلى جدول
        history_df = pd.DataFrame(st.session_state.history)
        
        # عرض الجدول
        st.dataframe(history_df)
        
        # إنشاء زر لتحميل السجل كملف Excel
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            history_df.to_excel(writer, index=False, sheet_name='سجل الجودة')
        excel_data = output.getvalue()
        
        st.download_button(
            label="📥 تحميل سجل الفحوصات (Excel)",
            data=excel_data,
            file_name=f"Quality_Report_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary"
        )
        
        # زر لمسح السجل
        if st.button("🗑️ مسح السجل الحالي"):
            st.session_state.history = []
            st.rerun()
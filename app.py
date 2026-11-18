import streamlit as st
import pandas as pd
import sqlite3
import os

st.set_page_config(page_title="السلوك المتميز", page_icon="⭐", layout="wide")

# مجلد لحفظ الشواهد المرفوعة (صور، فيديوهات، ملفات)
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# إعداد قاعدة البيانات
conn = sqlite3.connect('behavior_system.db', check_same_thread=False)
c = conn.cursor()

c.execute('''
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        classroom TEXT
    )
''')

c.execute('''
    CREATE TABLE IF NOT EXISTS records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_name TEXT,
        classroom TEXT,
        behavior TEXT,
        points INTEGER,
        date TEXT,
        evidence_file TEXT
    )
''')
conn.commit()

st.title("⭐ نظام متابعة وتوثيق السلوك المتميز")
st.markdown("---")

menu = ["استيراد الطالبات (Excel)", "رصد الشواهد والدرجات والشواهد", "عرض السجلات والتقارير"]
choice = st.sidebar.selectbox("القائمة الرئيسية", menu)

if choice == "استيراد الطالبات (Excel)":
    st.subheader("📁 استيراد بيانات الطالبات من ملف Excel")
    st.info("يجب أن يحتوي ملف الإكسل على عمودين باسم: (اسم الطالبة) و (الفصل)")
    
    uploaded_file = st.file_uploader("اختر ملف الإكسل (.xlsx)", type=["xlsx"])
    
    if uploaded_file is not None:
        try:
            df = pd.read_excel(uploaded_file)
            st.write("معاينة البيانات المستوردة:", df.head())
            
            if st.button("حفظ الطالبات في قاعدة البيانات"):
                if 'اسم الطالبة' in df.columns and 'الفصل' in df.columns:
                    count = 0
                    for _, row in df.iterrows():
                        name = str(row['اسم الطالبة']).strip()
                        classroom = str(row['الفصل']).strip()
                        if name and name != 'nan':
                            c.execute("INSERT INTO students (name, classroom) VALUES (?, ?)", (name, classroom))
                            count += 1
                    conn.commit()
                    st.success(f"تم استيراد {count} طالبة بنجاح!")
                else:
                    st.error("تأكد أن أسماء الأعمدة في ملف الإكسل مطابقة تماماً لـ: 'اسم الطالبة' و 'الفصل'")
        except Exception as e:
            st.error(f"حدث خطأ أثناء قراءة الملف: {e}")

elif choice == "رصد الشواهد والدرجات والشواهد":
    st.subheader("📝 رصد السلوك المتميز وإرفاق الشاهد (صور، فيديو، PDF)")
    
    c.execute("SELECT DISTINCT name, classroom FROM students")
    students = c.fetchall()
    
    if not students:
        st.warning("لا توجد طالبات مسجلات. يرجى استيراد القائمة من تبويب 'استيراد الطالبات' أولاً.")
    else:
        student_dict = {f"{s[0]} ({s[1]})": s for s in students}
        selected_student_str = st.selectbox("اختر الطالبة", list(student_dict.keys()))
        
        selected_student = student_dict[selected_student_str]
        student_name = selected_student[0]
        classroom = selected_student[1]
        
        # التحقق من مجموع الدرجات التراكمي للطالبة (الحد الأقصى 20)
        c.execute("SELECT SUM(points) FROM records WHERE student_name=?", (student_name,))
        res = c.fetchone()[0]
        current_total = res if res else 0
        
        st.info(f"📌 مجموع الدرجات التراكمي الحالي للطالبة: **{current_total} / 20** درجة")
        
        behavior_desc = st.text_area("وصف الشاهد أو السلوك المتميز")
        
        remaining_allowed = max(0, 20 - current_total)
        points = st.number_input(
            f"الدرجات المضافة (الحد الأقصى المتبقي: {remaining_allowed} درجة)",
            min_value=1,
            max_value=max(1, remaining_allowed),
            value=min(5, max(1, remaining_allowed))
        )
        
        date_str = st.date_input("تاريخ الرصد")
        
        # خانة رفع الشواهد (صور، فيديو، مستندات)
        evidence = st.file_uploader("إرفاق شاهد (صورة، فيديو، أو ملف PDF)", type=["png", "jpg", "jpeg", "mp4", "pdf", "mov"])
        
        if st.button("حفظ الرصد والشاهد"):
            if current_total >= 20:
                st.error("⚠️ لقد وصلت هذه الطالبة إلى الحد الأقصى التراكمي (20 درجة) ولا يمكن إضافة درجات أخرى.")
            elif current_total + points > 20:
                st.error(f"⚠️ عذراً، مجموع درجات الطالبة سيتجاوز الحد الأقصى (20 درجة). المتبقي لها فقط {remaining_allowed} درجات.")
            elif behavior_desc:
                file_path = ""
                if evidence is not None:
                    file_path = os.path.join(UPLOAD_DIR, evidence.name)
                    with open(file_path, "wb") as f:
                        f.write(evidence.getbuffer())
                
                c.execute("INSERT INTO records (student_name, classroom, behavior, points, date, evidence_file) VALUES (?, ?, ?, ?, ?, ?)",
                          (student_name, classroom, behavior_desc, points, str(date_str), file_path))
                conn.commit()
                st.success(f"تم حفظ الرصد والشاهد للطالبة {student_name} بنجاح!")
            else:
                st.warning("الرجاء كتابة وصف الشاهد.")

elif choice == "عرض السجلات والتقارير":
    st.subheader("📊 سجلات الشواهد والتقارير")
    
    c.execute("SELECT student_name, classroom, behavior, points, date, evidence_file FROM records")
    records = c.fetchall()
    
    if records:
        df_records = pd.DataFrame(records, columns=["اسم الطالبة", "الفصل", "وصف الشاهد", "الدرجات", "التاريخ", "ملف الشاهد"])
        st.dataframe(df_records, use_container_width=True)
        
        csv = df_records.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 تحميل التقرير كملف Excel / CSV",
            data=csv,
            file_name='behavior_report.csv',
            mime='text/csv',
        )
    else:
        st.info("لا توجد سجلات مرصودة حتى الآن.")

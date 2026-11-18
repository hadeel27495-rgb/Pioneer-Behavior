import streamlit as st
import pandas as pd
import sqlite3

st.set_page_config(page_title="السلوك المتميز", page_icon="⭐", layout="wide")

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
        date TEXT
    )
''')
conn.commit()

st.title("⭐ نظام متابعة وتوثيق السلوك المتميز")
st.markdown("---")

menu = ["استيراد الطالبات (Excel)", "رصد الشواهد والدرجات", "عرض السجلات والتقارير"]
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

elif choice == "رصد الشواهد والدرجات":
    st.subheader("📝 رصد الشواهد والدرجات")
    
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
        
        behavior_desc = st.text_area("وصف الشاهد أو السلوك المتميز")
        points = st.number_input("الدرجات المضافة (الحد الأقصى التراكمي 20 درجة)", min_value=1, max_value=20, value=5)
        date_str = st.date_input("تاريخ الرصد")
        
        if st.button("حفظ الرصد"):
            if behavior_desc:
                c.execute("INSERT INTO records (student_name, classroom, behavior, points, date) VALUES (?, ?, ?, ?, ?)",
                          (student_name, classroom, behavior_desc, points, str(date_str)))
                conn.commit()
                st.success(f"تم حفظ الشاهد للطالبة {student_name} بنجاح!")
            else:
                st.warning("الرجاء كتابة وصف الشاهد.")

elif choice == "عرض السجلات والتقارير":
    st.subheader("📊 سجلات الشواهد والتقارير")
    
    c.execute("SELECT student_name, classroom, behavior, points, date FROM records")
    records = c.fetchall()
    
    if records:
        df_records = pd.DataFrame(records, columns=["اسم الطالبة", "الفصل", "وصف الشاهد", "الدرجات", "التاريخ"])
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

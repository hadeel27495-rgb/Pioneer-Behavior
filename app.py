import streamlit as st
import pandas as pd
import sqlite3
import os

st.set_page_config(page_title="السلوك المتميز", page_icon="⭐", layout="wide")

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

# تحديث الجدول ليشمل اسم الراصد
c.execute('''
    CREATE TABLE IF NOT EXISTS records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_name TEXT,
        classroom TEXT,
        behavior TEXT,
        points INTEGER,
        date TEXT,
        observer_name TEXT,
        evidence_file TEXT
    )
''')
conn.commit()

# جدول بنود السلوك المعتمدة ودرجاتها
BEHAVIOR_RULES = {
    "انضباط الطالب وعدم غيابه بدون عذر خلال الفصل الدراسي.": 2,
    "المشاركة في أنشطة مهارة إدارة الوقت.": 4,
    "تقديم مقترح لصالح المجتمع المدرسي.": 2,
    "الالتحاق ببرنامج أو دورة.": 6,
    "المشاركة في أنشطة المهارات الرقمية.": 4,
    "المشاركة في الخدمة المجتمعية خارج المدرسة.": 6,
    "المشاركة في أنشطة القيادة والمسؤولية.": 4,
    "كتابة رسالة شكر (للوطن، للقيادة الرشيدة، للمعلم...إلخ)": 2,
    "تقديم فعالية حوارية.": 6,
    "المشاركة في حملة توعوية.": 6,
    "عرض تجارب شخصية ناجحة.": 6,
    "المشاركة في أنشطة مهارات الاتصال.": 4,
    "المشاركة في الإذاعة.": 2,
    "متميز": 4,
    "أخرى (بناءً على توصية لجنة التوجيه الطلابي).": 6
}

st.title("⭐ نظام متابعة وتوثيق السلوك المتميز")
st.markdown("---")

menu = ["استيراد الطالبات (Excel)", "رصد الشواهد والدرجات", "عرض السجلات والتقارير والشواهد المرئية"]
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
    st.subheader("📝 اختيار بند السلوك ورصد الشاهد المرئي")
    
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
        
        # فحص مجموع الدرجات التراكمي (الحد الأقصى 20)
        c.execute("SELECT SUM(points) FROM records WHERE student_name=?", (student_name,))
        res = c.fetchone()[0]
        current_total = res if res else 0
        
        st.info(f"📌 مجموع الدرجات التراكمي الحالي للطالبة: **{current_total} / 20** درجة")
        
        selected_behavior = st.selectbox("اختر بند السلوك المتميز", list(BEHAVIOR_RULES.keys()))
        auto_points = BEHAVIOR_RULES[selected_behavior]
        
        st.success(f"🎯 الدرجة المقررة لهذا البند تلقائياً: **{auto_points} درجات**")
        
        date_str = st.date_input("تاريخ الرصد")
        
        # خانة اسم الراصد (المعلم / الوكيل / الإداري)
        observer_name = st.text_input("اسم الراصد (المعلم / الوكيل / الإداري المسؤول)")
        
        evidence = st.file_uploader("إرفاق شاهد مرئي (صورة، فيديو، أو ملف PDF)", type=["png", "jpg", "jpeg", "mp4", "pdf", "mov"])
        
        if st.button("حفظ الرصد والشاهد المرئي"):
            if not observer_name.strip():
                st.warning("الرجاء إدخال اسم الراصد (المعلم / الوكيل / الإداري).")
            elif current_total >= 20:
                st.error("⚠️ لقد وصلت هذه الطالبة إلى الحد الأقصى التراكمي (20 درجة) ولا يمكن إضافة درجات أخرى.")
            elif current_total + auto_points > 20:
                st.error(f"⚠️ عذراً، إضافة {auto_points} درجات سيتجاوز الحد الأقصى التراكمي (20 درجة). المتبقي للطالبة هو {20 - current_total} درجات فقط.")
            else:
                file_path = ""
                if evidence is not None:
                    file_path = os.path.join(UPLOAD_DIR, evidence.name)
                    with open(file_path, "wb") as f:
                        f.write(evidence.getbuffer())
                
                c.execute("INSERT INTO records (student_name, classroom, behavior, points, date, observer_name, evidence_file) VALUES (?, ?, ?, ?, ?, ?, ?)",
                          (student_name, classroom, selected_behavior, auto_points, str(date_str), observer_name, file_path))
                conn.commit()
                st.success(f"تم حفظ السلوك ورصد الشاهد المرئي للطالبة {student_name} بنجاح!")

elif choice == "عرض السجلات والتقارير والشواهد المرئية":
    st.subheader("📊 سجلات الطالبات وعرض الشواهد المرئية المباشرة")
    
    c.execute("SELECT id, student_name, classroom, behavior, points, date, observer_name, evidence_file FROM records")
    records = c.fetchall()
    
    if records:
        for rec in records:
            rec_id, s_name, s_class, s_beh, s_pts, s_date, s_observer, s_file = rec
            observer_display = s_observer if s_observer else "غير محدد"
            with st.expander(f"الطالبة: {s_name} ({s_class}) - البند: {s_beh} ({s_pts} درجات)"):
                st.write(f"📅 **تاريخ الرصد:** {s_date}")
                st.write(f"👤 **الراصد / المسؤول:** {observer_display}")
                st.write(f"⭐ **الدرجات:** {s_pts}")
                
                if s_file and os.path.exists(s_file):
                    st.write("📎 **الشاهد المرئي المرفق:**")
                    if s_file.lower().endswith(('.png', '.jpg', '.jpeg')):
                        st.image(s_file, caption=s_name, use_container_width=True)
                    elif s_file.lower().endswith(('.mp4', '.mov')):
                        st.video(s_file)
                    else:
                        with open(s_file, "rb") as f:
                            st.download_button(
                                label="📥 تحميل ملف الشاهد (PDF / مستند)",
                                data=f,
                                file_name=os.path.basename(s_file),
                                key=f"dl_{rec_id}"
                            )
                else:
                    st.info("لا يوجد شاهد مرئي مرفق مع هذا الرصد.")
                
                if st.button(f"🗑️ حذف هذا السجل", key=f"del_{rec_id}"):
                    c.execute("DELETE FROM records WHERE id=?", (rec_id,))
                    conn.commit()
                    st.success("تم حذف السجل بنجاح! قم بتحديث الصفحة.")
                    st.rerun()
        
        st.markdown("---")
        df_records = pd.DataFrame(records, columns=["ID", "اسم الطالبة", "الفصل", "بند السلوك", "الدرجات", "التاريخ", "الراصد", "ملف الشاهد"])
        csv = df_records.drop(columns=["ID"]).to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 تحميل جدول التقارير كملف Excel / CSV",
            data=csv,
            file_name='behavior_report.csv',
            mime='text/csv',
        )
    else:
        st.info("لا توجد سجلات مرصودة حتى الآن.")

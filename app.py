import streamlit as st
import pandas as pd
import sqlite3
import os

st.set_page_config(
    page_title="نظام السلوك المتميز العصري",
    page_icon="⭐",
    layout="wide"
)

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

# القائمة الجانبية مع شعار المملكة الرسمي المضمون
st.sidebar.markdown("### 🇸🇦 وزارة التعليم")
st.sidebar.markdown("### 🎓 إدارة النظام")
menu = ["📊 لوحة التحكم", "📁 استيراد الطالبات", "📝 رصد الشواهد", "📋 بطاقات الطالبات والتقارير"]
choice = st.sidebar.radio("التنقل السريع", menu)

st.sidebar.markdown("---")
st.sidebar.info("⭐ **نظام السلوك المتميز**\nنسخة الأعمال الاحترافية v3.3")

# --- 1. لوحة التحكم ---
if choice == "📊 لوحة التحكم":
    st.markdown("### 🇸🇦 المملكة العربية السعودية - وزارة التعليم")
    st.title("🌟 لوحة التحكم الرئيسية")
    st.markdown("نظام توثيق ومتابعة السلوك المتميز والمعزز للانضباط المدرسي.")
    st.markdown("---")
    
    c.execute("SELECT COUNT(*) FROM students")
    total_students = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM records")
    total_records = c.fetchone()[0]
    
    c.execute("SELECT SUM(points) FROM records")
    res_pts = c.fetchone()[0]
    total_points = res_pts if res_pts else 0
    
    # بطاقات الإحصائيات متجاورة وأفقية بشكل جميل
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(label="👥 إجمالي الطالبات", value=total_students)
    with col2:
        st.metric(label="🏆 إجمالي الشواهد", value=total_records)
    with col3:
        st.metric(label="⭐ مجموع الدرجات", value=total_points)

# --- 2. استيراد الطالبات ---
elif choice == "📁 استيراد الطالبات":
    st.title("📁 استيراد بيانات الطالبات من ملف Excel")
    st.markdown("---")
    
    uploaded_file = st.file_uploader("اختر ملف الإكسل (.xlsx)", type=["xlsx"])
    
    if uploaded_file is not None:
        try:
            df = pd.read_excel(uploaded_file)
            st.write("📋 **معاينة البيانات المستوردة:**", df.head())
            
            if st.button("🚀 حفظ واعتماد الطالبات في النظام"):
                if 'اسم الطالبة' in df.columns and 'الفصل' in df.columns:
                    count = 0
                    for _, row in df.iterrows():
                        name = str(row['اسم الطالبة']).strip()
                        classroom = str(row['الفصل']).strip()
                        if name and name != 'nan':
                            c.execute("INSERT INTO students (name, classroom) VALUES (?, ?)", (name, classroom))
                            count += 1
                    conn.commit()
                    st.success(f"🎉 تم استيراد وحفظ {count} طالبة بنجاح تام!")
                else:
                    st.error("⚠️ تأكد أن أسماء الأعمدة في ملف الإكسل هي: 'اسم الطالبة' و 'الفصل'")
        except Exception as e:
            st.error(f"حدث خطأ أثناء قراءة الملف: {e}")

# --- 3. رصد الشواهد والدرجات ---
elif choice == "📝 رصد الشواهد":
    st.title("📝 رصد الشواهد والسلوك المتميز")
    st.markdown("---")
    
    c.execute("SELECT DISTINCT name, classroom FROM students")
    students = c.fetchall()
    
    if not students:
        st.warning("⚠️ لا توجد طالبات مسجلات. يرجى استيراد القائمة أولاً.")
    else:
        student_dict = {f"{s[0]} ({s[1]})": s for s in students}
        selected_student_str = st.selectbox("🎯 اختر الطالبة المستهدفة", list(student_dict.keys()))
        
        selected_student = student_dict[selected_student_str]
        student_name = selected_student[0]
        classroom = selected_student[1]
        
        c.execute("SELECT SUM(points) FROM records WHERE student_name=?", (student_name,))
        res = c.fetchone()[0]
        current_total = res if res else 0
        
        st.markdown(f"**مجموع الدرجات التراكمي الحالي للطالبة: {current_total} / 20 درجة**")
        st.progress(min(current_total / 20.0, 1.0))
        
        selected_behavior = st.selectbox("📌 اختر بند السلوك المتميز", list(BEHAVIOR_RULES.keys()))
        auto_points = BEHAVIOR_RULES[selected_behavior]
        
        st.info(f"⭐ **الدرجة المقررة لهذا البند تلقائياً:** {auto_points} درجات")
        
        col_date, col_obs = st.columns(2)
        with col_date:
            date_str = st.date_input("📅 تاريخ الرصد")
        with col_obs:
            observer_name = st.text_input("👤 اسم الراصد (المعلم / الوكيل / الإداري)")
        
        evidence = st.file_uploader("📎 إرفاق شاهد مرئي (صورة، فيديو، أو مستند PDF)", type=["png", "jpg", "jpeg", "mp4", "pdf", "mov"])
        
        st.markdown("")
        if st.button("💾 حفظ الاعتماد والرصد المرئي", use_container_width=True):
            if not observer_name.strip():
                st.warning("⚠️ الرجاء إدخال اسم الراصد.")
            elif current_total >= 20:
                st.error("⚠️ لقد وصلت هذه الطالبة إلى الحد الأقصى التراكمي (20 درجة).")
            elif current_total + auto_points > 20:
                st.error(f"⚠️ عذراً، الإضافة ستتجاوز 20 درجة. المتبقي للطالبة {20 - current_total} درجات فقط.")
            else:
                file_path = ""
                if evidence is not None:
                    file_path = os.path.join(UPLOAD_DIR, evidence.name)
                    with open(file_path, "wb") as f:
                        f.write(evidence.getbuffer())
                
                c.execute("INSERT INTO records (student_name, classroom, behavior, points, date, observer_name, evidence_file) VALUES (?, ?, ?, ?, ?, ?, ?)",
                          (student_name, classroom, selected_behavior, auto_points, str(date_str), observer_name, file_path))
                conn.commit()
                st.success(f"🎉 تم حفظ السلوك للطالبة {student_name} بنجاح!")

# --- 4. بطاقات الطالبات والتقارير ---
elif choice == "📋 بطاقات الطالبات والتقارير":
    st.title("📋 بطاقات الطالبات والأعمال التراكمية (من 20 درجة)")
    st.markdown("كل طالبة لها بطاقة خاصة بها تجمع إجمالي درجاتها وجميع شواهدها وأعمالها المرئية.")
    st.markdown("---")
    
    c.execute("SELECT DISTINCT student_name, classroom FROM records")
    active_students = c.fetchall()
    
    if not active_students:
        st.info("𭕀 لا توجد شواهد مرصودة للطالبات حتى الآن.")
    else:
        for s_name, s_class in active_students:
            c.execute("SELECT SUM(points) FROM records WHERE student_name=?", (s_name,))
            total_p = c.fetchone()[0]
            total_p = total_p if total_p else 0
            
            c.execute("SELECT id, behavior, points, date, observer_name, evidence_file FROM records WHERE student_name=?", (s_name,))
            student_records = c.fetchall()
            
            with st.expander(f"🎓 الطالبة: {s_name} | الفصل: {s_class} | ⭐ المجموع التراكمي: {total_p} / 20 درجة"):
                st.markdown(f"### سجل أعمال ومتميزات الطالبة: {s_name}")
                st.progress(min(total_p / 20.0, 1.0))
                st.markdown("---")
                
                for idx, rec in enumerate(student_records, 1):
                    rec_id, s_beh, s_pts, s_date, s_observer, s_file = rec
                    st.markdown(f"#### رصد رقم ({idx}) - {s_beh}")
                    st.write(f"⭐ **الدرجة الممنوحة:** {s_pts} درجات | 📅 **التاريخ:** {s_date} | 👤 **الراصد:** {s_observer}")
                    
                    if s_file and os.path.exists(s_file):
                        if s_file.lower().endswith(('.png', '.jpg', '.jpeg')):
                            st.image(s_file, caption=s_name, use_container_width=True)
                        elif s_file.lower().endswith(('.mp4', '.mov')):
                            st.video(s_file)
                        else:
                            with open(s_file, "rb") as f:
                                st.download_button(
                                    label="📥 تحميل ملف الشاهد المرفق",
                                    data=f,
                                    file_name=os.path.basename(s_file),
                                    key=f"dl_{rec_id}"
                                )
                    else:
                        st.text("لا يوجد شاهد مرئي مرفق مع هذا البند.")
                    
                    if st.button(f"🗑️ حذف هذا البند للطالبة {s_name}", key=f"del_{rec_id}"):
                        c.execute("DELETE FROM records WHERE id=?", (rec_id,))
                        conn.commit()
                        st.success("تم الحذف بنجاح!")
                        st.rerun()
                    st.markdown("---")
        
        st.markdown("---")
        c.execute("SELECT student_name, classroom, behavior, points, date, observer_name FROM records")
        all_data = c.fetchall()
        df_records = pd.DataFrame(all_data, columns=["اسم الطالبة", "الفصل", "بند السلوك", "الدرجات", "التاريخ", "الراصد"])
        csv = df_records.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 تحميل تقارير النظام كاملة كملف Excel / CSV",
            data=csv,
            file_name='behavior_cards_report.csv',
            mime='text/csv',
        )

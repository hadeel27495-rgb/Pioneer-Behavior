import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime
from fpdf import FPDF
import arabic_reshaper
from bidi.algorithm import get_display

# ---------------------------------------------------------
# 1. إعدادات الصفحة والتخزين
# ---------------------------------------------------------
st.set_page_config(page_title="نظام السلوك المتميز", layout="wide", page_icon="🌟")

UPLOAD_DIR = "evidences_files"
FONT_PATH = "Amiri-Regular.ttf"  # تأكد من وجود خط عربي يدعم UTF-8 بجانب الملف
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ---------------------------------------------------------
# 2. إعداد قاعدة البيانات (SQLite)
# ---------------------------------------------------------
def init_db():
    conn = sqlite3.connect("behavior_system.db", check_same_thread=False)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            classroom TEXT NOT NULL,
            UNIQUE(name, classroom)
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS evidences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            title TEXT NOT NULL,
            points REAL NOT NULL,
            file_path TEXT,
            file_type TEXT,
            created_at TEXT,
            FOREIGN KEY(student_id) REFERENCES students(id)
        )
    """)
    conn.commit()
    return conn

conn = init_db()

# ---------------------------------------------------------
# 3. دوال معالجة اللغة العربية وتوليد PDF
# ---------------------------------------------------------
def ar(text):
    if not text:
        return ""
    reshaped_text = arabic_reshaper.reshape(str(text))
    return get_display(reshaped_text)

class ArabicPDF(FPDF):
    def header(self):
        if os.path.exists(FONT_PATH):
            self.add_font("Arabic", "", FONT_PATH, uni=True)
            self.set_font("Arabic", "", 16)
        else:
            self.set_font("Arial", "B", 16)
        self.cell(0, 12, ar("برنامج السلوك المتميز - متوسطة طويق الأولى"), ln=True, align="C")
        self.ln(5)

def generate_student_pdf(student_name, classroom, total_score, evidences_df):
    pdf = ArabicPDF()
    pdf.add_page()
    if os.path.exists(FONT_PATH):
        pdf.add_font("Arabic", "", FONT_PATH, uni=True)
        pdf.set_font("Arabic", "", 13)
    else:
        pdf.set_font("Arial", "", 12)

    pdf.cell(0, 10, ar(f"تقرير السلوك المتميز للطالبة: {student_name}"), ln=True, align="R")
    pdf.cell(0, 10, ar(f"الفصل الدراسي: {classroom}"), ln=True, align="R")
    pdf.cell(0, 10, ar(f"الدرجة النهائية المكتسبة: {min(total_score, 20)} من 20"), ln=True, align="R")
    pdf.ln(8)

    # رأس الجدول
    pdf.set_fill_color(41, 128, 185)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(40, 10, ar("التاريخ"), 1, 0, "C", True)
    pdf.cell(35, 10, ar("الدرجة"), 1, 0, "C", True)
    pdf.cell(35, 10, ar("نوع الشاهد"), 1, 0, "C", True)
    pdf.cell(80, 10, ar("وصف الشاهد / المبادرة"), 1, 1, "C", True)

    # بيانات الشواهد
    pdf.set_text_color(0, 0, 0)
    for _, row in evidences_df.iterrows():
        pdf.cell(40, 10, ar(row["created_at"]), 1, 0, "C")
        pdf.cell(35, 10, ar(str(row["points"])), 1, 0, "C")
        pdf.cell(35, 10, ar(row["file_type"]), 1, 0, "C")
        pdf.cell(80, 10, ar(row["title"]), 1, 1, "R")

    return pdf.output(dest="S").encode("latin1")

def generate_class_pdf(classroom, summary_df):
    pdf = ArabicPDF()
    pdf.add_page()
    if os.path.exists(FONT_PATH):
        pdf.add_font("Arabic", "", FONT_PATH, uni=True)
        pdf.set_font("Arabic", "", 13)
    else:
        pdf.set_font("Arial", "", 12)

    pdf.cell(0, 10, ar(f"التقرير الإجمالي للسلوك المتميز - فصل: {classroom}"), ln=True, align="C")
    pdf.ln(5)

    # رأس الجدول
    pdf.set_fill_color(39, 174, 96)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(40, 10, ar("الدرجة (من 20)"), 1, 0, "C", True)
    pdf.cell(40, 10, ar("عدد الشواهد"), 1, 0, "C", True)
    pdf.cell(110, 10, ar("اسم الطالبة"), 1, 1, "C", True)

    pdf.set_text_color(0, 0, 0)
    for _, row in summary_df.iterrows():
        score = min(row["total_points"], 20)
        pdf.cell(40, 10, ar(str(score)), 1, 0, "C")
        pdf.cell(40, 10, ar(str(row["evidence_count"])), 1, 0, "C")
        pdf.cell(110, 10, ar(row["name"]), 1, 1, "R")

    return pdf.output(dest="S").encode("latin1")

# ---------------------------------------------------------
# 4. واجهة المستخدم (Streamlit)
# ---------------------------------------------------------
st.markdown("<h1 style='text-align: center; color: #1E6B7B;'>🌟 نظام متابعة وتوثيق السلوك المتميز</h1>", unsafe_allow_html=True)

tabs = st.tabs(["📥 استيراد الطالبات (Excel)", "➕ إضافة شاهد جديد", "📄 تقارير الطالبات والفصول"])

# --- التبويب الأول: رفع ملف الإكسل ---
with tabs[0]:
    st.subheader("استيراد بيانات الطالبات من ملف Excel")
    st.info("يجب أن يحتوي ملف الإكسل على عمودين باسم: (اسم الطالبة) و (الفصل)")
    uploaded_excel = st.file_uploader("اختر ملف الإكسل (.xlsx)", type=["xlsx"])
    if uploaded_excel:
        df_excel = pd.read_excel(uploaded_excel)
        if "اسم الطالبة" in df_excel.columns and "الفصل" in df_excel.columns:
            st.dataframe(df_excel.head(), use_container_width=True)
            if st.button("حفظ الطالبات في قاعدة البيانات"):
                c = conn.cursor()
                added = 0
                for _, r in df_excel.dropna(subset=["اسم الطالبة", "الفصل"]).iterrows():
                    try:
                        c.execute("INSERT OR IGNORE INTO students (name, classroom) VALUES (?, ?)",
                                  (str(r["اسم الطالبة"]).strip(), str(r["الفصل"]).strip()))
                        if c.rowcount > 0:
                            added += 1
                    except Exception as e:
                        pass
                conn.commit()
                st.success(f"تم استيراد {added} طالبة بنجاح!")
        else:
            st.error("تأكد من تسمية الأعمدة في ملف الإكسل بـ: 'اسم الطالبة' و 'الفصل'")

# --- التبويب الثاني: إضافة شاهد (صورة / فيديو / ملف) ---
with tabs[1]:
    st.subheader("رصد شاهد سلوك متميز (الحد الأقص للدرجة: 20)")
    students_df = pd.read_sql_query("SELECT * FROM students", conn)
    
    if students_df.empty:
        st.warning("يرجى استيراد أسماء الطالبات أولاً من التبويب الأول.")
    else:
        col1, col2 = st.columns(2)
        with col1:
            selected_class = st.selectbox("اختر الفصل:", students_df["classroom"].unique())
            filtered_students = students_df[students_df["classroom"] == selected_class]
            selected_student_name = st.selectbox("اختر الطالبة:", filtered_students["name"])
            student_id = int(filtered_students[filtered_students["name"] == selected_student_name]["id"].values[0])

            cur_score_df = pd.read_sql_query(f"SELECT COALESCE(SUM(points), 0) as total FROM evidences WHERE student_id = {student_id}", conn)
            current_score = float(cur_score_df["total"].values[0])
            remaining = max(0.0, 20.0 - current_score)
            st.metric("الدرجة الحالية للطالبة", f"{min(current_score, 20.0)} / 20", f"المتبقي للوصول للدرجة الكاملة: {remaining}")

        with col2:
            title = st.text_input("عنوان / وصف الشاهد (مثال: مبادرة تطوعية، انضباط مثالي)")
            points = st.number_input("درجة الشاهد:", min_value=0.5, max_value=20.0, value=min(2.0, remaining) if remaining > 0 else 0.5, step=0.5)
            evidence_file = st.file_uploader("ارفع الشاهد (صورة، فيديو، أو ملف PDF/Word)", type=["png", "jpg", "jpeg", "mp4", "mov", "pdf", "docx"])

        if st.button("اعتماد وحفظ الشاهد", type="primary"):
            if not title:
                st.error("يرجى كتابة عنوان للشاهد.")
            elif current_score >= 20.0:
                st.warning("الطالبة حاصلة بالفعل على الدرجة النهائية (20/20).")
            else:
                file_path = ""
                file_type = "بدون مرفق"
                if evidence_file:
                    ext = evidence_file.name.split(".")[-1].lower()
                    if ext in ["png", "jpg", "jpeg"]:
                        file_type = "صورة"
                    elif ext in ["mp4", "mov"]:
                        file_type = "فيديو"
                    else:
                        file_type = "ملف"
                    
                    safe_filename = f"{student_id}_{int(datetime.now().timestamp())}_{evidence_file.name}"
                    file_path = os.path.join(UPLOAD_DIR, safe_filename)
                    with open(file_path, "wb") as f:
                        f.write(evidence_file.getbuffer())

                final_points = min(points, remaining)
                c = conn.cursor()
                c.execute("""
                    INSERT INTO evidences (student_id, title, points, file_path, file_type, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (student_id, title, final_points, file_path, file_type, datetime.now().strftime("%Y-%m-%d")))
                conn.commit()
                st.success(f"تم إضافة الشاهد واحتساب {final_points} درجة للطالبة {selected_student_name}!")
                st.rerun()

# --- التبويب الثالث: التقارير واستعراض الشواهد ---
with tabs[2]:
    st.subheader("استخراج تقارير PDF واستعراض الشواهد")
    students_df = pd.read_sql_query("SELECT * FROM students", conn)
    
    if not students_df.empty:
        rep_class = st.selectbox("حدد الفصل لاستخراج التقارير:", students_df["classroom"].unique(), key="rep_class")
        
        class_query = """
            SELECT s.id, s.name, COUNT(e.id) as evidence_count, COALESCE(SUM(e.points), 0) as total_points
            FROM students s
            LEFT JOIN evidences e ON s.id = e.student_id
            WHERE s.classroom = ?
            GROUP BY s.id, s.name
            ORDER BY total_points DESC
        """
        class_summary_df = pd.read_sql_query(class_query, conn, params=(rep_class,))
        class_summary_df["الدرجة المعتمدة (من 20)"] = class_summary_df["total_points"].apply(lambda x: min(x, 20.0))
        
        st.markdown(f"### 📊 ملخص درجات فصل: {rep_class}")
        st.dataframe(class_summary_df[["name", "evidence_count", "الدرجة المعتمدة (من 20)"]], use_container_width=True)
        
        class_pdf_bytes = generate_class_pdf(rep_class, class_summary_df)
        st.download_button(
            label=f"⬇️ تحميل تقرير PDF الشامل لفصل ({rep_class})",
            data=class_pdf_bytes,
            file_name=f"تقرير_فصل_{rep_class}.pdf",
            mime="application/pdf"
        )

        st.divider()
        
        rep_student = st.selectbox("اختر طالبة لعرض شواهدها وتقريرها الفردي:", class_summary_df["name"])
        st_row = class_summary_df[class_summary_df["name"] == rep_student].iloc[0]
        st_id = int(st_row["id"])
        st_total = float(st_row["total_points"])

        ev_df = pd.read_sql_query("SELECT title, points, file_type, file_path, created_at FROM evidences WHERE student_id = ?", conn, params=(st_id,))
        
        if ev_df.empty:
            st.info("لا توجد شواهد مسجلة لهذه الطالبة حتى الآن.")
        else:
            st.write(f"**إجمالي الدرجة:** {min(st_total, 20.0)} / 20")
            for _, ev in ev_df.iterrows():
                with st.expander(f"📌 {ev['title']} ({ev['points']} درجات) - {ev['created_at']}"):
                    st.write(f"نوع الشاهد: **{ev['file_type']}**")
                    if ev["file_path"] and os.path.exists(ev["file_path"]):
                        if ev["file_type"] == "صورة":
                            st.image(ev["file_path"], width=350)
                        elif ev["file_type"] == "فيديو":
                            st.video(ev["file_path"])
                        else:
                            with open(ev["file_path"], "rb") as f:
                                st.download_button("تحميل الملف المرفق", f, file_name=os.path.basename(ev["file_path"]))

            student_pdf_bytes = generate_student_pdf(rep_student, rep_class, st_total, ev_df)
            st.download_button(
                label=f"⬇️ تحميل تقرير PDF الخاص بالطالبة ({rep_student})",
                data=student_pdf_bytes,
                file_name=f"تقرير_{rep_student}.pdf",
                mime="application/pdf"
            )

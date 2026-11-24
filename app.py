import os
import io
import json
import base64
import urllib.parse
from datetime import date
import pandas as pd
import streamlit as st
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader
import arabic_reshaper
from bidi.algorithm import get_display
from PIL import Image

st.set_page_config(
    page_title="السلوك المتميز",
    page_icon="🌟",
    layout="wide",
    initial_sidebar_state="collapsed",
)

MAX_POINTS = 20
DATA_DIR = "data_store"
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")
STUDENTS_FILE = os.path.join(DATA_DIR, "students.csv")
RECORDS_FILE = os.path.join(DATA_DIR, "records.csv")

SCHOOL_NAME = "متوسطة طويق الأولى للبنات"
EDU_ADMIN_TITLE = "الإدارة العامة للتعليم بمنطقة الرياض"
MINISTRY_TITLE = "وزارة التعليم"
FONT_PATH = "assets/fonts/Cairo-Regular.ttf"

HERO_CANDIDATES = [
    "assets/hero_edu.png",
    "assets/hero_edu.jpg",
    "assets/hero_edu.jpeg",
    "hero_edu.png",
    "hero_edu.jpg",
    "hero_edu.jpeg",
]

BEHAVIOR_RULES = {
    "الالتزام بالحضور والانضباط المدرسي": 3,
    "المبادرة والعمل التطوعي داخل المدرسة": 4,
    "التفوق والتميز العلمي والمشاركات": 5,
    "حسن الخلق والتعاون مع الزميلات والمعلمات": 3,
    "المحافظة على الممتلكات والبيئة المدرسية": 3,
    "تمثيل المدرسة في أنشطة أو مسابقات": 5,
}


def find_hero_image() -> str:
    for p in HERO_CANDIDATES:
        if os.path.exists(p):
            return p

    search_dirs = [".", "assets"]
    img_exts = (".png", ".jpg", ".jpeg", ".webp")
    for folder in search_dirs:
        if os.path.isdir(folder):
            for fname in sorted(os.listdir(folder)):
                fpath = os.path.join(folder, fname)
                if os.path.isfile(fpath) and fname.lower().endswith(img_exts):
                    if not fname.lower().startswith(("app", "test")):
                        return fpath
    return ""


def ensure_storage():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    if not os.path.exists(STUDENTS_FILE):
        pd.DataFrame(columns=["name", "classroom", "whatsapp"]).to_csv(
            STUDENTS_FILE, index=False, encoding="utf-8-sig"
        )

    if not os.path.exists(RECORDS_FILE):
        pd.DataFrame(
            columns=[
                "record_id",
                "student_name",
                "classroom",
                "whatsapp",
                "behavior",
                "points",
                "date",
                "observer_name",
                "evidence_file",
            ]
        ).to_csv(RECORDS_FILE, index=False, encoding="utf-8-sig")


def load_students_df() -> pd.DataFrame:
    ensure_storage()
    try:
        df = pd.read_csv(STUDENTS_FILE, dtype=str).fillna("")
    except Exception:
        df = pd.DataFrame(columns=["name", "classroom", "whatsapp"])
    for col in ["name", "classroom", "whatsapp"]:
        if col not in df.columns:
            df[col] = ""
    df["name"] = df["name"].astype(str).str.strip()
    df["classroom"] = df["classroom"].astype(str).str.strip()
    df["whatsapp"] = df["whatsapp"].astype(str).str.strip()
    df = df[(df["name"] != "") & (df["classroom"] != "")].drop_duplicates(
        subset=["name", "classroom"], keep="last"
    )
    return df.sort_values(["classroom", "name"]).reset_index(drop=True)


def save_students_df(df: pd.DataFrame):
    ensure_storage()
    clean_df = df.copy()
    for col in ["name", "classroom", "whatsapp"]:
        if col not in clean_df.columns:
            clean_df[col] = ""
    clean_df["name"] = clean_df["name"].astype(str).str.strip()
    clean_df["classroom"] = clean_df["classroom"].astype(str).str.strip()
    clean_df["whatsapp"] = clean_df["whatsapp"].astype(str).str.strip()
    clean_df = clean_df[(clean_df["name"] != "") & (clean_df["classroom"] != "")].drop_duplicates(
        subset=["name", "classroom"], keep="last"
    )
    clean_df.to_csv(STUDENTS_FILE, index=False, encoding="utf-8-sig")


def load_records_df() -> pd.DataFrame:
    ensure_storage()
    try:
        df = pd.read_csv(RECORDS_FILE, dtype=str).fillna("")
    except Exception:
        df = pd.DataFrame(
            columns=[
                "record_id",
                "student_name",
                "classroom",
                "whatsapp",
                "behavior",
                "points",
                "date",
                "observer_name",
                "evidence_file",
            ]
        )
    expected_cols = [
        "record_id",
        "student_name",
        "classroom",
        "whatsapp",
        "behavior",
        "points",
        "date",
        "observer_name",
        "evidence_file",
    ]
    for col in expected_cols:
        if col not in df.columns:
            df[col] = ""
    df["points"] = pd.to_numeric(df["points"], errors="coerce").fillna(0).astype(int)
    df["student_name"] = df["student_name"].astype(str).str.strip()
    df["classroom"] = df["classroom"].astype(str).str.strip()
    df["whatsapp"] = df["whatsapp"].astype(str).str.strip()
    df["behavior"] = df["behavior"].astype(str).str.strip()
    df["date"] = df["date"].astype(str).str.strip()
    df["observer_name"] = df["observer_name"].astype(str).str.strip()
    df["evidence_file"] = df["evidence_file"].astype(str).str.strip()
    df = df[(df["student_name"] != "") & (df["classroom"] != "")].reset_index(drop=True)
    if not df.empty and "record_id" in df.columns:
        df = df.iloc[::-1].reset_index(drop=True)
    return df


def save_records_df(df: pd.DataFrame):
    ensure_storage()
    df.to_csv(RECORDS_FILE, index=False, encoding="utf-8-sig")


def clean_phone(phone: str) -> str:
    digits = "".join(ch for ch in str(phone or "") if ch.isdigit())
    if digits.startswith("05") and len(digits) == 10:
        return "966" + digits[1:]
    if digits.startswith("5") and len(digits) == 9:
        return "966" + digits
    return digits


def build_whatsapp_link(phone: str, student_name: str, classroom: str, behavior: str, total_points: int) -> str:
    clean = clean_phone(phone)
    msg = (
        f"السلام عليكم ورحمة الله وبركاته 🌟\n"
        f"نفيدكم بتميز الطالبة: {student_name}\n"
        f"الفصل: {classroom}\n"
        f"مجال التميز: {behavior}\n"
        f"رصيد نقاط السلوك المتميز الحالي: {min(int(total_points), MAX_POINTS)} / {MAX_POINTS}\n"
        f"مع تحيات {SCHOOL_NAME}."
    )
    encoded = urllib.parse.quote(msg)
    if clean:
        return f"https://wa.me/{clean}?text={encoded}"
    return f"https://wa.me/?text={encoded}"


def upsert_students_from_df(df_upload: pd.DataFrame) -> int:
    cols_map = {str(c).strip(): c for c in df_upload.columns}
    name_col = cols_map.get("اسم الطالبة") or cols_map.get("الاسم") or cols_map.get("name")
    class_col = cols_map.get("الفصل") or cols_map.get("الصف والفصل") or cols_map.get("classroom")
    wa_col = (
        cols_map.get("الواتس")
        or cols_map.get("الواتساب")
        or cols_map.get("رقم الواتساب")
        or cols_map.get("الجوال")
        or cols_map.get("whatsapp")
    )

    if not name_col or not class_col:
        raise ValueError("يجب أن يحتوي الملف على عمودي (اسم الطالبة) و (الفصل).")

    current_df = load_students_df()
    existing_map = {
        (row["name"], row["classroom"]): row["whatsapp"]
        for _, row in current_df.iterrows()
    }

    added = 0
    for _, row in df_upload.iterrows():
        s_name = str(row[name_col] or "").strip()
        s_class = str(row[class_col] or "").strip()
        s_wa = str(row[wa_col] or "").strip() if wa_col and pd.notna(row[wa_col]) else ""
        if not s_name or not s_class or s_name.lower() == "nan":
            continue
        key = (s_name, s_class)
        if key not in existing_map:
            existing_map[key] = s_wa
            added += 1
        elif s_wa and not existing_map[key]:
            existing_map[key] = s_wa

    merged_rows = [{"name": k[0], "classroom": k[1], "whatsapp": v} for k, v in existing_map.items()]
    save_students_df(pd.DataFrame(merged_rows))
    return added


def add_single_student(name: str, classroom: str, whatsapp: str):
    df = load_students_df()
    new_row = pd.DataFrame(
        [{"name": name.strip(), "classroom": classroom.strip(), "whatsapp": whatsapp.strip()}]
    )
    save_students_df(pd.concat([df, new_row], ignore_index=True))


def update_student_whatsapp(student_name: str, classroom: str, whatsapp: str):
    wa_clean = whatsapp.strip()
    s_df = load_students_df()
    mask_s = (s_df["name"] == student_name) & (s_df["classroom"] == classroom)
    if mask_s.any():
        s_df.loc[mask_s, "whatsapp"] = wa_clean
    else:
        s_df = pd.concat(
            [s_df, pd.DataFrame([{"name": student_name, "classroom": classroom, "whatsapp": wa_clean}])],
            ignore_index=True,
        )
    save_students_df(s_df)

    r_df = load_records_df()
    if not r_df.empty:
        mask_r = (r_df["student_name"] == student_name) & (r_df["classroom"] == classroom)
        r_df.loc[mask_r, "whatsapp"] = wa_clean
        save_records_df(r_df)


def add_behavior_record(
    student_name: str,
    classroom: str,
    whatsapp: str,
    behavior: str,
    points: int,
    rec_date: str,
    observer_name: str,
    evidence_path: str,
):
    r_df = load_records_df()
    existing_pts = 0
    if not r_df.empty:
        sub = r_df[(r_df["student_name"] == student_name) & (r_df["classroom"] == classroom)]
        if not sub.empty:
            existing_pts = int(sub["points"].sum())

    remaining = max(0, MAX_POINTS - existing_pts)
    applied = min(int(points), remaining)
    new_total = existing_pts + applied

    if whatsapp.strip():
        update_student_whatsapp(student_name, classroom, whatsapp.strip())

    next_id = 1
    if not r_df.empty and "record_id" in r_df.columns:
        nums = pd.to_numeric(r_df["record_id"], errors="coerce").dropna()
        if not nums.empty:
            next_id = int(nums.max()) + 1

    new_rec = pd.DataFrame(
        [
            {
                "record_id": str(next_id),
                "student_name": student_name.strip(),
                "classroom": classroom.strip(),
                "whatsapp": whatsapp.strip(),
                "behavior": behavior.strip(),
                "points": int(applied),
                "date": str(rec_date),
                "observer_name": observer_name.strip(),
                "evidence_file": evidence_path.strip(),
            }
        ]
    )

    raw_df = (
        pd.read_csv(RECORDS_FILE, dtype=str).fillna("")
        if os.path.exists(RECORDS_FILE)
        else pd.DataFrame()
    )
    combined = pd.concat([raw_df, new_rec], ignore_index=True)
    save_records_df(combined)
    return applied, new_total


def delete_record_by_id(record_id: str):
    ensure_storage()
    raw_df = pd.read_csv(RECORDS_FILE, dtype=str).fillna("")
    if not raw_df.empty and "record_id" in raw_df.columns:
        filtered = raw_df[raw_df["record_id"].astype(str) != str(record_id)]
        save_records_df(filtered)


def build_backup_json() -> bytes:
    ensure_storage()
    s_df = load_students_df()
    r_df = (
        pd.read_csv(RECORDS_FILE, dtype=str).fillna("")
        if os.path.exists(RECORDS_FILE)
        else pd.DataFrame()
    )

    files_b64 = {}
    if os.path.exists(UPLOAD_DIR):
        for fname in os.listdir(UPLOAD_DIR):
            fpath = os.path.join(UPLOAD_DIR, fname)
            if os.path.isfile(fpath):
                with open(fpath, "rb") as f:
                    files_b64[fname] = base64.b64encode(f.read()).decode("utf-8")

    payload = {
        "students": s_df.to_dict(orient="records"),
        "records": r_df.to_dict(orient="records"),
        "files": files_b64,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")


def restore_backup_json(uploaded_json_file):
    ensure_storage()
    data = json.load(uploaded_json_file)

    students_list = data.get("students", [])
    records_list = data.get("records", [])
    files_dict = data.get("files", {})

    if students_list:
        save_students_df(pd.DataFrame(students_list))
    if records_list:
        save_records_df(pd.DataFrame(records_list))

    for fname, b64_content in files_dict.items():
        safe_name = os.path.basename(fname)
        target_path = os.path.join(UPLOAD_DIR, safe_name)
        with open(target_path, "wb") as f:
            f.write(base64.b64decode(b64_content))


def build_summary_excel(students_df: pd.DataFrame, records_df: pd.DataFrame) -> bytes:
    pts_map = {}
    cnt_map = {}
    if not records_df.empty:
        grouped = records_df.groupby(["student_name", "classroom"], as_index=False).agg(
            total_points=("points", "sum"),
            evidence_count=("behavior", "count"),
        )
        for _, r in grouped.iterrows():
            key = (str(r["student_name"]).strip(), str(r["classroom"]).strip())
            pts_map[key] = min(int(r["total_points"]), MAX_POINTS)
            cnt_map[key] = int(r["evidence_count"])

    rows = []
    if not students_df.empty:
        dedup_students = students_df.drop_duplicates(subset=["name", "classroom"])
        for _, s in dedup_students.iterrows():
            s_name = str(s["name"]).strip()
            s_class = str(s["classroom"]).strip()
            s_wa = str(s.get("whatsapp", "") or "").strip()
            key = (s_name, s_class)
            rows.append(
                {
                    "اسم الطالبة": s_name,
                    "الفصل": s_class,
                    "رقم الواتساب": s_wa,
                    "عدد الشواهد": cnt_map.get(key, 0),
                    "مجموع الدرجات": pts_map.get(key, 0),
                    "الحد الأقصى": MAX_POINTS,
                }
            )

    summary_df = pd.DataFrame(rows)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        summary_df.to_excel(writer, index=False, sheet_name="ملخص السلوك المتميز")
        if not records_df.empty:
            records_export = records_df.rename(
                columns={
                    "student_name": "اسم الطالبة",
                    "classroom": "الفصل",
                    "whatsapp": "رقم الواتساب",
                    "behavior": "السلوك المتميز",
                    "points": "الدرجات المضافة",
                    "date": "التاريخ",
                    "observer_name": "اسم الراصد",
                    "evidence_file": "ملف الشاهد",
                }
            )
            records_export.to_excel(writer, index=False, sheet_name="سجل الشواهد التفصيلي")
    return output.getvalue()


def ar_txt(text: str) -> str:
    s = str(text or "")
    reshaped = arabic_reshaper.reshape(s)
    return get_display(reshaped)


def generate_student_pdf(
    student_name: str,
    classroom: str,
    whatsapp: str,
    total_points: int,
    s_recs: pd.DataFrame,
) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4

    font_name = "Helvetica"
    if os.path.exists(FONT_PATH):
        font_name = "ArabicCairo"
        if font_name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(font_name, FONT_PATH))

    header_h = 3.2 * cm
    c.setFillColor(colors.HexColor("#0f4c3a"))
    c.rect(0, height - header_h, width, header_h, fill=1, stroke=0)

    c.setStrokeColor(colors.HexColor("#c59b27"))
    c.setLineWidth(2)
    c.line(0, height - header_h, width, height - header_h)

    c.setFillColor(colors.HexColor("#f3d882"))
    c.setFont(font_name, 13)
    c.drawRightString(width - 1.5 * cm, height - 1.1 * cm, ar_txt(MINISTRY_TITLE))

    c.setFillColor(colors.white)
    c.setFont(font_name, 11)
    c.drawRightString(width - 1.5 * cm, height - 1.75 * cm, ar_txt(EDU_ADMIN_TITLE))

    c.setFillColor(colors.HexColor("#f7e3a1"))
    c.setFont(font_name, 12)
    c.drawCentredString(
        width / 2, height - 2.55 * cm, ar_txt(f"تقرير شواهد السلوك المتميز — {SCHOOL_NAME}")
    )

    y = height - header_h - 1.0 * cm
    box_h = 2.6 * cm
    c.setFillColor(colors.HexColor("#fbfaf5"))
    c.setStrokeColor(colors.HexColor("#c59b27"))
    c.setLineWidth(1.2)
    c.roundRect(1.5 * cm, y - box_h, width - 3.0 * cm, box_h, 8, fill=1, stroke=1)

    c.setFillColor(colors.HexColor("#132620"))
    c.setFont(font_name, 12)
    c.drawRightString(width - 2.0 * cm, y - 0.75 * cm, ar_txt(f"اسم الطالبة: {student_name}"))
    c.drawRightString(
        width - 2.0 * cm,
        y - 1.45 * cm,
        ar_txt(f"الفصل: {classroom}   |   الواتساب: {whatsapp or 'غير مسجل'}"),
    )

    c.setFillColor(colors.HexColor("#0f4c3a"))
    c.setFont(font_name, 12)
    c.drawRightString(
        width - 2.0 * cm,
        y - 2.15 * cm,
        ar_txt(f"الدرجة التراكمية للسلوك المتميز: {min(int(total_points), MAX_POINTS)} / {MAX_POINTS}"),
    )

    y = y - box_h - 0.9 * cm
    c.setFillColor(colors.HexColor("#0f4c3a"))
    c.setFont(font_name, 12)
    c.drawRightString(width - 1.5 * cm, y, ar_txt("سجل الشواهد والدرجات المرصودة:"))
    y -= 0.6 * cm

    thumb_paths = []
    if s_recs is not None and not s_recs.empty:
        for _, rec in s_recs.iterrows():
            if y < 3.5 * cm:
                c.showPage()
                y = height - 2.0 * cm

            line_txt = (
                f"• {rec['behavior']}  (+{rec['points']} درجة) — "
                f"التاريخ: {rec['date']} — الراصد: {rec['observer_name']}"
            )
            c.setFillColor(colors.HexColor("#1e2d27"))
            c.setFont(font_name, 10)
            c.drawRightString(width - 1.5 * cm, y, ar_txt(line_txt))
            y -= 0.55 * cm

            ev_p = str(rec.get("evidence_file", "") or "").strip()
            if ev_p and os.path.exists(ev_p) and ev_p.lower().endswith((".png", ".jpg", ".jpeg")):
                thumb_paths.append(ev_p)
    else:
        c.setFillColor(colors.HexColor("#5d6f68"))
        c.setFont(font_name, 10)
        c.drawRightString(
            width - 1.5 * cm, y, ar_txt("لا توجد شواهد مسجلة لهذه الطالبة حتى الآن.")
        )
        y -= 0.6 * cm

    y -= 0.5 * cm
    if y < 6.5 * cm:
        c.showPage()
        y = height - 2.0 * cm

    c.setFillColor(colors.HexColor("#0f4c3a"))
    c.setFont(font_name, 12)
    c.drawRightString(width - 1.5 * cm, y, ar_txt("الشواهد المصغّرة:"))
    y -= 0.5 * cm

    if thumb_paths:
        cols_per_row = 2
        gap_x = 0.8 * cm
        gap_y = 0.7 * cm
        usable_w = width - 3.0 * cm - gap_x
        thumb_w = usable_w / cols_per_row
        thumb_h = 4.2 * cm

        for idx, img_path in enumerate(thumb_paths):
            col_idx = idx % cols_per_row
            row_idx = idx // cols_per_row

            if col_idx == 0 and row_idx > 0:
                y -= thumb_h + gap_y
                if y - thumb_h < 1.8 * cm:
                    c.showPage()
                    y = height - 2.5 * cm
                    row_idx = 0

            x_pos = width - 1.5 * cm - (col_idx + 1) * thumb_w - (col_idx * gap_x)
            y_pos = y - thumb_h if row_idx == 0 else y

            c.setStrokeColor(colors.HexColor("#c59b27"))
            c.setLineWidth(1)
            c.rect(x_pos, y_pos, thumb_w, thumb_h, fill=0, stroke=1)

            try:
                with Image.open(img_path) as im:
                    im_rgb = im.convert("RGB")
                    im_rgb.thumbnail((800, 800))
                    img_buf = io.BytesIO()
                    im_rgb.save(img_buf, format="JPEG", quality=82)
                    img_buf.seek(0)
                    reader = ImageReader(img_buf)
                    c.drawImage(
                        reader,
                        x_pos + 4,
                        y_pos + 4,
                        width=thumb_w - 8,
                        height=thumb_h - 8,
                        preserveAspectRatio=True,
                        anchor="c",
                    )
            except Exception:
                pass
    else:
        c.setFillColor(colors.HexColor("#6b7c75"))
        c.setFont(font_name, 10)
        c.drawRightString(
            width - 1.5 * cm, y - 0.4 * cm, ar_txt("لا توجد صور شواهد مرفقة للعرض المصغّر.")
        )

    c.save()
    buf.seek(0)
    return buf.getvalue()


st.markdown(
    """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@500;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Cairo', sans-serif;
        direction: RTL;
        text-align: right;
    }

    .stApp {
        background: linear-gradient(180deg, #f8f7f2 0%, #eff5f2 100%);
        color: #132620;
    }

    .light-header {
        background: #ffffff;
        border: 1px solid #d8dfd9;
        border-right: 5px solid #0f4c3a;
        border-radius: 14px;
        padding: 12px 16px;
        margin-bottom: 10px;
        box-shadow: 0 3px 12px rgba(15, 76, 58, 0.06);
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 10px;
    }

    .header-title {
        font-size: 1.15rem;
        font-weight: 800;
        color: #0f4c3a;
        margin: 0;
        line-height: 1.4;
    }

    .header-sub {
        font-size: 0.82rem;
        color: #5b6d66;
        margin: 0;
    }

    .gold-pill {
        background: #fdf7e4;
        color: #8a640b;
        border: 1px solid #e1c36b;
        border-radius: 999px;
        padding: 4px 12px;
        font-size: 0.82rem;
        font-weight: 800;
        white-space: nowrap;
    }

    .stat-box {
        background: #ffffff;
        border: 1px solid #dce4de;
        border-top: 3px solid #c59b27;
        border-radius: 14px;
        padding: 14px;
        text-align: center;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.03);
    }

    .stat-num {
        font-size: 1.65rem;
        font-weight: 800;
        color: #0f4c3a;
        line-height: 1.2;
    }

    .stat-txt {
        font-size: 0.86rem;
        color: #586a63;
        margin-top: 4px;
    }

    .student-box {
        background: #ffffff;
        border: 1px solid #dce4de;
        border-radius: 14px;
        padding: 14px 16px;
        margin-top: 12px;
        margin-bottom: 8px;
        box-shadow: 0 2px 10px rgba(15, 76, 58, 0.04);
    }

    .hero-frame {
        background: #ffffff;
        border: 1px solid #d9e2dc;
        border-radius: 16px;
        padding: 10px;
        box-shadow: 0 6px 20px rgba(15, 76, 58, 0.08);
    }
</style>
""",
    unsafe_allow_html=True,
)

ensure_storage()

if "nav_page" not in st.session_state:
    st.session_state.nav_page = "الواجهة الرئيسية"

if "menu_open" not in st.session_state:
    st.session_state.menu_open = False

nav_options = [
    "الواجهة الرئيسية",
    "استيراد الطالبات",
    "رصد السلوك والشواهد",
    "بطاقات الطالبات والواتساب و PDF",
    "التقارير والنسخ الاحتياطي",
]

# الشريط العلوي مع زر ☰ الأنيق على اليمين
top_right, top_main = st.columns([1.3, 8.7])
with top_right:
    if st.button("☰", key="hamburger_btn", help="فتح قائمة النوافذ", use_container_width=True):
        st.session_state.menu_open = not st.session_state.menu_open

with top_main:
    st.markdown(
        f"""
        <div class="light-header">
            <div>
                <p class="header-title">السلوك المتميز</p>
                <p class="header-sub">{st.session_state.nav_page} • {SCHOOL_NAME}</p>
            </div>
            <span class="gold-pill">الحد الأقصى: {MAX_POINTS}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

# قائمة النوافذ المرتبة عند الضغط على ☰
if st.session_state.menu_open:
    st.markdown("**النوافذ:**")
    nav_cols = st.columns(len(nav_options))
    for idx, opt in enumerate(nav_options):
        with nav_cols[idx]:
            btn_type = "primary" if st.session_state.nav_page == opt else "secondary"
            if st.button(opt, key=f"nav_btn_{idx}", type=btn_type, use_container_width=True):
                st.session_state.nav_page = opt
                st.session_state.menu_open = False
                st.rerun()

students_df = load_students_df()
records_df = load_records_df()

# فلتر مستقل لكل فصل
all_classes = sorted(
    list(
        set(
            (students_df["classroom"].tolist() if not students_df.empty else [])
            + (records_df["classroom"].tolist() if not records_df.empty else [])
        )
    )
)
class_options = ["جميع الفصول"] + all_classes
selected_class = st.selectbox("🏫 الفصل:", class_options)

if selected_class != "جميع الفصول":
    f_students = students_df[students_df["classroom"] == selected_class].copy()
    f_records = records_df[records_df["classroom"] == selected_class].copy()
else:
    f_students = students_df.copy()
    f_records = records_df.copy()

student_totals = {}
student_counts = {}
if not records_df.empty:
    grp = records_df.groupby(["student_name", "classroom"], as_index=False).agg(
        raw_pts=("points", "sum"),
        ev_cnt=("behavior", "count"),
    )
    for _, r in grp.iterrows():
        k = (str(r["student_name"]).strip(), str(r["classroom"]).strip())
        student_totals[k] = min(int(r["raw_pts"]), MAX_POINTS)
        student_counts[k] = int(r["ev_cnt"])

page = st.session_state.nav_page

if page == "الواجهة الرئيسية":
    hero_path = find_hero_image()
    col_visual, col_stats = st.columns([1.05, 1.45])

    with col_visual:
        if hero_path:
            st.markdown('<div class="hero-frame">', unsafe_allow_html=True)
            st.image(hero_path, use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.info("لم يتم العثور على صورة الهوية بعد. تأكد من رفعها داخل المستودع.")

    with col_stats:
        st.markdown("### ملخص المتابعة")
        st.caption(f"النطاق المعروض حالياً: {selected_class}")

        total_students_count = (
            len(f_students.drop_duplicates(subset=["name", "classroom"]))
            if not f_students.empty
            else 0
        )
        total_evidences_count = len(f_records) if not f_records.empty else 0

        if not f_students.empty:
            dedup_f = f_students.drop_duplicates(subset=["name", "classroom"])
            total_points_sum = sum(
                student_totals.get((str(row["name"]).strip(), str(row["classroom"]).strip()), 0)
                for _, row in dedup_f.iterrows()
            )
        elif not f_records.empty:
            unique_rec_students = f_records[["student_name", "classroom"]].drop_duplicates()
            total_points_sum = sum(
                student_totals.get(
                    (str(row["student_name"]).strip(), str(row["classroom"]).strip()), 0
                )
                for _, row in unique_rec_students.iterrows()
            )
        else:
            total_points_sum = 0

        s1, s2, s3 = st.columns(3)
        with s1:
            st.markdown(
                f"""
                <div class="stat-box">
                    <div class="stat-num">{total_students_count}</div>
                    <div class="stat-txt">عدد الطالبات</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with s2:
            st.markdown(
                f"""
                <div class="stat-box">
                    <div class="stat-num">{total_evidences_count}</div>
                    <div class="stat-txt">عدد الشواهد</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with s3:
            st.markdown(
                f"""
                <div class="stat-box">
                    <div class="stat-num">{total_points_sum}</div>
                    <div class="stat-txt">مجموع الدرجات</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("")
        q1, q2 = st.columns(2)
        with q1:
            if st.button("⭐ رصد سلوك وشاهد", type="primary", use_container_width=True):
                st.session_state.nav_page = "رصد السلوك والشواهد"
                st.rerun()
        with q2:
            if st.button("🪪 بطاقات الطالبات و PDF", use_container_width=True):
                st.session_state.nav_page = "بطاقات الطالبات والواتساب و PDF"
                st.rerun()

elif page == "استيراد الطالبات":
    st.markdown("### استيراد الطالبات أو إضافتهن")
    uploaded_excel = st.file_uploader(
        "ملف Excel (.xlsx) يحتوي على أعمدة: (اسم الطالبة) و (الفصل) واختيارياً (الواتساب)",
        type=["xlsx"],
    )
    if uploaded_excel is not None:
        try:
            xls = pd.ExcelFile(uploaded_excel)
            sheet_name = st.selectbox("اختر الورقة:", xls.sheet_names)
            preview_df = pd.read_excel(xls, sheet_name=sheet_name)
            st.dataframe(preview_df.head(10), use_container_width=True)
            if st.button("حفظ قائمة الطالبات", type="primary"):
                added = upsert_students_from_df(preview_df)
                st.success(f"تمت إضافة {added} طالبة جديدة بنجاح.")
                st.rerun()
        except Exception as e:
            st.error(f"تعذر قراءة الملف: {e}")

    st.markdown("---")
    st.markdown("#### إضافة طالبة يدوياً")
    with st.form("add_student_form", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            new_name = st.text_input("اسم الطالبة")
        with c2:
            new_class = st.text_input(
                "الفصل", value="" if selected_class == "جميع الفصول" else selected_class
            )
        with c3:
            new_wa = st.text_input("رقم الواتساب (مثال: 05xxxxxxxx)")
        if st.form_submit_button("حفظ الطالبة") and new_name.strip() and new_class.strip():
            add_single_student(new_name, new_class, new_wa)
            st.success("تمت إضافة الطالبة.")
            st.rerun()

elif page == "رصد السلوك والشواهد":
    st.markdown("### رصد السلوك المتميز والشواهد")
    if f_students.empty:
        st.warning("لا توجد طالبات مسجلات في هذا الفصل حالياً.")
    else:
        class_students_list = sorted(f_students["name"].unique().tolist())
        with st.form("record_behavior_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                chosen_student = st.selectbox("الطالبة:", class_students_list)
                student_row = f_students[f_students["name"] == chosen_student].iloc[0]
                default_wa = str(student_row.get("whatsapp", "") or "")
                wa_input = st.text_input("رقم الواتساب:", value=default_wa)
                observer_input = st.text_input("اسم الراصد:")
            with c2:
                chosen_behavior = st.selectbox("مجال السلوك المتميز:", list(BEHAVIOR_RULES.keys()))
                auto_pts = BEHAVIOR_RULES[chosen_behavior]
                st.caption(
                    f"النقاط المقررة: {auto_pts} درجات • الحد الأقصى لكل طالبة: {MAX_POINTS} درجة"
                )
                rec_date_input = st.date_input("التاريخ:", value=date.today())
                evidence_file = st.file_uploader(
                    "إرفاق شاهد (صورة / فيديو / PDF):",
                    type=["png", "jpg", "jpeg", "mp4", "mov", "pdf"],
                )

            if st.form_submit_button("اعتماد وحفظ الشاهد", type="primary"):
                if not observer_input.strip():
                    st.error("يرجى إدخال اسم الراصد.")
                else:
                    saved_rel_path = ""
                    if evidence_file is not None:
                        safe_filename = f"{chosen_student}_{rec_date_input}_{evidence_file.name}".replace(
                            " ", "_"
                        )
                        saved_rel_path = os.path.join(UPLOAD_DIR, safe_filename)
                        with open(saved_rel_path, "wb") as f_out:
                            f_out.write(evidence_file.getbuffer())

                    applied, new_total = add_behavior_record(
                        student_name=chosen_student,
                        classroom=str(student_row["classroom"]).strip(),
                        whatsapp=wa_input,
                        behavior=chosen_behavior,
                        points=auto_pts,
                        rec_date=str(rec_date_input),
                        observer_name=observer_input,
                        evidence_path=saved_rel_path,
                    )
                    st.success(
                        f"تم اعتماد ({applied}) درجة. الرصيد الحالي للطالبة: ({new_total} / {MAX_POINTS})."
                    )
                    st.rerun()

elif page == "بطاقات الطالبات والواتساب و PDF":
    st.markdown("### بطاقات الطالبات والواتساب وتقرير PDF")
    search_q = st.text_input("بحث باسم الطالبة أو رقم الواتساب:")

    if f_students.empty:
        st.info("لا توجد طالبات لعرضهن في هذا الفصل.")
    else:
        view_df = f_students.drop_duplicates(subset=["name", "classroom"]).copy()
        if search_q.strip():
            q = search_q.strip()
            view_df = view_df[
                view_df["name"].astype(str).str.contains(q, case=False, na=False)
                | view_df["whatsapp"].astype(str).str.contains(q, case=False, na=False)
            ]

        for _, s_row in view_df.iterrows():
            s_name = str(s_row["name"]).strip()
            s_class = str(s_row["classroom"]).strip()
            s_wa = str(s_row.get("whatsapp", "") or "").strip()
            key = (s_name, s_class)
            pts_val = student_totals.get(key, 0)
            cnt_val = student_counts.get(key, 0)

            s_recs = (
                records_df[
                    (records_df["student_name"] == s_name) & (records_df["classroom"] == s_class)
                ]
                if not records_df.empty
                else pd.DataFrame()
            )
            latest_behavior = (
                str(s_recs.iloc[0]["behavior"]) if not s_recs.empty else "سلوك متميز"
            )
            wa_url = build_whatsapp_link(s_wa, s_name, s_class, latest_behavior, pts_val)

            st.markdown(
                f"""
                <div class="student-box">
                    <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
                        <div>
                            <strong style="font-size:1.05rem; color:#132620;">{s_name}</strong>
                            <span style="color:#5d7068; margin-right:8px;">الفصل: {s_class}</span>
                        </div>
                        <span class="gold-pill">{pts_val} / {MAX_POINTS} درجة • {cnt_val} شاهد</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            c_wa1, c_wa2, c_wa3 = st.columns([2.2, 1.3, 2.0])
            with c_wa1:
                new_wa_val = st.text_input(
                    "الواتساب",
                    value=s_wa,
                    placeholder="رقم الواتساب (05xxxxxxxx)",
                    key=f"wa_edit_{s_class}_{s_name}",
                    label_visibility="collapsed",
                )
            with c_wa2:
                if st.button("حفظ الواتساب", key=f"wa_save_{s_class}_{s_name}", use_container_width=True):
                    update_student_whatsapp(s_name, s_class, new_wa_val)
                    st.success("تم حفظ رقم الواتساب.")
                    st.rerun()
            with c_wa3:
                st.link_button("إرسال واتساب", wa_url, use_container_width=True)

            pdf_bytes = generate_student_pdf(
                student_name=s_name,
                classroom=s_class,
                whatsapp=s_wa,
                total_points=pts_val,
                s_recs=s_recs,
            )
            st.download_button(
                label=f"تقرير PDF — {s_name}",
                data=pdf_bytes,
                file_name=f"تقرير_السلوك_{s_name}_{s_class}.pdf".replace(" ", "_"),
                mime="application/pdf",
                key=f"pdf_btn_{s_class}_{s_name}",
                use_container_width=True,
            )

            if not s_recs.empty:
                with st.expander(f"سجل شواهد الطالبة ({s_name})"):
                    for _, rec in s_recs.iterrows():
                        st.write(
                            f"• **{rec['behavior']}** (+{rec['points']} درجة) — "
                            f"التاريخ: {rec['date']} — الراصد: {rec['observer_name']}"
                        )
                        ev_path = str(rec.get("evidence_file", "") or "")
                        if ev_path and os.path.exists(ev_path):
                            lower_p = ev_path.lower()
                            if lower_p.endswith((".png", ".jpg", ".jpeg")):
                                st.image(ev_path, width=220)
                            elif lower_p.endswith((".mp4", ".mov")):
                                st.video(ev_path)
                        if st.button("حذف هذا السجل", key=f"del_rec_{rec['record_id']}"):
                            delete_record_by_id(str(rec["record_id"]))
                            st.rerun()

elif page == "التقارير والنسخ الاحتياطي":
    st.markdown("### التقارير والنسخ الاحتياطي")

    b_col1, b_col2 = st.columns(2)
    with b_col1:
        st.markdown("#### حفظ نسخة احتياطية كاملة")
        backup_bytes = build_backup_json()
        st.download_button(
            label="تحميل النسخة الاحتياطية (.json)",
            data=backup_bytes,
            file_name=f"نسخة_احتياطية_السلوك_{date.today()}.json",
            mime="application/json",
            type="primary",
            use_container_width=True,
        )

    with b_col2:
        st.markdown("#### استعادة نسخة احتياطية")
        rest_file = st.file_uploader(
            "ارفع ملف النسخة الاحتياطية (.json):", type=["json"]
        )
        if rest_file is not None:
            if st.button("استعادة البيانات الآن", type="primary", use_container_width=True):
                restore_backup_json(rest_file)
                st.success("تمت استعادة البيانات بنجاح!")
                st.rerun()

    st.markdown("---")
    st.markdown("#### تصدير Excel وسجل الفصل")
    excel_bytes = build_summary_excel(f_students, f_records)
    st.download_button(
        label=f"تحميل ملف Excel ({selected_class})",
        data=excel_bytes,
        file_name=f"السلوك_المتميز_{selected_class}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )
    if not f_records.empty:
        st.dataframe(f_records, use_container_width=True)
    else:
        st.info("لا توجد سجلات رصد في هذا الفصل حالياً.")

import os
import io
import json
import base64
import mimetypes
import urllib.parse
from datetime import date
import pandas as pd
import streamlit as st

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

HERO_CANDIDATES = [
    "assets/hero_edu.png",
    "assets/hero_edu.jpg",
    "assets/hero_edu.jpeg",
    "hero_edu.png",
    "hero_edu.jpg",
    "hero_edu.jpeg",
]

BEHAVIOR_RULES = {
    "انضباط الطالب وعدم غيابه بدون عذر خلال الفصل الدراسي.": 6,
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
    "أخرى (بناءً على توصية لجنة التوجيه الطلابي).": 6,
    "متميز": 4,
}

RECORD_COLS = [
    "record_id",
    "student_name",
    "classroom",
    "whatsapp",
    "behavior",
    "points",
    "date",
    "observer_name",
    "evidence_text",
    "evidence_file",
]

if "mem_uploads" not in st.session_state:
    st.session_state.mem_uploads = {}


def norm_txt(val) -> str:
    s = str(val or "").strip()
    s = (
        s.replace("أ", "ا")
        .replace("إ", "ا")
        .replace("آ", "ا")
        .replace("ة", "ه")
        .replace("ى", "ي")
    )
    return " ".join(s.split())


def display_txt(val) -> str:
    return " ".join(str(val or "").strip().split())


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


def image_to_data_uri(img_path: str) -> str:
    if not img_path or not os.path.exists(img_path):
        return ""
    mime, _ = mimetypes.guess_type(img_path)
    if not mime:
        ext = os.path.splitext(img_path)[1].lower()
        mime = "image/png" if ext == ".png" else "image/jpeg"
    try:
        with open(img_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
        return f"data:{mime};base64,{b64}"
    except Exception:
        return ""


def get_evidence_media(raw_path: str):
    p = str(raw_path or "").strip()
    base = os.path.basename(p) if p else ""

    if base and base in st.session_state.mem_uploads:
        return base, st.session_state.mem_uploads[base]

    if p and os.path.exists(p) and os.path.isfile(p):
        try:
            with open(p, "rb") as f:
                data = f.read()
            if base:
                st.session_state.mem_uploads[base] = data
            return base or p, data
        except Exception:
            pass

    if base:
        cand = os.path.join(UPLOAD_DIR, base)
        if os.path.exists(cand) and os.path.isfile(cand):
            try:
                with open(cand, "rb") as f:
                    data = f.read()
                st.session_state.mem_uploads[base] = data
                return base, data
            except Exception:
                pass

    return "", None


def ensure_storage():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    if not os.path.exists(STUDENTS_FILE):
        pd.DataFrame(columns=["name", "classroom", "whatsapp"]).to_csv(
            STUDENTS_FILE, index=False, encoding="utf-8-sig"
        )

    if not os.path.exists(RECORDS_FILE):
        pd.DataFrame(columns=RECORD_COLS).to_csv(
            RECORDS_FILE, index=False, encoding="utf-8-sig"
        )


def load_students_df() -> pd.DataFrame:
    ensure_storage()
    try:
        df = pd.read_csv(STUDENTS_FILE, dtype=str).fillna("")
    except Exception:
        df = pd.DataFrame(columns=["name", "classroom", "whatsapp"])
    for col in ["name", "classroom", "whatsapp"]:
        if col not in df.columns:
            df[col] = ""
    df["name"] = df["name"].apply(display_txt)
    df["classroom"] = df["classroom"].apply(display_txt)
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
    clean_df["name"] = clean_df["name"].apply(display_txt)
    clean_df["classroom"] = clean_df["classroom"].apply(display_txt)
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
        df = pd.DataFrame(columns=RECORD_COLS)
    for col in RECORD_COLS:
        if col not in df.columns:
            df[col] = ""
    df["points"] = pd.to_numeric(df["points"], errors="coerce").fillna(0).astype(int)
    df["student_name"] = df["student_name"].apply(display_txt)
    df["classroom"] = df["classroom"].apply(display_txt)
    df["whatsapp"] = df["whatsapp"].astype(str).str.strip()
    df["behavior"] = df["behavior"].apply(display_txt)
    df["date"] = df["date"].astype(str).str.strip()
    df["observer_name"] = df["observer_name"].apply(display_txt)
    df["evidence_text"] = df["evidence_text"].astype(str).str.strip()
    df["evidence_file"] = df["evidence_file"].astype(str).str.strip()
    df = df[(df["student_name"] != "") & (df["classroom"] != "")].reset_index(drop=True)
    if not df.empty and "record_id" in df.columns:
        df = df.iloc[::-1].reset_index(drop=True)
    return df


def save_records_df(df: pd.DataFrame):
    ensure_storage()
    clean_df = df.copy()
    for col in RECORD_COLS:
        if col not in clean_df.columns:
            clean_df[col] = ""
    clean_df[RECORD_COLS].to_csv(RECORDS_FILE, index=False, encoding="utf-8-sig")


def clean_phone(phone: str) -> str:
    digits = "".join(ch for ch in str(phone or "") if ch.isdigit())
    if digits.startswith("05") and len(digits) == 10:
        return "966" + digits[1:]
    if digits.startswith("5") and len(digits) == 9:
        return "966" + digits
    return digits


def build_whatsapp_link(
    phone: str, student_name: str, classroom: str, behavior: str, total_points: int
) -> str:
    clean = clean_phone(phone)
    current_pts = min(max(int(total_points), 0), MAX_POINTS)
    remaining_pts = max(0, MAX_POINTS - current_pts)

    if remaining_pts == 0:
        guidance = (
            f"ما شاء الله تبارك الله، فقد أتمّت الدرجة الكاملة ({MAX_POINTS} / {MAX_POINTS}) في السلوك المتميز، "
            f"ونأمل استمرارها على هذا المستوى المشرف والتميّز الدائم."
        )
    else:
        guidance = (
            f"حصلت الطالبة حتى الآن على ({current_pts} / {MAX_POINTS}) درجة، "
            f"ومتبقٍ لها ({remaining_pts}) درجات للوصول إلى الدرجة الكاملة ({MAX_POINTS} / {MAX_POINTS})؛ "
            f"ونأمل متابعتها وتشجيعها على مواصلة التميز والانضباط وتقديم الشواهد والمبادرات المتميزة "
            f"لتحقيق الدرجة الكاملة بإذن الله."
        )

    msg = (
        f"السلام عليكم ورحمة الله وبركاته 🌟\n"
        f"ولي أمر الطالبة الفاضلة: {student_name}\n"
        f"الصف / الفصل: {classroom}\n"
        f"أحدث سلوك متميز مرصود: {behavior}\n"
        f"{guidance}\n"
        f"مع خالص التقدير من إدارة {SCHOOL_NAME}."
    )
    encoded = urllib.parse.quote(msg)
    if clean:
        return f"https://wa.me/{clean}?text={encoded}"
    return f"https://wa.me/?text={encoded}"


def upsert_students_from_df(df_upload: pd.DataFrame) -> int:
    cols_map = {display_txt(c): c for c in df_upload.columns}
    name_col = (
        cols_map.get("الاسم")
        or cols_map.get("اسم الطالبة")
        or cols_map.get("اسم الطالب")
        or cols_map.get("name")
    )
    class_col = (
        cols_map.get("الصف")
        or cols_map.get("الفصل")
        or cols_map.get("الصف والفصل")
        or cols_map.get("classroom")
    )
    wa_col = (
        cols_map.get("الواتس")
        or cols_map.get("الواتساب")
        or cols_map.get("رقم الواتساب")
        or cols_map.get("الجوال")
        or cols_map.get("whatsapp")
    )

    if not name_col or not class_col:
        raise ValueError("يجب أن يحتوي ملف الإكسل على عمودي (الاسم) و (الصف) فقط.")

    current_df = load_students_df()
    existing_map = {
        (norm_txt(row["name"]), norm_txt(row["classroom"])): (
            display_txt(row["name"]),
            display_txt(row["classroom"]),
            str(row["whatsapp"] or "").strip(),
        )
        for _, row in current_df.iterrows()
    }

    added = 0
    for _, row in df_upload.iterrows():
        s_name = display_txt(row[name_col])
        s_class = display_txt(row[class_col])
        s_wa = str(row[wa_col] or "").strip() if wa_col and pd.notna(row[wa_col]) else ""
        if not s_name or not s_class or s_name.lower() == "nan" or s_class.lower() == "nan":
            continue
        key = (norm_txt(s_name), norm_txt(s_class))
        if key not in existing_map:
            existing_map[key] = (s_name, s_class, s_wa)
            added += 1
        else:
            old_n, old_c, old_w = existing_map[key]
            existing_map[key] = (old_n, old_c, s_wa if s_wa and not old_w else old_w)

    merged_rows = [
        {"name": v[0], "classroom": v[1], "whatsapp": v[2]} for v in existing_map.values()
    ]
    save_students_df(pd.DataFrame(merged_rows))
    return added


def add_single_student(name: str, classroom: str, whatsapp: str):
    df = load_students_df()
    new_row = pd.DataFrame(
        [
            {
                "name": display_txt(name),
                "classroom": display_txt(classroom),
                "whatsapp": whatsapp.strip(),
            }
        ]
    )
    save_students_df(pd.concat([df, new_row], ignore_index=True))


def update_student_whatsapp(student_name: str, classroom: str, whatsapp: str):
    s_name_n = norm_txt(student_name)
    s_class_n = norm_txt(classroom)
    wa_clean = whatsapp.strip()

    s_df = load_students_df()
    mask_s = (s_df["name"].apply(norm_txt) == s_name_n) & (
        s_df["classroom"].apply(norm_txt) == s_class_n
    )
    if mask_s.any():
        s_df.loc[mask_s, "whatsapp"] = wa_clean
    else:
        s_df = pd.concat(
            [
                s_df,
                pd.DataFrame(
                    [
                        {
                            "name": display_txt(student_name),
                            "classroom": display_txt(classroom),
                            "whatsapp": wa_clean,
                        }
                    ]
                ),
            ],
            ignore_index=True,
        )
    save_students_df(s_df)

    r_df = load_records_df()
    if not r_df.empty:
        mask_r = (r_df["student_name"].apply(norm_txt) == s_name_n) & (
            r_df["classroom"].apply(norm_txt) == s_class_n
        )
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
    evidence_text: str,
    evidence_path: str,
):
    s_name_n = norm_txt(student_name)
    s_class_n = norm_txt(classroom)
    r_df = load_records_df()

    existing_pts = 0
    if not r_df.empty:
        sub = r_df[
            (r_df["student_name"].apply(norm_txt) == s_name_n)
            & (r_df["classroom"].apply(norm_txt) == s_class_n)
        ]
        if not sub.empty:
            existing_pts = int(pd.to_numeric(sub["points"], errors="coerce").fillna(0).sum())

    remaining = max(0, MAX_POINTS - existing_pts)
    applied = min(int(points), remaining)
    new_total = min(MAX_POINTS, existing_pts + applied)

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
                "student_name": display_txt(student_name),
                "classroom": display_txt(classroom),
                "whatsapp": whatsapp.strip(),
                "behavior": display_txt(behavior),
                "points": int(applied),
                "date": str(rec_date),
                "observer_name": display_txt(observer_name),
                "evidence_text": str(evidence_text or "").strip(),
                "evidence_file": evidence_path.strip(),
            }
        ]
    )

    raw_df = (
        pd.read_csv(RECORDS_FILE, dtype=str).fillna("")
        if os.path.exists(RECORDS_FILE)
        else pd.DataFrame(columns=RECORD_COLS)
    )
    for col in RECORD_COLS:
        if col not in raw_df.columns:
            raw_df[col] = ""
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
    r_df = load_records_df()

    files_b64 = dict(
        {k: base64.b64encode(v).decode("utf-8") for k, v in st.session_state.mem_uploads.items()}
    )
    if os.path.exists(UPLOAD_DIR):
        for fname in os.listdir(UPLOAD_DIR):
            fpath = os.path.join(UPLOAD_DIR, fname)
            if os.path.isfile(fpath) and fname not in files_b64:
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
        raw_bytes = base64.b64decode(b64_content)
        st.session_state.mem_uploads[safe_name] = raw_bytes
        target_path = os.path.join(UPLOAD_DIR, safe_name)
        with open(target_path, "wb") as f:
            f.write(raw_bytes)


def build_summary_excel(students_df: pd.DataFrame, records_df: pd.DataFrame) -> bytes:
    pts_map = {}
    cnt_map = {}
    if not records_df.empty:
        tmp = records_df.copy()
        tmp["k_name"] = tmp["student_name"].apply(norm_txt)
        tmp["k_class"] = tmp["classroom"].apply(norm_txt)
        tmp["pts_num"] = pd.to_numeric(tmp["points"], errors="coerce").fillna(0).astype(int)
        grouped = tmp.groupby(["k_name", "k_class"], as_index=False).agg(
            total_points=("pts_num", "sum"),
            evidence_count=("behavior", "count"),
        )
        for _, r in grouped.iterrows():
            key = (r["k_name"], r["k_class"])
            pts_map[key] = min(int(r["total_points"]), MAX_POINTS)
            cnt_map[key] = int(r["evidence_count"])

    rows = []
    if not students_df.empty:
        dedup_students = students_df.drop_duplicates(subset=["name", "classroom"])
        for _, s in dedup_students.iterrows():
            s_name = display_txt(s["name"])
            s_class = display_txt(s["classroom"])
            s_wa = str(s.get("whatsapp", "") or "").strip()
            key = (norm_txt(s_name), norm_txt(s_class))
            rows.append(
                {
                    "الاسم": s_name,
                    "الصف": s_class,
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
                    "student_name": "الاسم",
                    "classroom": "الصف",
                    "whatsapp": "رقم الواتساب",
                    "behavior": "نوع السلوك",
                    "points": "الدرجة الممنوحة",
                    "date": "التاريخ",
                    "observer_name": "الراصد",
                    "evidence_text": "نص الشاهد",
                    "evidence_file": "ملف الشاهد",
                }
            )
            records_export.to_excel(writer, index=False, sheet_name="سجل الشواهد التفصيلي")
    return output.getvalue()


ensure_storage()

if "nav_page" not in st.session_state:
    st.session_state.nav_page = "الواجهة الرئيسية"

if "menu_open" not in st.session_state:
    st.session_state.menu_open = False

is_home = st.session_state.nav_page == "الواجهة الرئيسية"
hero_path = find_hero_image()
hero_uri = image_to_data_uri(hero_path) if is_home else ""

if is_home and hero_uri:
    bg_rule = f"""
    .stApp {{
        background-image: url("{hero_uri}");
        background-size: cover;
        background-position: center top;
        background-repeat: no-repeat;
        background-attachment: fixed;
        color: #132620;
    }}
    """
else:
    bg_rule = """
    .stApp {
        background: #f6f5ef;
        color: #132620;
    }
    """

card_bg = "rgba(255, 255, 255, 0.90)" if (is_home and hero_uri) else "#ffffff"

st.markdown(
    f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@500;600;700;800&display=swap');

    html, body, [class*="css"] {{
        font-family: 'Cairo', sans-serif;
        direction: RTL;
        text-align: right;
    }}

    {bg_rule}

    .stButton > button, .stDownloadButton > button, .stLinkButton > a {{
        background-color: #0f4c3a !important;
        color: #ffffff !important;
        border: 1px solid #c59b27 !important;
        border-radius: 12px !important;
        font-weight: 700 !important;
        padding: 0.55rem 1rem !important;
        box-shadow: 0 3px 10px rgba(15, 76, 58, 0.2) !important;
    }}

    .stButton > button p, .stDownloadButton > button p, .stLinkButton > a p,
    .stButton > button span, .stDownloadButton > button span, .stLinkButton > a span {{
        color: #ffffff !important;
    }}

    .stButton > button:hover, .stDownloadButton > button:hover, .stLinkButton > a:hover {{
        background-color: #16664f !important;
        border-color: #e6c567 !important;
    }}

    .brand-card {{
        background: {card_bg};
        backdrop-filter: blur(8px);
        -webkit-backdrop-filter: blur(8px);
        border: 1px solid rgba(197, 155, 39, 0.45);
        border-right: 5px solid #0f4c3a;
        border-radius: 14px;
        padding: 12px 16px;
        margin-bottom: 10px;
        box-shadow: 0 4px 14px rgba(15, 76, 58, 0.1);
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 10px;
    }}

    .brand-name {{
        font-size: 1.15rem;
        font-weight: 800;
        color: #0f4c3a;
        margin: 0;
    }}

    .brand-desc {{
        font-size: 0.82rem;
        color: #465850;
        margin: 2px 0 0 0;
    }}

    .cap-badge {{
        background: #fdf6e2;
        color: #8a640b;
        border: 1px solid #dfc067;
        border-radius: 999px;
        padding: 4px 12px;
        font-size: 0.82rem;
        font-weight: 800;
        white-space: nowrap;
    }}

    .kpi-grid {{
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 10px;
        margin: 12px 0;
    }}

    .kpi-item {{
        background: {card_bg};
        backdrop-filter: blur(8px);
        -webkit-backdrop-filter: blur(8px);
        border: 1px solid rgba(197, 155, 39, 0.45);
        border-top: 3px solid #c59b27;
        border-radius: 14px;
        padding: 12px 8px;
        text-align: center;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
    }}

    .kpi-num {{
        font-size: 1.5rem;
        font-weight: 800;
        color: #0f4c3a;
        line-height: 1.2;
    }}

    .kpi-lbl {{
        font-size: 0.78rem;
        color: #495a53;
        margin-top: 4px;
        font-weight: 700;
    }}

    .behavior-preview {{
        background: #ffffff;
        border: 1px solid #dcd9ce;
        border-right: 4px solid #c59b27;
        border-radius: 12px;
        padding: 10px 14px;
        margin: 8px 0 12px 0;
        color: #132620;
        font-weight: 700;
    }}

    .rec-card {{
        background: #fbfaf5;
        border: 1px solid #e3decb;
        border-right: 4px solid #0f4c3a;
        border-radius: 12px;
        padding: 10px 12px;
        margin: 8px 0 6px 0;
    }}

    .rec-head {{
        font-size: 0.98rem;
        font-weight: 800;
        color: #132620;
        margin-bottom: 4px;
    }}

    .rec-sub {{
        font-size: 0.83rem;
        color: #4e6059;
        font-weight: 600;
    }}

    .rec-note {{
        background: #ffffff;
        border: 1px dashed #c59b27;
        border-radius: 10px;
        padding: 8px 12px;
        margin-top: 8px;
        color: #132620;
        font-size: 0.92rem;
        line-height: 1.6;
        white-space: pre-wrap;
    }}

    [data-testid="stExpander"] {{
        background: #ffffff !important;
        border: 1px solid #dcd9ce !important;
        border-right: 4px solid #c59b27 !important;
        border-radius: 14px !important;
        margin-top: 10px !important;
        margin-bottom: 10px !important;
        box-shadow: 0 3px 10px rgba(15, 76, 58, 0.05) !important;
    }}

    [data-testid="stExpander"] summary {{
        font-weight: 800 !important;
        color: #0f4c3a !important;
        font-size: 1rem !important;
    }}
</style>
""",
    unsafe_allow_html=True,
)

nav_options = [
    "الواجهة الرئيسية",
    "استيراد الطالبات",
    "رصد السلوك والشواهد",
    "بطاقات الطالبات والواتساب",
    "التقارير والنسخ الاحتياطي",
]

st.markdown(
    f"""
    <div class="brand-card">
        <div>
            <p class="brand-name">السلوك المتميز</p>
            <p class="brand-desc">{st.session_state.nav_page} • {SCHOOL_NAME}</p>
        </div>
        <span class="cap-badge">الحد الأقصى: {MAX_POINTS}</span>
    </div>
    """,
    unsafe_allow_html=True,
)

if st.button("☰ النوافذ", key="hamburger_btn"):
    st.session_state.menu_open = not st.session_state.menu_open

if st.session_state.menu_open:
    for idx, opt in enumerate(nav_options):
        label_txt = f"✓ {opt}" if st.session_state.nav_page == opt else opt
        if st.button(label_txt, key=f"nav_btn_{idx}", use_container_width=True):
            st.session_state.nav_page = opt
            st.session_state.menu_open = False
            st.rerun()

students_df = load_students_df()
records_df = load_records_df()

all_classes = sorted(
    list(
        set(
            [
                display_txt(c)
                for c in (students_df["classroom"].tolist() if not students_df.empty else [])
                if display_txt(c)
            ]
            + [
                display_txt(c)
                for c in (records_df["classroom"].tolist() if not records_df.empty else [])
                if display_txt(c)
            ]
        )
    )
)
class_options = ["جميع الصفوف"] + all_classes
selected_class = st.selectbox("🏫 اختر الصف:", class_options)
selected_class_n = norm_txt(selected_class)

if selected_class != "جميع الصفوف":
    f_students = students_df[students_df["classroom"].apply(norm_txt) == selected_class_n].copy()
    f_records = records_df[records_df["classroom"].apply(norm_txt) == selected_class_n].copy()
else:
    f_students = students_df.copy()
    f_records = records_df.copy()

student_totals = {}
student_counts = {}
if not records_df.empty:
    tmp_r = records_df.copy()
    tmp_r["k_name"] = tmp_r["student_name"].apply(norm_txt)
    tmp_r["k_class"] = tmp_r["classroom"].apply(norm_txt)
    tmp_r["pts_num"] = pd.to_numeric(tmp_r["points"], errors="coerce").fillna(0).astype(int)
    grp = tmp_r.groupby(["k_name", "k_class"], as_index=False).agg(
        raw_pts=("pts_num", "sum"),
        ev_cnt=("behavior", "count"),
    )
    for _, r in grp.iterrows():
        k = (r["k_name"], r["k_class"])
        student_totals[k] = min(int(r["raw_pts"]), MAX_POINTS)
        student_counts[k] = int(r["ev_cnt"])

page = st.session_state.nav_page

if page == "الواجهة الرئيسية":
    student_keys_in_scope = set()
    if not f_students.empty:
        for _, row in f_students.drop_duplicates(subset=["name", "classroom"]).iterrows():
            student_keys_in_scope.add((norm_txt(row["name"]), norm_txt(row["classroom"])))
    if not f_records.empty:
        for _, row in f_records.drop_duplicates(subset=["student_name", "classroom"]).iterrows():
            student_keys_in_scope.add((norm_txt(row["student_name"]), norm_txt(row["classroom"])))

    total_students_count = len(student_keys_in_scope)
    total_evidences_count = len(f_records) if not f_records.empty else 0
    total_points_sum = sum(student_totals.get(k, 0) for k in student_keys_in_scope)

    st.markdown(
        f"""
        <div class="kpi-grid">
            <div class="kpi-item">
                <div class="kpi-num">{total_students_count}</div>
                <div class="kpi-lbl">الطالبات</div>
            </div>
            <div class="kpi-item">
                <div class="kpi-num">{total_evidences_count}</div>
                <div class="kpi-lbl">الشواهد</div>
            </div>
            <div class="kpi-item">
                <div class="kpi-num">{total_points_sum}</div>
                <div class="kpi-lbl">مجموع الدرجات</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    q1, q2 = st.columns(2)
    with q1:
        if st.button("⭐ رصد سلوك وشاهد", use_container_width=True):
            st.session_state.nav_page = "رصد السلوك والشواهد"
            st.rerun()
    with q2:
        if st.button("🪪 بطاقات الطالبات والواتساب", use_container_width=True):
            st.session_state.nav_page = "بطاقات الطالبات والواتساب"
            st.rerun()

elif page == "استيراد الطالبات":
    st.markdown("### استيراد الطالبات أو إضافتهن")
    uploaded_excel = st.file_uploader(
        "ملف Excel (.xlsx) يحتوي على عمودي (الاسم) و (الصف) فقط",
        type=["xlsx"],
    )
    if uploaded_excel is not None:
        try:
            xls = pd.ExcelFile(uploaded_excel)
            sheet_name = st.selectbox("اختر الورقة:", xls.sheet_names)
            preview_df = pd.read_excel(xls, sheet_name=sheet_name)
            st.dataframe(preview_df.head(10), use_container_width=True)
            if st.button("حفظ قائمة الطالبات"):
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
            new_name = st.text_input("الاسم")
        with c2:
            new_class = st.text_input(
                "الصف", value="" if selected_class == "جميع الصفوف" else selected_class
            )
        with c3:
            new_wa = st.text_input("رقم الواتساب (اختياري - مثال: 05xxxxxxxx)")
        if st.form_submit_button("حفظ الطالبة") and new_name.strip() and new_class.strip():
            add_single_student(new_name, new_class, new_wa)
            st.success("تمت إضافة الطالبة.")
            st.rerun()

elif page == "رصد السلوك والشواهد":
    st.markdown("### رصد السلوك المتميز والشواهد")
    if f_students.empty:
        st.warning("لا توجد طالبات مسجلات في هذا الصف حالياً.")
    else:
        chosen_behavior = st.selectbox("نوع السلوك:", list(BEHAVIOR_RULES.keys()))
        auto_pts = int(BEHAVIOR_RULES[chosen_behavior])
        st.markdown(
            f"""
            <div class="behavior-preview">
                السلوك المحدد: <span style="color:#0f4c3a;">{chosen_behavior}</span>
                • الدرجة المقررة: <span class="cap-badge">{auto_pts} درجات</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        class_students_list = sorted(f_students["name"].apply(display_txt).unique().tolist())
        with st.form("record_behavior_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                chosen_student = st.selectbox("الطالبة:", class_students_list)
                student_row = f_students[
                    f_students["name"].apply(norm_txt) == norm_txt(chosen_student)
                ].iloc[0]
                default_wa = str(student_row.get("whatsapp", "") or "")
                wa_input = st.text_input("رقم الواتساب:", value=default_wa)
                observer_input = st.text_input("اسم الراصد:")
            with c2:
                rec_date_input = st.date_input("التاريخ:", value=date.today())
                evidence_text_input = st.text_area(
                    "إضافة نص شاهد (اختياري):",
                    placeholder="اكتب وصف الشاهد أو المبادرة أو الملاحظة هنا...",
                    height=95,
                )
                evidence_file = st.file_uploader(
                    "إرفاق ملف شاهد (صورة / فيديو / PDF):",
                    type=["png", "jpg", "jpeg", "webp", "mp4", "mov", "pdf"],
                )

            if st.form_submit_button("اعتماد وحفظ الشاهد"):
                if not observer_input.strip():
                    st.error("يرجى إدخال اسم الراصد.")
                else:
                    saved_rel_path = ""
                    if evidence_file is not None:
                        file_bytes = evidence_file.getvalue()
                        safe_filename = (
                            f"{norm_txt(chosen_student)}_{rec_date_input}_{evidence_file.name}"
                            .replace(" ", "_")
                        )
                        st.session_state.mem_uploads[safe_filename] = file_bytes
                        saved_rel_path = os.path.join(UPLOAD_DIR, safe_filename)
                        try:
                            with open(saved_rel_path, "wb") as f_out:
                                f_out.write(file_bytes)
                        except Exception:
                            pass

                    applied, new_total = add_behavior_record(
                        student_name=chosen_student,
                        classroom=display_txt(student_row["classroom"]),
                        whatsapp=wa_input,
                        behavior=chosen_behavior,
                        points=auto_pts,
                        rec_date=str(rec_date_input),
                        observer_name=observer_input,
                        evidence_text=evidence_text_input,
                        evidence_path=saved_rel_path,
                    )
                    st.success(
                        f"تم اعتماد ({applied}) درجة للسلوك ({chosen_behavior}). الرصيد الحالي للطالبة: ({new_total} / {MAX_POINTS})."
                    )
                    st.rerun()

elif page == "بطاقات الطالبات والواتساب":
    st.markdown("### بطاقات الطالبات والواتساب والشواهد")
    search_q = st.text_input("بحث باسم الطالبة أو رقم الواتساب:")

    card_entries = []
    seen_entries = set()

    if not f_students.empty:
        for _, s_row in f_students.drop_duplicates(subset=["name", "classroom"]).iterrows():
            sn_disp = display_txt(s_row["name"])
            sc_disp = display_txt(s_row["classroom"])
            sw = str(s_row.get("whatsapp", "") or "").strip()
            k = (norm_txt(sn_disp), norm_txt(sc_disp))
            if k not in seen_entries:
                seen_entries.add(k)
                card_entries.append({"name": sn_disp, "classroom": sc_disp, "whatsapp": sw})

    if not f_records.empty:
        for _, r_row in f_records.drop_duplicates(subset=["student_name", "classroom"]).iterrows():
            sn_disp = display_txt(r_row["student_name"])
            sc_disp = display_txt(r_row["classroom"])
            sw = str(r_row.get("whatsapp", "") or "").strip()
            k = (norm_txt(sn_disp), norm_txt(sc_disp))
            if k not in seen_entries:
                seen_entries.add(k)
                card_entries.append({"name": sn_disp, "classroom": sc_disp, "whatsapp": sw})

    if search_q.strip():
        q = display_txt(search_q).lower()
        card_entries = [
            item
            for item in card_entries
            if q in item["name"].lower() or q in item["whatsapp"].lower()
        ]

    if not card_entries:
        st.info("لا توجد طالبات لعرضهن في هذا الصف.")
    else:
        for idx_c, item in enumerate(card_entries):
            s_name = item["name"]
            s_class = item["classroom"]
            s_wa = item["whatsapp"]
            key = (norm_txt(s_name), norm_txt(s_class))
            card_key = f"{key[0]}__{key[1]}"
            pts_val = student_totals.get(key, 0)
            cnt_val = student_counts.get(key, 0)

            s_recs = (
                records_df[
                    (records_df["student_name"].apply(norm_txt) == key[0])
                    & (records_df["classroom"].apply(norm_txt) == key[1])
                ]
                if not records_df.empty
                else pd.DataFrame()
            )
            latest_behavior = (
                display_txt(s_recs.iloc[0]["behavior"]) if not s_recs.empty else "متميز"
            )
            wa_url = build_whatsapp_link(s_wa, s_name, s_class, latest_behavior, pts_val)

            exp_label = (
                f"سجل أعمال ومتميزات الطالبة: {s_name}  |  الصف: {s_class}  |  "
                f"{pts_val} / {MAX_POINTS} درجة ({cnt_val} شاهد)"
            )
            with st.expander(exp_label, expanded=False):
                c_wa1, c_wa2, c_wa3 = st.columns([2.2, 1.3, 2.0])
                with c_wa1:
                    new_wa_val = st.text_input(
                        "رقم الواتساب",
                        value=s_wa,
                        placeholder="أدخل رقم الواتساب (05xxxxxxxx)",
                        key=f"wa_edit_{idx_c}_{card_key}",
                        label_visibility="collapsed",
                    )
                with c_wa2:
                    if st.button("حفظ الواتساب", key=f"wa_save_{idx_c}_{card_key}", use_container_width=True):
                        update_student_whatsapp(s_name, s_class, new_wa_val)
                        st.success("تم حفظ رقم الواتساب.")
                        st.rerun()
                with c_wa3:
                    st.link_button("إرسال واتساب", wa_url, use_container_width=True)

                if not s_recs.empty:
                    total_recs = len(s_recs)
                    for idx_r, (_, rec) in enumerate(s_recs.iterrows()):
                        rec_num = total_recs - idx_r
                        rec_pts = int(pd.to_numeric(rec.get("points", 0), errors="coerce") or 0)
                        ev_txt = str(rec.get("evidence_text", "") or "").strip()
                        note_html = (
                            f'<div class="rec-note"><strong>نص الشاهد:</strong><br>{ev_txt}</div>'
                            if ev_txt
                            else ""
                        )
                        st.markdown(
                            f"""
                            <div class="rec-card">
                                <div class="rec-head">رصد رقم ({rec_num}) - {rec['behavior']}</div>
                                <div class="rec-sub">
                                    الدرجة الممنوحة: {rec_pts} درجات • التاريخ: {rec['date']} • الراصد: {rec['observer_name']}
                                </div>
                                {note_html}
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

                        ev_name, ev_bytes = get_evidence_media(rec.get("evidence_file", ""))
                        if ev_bytes:
                            lower_n = ev_name.lower()
                            if lower_n.endswith((".png", ".jpg", ".jpeg", ".webp")):
                                st.image(
                                    ev_bytes,
                                    caption=f"شاهد رصد رقم ({rec_num}): {rec['behavior']}",
                                    use_container_width=True,
                                )
                            elif lower_n.endswith((".mp4", ".mov")):
                                st.video(ev_bytes)
                            elif lower_n.endswith(".pdf"):
                                st.download_button(
                                    label=f"فتح / تحميل ملف الشاهد ({ev_name})",
                                    data=ev_bytes,
                                    file_name=ev_name,
                                    mime="application/pdf",
                                    key=f"ev_dl_{rec['record_id']}_{idx_r}",
                                    use_container_width=True,
                                )

                        if st.button("حذف هذا السجل", key=f"del_rec_{rec['record_id']}_{idx_r}"):
                            delete_record_by_id(str(rec["record_id"]))
                            st.rerun()
                else:
                    st.info("لا توجد شواهد مسجلة لهذه الطالبة حتى الآن.")

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
            use_container_width=True,
        )

    with b_col2:
        st.markdown("#### استعادة نسخة احتياطية")
        rest_file = st.file_uploader(
            "ارفع ملف النسخة الاحتياطية (.json):", type=["json"]
        )
        if rest_file is not None:
            if st.button("استعادة البيانات الآن", use_container_width=True):
                restore_backup_json(rest_file)
                st.success("تمت استعادة البيانات بنجاح!")
                st.rerun()

    st.markdown("---")
    st.markdown("#### تصدير Excel وسجل الصف")
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
        st.info("لا توجد سجلات رصد في هذا الصف حالياً.")

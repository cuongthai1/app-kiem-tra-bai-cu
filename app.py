import streamlit as st
import pandas as pd
import json
import re
import docx
import base64
import zlib
import random
import xml.etree.ElementTree as ET

st.set_page_config(page_title="Hệ Thống Kiểm Tra Bài Cũ", layout="centered")

# --- NHÚNG KATEX ĐỂ HIỂN THỊ CÔNG THỨC TOÁN / LÝ ---
st.markdown(
    """
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.8/dist/katex.min.css">
    <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.8/dist/katex.min.js"></script>
    <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.8/dist/contrib/auto-render.min.js"
        onload="renderMathInElement(document.body);"></script>
    """,
    unsafe_allow_html=True
)

# --- XỬ LÝ CÔNG THỨC WORD (OMML TO LATEX) ---
def omml_to_latex(element):
    try:
        tag = element.tag.split('}')[-1]
        if tag == 't':
            return element.text or ""
        elif tag == 'f':
            num, den = "", ""
            for child in element:
                c_tag = child.tag.split('}')[-1]
                if c_tag == 'num':
                    num = "".join([omml_to_latex(c) for c in child])
                elif c_tag == 'den':
                    den = "".join([omml_to_latex(c) for c in child])
            return f"\\frac{{{num}}}{{{den}}}"
        elif tag == 'sSup':
            e, sup = "", ""
            for child in element:
                c_tag = child.tag.split('}')[-1]
                if c_tag == 'e':
                    e = "".join([omml_to_latex(c) for c in child])
                elif c_tag == 'sup':
                    sup = "".join([omml_to_latex(c) for c in child])
            return f"{{{e}}}^{{{sup}}}"
        elif tag == 'sSub':
            e, sub = "", ""
            for child in element:
                c_tag = child.tag.split('}')[-1]
                if c_tag == 'e':
                    e = "".join([omml_to_latex(c) for c in child])
                elif c_tag == 'sub':
                    sub = "".join([omml_to_latex(c) for c in child])
            return f"{{{e}}}_{{{sub}}}"
        elif tag == 'rad':
            e = "".join([omml_to_latex(c) for c in element if c.tag.endswith('e')])
            return f"\\sqrt{{{e}}}"
        else:
            return "".join([omml_to_latex(child) for child in element])
    except Exception:
        return ""

def read_docx_with_math(file):
    doc = docx.Document(file)
    text_list = []
    for p in doc.paragraphs:
        p_text = ""
        for child in p._element:
            tag = child.tag.split('}')[-1]
            if tag == 'r':
                for grand in child:
                    if grand.tag.endswith('t'):
                        p_text += grand.text or ""
            elif tag == 'oMath':
                latex = omml_to_latex(child)
                if latex:
                    p_text += f" ${latex}$ "
        if p_text.strip():
            text_list.append(p_text.strip())
    return "\n".join(text_list)

def clean_prefix(text):
    text = re.sub(r'^(Câu|Câu hỏi)\s*\d+[:\.]?\s*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'^[A-D][:\.]\s*', '', text, flags=re.IGNORECASE)
    return text.strip()

def parse_docx_questions(text):
    questions = []
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    current_q = None
    
    for line in lines:
        if re.match(r'^(Câu|Câu hỏi)\s*\d+', line, re.IGNORECASE):
            if current_q and current_q['options']:
                questions.append(current_q)
            q_text = clean_prefix(line)
            current_q = {"question": q_text, "options": [], "correct": None}
        elif current_q and re.match(r'^[A-D][:\.]', line, re.IGNORECASE):
            is_correct = '*' in line or 'TRUE' in line.upper()
            opt_text = line.replace('*', '').strip()
            opt_text = clean_prefix(opt_text)
            current_q["options"].append(opt_text)
            if is_correct:
                current_q["correct"] = len(current_q["options"]) - 1
                
    if current_q and current_q['options']:
        questions.append(current_q)
    return questions

# --- LƯU ĐIỂM VỀ GOOGLE SHEETS ---
def save_to_google_sheets(student_name, student_class, score, total):
    try:
        import gspread
        from google.oauth2.service_account import Credentials
        
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_dict = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)
        
        sheet = client.open("diem_kiem_tra").worksheet("KetQua")
        sheet.append_row([student_name, student_class, f"{score}/{total}", round(score/total*10, 2)])
        return True
    except Exception:
        return False

# --- GIAO DIỆN CHÍNH ---
st.title("🔒 HỆ THỐNG KIỂM TRA BÀI CŨ")

# Khởi tạo bộ nhớ chung cho bài kiểm tra
if "active_quiz" not in st.session_state:
    st.session_state.active_quiz = None

role = st.sidebar.radio("Chọn vai trò:", ["Học sinh", "Giáo viên"])

if role == "Giáo viên":
    st.subheader("👨‍🏫 Dành Cho Giáo Viên - Nạp Đề Thi")
    uploaded_file = st.file_uploader("Tải file đề thi Word (.docx)", type=["docx"])
    
    if uploaded_file:
        raw_text = read_docx_with_math(uploaded_file)
        parsed_q = parse_docx_questions(raw_text)
        if parsed_q:
            st.session_state.active_quiz = parsed_q
            st.success(f"✅ Nạp thành công {len(parsed_q)} câu hỏi vào hệ thống!")
            st.info("Bây giờ bạn chỉ cần copy link web dán qua Zalo, tất cả Học sinh bấm vào link đều sẽ mở được đề này ngay lập tức.")
        else:
            st.error("Không tìm thấy câu hỏi đúng định dạng trong file Word!")

else:
    st.subheader("👨‍🎓 Dành Cho Học Sinh Làm Bài")
    
    # Kiểm tra xem đã có đề thi nạp vào hệ thống chưa
    if not st.session_state.active_quiz:
        st.warning("⚠️ Hiện tại chưa có bài kiểm tra nào được nạp! Vui lòng liên hệ Giáo viên.")
    else:
        questions = st.session_state.active_quiz
        
        # Khởi tạo đề xáo trộn riêng cho từng học sinh
        if "student_quiz" not in st.session_state:
            shuffled_q = []
            for q in questions:
                opts = list(enumerate(q["options"]))
                random.shuffle(opts)
                new_opts = [opt[1] for opt in opts]
                new_correct = [i for i, opt in enumerate(opts) if opt[0] == q["correct"]]
                shuffled_q.append({
                    "question": q["question"],
                    "options": new_opts,
                    "correct": new_correct[0] if new_correct else 0
                })
            random.shuffle(shuffled_q)
            st.session_state.student_quiz = shuffled_q

        quiz = st.session_state.student_quiz
        
        with st.form("quiz_form"):
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("Họ và tên học sinh:")
            with col2:
                student_class = st.text_input("Lớp:")
                
            st.divider()
            
            user_answers = {}
            labels = ["A", "B", "C", "D"]
            
            for idx, q in enumerate(quiz):
                st.markdown(f"**Câu {idx + 1}:** {q['question']}")
                formatted_opts = [f"{labels[i]}. {opt}" for i, opt in enumerate(q["options"])]
                ans = st.radio(f"Chọn đáp án câu {idx + 1}:", formatted_opts, index=None, key=f"q_{idx}", label_visibility="collapsed")
                user_answers[idx] = ans
                st.markdown("---")
                
            submitted = st.form_submit_button("NỘP BÀI KIỂM TRA", use_container_width=True)
            
            if submitted:
                if not name.strip() or not student_class.strip():
                    st.error("❌ Vui lòng nhập đầy đủ Họ tên và Lớp trước khi nộp bài!")
                else:
                    score = 0
                    for idx, q in enumerate(quiz):
                        if user_answers[idx] is not None:
                            selected_label = user_answers[idx].split(".")[0]
                            selected_idx = labels.index(selected_label)
                            if selected_idx == q["correct"]:
                                score += 1
                                
                    total = len(quiz)
                    final_grade = round(score / total * 10, 2)
                    
                    st.balloons()
                    st.success(f"🎉 Kết quả của {name} - Lớp {student_class}: {score}/{total} câu đúng ({final_grade} điểm)")
                    
                    # Tự động gửi kết quả về Google Sheets
                    sheet_saved = save_to_google_sheets(name, student_class, score, total)
                    if sheet_saved:
                        st.info("✅ Kết quả làm bài đã được tự động lưu vào hệ thống điểm của Giáo viên.")
                    else:
                        st.warning("⚠️ Bài làm đã chấm điểm xong (không thể kết nối Google Sheets).")

import streamlit as st
import pandas as pd
import json
import re
import docx
import base64
import zlib

st.set_page_config(page_title="Kiểm Tra Bài Cũ", layout="centered")

# ----------------------------------------------------
# HÀM NÉN & MÃ HÓA DỮ LIỆU ĐƯA VÀO URL LINK
# ----------------------------------------------------
def encode_data(data):
    try:
        json_str = json.dumps(data, ensure_ascii=False)
        compressed = zlib.compress(json_str.encode('utf-8'))
        return base64.urlsafe_b64encode(compressed).decode('utf-8')
    except Exception:
        return ""

def decode_data(encoded_str):
    try:
        compressed_bytes = base64.urlsafe_b64decode(encoded_str)
        decompressed = zlib.decompress(compressed_bytes)
        return json.loads(decompressed.decode('utf-8'))
    except Exception:
        return None

# Tự động đọc dữ liệu từ tham số URL nếu học sinh mở link
query_params = st.query_params
is_student_mode = "data" in query_params  # Kiểm tra nếu là học sinh vào bằng link Zalo

url_data = None
if is_student_mode:
    url_data = decode_data(query_params["data"])

# Khởi tạo lưu trữ Session State
if 'student_list' not in st.session_state:
    st.session_state.student_list = url_data.get("students", []) if url_data else []

if 'quiz_data' not in st.session_state:
    st.session_state.quiz_data = url_data.get("quiz", []) if url_data else []

if 'completed_students' not in st.session_state:
    st.session_state.completed_students = set()

# Hàm bóc tách câu hỏi từ Word / TXT
def parse_questions_from_text(text):
    questions = []
    blocks = re.split(r'\n(?=Câu\s*\d+|[0-9]+\.)', text, flags=re.IGNORECASE)
    
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        lines = [l.strip() for l in block.split('\n') if l.strip()]
        if len(lines) >= 2:
            q_text = lines[0]
            options = []
            for line in lines[1:]:
                if re.match(r'^[A-Dd][\.\:\)].*', line):
                    options.append(line)
            if not options and len(lines) > 1:
                options = lines[1:]
            if len(options) >= 2:
                questions.append({
                    "question": q_text,
                    "options": options,
                    "answer": options[0]
                })
    return questions

# ----------------------------------------------------
# CASE 1: MÀN HÌNH GIÁO VIÊN (Vào bằng Link gốc)
# ----------------------------------------------------
if not is_student_mode:
    st.title("⚙️ Màn Hình Quản Lý - Giáo Viên")
    
    with st.sidebar:
        st.header("⚙️ TẢI DỮ LIỆU ĐỀ THI")
        
        # 1. Tải danh sách học sinh
        st.subheader("1. Tải danh sách lớp")
        students_file = st.file_uploader("Tải file Excel/CSV danh sách lớp", type=["csv", "xlsx"], key="students_upload")
        
        if students_file:
            try:
                if students_file.name.endswith('.csv'):
                    df = pd.read_csv(students_file, header=None)
                else:
                    df = pd.read_excel(students_file, header=None)
                
                found_names = []
                for col in df.columns:
                    for val in df[col].dropna():
                        val_str = str(val).strip()
                        if val_str and val_str.lower() not in ['hoten', 'họ tên', 'ho ten', 'stt', 'trạng thái', 'lớp']:
                            if len(val_str) > 2 and not val_str.isdigit():
                                found_names.append(val_str)
                
                st.session_state.student_list = [name for name in found_names if "HoTen" not in name and "Họ tên" not in name]
                st.success(f"✅ Đã nạp {len(st.session_state.student_list)} học sinh!")
            except Exception as e:
                st.error(f"Lỗi đọc file học sinh: {str(e)}")

        st.markdown("---")
        
        # 2. Tải câu hỏi lên
        st.subheader("2. Tải bộ câu hỏi")
        st.caption("Hỗ trợ file Word (.docx), TXT hoặc Excel (.xlsx)")
        quiz_file = st.file_uploader("Tải file câu hỏi", type=["docx", "txt", "xlsx"], key="quiz_upload")
        
        if quiz_file:
            parsed_q = []
            file_ext = quiz_file.name.split('.')[-1].lower()
            try:
                if file_ext == 'docx':
                    doc = docx.Document(quiz_file)
                    full_text = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
                    parsed_q = parse_questions_from_text(full_text)
                elif file_ext == 'txt':
                    full_text = quiz_file.read().decode("utf-8")
                    parsed_q = parse_questions_from_text(full_text)
                elif file_ext == 'xlsx':
                    df_q = pd.read_excel(quiz_file)
                    for _, row in df_q.iterrows():
                        cols = row.dropna().tolist()
                        if len(cols) >= 3:
                            parsed_q.append({
                                "question": str(cols[0]),
                                "options": [str(c) for c in cols[1:]],
                                "answer": str(cols[1])
                            })
                if parsed_q:
                    st.session_state.quiz_data = parsed_q
                    st.success(f"✅ Đã nạp {len(parsed_q)} câu hỏi!")
            except Exception as e:
                st.error(f"Lỗi đọc file câu hỏi: {str(e)}")

    if not st.session_state.student_list or not st.session_state.quiz_data:
        st.info("👈 Giáo viên vui lòng nạp Danh sách lớp và File câu hỏi ở thanh menu bên trái.")
    else:
        st.success("🎉 ĐÃ TẠO ĐỀ THÀNH CÔNG!")
        
        # Duyệt đáp án đúng
        with st.expander("📝 Bấm vào đây để xem/chỉnh sửa đáp án đúng cho từng câu", expanded=True):
            for idx, q in enumerate(st.session_state.quiz_data):
                st.markdown(f"**Câu {idx+1}:** {q['question']}")
                current_ans = q.get('answer', q['options'][0])
                correct_ans = st.selectbox(
                    f"Đáp án đúng Câu {idx+1}:",
                    options=q['options'],
                    index=q['options'].index(current_ans) if current_ans in q['options'] else 0,
                    key=f"config_ans_{idx}"
                )
                st.session_state.quiz_data[idx]['answer'] = correct_ans
                st.write("---")

        # Tạo mã mã hóa link
        payload = {
            "students": st.session_state.student_list,
            "quiz": st.session_state.quiz_data
        }
        encoded_str = encode_data(payload)
        
        app_url = st.context.headers.get("Host", "")
        if app_url:
            full_share_url = f"https://{app_url}/?data={encoded_str}"
        else:
            full_share_url = f"?data={encoded_str}"
        
        st.subheader("🔗 LINK DÀNH RIÊNG CHO HỌC SINH (GỬI QUA ZALO):")
        st.code(full_share_url, language="text")
        st.info("👉 Hãy sao chép link trên gửi qua Zalo. Khi học sinh bấm vào link này, giao diện của Giáo viên sẽ tự động ẩn đi!")

# ----------------------------------------------------
# CASE 2: MÀN HÌNH HỌC SINH (Mở từ Link Zalo chứa ?data=...)
# ----------------------------------------------------
else:
    # Ẩn thanh Sidebar của giáo viên hoàn toàn bằng CSS
    st.markdown(
        """
        <style>
            [data-testid="stSidebar"] {display: none;}
            [data-testid="collapsedControl"] {display: none;}
        </style>
        """,
        unsafe_allow_html=True
    )
    
    st.title("📚 Màn Hình Làm Bài Học Sinh")

    if not st.session_state.student_list or not st.session_state.quiz_data:
        st.error("❌ Link bài kiểm tra không hợp lệ hoặc đã bị lỗi! Vui lòng liên hệ lại Giáo viên.")
    else:
        selected_student = st.selectbox("👉 Chọn Họ và Tên của bạn:", ["-- Chọn đúng tên bạn --"] + st.session_state.student_list)
        
        if selected_student != "-- Chọn đúng tên bạn --":
            if selected_student in st.session_state.completed_students:
                st.warning(f"❌ Học sinh **{selected_student}** đã hoàn thành bài kiểm tra này rồi!")
            else:
                st.success(f"Xin chào **{selected_student}**, hãy hoàn thành các câu hỏi dưới đây:")
                
                user_answers = {}
                with st.form("quiz_form"):
                    for idx, q in enumerate(st.session_state.quiz_data):
                        st.markdown(f"**Câu {idx+1}:** {q['question']}")
                        user_answers[idx] = st.radio(f"Chọn đáp án:", q['options'], key=f"student_q_{idx}")
                        st.write("---")
                    
                    submit_btn = st.form_submit_button("NỘP BÀI KIỂM TRA")
                    
                    if submit_btn:
                        score = 0
                        total = len(st.session_state.quiz_data)
                        for idx, q in enumerate(st.session_state.quiz_data):
                            if user_answers[idx] == q['answer']:
                                score += 1
                        
                        st.session_state.completed_students.add(selected_student)
                        st.balloons()
                        st.success(f"🎉 Bạn đã nộp bài thành công! Kết quả: {score}/{total} câu đúng.")

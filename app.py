import streamlit as st
import pandas as pd
import json
import re
import docx

st.set_page_config(page_title="Kiểm Tra Bài Cũ", layout="centered")
st.title("📚 App Kiểm Tra Bài Cũ Học Sinh")

# Khởi tạo lưu trữ trong session
if 'completed_students' not in st.session_state:
    st.session_state.completed_students = set()

if 'quiz_data' not in st.session_state:
    st.session_state.quiz_data = []

# Hàm hỗ trợ đọc câu hỏi từ file Word/TXT
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
            
            if len(options) >= 2:
                questions.append({
                    "question": q_text,
                    "options": options,
                    "answer": options[0]  # Mặc định chọn đáp án đầu tiên
                })
    return questions

# ----------------------------------------------------
# PHẦN 1: DÀNH CHO GIÁO VIÊN
# ----------------------------------------------------
with st.sidebar:
    st.header("⚙️ DÀNH CHO GIÁO VIÊN")
    
    # 1. Tải danh sách học sinh
    st.subheader("1. Tải danh sách lớp")
    students_file = st.file_uploader("Tải file Excel/CSV danh sách lớp", type=["csv", "xlsx"], key="students_upload")
    student_list = []
    
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
            
            student_list = [name for name in found_names if "HoTen" not in name and "Họ tên" not in name]
            
            if student_list:
                st.success(f"Đã tải {len(student_list)} học sinh!")
            else:
                st.error("Không tìm thấy danh sách tên trong file.")
        except Exception:
            st.error("Lỗi đọc file danh sách học sinh!")

    st.markdown("---")
    
    # 2. Tải câu hỏi lên
    st.subheader("2. Tải bộ câu hỏi")
    st.caption("Chấp nhận file Word (.docx), TXT hoặc Excel (.xlsx)")
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
                # Giả định cấu hình cột: Câu hỏi | Lựa chọn A | Lựa chọn B | Lựa chọn C | Lựa chọn D
                for _, row in df_q.iterrows():
                    cols = row.dropna().tolist()
                    if len(cols) >= 3:
                        q_title = str(cols[0])
                        opts = [str(c) for c in cols[1:]]
                        parsed_q.append({
                            "question": q_title,
                            "options": opts,
                            "answer": opts[0]
                        })
            
            if parsed_q and not st.session_state.quiz_data:
                st.session_state.quiz_data = parsed_q
                st.success(f"Đã nạp {len(parsed_q)} câu hỏi!")
        except Exception as e:
            st.error(f"Lỗi đọc file câu hỏi: {str(e)}")

    st.markdown("---")
    st.subheader("📊 THỐNG KÊ LÀM BÀI")
    st.metric("Số HS đã nộp bài:", len(st.session_state.completed_students))
    if st.session_state.completed_students:
        st.write("Danh sách HS đã nộp:")
        for name in st.session_state.completed_students:
            st.write(f"- {name}")

# ----------------------------------------------------
# PHẦN 2: CHỈNH SỬA & DUYỆT ĐÁP ÁN ĐÚNG (GIÁO VIÊN)
# ----------------------------------------------------
if st.session_state.quiz_data:
    with st.expander("📝 CẤU HÌNH & CHỌN ĐÁP ÁN ĐÚNG CHO BỘ CÂU HỎI", expanded=True):
        st.info("Hãy chọn chính xác ĐÁP ÁN ĐÚNG cho từng câu hỏi bên dưới trước khi cho học sinh làm bài:")
        
        for idx, q in enumerate(st.session_state.quiz_data):
            st.markdown(f"**Câu {idx+1}:** {q['question']}")
            
            # Chọn đáp án đúng cho câu hỏi
            correct_ans = st.selectbox(
                f"Chọn đáp án đúng cho Câu {idx+1}:",
                options=q['options'],
                index=q['options'].index(q['answer']) if q['answer'] in q['options'] else 0,
                key=f"config_ans_{idx}"
            )
            # Cập nhật đáp án đúng vào session
            st.session_state.quiz_data[idx]['answer'] = correct_ans
            st.write("---")

# ----------------------------------------------------
# PHẦN 3: DÀNH CHO HỌC SINH LÀM BÀI
# ----------------------------------------------------
st.subheader("📝 Màn Hình Làm Bài Học Sinh")

if not student_list:
    st.info("👈 Giáo viên vui lòng mở thanh menu bên trái để tải danh sách lớp!")
elif not st.session_state.quiz_data:
    st.info("👈 Giáo viên vui lòng tải file câu hỏi (Word, TXT, Excel) ở menu bên trái.")
else:
    selected_student = st.selectbox("👉 Chọn Họ và Tên của bạn:", ["-- Chọn đúng tên bạn --"] + student_list)
    
    if selected_student != "-- Chọn đúng tên bạn --":
        if selected_student in st.session_state.completed_students:
            st.warning(f"❌ Học sinh **{selected_student}** đã hoàn thành bài kiểm tra này rồi! Bạn không thể làm lại.")
        else:
            st.success(f"Xin chào **{selected_student}**, hãy trả lời các câu hỏi dưới đây:")
            
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

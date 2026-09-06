import streamlit as st
import pandas as pd
import json
import os
import re
import docx

# Cấu hình đường dẫn lưu file dữ liệu chung trên server
DATA_FILE = "app_database.json"

st.set_page_config(page_title="Kiểm Tra Bài Cũ", layout="centered")
st.title("📚 App Kiểm Tra Bài Cũ Học Sinh")

# ----------------------------------------------------
# HÀM ĐỌC / GHI DỮ LIỆU DÙNG CHUNG CHO TẤT CẢ USER
# ----------------------------------------------------
def load_global_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "student_list": [],
        "quiz_data": [],
        "completed_students": []
    }

def save_global_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# Load dữ liệu chung khi khởi chạy
global_db = load_global_data()

# Hàm hỗ trợ bóc tách câu hỏi từ Word/TXT
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
                    "answer": options[0]  # Mặc định lấy đáp án đầu
                })
    return questions

# ----------------------------------------------------
# PHẦN 1: DÀNH CHO GIÁO VIÊN (CÀI ĐẶT & NẠP ĐỀ)
# ----------------------------------------------------
with st.sidebar:
    st.header("⚙️ DÀNH CHO GIÁO VIÊN")
    
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
            
            student_list = [name for name in found_names if "HoTen" not in name and "Họ tên" not in name]
            
            if student_list:
                global_db["student_list"] = student_list
                save_global_data(global_db)
                st.success(f"Đã lưu {len(student_list)} học sinh vào hệ thống!")
                st.rerun()
            else:
                st.error("Không tìm thấy tên trong file.")
        except Exception:
            st.error("Lỗi đọc file danh sách học sinh!")

    st.markdown("---")
    
    # 2. Tải câu hỏi lên
    st.subheader("2. Tải bộ câu hỏi")
    st.caption("Chấp nhận Word (.docx), TXT hoặc Excel (.xlsx)")
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
                        q_title = str(cols[0])
                        opts = [str(c) for c in cols[1:]]
                        parsed_q.append({
                            "question": q_title,
                            "options": opts,
                            "answer": opts[0]
                        })
            
            if parsed_q:
                global_db["quiz_data"] = parsed_q
                save_global_data(global_db)
                st.success(f"Đã lưu {len(parsed_q)} câu hỏi vào hệ thống!")
                st.rerun()
        except Exception as e:
            st.error(f"Lỗi đọc file câu hỏi: {str(e)}")

    st.markdown("---")
    # Nút xóa dữ liệu làm mới bài kiểm tra
    if st.button("🗑️ Đặt lại / Xóa bài kiểm tra này"):
        if os.path.exists(DATA_FILE):
            os.remove(DATA_FILE)
        st.success("Đã xóa toàn bộ dữ liệu! Bạn có thể nạp bài mới.")
        st.rerun()

    st.markdown("---")
    st.subheader("📊 THỐNG KÊ LÀM BÀI")
    completed = global_db.get("completed_students", [])
    st.metric("Số HS đã nộp bài:", len(completed))
    if completed:
        st.write("Danh sách HS đã nộp:")
        for name in completed:
            st.write(f"- {name}")

# ----------------------------------------------------
# PHẦN 2: CHỈNH SỬA & CHỌN ĐÁP ÁN ĐÚNG (GIÁO VIÊN)
# ----------------------------------------------------
if global_db.get("quiz_data"):
    with st.expander("📝 ĐÁP ÁN ĐÚNG CỦA BỘ CÂU HỎI (GIÁO VIÊN)", expanded=False):
        st.info("Bấm vào đây để xem hoặc thay đổi đáp án đúng trước khi học sinh làm bài:")
        
        has_changed = False
        for idx, q in enumerate(global_db["quiz_data"]):
            st.markdown(f"**Câu {idx+1}:** {q['question']}")
            
            current_ans = q.get('answer', q['options'][0])
            correct_ans = st.selectbox(
                f"Đáp án đúng Câu {idx+1}:",
                options=q['options'],
                index=q['options'].index(current_ans) if current_ans in q['options'] else 0,
                key=f"config_ans_{idx}"
            )
            if correct_ans != current_ans:
                global_db["quiz_data"][idx]['answer'] = correct_ans
                has_changed = True
            st.write("---")
        
        if has_changed:
            save_global_data(global_db)
            st.success("Đã cập nhật đáp án đúng!")

# ----------------------------------------------------
# PHẦN 3: DÀNH CHO HỌC SINH LÀM BÀI
# ----------------------------------------------------
st.subheader("📝 Màn Hình Làm Bài Học Sinh")

student_list = global_db.get("student_list", [])
quiz_data = global_db.get("quiz_data", [])
completed_students = global_db.get("completed_students", [])

if not student_list:
    st.info("👈 Giáo viên vui lòng mở menu bên trái để tải danh sách lớp lên trước!")
elif not quiz_data:
    st.info("👈 Giáo viên vui lòng mở menu bên trái để tải file câu hỏi lên trước!")
else:
    selected_student = st.selectbox("👉 Chọn Họ và Tên của bạn:", ["-- Chọn đúng tên bạn --"] + student_list)
    
    if selected_student != "-- Chọn đúng tên bạn --":
        if selected_student in completed_students:
            st.warning(f"❌ Học sinh **{selected_student}** đã hoàn thành bài kiểm tra này rồi! Bạn không thể làm lại.")
        else:
            st.success(f"Xin chào **{selected_student}**, hãy trả lời các câu hỏi dưới đây:")
            
            user_answers = {}
            with st.form("quiz_form"):
                for idx, q in enumerate(quiz_data):
                    st.markdown(f"**Câu {idx+1}:** {q['question']}")
                    user_answers[idx] = st.radio(f"Chọn đáp án:", q['options'], key=f"student_q_{idx}")
                    st.write("---")
                
                submit_btn = st.form_submit_button("NỘP BÀI KIỂM TRA")
                
                if submit_btn:
                    score = 0
                    total = len(quiz_data)
                    for idx, q in enumerate(quiz_data):
                        if user_answers[idx] == q['answer']:
                            score += 1
                    
                    # Cập nhật danh sách đã làm bài vào file chung
                    if selected_student not in global_db["completed_students"]:
                        global_db["completed_students"].append(selected_student)
                        save_global_data(global_db)
                    
                    st.balloons()
                    st.success(f"🎉 Bạn đã nộp bài thành công! Kết quả: {score}/{total} câu đúng.")

import streamlit as st
import pandas as pd
import google.generativeai as genai
import json
from PIL import Image

# CẤU HÌNH API KEY (Dán mã khóa của bạn vào giữa 2 dấu ngoặc kép ở dòng dưới)
GEMINI_API_KEY = "AQ.Ab8RN6LAdAxqsS0oCV37oXpDBar1_zWEryngmzcomDPINt_tlw"

genai.configure(api_key=GEMINI_API_KEY)

st.set_page_config(page_title="Kiểm Tra Bài Cũ", layout="centered")
st.title("📚 App Kiểm Tra Bài Cũ Học Sinh")

# Bộ nhớ lưu trữ tạm thời
if 'completed_students' not in st.session_state:
    st.session_state.completed_students = set()

if 'quiz_data' not in st.session_state:
    st.session_state.quiz_data = None

# ----------------------------------------------------
# PHẦN 1: DÀNH CHO GIÁO VIÊN (Thanh bên trái)
# ----------------------------------------------------
with st.sidebar:
    st.header("⚙️ DÀNH CHO GIÁO VIÊN")
    
    # 1. Tải danh sách học sinh
    st.subheader("1. Tải danh sách lớp")
    students_file = st.file_uploader("Tải file Excel/CSV (Cần có cột tên là 'HoTen')", type=["csv", "xlsx"])
    student_list = []
    if students_file:
        try:
            if students_file.name.endswith('.csv'):
                df_students = pd.read_csv(students_file)
            else:
                df_students = pd.read_excel(students_file)
            student_list = df_students['HoTen'].tolist()
            st.success(f"Đã tải {len(student_list)} học sinh.")
        except:
            st.error("File Excel cần có cột tên đúng chữ: HoTen")

    # 2. Tải ảnh bài học
    st.subheader("2. Tải ảnh nội dung bài học")
    lesson_image = st.file_uploader("Tải ảnh chụp trang sách", type=["jpg", "jpeg", "png"])
    
    # 3. Chọn số câu hỏi
    st.subheader("3. Cấu hình câu hỏi")
    num_questions = st.number_input("Số câu hỏi AI tự sinh:", min_value=1, max_value=20, value=5)
    
    # Nút tạo đề
    if st.button("🚀 AI Tạo Câu Hỏi") and lesson_image:
        with st.spinner("AI đang đọc sách và soạn câu hỏi lý thuyết..."):
            try:
                img = Image.open(lesson_image)
                prompt = f"""
                Bạn là giáo viên. Đọc hình ảnh bài học này và tạo ra đúng {num_questions} câu hỏi trắc nghiệm lý thuyết để kiểm tra bài cũ.
                Yêu cầu:
                1. Trộn lẫn các mức độ Dễ, Khá, Khó để học sinh nắm vững bài.
                2. Trả về ĐÚNG định dạng JSON sau (không thêm văn bản ngoài):
                [
                    {{
                        "question": "Nội dung câu hỏi?",
                        "options": ["A. Đáp án 1", "B. Đáp án 2", "C. Đáp án 3", "D. Đáp án 4"],
                        "answer": "A. Đáp án 1",
                        "level": "Dễ"
                    }}
                ]
                """
                model = genai.GenerativeModel('gemini-1.5-flash')
                response = model.generate_content([prompt, img])
                
                clean_json = response.text.replace("```json", "").replace("```", "").strip()
                st.session_state.quiz_data = json.loads(clean_json)
                st.success("Tạo đề thành công!")
            except Exception as e:
                st.error("Có lỗi xảy ra khi tạo câu hỏi. Hãy thử lại!")

    # 4. Thống kê
    st.markdown("---")
    st.subheader("📊 THỐNG KÊ LÀM BÀI")
    st.metric("Số HS đã làm (Không tính trùng):", len(st.session_state.completed_students))
    if st.session_state.completed_students:
        st.write("Danh sách HS đã nộp:")
        for name in st.session_state.completed_students:
            st.write(f"- {name}")

# ----------------------------------------------------
# PHẦN 2: DÀNH CHO HỌC SINH LÀM BÀI
# ----------------------------------------------------
st.subheader("📝 Màn Hình Làm Bài Học Sinh")

if not student_list:
    st.info("👈 Giáo viên vui lòng mở thanh menu bên trái để tải danh sách lớp và tạo đề trước!")
elif not st.session_state.quiz_data:
    st.info("👈 Giáo viên vui lòng tải ảnh trang sách và bấm 'AI Tạo Câu Hỏi'.")
else:
    # Học sinh chọn tên
    selected_student = st.selectbox("👉 Chọn Họ và Tên của bạn:", ["-- Chọn đúng tên bạn --"] + student_list)
    
    if selected_student != "-- Chọn đúng tên bạn --":
        if selected_student in st.session_state.completed_students:
            st.warning(f"❌ Học sinh **{selected_student}** đã hoàn thành bài kiểm tra này rồi! Bạn không thể làm lại.")
        else:
            st.success(f"Xin chào **{selected_student}**, hãy trả lời các câu hỏi dưới đây:")
            
            user_answers = {}
            with st.form("quiz_form"):
                for idx, q in enumerate(st.session_state.quiz_data):
                    st.markdown(f"**Câu {idx+1} [{q['level']}]:** {q['question']}")
                    user_answers[idx] = st.radio(f"Chọn đáp án:", q['options'], key=f"q_{idx}")
                    st.write("---")
                
                submit_btn = st.form_submit_button("NỘP BÀI KIỂM TRA")
                
                if submit_btn:
                    score = 0
                    total = len(st.session_state.quiz_data)
                    for idx, q in enumerate(st.session_state.quiz_data):
                        if user_answers[idx] == q['answer']:
                            score += 1
                    
                    # Ghi nhận học sinh đã làm
                    st.session_state.completed_students.add(selected_student)
                    st.balloons()
                    st.success(f"🎉 Bạn đã nộp bài thành công! Kết quả: {score}/{total} câu đúng.")

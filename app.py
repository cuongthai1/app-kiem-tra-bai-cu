import streamlit as st
import pandas as pd
import google.generativeai as genai
import json
import re
from PIL import Image
import docx
from pypdf import PdfReader

# Lấy API Key từ Streamlit Secrets
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

st.set_page_config(page_title="Kiểm Tra Bài Cũ", layout="centered")
st.title("📚 App Kiểm Tra Bài Cũ Học Sinh")

if 'completed_students' not in st.session_state:
    st.session_state.completed_students = set()

if 'quiz_data' not in st.session_state:
    st.session_state.quiz_data = None

# Hàm khởi tạo Gemini model tương thích linh hoạt
def get_working_model():
    models_to_try = [
        'gemini-1.5-flash',
        'gemini-1.5-flash-latest',
        'gemini-2.0-flash',
        'gemini-2.5-flash',
        'gemini-1.5-pro'
    ]
    for model_name in models_to_try:
        try:
            return genai.GenerativeModel(model_name)
        except Exception:
            continue
    return genai.GenerativeModel('gemini-1.5-flash')

# Hàm bóc tách và tự động vá lỗi cấu trúc JSON khi sinh số lượng lớn câu hỏi
def parse_json_safely(text):
    clean_text = text.strip()
    if "```json" in clean_text:
        clean_text = clean_text.split("```json")[1].split("```")[0].strip()
    elif "```" in clean_text:
        clean_text = clean_text.split("```")[1].split("```")[0].strip()
    
    # Tìm đoạn JSON mảng []
    match = re.search(r'\[.*\]', clean_text, re.DOTALL)
    if match:
        clean_text = match.group(0)
    else:
        # Tự động vá ngoặc đóng nếu bị dở dang
        if clean_text.startswith("[") and not clean_text.endswith("]"):
            clean_text += "]"

    return json.loads(clean_text)

# ----------------------------------------------------
# PHẦN 1: DÀNH CHO GIÁO VIÊN
# ----------------------------------------------------
with st.sidebar:
    st.header("⚙️ DÀNH CHO GIÁO VIÊN")
    
    # 1. Tải danh sách học sinh
    st.subheader("1. Tải danh sách lớp")
    students_file = st.file_uploader("Tải file Excel/CSV", type=["csv", "xlsx"])
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
                st.success(f"Đã tải thành công {len(student_list)} học sinh!")
            else:
                st.error("Không tìm thấy danh sách tên trong file Excel.")
        except Exception:
            st.error("Lỗi đọc file Excel. Vui lòng kiểm tra lại định dạng file!")

    # 2. Tải bài học (PDF, Word, Ảnh)
    st.subheader("2. Tải tài liệu bài học")
    lesson_file = st.file_uploader("Tải file PDF, Word (.docx) hoặc Ảnh", type=["pdf", "docx", "jpg", "jpeg", "png"])
    
    # 3. Cấu hình câu hỏi
    st.subheader("3. Cấu hình câu hỏi")
    num_questions = st.number_input("Số câu hỏi AI tự sinh:", min_value=1, max_value=20, value=5)
    
    if st.button("🚀 AI Tạo Câu Hỏi") and lesson_file:
        with st.spinner(f"AI đang soạn {num_questions} câu hỏi từ tài liệu, vui lòng chờ trong giây lát..."):
            try:
                file_ext = lesson_file.name.split('.')[-1].lower()
                
                # Tối ưu hóa Prompt ngắn gọn và xuất dữ liệu nhanh
                prompt = f"""
                Bạn là giáo viên. Hãy tạo đúng {num_questions} câu hỏi trắc nghiệm lý thuyết từ bài học.
                Yêu cầu:
                - Kết quả trả về duy nhất 1 mảng JSON thuần túy theo đúng định dạng sau:
                [
                    {{
                        "question": "Câu hỏi?",
                        "options": ["A. Đáp án 1", "B. Đáp án 2", "C. Đáp án 3", "D. Đáp án 4"],
                        "answer": "A. Đáp án 1",
                        "level": "Dễ"
                    }}
                ]
                Không được thêm bất kỳ văn bản chào hỏi hay giải thích nào bên ngoài mảng JSON.
                """
                
                model = get_working_model()
                response_text = ""

                # Xử lý File PDF
                if file_ext == 'pdf':
                    reader = PdfReader(lesson_file)
                    extracted_text = "".join([page.extract_text() or "" for page in reader.pages]).strip()
                    
                    if len(extracted_text) > 50:
                        res = model.generate_content([prompt, f"Nội dung bài học:\n{extracted_text}"])
                    else:
                        lesson_file.seek(0)
                        pdf_bytes = lesson_file.read()
                        pdf_part = {"mime_type": "application/pdf", "data": pdf_bytes}
                        res = model.generate_content([prompt, pdf_part])
                    response_text = res.text

                # Xử lý File Word (.docx)
                elif file_ext in ['docx', 'doc']:
                    doc = docx.Document(lesson_file)
                    doc_text = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
                    res = model.generate_content([prompt, f"Nội dung bài học:\n{doc_text}"])
                    response_text = res.text

                # Xử lý File Ảnh
                elif file_ext in ['jpg', 'jpeg', 'png']:
                    img = Image.open(lesson_file)
                    res = model.generate_content([prompt, img])
                    response_text = res.text

                # Parse JSON an toàn
                st.session_state.quiz_data = parse_json_safely(response_text)
                st.success(f"Đã tạo thành công {len(st.session_state.quiz_data)} câu hỏi!")

            except Exception as e:
                st.error(f"Chi tiết lỗi: {str(e)}")

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
    st.info("👈 Giáo viên vui lòng tải tài liệu (PDF, Word, Ảnh) và bấm 'AI Tạo Câu Hỏi'.")
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
                    st.markdown(f"**Câu {idx+1} [{q.get('level', 'Trung bình')}]:** {q['question']}")
                    user_answers[idx] = st.radio(f"Chọn đáp án:", q['options'], key=f"q_{idx}")
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

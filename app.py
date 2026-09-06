import streamlit as st
import pandas as pd
import json
import re
import docx
import base64
import zlib

st.set_page_config(page_title="Hệ Thống Kiểm Tra Bài Cũ", layout="centered")

# ----------------------------------------------------
# HÀM NÉN & MÃ HÓA DỮ LIỆU
# ----------------------------------------------------
def encode_data(data):
    try:
        json_str = json.dumps(data, ensure_ascii=False)
        compressed = zlib.compress(json_str.encode('utf-8'))
        return base64.urlsafe_b64encode(compressed).decode('utf-8')
    except Exception as e:
        return ""

def decode_data(encoded_str):
    try:
        compressed_bytes = base64.urlsafe_b64decode(encoded_str)
        decompressed = zlib.decompress(compressed_bytes)
        return json.loads(decompressed.decode('utf-8'))
    except Exception as e:
        return None

# Đọc dữ liệu từ URL khi học sinh mở link
query_params = st.query_params
url_data = None
if "data" in query_params:
    url_data = decode_data(query_params["data"])

# Khởi tạo Session State
if 'users_db' not in st.session_state:
    st.session_state.users_db = url_data.get("users", {}) if url_data else {}

if 'quiz_data' not in st.session_state:
    st.session_state.quiz_data = url_data.get("quiz", []) if url_data else []

if 'results' not in st.session_state:
    st.session_state.results = url_data.get("results", {}) if url_data else {}

# Đồng bộ nếu url_data có dữ liệu mới hơn
if url_data:
    if url_data.get("users"):
        st.session_state.users_db = url_data.get("users")
    if url_data.get("quiz"):
        st.session_state.quiz_data = url_data.get("quiz")

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
# MÀN HÌNH CHÍNH
# ----------------------------------------------------
st.title("🔐 HỆ THỐNG KIỂM TRA BÀI CŨ")

role = st.radio("👉 Chọn vai trò của bạn:", ["Học sinh", "Giáo viên"], horizontal=True)

# ----------------------------------------------------
# PHẦN 1: GIAO DIỆN HỌC SINH
# ----------------------------------------------------
if role == "Học sinh":
    st.subheader("👨‍🎓 Dành Cho Học Sinh Làm Bài")
    
    if not st.session_state.users_db or not st.session_state.quiz_data:
        st.warning("⚠️ Chưa có bài kiểm tra nào được nạp hoặc Link bị thiếu dữ liệu! Vui lòng liên hệ Giáo viên để nhận Link chuẩn.")
    else:
        # Lấy danh sách tên học sinh
        student_names = list(st.session_state.users_db.keys())
        
        selected_student = st.selectbox("1. Chọn Họ và Tên của bạn:", ["-- Chọn tên bạn --"] + student_names)
        input_pass = st.text_input("2. Nhập Mật khẩu của bạn:", type="password")
        
        if selected_student != "-- Chọn tên bạn --" and input_pass:
            correct_pass = str(st.session_state.users_db[selected_student]['password']).strip()
            
            if input_pass.strip() != correct_pass:
                st.error("❌ Mật khẩu không chính xác! Vui lòng kiểm tra lại.")
            else:
                st.success(f"✅ Đăng nhập thành công! Xin chào học sinh **{selected_student}**")
                
                # Kiểm tra nếu học sinh đã làm bài
                if selected_student in st.session_state.results:
                    res = st.session_state.results[selected_student]
                    st.warning(f"❌ Bạn đã hoàn thành bài kiểm tra này rồi!")
                    st.info(f"📊 Kết quả bài làm: **{res['score']}/{res['total']} câu đúng**")
                else:
                    st.markdown("---")
                    st.markdown("### 📝 BÀI KIỂM TRA")
                    
                    user_answers = {}
                    with st.form("quiz_form"):
                        for idx, q in enumerate(st.session_state.quiz_data):
                            st.markdown(f"**Câu {idx+1}:** {q['question']}")
                            user_answers[idx] = st.radio(f"Chọn đáp án:", q['options'], key=f"q_{idx}")
                            st.write("---")
                        
                        submit_btn = st.form_submit_button("NỘP BÀI KIỂM TRA")
                        
                        if submit_btn:
                            score = 0
                            total = len(st.session_state.quiz_data)
                            for idx, q in enumerate(st.session_state.quiz_data):
                                if user_answers[idx] == q['answer']:
                                    score += 1
                            
                            # Lưu kết quả bài làm
                            st.session_state.results[selected_student] = {
                                "score": score,
                                "total": total
                            }
                            st.balloons()
                            st.success(f"🎉 Bạn đã nộp bài thành công! Kết quả: {score}/{total} câu đúng.")

# ----------------------------------------------------
# PHẦN 2: GIAO DIỆN GIÁO VIÊN
# ----------------------------------------------------
else:
    st.subheader("👨‍🏫 Dành Cho Giáo Viên Quản Lý")
    
    # Ẩn hoàn toàn thông báo mật khẩu mặc định
    admin_pass = st.text_input("Nhập Mật khẩu Giáo viên:", type="password")
    
    # Mật khẩu quản lý mặc định là admin123
    if admin_pass == "admin123":
        st.success("✅ Đã xác minh quyền Giáo viên thành công!")
        
        tab1, tab2, tab3 = st.tabs(["1. Tải Dữ Liệu", "2. Duyệt Đáp Án & Tạo Link Zalo", "3. Báo Cáo Kết Quả"])
        
        with tab1:
            st.markdown("#### A. Tải danh sách Học sinh & Mật khẩu")
            st.caption("File Excel/CSV gồm: Cột 1 (Họ Tên), Cột 2 (Mật Khẩu - Tùy chọn). Nếu không có Cột Mật khẩu, hệ thống tự đặt mặc định là '123456'.")
            users_file = st.file_uploader("Tải file Danh sách Lớp", type=["csv", "xlsx"])
            
            if users_file:
                try:
                    if users_file.name.endswith('.csv'):
                        df = pd.read_csv(users_file, header=None)
                    else:
                        df = pd.read_excel(users_file, header=None)
                    
                    users_dict = {}
                    for _, row in df.iterrows():
                        vals = [str(v).strip() for v in row.dropna().tolist() if str(v).strip()]
                        if vals:
                            name = vals[0]
                            # Loại bỏ các tiêu đề cột nếu có
                            if name.lower() not in ['hoten', 'họ tên', 'ho ten', 'stt', 'tên học sinh', 'họ và tên']:
                                pwd = vals[1] if len(vals) >= 2 else "123456"
                                users_dict[name] = {"password": pwd}
                    
                    if users_dict:
                        st.session_state.users_db = users_dict
                        st.success(f"✅ Đã nạp thành công {len(users_dict)} học sinh vào hệ thống!")
                    else:
                        st.error("Không bóc tách được danh sách tên từ file.")
                except Exception as e:
                    st.error(f"Lỗi đọc file danh sách: {str(e)}")

            st.markdown("---")
            st.markdown("#### B. Tải bộ câu hỏi")
            quiz_file = st.file_uploader("Tải file câu hỏi (.docx, .txt, .xlsx)", type=["docx", "txt", "xlsx"])
            
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
                        st.success(f"✅ Đã nạp thành công {len(parsed_q)} câu hỏi!")
                except Exception as e:
                    st.error(f"Lỗi đọc file câu hỏi: {str(e)}")

        with tab2:
            if st.session_state.quiz_data and st.session_state.users_db:
                st.markdown("#### Cấu hình đáp án đúng cho câu hỏi:")
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

                # Mã hóa dữ liệu gói vào Link
                payload = {
                    "users": st.session_state.users_db,
                    "quiz": st.session_state.quiz_data
                }
                encoded_str = encode_data(payload)
                
                app_url = st.context.headers.get("Host", "")
                full_share_url = f"https://{app_url}/?data={encoded_str}" if app_url else f"?data={encoded_str}"
                
                st.subheader("🔗 LINK BÀI KIỂM TRA GỬI QUA ZALO CHO HỌC SINH:")
                st.code(full_share_url, language="text")
                st.info("👉 Copy đường link trên và gửi cho học sinh. Khi học sinh bấm vào link, danh sách tên sẽ hiện đầy đủ!")
            else:
                st.warning("⚠️ Vui lòng nạp đủ Danh sách học sinh và Bộ câu hỏi ở Tab 1 trước!")

        with tab3:
            st.markdown("#### 📊 THỐNG KÊ KẾT QUẢ BÀI LÀM")
            if not st.session_state.results:
                st.info("Chưa có học sinh nào nộp bài trong phiên này.")
            else:
                total_students = len(st.session_state.users_db)
                done_count = len(st.session_state.results)
                
                st.metric("Số học sinh đã làm bài:", f"{done_count}/{total_students}")
                
                res_data = []
                for student, data in st.session_state.results.items():
                    res_data.append({
                        "Họ và Tên Học Sinh": student,
                        "Kết quả làm bài": f"{data['score']}/{data['total']} câu đúng"
                    })
                
                df_res = pd.DataFrame(res_data)
                st.dataframe(df_res, use_container_width=True)
    elif admin_pass:
        st.error("❌ Mật khẩu Giáo viên không chính xác!")

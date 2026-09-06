import streamlit as st
import pandas as pd
import json
import re
import docx
import base64
import zlib
import xml.etree.ElementTree as ET

st.set_page_config(page_title="Hệ Thống Kiểm Tra Bài Cũ", layout="centered")

# Nhúng thư viện KaTeX để hiển thị công thức Lý / Toán
st.markdown(
    """
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.8/dist/katex.min.css">
    """,
    unsafe_allow_html=True
)

# ----------------------------------------------------
# HÀM BÓC TÁCH XML CÔNG THỨC TOÁN WORD (OMML)
# ----------------------------------------------------
def get_docx_text_with_math(docx_file):
    doc = docx.Document(docx_file)
    full_text = []
    
    ns = {
        'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
        'm': 'http://schemas.openxmlformats.org/officeDocument/2006/math'
    }

    for p in doc.paragraphs:
        p_xml = ET.fromstring(p._p.xml)
        para_text = ""
        
        for child in p_xml:
            tag = child.tag.split('}')[-1]
            if tag == 'r':
                texts = child.findall('.//w:t', ns)
                for t in texts:
                    if t.text:
                        para_text += t.text
            elif tag == 'oMath' or tag == 'oMathPara':
                math_texts = child.findall('.//m:t', ns)
                math_str = "".join([t.text for t in math_texts if t.text])
                if math_str:
                    para_text += f" {math_str} "
            else:
                texts = child.findall('.//w:t', ns)
                for t in texts:
                    if t.text:
                        para_text += t.text
                        
        if para_text.strip():
            full_text.append(para_text.strip())
            
    return "\n".join(full_text)

# ----------------------------------------------------
# HÀM XỬ LÝ KÝ HIỆU TOÁN & VẬT LÝ
# ----------------------------------------------------
def format_math_text(text):
    if not isinstance(text, str):
        return str(text)
    
    text = re.sub(r'\\\((.*?)\\\)', r'$\1$', text)
    text = re.sub(r'\\\[(.*?)\\\]', r'$$\1$$', text)
    
    return text

# ----------------------------------------------------
# HÀM NÉN & MÃ HÓA DỮ LIỆU
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

if url_data:
    if url_data.get("users"):
        st.session_state.users_db = url_data.get("users")
    if url_data.get("quiz"):
        st.session_state.quiz_data = url_data.get("quiz")

# ----------------------------------------------------
# HÀM BÓC TÁCH CÂU HỎI TỪ VĂN BẢN
# ----------------------------------------------------
def parse_questions_from_text(text):
    questions = []
    blocks = re.split(r'\n(?=Câu\s*\d+[\.\:\s])', text, flags=re.IGNORECASE)
    
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        
        opt_match = re.search(r'(?=\b[A-D][\.\:\)])', block)
        
        if opt_match:
            q_text = block[:opt_match.start()].strip()
            opts_part = block[opt_match.start():].strip()
            
            raw_options = re.split(r'\s*(?=\b[A-D][\.\:\)])', opts_part)
            options = [o.strip() for o in raw_options if o.strip()]
            
            if len(options) >= 2:
                q_lines = [l.strip() for l in q_text.split('\n') if l.strip()]
                full_q = " ".join(q_lines)
                
                questions.append({
                    "question": full_q,
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
        student_names = list(st.session_state.users_db.keys())
        
        selected_student = st.selectbox("1. Chọn Họ và Tên của bạn:", ["-- Chọn tên bạn --"] + student_names)
        input_pass = st.text_input("2. Nhập Mật khẩu của bạn:", type="password")
        
        if selected_student != "-- Chọn tên bạn --" and input_pass:
            correct_pass = str(st.session_state.users_db[selected_student]['password']).strip()
            
            if input_pass.strip() != correct_pass:
                st.error("❌ Mật khẩu không chính xác! Vui lòng kiểm tra lại.")
            else:
                st.success(f"✅ Đăng nhập thành công! Xin chào học sinh **{selected_student}**")
                
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
                            formatted_q = format_math_text(q['question'])
                            st.markdown(f"**{formatted_q}**")
                            
                            formatted_opts = [format_math_text(opt) for opt in q['options']]
                            
                            # Đặt index=None để MẶC ĐỊNH KHÔNG CÓ CHẤM ĐỎ nào được chọn
                            user_answers[idx] = st.radio(
                                f"Chọn đáp án:", 
                                formatted_opts, 
                                index=None, 
                                key=f"q_{idx}"
                            )
                            st.write("---")
                        
                        submit_btn = st.form_submit_button("NỘP BÀI KIỂM TRA")
                        
                        if submit_btn:
                            # Kiểm tra xem học sinh đã trả lời hết các câu chưa
                            unanswered = [i + 1 for i, ans in user_answers.items() if ans is None]
                            
                            if unanswered:
                                st.error(f"⚠️ Bạn chưa chọn đáp án cho các câu: {', '.join(map(str, unanswered))}. Vui lòng hoàn thành tất cả các câu trước khi nộp!")
                            else:
                                score = 0
                                total = len(st.session_state.quiz_data)
                                for idx, q in enumerate(st.session_state.quiz_data):
                                    formatted_opts = [format_math_text(opt) for opt in q['options']]
                                    formatted_ans = format_math_text(q['answer'])
                                    if user_answers[idx] == formatted_ans or user_answers[idx] == formatted_opts[0]:
                                        score += 1
                                
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
    
    admin_pass = st.text_input("Nhập Mật khẩu Giáo viên:", type="password")
    
    if admin_pass == "admin123":
        st.success("✅ Đã xác minh quyền Giáo viên thành công!")
        
        tab1, tab2, tab3 = st.tabs(["1. Tải Dữ Liệu", "2. Duyệt Đáp Án & Tạo Link Zalo", "3. Báo Cáo Kết Quả"])
        
        with tab1:
            st.markdown("#### A. Tải danh sách Học sinh & Mật khẩu")
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
                            if name.lower() not in ['hoten', 'họ tên', 'ho ten', 'stt', 'tên học sinh', 'họ và tên']:
                                pwd = vals[1] if len(vals) >= 2 else "123456"
                                users_dict[name] = {"password": pwd}
                    
                    if users_dict:
                        st.session_state.users_db = users_dict
                        st.success(f"✅ Đã nạp thành công {len(users_dict)} học sinh!")
                except Exception as e:
                    st.error(f"Lỗi đọc file danh sách: {str(e)}")

            st.markdown("---")
            st.markdown("#### B. Tải bộ câu hỏi (.docx, .txt, .xlsx)")
            quiz_file = st.file_uploader("Tải file câu hỏi", type=["docx", "txt", "xlsx"])
            
            if quiz_file:
                parsed_q = []
                file_ext = quiz_file.name.split('.')[-1].lower()
                try:
                    if file_ext == 'docx':
                        full_text = get_docx_text_with_math(quiz_file)
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
                        st.success(f"✅ Đã nạp thành công {len(parsed_q)} câu hỏi từ file Word!")
                    else:
                        st.error("Không bóc tách được câu hỏi nào. Vui lòng kiểm tra lại định dạng 'Câu 1.', 'Câu 2.'...")
                except Exception as e:
                    st.error(f"Lỗi đọc file câu hỏi: {str(e)}")

        with tab2:
            if st.session_state.quiz_data and st.session_state.users_db:
                st.markdown("#### Cấu hình & Xem trước bộ câu hỏi:")
                for idx, q in enumerate(st.session_state.quiz_data):
                    formatted_q = format_math_text(q['question'])
                    st.markdown(f"**{formatted_q}**")
                    
                    formatted_opts = [format_math_text(opt) for opt in q['options']]
                    current_ans = format_math_text(q.get('answer', q['options'][0]))
                    
                    correct_ans = st.selectbox(
                        f"Đáp án đúng cho Câu {idx+1}:",
                        options=formatted_opts,
                        index=formatted_opts.index(current_ans) if current_ans in formatted_opts else 0,
                        key=f"config_ans_{idx}"
                    )
                    st.session_state.quiz_data[idx]['answer'] = correct_ans
                    st.write("---")

                payload = {
                    "users": st.session_state.users_db,
                    "quiz": st.session_state.quiz_data
                }
                encoded_str = encode_data(payload)
                
                app_url = st.context.headers.get("Host", "")
                full_share_url = f"https://{app_url}/?data={encoded_str}" if app_url else f"?data={encoded_str}"
                
                st.subheader("🔗 LINK BÀI KIỂM TRA GỬI QUA ZALO CHO HỌC SINH:")
                st.code(full_share_url, language="text")
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

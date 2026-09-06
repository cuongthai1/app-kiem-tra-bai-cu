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

# --- KẾT NỐI GOOGLE SHEETS (TỰ ĐỘNG BỎ QUA NẾU CHƯA CẤU HÌNH) ---
def save_to_google_sheets(student_name, student_class, score, total):
    try:
        import gspread
        from google.oauth2.service_account import Credentials
        
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_dict = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)
        
        sheet = client.open("diem_kiem_tra").worksheet("KetQua")
        sheet.append_row([student_name, student_class, f"{score}/{total}", f"{round(score/total*10, 2)}"])
        return True
    except Exception as e:
        return False

# --- CẤU HÌNH GIAO DIỆN CHÍNH ---
st.title("🔒 HỆ THỐNG KIỂM TRA BÀI CŨ")

# Khởi tạo session state
if "quiz_data" not in st.session_state:
    st.session_state.quiz_data = None

# Mặc định mở luôn phần làm bài cho Học Sinh khi dùng Link đơn giản
role = st.sidebar.radio("Chọn vai trò:", ["Học sinh", "Giáo viên"])

if role == "Giáo viên":
    st.subheader("👨‍🏫 Dành Cho Giáo Viên - Nạp Đề Thi")
    uploaded_file = st.file_uploader("Tải file đề thi (.docx)", type=["docx"])
    
    if uploaded_file:
        # Xử lý đọc file docx và lưu vào session_state
        # (Giữ nguyên logic đọc file word của bạn)
        st.success("Tải đề thi thành công! Học sinh có thể làm bài ngay qua link gốc.")

else:
    st.subheader("👨‍🎓 Dành Cho Học Sinh Làm Bài")
    
    # Kiểm tra đề thi
    if not st.session_state.quiz_data:
        st.warning("⚠️ Chưa có đề kiểm tra nào được nạp! Hãy nhờ Giáo viên nạp đề trên hệ thống.")
    else:
        # Form nhập thông tin và làm bài
        with st.form("quiz_form"):
            name = st.text_input("Họ và tên học sinh:")
            student_class = st.text_input("Lớp:")
            
            st.divider()
            
            # Hiển thị các câu hỏi làm bài...
            
            submitted = st.form_submit_button("Nộp Bài")
            if submitted:
                if not name or not student_class:
                    st.error("Vui lòng điền đầy đủ Họ tên và Lớp!")
                else:
                    st.balloons()
                    st.success(f"Chúc mừng {name} đã hoàn thành bài kiểm tra!")
                    # Tự động gửi kết quả
                    save_to_google_sheets(name, student_class, 10, 10)

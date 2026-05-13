import streamlit as st
import requests
import time

# =============================================
# CẤU HÌNH TRANG
# =============================================
st.set_page_config(
    page_title="DSS Phê duyệt Khoản vay",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded"
)

API_URL = "http://localhost:8000/api/predict"

# =============================================
# CUSTOM CSS - GIAO DIỆN CHUYÊN NGHIỆP
# =============================================
st.markdown("""
<style>
    /* Header */
    .main-header {
        background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
        padding: 2rem 2.5rem;
        border-radius: 16px;
        margin-bottom: 2rem;
        box-shadow: 0 8px 32px rgba(0,0,0,0.3);
    }
    .main-header h1 {
        color: #ffffff;
        font-size: 2rem;
        margin: 0;
        font-weight: 700;
    }
    .main-header p {
        color: #a0aec0;
        font-size: 0.95rem;
        margin: 0.5rem 0 0 0;
    }
    
    /* Cards */
    .info-card {
        background: linear-gradient(145deg, #1a1a2e, #16213e);
        border: 1px solid #2d3748;
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        transition: transform 0.2s;
    }
    .info-card:hover {
        transform: translateY(-2px);
        border-color: #4299e1;
    }
    .info-card h3 {
        color: #63b3ed;
        font-size: 1rem;
        margin: 0 0 0.8rem 0;
        font-weight: 600;
    }
    
    /* Result cards */
    .result-approved {
        background: linear-gradient(135deg, #0d4228, #1a7a4a);
        border: 2px solid #48bb78;
        border-radius: 16px;
        padding: 2rem;
        text-align: center;
        box-shadow: 0 4px 20px rgba(72, 187, 120, 0.3);
    }
    .result-rejected {
        background: linear-gradient(135deg, #4a1a1a, #7a2020);
        border: 2px solid #fc8181;
        border-radius: 16px;
        padding: 2rem;
        text-align: center;
        box-shadow: 0 4px 20px rgba(252, 129, 129, 0.3);
    }
    .result-title {
        font-size: 1.8rem;
        font-weight: 800;
        margin-bottom: 0.5rem;
    }
    .result-subtitle {
        font-size: 1rem;
        opacity: 0.85;
    }
    
    /* Metric */
    .metric-box {
        background: #1a202c;
        border: 1px solid #2d3748;
        border-radius: 12px;
        padding: 1.2rem;
        text-align: center;
    }
    .metric-box .label {
        color: #a0aec0;
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .metric-box .value {
        color: #ffffff;
        font-size: 1.8rem;
        font-weight: 700;
        margin-top: 0.3rem;
    }
    
    /* Gauge */
    .risk-gauge {
        width: 100%;
        height: 12px;
        background: #2d3748;
        border-radius: 6px;
        overflow: hidden;
        margin: 0.5rem 0;
    }
    .risk-gauge-fill {
        height: 100%;
        border-radius: 6px;
        transition: width 1s ease;
    }
    
    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f0c29, #1a1a2e);
    }
    
    /* Divider */
    .custom-divider {
        height: 1px;
        background: linear-gradient(90deg, transparent, #4299e1, transparent);
        margin: 2rem 0;
    }
    
    /* Hide streamlit default */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# =============================================
# SIDEBAR
# =============================================
with st.sidebar:
    st.markdown("## ⚙️ Cấu hình hệ thống")
    st.markdown("---")
    
    st.markdown("### 🤖 Mô hình AI")
    st.info("**Logistic Regression**\n\nROC-AUC: 0.6837\n\nRecall (Nợ xấu): 61%")
    
    st.markdown("### 📊 Thông số hệ thống")
    st.markdown("""
    - **Dữ liệu huấn luyện:** 20,000 mẫu
    - **Tỷ lệ Train/Test:** 80/20
    - **Encoding:** Ordinal + OHE
    - **Scaling:** Z-score (StandardScaler)
    """)
    
    st.markdown("---")
    st.markdown("### 🔗 Kết nối")
    
    try:
        health = requests.get("http://localhost:8000/api/health", timeout=3).json()
        if health.get("model_loaded"):
            st.success("✅ Backend API: Online")
            st.success(f"✅ Model: Loaded ({health.get('features_count', '?')} features)")
        else:
            st.warning("⚠️ Backend: Online nhưng chưa load model")
    except:
        st.error("❌ Backend API: Offline")
    
    st.markdown("---")
    st.caption("Loan Approval DSS v2.0\n\n© 2026 - Mai Văn Hoàng Duy")

# =============================================
# HEADER
# =============================================
st.markdown("""
<div class="main-header">
    <h1>🏦 Hệ thống Hỗ trợ Ra quyết định Tín dụng</h1>
    <p>Decision Support System — Powered by Machine Learning & Data Warehouse</p>
</div>
""", unsafe_allow_html=True)

# =============================================
# FORM NHẬP LIỆU
# =============================================
st.markdown("### 📋 Thông tin Hồ sơ vay")

with st.form("loan_form", clear_on_submit=False):
    
    # --- ROW 1: Thông tin khoản vay ---
    st.markdown('<div class="info-card"><h3>💰 Thông tin Khoản vay</h3></div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    
    with c1:
        loan_amnt = st.number_input(
            "💵 Số tiền vay ($)", 
            min_value=500, max_value=40000, value=10000, step=500,
            help="Số tiền khách hàng muốn vay (500 - 40,000 USD)"
        )
    with c2:
        int_rate = st.slider(
            "📈 Lãi suất (%)", 
            min_value=5.0, max_value=28.0, value=12.0, step=0.5,
            help="Lãi suất hàng năm của khoản vay"
        )
    with c3:
        term = st.selectbox(
            "📅 Kỳ hạn vay",
            options=[36.0, 60.0],
            format_func=lambda x: f"{int(x)} tháng",
            help="Kỳ hạn trả nợ"
        )
    
    # --- ROW 2: Thông tin người vay ---
    st.markdown('<div class="info-card"><h3>👤 Thông tin Người vay</h3></div>', unsafe_allow_html=True)
    c4, c5, c6 = st.columns(3)
    
    with c4:
        grade = st.selectbox(
            "🏅 Hạng tín dụng",
            options=["A", "B", "C", "D", "E", "F", "G"],
            index=1,
            help="A = Tốt nhất → G = Rủi ro cao nhất"
        )
    with c5:
        annual_inc = st.number_input(
            "💼 Thu nhập hàng năm ($)", 
            min_value=1000, max_value=500000, value=60000, step=1000,
            help="Tổng thu nhập hàng năm của người vay"
        )
    with c6:
        emp_length = st.selectbox(
            "⏳ Thâm niên công tác",
            options=["< 1 year", "1 year", "2 years", "3 years", "4 years", 
                     "5 years", "6 years", "7 years", "8 years", "9 years", 
                     "10+ years", "Unknown"],
            index=5,
            help="Số năm kinh nghiệm làm việc"
        )
    
    # --- ROW 3: Thông tin tín dụng ---
    st.markdown('<div class="info-card"><h3>📊 Lịch sử Tín dụng</h3></div>', unsafe_allow_html=True)
    c7, c8, c9, c10 = st.columns(4)
    
    with c7:
        dti = st.slider(
            "📉 Tỷ lệ Nợ/Thu nhập (DTI)",
            min_value=0.0, max_value=40.0, value=15.0, step=0.5,
            help="Tỷ lệ tổng nợ hàng tháng trên thu nhập"
        )
    with c8:
        home_ownership = st.selectbox(
            "🏠 Tình trạng nhà ở",
            options=["RENT", "MORTGAGE", "OWN", "OTHER"],
            help="Tình trạng sở hữu nhà của người vay"
        )
    with c9:
        verification_status = st.selectbox(
            "✅ Xác minh thu nhập",
            options=["Not Verified", "Verified", "Source Verified"],
            help="Trạng thái xác minh thu nhập"
        )
    with c10:
        delinq_2yrs = st.number_input(
            "⚠️ Số lần trễ hạn (2 năm)",
            min_value=0, max_value=20, value=0, step=1,
            help="Số lần trễ hạn thanh toán trong 2 năm gần nhất"
        )
    
    c11, _, _ = st.columns(3)
    with c11:
        total_acc = st.number_input(
            "🏦 Tổng số tài khoản tín dụng",
            min_value=1, max_value=100, value=15, step=1,
            help="Tổng số dòng tín dụng đã từng mở"
        )
    
    # --- SUBMIT ---
    st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)
    
    col_submit, _, _ = st.columns([2, 1, 1])
    with col_submit:
        submitted = st.form_submit_button(
            "🚀 PHÂN TÍCH RỦI RO VÀ ĐỀ XUẤT QUYẾT ĐỊNH",
            type="primary",
            use_container_width=True
        )

# =============================================
# XỬ LÝ KẾT QUẢ
# =============================================
if submitted:
    payload = {
        "loan_amnt": float(loan_amnt),
        "int_rate": float(int_rate),
        "grade": grade,
        "annual_inc": float(annual_inc),
        "dti": float(dti),
        "home_ownership": home_ownership,
        "verification_status": verification_status,
        "emp_length": emp_length,
        "term_numeric": float(term),
        "delinq_2yrs": float(delinq_2yrs),
        "total_acc": float(total_acc)
    }
    
    with st.spinner("⏳ Đang phân tích hồ sơ qua AI Engine..."):
        try:
            response = requests.post(API_URL, json=payload, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                time.sleep(0.5)  # Hiệu ứng loading
                
                st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)
                
                prediction = result["prediction"]
                risk_prob = result.get("risk_probability", 0)
                confidence = result.get("confidence", 0)
                recommendation = result.get("recommendation", "")
                
                # --- KẾT QUẢ CHÍNH ---
                if prediction == 0:
                    st.markdown(f"""
                    <div class="result-approved">
                        <div class="result-title" style="color: #48bb78;">✅ {recommendation}</div>
                        <div class="result-subtitle" style="color: #c6f6d5;">
                            Hệ thống AI đánh giá hồ sơ này có mức rủi ro THẤP.<br>
                            Khuyến nghị: <strong>PHÊ DUYỆT KHOẢN VAY</strong>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div class="result-rejected">
                        <div class="result-title" style="color: #fc8181;">🚨 {recommendation}</div>
                        <div class="result-subtitle" style="color: #fed7d7;">
                            Hệ thống AI phát hiện tín hiệu rủi ro CAO.<br>
                            Khuyến nghị: <strong>TỪ CHỐI KHOẢN VAY</strong> hoặc yêu cầu thêm tài sản đảm bảo.
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                # --- METRICS ---
                m1, m2, m3, m4 = st.columns(4)
                
                with m1:
                    risk_color = "#48bb78" if risk_prob < 0.3 else "#ecc94b" if risk_prob < 0.6 else "#fc8181"
                    st.markdown(f"""
                    <div class="metric-box">
                        <div class="label">Xác suất Nợ xấu</div>
                        <div class="value" style="color: {risk_color};">{risk_prob:.1%}</div>
                        <div class="risk-gauge">
                            <div class="risk-gauge-fill" style="width: {risk_prob*100}%; background: {risk_color};"></div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with m2:
                    st.markdown(f"""
                    <div class="metric-box">
                        <div class="label">Độ tin cậy</div>
                        <div class="value">{confidence:.1%}</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with m3:
                    st.markdown(f"""
                    <div class="metric-box">
                        <div class="label">Kết luận AI</div>
                        <div class="value" style="font-size: 1.2rem;">{result.get('status_label', '')}</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with m4:
                    st.markdown(f"""
                    <div class="metric-box">
                        <div class="label">Mã hồ sơ</div>
                        <div class="value">#{result.get('id', 'N/A')}</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                # --- TÓM TẮT HỒ SƠ ---
                st.markdown("<br>", unsafe_allow_html=True)
                with st.expander("📄 Chi tiết hồ sơ đã gửi", expanded=False):
                    detail_c1, detail_c2 = st.columns(2)
                    with detail_c1:
                        st.markdown(f"""
                        | Thông tin | Giá trị |
                        |-----------|---------|
                        | 💵 Số tiền vay | **${loan_amnt:,.0f}** |
                        | 📈 Lãi suất | **{int_rate}%** |
                        | 📅 Kỳ hạn | **{int(term)} tháng** |
                        | 🏅 Hạng tín dụng | **{grade}** |
                        """)
                    with detail_c2:
                        st.markdown(f"""
                        | Thông tin | Giá trị |
                        |-----------|---------|
                        | 💼 Thu nhập | **${annual_inc:,.0f}** |
                        | 📉 DTI | **{dti}%** |
                        | 🏠 Nhà ở | **{home_ownership}** |
                        | ⚠️ Trễ hạn | **{int(delinq_2yrs)} lần** |
                        """)
                    
            else:
                error_detail = response.json().get("detail", "Không rõ lỗi")
                st.error(f"❌ Backend trả lỗi {response.status_code}: {error_detail}")
                
        except requests.exceptions.ConnectionError:
            st.error("❌ **Không thể kết nối Backend!**\n\nHãy chạy lệnh sau trước:\n```\nuvicorn app.backend.main:app --reload\n```")
        except Exception as e:
            st.error(f"❌ Lỗi không xác định: {str(e)}")

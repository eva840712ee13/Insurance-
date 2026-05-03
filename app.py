import streamlit as st
import google.generativeai as genai
from PIL import Image
import pandas as pd
import plotly.graph_objects as go
import json

# --- 網頁基礎配置 ---
st.set_page_config(page_title="專業保單健檢系統", layout="centered")

st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stButton>button { width: 100%; border-radius: 20px; background-color: #2ecc71; color: white; }
    </style>
    """, unsafe_allow_html=True)

# --- 側邊欄：設定 ---
with st.sidebar:
    st.title("⚙️ 設定")
    api_key = st.text_input("請輸入 Gemini API Key", type="password")
    st.info("請至 Google AI Studio 申請免費 Key")

# --- 核心邏輯 ---
TARGETS = {
    "壽險": 500,
    "意外險": 300,
    "實支實付": 20,
    "重大傷病": 100,
    "癌症險": 200,
    "長照險": 300
}

def analyze_image(img, key):
    genai.configure(api_key=key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    prompt = """
    你是一位保險專家。請分析這張保單照片，並提取以下險種的投保金額（單位：萬元）：
    壽險、意外險、實支實付、重大傷病、癌症險、長照險。
    請只回傳 JSON 格式，例如：{"壽險": 100, "意外險": 50...}。
    如果沒看到該險種，請填 0。
    """
    response = model.generate_content([prompt, img])
    # 移除 Markdown 標籤以防解析錯誤
    clean_text = response.text.replace('```json', '').replace('```', '').strip()
    return json.loads(clean_text)

# --- 主介面 ---
st.title("🛡️ 智慧保單健檢系統")
st.write("透過 AI 快速分析您的保障缺口")

tab1, tab2 = st.tabs(["📸 拍照/上傳辨識", "✍️ 手動輸入"])

current_data = {k: 0.0 for k in TARGETS.keys()}

with tab1:
    uploaded_file = st.file_uploader("上傳保單照片", type=["jpg", "jpeg", "png"])
    if uploaded_file and api_key:
        if st.button("開始 AI 辨識"):
            with st.spinner("AI 正在閱讀保單中..."):
                img = Image.open(uploaded_file)
                st.image(img, caption="上傳的保單", use_column_width=True)
                try:
                    result = analyze_image(img, api_key)
                    st.success("辨識成功！")
                    current_data.update(result)
                except Exception as e:
                    st.error(f"辨識失敗：{e}")
    elif not api_key:
        st.warning("請先在左側輸入 API Key 才能執行辨識。")

with tab2:
    col1, col2 = st.columns(2)
    for i, (key, val) in enumerate(TARGETS.items()):
        with col1 if i % 2 == 0 else col2:
            current_data[key] = st.number_input(f"{key} 現有額度 (萬)", min_value=0.0, value=float(current_data[key]), step=10.0)

# --- 健檢分析結果 ---
if st.button("查看健檢報告"):
    st.divider()
    st.header("📊 健檢報告摘要")
    
    # 1. 雷達圖分析
    categories = list(TARGETS.keys())
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=[current_data[c] for c in categories],
        theta=categories,
        fill='toself',
        name='現有保障',
        line_color='#2ecc71'
    ))
    fig.add_trace(go.Scatterpolar(
        r=[TARGETS[c] for c in categories],
        theta=categories,
        fill='none',
        name='建議標準',
        line_color='#bdc3c7',
        line_dash='dash'
    ))
    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 500])), showlegend=True)
    st.plotly_chart(fig, use_container_width=True)

    # 2. 缺口細節
    df_data = []
    for key in TARGETS:
        current = current_data[key]
        target = TARGETS[key]
        gap = max(0.0, target - current)
        status = "✅ 充足" if gap <= 0 else f"⚠️ 缺口 {gap}萬"
        df_data.append({"險種": key, "現有額度": f"{current}萬", "建議額度": f"{target}萬", "診斷結果": status})
    
    st.table(pd.DataFrame(df_data))
    
    # 3. 專業建議
    st.subheader("💡 顧問建議")
    gaps = [k for k, v in TARGETS.items() if current_data[k] < v]
    if gaps:
        st.write(f"針對您的狀況，建議優先補強 **{', '.join(gaps)}**。")
        st.write("特別提醒：醫療技術日新月異，實支實付與重大傷病是目前的規劃重點。")
    else:
        st.write("太棒了！您的基礎保障非常完整。建議定期檢視受益人設定與保費負擔比例。")

st.caption("本工具僅供參考，實際保障內容請以保險單據與保險公司核定為準。")

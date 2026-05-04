import streamlit as st
import google.generativeai as genai
from PIL import Image
import pandas as pd
import plotly.graph_objects as go
import json

# --- 網頁基礎配置 (已加入專屬品牌) ---
st.set_page_config(page_title="新光人壽許家榛Lydia - 專屬保單健檢", layout="centered")

st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stButton>button { width: 100%; border-radius: 20px; background-color: #e74c3c; color: white; font-weight: bold;}
    </style>
    """, unsafe_allow_html=True)

# --- 側邊欄：設定 ---
with st.sidebar:
    st.title("⚙️ 系統設定")
    api_key = st.text_input("請輸入 Gemini API Key", type="password")
    st.info("💡 提示：輸入 API Key 後即可啟用 AI 照片辨識與保單名稱解析功能。")

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
    # 這裡更新為 -latest
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
    prompt = """
    你是一位保險專家。請分析這張保單照片，並提取以下險種的投保金額（單位：萬元）：
    壽險、意外險、實支實付、重大傷病、癌症險、長照險。
    請只回傳 JSON 格式，例如：{"壽險": 100, "意外險": 50, "實支實付": 0, "重大傷病": 0, "癌症險": 0, "長照險": 0}。
    """
    response = model.generate_content([prompt, img])
    clean_text = response.text.replace("```json", "").replace("
```", "").strip()
    return json.loads(clean_text)

def analyze_policy_names(text, key):
    """將輸入的保單名稱與額度轉化為六大險種"""
    genai.configure(api_key=key)
    # 這裡也更新為 -latest
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
    prompt = f"""
    你是一位台灣的專業壽險顧問。客戶提供了以下保單名稱與額度：
    {text}
    
    請幫我將這些保單的保障內容，歸類到以下六大險種中，並加總額度（單位：萬元）：
    壽險、意外險、實支實付、重大傷病、癌症險、長照險。
    (例如：輸入"新光人壽呵護安心重大傷病 100萬"，重大傷病就要填 100)
    
    請只回傳 JSON 格式，例如：{{"壽險": 0, "意外險": 0, "實支實付": 0, "重大傷病": 100, "癌症險": 0, "長照險": 0}}。
    """
    response = model.generate_content(prompt)
    clean_text = response.text.replace("```json", "").replace("```", "").strip()
    return json.loads(clean_text)



# --- 主介面 ---
st.title("🛡️ 新光人壽許家榛Lydia")
st.subheader("智慧保單健檢系統")
st.write("透過 AI 快速分析您的保障缺口，為您量身打造防護網。")

# 新增了三個頁籤
tab1, tab2, tab3 = st.tabs(["📝 輸入保單名稱", "📸 照片智能辨識", "✍️ 手動快速輸入"])

# 初始化或讀取暫存的資料
if 'current_data' not in st.session_state:
    st.session_state.current_data = {k: 0.0 for k in TARGETS.keys()}

with tab1:
    st.write("請輸入您現有的保單名稱與保額，AI 將自動為您分類。")
    policy_text = st.text_area("例如：\n新光人壽活力平安傷害保險 200萬\n國泰人壽鍾心呵護重大傷病 100萬", height=150)
    
    if st.button("🧠 AI 智能分析保單"):
        if api_key and policy_text:
            with st.spinner("Lydia 的 AI 助手正在分析保單條款..."):
                try:
                    result = analyze_policy_names(policy_text, api_key)
                    for k, v in result.items():
                        st.session_state.current_data[k] += float(v)
                    st.success("✅ 保單分析並歸類成功！請點擊最下方按鈕查看報告。")
                except Exception as e:
                    st.error(f"分析失敗，請檢查格式或 API Key。錯誤：{e}")
        elif not api_key:
             st.warning("請先在左側欄位輸入 API Key。")
        else:
             st.warning("請輸入保單名稱與額度。")

with tab2:
    uploaded_file = st.file_uploader("上傳保單總表照片", type=["jpg", "jpeg", "png"])
    if st.button("📸 開始照片辨識"):
        if uploaded_file and api_key:
            with st.spinner("Lydia 的 AI 助手正在閱讀照片..."):
                img = Image.open(uploaded_file)
                st.image(img, caption="上傳的保單", use_column_width=True)
                try:
                    result = analyze_image(img, api_key)
                    for k, v in result.items():
                        st.session_state.current_data[k] += float(v)
                    st.success("✅ 辨識成功！資料已加入。")
                except Exception as e:
                    st.error(f"辨識失敗：{e}")
        elif not api_key:
            st.warning("請先在左側欄位輸入 API Key。")

with tab3:
    st.write("您可以直接手動微調各險種的總額（單位：萬元）")
    col1, col2 = st.columns(2)
    for i, (key, val) in enumerate(TARGETS.items()):
        with col1 if i % 2 == 0 else col2:
            st.session_state.current_data[key] = st.number_input(
                f"{key} 額度 (萬)", 
                min_value=0.0, 
                value=float(st.session_state.current_data[key]), 
                step=10.0
            )

# --- 健檢分析結果 ---
if st.button("📊 生成專屬健檢報告"):
    st.divider()
    st.header("📋 您的保障缺口分析")
    
    # 雷達圖分析
    categories = list(TARGETS.keys())
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=[st.session_state.current_data[c] for c in categories],
        theta=categories,
        fill='toself',
        name='您目前的保障',
        line_color='#e74c3c'
    ))
    fig.add_trace(go.Scatterpolar(
        r=[TARGETS[c] for c in categories],
        theta=categories,
        fill='none',
        name='Lydia 建議標準',
        line_color='#bdc3c7',
        line_dash='dash'
    ))
    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, max(TARGETS.values()) + 100])), showlegend=True)
    st.plotly_chart(fig, use_container_width=True)

    # 缺口細節
    df_data = []
    for key in TARGETS:
        current = st.session_state.current_data[key]
        target = TARGETS[key]
        gap = max(0.0, target - current)
        status = "✅ 充足" if gap <= 0 else f"⚠️ 缺口 {gap}萬"
        df_data.append({"險種": key, "現有保障 (萬)": current, "建議額度 (萬)": target, "診斷結果": status})
    
    st.table(pd.DataFrame(df_data))
    
    # 專業建議
    st.subheader("💡 Lydia 的專業建議")
    gaps = [k for k, v in TARGETS.items() if st.session_state.current_data[k] < v]
    if gaps:
        st.info(f"👉 經過系統精密計算，建議您優先補強的板塊為：**{', '.join(gaps)}**。")
        st.write("在這個醫療自費項目變多的時代，實支實付與重大傷病是轉嫁龐大醫療開銷的關鍵。後續我們可以針對您的預算，討論最適合的補強方案。")
    else:
        st.success("太棒了！您的基礎防護網非常堅固。建議我們定期為您的保單做健康檢查，確保受益人設定與目前的人生階段相符。")

st.caption("本系統分析結果僅供參考，實際理賠與保障內容須以保險單據與公司條款為準。")

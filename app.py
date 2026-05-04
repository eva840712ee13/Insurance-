import streamlit as st
import google.generativeai as genai
from PIL import Image
import json

# --- 網頁基礎配置 (改為寬螢幕模式以容納報表) ---
st.set_page_config(page_title="新光人壽許家榛Lydia - 專屬保單健檢", layout="wide")

# --- 客製化 CSS (還原照片中的色塊與排版，並設定右上角品牌) ---
st.markdown("""
    <style>
    .main { background-color: #f4f6f7; }
    .stButton>button { width: 100%; border-radius: 10px; background-color: #3498db; color: white; font-weight: bold;}
    .brand-top-right { position: absolute; top: 0px; right: 20px; font-size: 18px; font-weight: bold; color: #2c3e50; z-index: 999;}
    .report-title { text-align: center; font-size: 28px; font-weight: bold; background-color: #aed6f1; padding: 10px; border-radius: 10px; margin-bottom: 20px; color: #2c3e50;}
    .box { padding: 15px; border-radius: 10px; margin-bottom: 20px; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); height: 100%;}
    .box-title { font-size: 20px; font-weight: bold; text-align: center; margin-bottom: 15px; color: #333;}
    .item-row { display: flex; justify-content: space-between; border-bottom: 1px dashed #ccc; padding: 5px 0; font-size: 14px;}
    .item-name { color: #555; }
    .item-value { font-weight: bold; color: #222; }
    
    /* 色塊定義 */
    .bg-disease { background-color: #d5f5e3; } /* 疾病-綠 */
    .bg-receipt { background-color: #fcf3cf; } /* 實支實付-黃 */
    .bg-accident { background-color: #d1f2eb; } /* 意外-淺綠藍 */
    .bg-critical { background-color: #d6eaf8; } /* 重大傷病-藍 */
    .bg-surgery { background-color: #e8daef; } /* 手術-紫 */
    .bg-cancer { background-color: #f5eef8; } /* 癌症-粉紫 */
    .bg-ltc { background-color: #fef9e7; } /* 長照-淺黃 */
    </style>
    
    <!-- 右上角專屬品牌 -->
    <div class="brand-top-right">新光人壽許家榛Lydia</div>
    """, unsafe_allow_html=True)

# --- 側邊欄：設定 ---
with st.sidebar:
    st.title("⚙️ 系統設定")
    api_key = st.text_input("請輸入 Gemini API Key", type="password")
    st.info("輸入後即可啟用 AI 條款深度解析功能。")

# --- AI 模型獲取 ---
def get_working_model(key):
    genai.configure(api_key=key)
    available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    for preferred in ['models/gemini-1.5-flash', 'models/gemini-1.5-pro']:
        if preferred in available_models:
            return genai.GenerativeModel(preferred)
    if available_models:
        return genai.GenerativeModel(available_models[0])
    raise Exception("無可用模型")

# --- AI 解析核心指令 (升級為深度解析 JSON) ---
JSON_FORMAT_PROMPT = """
請務必只回傳純 JSON 格式，不要包含 ```json 標籤或任何 Markdown。
JSON 結構必須嚴格如下：
{
  "讀取的保單與條款": ["保單名稱1", "保單名稱2..."],
  "疾病": {"一般住院每天": "金額", "加護病房每天": "金額", "...": "..."},
  "實支實付": {"住院病房限額每天": "金額", "每次醫療及雜項限額": "金額", "...": "..."},
  "意外": {"身故或一級失能": "金額", "意外住院每天": "金額", "...": "..."},
  "重大傷病": {"重大傷病一次領": "金額", "...": "..."},
  "手術": {"門診手術每次": "金額", "一般住院手術每次": "金額", "...": "..."},
  "癌症": {"初次罹患癌症一次領": "金額", "癌症住院每天": "金額", "...": "..."},
  "長照失能": {"完全失能每年領": "金額", "失能生活照顧金每月": "金額", "...": "..."}
}
如果沒有該類別的資料，請保持空字典 {}。如果金額未知，請填 "依條款"。
"""

def analyze_with_ai(content, key, is_image=False):
    model = get_working_model(key)
    if is_image:
        prompt = f"你是一位專業壽險顧問。請分析這張保單照片，並詳細提取各項理賠額度。\n{JSON_FORMAT_PROMPT}"
        response = model.generate_content([prompt, content])
    else:
        prompt = f"你是一位專業壽險顧問。客戶擁有以下保單：\n{content}\n請根據這些保單常見的條款內容，幫我整理出詳細的理賠額度。\n{JSON_FORMAT_PROMPT}"
        response = model.generate_content(prompt)
    
    clean_text = response.text.replace("```json", "").replace("```", "").strip()
    return json.loads(clean_text)

# --- 渲染 HTML 卡片函數 ---
def render_category_box(title, data_dict, bg_class):
    html = f"<div class='box {bg_class}'><div class='box-title'>{title}</div>"
    if not data_dict:
        html += "<div class='item-row'><span class='item-name'>無相關保障</span><span class='item-value'>-</span></div>"
    else:
        for k, v in data_dict.items():
            html += f"<div class='item-row'><span class='item-name'>{k}</span><span class='item-value'>{v}</span></div>"
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)

# --- 主介面 ---
st.markdown("<div class='report-title'>2024 年度保單健檢報告書</div>", unsafe_allow_html=True)

tab1, tab2 = st.tabs(["📝 輸入保單名稱解析條款", "📸 拍攝既有總表解析"])

if 'report_data' not in st.session_state:
    st.session_state.report_data = None

# 頁籤 1: 文字輸入
with tab1:
    policy_text = st.text_area("請輸入客戶擁有的保單名稱 (AI 將自動調閱常見條款並整理細項)：", height=100)
    if st.button("🧠 開始深度解析條款"):
        if api_key and policy_text:
            with st.spinner("正在調閱條款並生成細項報表..."):
                try:
                    st.session_state.report_data = analyze_with_ai(policy_text, api_key, is_image=False)
                    st.success("解析完成！請往下查看報告。")
                except Exception as e:
                    st.error(f"解析失敗，錯誤：{e}")
        else:
            st.warning("請輸入 API Key 與保單名稱。")

# 頁籤 2: 圖片上傳
with tab2:
    uploaded_file = st.file_uploader("上傳您手邊的保單總表或條款照片", type=["jpg", "jpeg", "png"])
    if st.button("📸 開始照片深度解析"):
        if uploaded_file and api_key:
            with st.spinner("正在閱讀照片中的各項額度..."):
                img = Image.open(uploaded_file)
                try:
                    st.session_state.report_data = analyze_with_ai(img, api_key, is_image=True)
                    st.success("解析完成！請往下查看報告。")
                except Exception as e:
                    st.error(f"辨識失敗：{e}")
        else:
            st.warning("請上傳照片並輸入 API Key。")

# --- 報表顯示區 ---
st.divider()

if st.session_state.report_data:
    data = st.session_state.report_data
    
    # 顯示讀取到的保單清單
    st.subheader("📑 系統讀取之保單/條款清單")
    policies = data.get("讀取的保單與條款", [])
    if policies:
        for p in policies:
            st.markdown(f"- **{p}**")
    else:
        st.write("未辨識到特定保單名稱。")
    
    st.write("---")
    
    # 排版：第一排 (疾病, 實支實付, 意外)
    col1, col2, col3 = st.columns(3)
    with col1: render_category_box("疾 病", data.get("疾病", {}), "bg-disease")
    with col2: render_category_box("實支實付", data.get("實支實付", {}), "bg-receipt")
    with col3: render_category_box("意 外", data.get("意外", {}), "bg-accident")
    
    # 排版：第二排 (重大傷病, 手術, 癌症)
    col4, col5, col6 = st.columns(3)
    with col4: render_category_box("重大傷病", data.get("重大傷病", {}), "bg-critical")
    with col5: render_category_box("手 術", data.get("手術", {}), "bg-surgery")
    with col6: render_category_box("癌 症", data.get("癌症", {}), "bg-cancer")
    
    # 排版：第三排 (長照失能)
    col7, col8 = st.columns([1, 2]) # 調整比例讓排版更好看
    with col7: render_category_box("長照 / 失能扶助", data.get("長照失能", {}), "bg-ltc")
    with col8:
        # 放一些總結或聲明
        st.info("💡 **顧問提醒**\n\n以上細項為 AI 根據保單名稱或圖片解析之結果。實際理賠條件（如：手術倍數表、重大傷病範圍定義）仍須以保單正本與保險公司最新公告條款為準。")
        st.success("若有任何缺口，我們可針對您的預算與人生階段，規劃最適合的補強方案。")
else:
    st.info("請於上方輸入資料或上傳照片，系統將在此為您生成全彩條款解析報表。")

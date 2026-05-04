import streamlit as st
import google.generativeai as genai
from PIL import Image
import json

# --- 網頁基礎配置 ---
st.set_page_config(page_title="新光人壽許家榛Lydia - 專屬保單健檢", layout="wide")

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
    
    .bg-disease { background-color: #d5f5e3; }
    .bg-receipt { background-color: #fcf3cf; }
    .bg-accident { background-color: #d1f2eb; }
    .bg-critical { background-color: #d6eaf8; }
    .bg-surgery { background-color: #e8daef; }
    .bg-cancer { background-color: #f5eef8; }
    .bg-ltc { background-color: #fef9e7; }
    </style>
    
    <div class="brand-top-right">新光人壽許家榛Lydia</div>
    """, unsafe_allow_html=True)

with st.sidebar:
    st.title("⚙️ 系統設定")
    api_key = st.text_input("請輸入 Gemini API Key", type="password")
    st.info("建議使用具備 Pro 模型權限的 Key 以確保條款精準度。")

# --- AI 模型獲取 (強制優先尋找能力最強的 Pro 模型) ---
def get_pro_model(key):
    genai.configure(api_key=key)
    available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    # 強制優先使用 1.5-pro，因為它的事實查證與回憶條款能力遠強於 flash
    for preferred in ['models/gemini-1.5-pro-latest', 'models/gemini-1.5-pro', 'models/gemini-1.5-flash-latest']:
        if preferred in available_models:
            return genai.GenerativeModel(preferred)
    if available_models:
        return genai.GenerativeModel(available_models[0])
    raise Exception("無可用模型")

# --- AI 解析核心指令 (真實查證版) ---
JSON_FORMAT_PROMPT = """
請務必只回傳純 JSON 格式，不要包含 ```json 標籤或任何 Markdown。
JSON 結構必須嚴格如下（必須完整保留這8個主鍵值，即便內容為空）：
{
  "讀取的保單與條款": ["保單名稱1", "保單名稱2..."],
  "疾病": {},
  "實支實付": {},
  "意外": {},
  "重大傷病": {},
  "手術": {},
  "癌症": {},
  "長照失能": {}
}

【最高專業查證指令】：
1. 你現在扮演台灣最嚴謹的保險核保人員。
2. 針對輸入的保單名稱（如「新光人壽倍感依靠30計劃」），你必須動用你資料庫中對台灣保險商品的知識，找出該商品的【實際條款理賠額度】。
3. 根據該商品特性，將細項名稱與真實數字填入對應的分類中。
   (例如：在"實支實付"分類中填入 {"住院病房費限額每天": "3,000元", "每次住院醫療費用限額": "30萬元", "門診手術限額": "30萬元"})
4. 【絕對禁止瞎猜】：如果你明確知道該商品，請列出實際金額；如果你真的查不到該商品的確切數字，請務必將該險種常見的項目列出，並將金額填寫為「需對照正本確認」，絕對不允許直接給空字典 {}，這會導致客戶以為沒有該項保障！
"""

def analyze_with_ai(content, key, is_image=False):
    model = get_pro_model(key)
    if is_image:
        prompt = f"你是一位專業壽險顧問。請分析這張保單照片，並詳細提取各項理賠額度。\n{JSON_FORMAT_PROMPT}"
        response = model.generate_content([prompt, content])
    else:
        prompt = f"你是一位專業壽險顧問。客戶擁有以下保單：\n{content}\n請務必依據真實商品條款，幫我整理出詳細的理賠額度。\n{JSON_FORMAT_PROMPT}"
        response = model.generate_content(prompt)
    
    clean_text = response.text.replace("```json", "").replace("```", "").strip()
    return json.loads(clean_text)

def render_category_box(title, data_dict, bg_class):
    html = f"<div class='box {bg_class}'><div class='box-title'>{title}</div>"
    if not data_dict:
         # 雙重保險：如果 AI 真的還是當機回傳空字典，我們手動幫它加上提示
        html += "<div class='item-row'><span class='item-name'>該險種細項</span><span class='item-value'>請查閱條款確認</span></div>"
    else:
        for k, v in data_dict.items():
            html += f"<div class='item-row'><span class='item-name'>{k}</span><span class='item-value'>{v}</span></div>"
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)

st.markdown("<div class='report-title'>2024 年度保單健檢報告書</div>", unsafe_allow_html=True)

tab1, tab2 = st.tabs(["📝 輸入保單名稱解析條款", "📸 拍攝既有總表解析"])

if 'report_data' not in st.session_state:
    st.session_state.report_data = None

with tab1:
    st.write("💡 提示：輸入越完整的名稱與計畫別（如：新光人壽倍感依靠住院醫療健康保險附約 30計畫），AI 能調閱的數字越精準。")
    policy_text = st.text_area("請輸入客戶擁有的保單名稱：", height=100)
    if st.button("🧠 開始深度比對條款"):
        if api_key and policy_text:
            with st.spinner("Lydia 的 AI 系統正在啟動高階比對，檢索實際理賠數字中..."):
                try:
                    st.session_state.report_data = analyze_with_ai(policy_text, api_key, is_image=False)
                    st.success("解析完成！請往下查看報告。")
                except Exception as e:
                    st.error(f"解析失敗，錯誤：{e}")
        else:
            st.warning("請輸入 API Key 與保單名稱。")

with tab2:
    uploaded_file = st.file_uploader("上傳您手邊的保單總表或條款照片", type=["jpg", "jpeg", "png"])
    if st.button("📸 開始照片深度解析"):
        if uploaded_file and api_key:
            with st.spinner("正在精準閱讀照片中的各項額度..."):
                img = Image.open(uploaded_file)
                try:
                    st.session_state.report_data = analyze_with_ai(img, api_key, is_image=True)
                    st.success("解析完成！請往下查看報告。")
                except Exception as e:
                    st.error(f"辨識失敗：{e}")
        else:
            st.warning("請上傳照片並輸入 API Key。")

st.divider()

if st.session_state.report_data:
    data = st.session_state.report_data
    
    st.subheader("📑 系統比對之保單/條款清單")
    policies = data.get("讀取的保單與條款", [])
    if policies:
        for p in policies:
            st.markdown(f"- **{p}**")
    else:
        st.write("未辨識到特定保單名稱。")
    
    st.write("---")
    
    col1, col2, col3 = st.columns(3)
    with col1: render_category_box("疾 病", data.get("疾病", {}), "bg-disease")
    with col2: render_category_box("實支實付", data.get("實支實付", {}), "bg-receipt")
    with col3: render_category_box("意 外", data.get("意外", {}), "bg-accident")
    
    col4, col5, col6 = st.columns(3)
    with col4: render_category_box("重大傷病", data.get("重大傷病", {}), "bg-critical")
    with col5: render_category_box("手 術", data.get("手術", {}), "bg-surgery")
    with col6: render_category_box("癌 症", data.get("癌症", {}), "bg-cancer")
    
    col7, col8 = st.columns([1, 2])
    with col7: render_category_box("長照 / 失能扶助", data.get("長照失能", {}), "bg-ltc")
    with col8:
        st.info("💡 **顧問提醒**\n\n以上細項為 AI 檢索條款資料庫之數據。為求100%嚴謹，實際理賠條件（如：手術倍數表、重大傷病範圍定義）仍須以您的保單正本與保險公司最新公告條款為準。")
        st.success("若有任何缺口或條款疑慮，我們可針對您的預算與目前的人生階段，規劃最適合的補強方案。")
else:
    st.info("請於上方輸入資料或上傳照片，系統將在此為您比對並生成全彩條款解析報表。")

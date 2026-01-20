import streamlit as st
import requests
import json
import pandas as pd
from newsapi import NewsApiClient
from datetime import datetime, timedelta
import re

# ตั้งค่าหน้าเว็บ
st.set_page_config(page_title="Gold AI Specialist", page_icon="💰", layout="wide")

st.title("💰 Gold Market Intelligence Agent")
st.caption("วิเคราะห์เจาะลึกข่าวสารที่มีผลต่อราคาทองคำโดย AI")

# ==============================================================================
# 🔴 ส่วนดึงรหัสจาก Secrets
# ==============================================================================
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    NEWS_API_KEY = st.secrets["NEWS_API_KEY"]
except:
    st.error("❌ ไม่พบ API Key! กรุณาตั้งค่าใน Streamlit Cloud")
    st.stop()

# ==============================================================================
# ฟังก์ชันการทำงาน
# ==============================================================================

def find_best_model():
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_API_KEY}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            for model in data.get('models', []):
                name = model['name']
                methods = model.get('supportedGenerationMethods', [])
                if 'gemini' in name and 'generateContent' in methods:
                    return name
        return "models/gemini-1.5-flash"
    except:
        return "models/gemini-1.5-flash"

def get_detailed_analysis(model_name, news_list):
    clean_model_name = model_name.replace("models/", "")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{clean_model_name}:generateContent?key={GEMINI_API_KEY}"
    headers = {'Content-Type': 'application/json'}
    
    # ส่งข่าวทั้งหมดไปให้ AI วิเคราะห์แยกเป็นรายชิ้น
    news_input = ""
    for i, n in enumerate(news_list):
        news_input += f"ข่าวที่ {i+1}: {n['title']} - {n['description']}\n\n"

    prompt = f"""
    ในฐานะนักกลยุทธ์ทองคำ วิเคราะห์ข่าวต่อไปนี้และตอบในรูปแบบ JSON ภาษาไทยเท่านั้น:
    {news_input}
    
    รูปแบบที่ต้องการ:
    {{
        "individual_news": [
            {{
                "title": "หัวข้อข่าวภาษาไทย",
                "summary": "สรุปเนื้อหาสำคัญสั้นๆ",
                "weight": "คะแนนผลกระทบต่อราคาทอง (0-100 โดย 0=ลบมาก, 100=บวกมาก)"
            }}
        ],
        "overall_sentiment_score": "คะแนนเฉลี่ยภาพรวม",
        "overall_summary": "สรุปภาพรวมตลาด",
        "action_plan": "คำแนะนำการลงทุน"
    }}
    """
    data = {"contents": [{"parts": [{"text": prompt}]}]}
    try:
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            return response.json()['candidates'][0]['content']['parts'][0]['text']
    except:
        return None

def clean_json_text(text):
    if not text: return None
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```', '', text)
    return text.strip()

# ==============================================================================
# ส่วนแสดงผล Dashboard
# ==============================================================================

if st.button("🚀 เริ่มการวิเคราะห์เชิงลึก", type="primary"):
    with st.spinner('📡 กำลังกวาดข่าวและให้น้ำหนักคะแนน...'):
        newsapi = NewsApiClient(api_key=NEWS_API_KEY)
        keywords = ["Gold Price", "US Federal Reserve", "Trump Policy"]
        all_articles = newsapi.get_everything(
            q=" OR ".join(keywords),
            from_param=(datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d'),
            language='en',
            sort_by='relevancy',
            page_size=5
        )
        articles = all_articles.get('articles', [])

        if articles:
            best_model = find_best_model()
            raw_res = get_detailed_analysis(best_model, articles)
            
            if raw_res:
                try:
                    analysis = json.loads(clean_json_text(raw_res))
                    
                    # 1. แสดงคะแนนภาพรวม
                    st.divider()
                    col_a, col_b = st.columns([1, 2])
                    with col_a:
                        st.metric("Overall Score", f"{analysis.get('overall_sentiment_score')}/100")
                    with col_b:
                        st.info(f"**กลยุทธ์:** {analysis.get('action_plan')}")

                    # 2. แสดงรายละเอียดรายข่าว (จุดที่เพิ่มใหม่)
                    st.subheader("📰 วิเคราะห์รายข่าว (News Breakdown)")
                    for news in analysis.get('individual_news', []):
                        with st.container(border=True):
                            c1, c2 = st.columns([4, 1])
                            with c1:
                                st.write(f"**{news.get('title')}**")
                                st.caption(news.get('summary'))
                            with c2:
                                weight = int(news.get('weight', 50))
                                st.write(f"คะแนน: **{weight}**")
                                if weight >= 60: st.write("🟢 บวก")
                                elif weight <= 40: st.write("🔴 ลบ")
                                else: st.write("🟡 กลาง")

                except Exception as e:
                    st.error(f"การประมวลผลผิดพลาด: {e}")
        else:
            st.warning("ไม่พบข่าวใหม่")

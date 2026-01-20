import streamlit as st
import requests
import json
import pandas as pd
from newsapi import NewsApiClient
from datetime import datetime, timedelta
import re

# ตั้งค่าหน้าเว็บ
st.set_page_config(page_title="Gold AI Analyst", page_icon="💰")

st.title("💰 Gold Market Intelligence Agent")
st.caption("วิเคราะห์ตลาดทองคำด้วย AI (Gemini 2.5 Flash)")

# ==============================================================================
# 🔴 ส่วนดึงรหัสจาก Secrets
# ==============================================================================
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    NEWS_API_KEY = st.secrets["NEWS_API_KEY"]
except:
    st.error("❌ ไม่พบ API Key ใน Secrets! กรุณาตั้งค่าใน Streamlit Cloud")
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

def get_market_sentiment(model_name, all_news_text):
    clean_model_name = model_name.replace("models/", "")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{clean_model_name}:generateContent?key={GEMINI_API_KEY}"
    headers = {'Content-Type': 'application/json'}
    
    prompt = f"""
    Role: Gold Strategist.
    Input News:
    {all_news_text}
    
    Task: Analyze sentiment for XAU/USD. Response in Thai JSON ONLY:
    {{
        "market_status": "สภาวะตลาดสั้นๆ",
        "sentiment_score": "คะแนน 0-100 (เป็นตัวเลข)",
        "action_plan": "คำแนะนำสั้นๆ",
        "key_factors": "ปัจจัยหลัก"
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
# หน้าจอแสดงผล
# ==============================================================================

if st.button("🚀 เริ่มวิเคราะห์ตลาด (Analyze Now)", type="primary"):
    with st.spinner('📡 กำลังรวบรวมข่าวและประมวลผล...'):
        # 1. ดึงข่าว
        newsapi = NewsApiClient(api_key=NEWS_API_KEY)
        keywords = ["Gold Price", "Federal Reserve", "US Economy", "Trump"]
        today = datetime.now()
        yesterday = today - timedelta(days=2)
        
        all_articles = newsapi.get_everything(
            q=" OR ".join(keywords),
            from_param=yesterday.strftime('%Y-%m-%d'),
            language='en',
            sort_by='relevancy',
            page_size=5
        )
        articles = all_articles.get('articles', [])

        if articles:
            news_text = ""
            for i, article in enumerate(articles, 1):
                news_text += f"{i}. {article['title']}\n"
            
            # 2. ส่ง AI วิเคราะห์
            best_model = find_best_model()
            raw_res = get_market_sentiment(best_model, news_text)
            
            if raw_res:
                try:
                    analysis = json.loads(clean_json_text(raw_res))
                    
                    st.divider()
                    st.header("📊 ผลการวิเคราะห์")
                    
                    score = int(analysis.get('sentiment_score', 50))
                    st.metric("Sentiment Score", f"{score}/100")
                    
                    if score >= 60: st.success("📈 แนวโน้ม: ขาขึ้น (Bullish)")
                    elif score <= 40: st.error("📉 แนวโน้ม: ขาลง (Bearish)")
                    else: st.warning("⚖️ แนวโน้ม: ไซด์เวย์ (Neutral)")

                    st.write(f"**🌊 สภาวะตลาด:** {analysis.get('market_status')}")
                    st.write(f"**💡 คำแนะนำ:** {analysis.get('action_plan')}")
                    st.write(f"**🔑 ปัจจัยสำคัญ:** {analysis.get('key_factors')}")
                    st.caption(f"โมเดลที่ใช้: {best_model}")
                    
                except:
                    st.error("เกิดข้อผิดพลาดในการอ่านข้อมูลจาก AI")
        else:
            st.warning("ไม่พบข่าวใหม่ในขณะนี้")

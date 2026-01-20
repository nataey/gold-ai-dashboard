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
st.caption("วิเคราะห์เจาะลึกข่าวสารและนโยบาย Trump ที่มีผลต่อราคาทองคำ (เรียงตามข่าวใหม่ล่าสุด)")

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
    
    news_input = ""
    for i, n in enumerate(news_list):
        # เพิ่มข้อมูลเวลาเข้าไปให้ AI รับรู้ด้วย
        news_input += f"ข่าวที่ {i+1} [เวลา: {n['publishedAt']}]: {n['title']} - {n['description']}\n\n"

    prompt = f"""
    ในฐานะนักกลยุทธ์ทองคำ วิเคราะห์ข่าวต่อไปนี้ โดยเน้นนโยบาย Trump (Tariff/Greenland)
    และตอบในรูปแบบ JSON ภาษาไทยเท่านั้น:
    {news_input}
    
    รูปแบบที่ต้องการ:
    {{
        "individual_news": [
            {{
                "title": "หัวข้อข่าวภาษาไทย",
                "summary": "สรุปเนื้อหาสำคัญสั้นๆ",
                "weight": "คะแนนผลกระทบต่อทอง (0-100)"
            }}
        ],
        "overall_sentiment_score": "คะแนนเฉลี่ยภาพรวม",
        "overall_summary": "สรุปสภาวะตลาด",
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

if st.button("🚀 เริ่มการวิเคราะห์เชิงลึก (เรียงตามเวลาล่าสุด)", type="primary"):
    with st.spinner('📡 กำลังล่าข่าวใหม่ล่าสุดและประมวลผล...'):
        newsapi = NewsApiClient(api_key=NEWS_API_KEY)
        
        keywords = [
            "Gold Price impact Trump",
            "Trump Greenland tax", 
            "Trump 10 percent tariff", 
            "Trump trade war Europe",
            "US Federal Reserve"
        ]
        
        query_text = " OR ".join([f'"{k}"' for k in keywords])
        
        all_articles = newsapi.get_everything(
            q=query_text,
            from_param=(datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d'),
            language='en',
            sort_by='publishedAt', # บังคับเรียงตามเวลาใหม่ล่าสุดจากต้นทาง
            page_size=10
        )
        articles = all_articles.get('articles', [])

        if articles:
            best_model = find_best_model()
            raw_res = get_detailed_analysis(best_model, articles)
            
            if raw_res:
                try:
                    analysis = json.loads(clean_json_text(raw_res))
                    
                    st.divider()
                    col_a, col_b = st.columns([1, 2])
                    with col_a:
                        st.metric("Overall Score", f"{analysis.get('overall_sentiment_score')}/100")
                    with col_b:
                        st.info(f"**วิเคราะห์ภาพรวม:** {analysis.get('overall_summary')}")
                        st.success(f"**กลยุทธ์แนะนำ:** {analysis.get('action_plan')}")

                    st.subheader("📰 รายงานการวิเคราะห์รายข่าว (เรียงจากใหม่ไปเก่า)")
                    
                    # วนลูปแสดงข่าวพร้อมเวลา
                    for idx, news in enumerate(analysis.get('individual_news', [])):
                        # ดึงเวลาจากบทความต้นฉบับมาแสดง (จับคู่ตามลำดับ)
                        pub_date = articles[idx]['publishedAt']
                        # ปรับฟอร์แมตวันที่ให้ดูง่ายขึ้น
                        formatted_date = pub_date.replace('T', ' ').replace('Z', '')
                        
                        with st.container(border=True):
                            c1, c2 = st.columns([4, 1])
                            with c1:
                                st.write(f"**{news.get('title')}**")
                                st.caption(f"📅 เวลาเผยแพร่: {formatted_date}")
                                st.write(news.get('summary'))
                            with c2:
                                weight = int(news.get('weight', 50))
                                st.subheader(f"**{weight}**")
                                if weight >= 60: st.write("🟢 ผลบวกต่อทองคำ")
                                elif weight <= 40: st.write("🔴 ผลลบต่อทองคำ")
                                else: st.write("🟡 Neutral")

                except Exception as e:
                    st.error(f"เกิดข้อผิดพลาดในการแสดงผล: {e}")
        else:
            st.warning("ไม่พบข่าวใหม่ที่ตรงกับ Keywords ในขณะนี้")

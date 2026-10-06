# Trade Assistant 500 — Mobile V2

ออกแบบสำหรับเปิดบน Xiaomi/Android ผ่าน Chrome และ Deploy บน Streamlit Community Cloud

## จุดเด่น
- หน้า "หุ้นวันนี้" สแกนหุ้นสหรัฐยอดนิยม 12 ตัว
- วิเคราะห์รายตัว: EMA, RSI, MACD, Volume, แนวรับ/แนวต้าน, Volatility
- Fundamental snapshot
- คะแนน 0–100 พร้อมเหตุผล
- Entry / Stop Loss / Target 1 / Target 2
- คำนวณ Fractional Share ตามทุน 500 บาท
- Watchlist
- เปรียบเทียบหุ้น
- Trading Journal
- Responsive layout สำหรับมือถือ

## Deploy แบบง่าย
1. สร้าง GitHub repository ใหม่
2. Upload `streamlit_app.py` และ `requirements.txt`
3. เปิด Streamlit Community Cloud
4. Create app
5. เลือก repository และไฟล์ `streamlit_app.py`
6. Deploy
7. เปิด URL `.streamlit.app` ด้วย Chrome บน Xiaomi
8. Chrome > เมนู ⋮ > Add to Home screen

หมายเหตุ: Watchlist และ Journal ใน V2 เก็บใน session ของเว็บ ยังไม่ได้ใช้ฐานข้อมูลถาวร

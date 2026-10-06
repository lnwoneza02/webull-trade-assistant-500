
import math
from datetime import datetime
import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf

st.set_page_config(
    page_title="Trade Assistant 500",
    page_icon="📈",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ---------- Mobile CSS ----------
st.markdown("""
<style>
.block-container {padding-top: 1rem; padding-bottom: 5rem; max-width: 760px;}
h1 {font-size: 1.65rem !important; margin-bottom: .15rem;}
h2 {font-size: 1.25rem !important;}
h3 {font-size: 1.05rem !important;}
div[data-testid="stMetric"] {
    border: 1px solid rgba(128,128,128,.20);
    border-radius: 14px;
    padding: 10px 12px;
}
div.stButton > button, div.stDownloadButton > button {
    width: 100%;
    min-height: 46px;
    border-radius: 12px;
    font-weight: 700;
}
div[data-baseweb="input"] > div {min-height: 45px;}
.small-note {font-size:.84rem; opacity:.78}
.hero {
    padding: 14px 16px;
    border: 1px solid rgba(128,128,128,.22);
    border-radius: 16px;
    margin: 4px 0 14px 0;
}
.score {
    font-size: 1.55rem;
    font-weight: 800;
}
</style>
""", unsafe_allow_html=True)

DEFAULT_UNIVERSE = [
    "AAPL","MSFT","NVDA","AMZN","GOOGL","META",
    "AMD","TSLA","AVGO","NFLX","PLTR","COST"
]

# ---------- Data ----------
@st.cache_data(ttl=300)
def usd_thb():
    try:
        fx = yf.Ticker("THB=X").history(period="5d", interval="1d")
        if not fx.empty:
            return float(fx["Close"].dropna().iloc[-1])
    except Exception:
        pass
    return 33.0

@st.cache_data(ttl=300)
def stock_history(symbol, period="1y"):
    return yf.Ticker(symbol).history(period=period, interval="1d", auto_adjust=False)

@st.cache_data(ttl=900)
def stock_info(symbol):
    try:
        return yf.Ticker(symbol).info or {}
    except Exception:
        return {}

def rsi(series, n=14):
    d = series.diff()
    g = d.clip(lower=0)
    l = -d.clip(upper=0)
    ag = g.ewm(alpha=1/n, adjust=False, min_periods=n).mean()
    al = l.ewm(alpha=1/n, adjust=False, min_periods=n).mean()
    rs = ag / al.replace(0, np.nan)
    return 100 - 100/(1+rs)

def indicators(df):
    x = df.copy()
    for n in [9,21,50,200]:
        x[f"EMA{n}"] = x["Close"].ewm(span=n, adjust=False).mean()
    x["RSI14"] = rsi(x["Close"])
    e12 = x["Close"].ewm(span=12, adjust=False).mean()
    e26 = x["Close"].ewm(span=26, adjust=False).mean()
    x["MACD"] = e12 - e26
    x["MACD_SIGNAL"] = x["MACD"].ewm(span=9, adjust=False).mean()
    x["MACD_HIST"] = x["MACD"] - x["MACD_SIGNAL"]
    x["VOL20"] = x["Volume"].rolling(20).mean()
    x["VOL_RATIO"] = x["Volume"] / x["VOL20"].replace(0, np.nan)
    x["SUPPORT20"] = x["Low"].rolling(20).min()
    x["RESIST20"] = x["High"].rolling(20).max()
    x["VOLATILITY20"] = x["Close"].pct_change().rolling(20).std() * math.sqrt(252)
    return x

def sf(v):
    try:
        v = float(v)
        if math.isnan(v) or math.isinf(v):
            return None
        return v
    except Exception:
        return None

def score(df, info=None):
    info = info or {}
    row = df.iloc[-1]
    c = float(row["Close"])
    e21, e50, e200 = map(sf, [row["EMA21"], row["EMA50"], row["EMA200"]])
    rrsi = sf(row["RSI14"])
    macdh = sf(row["MACD_HIST"])
    vr = sf(row["VOL_RATIO"])
    vol = sf(row["VOLATILITY20"])
    sup, res = sf(row["SUPPORT20"]), sf(row["RESIST20"])

    points = 0
    pos, warn = [], []

    if e21 and c > e21:
        points += 10; pos.append("ราคาอยู่เหนือ EMA21")
    else: warn.append("ราคายังไม่ยืนเหนือ EMA21")

    if e21 and e50 and e21 > e50:
        points += 9; pos.append("EMA21 > EMA50")
    else: warn.append("แนวโน้มกลางยังไม่แข็งแรง")

    if e50 and c > e50: points += 6
    if e200 and c > e200:
        points += 7; pos.append("ราคาอยู่เหนือ EMA200")
    else: warn.append("แนวโน้มใหญ่ยังต้องระวัง")

    if rrsi is not None:
        if 45 <= rrsi <= 65:
            points += 12; pos.append(f"RSI {rrsi:.1f} อยู่ในโซนดี")
        elif 35 <= rrsi < 45 or 65 < rrsi <= 72:
            points += 7
        elif rrsi > 72:
            points += 2; warn.append(f"RSI {rrsi:.1f} เริ่มร้อนแรง")
        else:
            points += 3

    if macdh is not None and macdh > 0:
        points += 11; pos.append("MACD Momentum เป็นบวก")
    else: warn.append("MACD ยังไม่สนับสนุน")

    if vr is not None:
        if vr >= 1.15:
            points += 8; pos.append(f"Volume สูงกว่าค่าเฉลี่ย {vr:.2f}x")
        elif vr >= .75:
            points += 5
        else:
            points += 2; warn.append("Volume ค่อนข้างเบา")

    if sup and res and res > sup:
        loc = (c-sup)/(res-sup)
        if .10 <= loc <= .70:
            points += 10; pos.append("ตำแหน่งราคาไม่ชิดแนวต้านเกินไป")
        elif loc < .10:
            points += 8
        elif loc <= .90:
            points += 5
        else:
            warn.append("ราคาอยู่ใกล้แนวต้านระยะสั้น")

    if e21 and abs(c-e21)/c <= .05:
        points += 5

    rev = sf(info.get("revenueGrowth"))
    earn = sf(info.get("earningsGrowth"))
    roe = sf(info.get("returnOnEquity"))
    if rev is not None and rev > 0:
        points += 4; pos.append(f"รายได้เติบโต {rev*100:.1f}%")
    if earn is not None and earn > 0:
        points += 4; pos.append(f"กำไรเติบโต {earn*100:.1f}%")
    if roe is not None and roe > .10: points += 2

    if vol is not None:
        if vol < .30: points += 12
        elif vol < .50: points += 8
        elif vol < .75:
            points += 4; warn.append("ความผันผวนค่อนข้างสูง")
        else:
            warn.append("ความผันผวนสูง")

    points = max(0, min(100, int(round(points))))
    if points >= 80: label = "🟢 น่าสนใจมาก"
    elif points >= 68: label = "🟢 น่าสนใจ"
    elif points >= 55: label = "🟡 รอจังหวะ"
    elif points >= 42: label = "🟠 เสี่ยงสูง"
    else: label = "🔴 ยังไม่ผ่านเกณฑ์"

    return {
        "score":points,"label":label,"close":c,"ema21":e21,"ema50":e50,"ema200":e200,
        "rsi":rrsi,"macd":macdh,"vol_ratio":vr,"volatility":vol,"support":sup,"resistance":res,
        "positive":pos[:6],"warning":warn[:6],
    }

def trade_plan(a, capital_thb, fx, allocation_pct, risk_pct):
    c = a["close"]
    sup = a["support"] or c*.95
    e21 = a["ema21"] or c
    preferred = max(sup*1.01, min(c, e21*1.01))
    entry = (preferred + c)/2
    entry_low = min(preferred,c)*.995
    entry_high = max(preferred,c)*1.005
    stop = max(sup*.985, entry*.93)
    if stop >= entry: stop = entry*.96
    per_share_risk = max(entry-stop, entry*.01)

    max_position_thb = capital_thb*allocation_pct
    risk_budget_thb = capital_thb*risk_pct
    qty_alloc = (max_position_thb/fx)/entry
    qty_risk = (risk_budget_thb/fx)/per_share_risk
    qty = max(0, min(qty_alloc, qty_risk))
    pos_thb = qty*entry*fx
    actual_risk = qty*per_share_risk*fx

    return {
        "entry_low":entry_low, "entry_high":entry_high,
        "stop":stop, "target1":entry+per_share_risk*1.5, "target2":entry+per_share_risk*2.5,
        "qty":qty, "position_thb":pos_thb, "risk_thb":actual_risk,
        "order_usd":qty*entry,
    }

def quick_scan(symbol):
    df = stock_history(symbol, "1y")
    if df is None or df.empty or len(df) < 60:
        return None
    d = indicators(df)
    a = score(d, {})
    day = d["Close"].pct_change().iloc[-1]*100
    return {
        "Ticker":symbol, "Score":a["score"], "มุมมอง":a["label"],
        "ราคา":round(a["close"],2), "วันนี้ %":round(float(day),2),
        "RSI":None if a["rsi"] is None else round(a["rsi"],1)
    }

def full_analysis(symbol, capital, fx, alloc, risk):
    symbol = symbol.strip().upper()
    df = stock_history(symbol, "1y")
    if df is None or df.empty or len(df)<60:
        raise ValueError("ไม่พบข้อมูลหุ้น หรือข้อมูลย้อนหลังไม่เพียงพอ")
    info = stock_info(symbol)
    d = indicators(df)
    a = score(d, info)
    p = trade_plan(a, capital, fx, alloc, risk)
    return d, info, a, p

# ---------- State ----------
if "watchlist" not in st.session_state:
    st.session_state.watchlist = ["AAPL","MSFT","NVDA"]
if "journal" not in st.session_state:
    st.session_state.journal = []

# ---------- Header ----------
st.title("📈 Trade Assistant 500")
st.markdown('<div class="small-note">ตัวช่วยวิเคราะห์หุ้นสหรัฐสำหรับใช้คู่กับ Webull บนมือถือ</div>', unsafe_allow_html=True)

with st.expander("⚙️ ตั้งค่าพอร์ต", expanded=False):
    capital = st.number_input("ทุน (บาท)", min_value=100.0, value=500.0, step=100.0)
    fx = st.number_input("USD/THB", min_value=20.0, max_value=60.0, value=round(usd_thb(),2), step=.1)
    allocation = st.slider("เงินสูงสุดต่อหุ้น", 10, 100, 25, 5)/100
    risk = st.slider("ความเสี่ยงสูงสุดต่อครั้ง", .5, 5.0, 1.0, .5)/100

menu = st.radio(
    "เมนู",
    ["🔥 หุ้นวันนี้","🔎 วิเคราะห์","⭐ Watchlist","⚖️ เปรียบเทียบ","📝 Journal"],
    horizontal=True,
    label_visibility="collapsed"
)

# ---------- Today ----------
if menu == "🔥 หุ้นวันนี้":
    st.subheader("🔥 หุ้นน่าสนใจจากชุดติดตาม")
    st.caption("สแกนจากกฎ Technical ของระบบ ไม่ใช่การรับประกันผลตอบแทน")
    if st.button("สแกนหุ้นวันนี้", type="primary"):
        rows=[]
        bar=st.progress(0)
        for i,s in enumerate(DEFAULT_UNIVERSE):
            try:
                x=quick_scan(s)
                if x: rows.append(x)
            except Exception:
                pass
            bar.progress((i+1)/len(DEFAULT_UNIVERSE))
        bar.empty()
        if rows:
            xdf=pd.DataFrame(rows).sort_values(["Score","วันนี้ %"], ascending=[False,False])
            st.dataframe(xdf, use_container_width=True, hide_index=True)
            best=xdf.iloc[0]
            st.success(f'คะแนนสูงสุดในชุดติดตาม: {best["Ticker"]} — {int(best["Score"])}/100')
            st.caption("แตะเมนู “วิเคราะห์” แล้วใส่ Ticker เพื่อดู Entry / Stop / Target แบบละเอียด")

# ---------- Analyze ----------
elif menu == "🔎 วิเคราะห์":
    symbol=st.text_input("Ticker", value="AAPL", placeholder="เช่น AAPL, NVDA, MSFT").upper()
    c1,c2=st.columns(2)
    analyze=c1.button("วิเคราะห์", type="primary")
    if c2.button("⭐ เพิ่ม Watchlist"):
        if symbol and symbol not in st.session_state.watchlist:
            st.session_state.watchlist.append(symbol)
            st.success(f"เพิ่ม {symbol} แล้ว")

    if analyze:
        try:
            df,info,a,p=full_analysis(symbol,capital,fx,allocation,risk)
            st.markdown(
                f'<div class="hero"><b>{symbol}</b><br>'
                f'<span class="score">{a["score"]}/100</span><br>{a["label"]}</div>',
                unsafe_allow_html=True
            )
            x1,x2=st.columns(2)
            x1.metric("ราคาล่าสุด", f'${a["close"]:.2f}')
            x2.metric("RSI(14)", "-" if a["rsi"] is None else f'{a["rsi"]:.1f}')

            chart=df[["Close","EMA21","EMA50","EMA200"]].dropna(how="all").tail(180)
            st.line_chart(chart)

            st.subheader("🎯 แผนตามกฎระบบ")
            t1,t2=st.columns(2)
            t1.metric("Entry", f'${p["entry_low"]:.2f}–${p["entry_high"]:.2f}')
            t2.metric("Stop Loss", f'${p["stop"]:.2f}')
            t3,t4=st.columns(2)
            t3.metric("Target 1", f'${p["target1"]:.2f}')
            t4.metric("Target 2", f'${p["target2"]:.2f}')

            m1,m2=st.columns(2)
            m1.metric("เงินที่ใช้ตามกฎ", f'{p["position_thb"]:.0f} บาท')
            m2.metric("Fractional Qty", f'{p["qty"]:.4f}')

            st.metric("เงินที่เสี่ยงโดยประมาณ", f'{p["risk_thb"]:.1f} บาท')

            if p["order_usd"] < 1:
                st.warning("ขนาดรายการต่ำกว่า US$1 — อาจต่ำกว่าขั้นต่ำของ Fractional Share")

            with st.expander("✅ เหตุผลที่ระบบให้คะแนน"):
                for z in a["positive"]:
                    st.write("✅",z)
            with st.expander("⚠️ จุดที่ต้องระวัง"):
                for z in a["warning"]:
                    st.write("⚠️",z)

            st.subheader("🏢 พื้นฐานบริษัท")
            name=info.get("longName") or info.get("shortName") or symbol
            st.write(f"**{name}**")
            frows=[
                ["Sector",info.get("sector","-")],
                ["P/E",info.get("trailingPE","-")],
                ["Forward P/E",info.get("forwardPE","-")],
                ["Revenue Growth", "-" if sf(info.get("revenueGrowth")) is None else f'{sf(info.get("revenueGrowth"))*100:.1f}%'],
                ["Earnings Growth","-" if sf(info.get("earningsGrowth")) is None else f'{sf(info.get("earningsGrowth"))*100:.1f}%'],
                ["ROE","-" if sf(info.get("returnOnEquity")) is None else f'{sf(info.get("returnOnEquity"))*100:.1f}%'],
            ]
            st.dataframe(pd.DataFrame(frows,columns=["หัวข้อ","ค่า"]),hide_index=True,use_container_width=True)

        except Exception as e:
            st.error(f"วิเคราะห์ไม่ได้: {e}")

# ---------- Watchlist ----------
elif menu == "⭐ Watchlist":
    st.subheader("⭐ Watchlist")
    if not st.session_state.watchlist:
        st.info("ยังไม่มีหุ้นใน Watchlist")
    else:
        remove=None
        for s in st.session_state.watchlist:
            c1,c2,c3=st.columns([2,2,1])
            c1.write(f"**{s}**")
            try:
                q=quick_scan(s)
                c2.write(f'{q["Score"]}/100 · {q["มุมมอง"]}')
            except Exception:
                c2.write("โหลดไม่ได้")
            if c3.button("ลบ",key=f"del_{s}"):
                remove=s
        if remove:
            st.session_state.watchlist.remove(remove)
            st.rerun()

# ---------- Compare ----------
elif menu == "⚖️ เปรียบเทียบ":
    raw=st.text_input("Ticker หลายตัว คั่นด้วย ,", value="AAPL,MSFT,NVDA,AMD")
    if st.button("เปรียบเทียบ", type="primary"):
        rows=[]
        for s in [x.strip().upper() for x in raw.split(",") if x.strip()][:10]:
            try:
                q=quick_scan(s)
                if q: rows.append(q)
            except Exception:
                rows.append({"Ticker":s,"Score":None,"มุมมอง":"ข้อมูลไม่พอ"})
        if rows:
            rdf=pd.DataFrame(rows).sort_values("Score",ascending=False,na_position="last")
            st.dataframe(rdf,use_container_width=True,hide_index=True)

# ---------- Journal ----------
elif menu == "📝 Journal":
    st.subheader("📝 Trading Journal")
    ticker=st.text_input("Ticker",key="jt").upper()
    c1,c2=st.columns(2)
    entry=c1.number_input("ราคาเข้า $",min_value=0.0,step=.01)
    exitp=c2.number_input("ราคาออก $",min_value=0.0,step=.01)
    amount=st.number_input("เงินที่ใช้ (บาท)",min_value=0.0,step=10.0)
    note=st.text_input("เหตุผล / หมายเหตุ")
    if st.button("บันทึก",type="primary"):
        ret=None
        if entry>0 and exitp>0: ret=(exitp/entry-1)*100
        st.session_state.journal.append({
            "วันที่":str(datetime.now().date()),"Ticker":ticker,
            "เข้า":entry,"ออก":exitp,"เงินบาท":amount,
            "ผลตอบแทน %":None if ret is None else round(ret,2),"หมายเหตุ":note
        })
        st.success("บันทึกแล้ว")
    if st.session_state.journal:
        jdf=pd.DataFrame(st.session_state.journal)
        st.dataframe(jdf,use_container_width=True,hide_index=True)
        st.download_button(
            "ดาวน์โหลด CSV",
            jdf.to_csv(index=False).encode("utf-8-sig"),
            "trade_journal.csv","text/csv"
        )

st.divider()
st.caption(
    "⚠️ เครื่องมือนี้เป็นตัวช่วยคัดกรองและบริหารความเสี่ยง ไม่ใช่คำแนะนำส่วนบุคคลหรือการรับประกันกำไร "
    "ข้อมูลจากแหล่งภายนอกอาจล่าช้าหรือคลาดเคลื่อนได้ โปรดตรวจสอบราคาใน Webull ก่อนส่งคำสั่งจริง"
)

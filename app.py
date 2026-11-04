import asyncio

# 비동기 이벤트 루프 방어 코드
try:
    asyncio.get_running_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

import io
import os
import urllib.request
from datetime import datetime, timedelta
import pandas as pd
import streamlit as st
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

st.set_page_config(page_title="100x100 라벨 생성기", layout="centered")
st.title("🏷️ 100×100mm 납품 라벨 생성기")
st.write("발주 파일(`result.xls`)을 업로드하면 100×100mm 규격의 PDF 라벨을 생성합니다.")


# ---------------------------------------------------------
# 한글 폰트 안전 로드 (다운로드 실패 시에도 앱 중단 없이 대체)
# ---------------------------------------------------------
def get_label_font():
    font_file = "NanumGothic.ttf"
    if not os.path.exists(font_file):
        try:
            url = "https://raw.githubusercontent.com/google/fonts/main/ofl/nanumgothic/NanumGothic-Regular.ttf"
            urllib.request.urlretrieve(url, font_file)
        except Exception:
            pass

    if os.path.exists(font_file):
        try:
            pdfmetrics.registerFont(TTFont("NanumFont", font_file))
            return "NanumFont"
        except Exception:
            pass
    return "Helvetica"

FONT_NAME = get_label_font()


# ---------------------------------------------------------
# 발주 데이터 파싱 (HTML/XLS 호환)
# ---------------------------------------------------------
def parse_data(file_bytes):
    try:
        try:
            dfs = pd.read_html(io.BytesIO(file_bytes), encoding="cp949")
        except Exception:
            dfs = pd.read_html(io.BytesIO(file_bytes), encoding="utf-8")
        df = dfs[0]
        df.columns = [str(x).strip() for x in df.iloc[0]]
        df = df[1:].copy()
    except Exception:
        df = pd.read_excel(io.BytesIO(file_bytes))
        df.columns = [str(x).strip() for x in df.columns]

    df = df[df["매장"].notna()].copy()
    df = df[~df["매장"].astype(str).str.contains("합 계|합계", na=False)]
    return df


# ---------------------------------------------------------
# 100x100mm 라벨 PDF 생성
# ---------------------------------------------------------
def create_pdf(df):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=(100 * mm, 100 * mm))

    grouped = df.groupby("매장", sort=False)
    for store_name, group in grouped:
        x = 8 * mm
        y = 100 * mm - 14 * mm

        # 매장명
        c.setFont(FONT_NAME, 16)
        c.drawString(x, y, str(store_name))
        y -= 9 * mm

        # 상품명 및 주문수량 순차 출력
        for _, row in group.iterrows():
            item = str(row.get("상품", "")).strip()
            qty = str(row.get("주문수량", "")).strip()

            c.setFont(FONT_NAME, 10)
            c.drawString(x, y, item)
            y -= 5 * mm
            c.drawString(x, y, f"{qty} EA")
            y -= 7 * mm

        # 소비기한 (+5일)
        raw_date = group.iloc[0].get("납품예정일자", "")
        try:
            order_dt = pd.to_datetime(raw_date)
            exp_text = (order_dt + timedelta(days=5)).strftime("%y.%m.%d")
        except Exception:
            exp_text = "확인필요"

        # 소비기한 하단 배치
        c.setFont(FONT_NAME, 12)
        c.drawString(x, 10 * mm, "소비기한")
        c.drawString(x + 28 * mm, 10 * mm, exp_text)

        c.showPage()

    c.save()
    buffer.seek(0)
    return buffer


# ---------------------------------------------------------
# 업로드 UI
# ---------------------------------------------------------
uploaded_file = st.file_uploader(
    "발주 파일(result.xls)을 올려주세요", type=["xls", "xlsx", "html"]
)

if uploaded_file:
    try:
        df = parse_data(uploaded_file.read())
        st.success(f"매장 {len(df['매장'].unique())}개 확인 완료")

        cols = [
            c for c in ["납품예정일자", "매장", "상품", "주문수량"] if c in df.columns
        ]
        st.write(df[cols])

        pdf_data = create_pdf(df)
        st.download_button(
            "📥 100×100 라벨 PDF 다운로드",
            data=pdf_data,
            file_name=f"라벨_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
            mime="application/pdf",
            type="primary",
        )
    except Exception as e:
        st.error(f"처리 중 에러 발생: {e}")

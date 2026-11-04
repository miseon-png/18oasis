import streamlit as st
import pandas as pd
import tempfile
from datetime import timedelta
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os

# ⚠️ 한글 깨짐 방지를 위해 폰트 등록 (NanumGothic.ttf 파일을 코드와 같은 폴더에 넣어주세요)
# 폰트 파일이 없으면 에러가 납니다. 무료 폰트(나눔고딕 등)를 다운받아 같이 깃허브에 올려야 합니다.
try:
    pdfmetrics.registerFont(TTFont('KoreanFont', 'NanumGothic.ttf'))
    font_name = 'KoreanFont'
except:
    font_name = 'Helvetica' # 폰트가 없을 경우 기본 폰트 (한글 깨짐)

@st.cache_data
def create_labels(_df):
    # 날짜 데이터 변환 및 유통기한(+5일) 계산
    _df['납품예정일지'] = pd.to_datetime(_df['납품예정일지'])
    _df['유통기한'] = _df['납품예정일지'] + timedelta(days=5)
    _df['유통기한_str'] = _df['유통기한'].dt.strftime('%y%m%d') # YYMMDD 포맷

    # 서버 메모리를 쓰지 않도록 임시 파일 생성
    temp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    
    # 10cm x 10cm 캔버스 설정 (10cm = 100mm)
    c = canvas.Canvas(temp_pdf.name, pagesize=(100*mm, 100*mm))
    
    # 매장별로 데이터 묶기 (한 매장에 여러 상품이 있어도 하나로 처리)
    grouped = _df.groupby(['매장', '유통기한_str'])
    
    for (store, exp_date), group in grouped:
        # 1. 맨 위: 매장 이름
        c.setFont(font_name, 16)
        c.drawString(10*mm, 85*mm, f"매장: {store}")
        
        # 2. 중간: 상품명 및 주문수량+단위
        c.setFont(font_name, 10)
        y_position = 75*mm # 상품 목록이 시작될 Y 좌표
        
        for _, row in group.iterrows():
            product_name = str(row['상품'])
            qty_unit = f"{row['주문수량']} {row['단위']}"
            
            # 상품명과 수량 출력
            c.drawString(10*mm, y_position, f"{product_name}")
            c.drawString(80*mm, y_position, f"{qty_unit}")
            
            y_position -= 6*mm # 다음 상품은 아래 줄에 출력
            
            # 상품이 너무 많아서 라벨을 벗어나면 다음 장으로 넘기는 로직 (선택사항)
            if y_position < 25*mm:
                c.drawString(10*mm, y_position, "...(이하 생략 - 상품 과다)...")
                break
                
        # 3. 맨 아래: 유통기한
        c.setFont(font_name, 14)
        c.drawString(10*mm, 15*mm, f"유통기한: {exp_date}")
        
        # 한 장 완성 후 다음 페이지로 넘김
        c.showPage()
        
    c.save()
    return temp_pdf.name

# --- Streamlit 화면 구성 ---
st.title("📦 매장별 물류 라벨 생성기 (10x10cm)")

uploaded_file = st.file_uploader("엑셀 파일을 업로드하세요", type=['xlsx'])

if uploaded_file is not None:
    try:
        # 엑셀 읽기
        df = pd.read_excel(uploaded_file)
        
        with st.spinner('라벨 PDF를 생성하고 있습니다...'):
            # PDF 생성 (캐싱되어 있어서 다시 눌러도 메모리 터지지 않음)
            pdf_path = create_labels(df)
            
            # 생성된 임시 파일 읽어서 다운로드 버튼 제공
            with open(pdf_path, "rb") as f:
                st.download_button(
                    label="📥 10x10 라벨 PDF 다운로드",
                    data=f,
                    file_name="store_labels.pdf",
                    mime="application/pdf"
                )
    except Exception as e:
        st.error(f"오류가 발생했습니다: {e}")

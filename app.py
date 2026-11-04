import streamlit as st
import pandas as pd
import tempfile
from datetime import timedelta
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

st.title("📦 매장별 물류 라벨 생성기 (안전 모드)")

uploaded_file = st.file_uploader("엑셀 파일을 업로드하세요", type=['xlsx'])

if uploaded_file is not None:
    st.info("✅ 1. 엑셀 파일 업로드 완료! 데이터를 읽습니다...")
    
    try:
        # 1. 엑셀 읽기
        df = pd.read_excel(uploaded_file)
        st.success(f"✅ 2. 엑셀 데이터 읽기 완료! (총 {len(df)}줄)")
        
        # 2. 날짜 데이터 안전하게 변환 (에러가 나면 무시하고 빈칸 처리)
        df['납품예정일지'] = pd.to_datetime(df['납품예정일지'], errors='coerce')
        df['유통기한'] = df['납품예정일지'] + timedelta(days=5)
        df['유통기한_str'] = df['유통기한'].dt.strftime('%y%m%d').fillna('날짜없음')
        st.success("✅ 3. 유통기한 날짜 계산 완료!")
        
        # 3. 폰트 설정 (폰트 없으면 경고 띄우고 기본 폰트로 진행)
        try:
            pdfmetrics.registerFont(TTFont('KoreanFont', 'NanumGothic.ttf'))
            font_name = 'KoreanFont'
        except:
            font_name = 'Helvetica'
            st.warning("⚠️ 한글 폰트(NanumGothic.ttf)가 없어 임시 영어 폰트로 진행합니다.")
            
        # 4. PDF 캔버스 생성
        temp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        c = canvas.Canvas(temp_pdf.name, pagesize=(100*mm, 100*mm))
        
        # 매장별 데이터 묶기
        df['매장'] = df['매장'].fillna('알수없는매장')
        grouped = df.groupby(['매장', '유통기한_str'])
        st.info(f"✅ 4. 총 {len(grouped)}개의 매장 라벨을 그리기 시작합니다...")
        
        # 라벨 그리기 반복문
        for (store, exp_date), group in grouped:
            c.setFont(font_name, 16)
            c.drawString(10*mm, 85*mm, f"매장: {store}")
            
            c.setFont(font_name, 10)
            y_position = 75*mm
            
            for _, row in group.iterrows():
                product_name = str(row['상품'])
                qty_unit = f"{row['주문수량']} {row['단위']}"
                
                c.drawString(10*mm, y_position, f"{product_name}")
                c.drawString(80*mm, y_position, f"{qty_unit}")
                
                y_position -= 6*mm
                if y_position < 25*mm:
                    c.drawString(10*mm, y_position, "...(이하 생략)...")
                    break
                    
            c.setFont(font_name, 14)
            c.drawString(10*mm, 15*mm, f"유통기한: {exp_date}")
            c.showPage()
            
        c.save()
        st.success("✅ 5. PDF 생성 완료! 아래 버튼이 나타납니다.")
        
        # 5. 다운로드 버튼 생성
        with open(temp_pdf.name, "rb") as f:
            st.download_button(
                label="📥 10x10 라벨 PDF 다운로드",
                data=f,
                file_name="store_labels.pdf",
                mime="application/pdf"
            )
            
    except Exception as e:
        # 어디서 어떤 에러가 났는지 화면에 빨간색으로 출력해줍니다.
        st.error(f"❌ 작업 중 에러가 발생했습니다: {e}")

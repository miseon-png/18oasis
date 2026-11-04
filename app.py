import streamlit as st
import pandas as pd
import tempfile
from datetime import timedelta
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

st.title("📦 매장별 물류 라벨 생성기 (안전 모드)")

uploaded_file = st.file_uploader("엑셀 파일을 업로드하세요", type=['xlsx', 'xls'])

if uploaded_file is not None:
    st.info("✅ 1. 엑셀 파일 업로드 완료! 데이터를 읽습니다...")
    
    try:
        df = pd.read_excel(uploaded_file)
        st.success(f"✅ 2. 엑셀 데이터 읽기 완료! (총 {len(df)}줄)")
        
        # 날짜 데이터 변환 및 소비기한(+5일) 계산
        df['납품예정일자'] = pd.to_datetime(df['납품예정일자'], errors='coerce')
        df['유통기한'] = df['납품예정일자'] + timedelta(days=5)
        df['유통기한_str'] = df['유통기한'].dt.strftime('%y.%m.%d').fillna('날짜없음')
        st.success("✅ 3. 소비기한 날짜 계산 완료!")
        
        # 다운로드 파일명을 위한 날짜 추출
        try:
            file_date_str = df['납품예정일자'].dropna().iloc[0].strftime('%y%m%d')
        except:
            file_date_str = "날짜없음"
        
        download_filename = f"오아이스 매장라벨 ({file_date_str}).pdf"
        
        # 폰트 설정
        try:
            pdfmetrics.registerFont(TTFont('KoreanFont', 'NanumGothic.ttf'))
            font_name = 'KoreanFont'
        except:
            font_name = 'Helvetica'
            st.warning("⚠️ 한글 폰트(NanumGothic.ttf)가 없어 임시 영어 폰트로 진행합니다.")
            
        temp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        c = canvas.Canvas(temp_pdf.name, pagesize=(100*mm, 100*mm))
        
        df['매장'] = df['매장'].fillna('알수없는매장')
        grouped = df.groupby(['매장', '유통기한_str'])
        st.info(f"✅ 4. 총 {len(grouped)}개의 매장 라벨을 그리기 시작합니다...")
        
        for (store, exp_date), group in grouped:
            # 1. 맨 위: 매장명 (크기 28, 상단 88mm)
            c.setFont(font_name, 28)
            c.drawString(10*mm, 88*mm, f"{store}")
            
            # 2. 중간: 상품 목록 시작 위치 (74mm)
            y_position = 74*mm
            
            for _, row in group.iterrows():
                product_name = str(row['상품'])
                qty_unit = f"{row['주문수량']} {row['단위']}"
                
                # 상품명 (크기 13)
                c.setFont(font_name, 13)
                c.drawString(10*mm, y_position, f"{product_name}")
                y_position -= 5.5*mm 
                
                # 수량 (크기 16)
                c.setFont(font_name, 16)
                c.drawString(10*mm, y_position, f"수량: {qty_unit}")
                
                # 다음 상품 간격 (한 제품당 약 12mm 사용 -> 3개 제품 총 36mm로 여유 확보)
                y_position -= 6.5*mm 
                
                if y_position < 20*mm:
                    break
                    
            # 3. 맨 아래: 소비기한 (크기 28, 하단 9mm)
            c.setFont(font_name, 28) 
            c.drawString(10*mm, 9*mm, f"소비기한: {exp_date}")
            c.showPage()
            
        c.save()
        st.success(f"✅ 5. PDF 생성 완료! 파일명: {download_filename}")
        
        with open(temp_pdf.name, "rb") as f:
            st.download_button(
                label="📥 10x10 라벨 PDF 다운로드",
                data=f,
                file_name=download_filename,
                mime="application/pdf"
            )
            
    except Exception as e:
        st.error(f"❌ 작업 중 에러가 발생했습니다: {e}")

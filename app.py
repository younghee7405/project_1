import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import platform

# ---------------------------------------------------------
# 0. 한글 폰트 설정 (환경별 호환)
# ---------------------------------------------------------
plt.rcParams['axes.unicode_minus'] = False
system_name = platform.system()
if system_name == 'Windows':
    plt.rc('font', family='NanumGothicEco.otf')
elif system_name == 'Darwin': # Mac
    plt.rc('font', family='AppleGothic')
else: # Linux/Colab 등
    plt.rc('font', family='NanumGothic')

# 페이지 기본 설정
st.set_page_config(page_title="무역 분석 대시보드", layout="wide")

# ---------------------------------------------------------
# 1. 데이터 로드 및 전처리
# ---------------------------------------------------------
@st.cache_data
def load_data():
    baci_df = pd.read_csv('baci_85_sample.csv')
    country_df = pd.read_csv('country_codes_sample.csv')

    # BACI 컬럼 통일 처리 (대소문자 무관)
    baci_df.columns = [c.lower() for c in baci_df.columns]
    country_df.columns = [c.lower() for c in country_df.columns]

    # 국가 코드(i: 수출국, country_code/iso 등) 매핑 확인
    code_col = [c for c in country_df.columns if 'code' in c or 'iso' in c or c == 'id'][0]
    name_col = [c for c in country_df.columns if 'name' in c or 'country' in c][0]
    
    country_map = dict(zip(country_df[code_col], country_df[name_col]))

    # 수출국 컬럼(i)을 국가명으로 매핑 (없으면 코드 유지)
    export_col = 'i' if 'i' in baci_df.columns else ('exporter' if 'exporter' in baci_df.columns else baci_df.columns[1])
    baci_df['country_name'] = baci_df[export_col].map(country_map).fillna(baci_df[export_col].astype(str))

    # 무역액 컬럼(v: 천 달러 단위 또는 달러 단위)
    val_col = 'v' if 'v' in baci_df.columns else ('trade_value' if 'trade_value' in baci_df.columns else 'value')
    baci_df['trade_val'] = pd.to_numeric(baci_df[val_col], errors='coerce').fillna(0)

    # 연도 컬럼(t: year)
    year_col = 't' if 't' in baci_df.columns else ('year' if 'year' in baci_df.columns else baci_df.columns[0])
    baci_df['year'] = baci_df[year_col]

    # 무역액 등급 분류 (3분위 기준: 대, 중, 소)
    try:
        baci_df['무역액등급'] = pd.qcut(
            baci_df['trade_val'].rank(method='first'),
            q=3,
            labels=['소', '중', '대']
        )
    except Exception:
        baci_df['무역액등급'] = '중'

    return baci_df

raw_baci = load_data()

# ---------------------------------------------------------
# 2. 사이드바 (필터)
# ---------------------------------------------------------
st.sidebar.header("🔍 필터 설정")

# 국가 선택
all_countries = sorted(list(raw_baci['country_name'].unique()))
selected_countries = st.sidebar.multiselect(
    "국가 선택 (비워둘 시 전체)",
    options=all_countries,
    default=[]
)

# 무역액 등급 선택
grade_options = ['대', '중', '소']
selected_grades = st.sidebar.multiselect(
    "무역액 등급 선택 (대, 중, 소)",
    options=grade_options,
    default=grade_options
)

# 데이터 필터링
filtered_df = raw_baci.copy()
if selected_countries:
    filtered_df = filtered_df[filtered_df['country_name'].isin(selected_countries)]
if selected_grades:
    filtered_df = filtered_df[filtered_df['무역액등급'].isin(selected_grades)]

# ---------------------------------------------------------
# 3. 메인 화면 출력
# ---------------------------------------------------------
# 1. 타이틀
st.title("📊 무역 분석 대시보드")
st.markdown("---")

# 2. baci_85_sample.csv 파일의 결측치
st.subheader("1. 원본 데이터 결측치 현황")
missing_df = pd.DataFrame({
    '컬럼명': raw_baci.columns,
    '결측치 개수': raw_baci.isnull().sum().values,
    '결측 비율(%)': (raw_baci.isnull().mean() * 100).round(2).values
})
st.dataframe(missing_df.T, use_container_width=True)

st.markdown("---")

# 3. 총거래건수 / 총 수출액(달러)
st.subheader("2. 주요 지표 요약")
col1, col2 = st.columns(2)

total_count = len(filtered_df)
total_trade_value = filtered_df['trade_val'].sum()

col1.metric(label="총 거래 건수", value=f"{total_count:,} 건")
col2.metric(label="총 수출액(달러)", value=f"${total_trade_value:,.2f}")

st.markdown("---")

# 4. 국가*연도 수출액 히트맵(상위 8개국) & 무역액 등급분포
st.subheader("3. 수출액 히트맵 및 등급 분포")
col_chart1, col_chart2 = st.columns(2)

with col_chart1:
    st.markdown("#### 국가 × 연도 수출액 히트맵 (상위 8개국)")
    # 상위 8개국 선정 (필터링된 데이터 기준)
    top_8_countries = filtered_df.groupby('country_name')['trade_val'].sum().nlargest(8).index
    heat_data = filtered_df[filtered_df['country_name'].isin(top_8_countries)]
    
    if not heat_data.empty:
        pivot_heat = heat_data.pivot_table(index='country_name', columns='year', values='trade_val', aggfunc='sum', fill_value=0)
        fig_heat, ax_heat = plt.subplots(figsize=(7, 5))
        sns.heatmap(pivot_heat, annot=False, cmap='YlGnBu', fmt='.0f', ax=ax_heat)
        ax_heat.set_xlabel("연도")
        ax_heat.set_ylabel("국가")
        st.pyplot(fig_heat)
    else:
        st.info("표시할 데이터가 없습니다.")

with col_chart2:
    st.markdown("#### 무역액 등급 분포")
    grade_counts = filtered_df['무역액등급'].value_counts().reindex(['대', '중', '소']).fillna(0)
    
    fig_grade, ax_grade = plt.subplots(figsize=(7, 5))
    bars = ax_grade.bar(grade_counts.index, grade_counts.values, color=['#4C72B0', '#55A868', '#C44E52'])
    ax_grade.set_xlabel("등급")
    ax_grade.set_ylabel("건수")
    for bar in bars:
        height = bar.get_height()
        ax_grade.text(bar.get_x() + bar.get_width()/2., height + 0.5, f'{int(height):,}', ha='center', va='bottom')
    st.pyplot(fig_grade)

st.markdown("---")

# 5. 상위 5개국 * 무역액 등급 교차표 (원본건수 & 정규화비율)
st.subheader("4. 상위 5개국 × 무역액 등급 교차표")
top_5_countries = filtered_df.groupby('country_name')['trade_val'].sum().nlargest(5).index
crosstab_df = filtered_df[filtered_df['country_name'].isin(top_5_countries)]

if not crosstab_df.empty:
    col_cross1, col_cross2 = st.columns(2)
    
    # 원본 건수
    ct_counts = pd.crosstab(crosstab_df['country_name'], crosstab_df['무역액등급'])
    # 정규화 비율 (행 기준 백분율 %)
    ct_normalized = pd.crosstab(crosstab_df['country_name'], crosstab_df['무역액등급'], normalize='index') * 100

    with col_cross1:
        st.markdown("##### 원본 건수")
        st.dataframe(ct_counts, use_container_width=True)

    with col_cross2:
        st.markdown("##### 정규화 비율 (%)")
        st.dataframe(ct_normalized.round(2), use_container_width=True)
else:
    st.info("표시할 데이터가 없습니다.")
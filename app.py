@st.cache_data
def load_data():
    baci_df = pd.read_csv('baci_85_sample.csv')
    country_df = pd.read_csv('country_codes_sample.csv')

    # 컬럼명 공백 제거 및 소문자 통일
    baci_df.columns = [str(c).strip().lower() for c in baci_df.columns]
    country_df.columns = [str(c).strip().lower() for c in country_df.columns]

    # 국가 코드 컬럼 감지 (없을 경우 첫 번째 컬럼 사용)
    code_candidates = [c for c in country_df.columns if any(k in c for k in ['code', 'iso', 'id', 'i', 'num'])]
    code_col = code_candidates[0] if code_candidates else country_df.columns[0]

    # 국가명 컬럼 감지 (없을 경우 두 번째 컬럼 또는 첫 번째 컬럼 사용)
    name_candidates = [c for c in country_df.columns if any(k in c for k in ['name', 'country', 'desc', 'label']) and c != code_col]
    if name_candidates:
        name_col = name_candidates[0]
    elif len(country_df.columns) > 1:
        name_col = country_df.columns[1]
    else:
        name_col = code_col
    
    country_map = dict(zip(country_df[code_col], country_df[name_col]))

    # 수출국 컬럼(i)을 국가명으로 매핑
    export_candidates = [c for c in baci_df.columns if c in ['i', 'exporter', 'iso_i', 'country']]
    export_col = export_candidates[0] if export_candidates else baci_df.columns[1]
    
    baci_df['country_name'] = baci_df[export_col].map(country_map).fillna(baci_df[export_col].astype(str))

    # 무역액 컬럼(v: value)
    val_candidates = [c for c in baci_df.columns if c in ['v', 'trade_value', 'value', 'val']]
    val_col = val_candidates[0] if val_candidates else baci_df.columns[-1]
    baci_df['trade_val'] = pd.to_numeric(baci_df[val_col], errors='coerce').fillna(0)

    # 연도 컬럼(t: year)
    year_candidates = [c for c in baci_df.columns if c in ['t', 'year', 'yr']]
    year_col = year_candidates[0] if year_candidates else baci_df.columns[0]
    baci_df['year'] = baci_df[year_col]

    # 무역액 등급 분류 (3분위 기준: 소, 중, 대)
    try:
        baci_df['무역액등급'] = pd.qcut(
            baci_df['trade_val'].rank(method='first'),
            q=3,
            labels=['소', '중', '대']
        )
    except Exception:
        baci_df['무역액등급'] = '중'

    return baci_df
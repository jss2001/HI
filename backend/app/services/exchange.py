import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Any

SYMBOLS = {
    "USD": "USDKRW=X",
    "EUR": "EURKRW=X",
    "JPY": "JPYKRW=X",
    "CNY": "CNYKRW=X"
}

def fetch_exchange_data(period: str = "120d") -> Dict[str, pd.DataFrame]:
    """각 통화별 환율 데이터를 수집합니다."""
    data = {}
    
    # 1. 일반 통화 수집 (USD, EUR, JPY)
    for code in ["USD", "EUR", "JPY"]:
        symbol = SYMBOLS[code]
        try:
            df = yf.download(symbol, period=period)
            if not df.empty:
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                df = df[['Close']].copy()
                df.dropna(inplace=True)
                data[code] = df
        except Exception as e:
            print(f"Error fetching {code}: {e}")

    # 2. CNY 특수 처리 (CNYKRW=X 히스토리 부족 대응)
    try:
        # USD/KRW와 USD/CNY를 사용하여 CNY/KRW 계산
        usd_krw = data.get("USD")
        usd_cny = yf.download("USDCNY=X", period=period)
        
        if usd_krw is not None and not usd_cny.empty:
            if isinstance(usd_cny.columns, pd.MultiIndex):
                usd_cny.columns = usd_cny.columns.get_level_values(0)
            
            usd_cny = usd_cny[['Close']].copy()
            # 두 데이터프레임 병합 (날짜 기준)
            combined = pd.merge(usd_krw, usd_cny, left_index=True, right_index=True, suffixes=('_krw', '_cny'))
            # CNY/KRW = (USD/KRW) / (USD/CNY)
            combined['Close'] = combined['Close_krw'] / combined['Close_cny']
            data["CNY"] = combined[['Close']]
    except Exception as e:
        print(f"Error calculating CNY: {e}")

    return data

def analyze_currency(code: str, df: pd.DataFrame) -> Dict[str, Any]:
    """단일 통화에 대한 기술적 분석을 수행합니다."""
    # 1. 이동평균
    df['MA7'] = df['Close'].rolling(window=7).mean()
    df['MA30'] = df['Close'].rolling(window=30).mean()
    
    # 2. 일일 변동률
    df['pct_change'] = df['Close'].pct_change() * 100
    
    # 3. 변동성 (20일 기준 표준편차)
    df['volatility'] = df['pct_change'].rolling(window=20).std()
    
    # 최신 데이터 추출
    latest = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else latest
    
    current_price = float(latest['Close'])
    # JPY 100엔 기준 보정
    display_price = current_price * 100 if code == "JPY" else current_price
    
    change_val = float(latest['Close'] - prev['Close'])
    change_pct = float(latest['pct_change'])
    
    # 4. 이상치 탐지 (변동률이 2표준편차를 벗어나는 경우)
    vol = float(latest['volatility'])
    is_outlier = abs(change_pct) > (2 * vol) if not np.isnan(vol) else False
    
    # 5. 이동평균 교차 신호
    signal = None
    if len(df) > 1:
        curr_ma7 = float(latest['MA7'])
        curr_ma30 = float(latest['MA30'])
        prev_ma7 = float(prev['MA7'])
        prev_ma30 = float(prev['MA30'])
        
        if prev_ma7 <= prev_ma30 and curr_ma7 > curr_ma30:
            signal = "Golden Cross"
        elif prev_ma7 >= prev_ma30 and curr_ma7 < curr_ma30:
            signal = "Dead Cross"

    return {
        "code": code,
        "current_price": round(display_price, 2),
        "change_val": round(change_val * (100 if code == "JPY" else 1), 2),
        "change_pct": round(change_pct, 2),
        "ma7": round(float(latest['MA7']) * (100 if code == "JPY" else 1), 2) if not np.isnan(latest['MA7']) else None,
        "ma30": round(float(latest['MA30']) * (100 if code == "JPY" else 1), 2) if not np.isnan(latest['MA30']) else None,
        "volatility": round(vol, 2) if not np.isnan(vol) else 0,
        "is_outlier": is_outlier,
        "signal": signal,
        "history": df.tail(30).reset_index().to_dict(orient='records') # 최근 30일 데이터만 전달
    }

def generate_report(analysis_list: List[Dict[str, Any]]) -> str:
    """분석 결과를 바탕으로 텍스트 리포트를 생성합니다."""
    report = []
    report.append(f"📅 {datetime.now().strftime('%Y-%m-%d')} 환율 자동 분석 리포트\n")
    
    for item in analysis_list:
        code = item['code']
        price = item['current_price']
        chg_pct = item['change_pct']
        
        status = "상승" if chg_pct > 0 else "하락" if chg_pct < 0 else "보합"
        trend = "상승 추세" if item['ma7'] and item['ma30'] and item['ma7'] > item['ma30'] else "하락 추세"
        
        line = f"[{code}] 현재 {price}원 ({chg_pct}% {status})"
        if item['is_outlier']:
            line += " ⚠️ 이상 변동 감지!"
        if item['signal']:
            line += f" ({item['signal']} 발생)"
        
        report.append(line)
        report.append(f"- 추세: {trend}, 변동성: {'높음' if item['volatility'] > 1.0 else '낮음'}")
        report.append("")
        
    return "\n".join(report)

def get_exchange_report():
    raw_data = fetch_exchange_data()
    analysis_results = []
    for code, df in raw_data.items():
        if len(df) < 5: 
            print(f"Warning: Not enough data for {code}. Rows: {len(df)}")
            continue
        try:
            res = analyze_currency(code, df)
            analysis_results.append(res)
        except Exception as e:
            print(f"Error analyzing {code}: {e}")
    
    report_text = generate_report(analysis_results)
    
    return {
        "timestamp": datetime.now().isoformat(),
        "analysis": analysis_results,
        "report": report_text
    }

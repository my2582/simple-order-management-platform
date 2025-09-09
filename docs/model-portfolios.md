# Model Portfolio Management Guide 📊

모델 포트폴리오 관리 및 커스터마이징 가이드입니다.

## 📋 모델 포트폴리오 개요

Simple Order Management Platform은 CSV 기반의 모델 포트폴리오 시스템을 사용합니다. 각 전략은 Portfolio ID로 구분되며, 종목별 목표 비중을 정의합니다.

### 현재 지원 포트폴리오

| Portfolio ID | 전략명 | 구성 | 특성 |
|--------------|--------|------|------|
| **B301** | Future Fund - GTAA | SPMO, SMH, IAU (33.33% 균등) | 글로벌 전술적 자산배분 |
| B101 | Peace of Mind | VTI, BND | 보수적 균형 전략 |
| B201 | Income Builder - 1 | - | 배당 중심 전략 |
| B202 | Income Builder - 2 | - | 고배당 전략 |

## 📁 파일 구조

### MP_Master.csv 파일 위치
```
data/model_portfolios/MP_Master.csv
```

### 표준 CSV 형식
```csv
Portfolio ID,Bucket Name,ISIN,Ticker,Weight,Effective Date
B301,Future Fund - GTAA,,SPMO,33.34,18/07/25
B301,Future Fund - GTAA,,SMH,33.33,18/07/25
B301,Future Fund - GTAA,,IAU,33.33,18/07/25
```

### 필드 설명

| 필드 | 필수 | 설명 | 예시 |
|------|------|------|------|
| **Portfolio ID** | ✅ | 포트폴리오 식별자 | B301, B101 |
| **Bucket Name** | ✅ | 전략 이름 | Future Fund - GTAA |
| **ISIN** | ❌ | 국제증권식별번호 | (보통 비워둠) |
| **Ticker** | ✅ | 종목 심볼 | SPMO, SMH, IAU |
| **Weight** | ✅ | 목표 비중 (%) | 33.33 |
| **Effective Date** | ✅ | 적용 날짜 | 18/07/25 |

## 🛠️ 새 모델 포트폴리오 생성

### 1단계: 전략 설계

새로운 전략을 만들기 전에 고려사항:

#### 투자 목표 정의
- **수익률 목표**: 연 몇 %를 목표로 하는가?
- **리스크 허용도**: 최대 몇 % 손실까지 감내할 것인가?
- **투자 기간**: 단기, 중기, 장기 중 어떤 전략인가?

#### 종목 선택 기준
- **유동성**: 충분한 거래량이 있는 종목인가?
- **수수료**: ETF의 경우 운용보수가 합리적인가?
- **상관관계**: 종목들 간의 분산효과가 있는가?

### 2단계: CSV 파일 편집

#### 예시: Conservative Growth 전략 (B401) 추가

```bash
# 백업 생성
cp data/model_portfolios/MP_Master.csv data/model_portfolios/MP_Master.csv.backup

# 파일 편집
vim data/model_portfolios/MP_Master.csv
```

새로 추가할 내용:
```csv
B401,Conservative Growth,,VTI,60.00,06/09/25
B401,Conservative Growth,,BND,25.00,06/09/25
B401,Conservative Growth,,VNQ,10.00,06/09/25
B401,Conservative Growth,,VEA,5.00,06/09/25
```

#### 비중 검증
```bash
# 포트폴리오 비중 합계 확인
simple-order list-portfolios
```

**중요**: 각 포트폴리오의 비중 합계는 정확히 100.00이어야 합니다.

### 3단계: 검증 및 테스트

```bash
# 1. 새 포트폴리오 확인
simple-order list-portfolios

# 2. 가상 주문 생성 테스트 (Paper Trading)
simple-order generate-orders DU123456 B401 --type deposit --amount 10000 --output test_B401.csv

# 3. 생성된 주문지 확인
cat data/output/test_B401.csv
```

## ⚖️ 기존 포트폴리오 수정

### GTAA 전략 (B301) 비중 조정 예시

현재 균등 비중에서 전술적 비중으로 변경:

#### Before (균등 비중):
```csv
B301,Future Fund - GTAA,,SPMO,33.34,18/07/25
B301,Future Fund - GTAA,,SMH,33.33,18/07/25
B301,Future Fund - GTAA,,IAU,33.33,18/07/25
```

#### After (전술적 비중):
```csv
B301,Future Fund - GTAA,,SPMO,40.00,06/09/25
B301,Future Fund - GTAA,,SMH,35.00,06/09/25
B301,Future Fund - GTAA,,IAU,25.00,06/09/25
```

### 종목 교체

#### SMH를 QQQ로 교체하는 경우:
```csv
# 기존
B301,Future Fund - GTAA,,SMH,33.33,18/07/25

# 변경
B301,Future Fund - GTAA,,QQQ,33.33,06/09/25
```

### Effective Date 업데이트
비중이나 종목을 변경할 때는 반드시 Effective Date를 업데이트하세요:
```
형식: DD/MM/YY
예시: 06/09/25 (2025년 9월 6일)
```

## 📊 고급 포트폴리오 전략

### 1. 섹터 로테이션 전략

기술주 중심 전략 (B501):
```csv
B501,Tech Rotation,,QQQ,40.00,06/09/25
B501,Tech Rotation,,ARKK,30.00,06/09/25
B501,Tech Rotation,,SOXX,20.00,06/09/25
B501,Tech Rotation,,WCLD,10.00,06/09/25
```

### 2. 글로벌 다변화 전략

국제 분산 전략 (B601):
```csv
B601,Global Diversified,,VTI,40.00,06/09/25
B601,Global Diversified,,VEA,25.00,06/09/25
B601,Global Diversified,,VWO,15.00,06/09/25
B601,Global Diversified,,BND,10.00,06/09/25
B601,Global Diversified,,VGIT,10.00,06/09/25
```

### 3. ESG 중심 전략

ESG 투자 전략 (B701):
```csv
B701,ESG Focus,,ESGV,50.00,06/09/25
B701,ESG Focus,,USSG,30.00,06/09/25
B701,ESG Focus,,ICLN,20.00,06/09/25
```

### 4. 배당 수익 전략

고배당 전략 (B801):
```csv
B801,High Dividend,,VYM,40.00,06/09/25
B801,High Dividend,,SCHD,30.00,06/09/25
B801,High Dividend,,DVY,20.00,06/09/25
B801,High Dividend,,VIG,10.00,06/09/25
```

## 🔄 리밸런싱 전략

### 정기 리밸런싱
월별, 분기별 또는 연별 리밸런싱 스케줄:

```bash
# 월말 리밸런싱 (첫째 주 금요일)
# crontab -e
0 16 1-7 * 5 /usr/local/bin/simple-order generate-orders DU123456 B301 --type rebalance --amount 100000

# 분기별 리밸런싱 (3, 6, 9, 12월)
0 16 1 3,6,9,12 * /usr/local/bin/simple-order generate-orders DU123456 B301 --type rebalance --amount 100000
```

### 임계값 기반 리밸런싱
포지션이 목표 비중에서 일정 % 이상 벗어날 때:

```bash
# 일일 포지션 체크 및 리밸런싱 필요성 판단
simple-order positions -o daily_check.xlsx
# Excel에서 수동 확인 또는 자동화 스크립트 작성
```

## 📈 백테스팅 및 성과 분석

### 포트폴리오 성과 추적

#### 1. 정기 포지션 스냅샷
```bash
# 매일 포지션 기록
simple-order positions -o "positions_$(date +%Y%m%d).xlsx"

# 월별 성과 요약
mkdir -p data/performance/$(date +%Y%m)
mv positions_*.xlsx data/performance/$(date +%Y%m)/
```

#### 2. 벤치마크 비교
각 전략별 적절한 벤치마크 설정:

| 전략 | 벤치마크 | 비교 지표 |
|------|----------|-----------|
| B301 (GTAA) | 60/40 포트폴리오 | 샤프비율, MDD |
| B101 (Conservative) | 보수적 혼합펀드 | 변동성, 안정성 |
| B501 (Tech) | QQQ | 베타, 알파 |

### 리스크 관리

#### 포트폴리오 리스크 지표 모니터링
- **최대 낙폭 (MDD)**: 각 전략별 허용 수준 설정
- **변동성**: 연율화 표준편차 추적
- **상관관계**: 종목 간 상관관계 정기 점검

#### 스톱로스 규칙
```csv
# 손절 규칙이 있는 포트폴리오 (메모)
# B301: 개별 종목 -20% 또는 포트폴리오 -15% 시 재검토
```

## 🛡️ 규정 준수 및 거버넌스

### 투자 정책서 (IPS) 반영
모델 포트폴리오는 다음을 준수해야 합니다:

#### 투자 한도
- **개별 종목**: 최대 50%
- **섹터 집중**: 최대 60%
- **해외 투자**: 최대 40%

#### 허용 투자 대상
- ✅ 상장 ETF
- ✅ 대형주 개별 주식 (시가총액 100억 이상)
- ❌ 레버리지 ETF (정책에 따라)
- ❌ 암호화폐 관련 상품

### 컴플라이언스 체크

포트폴리오 추가 시 확인사항:
```bash
# 1. 비중 합계 확인 (100.00%)
awk -F',' '$1=="B301" {sum+=$5} END {print "Total:", sum}' data/model_portfolios/MP_Master.csv

# 2. 개별 종목 한도 확인 (50% 미만)
awk -F',' '$1=="B301" && $5>50 {print "Warning:", $4, "exceeds 50%"}' data/model_portfolios/MP_Master.csv

# 3. 종목 중복 확인
awk -F',' '{count[$4]++} END {for(i in count) if(count[i]>1) print "Duplicate:", i}' data/model_portfolios/MP_Master.csv
```

## 🔧 문제 해결

### 일반적인 문제

#### 1. 비중 합계 오류
```
Error: Portfolio B301 weights sum to 99.99, expected 100.00
```

**해결책**:
```csv
# 소수점 반올림 조정
B301,Future Fund - GTAA,,SPMO,33.34,06/09/25  # 0.01 증가
B301,Future Fund - GTAA,,SMH,33.33,06/09/25
B301,Future Fund - GTAA,,IAU,33.33,06/09/25
```

#### 2. 종목 심볼 오류
```
Error: Symbol SPMO not found in IBKR
```

**해결책**:
1. IBKR에서 정확한 심볼 확인
2. 상장 폐지 여부 확인
3. 대체 ETF 검토

#### 3. 날짜 형식 오류
```
Error: Invalid date format in Effective Date
```

**해결책**:
```csv
# 올바른 형식: DD/MM/YY
06/09/25  ✅
2025-09-06  ❌
09/06/25  ❌ (월/일 순서 주의)
```

### 데이터 검증 스크립트

자동 검증을 위한 스크립트:
```bash
#!/bin/bash
# validate_portfolios.sh

CSV_FILE="data/model_portfolios/MP_Master.csv"

echo "Validating model portfolios..."

# 1. 파일 존재 확인
if [[ ! -f $CSV_FILE ]]; then
    echo "ERROR: MP_Master.csv not found"
    exit 1
fi

# 2. 각 포트폴리오별 비중 합계 확인
for portfolio in $(awk -F',' 'NR>1 {print $1}' $CSV_FILE | sort -u); do
    sum=$(awk -F',' -v p="$portfolio" '$1==p {sum+=$5} END {print sum}' $CSV_FILE)
    if (( $(echo "$sum != 100.00" | bc -l) )); then
        echo "WARNING: Portfolio $portfolio weights sum to $sum"
    else
        echo "OK: Portfolio $portfolio weights sum to 100.00"
    fi
done

# 3. 필수 필드 확인
awk -F',' 'NR>1 && ($1=="" || $2=="" || $4=="" || $5=="") {print "ERROR: Missing required field in line " NR}' $CSV_FILE

echo "Validation complete."
```

## 📚 참고 자료

### ETF 리서치 사이트
- **ETF.com**: 종합 ETF 정보
- **Morningstar**: ETF 등급 및 분석
- **ETF Database**: 상세 데이터 및 스크리닝

### 포트폴리오 이론
- **Modern Portfolio Theory (MPT)**: 위험 대비 수익 최적화
- **Factor Investing**: 팩터 기반 전략 구성
- **Strategic vs Tactical Asset Allocation**: 전략적/전술적 자산배분

### 백테스팅 도구
- **Portfolio Visualizer**: 무료 백테스팅
- **Quantopian/Zipline**: 프로그래밍 기반 백테스팅
- **Bloomberg Terminal**: 전문가용 분석 도구

모델 포트폴리오 관리를 통해 체계적이고 일관된 투자 전략을 실행할 수 있습니다!
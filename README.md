# Simple Order Management Platform 🚀

> **포트폴리오 관리와 모델 기반 리밸런싱을 위한 완전 통합 플랫폼**  
> IBKR API 연동 + 자동화된 포지션 다운로드 + 스마트 리밸런싱 시스템

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![IBKR](https://img.shields.io/badge/IBKR-API-green.svg)](https://interactivebrokers.github.io/tws-api/)
[![Production Ready](https://img.shields.io/badge/Production-Ready-success.svg)](#-deployment-infrastructure)

## 📋 **목차**

1. [🎯 핵심 기능](#-핵심-기능)
2. [🚀 빠른 시작](#-빠른-시작)
3. [📊 포지션 다운로드](#-포지션-다운로드-시스템)
4. [⚖️ 모델 포트폴리오 리밸런싱](#️-모델-포트폴리오-리밸런싱)
5. [🛠️ 일반적인 사용법](#️-일반적인-사용법)
6. [💡 실무 시나리오](#-실무-시나리오)
7. [🔧 고급 기능](#-고급-기능)

## 🎯 **핵심 기능**

### ✅ **포트폴리오 위치 추적**
- **IBKR 실시간 연동**: Interactive Brokers API를 통한 실시간 포지션 데이터
- **SGD 기준 통화**: 모든 금액이 자동으로 SGD로 통일 표시
- **Excel 표준 출력**: IBKR 호환 Summary + Matrix 시트 형식
- **다중 계좌 지원**: 여러 계좌를 한 번에 통합 다운로드

### ✅ **모델 포트폴리오 기반 리밸런싱**
- **GTAA 전략**: SPMO(33.34%) + SMH(33.33%) + IAU(33.33%) 미국 ETF 포트폴리오
- **2일차 주문 전략**: Day 1 (MoC 정수) + Day 2 (LIMIT 소수점)
- **IBKR CSV 주문지**: 바로 실행 가능한 표준 형식 주문서 생성
- **스마트 리밸런싱**: 현재 비중 vs 목표 비중 자동 계산 및 최적화

### ✅ **완전 자동화**
- **일일 스케줄링**: Singapore 시간대 기준 자동 실행
- **캐시 시스템**: 오프라인 작업을 위한 마켓 데이터 캐싱
- **통합 워크플로우**: 데이터 수집 → 분석 → 보고서 → 주문지까지 원스톱

## 🚀 **빠른 시작**

### 1. 설치
```bash
git clone https://github.com/my2582/simple-order-management-platform.git
cd simple-order-management-platform
pip install -r requirements.txt
```

### 2. IBKR 연결 설정
1. IB Gateway 또는 TWS 실행
2. API 설정에서 포트 활성화 (Paper: 4002, Live: 4001)
3. "Read-Only API" 옵션 활성화 (안전을 위해)

### 3. 첫 포지션 다운로드
```bash
# 모든 계좌 포지션 다운로드
./positions

# 특정 계좌만 다운로드
./positions --accounts DU123456
```

### 4. 모델 포트폴리오 확인
```bash
# 사용 가능한 모델 포트폴리오 목록
./model-portfolios

# GTAA 모델 상세 정보
python3 -m simple_order_management_platform.cli show-model-portfolio GTAA
```

## 📊 **포지션 다운로드 시스템**

### 🎯 **기본 사용법**

#### 📈 **실시간 포지션 다운로드**
```bash
# 전체 계좌 포지션 (실시간 가격)
./positions

# 특정 계좌만 선택
./positions --accounts DU123456,DU789012

# Paper Trading 계좌 (4002 포트)
./positions --port 4002

# Live Trading 계좌 (4001 포트)  
./positions --port 4001
```

#### ⚡ **캐시된 가격으로 빠른 조회**
```bash
# 캐시된 가격 사용 (30초 내 완료)
./positions-cached

# 특정 계좌만 빠른 조회
./positions-cached --accounts DU123456
```

### 📋 **출력 형식**

#### **Excel 파일 구조**
생성되는 Excel 파일 (`./data/output/portfolio_positions_YYYYMMDD_HHMMSS.xlsx`):

**Summary 시트**:
| Account | Net Liquidation Value | Securities Gross Position Value | Cash | % of Net Liq |
|---------|----------------------|--------------------------------|------|-------------|
| DU123456| SGD 150,250.00      | SGD 142,750.00                | SGD 7,500.00 | 95.01% / 4.99% |

**Matrix 시트**:
| Account_ID | Gross/NLV | Cash % | SPMO_Weight | SMH_Weight | IAU_Weight | 
|------------|-----------|--------|-------------|------------|------------|
| DU123456   | 95.01%    | 4.99%  | 33.5%       | 33.2%      | 33.3%      |

#### **콘솔 출력 예시**
```
📊 Starting IBKR standard portfolio positions download
✅ Connected to IBKR (Port: 4002, Client ID: 1)
📈 Found 2 managed accounts: ['DU123456', 'DU789012']

Account: DU123456
├─ Total Value: SGD 150,250.00
├─ Active Positions: 3
├─ SPMO: 150 shares (SGD 50,325.00)
├─ SMH: 200 shares (SGD 50,200.00) 
├─ IAU: 1,500 shares (SGD 42,225.00)
└─ Cash: SGD 7,500.00

💾 Excel saved: ./data/output/portfolio_positions_20250908_143022.xlsx
```

### 🔄 **마켓 데이터 관리**

#### **가격 데이터 업데이트**
```bash
# 일반 업데이트 (24시간 이내면 스킵)
./update-market-data

# 강제 업데이트 (최신 가격 필수)
./update-market-data --force

# 캐시 상태 확인
./market-data-status
```

#### **캐시 상태 확인 결과**
```
📊 Market Data Cache Status
Current time (SGT): 2025-09-08 14:30:45 +08
Cache Status: ✅ FRESH (Age: 2.3 hours)
Last Updated: 2025-09-08 12:15:22 +08  
Cached Symbols: 450+ symbols
```

## ⚖️ **모델 포트폴리오 리밸런싱**

### 🎯 **GTAA 모델 포트폴리오**

#### **포트폴리오 구성**
| 종목 | 비중 | 설명 |
|------|------|------|
| **SPMO** | 33.34% | Invesco S&P 500 Momentum ETF |
| **SMH** | 33.33% | VanEck Semiconductor ETF |
| **IAU** | 33.33% | iShares Gold Trust |

```bash
# GTAA 모델 상세 정보 보기
python3 -m simple_order_management_platform.cli show-model-portfolio GTAA
```

### 🔧 **계정 설정 및 할당**

#### **계정을 모델 포트폴리오에 할당**
```bash
# 수동 할당
python3 -m simple_order_management_platform.cli assign-account DU123456 GTAA

# 또는 헬퍼 스크립트 사용 (여러 계정 한 번에)
python3 scripts/setup_gtaa_accounts.py DU123456 DU789012 DU345678
```

### 📊 **리밸런싱 분석**

#### **현재 포트폴리오와 목표 비중 비교**
```bash
# 전체 계좌 리밸런싱 분석
./rebalance

# 특정 계좌만 분석
./rebalance --accounts DU123456

# 특정 모델 포트폴리오로 분석
./rebalance --model-portfolio GTAA
```

#### **분석 결과 예시**
```
⚖️ Calculating Rebalancing Requirements

Account: DU123456
Model Portfolio: GTAA
Total Value: SGD 150,250.00

┌────────┬──────────────┬──────────────┬────────────┬────────────┬─────────────────┐
│ Symbol │ Current Wt.  │ Target Wt.   │ Difference │ Current    │ Required Action │
│        │              │              │            │ Shares     │                 │
├────────┼──────────────┼──────────────┼────────────┼────────────┼─────────────────┤
│ SPMO   │ 33.50%       │ 33.34%       │ +0.16%     │ 150.00     │ -1.20           │
│ SMH    │ 33.21%       │ 33.33%       │ -0.12%     │ 200.00     │ +1.85           │  
│ IAU    │ 33.29%       │ 33.33%       │ -0.04%     │ 1,500.00   │ +15.30          │
└────────┴──────────────┴──────────────┴────────────┴────────────┴─────────────────┘

📈 Rebalancing recommended
```

### 📋 **주문지 생성**

#### **IBKR 호환 CSV 주문지 생성**
```bash
# 전체 주문지 (Day 1 + Day 2)
./generate-orders orders.csv

# Day 1만 (MoC 정수 주문)
./generate-orders day1_orders.csv --day 1

# Day 2만 (LIMIT 소수점 주문)
./generate-orders day2_orders.csv --day 2

# 특정 계좌만
./generate-orders orders.csv --accounts DU123456
```

#### **생성된 IBKR CSV 형식**
```csv
Action,Quantity,Symbol,SecType,Exchange,Currency,TimeInForce,OrderType,LmtPrice,BasketTag,Account,UsePriceMgmtAlgo,OrderRef
SELL,1,SPMO,STK,SMART,USD,DAY,MOC,,EX_20250908_1,DU123456,TRUE,
BUY,1,SMH,STK,SMART,USD,DAY,MOC,,EX_20250908_1,DU123456,TRUE,
BUY,15,IAU,STK,SMART,USD,DAY,MOC,,EX_20250908_1,DU123456,TRUE,
```

### 🎯 **2일차 주문 전략**

#### **Day 1 주문 (Market on Close)**
- **대상**: 5% 이상 비중 종목 중 최소 비중 종목 제외
- **주문 타입**: MOC (Market on Close)
- **수량**: 정수 단위만 (fractional shares 불가)
- **목적**: 주요 포지션 조정

#### **Day 2 주문 (Limit)**
- **대상**: 잔여 모든 종목 (소수점 조정 포함)
- **주문 타입**: LIMIT 
- **수량**: 소수점 단위까지 정확한 조정
- **목적**: 정밀한 비중 맞추기

## 🛠️ **일반적인 사용법**

### 📈 **일일 워크플로우**

#### 🌅 **매일 아침 (업무 시작)**
```bash
# 1. 시스템 상태 확인
./test-integrations

# 2. 마켓 데이터 업데이트
./update-market-data

# 3. 전체 포지션 다운로드
./positions

# ✅ 결과: 최신 데이터 포트폴리오 보고서 완성
```

#### 📊 **완전 자동화 실행**
```bash
# 원클릭 전체 업데이트 (마켓데이터 + 포지션)
./run-daily-update

# 이 명령어는 자동 실행:
# 1️⃣ 마켓 데이터 업데이트
# 2️⃣ 전체 계좌 포지션 다운로드
# 3️⃣ Excel 보고서 생성
# 4️⃣ SharePoint 업로드 (설정된 경우)
# 5️⃣ 이메일 발송 (설정된 경우)
```

### 🕒 **자동 스케줄링**

#### **Singapore 시간대 자동화**
```bash
# 스케줄러 시작
./start-scheduler

# 스케줄러 상태 확인
./scheduler-status

# 기본 스케줄:
# • 06:00 SGT: 마켓 데이터 업데이트
# • 06:30 SGT: 포트폴리오 위치 다운로드
```

## 💡 **실무 시나리오**

### 🎯 **시나리오 1: 고객 포트폴리오 현황 문의**
```bash
# 빠른 확인 (캐시 사용, ~30초)
./positions-cached --accounts DU123456

# 정확한 확인 (실시간, ~3분)
./positions --accounts DU123456
```

### 💰 **시나리오 2: 고객 신규 투자 (입금)**
```bash
# 1. 계좌를 GTAA 모델에 할당
python3 -m simple_order_management_platform.cli assign-account DU123456 GTAA

# 2. 리밸런싱 필요도 확인
./rebalance --accounts DU123456

# 3. 주문서 생성
./generate-orders new_investment_orders.csv --accounts DU123456
```

### ⚖️ **시나리오 3: 정기 리밸런싱**
```bash
# 1. 전체 계좌 리밸런싱 분석
./rebalance

# 2. Day 1 주문서 생성 (MoC)
./generate-orders day1_rebalance.csv --day 1

# 3. (다음날) Day 2 주문서 생성 (LIMIT)
./generate-orders day2_rebalance.csv --day 2
```

### 📱 **시나리오 4: 고객 출금 요청**
```bash
# 현재 포지션 확인
./positions --accounts DU123456

# 출금용 주문서는 현재 GTAA 모델로 비례 매도
# (향후 withdrawal 타입 추가 예정)
```

### 📞 **시나리오 5: 월말 보고서 작성**
```bash
# 1. 최신 가격으로 강제 업데이트
./update-market-data --force

# 2. 전체 계좌 포지션 다운로드
./positions

# 3. 파일 위치 확인
ls -la ./data/output/portfolio_positions_*.xlsx
```

## 🔧 **고급 기능**

### 🔗 **IBKR 연결 옵션**

#### **다중 포트 지원**
```bash
# Paper Trading (기본)
./positions --port 4002

# Live Trading
./positions --port 4001  

# TWS (Trader Workstation)
./positions --port 7497

# 자동 포트 탐지 (권장)
./positions  # 4001→4002→7497→7496 순서로 시도
```

#### **연결 테스트**
```bash
# IBKR 연결 상태 확인
./test-connection

# 특정 포트 테스트
./test-connection --port 4001

# 전체 시스템 통합 테스트
./test-integrations
```

### ⚙️ **설정 및 커스터마이징**

#### **모델 포트폴리오 추가/수정**
```yaml
# src/simple_order_management_platform/config/model_portfolios.yaml
model_portfolios:
  CUSTOM:
    name: "Custom Strategy"
    description: "My custom portfolio"
    holdings:
      - symbol: "VTI"
        target_weight: 0.6000  # 60%
        security_type: "STK"
      - symbol: "VXUS"  
        target_weight: 0.4000  # 40%
        security_type: "STK"
```

#### **계좌 매핑 설정**
```yaml
# config/model_portfolios.yaml
account_mappings:
  "DU123456": "GTAA"
  "DU789012": "GTAA" 
  "DU345678": "CUSTOM"
```

### 📊 **데이터 및 로깅**

#### **파일 저장 위치**
```
./data/
├── output/                              # 생성된 보고서
│   ├── portfolio_positions_20250908_143022.xlsx
│   └── orders_20250908_143530.csv
├── market_data_cache/                   # 마켓 데이터 캐시
│   ├── prices_20250908.json
│   └── cache_metadata.json
└── logs/                               # 로그 파일
    ├── scheduler_daemon.log
    └── application.log
```

#### **실행 시간 가이드**
| 작업 | 소요 시간 | 설명 |
|------|-----------|------|
| `./positions-cached` | ~30초 | 캐시된 가격 사용 |
| `./positions` (1계좌) | ~2분 | 실시간 가격, 단일 계좌 |
| `./positions` (3계좌) | ~5분 | 실시간 가격, 다중 계좌 |
| `./update-market-data` | ~3분 | 450+ 종목 가격 업데이트 |
| `./rebalance` | ~1분 | 리밸런싱 계산 |
| `./generate-orders` | ~30초 | IBKR CSV 생성 |
| `./run-daily-update` | ~10분 | 완전한 워크플로우 |

### 🆘 **문제 해결**

#### **일반적인 오류**

**1. IBKR 연결 실패**
```bash
# 포트 확인
./test-connection --port 4002

# IB Gateway 재시작 후 재시도
./positions --port 4002
```

**2. 마켓 데이터 오래됨**
```bash
# 캐시 상태 확인
./market-data-status

# 강제 업데이트
./update-market-data --force
```

**3. 계좌 매핑 오류**
```bash
# 계좌 수동 할당
python3 -m simple_order_management_platform.cli assign-account DU123456 GTAA

# 또는 config 파일 직접 수정
nano src/simple_order_management_platform/config/model_portfolios.yaml
```

#### **도움말 및 지원**
```bash
# 전체 명령어 목록
./simple-order-help

# 특정 명령어 도움말
./positions --help
./rebalance --help
./generate-orders --help

# 자세한 로그와 함께 실행
python3 -m simple_order_management_platform.cli download-positions-ibkr --verbose
```

## 🎯 **시스템 특징**

### ✅ **Production-Ready**
- **무인 자동화**: 24/7 스케줄링 지원
- **견고한 에러 처리**: 연결 실패 시 자동 재시도
- **캐시 기반**: 네트워크 의존성 최소화
- **Unix 철학**: 각 도구는 한 가지 일을 완벽하게

### ✅ **IBKR 표준 준수**
- **ib-insync 기반**: 안정적인 IBKR API 연동
- **SGD 기준 통화**: 모든 계산 결과 일관성
- **표준 용어**: Net Liquidation Value, Securities Gross Position Value
- **CSV 호환**: IBKR에서 바로 실행 가능한 주문 형식

### ✅ **사용자 친화적**
- **직관적 명령어**: `./positions`, `./rebalance`, `./generate-orders`
- **실시간 피드백**: 진행 상황 실시간 표시
- **풍부한 출력**: 콘솔 + Excel + CSV 다중 형식
- **유연한 옵션**: 계좌별, 포트별, 모델별 세밀한 제어

## 📚 **추가 문서**

- **[CLI 명령어 상세 가이드](docs/cli-reference.md)**
- **[IBKR 연결 설정 방법](docs/ibkr-setup.md)**  
- **[자동화 스케줄러 가이드](docs/SCHEDULER_GUIDE.md)**
- **[모델 포트폴리오 정의](docs/model-portfolios.md)**

## 🤝 **기여 및 지원**

- **Issues**: GitHub Issues를 통한 버그 리포트
- **Pull Requests**: 기능 개선 및 버그 수정 환영
- **Documentation**: 문서 개선 제안

---

## 🎉 **최신 업데이트 (2025-09-08)**

### 🚀 **v3.0 - 모델 포트폴리오 리밸런싱 시스템**
- ✅ **GTAA 모델 포트폴리오**: SPMO + SMH + IAU 균등 비중 전략
- ✅ **2일차 주문 전략**: Day 1 MoC + Day 2 LIMIT 최적화
- ✅ **IBKR CSV 주문지**: 표준 형식 자동 생성
- ✅ **스마트 리밸런싱**: 현재 vs 목표 비중 자동 계산
- ✅ **다중 계좌 지원**: 여러 계좌 통합 리밸런싱
- ✅ **Unix 철학**: 간단하고 강력한 도구들

**개발자 노트**: 실제 포트폴리오 매니저를 위한 완전한 리밸런싱 워크플로우를 구현했습니다. 이제 포지션 분석부터 IBKR 주문 실행까지 완전히 자동화된 프로세스를 제공합니다.
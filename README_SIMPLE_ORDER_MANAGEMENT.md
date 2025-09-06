# Simple Order Management Platform

리눅스의 "1개의 일을 정말 잘하자"는 철학을 적용한 Simple Order Management Platform입니다. IBKR(Interactive Brokers) 계좌를 통해 포트폴리오 모니터링과 주문 관리를 효율적으로 수행할 수 있습니다.

## 🎯 주요 기능

### 1. 계좌별 포지션 다운로드
- **매일 간단한 명령어로 모든 계좌의 포지션을 엑셀로 다운로드**
- 종목별 금액과 비중 자동 계산
- 현금 비중(%) 표시
- 계좌별 상세 정보와 요약 제공

### 2. 모델 포트폴리오 기반 주문지 생성
- **GTAA 전략 등 모델 포트폴리오 기반 자동 주문지 생성**
- 입금/출금/리밸런싱 시나리오 지원
- CSV 형식의 주문지로 바로 실행 가능

### 3. 단순하고 직관적인 CLI 인터페이스
- 리눅스 철학에 따른 단순한 명령어 체계
- 각 기능은 독립적으로 완벽하게 동작

## 📋 전제 조건

1. **IBKR IB Gateway 실행 중**
2. **ib_insync 패키지 사용** (IBKR API wrapper)
3. **Python 3.9+ 환경**

## 🚀 설치 및 설정

```bash
# 1. 패키지 설치
cd /home/user/webapp
pip install -e .

# 2. IB Gateway 설정 확인
# config/app.yaml 파일에서 IBKR 연결 설정 확인
```

## 💼 사용 방법

### 1. 계좌별 포지션 다운로드

**모든 계좌의 포지션을 엑셀로 다운로드:**
```bash
simple-order download-positions
```

**특정 계좌만 다운로드:**
```bash
simple-order download-positions --accounts DU123456,DU789012
```

**출력 파일명 지정:**
```bash
simple-order download-positions --output "daily_positions_20250906.xlsx"
```

### 2. 모델 포트폴리오 확인

**사용 가능한 모델 포트폴리오 목록 확인:**
```bash
simple-order list-portfolios
```

현재 지원하는 포트폴리오:
- **B301**: Future Fund - GTAA (SPMO, SMH, IAU 동일 비중)
- B101: Peace of Mind
- B201: Income Builder - 1
- B202: Income Builder - 2

### 3. 주문지 생성

#### 📈 입금 주문지 (새 자금 투자)
```bash
# GTAA 전략으로 $10,000 신규 투자
simple-order generate-orders DU123456 B301 --type deposit --amount 10000
```

#### ⚖️ 리밸런싱 주문지
```bash
# 현재 포지션을 GTAA 모델에 맞게 $50,000 규모로 리밸런싱
simple-order generate-orders DU123456 B301 --type rebalance --amount 50000 --min-trade 100
```

#### 📉 출금 주문지
```bash
# $5,000 출금 (비례 매도)
simple-order generate-orders DU123456 B301 --type withdrawal --amount 5000 --proportional

# 큰 포지션부터 우선 매도
simple-order generate-orders DU123456 B301 --type withdrawal --amount 5000 --largest-first
```

### 4. 고급 옵션

**IB 연결 설정 오버라이드:**
```bash
simple-order download-positions --ib-host 127.0.0.1 --ib-port 4002 --ib-client-id 2
```

**모델 포트폴리오 파일 경로 지정:**
```bash
simple-order generate-orders DU123456 B301 --type deposit --amount 10000 --mp-path ./custom/MP_Master.csv
```

## 📊 출력 파일

### 포지션 엑셀 파일 구조
- **Summary 시트**: 전체 계좌 요약
- **Account_[계좌번호] 시트**: 각 계좌별 상세 포지션
  - 종목별 시장가, 비중, 손익 정보
  - 현금 비중 및 총 포트폴리오 가치

### 주문지 CSV 파일 구조
```csv
Account_ID,Symbol,Action,Quantity,Amount,Order_Type,Notes,Timestamp
DU123456,SPMO,BUY,,3334.0,MKT,New deposit allocation to B301 (33.34% target weight),2025-09-06 11:41:18
DU123456,SMH,BUY,,3333.0,MKT,New deposit allocation to B301 (33.33% target weight),2025-09-06 11:41:18
DU123456,IAU,BUY,,3333.0,MKT,New deposit allocation to B301 (33.33% target weight),2025-09-06 11:41:18
```

## 🛠️ 모델 포트폴리오 관리

**MP_Master.csv 파일 구조:**
```csv
Portfolio ID,Bucket Name,ISIN,Ticker,Weight,Effective Date
B301,Future Fund - GTAA,,SPMO,33.34,18/07/25
B301,Future Fund - GTAA,,SMH,33.33,18/07/25
B301,Future Fund - GTAA,,IAU,33.33,18/07/25
```

새로운 전략 추가 시 이 파일을 수정하면 됩니다.

## ⚡ 일일 워크플로우 예시

```bash
# 1. 아침: 모든 계좌 포지션 확인
simple-order download-positions --output "positions_$(date +%Y%m%d).xlsx"

# 2. 고객 입금 시: 즉시 주문지 생성
simple-order generate-orders DU123456 B301 --type deposit --amount 25000

# 3. 월말 리밸런싱: 목표 금액으로 리밸런싱
simple-order generate-orders DU123456 B301 --type rebalance --amount 100000

# 4. 출금 요청 시: 출금 주문지 생성
simple-order generate-orders DU123456 B301 --type withdrawal --amount 15000
```

## 🔧 문제 해결

### IBKR 연결 테스트
```bash
simple-order test-connection
```

### 로깅 확인
- 모든 작업은 로그로 기록됩니다
- 오류 발생 시 상세한 오류 메시지 제공

### 일반적인 문제
1. **IB Gateway 연결 실패**: IB Gateway가 실행 중이고 포트 설정이 맞는지 확인
2. **계좌 접근 권한**: 관리 계좌 권한이 설정되어 있는지 확인
3. **최소 거래 금액**: 리밸런싱 시 `--min-trade` 옵션으로 조정

## 🎯 철학과 설계

이 플랫폼은 **리눅스의 "1개의 일을 정말 잘하자"** 철학을 따릅니다:

- **각 명령어는 하나의 작업만 완벽하게 수행**
- **단순하고 직관적인 인터페이스**
- **조합 가능한 기능들**
- **예측 가능한 출력 형식**

복잡한 포트폴리오 관리 시스템 대신, 매일 필요한 핵심 기능들을 단순하고 안정적으로 제공하여 실제 업무에서 바로 사용할 수 있도록 설계되었습니다.

---

**개발자**: 포트폴리오 매니저의 실제 니즈를 반영한 실용적인 도구
**업데이트**: 2025-09-06
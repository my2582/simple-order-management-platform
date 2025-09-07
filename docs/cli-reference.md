# CLI Command Reference 📋

완전한 CLI 명령어 레퍼런스 가이드입니다.

## 기본 사용법

```bash
simple-order [OPTIONS] COMMAND [ARGS]...
```

### 글로벌 옵션
- `--help`: 도움말 표시
- `--install-completion`: Shell completion 설치
- `--show-completion`: Shell completion 스크립트 표시

## 📊 포트폴리오 관리 명령어

### `positions`
모든 또는 특정 계좌의 포지션을 Excel 파일로 다운로드합니다.

```bash
simple-order positions [OPTIONS]
```

#### 옵션
- `-a, --accounts TEXT`: 특정 계좌 ID들 (쉼표로 구분)
- `-o, --output TEXT`: 출력 Excel 파일명 (기본값: 타임스탬프 자동 생성)
- `--ib-host TEXT`: IB 호스트 주소 오버라이드 (기본값: 127.0.0.1)
- `--ib-port INTEGER`: IB 포트 오버라이드 (기본값: 4002)
- `--ib-client-id INTEGER`: IB 클라이언트 ID 오버라이드 (기본값: 1)

#### 사용 예시
```bash
# 모든 계좌 다운로드
simple-order positions

# 특정 계좌들만 다운로드
simple-order positions -a "DU123456,DU789012"

# 파일명 지정
simple-order positions -o "daily_positions_20250906.xlsx"

# IB 연결 설정 변경
simple-order positions --ib-host 192.168.1.100 --ib-port 4003
```

#### 출력 파일 구조
**Portfolio_Matrix Sheet**:
- Account_ID: 계좌 식별자
- Net_Liquidation_Value: 순청산가치 (IBKR 표준)
- Risk_Asset_Pct: 위험자산 비중 (%)
- Cash_Pct: 현금 비중 (%)
- Cash_Base_Currency: 기준통화 현금
- Cash_Local_Currency: 현지통화 현금
- [Symbol]_Weight: 각 종목별 포지션 비중 (%)

**Summary Sheet**:
- 전체 계좌 요약 정보
- 계좌별 상세 통계

## ⚖️ 주문 생성 명령어

### `generate-orders`
모델 포트폴리오 기반으로 주문지를 생성합니다.

```bash
simple-order generate-orders ACCOUNT_ID PORTFOLIO_ID [OPTIONS]
```

#### 필수 인자
- `ACCOUNT_ID`: 대상 계좌 ID (예: DU123456)
- `PORTFOLIO_ID`: 모델 포트폴리오 ID (예: B301)

#### 옵션
- `--type [deposit|withdrawal|rebalance]`: 주문 유형 (**필수**)
- `--amount FLOAT`: 거래 금액 (**필수**)
- `--proportional`: 출금 시 비례 매도 (기본값)
- `--largest-first`: 출금 시 큰 포지션부터 매도
- `--min-trade FLOAT`: 최소 거래 금액 (기본값: 50)
- `--mp-path TEXT`: 모델 포트폴리오 파일 경로 오버라이드
- `-o, --output TEXT`: 출력 CSV 파일명
- `--ib-host TEXT`: IB 호스트 오버라이드
- `--ib-port INTEGER`: IB 포트 오버라이드
- `--ib-client-id INTEGER`: IB 클라이언트 ID 오버라이드

### 주문 유형별 사용법

#### 1. 입금 주문지 (deposit)
새로운 자금을 모델 포트폴리오에 맞게 투자하는 주문지를 생성합니다.

```bash
# GTAA 전략으로 $10,000 신규 투자
simple-order generate-orders DU123456 B301 --type deposit --amount 10000

# 출력 파일명 지정
simple-order generate-orders DU123456 B301 --type deposit --amount 25000 -o "deposit_order_20250906.csv"
```

**출력 예시**:
```csv
Account_ID,Symbol,Action,Quantity,Amount,Order_Type,Notes,Timestamp
DU123456,SPMO,BUY,,3334.0,MKT,New deposit allocation to B301 (33.34% target weight),2025-09-06 11:41:18
DU123456,SMH,BUY,,3333.0,MKT,New deposit allocation to B301 (33.33% target weight),2025-09-06 11:41:18
DU123456,IAU,BUY,,3333.0,MKT,New deposit allocation to B301 (33.33% target weight),2025-09-06 11:41:18
```

#### 2. 리밸런싱 주문지 (rebalance)
현재 포지션을 목표 포트폴리오로 조정하는 주문지를 생성합니다.

```bash
# 현재 포지션을 $50,000 규모의 GTAA로 리밸런싱
simple-order generate-orders DU123456 B301 --type rebalance --amount 50000

# 최소 거래 금액 설정
simple-order generate-orders DU123456 B301 --type rebalance --amount 100000 --min-trade 100
```

**특징**:
- 현재 포지션과 목표 포지션을 비교
- `--min-trade` 미만의 거래는 제외
- 매수와 매도 주문이 모두 포함될 수 있음

#### 3. 출금 주문지 (withdrawal)
포지션을 매도하여 현금을 확보하는 주문지를 생성합니다.

```bash
# $5,000 비례 매도 (기본값)
simple-order generate-orders DU123456 B301 --type withdrawal --amount 5000 --proportional

# 큰 포지션부터 우선 매도
simple-order generate-orders DU123456 B301 --type withdrawal --amount 8000 --largest-first
```

**매도 전략**:
- `--proportional`: 모든 포지션을 비례적으로 매도
- `--largest-first`: 큰 포지션부터 우선 매도

## 📋 정보 조회 명령어

### `test-connection`
IBKR TWS/Gateway 연결 상태를 테스트합니다.

```bash
simple-order test-connection [OPTIONS]
```

#### 옵션
- `--ib-host TEXT`: IB 호스트 오버라이드
- `--ib-port INTEGER`: IB 포트 오버라이드
- `--ib-client-id INTEGER`: IB 클라이언트 ID 오버라이드

#### 사용 예시
```bash
# 기본 설정으로 연결 테스트
simple-order test-connection

# 다른 포트로 테스트
simple-order test-connection --ib-port 4003
```

### `list-portfolios`
사용 가능한 모델 포트폴리오 목록을 표시합니다.

```bash
simple-order list-portfolios [OPTIONS]
```

#### 옵션
- `--mp-path TEXT`: 모델 포트폴리오 파일 경로 오버라이드

#### 사용 예시
```bash
# 기본 모델 포트폴리오 목록
simple-order list-portfolios

# 커스텀 파일 경로
simple-order list-portfolios --mp-path "./custom/MP_Master.csv"
```

### `list-strategies`
사용 가능한 전략 목록을 표시합니다.

```bash
simple-order list-strategies
```

### `list-master`
마스터 유니버스 데이터 상태를 표시합니다.

```bash
simple-order list-master
```

## 🔧 고급 사용법

### IB 연결 설정 오버라이드
모든 명령어에서 IB 연결 설정을 임시로 변경할 수 있습니다:

```bash
# Paper Trading 계정 (포트 4002)
simple-order positions --ib-port 4002

# Live Trading 계정 (포트 7497)
simple-order positions --ib-port 7497

# 다른 서버의 IB Gateway
simple-order positions --ib-host 192.168.1.100 --ib-port 4002 --ib-client-id 2
```

### 배치 처리 예시
쉘 스크립트와 조합하여 배치 처리가 가능합니다:

```bash
#!/bin/bash
# daily_portfolio_check.sh

DATE=$(date +%Y%m%d)
ACCOUNTS=("DU123456" "DU789012" "DU345678")

# 모든 계좌 포지션 다운로드
simple-order positions -o "all_positions_${DATE}.xlsx"

# 각 계좌별 개별 다운로드
for account in "${ACCOUNTS[@]}"; do
    simple-order positions -a "$account" -o "positions_${account}_${DATE}.xlsx"
done

echo "Daily portfolio check completed for $DATE"
```

### 파이프라인 사용
Unix 파이프라인과 조합하여 사용할 수 있습니다:

```bash
# 생성된 CSV 파일 내용 확인
simple-order generate-orders DU123456 B301 --type deposit --amount 10000 | head -5

# 특정 조건 필터링 (예: SMH 종목만)
simple-order generate-orders DU123456 B301 --type rebalance --amount 50000 | grep SMH
```

## ❗ 오류 처리

### 일반적인 오류와 해결책

**1. Connection Error**
```
Error: Could not connect to IB Gateway
```
- IB Gateway/TWS가 실행 중인지 확인
- API 설정이 활성화되어 있는지 확인
- 포트 번호가 올바른지 확인

**2. Account Access Error**
```
Error: No access to account DU123456
```
- 계좌 번호가 올바른지 확인
- 관리 계좌 권한이 설정되어 있는지 확인

**3. Portfolio Not Found**
```
Error: Portfolio B301 not found
```
- `simple-order list-portfolios`로 사용 가능한 포트폴리오 확인
- MP_Master.csv 파일이 존재하는지 확인

**4. Insufficient Data**
```
Error: No positions found for account
```
- 계좌에 포지션이 있는지 확인
- IB Gateway에서 계좌가 올바르게 연결되어 있는지 확인

## 🚀 성능 최적화

### 팁과 권장사항

1. **배치 처리**: 여러 계좌를 한 번에 처리하는 것이 효율적
2. **캐싱**: 동일한 데이터를 반복 요청하지 않도록 주의
3. **최소 거래 금액**: 리밸런싱 시 `--min-trade` 옵션으로 불필요한 소액 거래 제거
4. **파일명 규칙**: 날짜와 시간을 포함한 일관된 파일명 사용

### 권장 워크플로우
```bash
# 1. 연결 확인
simple-order test-connection

# 2. 포지션 확인
simple-order positions -o "morning_check_$(date +%Y%m%d).xlsx"

# 3. 필요한 주문지 생성
simple-order generate-orders ACCOUNT PORTFOLIO --type TYPE --amount AMOUNT

# 4. 결과 검토 후 실행
```

이 레퍼런스를 통해 모든 CLI 명령어를 효과적으로 활용할 수 있습니다.
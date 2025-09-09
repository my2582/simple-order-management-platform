# Daily Workflow Guide 💼

포트폴리오 매니저를 위한 일일 업무 워크플로우 가이드입니다.

## ⏰ 시간대별 워크플로우

### 🌅 시장 개장 전 (08:00-09:30 EST)

#### 1. 시스템 상태 점검
```bash
# IB Gateway 연결 확인
simple-order test-connection

# 성공 시 출력:
# ✅ IB Connection Test Successful
# 📊 Connected to IB Gateway
# 🏢 Account: DU123456
```

#### 2. 일일 포지션 다운로드
```bash
# 모든 계좌의 포지션을 통합 매트릭스로 다운로드
simple-order positions --output "daily_positions_$(date +%Y%m%d).xlsx"

# 특정 계좌만 확인이 필요한 경우
simple-order positions --accounts "DU123456,DU789012" --output "priority_accounts_$(date +%Y%m%d).xlsx"
```

#### 3. 포지션 분석
Excel 파일을 열어 다음 사항 확인:

**Portfolio_Matrix Sheet 체크리스트**:
- ✅ **Net Liquidation Value**: 예상 범위 내 변동인가?
- ✅ **Risk Asset Pct**: 목표 범위 (예: 80-95%) 내에 있는가?
- ✅ **Cash Pct**: 적정 현금 비중 (예: 5-20%) 유지 중인가?
- ✅ **Position Weights**: 각 종목이 목표 비중 ±5% 내에 있는가?

**이상 징후 감지**:
- 🚨 Net Liquidation Value 급격한 변동 (±10% 이상)
- 🚨 개별 종목 비중이 목표에서 크게 벗어남 (±10% 이상)
- 🚨 현금 비중이 과도하게 높거나 낮음

### 📈 시장 개장 중 (09:30-16:00 EST)

#### 1. 고객 요청 처리

##### 신규 입금 처리
```bash
# 고객이 $25,000를 GTAA 전략으로 신규 투자
simple-order generate-orders DU123456 B301 --type deposit --amount 25000 --output "deposit_DU123456_$(date +%Y%m%d_%H%M).csv"

# 생성된 주문지 확인
cat data/output/deposit_DU123456_*.csv
```

**주문지 검토 포인트**:
- ✅ 각 종목별 할당 금액이 목표 비중과 일치하는가?
- ✅ 총 주문 금액이 입금액과 일치하는가?
- ✅ 모든 종목이 매수(BUY) 주문인가?

##### 출금 요청 처리
```bash
# $15,000 출금 - 비례 매도 방식 (기본)
simple-order generate-orders DU123456 B301 --type withdrawal --amount 15000 --proportional --output "withdrawal_DU123456_$(date +%Y%m%d_%H%M).csv"

# 또는 큰 포지션부터 우선 매도
simple-order generate-orders DU123456 B301 --type withdrawal --amount 15000 --largest-first --output "withdrawal_priority_DU123456_$(date +%Y%m%d_%H%M).csv"
```

##### 리밸런싱 요청 처리
```bash
# 현재 포지션을 $100,000 규모로 리밸런싱
simple-order generate-orders DU123456 B301 --type rebalance --amount 100000 --min-trade 100 --output "rebalance_DU123456_$(date +%Y%m%d_%H%M).csv"
```

**리밸런싱 주의사항**:
- 🎯 `--min-trade` 옵션으로 소액 거래 제외 (권장: $100-$500)
- 📊 매수와 매도가 동시에 발생할 수 있음
- ⏰ 시장 변동성이 높은 시간대 피하기

#### 2. 주문 실행 및 모니터링

##### 주문 전 최종 확인
```bash
# 주문지를 Excel이나 텍스트 에디터로 검토
cat data/output/order_file.csv | column -t -s','

# 주문 총액 계산 (간단한 체크)
awk -F',' 'NR>1 {sum+=$5} END {print "Total Order Amount: $" sum}' data/output/order_file.csv
```

##### 주문 실행 체크리스트
1. ✅ **시장 상황 확인**: 극심한 변동성은 없는가?
2. ✅ **계좌 잔고 확인**: 매수 주문 시 충분한 현금이 있는가?
3. ✅ **포지션 확인**: 매도 주문 시 충분한 포지션이 있는가?
4. ✅ **주문 유형**: MKT (시장가) vs LMT (지정가) 선택
5. ✅ **분할 실행**: 대량 주문 시 분할 실행 고려

#### 3. 실시간 모니터링

##### 실행된 주문 추적
```bash
# 주문 실행 후 포지션 재확인
simple-order positions --accounts DU123456 --output "post_order_check_$(date +%H%M).xlsx"
```

##### 예외 상황 대응
- 🚨 **부분 체결**: 미체결 수량에 대한 추가 조치
- 🚨 **주문 거부**: 거부 사유 확인 및 수정 주문
- 🚨 **시스템 오류**: 백업 시스템 또는 수동 주문 준비

### 🌆 시장 마감 후 (16:00-18:00 EST)

#### 1. 일일 정산 및 검토

##### 최종 포지션 확인
```bash
# 마감 후 최종 포지션 스냅샷
simple-order positions --output "eod_positions_$(date +%Y%m%d).xlsx"
```

##### 일일 성과 요약
**체크할 항목들**:
- 📊 각 계좌별 일일 손익
- 📈 포트폴리오 대비 벤치마크 성과
- 💰 현금 플로우 (입금/출금) 정확성
- ⚖️ 목표 비중 대비 현재 비중 편차

#### 2. 리포트 생성 및 파일 정리

##### 일일 리포트 디렉토리 정리
```bash
# 일일 파일들을 날짜별 폴더로 정리
DATE=$(date +%Y%m%d)
mkdir -p "data/daily_reports/$DATE"
mv data/output/*$DATE* "data/daily_reports/$DATE/"

# 주요 파일들 백업
cp "data/daily_reports/$DATE/daily_positions_$DATE.xlsx" "data/daily_reports/latest_positions.xlsx"
```

##### 성과 트래킹 업데이트
```bash
# 성과 데이터베이스 업데이트 (CSV 형태)
echo "$DATE,$(awk -F',' 'NR>1 {sum+=$3} END {print sum}' data/daily_reports/$DATE/eod_positions_$DATE.xlsx)" >> data/performance/daily_nav.csv
```

## 📅 주간/월간 워크플로우

### 🗓️ 주간 업무 (매주 금요일)

#### 1. 주간 성과 리뷰
```bash
# 주간 포지션 변화 분석
WEEK_START=$(date -d "last monday" +%Y%m%d)
WEEK_END=$(date +%Y%m%d)

# 주초 vs 주말 포지션 비교
echo "Week start: $WEEK_START"
echo "Week end: $WEEK_END"
ls data/daily_reports/$WEEK_START/
ls data/daily_reports/$WEEK_END/
```

#### 2. 리밸런싱 필요성 검토
```bash
# 각 포트폴리오별 목표 대비 편차 확인
simple-order list-portfolios

# 편차가 큰 계좌들 식별 (수동 분석)
simple-order positions --output "weekly_rebalance_check_$(date +%Y%m%d).xlsx"
```

#### 3. 리스크 관리 점검
- 📊 **개별 종목 집중도**: 단일 종목이 포트폴리오의 과도한 비중을 차지하지 않는가?
- 📈 **섹터 집중도**: 특정 섹터에 과도하게 집중되어 있지 않는가?
- 💹 **변동성 분석**: 최근 1주간 일일 변동성이 평소보다 높지 않은가?

### 📆 월간 업무 (매월 말일)

#### 1. 월간 리밸런싱
```bash
# 모든 계좌의 월말 리밸런싱 주문지 생성
ACCOUNTS=("DU123456" "DU789012" "DU345678")

for account in "${ACCOUNTS[@]}"; do
    echo "Generating monthly rebalance for $account"
    simple-order generate-orders "$account" B301 --type rebalance --amount 100000 --min-trade 200 --output "monthly_rebalance_${account}_$(date +%Y%m).csv"
done
```

#### 2. 월간 성과 리포트
```bash
# 월간 성과 데이터 수집
MONTH=$(date +%Y%m)
mkdir -p "data/monthly_reports/$MONTH"

# 월간 모든 일일 포지션 파일들을 월간 폴더로 복사
cp data/daily_reports/${MONTH}*/daily_positions_*.xlsx "data/monthly_reports/$MONTH/"

# 월말 최종 포지션
simple-order positions --output "data/monthly_reports/$MONTH/month_end_positions_$MONTH.xlsx"
```

#### 3. 모델 포트폴리오 검토
- 📊 **성과 분석**: 각 전략별 월간 수익률 계산
- 🎯 **벤치마크 비교**: 관련 지수 대비 성과 평가  
- 🔄 **전략 조정**: 필요시 모델 포트폴리오 비중 조정

## 🚨 예외 상황 대응 매뉴얼

### 시장 급락 상황 (-5% 이상)

#### 즉시 대응 (15분 내)
```bash
# 1. 모든 계좌 현황 파악
simple-order positions --output "crisis_positions_$(date +%Y%m%d_%H%M).xlsx"

# 2. 현금 포지션 확인
echo "Emergency cash check completed at $(date)"
```

#### 단기 대응 (1시간 내)
- 📞 **고객 커뮤니케이션**: 주요 고객들에게 상황 설명
- 🛑 **신규 주문 보류**: 시장 안정화까지 대기
- 📊 **손실 평가**: 포트폴리오별 손실 규모 파악

#### 중기 대응 (1-3일)
- 🎯 **기회 포착**: 저가 매수 기회 검토
- ⚖️ **리밸런싱**: 목표 비중 이탈 시 조정
- 📈 **전략 재검토**: 극한 상황에서의 전략 유효성 평가

### 시스템 장애 상황

#### IB Gateway 연결 장애
```bash
# 1. 연결 상태 진단
simple-order test-connection --ib-port 4002
simple-order test-connection --ib-port 7497

# 2. 대체 연결 시도
simple-order test-connection --ib-host backup_server_ip --ib-port 4002

# 3. 수동 백업 절차
echo "Switching to manual trading mode at $(date)" >> emergency.log
```

#### 네트워크 장애
- 📱 **모바일 백업**: IB Mobile App 사용
- ☎️ **전화 주문**: IB 고객센터 통화
- 💻 **백업 시스템**: 다른 위치의 백업 서버 사용

### 규제 및 컴플라이언스 상황

#### 투자 한도 위반 감지
```bash
# 포트폴리오 컴플라이언스 체크
awk -F',' '$5 > 50 {print "WARNING: " $4 " exceeds 50% limit: " $5 "%"}' data/model_portfolios/MP_Master.csv
```

#### 즉시 조치
1. 🛑 **관련 거래 중단**
2. 📋 **상황 문서화** 
3. 🏛️ **규제 보고** (필요시)
4. 🔄 **포지션 조정** (순서대로 처리)

## 🤖 자동화 및 효율성 개선

### Cron 작업 설정

#### 일일 자동화 스크립트
```bash
# crontab -e 에 추가

# 매일 오전 8시 30분: 일일 포지션 체크
30 8 * * 1-5 /usr/local/bin/simple-order positions --output "/home/user/daily_auto_$(date +\%Y\%m\%d).xlsx"

# 매일 오후 4시 30분: 마감 후 포지션 체크  
30 16 * * 1-5 /usr/local/bin/simple-order positions --output "/home/user/eod_auto_$(date +\%Y\%m\%d).xlsx"

# 매주 금요일 오후 5시: 주간 리포트
0 17 * * 5 /home/user/scripts/weekly_report.sh

# 매월 마지막 날: 월간 리밸런싱 체크
0 18 28-31 * * [ $(date -d tomorrow +\%d) -eq 1 ] && /home/user/scripts/monthly_rebalance.sh
```

### 배치 스크립트 예시

#### daily_routine.sh
```bash
#!/bin/bash
# daily_routine.sh - 일일 루틴 자동화

DATE=$(date +%Y%m%d)
LOG_FILE="logs/daily_routine_$DATE.log"

echo "Starting daily routine at $(date)" >> $LOG_FILE

# 1. 연결 테스트
if ! simple-order test-connection >> $LOG_FILE 2>&1; then
    echo "ERROR: IB connection failed" >> $LOG_FILE
    exit 1
fi

# 2. 포지션 다운로드
simple-order positions --output "daily_positions_$DATE.xlsx" >> $LOG_FILE 2>&1

# 3. 성과 기록
echo "$DATE,$(get_total_portfolio_value)" >> data/performance/daily_nav.csv

echo "Daily routine completed at $(date)" >> $LOG_FILE
```

### 알림 시스템

#### Slack/이메일 알림 설정
```bash
# 중요 이벤트 알림
send_alert() {
    local message=$1
    # Slack webhook 또는 이메일 전송
    curl -X POST -H 'Content-type: application/json' \
        --data "{\"text\":\"$message\"}" \
        $SLACK_WEBHOOK_URL
}

# 사용 예시
if [[ $portfolio_drop > 5 ]]; then
    send_alert "🚨 Portfolio down more than 5%: $portfolio_drop%"
fi
```

## 📊 성과 측정 및 개선

### KPI 추적

#### 일일 KPI
- 📈 **포트폴리오 수익률**: 일일, 월간, 연간
- 🎯 **추적 오차**: 목표 포트폴리오 대비 편차
- 💼 **거래 회전율**: 과도한 거래 방지
- 📞 **고객 만족도**: 요청 처리 시간

#### 주간 KPI  
- 🏆 **벤치마크 대비 성과**: 알파 생성 여부
- 📊 **리스크 조정 수익률**: 샤프 비율, 소르티노 비율
- 🔄 **리밸런싱 효과**: 리밸런싱으로 인한 수익 개선

### 지속적 개선

#### 프로세스 최적화
1. **병목 지점 식별**: 가장 시간이 많이 걸리는 작업
2. **자동화 확대**: 반복적인 작업의 자동화
3. **오류 감소**: 체크리스트와 검증 강화
4. **응답 시간 단축**: 고객 요청 처리 시간 개선

이 워크플로우를 통해 효율적이고 체계적인 포트폴리오 관리를 수행할 수 있습니다!
---
title: '[Kafka 기초] 컨슈머와 컨슈머 그룹: 리밸런스와 새 프로토콜(KIP-848)'
date: '2025-12-13T21:00:00+09:00'
categories:
- Kafka
tags:
- kafka
- consumer
- consumer-group
- rebalance
- kip-848
- group-protocol
- assignor
- lag
- share-group
- 프로듀서와 컨슈머
series:
- Kafka 기초
series_order: 7
---

컨슈머 그룹은 파티션을 그룹 안의 컨슈머들이 나눠 맡는 구조인데, 컨슈머가 들어오고 나갈 때마다 다시 나누는 리밸런스가 핵심이었다. 4.0에서 GA가 된 새 리밸런스 프로토콜도 직접 켜서 컨슈머 두 개로 확인했다.

## 요약

- 그룹 안에서 파티션 하나는 컨슈머 하나만 맡는다. 컨슈머가 파티션보다 많으면 남는 컨슈머는 논다.
- 컨슈머가 들어오거나 나가거나 죽으면 리밸런스가 일어나 파티션을 다시 나눈다.
- 예전(classic) 방식은 클라이언트 중 하나가 배정을 계산했고, 4.0에서 GA가 된 새 방식(consumer, KIP-848)은 브로커의 그룹 코디네이터가 계산해서 점진적으로 넘긴다.
- 클라이언트 기본값은 아직 group.protocol=classic이다. 새 방식을 쓰려면 group.protocol=consumer를 줘야 한다.
- kafka-groups.sh --list로 그룹마다 classic인지 consumer인지 바로 보인다.

## 1. 그룹과 파티션 배정

{{< mermaid >}}
flowchart LR
  subgraph topic["orders 토픽"]
    direction TB
    P0["파티션 0"]
    P1["파티션 1"]
    P2["파티션 2"]
  end
  subgraph g1["shipping 그룹"]
    direction TB
    C1["컨슈머 A"]
    C2["컨슈머 B"]
  end
  subgraph g2["analytics 그룹"]
    C3["컨슈머 C"]
  end
  P0 --> C1
  P1 --> C1
  P2 --> C2
  topic -.->|"세 파티션 모두"| C3
{{< /mermaid >}}

shipping 그룹은 파티션 세 개를 A와 B가 나눠 갖고, analytics 그룹은 C 혼자 셋을 다 읽는다. 두 그룹은 서로 상관없이 각자 오프셋을 관리한다.

## 2. 기본값 확인

```text
consumer auto.offset.reset = latest
consumer enable.auto.commit = true
consumer auto.commit.interval.ms = 5000
consumer session.timeout.ms = 45000
consumer heartbeat.interval.ms = 3000
consumer max.poll.records = 500
consumer max.poll.interval.ms = 300000
consumer group.protocol = classic
consumer partition.assignment.strategy = [RangeAssignor, CooperativeStickyAssignor]
```

4.1.0 클라이언트에서 직접 뽑은 값이다. 눈에 띈 건 두 가지다. auto.offset.reset이 latest라서 새 그룹이 처음 붙으면 과거 데이터는 건너뛰고 지금부터 읽는다(콘솔 컨슈머에 --from-beginning을 붙이는 이유). 그리고 group.protocol 기본값이 아직 classic이다.

| 설정 | 뜻 |
|---|---|
| session.timeout.ms | 이 시간 동안 하트비트가 없으면 죽은 것으로 보고 리밸런스 |
| max.poll.interval.ms | poll()과 poll() 사이가 이보다 길면(처리가 너무 느리면) 그룹에서 뺀다 |
| max.poll.records | poll() 한 번에 받아 오는 최대 레코드 수 |

## 3. 새 프로토콜로 컨슈머 두 개 붙여 보기

브로커 쪽은 이미 세 방식을 다 받는다.

```text
group.coordinator.rebalance.protocols=classic,consumer,streams
```

컨슈머 하나를 group.protocol=consumer로 띄우고 멤버를 봤다.

```bash
bin/kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic orders --group shipping \
  --consumer-property group.protocol=consumer
bin/kafka-consumer-groups.sh --bootstrap-server localhost:9092 --describe --group shipping --members
```

```text
GROUP           CONSUMER-ID            HOST            CLIENT-ID        #PARTITIONS     
shipping        vOB6bQ5ZTEGrQKp1MZrBmw /127.0.0.1      console-consumer 3               
```

같은 그룹으로 하나를 더 띄우고 바로 다시 봤다.

```text
Warning: Consumer group 'shipping' is rebalancing.

GROUP           CONSUMER-ID            HOST            CLIENT-ID        #PARTITIONS     
shipping        vOB6bQ5ZTEGrQKp1MZrBmw /127.0.0.1      console-consumer 2               
shipping        dB5yywSRQH2VO5Cujse_Yg /127.0.0.1      console-consumer 0               
```

리밸런스 중간에 찍힌 모습이다. 첫 번째 컨슈머가 파티션 하나를 내려놓아 2개가 됐는데, 새 컨슈머는 아직 0개다. 파티션별로 보면 내려놓은 2번 파티션의 주인이 비어 있다.

```text
GROUP           TOPIC           PARTITION  CURRENT-OFFSET  LOG-END-OFFSET  LAG             CONSUMER-ID
shipping        orders          0          0               0               0               vOB6bQ5ZTEGrQKp1MZrBmw
shipping        orders          1          2               2               0               vOB6bQ5ZTEGrQKp1MZrBmw
shipping        orders          2          6               6               0               -
```

예전 방식(eager)은 리밸런스 때 모든 컨슈머가 모든 파티션을 일단 내려놓았다가 다시 받았다. 새 방식은 옮겨야 하는 파티션만 내려놓고 넘긴다. 나머지 파티션은 리밸런스 중에도 계속 읽는다. 위 결과에서 0, 1번은 첫 컨슈머가 계속 잡고 있었다.

```bash
bin/kafka-groups.sh --bootstrap-server localhost:9092 --list
```

```text
GROUP                  TYPE      PROTOCOL 
shipping               Consumer  consumer 
console-consumer-56865 Classic   consumer 
billing                Classic   consumer 
```

TYPE이 Consumer면 새 프로토콜, Classic이면 예전 프로토콜 그룹이다.

| 비교 | classic | consumer(KIP-848) |
|---|---|---|
| 배정 계산 | 그룹 리더 컨슈머(클라이언트) | 브로커의 그룹 코디네이터 |
| 리밸런스 | 그룹 전체가 동기화 단계를 거침 | 멤버별로 점진적으로 |
| 배정 전략 설정 | partition.assignment.strategy(클라이언트) | group.remote.assignor(uniform, range) |
| 켜는 법 | 기본값 | group.protocol=consumer |

## 4. 컨슈머 수와 파티션 수

| 상황 | 결과 |
|---|---|
| 컨슈머 < 파티션 | 한 컨슈머가 여러 파티션을 맡는다 |
| 컨슈머 = 파티션 | 하나씩 맡는다. 가장 병렬성이 높다 |
| 컨슈머 > 파티션 | 남는 컨슈머는 아무것도 안 받는다 |

그래서 파티션 수가 컨슈머 그룹의 최대 병렬 처리 수가 된다.

## 5. Queues for Kafka 맛보기

4.1에는 공유 그룹(share group)이 미리보기로 들어왔다. 일반 그룹과 달리 파티션을 독점하지 않고 레코드 단위로 여러 컨슈머가 나눠 가져가며, 레코드마다 처리 완료를 따로 확인한다. 순서가 상관없는 작업 큐에 맞는 방식이다. 기능 버전 share.version이 0이라 지금은 꺼져 있고, kafka-console-share-consumer.sh 같은 도구는 이미 들어 있다.

> **쉬운 설명**
>
> 컨슈머 그룹은 식당 홀 직원들이고 파티션은 테이블이다. 테이블 하나는 직원 한 명이 맡는다. 직원이 새로 오면 테이블을 다시 나누는데(리밸런스), 예전 방식은 모든 직원이 일단 손을 놓고 매니저 한 명이 새 배치표를 짜는 동안 기다렸다. 새 방식은 점장(브로커)이 배치표를 짜고, 옮겨야 할 테이블만 넘기라고 한다. 나머지 테이블은 하던 대로 계속 서빙한다.

## 헷갈렸던 것들

- 같은 그룹 안에서는 파티션을 나눠 갖고, 다른 그룹끼리는 같은 데이터를 각자 다 읽는다.
- 새 그룹이 아무것도 못 읽는 것 같으면 auto.offset.reset=latest 때문인 경우가 많다.
- 새 프로토콜에서는 클라이언트의 partition.assignment.strategy 대신 group.remote.assignor를 쓴다.

## 용어 정리

| 용어 | 뜻 |
|---|---|
| 그룹 코디네이터 | 그룹 멤버십과 오프셋 커밋을 관리하는 브로커 쪽 역할 |
| 리밸런스 | 그룹 멤버가 바뀔 때 파티션 배정을 다시 하는 과정 |
| 랙(lag) | 로그 끝 오프셋과 그룹이 커밋한 오프셋의 차이. 밀린 양 |
| KIP-848 | 브로커가 배정을 계산하는 새 컨슈머 리밸런스 프로토콜 |
| 공유 그룹 | 레코드 단위로 나눠 처리하는 큐 방식 그룹(4.1 미리보기) |

## 복습 문제

**1.** 파티션 3개짜리 토픽을 같은 그룹의 컨슈머 4개가 읽으면 어떻게 되는가?

**2.** 그룹 shipping의 멤버별 파티션 개수를 보는 명령을 적어라.

**3.** 새 그룹으로 콘솔 컨슈머를 붙였는데 기존 데이터가 하나도 안 나온다. 이유와 해결 방법은?

## 답과 풀이

1. 컨슈머 3개가 파티션을 하나씩 맡고, 하나는 놀고 있다. 한 컨슈머가 빠지면 놀던 컨슈머가 이어받는다.

2. 

```bash
bin/kafka-consumer-groups.sh --bootstrap-server localhost:9092 --describe --group shipping --members
```

3. 새 그룹은 커밋된 오프셋이 없어서 auto.offset.reset을 따른다. 기본값 latest라 지금 이후 데이터만 읽는다. --from-beginning을 주거나 auto.offset.reset=earliest를 쓴다.

## 참고 자료

- Apache Kafka 문서, 컨슈머 리밸런스 프로토콜: <https://kafka.apache.org/41/operations/consumer-rebalance-protocol/>
- KIP-848, 차세대 컨슈머 리밸런스 프로토콜: <https://cwiki.apache.org/confluence/display/KAFKA/KIP-848%3A+The+Next+Generation+of+the+Consumer+Rebalance+Protocol>
- Apache Kafka 문서, 컨슈머 설정: <https://kafka.apache.org/41/configuration/consumer-configs/>
- KIP-932, Queues for Kafka: <https://cwiki.apache.org/confluence/display/KAFKA/KIP-932%3A+Queues+for+Kafka>

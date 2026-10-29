---
title: '[Kafka 기초] 오프셋 커밋과 전달 보장: at-most-once, at-least-once, exactly-once'
date: '2025-12-20T21:00:00+09:00'
categories:
- Kafka
tags:
- kafka
- offset-commit
- consumer-offsets
- auto-commit
- delivery-semantics
- idempotence
- transactions
- read-committed
- reset-offsets
- 프로듀서와 컨슈머
series:
- Kafka 기초
series_order: 8
---

컨슈머가 '어디까지 읽었다'를 어떻게 기록하는지(오프셋 커밋), 그리고 그 기록 시점에 따라 메시지를 잃거나 두 번 처리하는 경우를 정리했다. 오프셋을 되돌려 다시 읽는 것도 직접 해 봤다.

## 요약

- 컨슈머 그룹의 오프셋은 브로커의 __consumer_offsets 토픽에 저장된다. 압축(compact) 토픽이라 그룹, 파티션별 마지막 값만 남는다.
- 커밋하는 오프셋은 '다음에 읽을 위치'다. 5번까지 처리했으면 6을 커밋한다.
- 처리 전에 커밋하면 at-most-once(잃을 수 있음), 처리 후에 커밋하면 at-least-once(두 번 처리할 수 있음)다.
- exactly-once는 멱등 프로듀서와 트랜잭션, 그리고 read_committed로 읽는 컨슈머를 묶어서 '카프카 안에서' 만든다.
- kafka-consumer-groups.sh --reset-offsets로 그룹 오프셋을 되돌릴 수 있다. 그룹에 활성 멤버가 없어야 한다.

## 1. 커밋 시점과 전달 보장

{{< mermaid >}}
flowchart LR
  subgraph amo["at-most-once"]
    direction TB
    A1["poll"] --> A2["커밋"] --> A3["처리"]
    A3 -.->|"처리 중 죽으면<br>그 레코드는 잃음"| A1
  end
  subgraph alo["at-least-once"]
    direction TB
    B1["poll"] --> B2["처리"] --> B3["커밋"]
    B3 -.->|"커밋 전에 죽으면<br>다시 읽어 두 번 처리"| B1
  end
  amo ~~~ alo
{{< /mermaid >}}

자동 커밋(enable.auto.commit=true, 5초마다)은 다음 poll() 때 지난번에 받은 것까지 커밋한다. 처리가 끝난 다음 poll()을 부르는 일반적인 루프라면 at-least-once에 가깝다. 대신 컨슈머가 죽으면 마지막 커밋 뒤 최대 5초 분량을 다시 처리할 수 있다. 그래서 처리 로직을 같은 메시지가 두 번 와도 괜찮게(멱등하게) 만드는 게 기본이라고 한다.

## 2. 멱등 프로듀서를 로그에서 보기

프로듀서 편에서 enable.idempotence가 기본 true라고 정리했는데, 실제로 로그 파일에 그 흔적이 있었다.

```bash
bin/kafka-dump-log.sh --files /tmp/kraft-combined-logs/orders-2/00000000000000000000.log --print-data-log
```

```text
baseOffset: 0 lastOffset: 5 count: 6 baseSequence: 0 lastSequence: 5 producerId: 0 producerEpoch: 0 ... isTransactional: false ...
| offset: 0 ... sequence: 0 ... key: user-1 payload: 주문 생성 1001
| offset: 1 ... sequence: 1 ... key: user-2 payload: 주문 생성 1002
| offset: 2 ... sequence: 2 ... key: user-1 payload: 결제 완료 1001
```

producerId와 레코드마다 붙은 sequence가 보인다. 프로듀서가 같은 배치를 재시도하면 브로커는 (producerId, sequence)가 이미 받은 것인지 보고 중복을 버린다. 반대로 acks=1로 보낸 s2 레코드는 sequence가 -1이었는데, 콘솔 프로듀서에 acks를 직접 주면서 멱등성이 꺼진 것으로 보인다(멱등 프로듀서는 acks=all이 필요하다).

## 3. 트랜잭션과 exactly-once

| 구성 | 하는 일 |
|---|---|
| 멱등 프로듀서 | 한 세션 안에서 재시도 중복 방지 |
| transactional.id | 프로듀서를 재시작해도 같은 ID로 이어서, 이전 세션의 미완료 트랜잭션을 정리 |
| 트랜잭션 | 여러 파티션에 쓰기 + 컨슈머 오프셋 커밋을 한 단위로 커밋하거나 취소 |
| isolation.level=read_committed | 커밋된 트랜잭션 레코드만 읽음(기본값은 read_uncommitted) |

'읽고 → 처리해서 → 다른 토픽에 쓰는' 파이프라인에서, 출력 쓰기와 입력 오프셋 커밋을 한 트랜잭션으로 묶으면 중간에 죽어도 둘 다 반영되거나 둘 다 취소된다. Kafka Streams는 processing.guarantee=exactly_once_v2 설정 하나로 이걸 해 준다. 다만 이건 카프카 안에서의 이야기라, 처리 중에 외부 DB에 쓰거나 이메일을 보내는 건 따로 멱등하게 만들어야 한다.

## 4. 오프셋 되돌리기

billing 그룹은 orders를 끝까지 읽은 상태였다. 처음부터 다시 읽게 하려고 오프셋을 earliest로 돌렸다. 먼저 --dry-run으로 결과만 보고, --execute로 적용했다.

```bash
bin/kafka-consumer-groups.sh --bootstrap-server localhost:9092 --group billing --topic orders \
  --reset-offsets --to-earliest --dry-run
```

```text
GROUP                          TOPIC                          PARTITION  NEW-OFFSET     
billing                        orders                         0          0              
billing                        orders                         1          0              
billing                        orders                         2          0              
```

```bash
bin/kafka-consumer-groups.sh --bootstrap-server localhost:9092 --group billing --topic orders \
  --reset-offsets --to-earliest --execute
bin/kafka-consumer-groups.sh --bootstrap-server localhost:9092 --describe --group billing
```

```text
Consumer group 'billing' has no active members.

GROUP           TOPIC           PARTITION  CURRENT-OFFSET  LOG-END-OFFSET  LAG
billing         orders          0          0               0               0
billing         orders          1          0               2               2
billing         orders          2          0               6               6
```

랙이 다시 8건이 됐다. 다음에 이 그룹으로 읽으면 처음부터 다시 처리한다. 그룹에 컨슈머가 살아 있을 때는 reset이 거부된다. 실수로 돌아가는 서비스의 오프셋을 바꾸는 걸 막는 장치다.

| 옵션 | 되돌릴 위치 |
|---|---|
| --to-earliest, --to-latest | 처음, 끝 |
| --to-offset 100 | 특정 오프셋 |
| --shift-by -10 | 지금 위치에서 10개 앞으로 |
| --to-datetime 2025-12-20T09:00:00.000 | 그 시각 이후 첫 레코드 |

장애로 잘못 처리된 구간을 다시 처리할 때 --to-datetime이 제일 쓸모 있을 것 같다.

> **쉬운 설명**
>
> 오프셋 커밋은 책에 꽂는 책갈피다. 한 장을 다 읽고 책갈피를 옮기면(처리 후 커밋), 읽다가 졸아도 다음에 그 장부터 다시 읽게 되어 한 장을 두 번 읽을 수는 있어도 빼먹지는 않는다. 책갈피부터 옮기고 읽으면(처리 전 커밋), 졸았을 때 그 장을 건너뛴다. exactly-once는 '읽고, 요약 노트에 적고, 책갈피 옮기기'를 한 번에 묶어서, 셋 다 되거나 셋 다 안 된 것으로 치는 방법이다.

## 헷갈렸던 것들

- 커밋하는 값은 마지막으로 처리한 오프셋이 아니라 다음에 읽을 오프셋이다.
- 자동 커밋이라고 처리 전에 커밋되는 건 아니다. poll() 때 지난번 것을 커밋한다.
- exactly-once는 카프카 밖의 부수 효과(외부 API 호출 등)까지 막아 주지 않는다.

## 용어 정리

| 용어 | 뜻 |
|---|---|
| __consumer_offsets | 컨슈머 그룹 오프셋을 저장하는 내부 압축 토픽 |
| at-most-once | 최대 한 번. 잃을 수 있지만 중복은 없음 |
| at-least-once | 최소 한 번. 잃지 않지만 중복될 수 있음 |
| exactly-once | 카프카 안에서 정확히 한 번 반영 |
| transactional.id | 재시작을 넘어 트랜잭션 프로듀서를 식별하는 ID |
| read_committed | 커밋된 트랜잭션 레코드만 읽는 컨슈머 격리 수준 |

## 참고 자료

- Apache Kafka 문서, 설계(메시지 전달 보장): <https://kafka.apache.org/41/design/design/>
- Apache Kafka 문서, 기본 운영(컨슈머 그룹 관리): <https://kafka.apache.org/41/operations/basic-kafka-operations/>
- Apache Kafka 문서, 트랜잭션 프로토콜: <https://kafka.apache.org/41/operations/transaction-protocol/>

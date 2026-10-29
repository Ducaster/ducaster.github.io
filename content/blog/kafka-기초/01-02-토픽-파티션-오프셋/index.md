---
title: '[Kafka 기초] 토픽, 파티션, 오프셋: 키가 같으면 같은 파티션으로 간다'
date: '2025-11-01T21:00:00+09:00'
categories:
- Kafka
tags:
- kafka
- topic
- partition
- offset
- key
- murmur2
- ordering
- kafka-topics
- console-producer
- 기본 개념
series:
- Kafka 기초
series_order: 3
---

앞 글에서 그린 구조 중 토픽 부분을 직접 만들어 봤다. 파티션 3개짜리 orders 토픽에 키를 붙여 이벤트를 넣고, 어느 파티션 몇 번 오프셋에 들어갔는지 확인했다. 키 세 개가 전부 한 파티션에 들어가서, 카프카가 쓰는 해시 함수를 직접 계산해 봤다.

## 요약

- 토픽은 파티션 여러 개로 나뉘고, 파티션마다 0부터 시작하는 오프셋이 따로 붙는다.
- 키가 있으면 murmur2(키) % 파티션 수로 파티션이 정해진다. 그래서 같은 키는 항상 같은 파티션에 들어가 순서가 지켜진다.
- 순서는 파티션 안에서만 보장된다. 다른 파티션의 이벤트끼리는 순서가 없다.
- 키가 몇 개 안 되면 해시가 겹쳐 한 파티션에 몰릴 수 있다. 실제로 키 3개가 전부 2번 파티션에 들어갔다.
- 토픽을 미리 안 만들고 보내면 브로커가 기본값(파티션 1개)으로 자동 생성한다. 실수하기 쉬운 부분이다.

## 1. 토픽 만들기

```bash
bin/kafka-topics.sh --bootstrap-server localhost:9092 --create --topic orders --partitions 3 --replication-factor 1
# Created topic orders.
bin/kafka-topics.sh --bootstrap-server localhost:9092 --describe --topic orders
```

```text
Topic: orders	TopicId: 92aQTEZWRH6UhK5hvPsrVA	PartitionCount: 3	ReplicationFactor: 1	Configs: min.insync.replicas=1,segment.bytes=1073741824
	Topic: orders	Partition: 0	Leader: 1	Replicas: 1	Isr: 1	Elr: 	LastKnownElr: 
	Topic: orders	Partition: 1	Leader: 1	Replicas: 1	Isr: 1	Elr: 	LastKnownElr: 
	Topic: orders	Partition: 2	Leader: 1	Replicas: 1	Isr: 1	Elr: 	LastKnownElr: 
```

브로커가 하나라 리더도 복제본도 전부 1번이다. Isr, Elr은 복제를 정리할 때 다시 본다.

## 2. 키를 붙여 보내고 위치 확인하기

콘솔 프로듀서는 parse.key, key.separator를 주면 '키:값' 형태로 입력을 받는다.

```bash
printf 'user-1:주문 생성 1001\nuser-2:주문 생성 1002\nuser-1:결제 완료 1001\nuser-3:주문 생성 1003\nuser-2:결제 완료 1002\nuser-1:배송 시작 1001\n' | \
  bin/kafka-console-producer.sh --bootstrap-server localhost:9092 --topic orders \
  --property parse.key=true --property key.separator=:
bin/kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic orders --from-beginning \
  --property print.key=true --property print.partition=true --property print.offset=true
```

```text
Partition:2	Offset:0	user-1	주문 생성 1001
Partition:2	Offset:1	user-2	주문 생성 1002
Partition:2	Offset:2	user-1	결제 완료 1001
Partition:2	Offset:3	user-3	주문 생성 1003
Partition:2	Offset:4	user-2	결제 완료 1002
Partition:2	Offset:5	user-1	배송 시작 1001
```

파티션을 3개나 만들었는데 6건이 전부 2번 파티션에 들어갔다. 이어서 user-4, user-5로 두 건을 더 보냈더니 그건 1번 파티션으로 갔다.

```bash
bin/kafka-get-offsets.sh --bootstrap-server localhost:9092 --topic orders
# orders:0:0
# orders:1:2
# orders:2:6
```

kafka-get-offsets는 파티션별로 다음에 쓰일 오프셋(로그 끝)을 보여 준다. 0번은 아직 비어 있다.

## 3. 왜 한 파티션에 몰렸나: murmur2 직접 계산

키가 있는 레코드는 기본 파티셔너가 murmur2 해시를 쓴다. (해시 & 0x7fffffff) % 파티션 수가 파티션 번호다. 우연히 겹친 건지 보려고 카프카 소스의 Utils.murmur2를 파이썬으로 그대로 옮겨서 계산했다.

| 키 | 파티션 3개일 때 | 4개일 때 | 6개일 때 |
|---|---|---|---|
| user-1 | 2 | 0 | 2 |
| user-2 | 2 | 0 | 2 |
| user-3 | 2 | 3 | 5 |
| user-4 | 1 | 3 | 1 |
| user-5 | 1 | 2 | 4 |

브로커가 넣은 위치와 똑같았다. 키가 3개뿐이면 이렇게 한쪽에 몰릴 수 있다. 실제 서비스처럼 사용자가 수만 명이면 고르게 퍼진다. 키 종류가 적거나 특정 키에 이벤트가 몰리면(핫 키) 파티션 하나만 바빠진다.

표에서 하나 더 보이는 게 있다. 파티션을 3개에서 4개로 늘리면 user-1이 2번에서 0번으로 옮겨 간다. 이미 쓰인 user-1 이벤트는 2번에 남고 새 이벤트는 0번으로 가니, user-1의 순서가 두 파티션에 갈라진다. 키 순서가 중요한 토픽은 처음부터 파티션 수를 넉넉히 잡으라는 말이 이래서 나온다.

{{< mermaid >}}
flowchart LR
  P["프로듀서<br>key=user-1"] --> H["murmur2(user-1)<br>& 0x7fffffff"]
  H --> M3{"% 3"}
  H --> M4{"% 4"}
  M3 -->|"= 2"| A["파티션 3개일 때<br>2번 파티션"]
  M4 -->|"= 0"| B["파티션 4개로 늘리면<br>0번 파티션"]
{{< /mermaid >}}

## 4. 순서는 파티션 안에서만

컨슈머 그룹 billing으로 다섯 건만 읽었더니 이 순서로 나왔다.

```text
주문 생성 1004
주문 생성 1005
주문 생성 1001
주문 생성 1002
결제 완료 1001
```

나중에 보낸 1004, 1005(1번 파티션)가 먼저 나왔다. 컨슈머는 파티션을 번갈아 읽기 때문에 파티션 사이의 순서는 보장하지 않는다. 대신 user-1의 '주문 생성 → 결제 완료 → 배송 시작'은 한 파티션 안이라 항상 이 순서다.

## 5. 토픽 자동 생성에 당한 이야기

처음 실습할 때 브로커가 덜 떠서 토픽 생성이 타임아웃으로 실패했는데, 그걸 못 보고 바로 프로듀서를 돌렸다. 그런데 메시지가 잘 들어갔다. describe를 해 보니 orders가 파티션 1개로 만들어져 있었다.

```text
Topic: orders	TopicId: IzplDZ9hQMWIHKq5F3YYGA	PartitionCount: 1	ReplicationFactor: 1	...
```

auto.create.topics.enable 기본값이 true라서, 없는 토픽에 쓰면 브로커가 num.partitions(기본 1)로 알아서 만든다. 운영에서는 이게 꺼져 있는 경우가 많다고 한다. 오타 난 토픽 이름이 조용히 생기는 걸 막으려는 것이다.

> **쉬운 설명**
>
> 토픽은 택배 회사의 '서울행' 같은 행선지 이름이고, 파티션은 그 행선지로 가는 트럭 여러 대다. 송장 번호(키)를 넣은 계산식으로 트럭이 정해져서, 같은 고객의 택배는 늘 같은 트럭에 실린다. 그래서 한 고객의 택배끼리는 실은 순서대로 도착한다. 하지만 트럭이 다르면 누가 먼저 도착할지 모른다. 트럭을 한 대 더 늘리면 계산식 결과가 바뀌어 같은 고객 택배가 다른 트럭에 실리기 시작한다.

## 헷갈렸던 것들

- 오프셋은 토픽 전체가 아니라 파티션마다 따로 0부터 센다. orders-0의 5번과 orders-2의 5번은 다른 이벤트다.
- 키가 없으면 murmur2를 쓰지 않는다. 프로듀서가 한 배치를 한 파티션에 몰아 보내다가 다음 파티션으로 넘어간다(스티키 파티셔닝). 이건 프로듀서 편에서 다시 본다.
- 파티션은 늘릴 수만 있고 줄일 수는 없다.

## 용어 정리

| 용어 | 뜻 |
|---|---|
| 파티션 수 | 토픽을 몇 조각으로 나눌지. 병렬 처리 정도와 키 분산을 정한다 |
| 리더 | 파티션의 읽기, 쓰기를 맡는 브로커 |
| 로그 끝 오프셋(LEO) | 파티션에 다음으로 쓰일 오프셋 |
| murmur2 | 키 있는 레코드의 파티션을 정할 때 쓰는 해시 함수 |
| 핫 키 | 이벤트가 몰려 특정 파티션만 바쁘게 만드는 키 |

## 참고 자료

- Apache Kafka 문서, 토픽과 파티션 개념: <https://kafka.apache.org/41/getting-started/introduction/>
- Apache Kafka 소스, Utils.murmur2: <https://github.com/apache/kafka/blob/trunk/clients/src/main/java/org/apache/kafka/common/utils/Utils.java>
- Apache Kafka 문서, 브로커 설정 auto.create.topics.enable: <https://kafka.apache.org/41/configuration/broker-configs/>

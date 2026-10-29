---
title: '[Kafka 기초] 종합 실습: 주문 이벤트 파이프라인을 3노드 클러스터에 엮고 장애 내 보기'
date: '2026-02-21T21:00:00+09:00'
categories:
- Kafka
tags:
- kafka
- pipeline
- kafka-connect
- consumer-group
- replication
- failover
- operations
- checklist
- 종합 실습
series:
- Kafka 기초
series_order: 14
---

지금까지 따로 해 본 것들을 3노드 클러스터 하나에 엮었다. CSV 주문 파일을 Connect로 토픽에 넣고, 컨슈머 그룹 둘이 각자 읽고, 그 상태에서 브로커 하나를 내려서 무엇이 계속 되고 무엇이 막히는지 확인했다. 마지막에는 회사 클러스터를 처음 볼 때 확인할 목록을 만들었다.

## 요약

- 파이프라인: orders.csv → FileStreamSource → orders-raw(복제 계수 3) → billing, analytics 그룹, 그리고 FileStreamSink로 파일 사본.
- 브로커 하나를 내려도 min.insync.replicas=2라 쓰기, 읽기, Connect가 모두 계속 돌았다. 파티션 리더만 남은 브로커로 옮겨 갔다.
- 컨트롤러 쿼럼은 3대 중 2대가 살아 있어서 메타데이터 작업도 계속 됐다.
- 브로커를 되살리면 ISR은 알아서 돌아오지만 리더는 선호 리더 선출로 되돌린다.
- 기초에서 배운 것을 운영 점검표로 묶었다. 3.9 ZooKeeper 클러스터인 회사 환경에서는 쿼럼 대신 ZooKeeper 상태를 보는 것만 다르다.

## 1. 전체 구성

{{< mermaid >}}
flowchart LR
  CSV["orders.csv"] --> SRC["Connect<br>FileStreamSource"]
  SRC --> T["orders-raw<br>파티션 3, 복제 3<br>min.insync.replicas=2"]
  T --> G1["billing 그룹"]
  T --> G2["analytics 그룹"]
  T --> SNK["Connect<br>FileStreamSink"]
  SNK --> COPY["orders-copy.txt"]
  subgraph cluster["노드 3대 (브로커 + 컨트롤러 결합)"]
    T
  end
{{< /mermaid >}}

| 단계 | 쓴 것 | 처음 정리한 글 |
|---|---|---|
| 클러스터 | 노드 3대, 동적 쿼럼 | 브로커와 KRaft 컨트롤러 |
| 토픽 | 복제 계수 3, min.insync.replicas 2 | 복제와 ISR |
| 넣기 | FileStreamSource, JsonConverter | Kafka Connect |
| 읽기 | 그룹 둘, 각자 오프셋 | 컨슈머와 컨슈머 그룹 |
| 장애 | 브로커 하나 정지 | 복제와 ISR |

## 2. 정상 상태 기록

장애를 내기 전에 기준이 될 상태를 남겼다. 나중에 '뭐가 달라졌나'를 비교하려면 이게 있어야 했다.

```bash
bin/kafka-metadata-quorum.sh --bootstrap-server $B describe --status | grep -E 'LeaderId|CurrentVoters'
bin/kafka-topics.sh --bootstrap-server $B --describe --topic orders-raw
bin/kafka-consumer-groups.sh --bootstrap-server $B --describe --group billing
curl -s localhost:8083/connectors/orders-file-source/status
```

Connect 소스는 RUNNING이었고, 토픽에는 CSV 세 줄이 JSON 봉투에 싸여 들어가 있었다.

```text
{"schema":{"type":"string","optional":false},"payload":"1001,user-1,서울,32000"}
```

## 3. 브로커 하나 내리기

노드 3을 내리고 15초쯤 뒤에 본 orders-raw 상태다.

```text
Topic: orders-raw	TopicId: QdB0mt0YSD-hRh2ojhZjvQ	PartitionCount: 3	ReplicationFactor: 3	Configs: min.insync.replicas=2
	Topic: orders-raw	Partition: 0	Leader: 1	Replicas: 3,1,2	Isr: 1,2	Elr: 	LastKnownElr: 
	Topic: orders-raw	Partition: 1	Leader: 1	Replicas: 1,2,3	Isr: 1,2	Elr: 	LastKnownElr: 
	Topic: orders-raw	Partition: 2	Leader: 2	Replicas: 2,3,1	Isr: 1,2	Elr: 	LastKnownElr: 
```

그 상태에서 CSV에 한 줄을 붙이고, 새 그룹 analytics로 처음부터 읽고, 토픽도 하나 만들어 봤다.

```bash
echo '1005,user-4,대구,12000' >> orders.csv
tail -2 orders-copy.txt
# -3,광주,21000
# 1005,user-4,대구,12000
bin/kafka-console-consumer.sh --bootstrap-server $B --topic orders-raw --group analytics --from-beginning | tail -2
# {"schema":{"type":"string","optional":false},"payload":"-3,광주,21000"}
# {"schema":{"type":"string","optional":false},"payload":"1005,user-4,대구,12000"}
bin/kafka-topics.sh --bootstrap-server $B --create --topic created-while-node3-down --partitions 3 --replication-factor 2
# Created topic created-while-node3-down.
bin/kafka-metadata-quorum.sh --bootstrap-server $B describe --status | grep LeaderId
# LeaderId:               2
```

| 확인한 것 | 결과 | 이유 |
|---|---|---|
| Connect 소스, 싱크 | 새 줄이 토픽과 사본 파일에 반영, 상태 RUNNING | 워커가 남은 브로커로 붙음 |
| 새 그룹으로 읽기 | 처음부터 끝까지 읽힘 | 리더가 남은 브로커로 넘어감 |
| 토픽 생성 | 됨 | 컨트롤러 3대 중 2대(과반) 살아 있음 |
| min.insync.replicas=3 토픽에 acks=all | NotEnoughReplicasException(복제 편에서 확인) | ISR 2개 < 3 |

마지막 줄이 이번 기초 공부에서 제일 기억에 남은 부분이다. 같은 장애라도 토픽 설정에 따라 서비스가 멈출 수도 있다. min.insync.replicas를 복제 계수와 같게 두면 브로커 하나만 내려가도 쓰기가 막힌다.

그리고 출력에 이상한 줄이 하나 있다. -3,광주,21000은 원래 1004,user-3,광주,21000이어야 했다. Connect 편 실습 때 커넥터가 돌아가는 중에 orders.csv를 편집기로 열어 한 줄을 지웠다가 다시 붙였는데, FileStreamSource는 파일이 뒤에 추가만 된다고 보고 '몇 바이트까지 읽었나'를 기억한다. 앞부분이 바뀌니 기억해 둔 위치가 줄 중간이 돼 버린 것이다. 소스 파일은 덧붙이기만 해야 한다는 걸 이렇게 배웠다.


## 4. 되살리기

노드 3을 다시 띄우자 ISR은 1,2,3으로 돌아왔다. 리더는 선호 리더 선출로 되돌렸다.

```bash
bin/kafka-leader-election.sh --bootstrap-server $B --election-type preferred --all-topic-partitions
bin/kafka-topics.sh --bootstrap-server $B --describe --under-replicated-partitions    # 아무것도 안 나오면 정상
```

## 5. 회사 클러스터를 처음 볼 때 확인할 것

| 순서 | 볼 것 | 명령, 설정 |
|---|---|---|
| 1 | 버전, 모드 | 브로커 로그의 Kafka version, ZooKeeper 모드인지 KRaft인지 |
| 2 | 메타데이터 쪽 상태 | KRaft면 kafka-metadata-quorum describe, ZooKeeper면 ZooKeeper 앙상블 상태 |
| 3 | 복제 부족, 리더 없음 | --under-replicated-partitions, --unavailable-partitions |
| 4 | 주요 토픽 설정 | 복제 계수, min.insync.replicas, retention.ms, cleanup.policy |
| 5 | 클라이언트 설정 | 프로듀서 acks, 컨슈머 group.protocol, auto.offset.reset |
| 6 | 랙 | 그룹별 LAG 추세 |
| 7 | 자동 생성 | auto.create.topics.enable이 켜져 있는지 |

회사 클러스터는 3.9 ZooKeeper 모드다. 4.x로 가려면 KRaft로 먼저 옮겨야 한다. 그 작업은 컨트롤러 역할을 ZooKeeper와 브로커 하나에서 KRaft 쿼럼으로 옮기는 일이다.

> **쉬운 설명**
>
> 이번 실습은 소방 훈련이었다. 평소 상태를 사진으로 찍어 두고(정상 상태 기록), 일부러 한 층 불을 끈 뒤(브로커 정지) 엘리베이터, 비상등, 출입문이 각각 어떻게 되는지 확인했다. 대부분은 다른 층 전기로 계속 돌았지만, '세 층 다 켜져 있어야 열리는 문'(min.insync.replicas=3)은 바로 잠겼다. 훈련이 끝나면 불을 다시 켜고 담당자를 원래 자리로 돌려놓는다(선호 리더 선출).

## 헷갈렸던 것들

- 결합 모드 3노드는 브로커 하나가 죽을 때 컨트롤러도 하나 같이 죽는다. 2대까지는 버티지만 여유가 없다.
- 장애 중에 들어온 데이터도 살아난 브로커가 따라잡으면 ISR로 돌아온다. 따라잡는 동안은 under-replicated로 보인다.
- Connect 단독 모드 워커 자체가 죽으면 파이프라인이 멈춘다. 이건 분산 모드로 풀 문제다.
- 메타데이터 쿼럼 리더는 노드를 껐다 켜는 사이 1번에서 2번으로 바뀌어 있었다. 쿼럼 리더와 파티션 리더는 따로 움직인다.

## 용어 정리

| 용어 | 뜻 |
|---|---|
| 기준 상태 | 장애 실습 전에 남겨 두는 정상 상태 기록 |
| 장애 넘김(failover) | 리더가 죽으면 ISR의 다른 복제본이 리더가 되는 것 |
| 선호 리더 선출 | 리더를 Replicas 목록 첫 번째 브로커로 되돌리는 작업 |
| under-replicated | ISR이 복제 계수보다 적은 상태 |

## 참고 자료

- Apache Kafka 문서, 기본 운영: <https://kafka.apache.org/41/operations/basic-kafka-operations/>
- Apache Kafka 문서, 복제(설계): <https://kafka.apache.org/41/design/design/>
- Apache Kafka 문서, KRaft: <https://kafka.apache.org/41/operations/kraft/>

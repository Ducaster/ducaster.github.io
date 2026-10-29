---
title: '[Kafka 기초] 복제와 ISR: 브로커 하나를 내려 보고 알게 된 것'
date: '2025-11-22T21:00:00+09:00'
categories:
- Kafka
tags:
- kafka
- replication
- leader
- follower
- isr
- min-insync-replicas
- high-watermark
- elr
- kip-966
- leader-election
- 기본 개념
series:
- Kafka 기초
series_order: 5
---

앞 글에서 띄운 3노드 클러스터에서 복제 계수 3짜리 토픽을 만들고, 브로커 하나를 일부러 내렸다. ISR이 줄어드는 것, min.insync.replicas 때문에 쓰기가 거절되는 것까지는 예상대로였는데, acks=1로 쓴 레코드가 컨슈머에게 안 보이는 건 예상 못 했다. 원인은 4.x에 들어온 ELR 규칙이었다.

## 요약

- 파티션마다 리더 하나와 팔로워 여럿이 있다. 쓰기와 읽기는 리더가 맡고, 팔로워는 리더를 따라 복사한다.
- ISR(In-Sync Replicas)은 리더를 제때 따라오고 있는 복제본 목록이다. replica.lag.time.max.ms(기본 30초) 동안 못 따라오면 빠진다.
- 컨슈머는 하이 워터마크(HW)까지만 읽는다. HW는 ISR이 모두 복사한 지점이다.
- acks=all이면 ISR 수가 min.insync.replicas보다 적을 때 쓰기가 NotEnoughReplicasException으로 거절된다.
- 4.0부터 들어온 ELR(KIP-966) 규칙 때문에, ISR이 min.insync.replicas보다 적으면 acks=1로 쓴 레코드도 HW가 안 올라가서 컨슈머에게 보이지 않는다.

## 1. 리더와 팔로워

```bash
B=localhost:19092,localhost:29092
bin/kafka-topics.sh --bootstrap-server $B --create --topic payments --partitions 3 --replication-factor 3
bin/kafka-topics.sh --bootstrap-server $B --describe --topic payments
```

```text
Topic: payments	TopicId: _wsZpsIlSjuxl0EDKKsONQ	PartitionCount: 3	ReplicationFactor: 3	Configs: min.insync.replicas=2
	Topic: payments	Partition: 0	Leader: 3	Replicas: 3,1,2	Isr: 3,1,2	Elr: 	LastKnownElr: 
	Topic: payments	Partition: 1	Leader: 1	Replicas: 1,2,3	Isr: 1,2,3	Elr: 	LastKnownElr: 
	Topic: payments	Partition: 2	Leader: 2	Replicas: 2,3,1	Isr: 2,3,1	Elr: 	LastKnownElr: 
```

Replicas의 첫 번째가 선호 리더(preferred leader)다. 파티션마다 리더가 다른 브로커에 골고루 배치돼서, 한 브로커에 쓰기가 몰리지 않는다.

{{< mermaid >}}
sequenceDiagram
  participant P as 프로듀서 (acks=all)
  participant L as 리더 (브로커 1)
  participant F2 as 팔로워 (브로커 2)
  participant F3 as 팔로워 (브로커 3)
  P->>L: 레코드 쓰기
  L->>L: 로컬 로그에 추가 (LEO 증가)
  F2->>L: Fetch (가져가기)
  F3->>L: Fetch
  L->>L: ISR 모두 복사 → HW 증가
  L-->>P: 성공 응답
  Note over L: 컨슈머는 HW까지만 읽는다
{{< /mermaid >}}

팔로워는 리더에게 요청해서 데이터를 가져간다(pull). 컨슈머가 데이터를 가져가는 것과 같은 방식이다.

## 2. 브로커 하나를 내리면

노드 3을 내리고 10초쯤 뒤에 다시 봤다.

```text
Topic: payments	TopicId: _wsZpsIlSjuxl0EDKKsONQ	PartitionCount: 3	ReplicationFactor: 3	Configs: min.insync.replicas=2
	Topic: payments	Partition: 0	Leader: 1	Replicas: 3,1,2	Isr: 1,2	Elr: 	LastKnownElr: 
	Topic: payments	Partition: 1	Leader: 1	Replicas: 1,2,3	Isr: 1,2	Elr: 	LastKnownElr: 
	Topic: payments	Partition: 2	Leader: 2	Replicas: 2,3,1	Isr: 2,1	Elr: 	LastKnownElr: 
```

리더가 3이던 0번 파티션은 ISR에 남은 1번으로 리더가 넘어갔다. 모든 파티션의 ISR에서 3이 빠졌다. 복제본이 부족한 파티션은 이렇게 따로 볼 수 있다.

```bash
bin/kafka-topics.sh --bootstrap-server $B --describe --under-replicated-partitions
```

ISR이 2개라 min.insync.replicas=2를 만족하니 payments에 acks=all로 쓰는 건 그대로 됐다.

## 3. min.insync.replicas가 3이면

비교하려고 min.insync.replicas=3인 strict 토픽을 미리 만들어 뒀다. 브로커 하나가 빠진 상태에서 acks=all로 써 봤다.

```bash
echo 's1' | bin/kafka-console-producer.sh --bootstrap-server $B --topic strict --request-required-acks all
# org.apache.kafka.common.errors.NotEnoughReplicasException: Messages are rejected since there are fewer in-sync replicas than required.
```

거절됐다. 여기까지는 예상대로다. 그런데 acks=1로 보낸 s2는 오류 없이 들어갔는데, 읽어 보면 없었다.

```bash
echo 's2' | bin/kafka-console-producer.sh --bootstrap-server $B --topic strict --request-required-acks 1
bin/kafka-get-offsets.sh --bootstrap-server $B --topic strict
# strict:0:0
```

리더(노드 1)의 로그 파일을 직접 열어 보니 s2는 분명히 써져 있었다.

```bash
bin/kafka-dump-log.sh --files c3/n1/strict-0/00000000000000000000.log --print-data-log
# | offset: 0 CreateTime: … keySize: -1 valueSize: 2 sequence: -1 headerKeys: [] payload: s2
cat c3/n1/replication-offset-checkpoint | grep strict
# strict 0 0
```

로그 끝은 1인데 HW는 0이다. 이유는 ELR 문서에 있었다. 4.0부터 '엄격한 min ISR' 규칙이 적용돼서, ISR 크기가 min.insync.replicas보다 작으면 HW가 올라가지 않는다. 그래야 ISR에서 빠진 복제본 중 안전한 것(ELR)을 나중에 리더로 뽑아도 데이터를 잃지 않는다. 4.1에서 새로 만든 클러스터는 이 기능이 기본으로 켜져 있다(eligible.leader.replicas.version=1). describe 결과에도 strict 토픽의 Elr 칸에 3이 나와 있었다.

```text
	Topic: strict	Partition: 0	Leader: 1	Replicas: 1,2,3	Isr: 1,2	Elr: 3	LastKnownElr: 
```

acks=1은 '리더가 받았다'만 보장하고, 컨슈머가 볼 수 있는지는 HW가 정한다.

## 4. 다시 살리고 리더 되돌리기

노드 3을 다시 띄우자 ISR이 1,2,3으로 돌아왔고, strict의 HW도 1로 올라가 s2가 보이기 시작했다.

```bash
bin/kafka-get-offsets.sh --bootstrap-server $B --topic strict
# strict:0:1
```

하지만 0번 파티션 리더는 여전히 1이었다. 선호 리더로 되돌리려고 선출을 직접 돌렸다. (auto.leader.rebalance.enable 기본값이 true라 그냥 두면 주기적으로 알아서 되돌린다.)

```bash
bin/kafka-leader-election.sh --bootstrap-server $B --election-type preferred --all-topic-partitions
# Successfully completed leader election (PREFERRED) for partitions payments-0, perf-0
```

```text
	Topic: payments	Partition: 0	Leader: 3	Replicas: 3,1,2	Isr: 1,2,3	Elr: 	LastKnownElr: 
```

| 설정 | 기본값(4.1) | 뜻 |
|---|---|---|
| default.replication.factor | 1 | 토픽 만들 때 복제 계수를 안 주면 쓰는 값 |
| min.insync.replicas | 1 | acks=all 쓰기에 필요한 최소 ISR 수 |
| replica.lag.time.max.ms | 30000 | 이 시간 동안 못 따라오면 ISR에서 뺀다 |
| unclean.leader.election.enable | false | ISR 밖 복제본을 리더로 뽑을지. true면 데이터 유실 가능 |

기본값은 실습 브로커에서 kafka-configs --describe --all로 직접 확인했다. 운영에서 흔히 쓰는 조합은 복제 계수 3, min.insync.replicas 2, acks=all이라고 한다. 브로커 하나가 죽어도 쓰기가 되고, 데이터는 최소 두 곳에 있다.

> **쉬운 설명**
>
> 복제는 중요한 문서를 세 부 복사해서 세 사람이 나눠 들고 있는 것이다. 원본을 쥔 사람(리더)이 고칠 때마다 나머지 둘(팔로워)이 따라 고친다. 제때 따라 고치는 사람 명단이 ISR이다. '최소 두 사람이 갖고 있어야 결재 완료'(min.insync.replicas=2)로 정해 두면, 한 사람이 휴가 가도 결재는 된다. 그런데 기준을 세 사람으로 올리면, 한 명이 빠지는 순간 원본에 적어도 공식 문서(HW)로 인정되지 않는다.

## 헷갈렸던 것들

- 복제 계수 3은 '원본 1 + 복사본 2'가 아니라 '전부 합쳐 3부'다. 리더도 복제본 중 하나다.
- min.insync.replicas는 acks=all일 때만 쓰기 거절 조건이 된다. 하지만 4.x에서는 HW 진행에도 영향을 줘서 acks=1 데이터의 가시성까지 바뀐다.
- 브로커가 살아 돌아와도 리더가 자동으로 바로 돌아오지는 않는다. 선호 리더 선출이 따로 돈다.

## 용어 정리

| 용어 | 뜻 |
|---|---|
| 복제 계수 | 파티션 복제본 개수(리더 포함) |
| ISR | 리더를 제때 따라오고 있는 복제본 목록 |
| HW(하이 워터마크) | ISR이 모두 복사해서 컨슈머에게 보여도 되는 마지막 지점 |
| LEO(로그 끝 오프셋) | 각 복제본 로그의 다음 쓰기 위치 |
| ELR | ISR에서 빠졌지만 데이터 유실 없이 리더가 될 수 있는 복제본 목록(KIP-966) |
| 선호 리더 | Replicas 목록의 첫 번째 브로커 |

## 참고 자료

- Apache Kafka 문서, 복제: <https://kafka.apache.org/41/design/design/>
- Apache Kafka 문서, Eligible Leader Replicas: <https://kafka.apache.org/41/operations/eligible-leader-replicas/>
- KIP-966, Eligible Leader Replicas: <https://cwiki.apache.org/confluence/display/KAFKA/KIP-966%3A+Eligible+Leader+Replicas>

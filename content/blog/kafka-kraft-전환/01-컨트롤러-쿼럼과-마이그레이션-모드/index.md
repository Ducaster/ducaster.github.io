---
title: '[Kafka 전환] 3.9.1 ZooKeeper 클러스터를 KRaft로 (1): 컨트롤러 쿼럼을 붙이고 메타데이터 옮기기'
date: '2026-06-13T22:00:00+09:00'
categories:
- Kafka
tags:
- kafka
- kraft
- zookeeper
- migration
- kafka-3.9
- controller-quorum
- dual-write
- operations
- 운영
series:
- Kafka KRaft 전환
series_order: 1
---

회사 카프카 클러스터를 ZooKeeper 모드에서 KRaft로 옮기는 작업을 맡았다. 지금 버전은 3.9.1이고 브로커 3대, ZooKeeper 3대 구성이다. 4.x로 올리려면 KRaft가 먼저여야 해서, 이번 달 안에 전환과 4.2.1 업그레이드까지 끝내는 게 목표다. 작업 전에 노트북에 같은 구성을 작게 만들어 리허설했고, 이 글의 명령과 로그는 그 리허설 기록이다. 운영에는 컨트롤러 3대를 따로 두지만, 노트북에서는 ZooKeeper 1대, 브로커 3대, 컨트롤러 1대로 줄였다.

## 요약

- 4.0부터 ZooKeeper 모드가 없어서, ZooKeeper 클러스터는 3.9.x(3.9.1 이상)에서 KRaft로 옮긴 다음에 4.x로 올려야 한다. 브로커는 inter.broker.protocol.version=3.9여야 한다.
- 순서는 컨트롤러 쿼럼 준비 → 브로커를 마이그레이션 모드로 롤링 재시작 → 브로커를 KRaft 모드로 롤링 재시작 → 마무리(finalize)다.
- 컨트롤러는 기존 클러스터 ID로 포맷해야 한다. ID는 ZooKeeper의 /cluster/id에서 읽는다.
- 브로커가 전부 마이그레이션 모드로 붙으면 컨트롤러가 ZooKeeper 메타데이터를 한 번에 옮기고, 그 뒤로는 KRaft와 ZooKeeper 양쪽에 쓰는 이중 쓰기(DUAL_WRITE) 상태가 된다.
- 마무리 전까지는 ZooKeeper 모드로 되돌릴 수 있다. 되돌리기 표를 단계마다 확인하며 진행했다.

## 1. 전체 단계

{{< mermaid >}}
flowchart TB
  subgraph p1["이번 글"]
    direction LR
    A["0. 준비<br>3.9.1, IBP 3.9<br>클러스터 ID 확인"] --> B["1. KRaft 컨트롤러 쿼럼<br>migration.enable=true<br>zookeeper.connect"]
    B --> C["2. 브로커 마이그레이션 모드<br>롤링 재시작"]
    C --> D["메타데이터 이관 완료<br>DUAL_WRITE"]
  end
  subgraph p2["다음 글"]
    direction LR
    E["3. 브로커를 KRaft로<br>롤링 재시작"] --> F["4. 마무리<br>컨트롤러에서 ZK 설정 제거"]
    F --> G["5. ZooKeeper 철거"]
  end
  p1 --> p2
{{< /mermaid >}}

4번(마무리)을 하기 전까지는 각 단계에서 ZooKeeper 모드로 되돌리는 절차가 문서에 있다. 그래서 작업 계획을 '어디까지 했을 때 무엇을 되돌리나' 표와 같이 만들었다.

## 2. 준비

리허설용 ZooKeeper 모드 브로커 설정이다. 운영 설정에서 마이그레이션과 관계없는 것만 뺐다.

```text
broker.id=1
listeners=PLAINTEXT://:19092
advertised.listeners=PLAINTEXT://localhost:19092
listener.security.protocol.map=PLAINTEXT:PLAINTEXT
log.dirs=/data/kafka/b1
zookeeper.connect=localhost:2181
inter.broker.protocol.version=3.9
default.replication.factor=3
min.insync.replicas=2
offsets.topic.replication.factor=3
```

작업 전후를 비교하려고 토픽 끝 오프셋과 컨슈머 그룹 오프셋을 기록했다. 리허설에서는 orders 토픽(파티션 6, 복제 3)에 1만 건을 넣고 billing 그룹이 6천 건만 읽게 해 두었다.

```text
orders:0:1404
orders:1:2044
orders:2:936
orders:3:2496
orders:4:2028
orders:5:1092

GROUP   TOPIC  PARTITION  CURRENT-OFFSET  LOG-END-OFFSET  LAG
billing orders 0          1404            1404            0
billing orders 1          100             2044            1944
billing orders 2          936             936             0
billing orders 3          2496            2496            0
billing orders 4          0               2028            2028
billing orders 5          1064            1092            28
```

클러스터 ID와 지금 컨트롤러는 ZooKeeper에서 읽는다.

```bash
bin/zookeeper-shell.sh localhost:2181 get /cluster/id
# {"version":"1","id":"03uEjGEgRmybviSeUSD05A"}
bin/zookeeper-shell.sh localhost:2181 get /controller
# {"version":2,"brokerid":1,"timestamp":"…","kraftControllerEpoch":-1}
```

지금은 브로커 1이 ZooKeeper 방식 컨트롤러다. 문서 권고대로 컨트롤러의 log4j 설정에 org.apache.kafka.metadata.migration=TRACE를 넣어 이관 과정을 자세히 남기게 했다.

## 3. KRaft 컨트롤러 쿼럼 준비

```text
process.roles=controller
node.id=3000
controller.quorum.voters=3000@localhost:9093
controller.listener.names=CONTROLLER
listeners=CONTROLLER://:9093
listener.security.protocol.map=CONTROLLER:PLAINTEXT,PLAINTEXT:PLAINTEXT
log.dirs=/data/kafka/c3000
# ZooKeeper 마이그레이션
zookeeper.metadata.migration.enable=true
zookeeper.connect=localhost:2181
inter.broker.listener.name=PLAINTEXT
```

운영에서는 node.id 3000, 3001, 3002 세 대를 controller.quorum.voters에 모두 적었다. 브로커 ID와 겹치지 않게 큰 번호를 썼다. 포맷은 반드시 기존 클러스터 ID로 한다.

```bash
bin/kafka-storage.sh format --config controller.properties --cluster-id 03uEjGEgRmybviSeUSD05A
# Formatting metadata directory /data/kafka/c3000 with metadata.version 3.9-IV0.
bin/kafka-server-start.sh controller.properties
```

컨트롤러 로그에서 이관 상태가 이렇게 바뀌었다.

```text
[KRaftMigrationDriver id=3000] 3000 transitioning from UNINITIALIZED to INACTIVE state
[KRaftMigrationDriver id=3000] 3000 transitioning from INACTIVE to WAIT_FOR_CONTROLLER_QUORUM state
[KRaftMigrationDriver id=3000] Controller Quorum is ready for Zk to KRaft migration. Now waiting for ZK brokers.
[KRaftMigrationDriver id=3000] 3000 transitioning from WAIT_FOR_CONTROLLER_QUORUM to WAIT_FOR_BROKERS state
```

여기서 멈춰 있는 게 정상이다. 브로커들이 마이그레이션 모드로 붙어야 다음으로 넘어간다.

## 4. 브로커를 마이그레이션 모드로

브로커 설정에 네 줄을 더하고, 보안 프로토콜 맵에 CONTROLLER를 넣었다.

```text
listener.security.protocol.map=PLAINTEXT:PLAINTEXT,CONTROLLER:PLAINTEXT
# ZooKeeper -> KRaft migration
zookeeper.metadata.migration.enable=true
controller.quorum.voters=3000@localhost:9093
controller.listener.names=CONTROLLER
```

broker.id, zookeeper.connect, inter.broker.protocol.version은 그대로 둔다. 아직 ZooKeeper 모드 브로커이고, 컨트롤러와 통신할 준비만 하는 단계다. 한 대씩 내리고 새 설정으로 올렸다. 다음 브로커로 넘어가기 전에 --under-replicated-partitions가 비는지 확인했다.

세 번째 브로커가 붙자 컨트롤러 로그에 기다리던 줄이 나왔다.

```text
[KRaftMigrationDriver id=3000] Completed migration of metadata from ZooKeeper to KRaft. 62 records were generated in 126 ms across 1 batches.
The record types were {TOPIC_RECORD=2, PARTITION_RECORD=56, CONFIG_RECORD=3, PRODUCER_IDS_RECORD=1}.
The current metadata offset is now 231 with an epoch of 1. Saw 3 brokers in the migrated metadata [1, 2, 3].
[KRaftMigrationDriver id=3000] 3000 transitioning from ZK_MIGRATION to SYNC_KRAFT_TO_ZK state
[KRaftMigrationDriver id=3000] 3000 transitioning from SYNC_KRAFT_TO_ZK to KRAFT_CONTROLLER_TO_BROKER_COMM state
[KRaftMigrationDriver id=3000] 3000 transitioning from KRAFT_CONTROLLER_TO_BROKER_COMM to DUAL_WRITE state
```

토픽 2개(orders, __consumer_offsets)와 파티션 56개(6 + 50)가 KRaft 메타데이터 레코드로 옮겨졌다. ZooKeeper 쪽에서도 컨트롤러가 바뀐 게 보인다.

```bash
bin/zookeeper-shell.sh localhost:2181 get /controller
# {"version":2,"brokerid":3000,"timestamp":"…","kraftControllerEpoch":1}
bin/zookeeper-shell.sh localhost:2181 get /migration
# {"version":0,"kraft_metadata_offset":334,"kraft_controller_id":3000,"kraft_metadata_epoch":1,"kraft_controller_epoch":1}
```

## 5. 이중 쓰기 확인

DUAL_WRITE 상태에서는 KRaft 컨트롤러가 메타데이터를 바꿀 때마다 ZooKeeper에도 같이 쓴다. 되돌릴 수 있는 이유가 이것이다. 정말 그런지 토픽을 하나 만들어 ZooKeeper를 봤다.

```bash
bin/kafka-topics.sh --bootstrap-server localhost:19092 --create --topic created-during-dual-write --partitions 3 --replication-factor 3
bin/zookeeper-shell.sh localhost:2181 ls /brokers/topics
# [__consumer_offsets, created-during-dual-write, orders]
```

KRaft 쪽에서 만든 토픽이 ZooKeeper에도 있다.

## 6. 되돌리기 표

| 마지막으로 끝낸 단계 | 되돌리는 법(3.9 문서 요약) |
|---|---|
| 컨트롤러 쿼럼 준비 | 컨트롤러를 내리면 끝 |
| 브로커 마이그레이션 모드(지금) | 컨트롤러를 내리고, ZooKeeper의 /controller와 /migration을 지운 뒤, 브로커에서 마이그레이션 설정을 빼고 롤링 재시작 |
| 브로커 KRaft 모드 | 브로커를 ZooKeeper 모드 설정으로 롤링, 위와 같은 정리 후 한 번 더 롤링 |
| 마무리(finalize) | 되돌릴 수 없음 |

/controller를 지우기 전에 ZooKeeper의 controller_epoch와 /migration의 kraft_controller_epoch를 비교해서, ZooKeeper 쪽이 더 크게 맞춰 두라는 주의도 붙어 있었다. 이관 중에 파티션 상태에 KRaft 쪽 에포크가 기록되기 때문이다.

| 이관 중 하지 말 것 | 이유 |
|---|---|
| metadata.version(inter.broker.protocol.version) 바꾸기 | 이관 중에는 지원하지 않는다. 클러스터가 깨질 수 있다 |
| 여러 로그 디렉터리(JBOD) 브로커의 디스크 장애 방치 | 이관 중에는 디렉터리 하나만 깨져도 브로커가 내려간다 |

운영은 이번 주 화요일에 여기까지 진행했다. 리허설과 같은 순서로 했고, 컨트롤러 3대가 뜬 뒤 브로커 3대를 30분 간격으로 롤링했다. 지금은 이중 쓰기 상태로 서비스가 정상인지 지켜보는 중이다.

> **쉬운 설명**
>
> 이 작업은 회사 회계 장부를 외부 회계사무소(ZooKeeper)에서 사내 회계팀(KRaft 컨트롤러)으로 옮기는 일이다. 먼저 사내 팀을 꾸리고(컨트롤러 쿼럼), 지점(브로커)마다 '이제 사내 팀에도 보고하라'고 알린다. 지점이 다 준비되면 사내 팀이 외부 장부를 한 번에 베껴 오고(메타데이터 이관), 그 뒤로는 새로 생긴 거래를 사내 장부와 외부 장부 양쪽에 같이 적는다(이중 쓰기). 양쪽에 다 적고 있으니, 문제가 생기면 외부 사무소로 다시 돌아갈 수 있다.

## 헷갈렸던 것들

- 컨트롤러를 새 클러스터 ID로 포맷하면 안 된다. 기존 ID여야 브로커들이 같은 클러스터로 인식한다.
- 브로커 마이그레이션 모드 단계에서는 브로커가 아직 ZooKeeper 모드다. KRaft 브로커로 바꾸는 건 다음 단계다.
- 컨트롤러가 WAIT_FOR_BROKERS에서 멈춰 있는 건 오류가 아니다. 모든 브로커가 붙을 때까지 기다리는 것이다.

## 용어 정리

| 용어 | 뜻 |
|---|---|
| 마이그레이션 모드 | zookeeper.metadata.migration.enable=true로 KRaft 컨트롤러와 통신할 준비를 한 상태 |
| 메타데이터 이관 | ZooKeeper의 토픽, 파티션, 설정을 KRaft 메타데이터 레코드로 옮기는 것 |
| 이중 쓰기(DUAL_WRITE) | KRaft 컨트롤러가 메타데이터를 ZooKeeper에도 함께 쓰는 상태 |
| /migration | ZooKeeper에 남는 이관 상태 znode |
| 마무리(finalize) | 컨트롤러에서 ZooKeeper 설정을 빼서 이중 쓰기를 끝내는 마지막 단계 |

## 참고 자료

- Apache Kafka 3.9 문서, ZooKeeper에서 KRaft로 이관: <https://kafka.apache.org/39/operations/kraft/>
- Apache Kafka 3.9.0 릴리스 발표: <https://kafka.apache.org/blog/2024/11/06/apache-kafka-3.9.0-release-announcement/>
- KIP-866, ZooKeeper에서 KRaft로 이관: <https://cwiki.apache.org/confluence/display/KAFKA/KIP-866+ZooKeeper+to+KRaft+Migration>

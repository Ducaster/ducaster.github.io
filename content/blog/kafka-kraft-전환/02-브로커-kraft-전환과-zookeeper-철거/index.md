---
title: '[Kafka 전환] 3.9.1 ZooKeeper 클러스터를 KRaft로 (2): 브로커를 KRaft로 바꾸고 ZooKeeper 걷어내기'
date: '2026-06-20T22:00:00+09:00'
categories:
- Kafka
tags:
- kafka
- kraft
- zookeeper
- migration
- finalize
- broker
- operations
- rollback
- 운영
series:
- Kafka KRaft 전환
series_order: 2
---

지난주에 컨트롤러 쿼럼을 붙이고 이중 쓰기 상태까지 왔다. 이번 주에는 브로커를 진짜 KRaft 브로커로 바꾸고, 컨트롤러에서 ZooKeeper 설정을 빼 마무리하고, ZooKeeper를 내렸다. 마무리하면 되돌릴 수 없어서, 브로커 전환과 마무리 사이에 며칠을 두고 지켜봤다. 이번에도 명령과 로그는 노트북 리허설 기록이다.

## 요약

- 브로커 설정에서 broker.id를 node.id로, zookeeper.connect와 마이그레이션 설정을 지우고 process.roles=broker를 넣어 한 대씩 재시작했다.
- 전환 뒤 토픽 끝 오프셋과 컨슈머 그룹 오프셋이 작업 전 기록과 한 자리도 다르지 않았다.
- 쿼럼을 보면 컨트롤러가 voter, 브로커 셋이 observer로 나온다. kraft.version이 0이라 정적 쿼럼이다.
- 마무리는 컨트롤러에서 zookeeper.metadata.migration.enable과 zookeeper.connect를 지우고 재시작하는 것뿐이다. 이 순간부터 ZooKeeper로 돌아갈 수 없다.
- 마무리 뒤 ZooKeeper를 내려도 토픽 생성, 소비, 오프셋 커밋이 정상이었다.

## 1. 브로커를 KRaft 모드로

```text
process.roles=broker
node.id=1
listeners=PLAINTEXT://:19092
advertised.listeners=PLAINTEXT://localhost:19092
listener.security.protocol.map=PLAINTEXT:PLAINTEXT,CONTROLLER:PLAINTEXT
controller.quorum.voters=3000@localhost:9093
controller.listener.names=CONTROLLER
log.dirs=/data/kafka/b1
default.replication.factor=3
min.insync.replicas=2
offsets.topic.replication.factor=3
```

| 바뀐 것 | 전 | 후 |
|---|---|---|
| 브로커 ID | broker.id=1 | node.id=1 (같은 번호) |
| 역할 | 없음(ZooKeeper 모드) | process.roles=broker |
| ZooKeeper | zookeeper.connect, migration.enable | 삭제 |
| IBP | inter.broker.protocol.version=3.9 | 삭제(KRaft에서는 metadata.version을 쓴다) |
| log.dirs | 그대로 | 그대로. 데이터는 손대지 않는다 |

node.id를 브로커 ID와 같은 번호로 둬야 기존 파티션 배치가 그대로 이어진다. 한 대씩 재시작하고 로그를 확인했다.

```text
INFO [KafkaRaftServer nodeId=1] Kafka Server started (kafka.server.KafkaRaftServer)
INFO [KafkaRaftServer nodeId=2] Kafka Server started (kafka.server.KafkaRaftServer)
INFO [KafkaRaftServer nodeId=3] Kafka Server started (kafka.server.KafkaRaftServer)
```

ZooKeeper 모드에서는 시작 로그가 KafkaServer started였는데, KafkaRaftServer로 바뀌었다.

## 2. 데이터와 오프셋 비교

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

지난 글의 작업 전 기록과 똑같다. 리더는 롤링 중에 몇 개 옮겨 가 있었다(1번 파티션 리더가 2에서 1로). 선호 리더 선출은 업그레이드까지 끝내고 한 번에 하기로 했다.

이제 KRaft 도구로 쿼럼을 볼 수 있다.

```text
ClusterId:              03uEjGEgRmybviSeUSD05A
LeaderId:               3000
LeaderEpoch:            1
HighWatermark:          1076
CurrentVoters:          [{"id": 3000, "directoryId": null, "endpoints": ["CONTROLLER://localhost:9093"]}]
CurrentObservers:       [{"id": 1, ...}, {"id": 2, ...}, {"id": 3, ...}]

Feature: kraft.version	SupportedMinVersion: 0	SupportedMaxVersion: 1	FinalizedVersionLevel: 0
Feature: metadata.version	SupportedMinVersion: 3.0-IV1	SupportedMaxVersion: 3.9-IV0	FinalizedVersionLevel: 3.9-IV0
```

ClusterId가 ZooKeeper 시절과 같다. kraft.version이 0이라 정적 쿼럼(controller.quorum.voters)이다. 컨트롤러의 directoryId가 null인 것도 정적 쿼럼이라 그렇다.

## 3. 며칠 지켜보기

브로커를 KRaft로 바꾼 뒤에도 마무리 전까지는 컨트롤러가 ZooKeeper에 계속 쓰고 있어서 되돌릴 수 있다. 문서에도 마무리 전에 1~2주 지켜보는 사람들이 있다고 적혀 있다. 운영에서는 화요일에 브로커를 바꾸고 금요일까지 지켜봤다. 본 것은 이렇다.

| 지표 | 기준 |
|---|---|
| 복제 부족 파티션 | 0 유지 |
| 주요 컨슈머 그룹 랙 | 평소 범위 |
| 프로듀서 오류율, 지연 | 평소 범위 |
| 컨트롤러 로그 | 이관 관련 ERROR 없음 |
| 토픽 생성, 설정 변경 | ZooKeeper에도 반영되는지 표본 확인 |

## 4. 마무리

컨트롤러 설정에서 ZooKeeper 관련 줄을 지웠다. zookeeper.metadata.migration.enable을 false로 바꾸는 게 아니라 줄 자체를 지운다.

```text
process.roles=controller
node.id=3000
controller.quorum.voters=3000@localhost:9093
controller.listener.names=CONTROLLER
listeners=CONTROLLER://:9093
listener.security.protocol.map=CONTROLLER:PLAINTEXT,PLAINTEXT:PLAINTEXT
log.dirs=/data/kafka/c3000
```

컨트롤러를 한 대씩 재시작했다. 운영처럼 컨트롤러가 셋이면 마지막 컨트롤러가 재시작될 때 마무리가 끝난다. 이 시점부터 ZooKeeper에는 아무것도 쓰지 않는다.

## 5. ZooKeeper 내리고 확인

리허설에서는 마무리 직후 ZooKeeper를 내리고 바로 확인했다.

```bash
lsof -nP -iTCP:2181 -sTCP:LISTEN | wc -l        # 0
bin/kafka-topics.sh --bootstrap-server $B --create --topic after-zk-removed --partitions 3 --replication-factor 3
# Created topic after-zk-removed.
bin/kafka-console-consumer.sh --bootstrap-server $B --topic orders --group billing --max-messages 3 | wc -l
# 3
bin/kafka-consumer-groups.sh --bootstrap-server $B --describe --group billing | head -4
```

```text
GROUP   TOPIC  PARTITION  CURRENT-OFFSET  LOG-END-OFFSET  LAG
billing orders 0          1404            1404            0
billing orders 1          103             2044            1941
```

billing 그룹이 1번 파티션의 커밋된 위치(100)부터 이어서 3건을 읽고 103을 커밋했다. 운영에서는 ZooKeeper를 바로 지우지 않고 프로세스만 멈춰 두었다. 다음 주 월요일까지 문제가 없으면 서버를 반납할 예정이다.

## 6. 정리한 체크리스트

{{< mermaid >}}
flowchart TB
  subgraph s1["되돌리기 가능"]
    direction LR
    A["브로커 KRaft 롤링"] --> B["오프셋, 랙 비교"]
    B --> C["며칠 관찰"]
  end
  subgraph s2["되돌리기 불가"]
    direction LR
    D["컨트롤러에서<br>ZK 설정 제거, 재시작<br>(마무리)"] --> F["ZooKeeper 정지<br>며칠 뒤 철거"]
  end
  s1 --> s2
{{< /mermaid >}}

| 하고 나서 놓칠 뻔한 것 | 내용 |
|---|---|
| 모니터링 | ZooKeeper 지표와 경보를 정리하고, 컨트롤러 쿼럼 지표(리더, 팔로워 랙)를 새로 걸었다 |
| 운영 스크립트 | --zookeeper를 쓰던 오래된 스크립트를 --bootstrap-server로 바꿨다 |
| 설정 관리 | 브로커 설정의 ZooKeeper 줄을 배포 템플릿에서도 지웠다. 안 그러면 다음 배포 때 되살아난다 |

> **쉬운 설명**
>
> 지난주가 '사내 장부와 외부 장부에 같이 적기'였다면, 이번 주는 지점(브로커)들도 사내 회계팀에만 보고하게 바꾸고, 며칠 동안 숫자가 맞는지 본 다음 외부 사무소와의 계약을 끝낸 것이다(마무리). 계약을 끝내면 외부 장부는 더 이상 갱신되지 않아서 돌아갈 수 없다. 그래서 끝내기 전에 며칠 지켜봤고, 사무소 문은 바로 부수지 않고 며칠 잠가 두었다가 정리했다.

## 헷갈렸던 것들

- 마무리는 별도 명령이 아니다. 컨트롤러 설정에서 ZooKeeper 줄을 지우고 재시작하는 것이 마무리다.
- 브로커를 KRaft로 바꿔도 마무리 전까지는 되돌릴 수 있다. 되돌릴 수 없게 되는 건 컨트롤러 마무리 뒤다.
- 정적 쿼럼으로 이관했기 때문에 kraft.version이 0이다. 3.9 문서는 정적 쿼럼을 동적으로 바꾸는 건 아직 안 된다고 했다.

## 용어 정리

| 용어 | 뜻 |
|---|---|
| node.id | KRaft에서 노드를 식별하는 번호. 브로커는 기존 broker.id와 같게 둔다 |
| observer | 메타데이터 로그를 받아 보기만 하는 노드(브로커) |
| 정적 쿼럼 | controller.quorum.voters로 컨트롤러 목록을 고정한 쿼럼. kraft.version=0 |
| 마무리(finalize) | 컨트롤러에서 이관 설정을 지워 이중 쓰기를 끝내는 것 |

## 참고 자료

- Apache Kafka 3.9 문서, ZooKeeper에서 KRaft로 이관(브로커 전환, 마무리, 되돌리기): <https://kafka.apache.org/39/operations/kraft/>
- KIP-866, ZooKeeper에서 KRaft로 이관: <https://cwiki.apache.org/confluence/display/KAFKA/KIP-866+ZooKeeper+to+KRaft+Migration>

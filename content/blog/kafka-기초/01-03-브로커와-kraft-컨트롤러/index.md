---
title: '[Kafka 기초] 브로커와 KRaft 컨트롤러: 노트북에 3노드 클러스터 띄우기'
date: '2025-11-08T21:00:00+09:00'
categories:
- Kafka
tags:
- kafka
- broker
- controller
- kraft
- raft
- quorum
- cluster-metadata
- metadata-version
- zookeeper
- 기본 개념
series:
- Kafka 기초
series_order: 4
---

지금까지는 노드 하나로만 했는데, 복제를 보려면 브로커가 여럿 있어야 한다. 그래서 노트북 한 대에 포트만 다르게 해서 노드 셋을 띄웠다. 그 과정에서 컨트롤러 쿼럼이 무엇이고, ZooKeeper가 하던 일을 KRaft가 어떻게 대신하는지 정리했다.

## 요약

- 브로커는 파티션 데이터를 맡고, 컨트롤러는 클러스터 메타데이터(토픽, 파티션 배치, 리더, 설정)를 맡는다.
- KRaft에서 컨트롤러들은 Raft 합의로 메타데이터를 __cluster_metadata라는 내부 로그에 쓴다. 과반이 살아 있어야 메타데이터를 바꿀 수 있다.
- 한 프로세스가 브로커와 컨트롤러를 같이 맡는 결합(combined) 모드와, 따로 두는 분리 모드가 있다. 운영에서는 분리 모드를 권한다.
- 컨트롤러 쿼럼을 정하는 방법은 정적(controller.quorum.voters)과 동적(controller.quorum.bootstrap.servers + --initial-controllers) 두 가지다.
- 클러스터가 쓰는 메타데이터 형식은 metadata.version으로 관리한다. 4.1.0에서 새로 만든 클러스터는 4.1-IV1이었다.

## 1. 브로커와 컨트롤러

{{< mermaid >}}
flowchart TB
  subgraph quorum["컨트롤러 쿼럼 (Raft)"]
    direction LR
    C1["컨트롤러 1<br>리더"] --> C2["컨트롤러 2"]
    C1 --> C3["컨트롤러 3"]
  end
  subgraph brokers["브로커"]
    direction LR
    B1["브로커 1"]
    B2["브로커 2"]
    B3["브로커 3"]
    B1 ~~~ B2 ~~~ B3
  end
  quorum -->|"__cluster_metadata 변경을<br>브로커가 받아 감"| brokers
{{< /mermaid >}}

| 구분 | 브로커 | 컨트롤러 |
|---|---|---|
| 맡는 것 | 파티션 데이터 저장, 클라이언트 요청 처리 | 토픽 생성, 파티션 배치, 리더 선출, 브로커 상태 관리 |
| 저장하는 로그 | 각 파티션의 로그 | __cluster_metadata (메타데이터 로그) |
| 몇 대 | 필요한 만큼 | 보통 3대나 5대(홀수) |

예전에는 이 메타데이터를 ZooKeeper라는 별도 시스템에 두고, 브로커 중 하나가 컨트롤러가 돼서 ZooKeeper를 보며 일했다. 시스템이 두 개라 운영할 것도 두 배였고, 파티션이 많으면 컨트롤러가 바뀔 때 ZooKeeper에서 메타데이터를 다시 읽느라 느렸다. KRaft는 메타데이터를 카프카 자신의 로그로 관리해서 이 문제를 없앴다.

## 2. 3노드 클러스터 띄우기

노드마다 설정 파일을 따로 만들었다. 노드 2의 설정이다.

```text
process.roles=broker,controller
node.id=2
listeners=PLAINTEXT://:29092,CONTROLLER://:29093
advertised.listeners=PLAINTEXT://localhost:29092,CONTROLLER://localhost:29093
controller.listener.names=CONTROLLER
inter.broker.listener.name=PLAINTEXT
listener.security.protocol.map=CONTROLLER:PLAINTEXT,PLAINTEXT:PLAINTEXT
controller.quorum.bootstrap.servers=localhost:19093,localhost:29093,localhost:39093
log.dirs=/Users/me/kafka-lab/c3/n2
num.partitions=3
default.replication.factor=3
min.insync.replicas=2
offsets.topic.replication.factor=3
transaction.state.log.replication.factor=3
transaction.state.log.min.isr=2
```

동적 쿼럼은 포맷할 때 처음 컨트롤러 목록을 --initial-controllers로 준다. 노드 ID, 주소, 디렉터리 ID를 묶은 값이고, 세 노드 모두 같은 값으로 포맷한다.

```bash
CID=$(bin/kafka-storage.sh random-uuid)
D1=$(bin/kafka-storage.sh random-uuid); D2=$(bin/kafka-storage.sh random-uuid); D3=$(bin/kafka-storage.sh random-uuid)
IC="1@localhost:19093:$D1,2@localhost:29093:$D2,3@localhost:39093:$D3"
for n in 1 2 3; do
  bin/kafka-storage.sh format --cluster-id $CID --initial-controllers "$IC" --config c3/server-$n.properties
done
# Formatting dynamic metadata voter directory .../c3/n1 with metadata.version 4.1-IV1.
```

세 노드를 각각 띄우고 쿼럼 상태를 봤다. 첫 노드가 떴을 때 다른 노드에 연결할 수 없다는 경고가 몇 줄 나오다가, 셋이 다 뜨자 조용해졌다.

```bash
bin/kafka-metadata-quorum.sh --bootstrap-server localhost:19092 describe --status
```

```text
ClusterId:              cAUfCDCYTpOT2tuokQIKzQ
LeaderId:               1
LeaderEpoch:            1
HighWatermark:          68
MaxFollowerLag:         0
MaxFollowerLagTimeMs:   0
CurrentVoters:          [{"id": 1, ..."endpoints": ["CONTROLLER://localhost:19093"]}, {"id": 2, ...}, {"id": 3, ...}]
CurrentObservers:       []
```

```bash
bin/kafka-metadata-quorum.sh --bootstrap-server localhost:19092 describe --replication
```

```text
NodeId	DirectoryId           	LogEndOffset	Lag	LastFetchTimestamp	LastCaughtUpTimestamp	Status  	
1     	kru3n6nPTUGRoKdyr-pNJw	70          	0  	…     	…        	Leader  	
2     	yKxwUUPiTcObpuYgfXkSTg	70          	0  	…     	…        	Follower	
3     	u1Jmm_XGS4C7CwSHbP-SHg	70          	0  	…     	…        	Follower	
```

노드 1이 메타데이터 로그의 리더고, 2와 3이 따라 쓰고 있다. LogEndOffset이 같으니 뒤처진 노드가 없다. 결합 모드라서 Observers가 비어 있다. 브로커 전용 노드가 있었다면 Observers에 나왔을 것이다.

## 3. 정적 쿼럼과 동적 쿼럼

| 방식 | 설정 | 특징 |
|---|---|---|
| 정적 | controller.quorum.voters=1@host1:9093,2@host2:9093,3@host3:9093 | 컨트롤러 목록이 설정 파일에 고정. 바꾸려면 전체 재시작 |
| 동적(3.9부터) | controller.quorum.bootstrap.servers + format --initial-controllers 또는 --standalone | 컨트롤러를 실행 중에 추가, 제거할 수 있다(kafka-metadata-quorum add-controller, remove-controller) |

빠른 시작 문서가 동적 방식을 기본으로 쓰고 있어서 나도 그렇게 했다. 정적인지 동적인지는 포맷할 때 정해지고, kafka-features describe의 kraft.version이 0이면 정적, 1이면 동적이다. 회사 클러스터처럼 ZooKeeper에서 넘어오는 경우는 따로 알아볼 게 많아서 나중에 본다.

## 4. 기능 버전

```bash
bin/kafka-features.sh --bootstrap-server localhost:9092 describe
```

```text
Feature: eligible.leader.replicas.version	SupportedMinVersion: 0	SupportedMaxVersion: 1	FinalizedVersionLevel: 1	Epoch: 259
Feature: group.version	SupportedMinVersion: 0	SupportedMaxVersion: 1	FinalizedVersionLevel: 1	Epoch: 259
Feature: kraft.version	SupportedMinVersion: 0	SupportedMaxVersion: 1	FinalizedVersionLevel: 1	Epoch: 259
Feature: metadata.version	SupportedMinVersion: 3.3-IV3	SupportedMaxVersion: 4.1-IV1	FinalizedVersionLevel: 4.1-IV1	Epoch: 259
Feature: share.version	SupportedMinVersion: 0	SupportedMaxVersion: 1	FinalizedVersionLevel: 0	Epoch: 259
Feature: transaction.version	SupportedMinVersion: 0	SupportedMaxVersion: 2	FinalizedVersionLevel: 2	Epoch: 259
```

Supported는 이 프로그램이 지원하는 범위, Finalized는 클러스터가 실제로 쓰고 있는 값이다. 업그레이드할 때는 프로그램을 먼저 다 올린 다음, 마지막에 이 값을 올려서 새 기능을 켠다고 한다. share.version이 0인 건 공유 그룹(미리보기)이 꺼져 있다는 뜻이다. kraft.version 1은 동적 쿼럼을 쓰고 있다는 뜻이다.

> **쉬운 설명**
>
> 브로커는 창고, 컨트롤러는 본사다. 창고는 물건(데이터)을 보관하고 내주는 일만 하고, 어느 창고에 무엇을 둘지, 어느 창고가 책임자인지는 본사가 정한다. 예전에는 본사 회의록을 외부 회계사무소(ZooKeeper)에 맡겼는데, KRaft에서는 본사 임원 셋이 회의록(__cluster_metadata)을 직접 나눠 쓰고, 셋 중 둘 이상이 동의해야 결정이 확정된다.

## 헷갈렸던 것들

- 컨트롤러 3대면 1대까지, 5대면 2대까지 죽어도 된다. 과반이 있어야 하므로 짝수는 이득이 없다.
- 결합 모드에서 노드 셋 중 둘이 죽으면 데이터 복제본이 남아 있어도 메타데이터를 바꿀 수 없다. 운영에서 분리 모드를 권하는 이유다.
- metadata.version은 카프카 프로그램 버전과 따로 움직인다. 프로그램을 올려도 이 값을 올리기 전까지는 예전 형식을 쓴다.

## 용어 정리

| 용어 | 뜻 |
|---|---|
| 컨트롤러 쿼럼 | 메타데이터 로그를 Raft로 함께 관리하는 컨트롤러 묶음 |
| __cluster_metadata | KRaft 메타데이터가 쓰이는 내부 로그 |
| voter, observer | 쿼럼 투표에 참여하는 컨트롤러와, 메타데이터를 받아 보기만 하는 브로커 |
| 결합 모드 | process.roles=broker,controller. 한 프로세스가 두 역할을 함 |
| metadata.version | 클러스터가 쓰는 메타데이터 형식 버전. kafka-features로 올린다 |

## 참고 자료

- Apache Kafka 문서, KRaft: <https://kafka.apache.org/41/operations/kraft/>
- KIP-500, ZooKeeper를 자체 관리 메타데이터 쿼럼으로 대체: <https://cwiki.apache.org/confluence/display/KAFKA/KIP-500%3A+Replace+ZooKeeper+with+a+Self-Managed+Metadata+Quorum>
- KIP-853, KRaft 컨트롤러 멤버십 변경: <https://cwiki.apache.org/confluence/display/KAFKA/KIP-853%3A+KRaft+Controller+Membership+Changes>

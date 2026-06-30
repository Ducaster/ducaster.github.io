---
title: '[Kafka 전환] 3.9.1 ZooKeeper 클러스터를 KRaft로 (3): 4.2.1로 올리고 min.insync.replicas가 1이 된 이야기'
date: '2026-06-30T22:00:00+09:00'
categories:
- Kafka
tags:
- kafka
- kafka-4.2
- upgrade
- metadata-version
- kafka-features
- elr
- min-insync-replicas
- operations
- retrospective
- 운영
series:
- Kafka KRaft 전환
series_order: 3
---

KRaft 전환을 마치고 마지막으로 4.2.1까지 올렸다. 4.2.1은 5월 30일에 나온 패치 버전이다. 바이너리 교체는 싱거웠는데, 메타데이터 버전을 올린 직후 토픽의 min.insync.replicas가 2에서 1로 바뀌어 보이는 걸 리허설에서 발견했다. 이유를 찾고 나서 운영에서는 미리 막았다. 이번 달 작업 회고도 같이 적는다.

## 요약

- 4.x로 올리려면 KRaft 모드여야 하고, 소프트웨어와 메타데이터 버전이 3.3 이상이어야 한다. 브로커와 도구는 자바 17 이상, 클라이언트는 2.1 이상이어야 한다.
- 순서는 브로커를 한 대씩 새 바이너리로 재시작 → 컨트롤러 재시작 → 동작 확인 → kafka-features.sh upgrade --release-version 4.2다.
- 메타데이터 버전을 올리면 ELR이 켜지면서 클러스터 수준 min.insync.replicas가 활성 컨트롤러의 정적 설정값으로 생기고, 브로커 수준 값은 지워진다. 컨트롤러 설정에 없으면 기본값 1이 된다.
- 리허설에서 orders 토픽이 min.insync.replicas=1로 보였다. 클러스터 기본값을 2로 다시 넣어 해결했고, 운영에서는 업그레이드 전에 컨트롤러 설정에도 넣었다.
- 4.2에서는 Queues for Kafka(공유 그룹)가 정식이 됐고, 콘솔 도구의 --property, --producer.config 같은 옵션은 지원 중단 표시가 붙었다.

## 1. 올리기 전에 확인한 것

4.2 업그레이드 문서와 4.0 변경 사항을 읽고 우리 환경에 해당하는 것만 골랐다.

| 항목 | 확인 결과 |
|---|---|
| KRaft 모드 | 지난주 마무리 완료 |
| metadata.version | 3.9-IV0(3.3 이상이면 됨) |
| 자바 | 브로커, 도구는 17 이상. 클라이언트, Streams는 11 이상 |
| 클라이언트 버전 | 4.0부터 2.1 미만 클라이언트는 안 된다. 브로커의 요청 버전별 지표로 오래된 프로토콜을 쓰는 클라이언트가 없는지 봤다 |
| 지워진 설정 | log.message.format.version, message.format.version. 우리 설정에는 없었다 |
| MirrorMaker 1 | 4.0에서 제거. MirrorMaker 2(Connect 기반)를 쓰고 있어서 해당 없음 |
| 로깅 | Log4j에서 Log4j2로. 커스텀 log4j.properties를 쓰던 서버는 변환이 필요 |
| 설정 파일 위치 | 4.0부터 config/kraft 디렉터리가 없어지고 config로 합쳐짐. 배포 스크립트 경로 수정 |

## 2. 롤링 업그레이드

설정 파일은 그대로 두고 바이너리만 4.2.1로 바꿔 한 대씩 재시작했다. 브로커 셋 다음에 컨트롤러 순서였다.

```text
INFO Kafka version: 4.2.1 (org.apache.kafka.common.utils.AppInfoParser)
INFO [KafkaRaftServer nodeId=1] Kafka Server started (kafka.server.KafkaRaftServer)
...
INFO Kafka version: 4.2.1 (org.apache.kafka.common.utils.AppInfoParser)
INFO [KafkaRaftServer nodeId=3000] Kafka Server started (kafka.server.KafkaRaftServer)
```

이 상태는 '프로그램은 4.2.1, 메타데이터 형식은 3.9'다. 되돌릴 일이 생기면 바이너리만 다시 바꾸면 된다.

```text
Feature: eligible.leader.replicas.version	SupportedMinVersion: 0	SupportedMaxVersion: 1	FinalizedVersionLevel: 0
Feature: group.version	SupportedMinVersion: 0	SupportedMaxVersion: 1	FinalizedVersionLevel: 0
Feature: kraft.version	SupportedMinVersion: 0	SupportedMaxVersion: 1	FinalizedVersionLevel: 0
Feature: metadata.version	SupportedMinVersion: 3.3-IV3	SupportedMaxVersion: 4.2-IV1	FinalizedVersionLevel: 3.9-IV0
Feature: share.version	SupportedMinVersion: 0	SupportedMaxVersion: 1	FinalizedVersionLevel: 0
Feature: streams.version	SupportedMinVersion: 0	SupportedMaxVersion: 1	FinalizedVersionLevel: 0
Feature: transaction.version	SupportedMinVersion: 0	SupportedMaxVersion: 2	FinalizedVersionLevel: 0
```

## 3. 메타데이터 버전 올리기

먼저 --dry-run으로 무엇이 바뀌는지 봤다.

```bash
bin/kafka-features.sh --bootstrap-server $B upgrade --release-version 4.2 --dry-run
```

```text
eligible.leader.replicas.version can be upgraded to 1.
group.version can be upgraded to 1.
kraft.version can be upgraded to 1.
metadata.version can be upgraded to 29.
share.version can be upgraded to 1.
streams.version can be upgraded to 1.
transaction.version can be upgraded to 2.
```

--release-version 4.2는 metadata.version만이 아니라 4.2 기본 기능 버전을 한꺼번에 올린다. ELR, 새 그룹 코디네이터 기능, 공유 그룹, Streams 그룹, 트랜잭션 버전 2까지 같이 켜진다. 문서에 따르면 메타데이터 변경이 있는 버전 사이에서는 메타데이터 버전 다운그레이드가 안 되니, 여기가 실제로 되돌릴 수 없는 지점이다.

```bash
bin/kafka-features.sh --bootstrap-server $B upgrade --release-version 4.2
```

```text
eligible.leader.replicas.version was upgraded to 1.
group.version was upgraded to 1.
kraft.version was upgraded to 1.
metadata.version was upgraded to 29.
share.version was upgraded to 1.
streams.version was upgraded to 1.
transaction.version was upgraded to 2.
```

kraft.version도 1이 됐다. 3.9 문서에는 정적 쿼럼을 동적으로 바꿀 수 없다고 적혀 있었는데, 4.2에서는 기능 버전 업그레이드로 넘어갔다. 컨트롤러를 나중에 add-controller로 늘릴 수 있는지는 따로 확인할 생각이다.

## 4. min.insync.replicas가 1이 됐다

업그레이드 후 토픽을 확인하다가 이상한 걸 봤다.

```text
# 업그레이드 전
Topic: orders	...	ReplicationFactor: 3	Configs: min.insync.replicas=2
# 업그레이드 후
Topic: orders	...	ReplicationFactor: 3	Configs: min.insync.replicas=1
```

브로커 설정 파일에는 분명히 min.insync.replicas=2가 있다. 클러스터 기본 설정을 보니 1이 동적으로 들어가 있었다.

```bash
bin/kafka-configs.sh --bootstrap-server $B --describe --entity-type brokers --entity-default
# Default configs for brokers in the cluster are:
#   min.insync.replicas=1 sensitive=false synonyms={DYNAMIC_DEFAULT_BROKER_CONFIG:min.insync.replicas=1}
```

이유는 ELR 문서에 있었다. ELR이 켜지면 클러스터 수준 min.insync.replicas가 없을 때 새로 만들어지는데, 그 값은 활성 컨트롤러의 정적 설정을 따른다. 그리고 그전에 브로커 수준으로 설정한 값은 지워진다. 우리 컨트롤러 설정에는 min.insync.replicas가 없었으니 기본값 1이 들어간 것이다. 4.2 업그레이드 문서의 4.0 변경 사항에도 같은 문장이 있었는데 처음 읽을 때 놓쳤다.

복제 계수 3에 min.insync.replicas 1이면, acks=all이어도 리더 혼자 받은 데이터를 성공으로 처리할 수 있다. 조용히 안전장치가 하나 빠지는 셈이라 바로 고쳤다.

```bash
bin/kafka-configs.sh --bootstrap-server $B --alter --entity-type brokers --entity-default --add-config min.insync.replicas=2
bin/kafka-topics.sh --bootstrap-server $B --describe --topic orders | head -1
# Topic: orders	...	ReplicationFactor: 3	Configs: min.insync.replicas=2
```

운영에서는 순서를 바꿨다. 업그레이드 전에 컨트롤러 3대의 설정에 min.insync.replicas=2를 넣고 재시작해 둔 다음 기능 버전을 올렸고, 올린 직후 클러스터 기본값이 2인지 확인했다. 토픽 단위로 따로 준 값은 영향이 없다. ELR이 켜진 뒤에는 브로커 수준 min.insync.replicas를 바꾸는 게 막히고 클러스터 수준으로만 바꿀 수 있다는 것도 운영 문서에 적어 뒀다.

## 5. 마무리 작업

```bash
bin/kafka-leader-election.sh --bootstrap-server $B --election-type preferred --all-topic-partitions
```

롤링 동안 옮겨 간 리더를 선호 리더로 되돌렸다. 오프셋과 컨슈머 그룹은 4.2.1에서도 그대로였다. 바뀐 도구 옵션도 정리했다.

| 도구 | 지원 중단 표시 | 대신 쓸 것 |
|---|---|---|
| 콘솔 프로듀서 | --property, --producer-property, --producer.config | --reader-property, --command-config |
| 콘솔 컨슈머 | --property, --consumer-property, --consumer.config | --formatter-property, --command-config |
| 콘솔 프로듀서 | --max-partition-memory-bytes | --batch-size |

4.2.1의 --help에서 직접 확인한 내용이다. 당장 동작은 하지만 운영 스크립트는 새 옵션으로 바꿔 두었다.

## 6. 이번 달 회고

{{< mermaid >}}
flowchart LR
  A["6월 1주<br>노트북 리허설"] --> B["6월 2주<br>컨트롤러 쿼럼<br>브로커 이관 모드"]
  B --> C["6월 3주<br>브로커 KRaft<br>마무리, ZK 정지"]
  C --> D["6월 4주<br>4.2.1 롤링<br>기능 버전 업그레이드"]
{{< /mermaid >}}

| 잘한 것 | 아쉬운 것 |
|---|---|
| 노트북 리허설로 로그 모양과 순서를 미리 익혔다 | 리허설은 컨트롤러 1대라 쿼럼 리더 교체는 운영에서 처음 봤다 |
| 단계마다 오프셋, 랙 기록을 남겨 비교가 쉬웠다 | 업그레이드 문서의 ELR 문장을 처음엔 놓쳤다 |
| 마무리 전에 며칠을 두고 지켜봤다 | 배포 템플릿의 ZooKeeper 설정을 늦게 지웠다 |

min.insync.replicas 건은 리허설이 없었으면 운영에서 한참 뒤에야 알았을 것이다. 다음 업그레이드부터는 기능 버전을 올린 직후 kafka-configs --entity-default와 주요 토픽 describe를 체크리스트에 넣었다.

> **쉬운 설명**
>
> 사내 회계팀으로 옮긴 뒤 회계 프로그램도 새 버전으로 바꿨다. 프로그램만 바꿀 때는 예전 장부 양식을 그대로 써서 문제가 없었는데, '새 양식으로 전환' 버튼(기능 버전 업그레이드)을 누르자 결재 규칙이 회계팀장 책상(컨트롤러 설정)에 적힌 대로 다시 정해졌다. 팀장 책상에는 규칙이 없었으니 기본값 '한 명만 결재해도 됨'이 들어갔다. 원래는 두 명 결재였다. 그래서 운영에서는 버튼을 누르기 전에 팀장 책상에 '두 명 결재'를 먼저 적어 두었다.

## 헷갈렸던 것들

- 바이너리 업그레이드와 기능 버전 업그레이드는 따로다. 되돌리기 어려워지는 건 기능 버전을 올린 뒤다.
- --release-version은 여러 기능 버전을 한 번에 올린다. 하나씩 올리고 싶으면 --feature로 따로 준다.
- ELR이 켜지면 min.insync.replicas는 클러스터 수준과 토픽 수준에서만 관리한다.

## 용어 정리

| 용어 | 뜻 |
|---|---|
| 롤링 업그레이드 | 노드를 한 대씩 새 버전으로 재시작해 서비스 중단 없이 올리는 것 |
| 기능 버전(feature level) | 클러스터가 실제로 쓰는 기능 단계. kafka-features로 올린다 |
| --release-version | 특정 릴리스의 기본 기능 버전들을 한 번에 지정하는 옵션 |
| 클러스터 수준 설정 | --entity-default로 주는 모든 브로커 공통 동적 설정 |
| ELR | 데이터 유실 없이 리더가 될 수 있는 ISR 밖 복제본 목록(KIP-966) |

## 참고 자료

- Apache Kafka 4.2 업그레이드 문서: <https://kafka.apache.org/42/getting-started/upgrade/>
- Apache Kafka 4.2.1 릴리스 발표: <https://kafka.apache.org/blog/2026/05/30/apache-kafka-4.2.1-release-announcement/>
- Apache Kafka 4.2 문서, Eligible Leader Replicas: <https://kafka.apache.org/42/operations/eligible-leader-replicas/>
- KIP-896, 오래된 클라이언트 프로토콜 버전 제거: <https://cwiki.apache.org/confluence/display/KAFKA/KIP-896%3A+Remove+old+client+protocol+API+versions+in+Kafka+4.0>

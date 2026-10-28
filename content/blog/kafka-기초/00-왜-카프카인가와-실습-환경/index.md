---
title: '[Kafka 기초] 왜 카프카인가, 그리고 노트북에 KRaft 단일 노드 띄우기'
date: '2025-10-11T21:00:00+09:00'
categories:
- Kafka
tags:
- kafka
- event-streaming
- kraft
- kafka-4.1
- quickstart
- java
- 시작
series:
- Kafka 기초
series_order: 1
---

카프카를 처음부터 공부하기로 했다. 회사에서 카프카 클러스터를 같이 보게 될 것 같은데, 토픽이나 컨슈머 그룹 같은 말을 들어는 봤어도 제대로 설명할 수 있는 게 없었다. 회사 클러스터는 3.9 버전이지만, 공부는 지금 최신인 4.1.0으로 한다. 4.0부터 ZooKeeper가 완전히 빠져서, 앞으로 볼 문서도 다 KRaft 기준이기 때문이다.

## 요약

- 카프카는 이벤트를 받아서 디스크에 순서대로 쌓아 두고, 여러 시스템이 각자 원하는 위치부터 읽어 가게 해 주는 분산 로그다.
- 보내는 쪽(프로듀서)과 받는 쪽(컨슈머)이 서로를 몰라도 된다. 둘 사이에 카프카만 있으면 된다.
- 메시지 큐와 달리 읽어도 지워지지 않는다. 보존 기간 동안 남아 있어서 여러 팀이 같은 데이터를 따로 읽을 수 있다.
- 4.0(2025년 3월)부터 ZooKeeper 모드가 없어지고 KRaft만 남았다. 4.1.0은 2025년 9월에 나왔다.
- 실습은 공식 바이너리와 자바 17 이상으로 한다. 저장소를 포맷하고 서버를 켜면 노트북 하나에서 단일 노드 클러스터가 뜬다.

## 1. 왜 카프카인가

카프카 없이 시스템 여러 개를 연결하면 이렇게 된다. 주문 서비스가 결제, 배송, 알림, 분석 서비스에 각각 데이터를 보내야 하고, 서비스가 하나 늘 때마다 연결도 늘어난다.

{{< mermaid >}}
flowchart TB
  subgraph before["직접 연결"]
    direction LR
    O1["주문"] --> P1["결제"]
    O1 --> S1["배송"]
    O1 --> N1["알림"]
    O1 --> A1["분석"]
    P1 --> A1
    S1 --> A1
  end
  subgraph after["카프카를 가운데에"]
    direction LR
    O2["주문"] --> K["카프카<br>orders 토픽"]
    P2["결제"] --> K
    K --> S2["배송"]
    K --> N2["알림"]
    K --> A2["분석"]
  end
  before ~~~ after
{{< /mermaid >}}

카프카를 가운데 두면 주문 서비스는 '주문이 생겼다'는 이벤트를 한 번만 쓴다. 누가 읽는지는 신경 쓰지 않는다. 배송, 알림, 분석은 각자 필요할 때 읽는다. 분석 서비스가 하루 멈췄다가 다시 켜져도, 카프카에 쌓여 있는 이벤트를 멈춘 지점부터 다시 읽으면 된다.

| 쓰임새 | 예 |
|---|---|
| 서비스 사이 이벤트 전달 | 주문 생성, 결제 완료 같은 이벤트를 여러 서비스가 구독 |
| 로그, 지표 모으기 | 서버 수백 대의 로그를 한곳으로 모아 저장소나 검색 엔진으로 넘김 |
| 데이터 파이프라인 | DB 변경 내역(CDC)을 읽어 다른 저장소로 옮김 |
| 스트림 처리 | 들어오는 이벤트를 실시간으로 집계, 변환 |

## 2. 버전 정리

공부하면서 헷갈리지 않게 버전부터 정리했다.

| 버전 | 시기 | 내용 |
|---|---|---|
| 2.8 | 2021 | ZooKeeper 없이 도는 KRaft 모드가 처음 들어옴(미리보기) |
| 3.3 | 2022 | KRaft가 운영에 써도 되는 수준이 됨 |
| 3.9 | 2024-11 | ZooKeeper 모드를 쓸 수 있는 마지막 마이너 버전 |
| 4.0 | 2025-03 | ZooKeeper 모드 제거. 새 컨슈머 리밸런스 프로토콜 GA |
| 4.1 | 2025-09 | Queues for Kafka(공유 그룹) 미리보기 |

회사 클러스터가 3.9라는 건, 언젠가 4.x로 가려면 KRaft로 먼저 옮겨야 한다는 뜻이다. 그건 나중 일이고, 지금은 개념부터 잡는다.

## 3. 실습 환경

도커 없이 공식 바이너리로 했다. 자바만 있으면 되고, 설정 파일을 직접 보면서 하는 게 공부에 나을 것 같았다. 4.0부터 브로커와 도구는 자바 17 이상, 클라이언트는 자바 11 이상이 필요하다. 나는 Homebrew openjdk를 썼다.

```bash
curl -O https://archive.apache.org/dist/kafka/4.1.0/kafka_2.13-4.1.0.tgz
curl -O https://archive.apache.org/dist/kafka/4.1.0/kafka_2.13-4.1.0.tgz.sha512
shasum -a 512 kafka_2.13-4.1.0.tgz       # .sha512 파일 값과 같은지 본다
tar xzf kafka_2.13-4.1.0.tgz && cd kafka_2.13-4.1.0
```

파일 이름의 2.13은 스칼라 버전이고, 4.1.0이 카프카 버전이다. 단일 노드 설정은 config/server.properties에 이미 들어 있다. 핵심 줄만 뽑아 봤다.

```text
process.roles=broker,controller
node.id=1
controller.quorum.bootstrap.servers=localhost:9093
listeners=PLAINTEXT://:9092,CONTROLLER://:9093
advertised.listeners=PLAINTEXT://localhost:9092,CONTROLLER://localhost:9093
log.dirs=/tmp/kraft-combined-logs
```

한 프로세스가 브로커(데이터 담당)와 컨트롤러(메타데이터 담당)를 같이 맡는 구성이다. 9092는 클라이언트용, 9093은 컨트롤러끼리 쓰는 포트다. 실행은 두 단계다.

```bash
KAFKA_CLUSTER_ID="$(bin/kafka-storage.sh random-uuid)"
bin/kafka-storage.sh format --standalone -t $KAFKA_CLUSTER_ID -c config/server.properties
# Formatting dynamic metadata voter directory /tmp/kraft-combined-logs with metadata.version 4.1-IV1.
bin/kafka-server-start.sh config/server.properties
# ... INFO [KafkaRaftServer nodeId=1] Kafka Server started
```

처음에 format 없이 바로 start를 했다가 '저장소가 포맷되지 않았다'는 오류를 봤다. KRaft에서는 데이터 디렉터리마다 클러스터 ID를 먼저 써 넣어야 한다. --standalone은 '컨트롤러가 나 하나뿐인 쿼럼'으로 포맷하라는 뜻이다.

```bash
bin/kafka-topics.sh --bootstrap-server localhost:9092 --list    # 아무것도 없으면 정상
```

복제나 장애 실습은 노트북에서 노드 셋을 따로 띄워서 한다. 포트만 다르게 주면 한 대에서도 된다.

> **쉬운 설명**
>
> 카프카는 동네 게시판 같다. 가게(프로듀서)는 공지를 게시판에 붙이기만 하고, 누가 읽는지는 모른다. 주민(컨슈머)은 필요할 때 와서 자기가 마지막으로 본 공지 다음부터 읽는다. 공지는 읽었다고 떼어 가지 않고 정해진 기간 동안 붙어 있어서, 늦게 온 주민도 지난 공지를 볼 수 있다. KRaft는 게시판 관리 대장을 외부 관리사무소(ZooKeeper)에 맡기지 않고 게시판 관리인들이 직접 쓰는 방식이다.

## 헷갈렸던 것들

- 카프카 버전과 스칼라 버전이 파일 이름에 같이 붙는다. kafka_2.13-4.1.0에서 카프카는 4.1.0이다.
- KRaft는 따로 설치하는 게 아니라 카프카 안에 있는 기능이다. ZooKeeper 대신 카프카 프로세스(컨트롤러)가 메타데이터를 관리한다.
- format은 처음 한 번만 한다. 이미 데이터가 있는 디렉터리를 다시 포맷하려고 하면 막힌다.

## 용어 정리

| 용어 | 뜻 |
|---|---|
| 이벤트(레코드) | 카프카에 쓰는 데이터 한 건. 키, 값, 타임스탬프, 헤더로 이뤄진다 |
| 프로듀서 | 이벤트를 쓰는 쪽 |
| 컨슈머 | 이벤트를 읽는 쪽 |
| 브로커 | 이벤트를 저장하고 읽기, 쓰기 요청을 처리하는 서버 |
| 컨트롤러 | 토픽, 파티션 배치 같은 클러스터 메타데이터를 관리하는 역할 |
| KRaft | ZooKeeper 없이 카프카 컨트롤러가 Raft 합의로 메타데이터를 관리하는 방식 |

## 복습 문제

**1.** 단일 노드 KRaft 설정에서 9092와 9093 포트는 각각 무엇에 쓰이는가?

**2.** 다운로드한 tgz 파일이 진짜인지 확인하는 명령을 적어라.

**3.** kafka-server-start.sh를 format 없이 처음 실행하면 왜 실패하는가?

## 답과 풀이

1. 9092는 PLAINTEXT 리스너로 프로듀서, 컨슈머, 관리 도구가 붙는 포트다. 9093은 CONTROLLER 리스너로 컨트롤러 쿼럼 통신에 쓴다. listeners와 controller.listener.names 설정에서 확인할 수 있다.

2. 배포 사이트의 .sha512 값과 직접 계산한 값을 비교한다.

```bash
shasum -a 512 kafka_2.13-4.1.0.tgz
cat kafka_2.13-4.1.0.tgz.sha512
```

3. KRaft 노드는 log.dirs에 클러스터 ID와 메타데이터 버전이 적힌 meta.properties가 있어야 시작한다. 그걸 만드는 게 kafka-storage.sh format이다.

## 참고 자료

- Apache Kafka 빠른 시작: <https://kafka.apache.org/41/getting-started/quickstart/>
- Apache Kafka 4.1.0 릴리스 발표: <https://kafka.apache.org/blog/2025/09/04/apache-kafka-4.1.0-release-announcement/>
- Apache Kafka 4.0.0 릴리스 발표: <https://kafka.apache.org/blog/2025/03/18/apache-kafka-4.0.0-release-announcement/>
- Apache Kafka 다운로드: <https://kafka.apache.org/downloads>

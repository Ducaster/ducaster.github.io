---
title: '[Kafka 기초] Kafka Connect: 코드 없이 파일을 토픽으로, 토픽을 파일로'
date: '2026-01-31T21:00:00+09:00'
categories:
- Kafka
tags:
- kafka
- kafka-connect
- source-connector
- sink-connector
- converter
- standalone
- distributed
- rest-api
- filestream
- 생태계
series:
- Kafka 기초
series_order: 12
---

외부 시스템과 카프카 사이에 데이터를 옮기는 일을 매번 프로듀서, 컨슈머 코드로 짜지 않게 해 주는 게 Kafka Connect다. 아파치 카프카에 같이 들어 있는 파일 커넥터로 CSV 파일을 토픽에 넣고, 토픽을 다시 파일로 빼 보며 구조를 익혔다.

## 요약

- Connect는 커넥터 설정만으로 외부 시스템 ↔ 카프카 데이터를 옮기는 프레임워크다. 소스 커넥터는 카프카로 넣고, 싱크 커넥터는 카프카에서 뺀다.
- 실행 모드는 단독(standalone)과 분산(distributed) 두 가지다. 단독은 오프셋을 파일에, 분산은 카프카 내부 토픽에 저장한다.
- 컨버터가 카프카에 들어갈 바이트 형식을 정한다. JsonConverter에 schemas.enable=true면 메시지마다 스키마가 붙는다.
- 실행 중인 커넥터는 REST API(기본 8083 포트)로 상태를 보고 관리한다.
- 파일 커넥터는 기본 클래스패스에 없어서 plugin.path에 connect-file jar를 지정해야 했다.

## 1. 구조

{{< mermaid >}}
flowchart LR
  F["orders.csv"] --> SC["소스 커넥터<br>FileStreamSource"]
  SC --> CV1["컨버터<br>JsonConverter"]
  CV1 --> T["orders-raw 토픽"]
  T --> CV2["컨버터"]
  CV2 --> SK["싱크 커넥터<br>FileStreamSink"]
  SK --> F2["orders-copy.txt"]
  subgraph worker["Connect 워커 (REST :8083)"]
    SC
    CV1
    CV2
    SK
  end
{{< /mermaid >}}

| 구성 요소 | 하는 일 |
|---|---|
| 워커 | 커넥터와 태스크를 실행하는 프로세스 |
| 커넥터 | 어디서 어디로 옮길지 정의하고 일을 태스크로 나눈다 |
| 태스크 | 실제로 데이터를 옮기는 단위 |
| 컨버터 | Connect 내부 데이터 ↔ 카프카 바이트 변환 |
| SMT | 레코드 하나씩 가볍게 바꾸는 변환(필드 이름 바꾸기, 마스킹 등) |

## 2. 단독 모드로 띄우기

워커 설정이다. 3노드 실습 클러스터에 붙였다.

```text
bootstrap.servers=localhost:19092,localhost:29092
key.converter=org.apache.kafka.connect.json.JsonConverter
value.converter=org.apache.kafka.connect.json.JsonConverter
key.converter.schemas.enable=true
value.converter.schemas.enable=true
offset.storage.file.filename=/Users/me/kafka-lab/connect/connect.offsets
offset.flush.interval.ms=10000
plugin.path=/Users/me/kafka-lab/kafka_2.13-4.1.0/libs/connect-file-4.1.0.jar
```

빠른 시작 문서에도 plugin.path에 connect-file jar를 넣으라는 단계가 있다. 이걸 빼면 FileStreamSource 클래스를 못 찾는다. 커넥터 설정은 짧다.

```text
# orders-source.properties
name=orders-file-source
connector.class=FileStreamSource
tasks.max=1
file=/Users/me/kafka-lab/connect/orders.csv
topic=orders-raw

# orders-sink.properties
name=orders-file-sink
connector.class=FileStreamSink
tasks.max=1
file=/Users/me/kafka-lab/connect/orders-copy.txt
topics=orders-raw
```

```bash
bin/connect-standalone.sh worker.properties orders-source.properties orders-sink.properties
```

## 3. 결과 확인

orders.csv에 세 줄을 넣어 두고 띄운 뒤 토픽을 읽었다.

```text
null	{"schema":{"type":"string","optional":false},"payload":"1001,user-1,서울,32000"}
null	{"schema":{"type":"string","optional":false},"payload":"1002,user-2,부산,15000"}
null	{"schema":{"type":"string","optional":false},"payload":"1003,user-1,서울,8000"}
```

파일 커넥터는 한 줄을 문자열 하나로 보내고, 키는 없다(null). JsonConverter가 스키마와 값을 감싸서 넣었다. 지난 글에서 말한 '메시지마다 스키마가 붙는' 모습이 이것이다.

REST API로 상태를 봤다.

```bash
curl -s localhost:8083/connectors
# ["orders-file-source","orders-file-sink"]
curl -s localhost:8083/connectors/orders-file-source/status
# {"name":"orders-file-source","connector":{"state":"RUNNING","worker_id":"127.0.0.1:8083","version":"4.1.0"},
#  "tasks":[{"id":0,"state":"RUNNING","worker_id":"127.0.0.1:8083","version":"4.1.0"}],"type":"source"}
```

파일에 한 줄을 더 붙이자 몇 초 안에 싱크 파일에도 생겼다.

```bash
echo '1004,user-3,광주,21000' >> orders.csv
cat orders-copy.txt
# 1001,user-1,서울,32000
# 1002,user-2,부산,15000
# 1003,user-1,서울,8000
# 1004,user-3,광주,21000
```

싱크 쪽은 결국 컨슈머라서, 그룹 목록에 connect-orders-file-sink라는 그룹이 생겨 있었다. 소스 쪽이 '파일 어디까지 읽었나'를 기억하는 곳은 오프셋 파일이고, 열어 보니 파일 이름을 키로 위치를 저장하고 있었다.

```text
["orders-file-source",{"filename":"/Users/me/kafka-lab/connect/orders.csv"}]
```

## 4. 단독 모드와 분산 모드

| 비교 | 단독(standalone) | 분산(distributed) |
|---|---|---|
| 워커 수 | 1개 | 여러 개가 한 그룹 |
| 커넥터 설정 | 실행 인자로 주는 파일 | REST API로 등록 |
| 오프셋, 설정, 상태 저장 | 로컬 파일 | 카프카 내부 토픽(config, offset, status 토픽) |
| 장애 | 워커가 죽으면 멈춤 | 다른 워커가 태스크를 이어받음 |
| 쓰임 | 개발, 테스트, 에이전트처럼 한 대에서 | 운영 |

실제 운영에서는 JDBC, Debezium(CDC), S3, Elasticsearch 같은 커넥터를 분산 모드로 띄워 쓴다. 파일 커넥터는 예제용이라 운영에서 쓰지 말라고 문서에 적혀 있다.

> **쉬운 설명**
>
> Connect는 택배 회사의 집하 기사와 배송 기사다. 소스 커넥터는 고객 집(파일, DB)에 가서 짐을 받아 물류 센터(카프카)에 넣고, 싱크 커넥터는 물류 센터에서 짐을 꺼내 다른 집(파일, 검색 엔진)에 배달한다. 짐 포장 방식(컨버터)은 회사 규칙으로 정해져 있고, 기사들이 어디까지 받아 왔는지는 장부(오프셋)에 적어 두어서 다음 날 이어서 일한다.

## 헷갈렸던 것들

- 컨버터는 커넥터가 아니라 워커 설정에 둔다(커넥터별로 덮어쓸 수는 있다).
- 싱크 커넥터는 내부적으로 컨슈머 그룹을 쓴다. 그룹 이름은 connect-커넥터이름이다.
- 단독 모드는 REST API가 있어도 커넥터를 등록하는 주 경로가 실행 인자다.

## 용어 정리

| 용어 | 뜻 |
|---|---|
| 소스 커넥터 | 외부 → 카프카로 데이터를 넣는 커넥터 |
| 싱크 커넥터 | 카프카 → 외부로 데이터를 빼는 커넥터 |
| 컨버터 | Connect 레코드와 카프카 바이트 사이 변환기 |
| plugin.path | 커넥터, 컨버터 플러그인 jar를 찾는 경로 |
| SMT | 단일 메시지 변환. 레코드를 하나씩 바꾸는 간단한 변환 |

## 복습 문제

**1.** 컨버터를 StringConverter로 바꾸면 orders-raw에 들어가는 값은 어떻게 달라지는가?

**2.** 싱크 커넥터가 어디까지 읽었는지 확인하는 방법을 적어라.

**3.** 단독 모드 워커가 죽었다 살아났을 때 파일을 처음부터 다시 읽지 않는 이유는?

## 답과 풀이

1. JSON 봉투 없이 1001,user-1,서울,32000 같은 문자열이 그대로 들어간다(value.converter=org.apache.kafka.connect.storage.StringConverter).

2. 싱크 커넥터의 컨슈머 그룹을 본다.

```bash
bin/kafka-consumer-groups.sh --bootstrap-server localhost:19092 --describe --group connect-orders-file-sink
```

3. 소스 오프셋(파일 이름별 위치)을 offset.storage.file.filename에 저장해 두고, 다시 시작할 때 거기서부터 읽기 때문이다.

## 참고 자료

- Apache Kafka 문서, Kafka Connect 사용자 가이드: <https://kafka.apache.org/41/kafka-connect/user-guide/>
- Apache Kafka 문서, 빠른 시작(Connect 단계): <https://kafka.apache.org/41/getting-started/quickstart/>
- Apache Kafka 문서, Connect 설정: <https://kafka.apache.org/41/configuration/kafka-connect-configs/>

---
title: '[Kafka 기초] 로그 세그먼트, 보존, 컴팩션: 디스크에서 직접 들여다보기'
date: '2026-01-03T21:00:00+09:00'
categories:
- Kafka
tags:
- kafka
- log-segment
- retention
- cleanup-policy
- log-compaction
- tombstone
- kafka-dump-log
- kafka-configs
- 저장과 운영
series:
- Kafka 기초
series_order: 9
---

지금까지는 '파티션은 로그 파일'이라고만 적었는데, 실제로 디스크에 어떤 파일이 생기는지 열어 봤다. 보존 기간을 바꾸는 법, 같은 키의 마지막 값만 남기는 로그 컴팩션도 실습했다.

## 요약

- 파티션 디렉터리 안에는 세그먼트 단위로 .log(데이터), .index(오프셋 → 위치), .timeindex(시간 → 오프셋) 파일이 생긴다.
- 지우는 단위는 레코드가 아니라 세그먼트다. 기본 세그먼트 크기는 1GiB(log.segment.bytes), 기본 보존 기간은 168시간(7일)이다.
- cleanup.policy=delete는 오래된 세그먼트를 통째로 지우고, compact는 키마다 마지막 값만 남긴다.
- 컴팩션 뒤에도 오프셋 번호는 그대로다. 지워진 오프셋은 건너뛰고 읽힌다.
- __consumer_offsets도 compact 토픽이다. 그룹, 파티션별 마지막 커밋만 있으면 되니까.

## 1. 파티션 디렉터리 열어 보기

```bash
ls -la /tmp/kraft-combined-logs/orders-2
```

```text
-rw-r--r--  1 me  wheel  10485760 Oct 28 13:13 00000000000000000000.index
-rw-r--r--  1 me  wheel       247 Oct 28 13:13 00000000000000000000.log
-rw-r--r--  1 me  wheel  10485756 Oct 28 13:13 00000000000000000000.timeindex
-rw-r--r--  1 me  wheel         8 Oct 28 13:13 leader-epoch-checkpoint
-rw-r--r--  1 me  wheel        43 Oct 28 13:13 partition.metadata
```

파일 이름 00000000000000000000은 이 세그먼트의 첫 오프셋이다. 레코드 6건이라 .log는 247바이트뿐인데, .index와 .timeindex는 10MiB로 미리 잡혀 있다. 세그먼트가 닫히면 실제 크기로 줄어든다고 한다.

{{< mermaid >}}
flowchart LR
  subgraph part["orders-2 파티션"]
    direction LR
    S1["세그먼트 0<br>00000...000.log<br>(닫힘)"] --> S2["세그먼트 1000<br>00000...1000.log<br>(닫힘)"] --> S3["세그먼트 2000<br>00000...2000.log<br>(활성: 여기에만 추가)"]
  end
  R["보존 정책"] -.->|"오래된 닫힌 세그먼트부터<br>통째로 삭제"| S1
{{< /mermaid >}}

kafka-dump-log로 .log 안을 보면 배치 단위로 묶여 있다.

```text
baseOffset: 0 lastOffset: 5 count: 6 ... producerId: 0 ... CreateTime: … size: 247 magic: 2 compresscodec: none ...
| offset: 0 CreateTime: … keySize: 6 valueSize: 18 sequence: 0 headerKeys: [] key: user-1 payload: 주문 생성 1001
```

콘솔 프로듀서로 한 번에 보낸 6건이 배치 하나로 들어갔다. valueSize가 18인 건 '주문 생성 1001'이 UTF-8로 18바이트라서다(한글 한 글자가 3바이트).

## 2. 보존 기간 바꾸기

실습 브로커의 기본값부터 확인했다.

```text
log.cleanup.policy=delete
log.retention.hours=168
log.retention.bytes=-1
log.segment.bytes=1073741824
log.cleaner.enable=true
```

토픽 단위로 덮어쓰려면 kafka-configs를 쓴다.

```bash
bin/kafka-configs.sh --bootstrap-server localhost:9092 --alter --entity-type topics --entity-name orders \
  --add-config retention.ms=604800000
bin/kafka-configs.sh --bootstrap-server localhost:9092 --describe --entity-type topics --entity-name orders
# Dynamic configs for topic orders are:
#   retention.ms=604800000 sensitive=false synonyms={DYNAMIC_TOPIC_CONFIG:retention.ms=604800000}
```

| 설정 | 기본값 | 뜻 |
|---|---|---|
| retention.ms | 7일 | 이보다 오래된 세그먼트를 지운다 |
| retention.bytes | -1(무제한) | 파티션 크기가 이걸 넘으면 오래된 세그먼트부터 지운다 |
| segment.bytes | 1GiB | 세그먼트를 닫고 새로 여는 크기 |
| segment.ms | 7일 | 이 시간이 지나면 크기와 상관없이 세그먼트를 닫는다 |

함정이 하나 있다. 활성 세그먼트는 지우지 않는다. 그래서 데이터가 적은 토픽은 retention.ms를 1시간으로 줘도, 세그먼트가 닫히기 전까지(segment.ms 기본 7일) 안 지워질 수 있다.

## 3. 로그 컴팩션

사용자 프로필처럼 '지금 값'만 중요한 데이터는 키마다 마지막 값만 남기면 된다. 실습이 빨리 끝나게 세그먼트를 5초마다 닫고, 조금만 지저분해져도 정리하게 설정했다.

```bash
bin/kafka-topics.sh --bootstrap-server localhost:9092 --create --topic user-profile --partitions 1 --replication-factor 1 \
  --config cleanup.policy=compact --config segment.ms=5000 \
  --config min.cleanable.dirty.ratio=0.01 --config delete.retention.ms=1000
printf 'u1:{"city":"서울"}\nu2:{"city":"부산"}\nu1:{"city":"대전"}\nu3:{"city":"광주"}\nu2:{"city":"제주"}\n' | \
  bin/kafka-console-producer.sh --bootstrap-server localhost:9092 --topic user-profile --property parse.key=true --property key.separator=:
```

바로 읽으면 다섯 건이 다 있다.

```text
Offset:0	u1	{"city":"서울"}
Offset:1	u2	{"city":"부산"}
Offset:2	u1	{"city":"대전"}
Offset:3	u3	{"city":"광주"}
Offset:4	u2	{"city":"제주"}
```

40초 기다렸다가 u4를 하나 더 보내서 세그먼트를 넘기고, 30초 뒤에 다시 읽었다.

```text
Offset:2	u1	{"city":"대전"}
Offset:3	u3	{"city":"광주"}
Offset:4	u2	{"city":"제주"}
Offset:5	u4	{"city":"인천"}
```

u1의 '서울', u2의 '부산'이 사라지고 키마다 최신 값만 남았다. 오프셋은 2, 3, 4, 5 그대로다. 컴팩션은 레코드를 지울 뿐 번호를 다시 매기지 않는다. u4를 일부러 하나 더 보낸 건 마지막 세그먼트(활성 세그먼트)는 컴팩션 대상이 아니라서다. 새 레코드가 들어와 세그먼트가 넘어가야 앞 세그먼트가 정리 대상이 된다.

| 개념 | 내용 |
|---|---|
| 톰스톤 | 값이 null인 레코드. '이 키 삭제'라는 뜻. delete.retention.ms 동안 남았다가 사라진다 |
| min.cleanable.dirty.ratio | 정리 안 된 부분 비율이 이 이상이어야 컴팩션을 시작(기본 0.5) |
| cleanup.policy=compact,delete | 키별 최신 값만 남기되, 보존 기간이 지나면 그것도 지운다 |

브로커 로그를 보니 __consumer_offsets 파티션도 cleanup.policy=compact로 만들어져 있었다.

```text
INFO Created log for partition __consumer_offsets-35 ... with properties {cleanup.policy=compact, compression.type="producer", segment.bytes=104857600}
```

> **쉬운 설명**
>
> 파티션은 일기장 묶음이고, 세그먼트는 한 권 한 권의 공책이다. 새 일기는 지금 쓰는 공책(활성 세그먼트)에만 적는다. 보존 정책은 '1주일 지난 공책은 통째로 버린다'다. 페이지 단위로 찢지는 않는다. 컴팩션은 주소록 정리와 같다. 같은 사람의 주소를 여러 번 적었으면 마지막 주소만 남기고 지운다. 다만 쪽 번호(오프셋)는 고치지 않아서 중간 번호가 비게 된다.

## 헷갈렸던 것들

- 보존 기간이 지나도 활성 세그먼트는 지워지지 않는다. 세그먼트가 닫혀야 지울 수 있다.
- 컴팩션은 바로 일어나지 않는다. 로그 클리너가 비율과 시간을 보고 돌아간다.
- 컴팩션 토픽은 키가 꼭 있어야 한다. 키 없는 레코드는 쓰기가 거부된다.

## 용어 정리

| 용어 | 뜻 |
|---|---|
| 세그먼트 | 파티션 로그를 나눈 파일 단위 |
| 활성 세그먼트 | 지금 쓰고 있는 마지막 세그먼트 |
| 로그 클리너 | 컴팩션을 수행하는 브로커 스레드 |
| 톰스톤 | 값이 null인 삭제 표시 레코드 |
| cleanup.policy | delete(기간, 크기로 삭제), compact(키별 최신만), 또는 둘 다 |

## 참고 자료

- Apache Kafka 문서, 로그 구현: <https://kafka.apache.org/41/implementation/log/>
- Apache Kafka 문서, 토픽 설정: <https://kafka.apache.org/41/configuration/topic-configs/>
- Apache Kafka 문서, 설계(로그 컴팩션): <https://kafka.apache.org/41/design/design/>

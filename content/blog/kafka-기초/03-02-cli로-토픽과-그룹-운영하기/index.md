---
title: '[Kafka 기초] CLI로 토픽과 컨슈머 그룹 운영하기: 자주 쓰는 명령 모음'
date: '2026-01-10T21:00:00+09:00'
categories:
- Kafka
tags:
- kafka
- cli
- kafka-topics
- kafka-configs
- kafka-consumer-groups
- kafka-reassign-partitions
- lag
- operations
- 저장과 운영
series:
- Kafka 기초
series_order: 10
---

지금까지 실습하면서 쓴 명령을 '운영할 때 무엇을 보고 싶은가' 기준으로 다시 묶었다. 회사에서 클러스터를 보게 되면 이 순서대로 열어 볼 생각이다. 직접 돌려 본 명령은 출력도 같이 남겼다.

## 요약

- 상태를 볼 때는 쿼럼 → 토픽(복제 부족) → 컨슈머 그룹(랙) 순서로 본다.
- kafka-topics는 생성, 조회, 파티션 늘리기를, kafka-configs는 토픽, 브로커 설정 변경을 맡는다.
- 랙은 kafka-consumer-groups --describe의 LAG 열로 본다. 랙이 계속 늘면 컨슈머가 못 따라가는 것이다.
- 파티션 재배치는 kafka-reassign-partitions로 계획 생성 → 실행 → 확인 세 단계로 한다.
- 4.x 도구는 --bootstrap-server로 브로커에 붙는다. ZooKeeper에 붙던 --zookeeper 옵션은 없다.

## 1. 상태 보는 순서

{{< mermaid >}}
flowchart TB
  A["쿼럼이 살아 있나<br>kafka-metadata-quorum<br>describe --status"] --> B["복제 부족한 파티션이 있나<br>kafka-topics --describe<br>--under-replicated-partitions"]
  B --> C["리더 없는 파티션이 있나<br>kafka-topics --describe<br>--unavailable-partitions"]
  C --> D["그룹이 밀리고 있나<br>kafka-consumer-groups<br>--describe --group ..."]
  D --> E["어느 브로커 디스크가 큰가<br>kafka-log-dirs --describe"]
{{< /mermaid >}}

## 2. 토픽

| 하려는 일 | 명령 |
|---|---|
| 목록 | kafka-topics --bootstrap-server $B --list |
| 상세 | kafka-topics --bootstrap-server $B --describe --topic orders |
| 생성 | kafka-topics --bootstrap-server $B --create --topic orders --partitions 6 --replication-factor 3 |
| 파티션 늘리기 | kafka-topics --bootstrap-server $B --alter --topic orders --partitions 12 |
| 삭제 | kafka-topics --bootstrap-server $B --delete --topic orders |
| 복제 부족 | kafka-topics --bootstrap-server $B --describe --under-replicated-partitions |
| 끝 오프셋 | kafka-get-offsets --bootstrap-server $B --topic orders |

파티션 늘리기는 줄일 수 없고, 키 순서가 바뀐다는 걸 토픽 편에서 직접 계산해 봤다. 키 기반 순서가 중요한 토픽은 늘리기 전에 컨슈머 쪽 영향을 먼저 봐야 한다.

## 3. 설정

```bash
# 토픽 설정 보기, 바꾸기, 지우기
bin/kafka-configs.sh --bootstrap-server $B --describe --entity-type topics --entity-name orders
bin/kafka-configs.sh --bootstrap-server $B --alter --entity-type topics --entity-name orders --add-config retention.ms=604800000
bin/kafka-configs.sh --bootstrap-server $B --alter --entity-type topics --entity-name orders --delete-config retention.ms
# 브로커 설정 전체(기본값 포함)
bin/kafka-configs.sh --bootstrap-server $B --describe --entity-type brokers --entity-name 1 --all
```

--all로 보면 각 값 옆에 synonyms가 나오는데, 값이 어디서 왔는지(DEFAULT_CONFIG, STATIC_BROKER_CONFIG, DYNAMIC_TOPIC_CONFIG 등) 알려 준다. '이 설정 누가 바꿨지?' 할 때 유용했다.

## 4. 컨슈머 그룹과 랙

```bash
bin/kafka-consumer-groups.sh --bootstrap-server $B --list
bin/kafka-consumer-groups.sh --bootstrap-server $B --describe --group billing
bin/kafka-consumer-groups.sh --bootstrap-server $B --describe --group billing --members
bin/kafka-consumer-groups.sh --bootstrap-server $B --describe --group billing --state
bin/kafka-groups.sh --bootstrap-server $B --list        # 그룹 종류(Classic, Consumer, Share, Streams)까지
```

```text
GROUP           TOPIC           PARTITION  CURRENT-OFFSET  LOG-END-OFFSET  LAG             CONSUMER-ID     HOST            CLIENT-ID
billing         orders          0          0               0               0               -               -               -
billing         orders          1          2               2               0               -               -               -
billing         orders          2          3               6               3               -               -               -
```

LAG = LOG-END-OFFSET − CURRENT-OFFSET이다. 위 결과는 2번 파티션에서 3건 밀린 상태다. 랙을 볼 때는 숫자 자체보다 추세를 본다고 한다. 잠깐 늘었다 줄면 괜찮고, 계속 늘면 컨슈머를 늘리거나(파티션 수까지) 처리를 빠르게 해야 한다.

## 5. 파티션 재배치

브로커를 새로 넣으면 기존 파티션은 저절로 옮겨 가지 않는다. 직접 재배치해야 한다. 이건 문서를 따라 순서만 정리했다.

```bash
# 1. 옮길 토픽 목록 파일
echo '{"topics":[{"topic":"orders"}],"version":1}' > topics.json
# 2. 계획 생성(브로커 1,2,3,4에 고르게)
bin/kafka-reassign-partitions.sh --bootstrap-server $B --topics-to-move-json-file topics.json --broker-list "1,2,3,4" --generate
#    출력의 'Proposed partition reassignment configuration'을 plan.json으로 저장
# 3. 실행(복제 대역폭 제한을 걸 수 있다)
bin/kafka-reassign-partitions.sh --bootstrap-server $B --reassignment-json-file plan.json --execute --throttle 50000000
# 4. 확인(끝나면 제한도 풀린다)
bin/kafka-reassign-partitions.sh --bootstrap-server $B --reassignment-json-file plan.json --verify
```

--generate의 출력에는 현재 배치(Current partition replica assignment)도 같이 나오니, 그걸 따로 저장해 두면 되돌릴 때 쓸 수 있다. 데이터가 큰 토픽은 복제 트래픽이 서비스 트래픽을 잡아먹지 않게 --throttle을 꼭 거는 게 좋다고 한다.

## 6. 그 밖에 쓸 만한 것

| 명령 | 쓰임 |
|---|---|
| kafka-leader-election --election-type preferred --all-topic-partitions | 리더를 선호 리더로 되돌리기(복제 편에서 써 봄) |
| kafka-log-dirs --describe --broker-list 1 | 브로커별, 파티션별 디스크 사용량 |
| kafka-delete-records --offset-json-file ... | 특정 오프셋 이전 레코드 삭제 |
| kafka-dump-log --files ...log --print-data-log | 세그먼트 파일 내용 보기 |
| kafka-features describe | 기능 버전 확인 |

> **쉬운 설명**
>
> 카프카 CLI는 건물 관리 열쇠 꾸러미다. kafka-topics는 방(토픽)을 만들고 넓히는 열쇠, kafka-configs는 방마다 규칙(보존 기간 등)을 바꾸는 열쇠, kafka-consumer-groups는 손님(컨슈머)이 어디까지 둘러봤는지 보는 열쇠다. 매일 아침 순찰은 '관리실(쿼럼) 정상 → 방마다 복사본 다 있나 → 손님이 밀려 있나' 순서로 돈다.

## 헷갈렸던 것들

- kafka-topics --describe의 Configs에는 기본값과 다른 값만 나온다. 기본값까지 다 보려면 kafka-configs --all을 쓴다.
- 컨슈머 그룹 describe에서 CONSUMER-ID가 -면 그 파티션을 지금 아무도 안 읽는 것이다.
- 파티션을 늘린 뒤 재배치를 안 하면 새 파티션만 새 브로커에 생기고, 기존 파티션은 그대로다.

## 용어 정리

| 용어 | 뜻 |
|---|---|
| 랙(lag) | 컨슈머 그룹이 밀린 레코드 수 |
| 재배치 | 파티션 복제본을 다른 브로커로 옮기는 작업 |
| 스로틀 | 재배치 복제 트래픽에 거는 대역폭 제한 |
| under-replicated | ISR이 복제 계수보다 적은 상태 |
| synonyms | 설정값이 어디서 왔는지 보여 주는 kafka-configs 출력 항목 |

## 참고 자료

- Apache Kafka 문서, 기본 운영: <https://kafka.apache.org/41/operations/basic-kafka-operations/>
- Apache Kafka 문서, 모니터링: <https://kafka.apache.org/41/operations/monitoring/>
- Apache Kafka 문서, 브로커 설정: <https://kafka.apache.org/41/configuration/broker-configs/>

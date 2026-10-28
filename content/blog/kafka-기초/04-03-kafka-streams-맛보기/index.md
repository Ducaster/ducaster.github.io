---
title: '[Kafka 기초] Kafka Streams 맛보기: 단어 세기 예제와 한글이 사라진 이유'
date: '2026-02-14T21:00:00+09:00'
categories:
- Kafka
tags:
- kafka
- kafka-streams
- kstream
- ktable
- state-store
- changelog
- repartition
- wordcount
- regex
- 생태계
series:
- Kafka 기초
series_order: 13
---

Kafka Streams는 별도 클러스터가 아니라 자바 라이브러리라서, 내 애플리케이션 안에서 토픽을 읽고 가공해서 다시 토픽에 쓴다. 카프카에 들어 있는 단어 세기 예제(WordCountDemo)를 돌렸는데, 한글로 넣은 단어가 전부 빠져서 이유를 찾아봤다.

## 요약

- Kafka Streams는 라이브러리다. 따로 띄울 처리 클러스터 없이 애플리케이션 프로세스 안에서 돈다.
- KStream은 '일어난 일'의 흐름, KTable은 '키별 지금 값'이다. count 같은 집계 결과는 KTable이 된다.
- 집계 상태는 로컬 상태 저장소에 두고, 같은 내용을 changelog 토픽에 백업한다. 키를 바꾸는 groupBy 뒤에는 repartition 토픽이 생긴다.
- 예제는 문장을 정규식 \\W+로 자르는데, 자바 기본 정규식에서 \\W는 한글을 단어 문자로 보지 않아 한글이 전부 구분자로 처리됐다.
- 4.1에는 Streams 전용 새 리밸런스 프로토콜(KIP-1071)이 early access로 들어왔다. 예제 앱은 아직 Classic 그룹으로 돌았다.

## 1. 예제 돌리기

입력, 출력 토픽을 만들고 문장 세 줄을 넣은 뒤 예제를 띄웠다. 예제는 첫 인자로 받은 설정 파일에서 bootstrap.servers를 읽는다.

```bash
bin/kafka-topics.sh --bootstrap-server $B --create --topic streams-plaintext-input --partitions 1 --replication-factor 3
bin/kafka-topics.sh --bootstrap-server $B --create --topic streams-wordcount-output --partitions 1 --replication-factor 3 --config cleanup.policy=compact
printf 'kafka streams 처음 써 보기\nkafka 토픽 파티션 오프셋\nstreams 는 그냥 라이브러리\n' | \
  bin/kafka-console-producer.sh --bootstrap-server $B --topic streams-plaintext-input
echo 'bootstrap.servers=localhost:19092,localhost:29092' > wordcount.properties
bin/kafka-run-class.sh org.apache.kafka.streams.examples.wordcount.WordCountDemo wordcount.properties
```

결과 토픽은 값이 Long이라 역직렬화기를 지정해서 읽었다.

```bash
bin/kafka-console-consumer.sh --bootstrap-server $B --topic streams-wordcount-output --from-beginning \
  --property print.key=true --value-deserializer org.apache.kafka.common.serialization.LongDeserializer
```

```text
streams	1
streams	2
kafka	1
kafka	2
kafka	3
kafka	4
streams	3
streams	4
```

숫자가 4까지 간 건 처음 시도 때 같은 세 줄을 한 번 더 넣어서다. 그건 그렇다 치고, '처음', '토픽', '파티션', '라이브러리' 같은 한글 단어가 하나도 없었다.

## 2. 한글이 사라진 이유

예제 클래스 안의 문자열을 보니 단어를 자르는 정규식이 W+였다. 소스를 보면 value.toLowerCase().split("\\W+")로 문장을 자른다. jshell로 같은 걸 해 봤다.

```text
jshell> Arrays.toString("kafka streams 처음 써 보기".split("\\W+"))
[kafka, streams]
```

자바 정규식의 \\w는 기본으로 [a-zA-Z_0-9]만 단어 문자로 본다. 그래서 \\W+(단어 문자가 아닌 것)로 자르면 한글이 구분자 취급을 받아 통째로 사라진다. 유니코드 문자를 단어로 보게 하려면 (?U) 플래그를 붙여 "(?U)\\W+"로 쓰거나, 그냥 공백("\\s+")으로 자르면 된다. 예제 코드라 고치지는 않았지만, 실제로 한글 데이터를 다룰 때 정규식 기본 동작을 꼭 확인해야겠다는 교훈을 얻었다.

## 3. 토폴로지와 내부 토픽

{{< mermaid >}}
flowchart TB
  I["streams-plaintext-input<br>(KStream)"] --> F["flatMapValues<br>소문자로, 단어로 쪼개기"]
  F --> G["groupBy(단어)<br>키를 단어로 바꿈"]
  G --> R["repartition 토픽<br>단어별로 다시 나눔"]
  R --> C["count()<br>상태 저장소"]
  C --> CL["changelog 토픽<br>상태 백업"]
  C --> O["toStream →<br>streams-wordcount-output<br>(KTable 변경분)"]
{{< /mermaid >}}

예제를 돌린 뒤 토픽 목록에 내부 토픽 두 개가 생겨 있었다.

```text
streams-plaintext-input
streams-wordcount-KSTREAM-AGGREGATE-STATE-STORE-0000000003-changelog
streams-wordcount-KSTREAM-AGGREGATE-STATE-STORE-0000000003-repartition
streams-wordcount-output
```

| 내부 토픽 | 왜 생기나 |
|---|---|
| repartition | groupBy로 키가 바뀌면, 같은 단어가 같은 파티션(같은 인스턴스)에 모이도록 다시 써야 한다 |
| changelog | 로컬 상태 저장소(RocksDB)의 변경을 카프카에 백업. 인스턴스가 죽으면 이걸로 상태를 복원 |

이름 앞의 streams-wordcount는 application.id다. 컨슈머 그룹 이름도 이것이다.

```text
GROUP                    TYPE                     PROTOCOL                
streams-wordcount        Classic                  consumer                 
connect-orders-file-sink Classic                  consumer                 
```

4.1에 Streams 전용 새 리밸런스 프로토콜이 early access로 들어왔고 kafka-streams-groups.sh라는 도구도 생겼지만, 예제는 기본값대로 Classic 그룹으로 돌아서 그 도구의 목록에는 아무것도 안 나왔다.

## 4. KStream과 KTable

| 비교 | KStream | KTable |
|---|---|---|
| 뜻 | 일어난 일 하나하나 | 키별 최신 상태 |
| 같은 키가 또 오면 | 새 레코드로 추가 | 값을 덮어씀 |
| 예 | 클릭, 주문 생성 이벤트 | 사용자별 현재 잔액, 단어별 개수 |
| 대응하는 토픽 | 일반(delete) 토픽 | 컴팩션 토픽이 잘 맞는다 |

출력 토픽을 cleanup.policy=compact로 만든 이유가 이것이다. 단어별로 마지막 개수만 있으면 된다.

> **쉬운 설명**
>
> Kafka Streams는 공장 컨베이어 벨트 옆에 붙이는 작업대다. 따로 공장(처리 클러스터)을 짓지 않고, 내 작업대(애플리케이션)에서 벨트(토픽)의 물건을 집어 다듬고 다른 벨트에 올린다. 개수를 세려면 메모장(상태 저장소)이 필요한데, 메모장을 잃어버릴 때를 대비해 사본을 카프카에 계속 적어 둔다(changelog). 한글이 사라진 건 작업 지시서에 '알파벳과 숫자만 단어로 친다'고 적혀 있었기 때문이다.

## 헷갈렸던 것들

- Streams 앱을 여러 개 띄우면 같은 application.id끼리 파티션을 나눠 처리한다. 컨슈머 그룹과 같은 원리다.
- 출력에 같은 단어가 여러 번 나오는 건 KTable의 변경분이 흘러나온 것이다. 마지막 값이 현재 개수다.
- 정규식 \\w, \\W의 의미는 언어와 플래그마다 다르다. 자바 기본값은 ASCII 기준이다.

## 용어 정리

| 용어 | 뜻 |
|---|---|
| 토폴로지 | 스트림 처리 단계를 연결한 그래프 |
| 상태 저장소 | 집계, 조인 상태를 저장하는 로컬 저장소. 기본은 RocksDB |
| changelog 토픽 | 상태 저장소 변경을 백업하는 내부 토픽 |
| repartition 토픽 | 키를 바꾼 뒤 데이터를 다시 나누는 내부 토픽 |
| application.id | Streams 앱 식별자. 그룹 이름과 내부 토픽 이름 앞에 붙는다 |

## 복습 문제

**1.** 같은 application.id로 예제를 두 개 띄우면 파티션 1개짜리 입력 토픽은 어떻게 처리되는가?

**2.** 한글 단어도 세게 하려면 split에 어떤 정규식을 쓰면 되는가?

**3.** changelog 토픽이 없다면 앱 인스턴스가 다른 서버에서 다시 뜰 때 무슨 문제가 생기는가?

## 답과 풀이

1. 파티션이 하나라 한 인스턴스만 처리하고 다른 하나는 대기한다. 처리 중인 쪽이 죽으면 대기하던 쪽이 이어받는다.

2. "(?U)\\W+"처럼 유니코드 플래그를 주거나, 공백 기준 "\\s+"로 자른다.

3. 로컬 상태 저장소가 새 서버에는 없어서 개수를 처음부터 다시 세야 한다. changelog가 있으면 그걸 읽어 상태를 복원한 뒤 이어서 처리한다.

## 참고 자료

- Apache Kafka 문서, Kafka Streams 빠른 시작: <https://kafka.apache.org/41/streams/quickstart/>
- Apache Kafka 문서, Streams 핵심 개념: <https://kafka.apache.org/41/streams/core-concepts/>
- WordCountDemo 소스: <https://github.com/apache/kafka/blob/trunk/streams/examples/src/main/java/org/apache/kafka/streams/examples/wordcount/WordCountDemo.java>
- 자바 Pattern 문서(UNICODE_CHARACTER_CLASS): <https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/regex/Pattern.html>

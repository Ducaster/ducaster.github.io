---
title: '[Kafka 기초] 직렬화와 스키마 레지스트리: 브로커는 바이트만 안다'
date: '2026-01-24T21:00:00+09:00'
categories:
- Kafka
tags:
- kafka
- serializer
- deserializer
- avro
- protobuf
- json-schema
- schema-registry
- compatibility
- wire-format
- 생태계
series:
- Kafka 기초
series_order: 11
---

생태계 편 첫 번째. 지금까지는 콘솔에서 문자열만 주고받았는데, 실제 서비스끼리는 주문 객체 같은 구조화된 데이터를 보낸다. 그때 필요한 직렬화와, 보내는 쪽과 받는 쪽이 같은 형식을 쓰게 맞춰 주는 스키마 레지스트리를 정리했다. 스키마 레지스트리는 아파치 카프카에 들어 있는 게 아니라 따로 띄우는 서비스라서 이번엔 직접 띄우지 않고 문서와 회사 설정을 보며 정리했다.

## 요약

- 브로커는 키와 값을 바이트 배열로만 다룬다. 바이트로 바꾸는 직렬화와 되돌리는 역직렬화는 클라이언트가 한다.
- 보내는 쪽과 받는 쪽이 형식에 대해 약속(스키마)을 해야 한다. 약속이 깨지면 컨슈머가 역직렬화에 실패한다.
- 스키마 레지스트리는 스키마를 버전별로 저장하고, 메시지에는 스키마 전체 대신 ID(4바이트)만 넣는다.
- 새 스키마를 등록할 때 호환성 규칙(BACKWARD가 기본)을 검사해서, 기존 컨슈머를 깨는 변경을 막는다.
- Kafka Connect의 JsonConverter는 schemas.enable=true면 메시지마다 스키마를 통째로 넣는다. 레지스트리를 쓰면 이 부담이 사라진다.

## 1. 직렬화

| 형식 | 장점 | 단점 |
|---|---|---|
| 문자열, JSON | 사람이 읽기 쉽다. 도구가 많다 | 크기가 크고, 필드 타입 약속이 느슨하다 |
| Avro | 작고 빠르다. 스키마 진화 규칙이 분명하다 | 스키마 없이는 못 읽는다 |
| Protobuf | 작고 빠르다. 여러 언어 지원이 좋다 | .proto 파일 관리가 필요하다 |
| JSON Schema | JSON 그대로 쓰면서 스키마 검증 | 크기는 JSON과 같다 |

자바 클라이언트에서는 key.serializer, value.serializer에 클래스를 지정한다. 기본으로 StringSerializer, LongSerializer, ByteArraySerializer 같은 단순한 것들이 들어 있다. Kafka Streams 단어 세기 예제는 결과 개수를 Long 8바이트로 써서, 콘솔 컨슈머로 읽을 때도 --value-deserializer로 LongDeserializer를 줘야 숫자로 보인다. 이건 Streams 편에서 직접 해 본다.

## 2. 스키마를 메시지마다 넣으면

다음 글에 정리할 Connect 실습을 먼저 해 봤는데, JsonConverter의 schemas.enable=true 설정으로 파일 한 줄을 보냈더니 토픽에 이렇게 들어갔다.

```text
{"schema":{"type":"string","optional":false},"payload":"1001,user-1,서울,32000"}
```

값은 문자열 하나인데 스키마가 매번 따라온다. 필드가 수십 개인 객체라면 스키마가 실제 데이터보다 커진다. 스키마 레지스트리는 이걸 ID 하나로 바꿔 준다.

## 3. 스키마 레지스트리 흐름

{{< mermaid >}}
sequenceDiagram
  participant P as 프로듀서
  participant SR as 스키마 레지스트리
  participant K as 카프카
  participant C as 컨슈머
  P->>SR: orders-value 주제에 스키마 등록(처음 한 번)
  SR->>SR: 호환성 검사
  SR-->>P: 스키마 ID 7
  P->>K: [0][ID 7][Avro 바이트]
  C->>K: 레코드 읽기
  C->>SR: ID 7 스키마 요청(캐시)
  SR-->>C: 스키마
  C->>C: 역직렬화
{{< /mermaid >}}

Confluent 형식 기준으로 메시지 값의 맨 앞 1바이트는 매직 바이트(0), 다음 4바이트가 스키마 ID, 그 뒤가 실제 데이터다. 스키마는 '주제(subject)' 단위로 버전 관리되고, 기본 규칙(TopicNameStrategy)은 토픽 이름에 -key, -value를 붙인다. orders 토픽의 값 스키마는 orders-value 주제가 된다.

예를 들어 주문 Avro 스키마는 이렇게 생겼다.

```json
{
  "type": "record",
  "name": "Order",
  "namespace": "shop",
  "fields": [
    {"name": "orderId", "type": "long"},
    {"name": "userId", "type": "string"},
    {"name": "amount", "type": "int"},
    {"name": "coupon", "type": ["null", "string"], "default": null}
  ]
}
```

## 4. 호환성 규칙

| 규칙 | 새 스키마가 보장하는 것 | 허용되는 변경 예 | 먼저 올릴 쪽 |
|---|---|---|---|
| BACKWARD(기본) | 새 스키마로 예전 데이터를 읽을 수 있다 | 필드 삭제, 기본값 있는 필드 추가 | 컨슈머 |
| FORWARD | 예전 스키마로 새 데이터를 읽을 수 있다 | 필드 추가, 기본값 있는 필드 삭제 | 프로듀서 |
| FULL | 양쪽 다 | 기본값 있는 필드 추가, 삭제 | 아무쪽이나 |
| NONE | 검사 안 함 | 아무 변경 | 조심 |

뒤에 _TRANSITIVE가 붙으면 바로 앞 버전뿐 아니라 모든 과거 버전과 비교한다. 위 Order 스키마에 coupon을 기본값 null로 넣은 건 BACKWARD, FORWARD 둘 다 지키는 추가다. 반대로 amount 타입을 int에서 string으로 바꾸면 어떤 규칙에서도 거절된다.

회사에서 BACKWARD를 쓰고 있다면 '컨슈머부터 새 스키마로 배포하고, 그다음 프로듀서'가 순서다. 컨슈머가 먼저 새 스키마를 알아야 예전 데이터와 새 데이터를 다 읽을 수 있기 때문이다.

## 5. 구현체

| 구현체 | 비고 |
|---|---|
| Confluent Schema Registry | 가장 널리 쓰임. Confluent Community License |
| Apicurio Registry | Apache 2.0 라이선스. Confluent 호환 API 제공 |
| 클라우드 관리형 | AWS Glue Schema Registry 등 |

> **쉬운 설명**
>
> 직렬화는 이삿짐을 상자에 싸는 것이고, 스키마는 상자에 붙이는 포장 목록이다. 목록을 상자마다 통째로 붙이면(schemas.enable=true) 목록이 짐보다 무거워진다. 스키마 레지스트리는 목록을 관리실 서랍에 보관하고 상자에는 '목록 7번'이라는 번호표만 붙이는 방법이다. 관리실은 새 목록을 받을 때 '예전 상자도 풀 수 있는지'(호환성)를 검사해서, 받는 사람이 상자를 못 푸는 일이 없게 한다.

## 헷갈렸던 것들

- 스키마 레지스트리는 카프카 브로커 기능이 아니다. 클라이언트의 직렬화 라이브러리가 레지스트리와 통신한다.
- BACKWARD는 '새 코드가 예전 데이터를 읽는다'는 뜻이라 컨슈머를 먼저 올린다. 이름만 보고 반대로 생각하기 쉽다.
- 레지스트리가 죽어도 이미 캐시된 스키마로는 계속 읽고 쓸 수 있다. 새 스키마 등록, 처음 보는 ID 조회가 막힌다.

## 용어 정리

| 용어 | 뜻 |
|---|---|
| 직렬화 | 객체를 바이트로 바꾸는 것 |
| 스키마 | 데이터의 필드와 타입 정의 |
| 주제(subject) | 레지스트리에서 스키마 버전을 묶는 이름. 보통 토픽-key, 토픽-value |
| 매직 바이트 | 메시지 형식을 알리는 맨 앞 1바이트 |
| 호환성 규칙 | 새 스키마 등록 때 기존 버전과 비교하는 기준 |

## 복습 문제

**1.** BACKWARD 규칙에서 기본값 없는 필드 phone을 추가하려 한다. 등록되는가?

**2.** 컨슈머가 '알 수 없는 매직 바이트' 오류를 낸다. 가장 흔한 원인은?

**3.** 스키마를 메시지마다 넣는 방식과 레지스트리 방식의 차이를 한 문장으로 적어라.

## 답과 풀이

1. 거절된다. 새 스키마로 예전 데이터를 읽을 때 phone 값이 없는데 기본값도 없어서 읽을 수 없기 때문이다. 기본값을 주면 된다.

2. 프로듀서는 레지스트리 형식이 아닌 직렬화(예: 그냥 JSON 문자열)로 썼는데 컨슈머는 레지스트리 역직렬화기를 쓰는 경우다. 양쪽 직렬화 설정을 맞춘다.

3. 메시지마다 넣으면 스키마가 매번 함께 전송돼 크기가 커지고, 레지스트리 방식은 4바이트 ID만 넣고 스키마는 한곳에서 버전과 호환성을 관리한다.

## 참고 자료

- Confluent 문서, 스키마 레지스트리 개요: <https://docs.confluent.io/platform/current/schema-registry/index.html>
- Confluent 문서, 스키마 진화와 호환성: <https://docs.confluent.io/platform/current/schema-registry/fundamentals/schema-evolution.html>
- Apache Avro 명세: <https://avro.apache.org/docs/current/specification/>
- Apicurio Registry: <https://www.apicur.io/registry/>

---
title: '[SQLD] TCL: COMMIT, ROLLBACK, SAVEPOINT와 트랜잭션의 특성'
date: '2024-12-01T22:26:00+09:00'
categories:
- SQLD
tags:
- sqld
- sql
- tcl
- 트랜잭션
- commit
- rollback
- savepoint
- acid
- 격리수준
- 관리 구문
series:
- SQLD
series_order: 29
---

관리 구문 두 번째, TCL. SAVEPOINT와 ROLLBACK이 섞인 SQL을 주고 최종 결과를 맞히라는 문제, Oracle과 SQL Server의 자동 커밋 차이가 자주 나온다.

## 요약

- 트랜잭션은 함께 성공하거나 함께 실패해야 하는 작업 단위이고, 원자성, 일관성, 고립성, 지속성(ACID)을 가진다.
- COMMIT은 변경을 확정하고, ROLLBACK은 마지막 COMMIT 이후의 변경을 취소한다.
- SAVEPOINT로 중간 저장점을 만들고, ROLLBACK TO로 그 지점까지만 되돌릴 수 있다.
- Oracle은 DDL을 실행하면 자동으로 COMMIT되고, SQL Server는 기본이 자동 커밋 모드다.
- 격리 수준이 낮으면 Dirty Read, Non-Repeatable Read, Phantom Read가 생길 수 있다.

## 1. 트랜잭션의 특성(ACID)

| 특성 | 뜻 |
|---|---|
| 원자성(Atomicity) | 트랜잭션의 연산은 모두 실행되거나 하나도 실행되지 않아야 한다(All or Nothing) |
| 일관성(Consistency) | 트랜잭션 전에 데이터베이스에 잘못된 내용이 없었다면, 끝난 뒤에도 없어야 한다 |
| 고립성(Isolation) | 실행 중인 트랜잭션은 다른 트랜잭션의 영향을 받아 잘못된 결과를 내면 안 된다 |
| 지속성(Durability) | 트랜잭션이 성공적으로 끝나면 그 결과는 영구히 저장된다 |

## 2. COMMIT과 ROLLBACK

### COMMIT 전후의 데이터 상태

| 시점 | 상태 |
|---|---|
| COMMIT 이전 | 변경 내용은 메모리 버퍼에만 있어 되돌릴 수 있다. 변경한 사용자는 결과를 볼 수 있지만, 다른 사용자는 볼 수 없다. 변경 중인 행에는 잠금(LOCK)이 걸려 다른 사용자가 바꿀 수 없다 |
| COMMIT 이후 | 변경이 데이터베이스에 영구 반영된다. 이전 데이터는 사라지고, 모든 사용자가 결과를 볼 수 있다. 잠금이 풀린다 |
| ROLLBACK 이후 | 변경이 취소되어 이전 상태로 돌아간다. 잠금이 풀린다 |

### 자동 커밋

| DBMS | 동작 |
|---|---|
| Oracle | DML은 직접 COMMIT해야 한다. DDL(CREATE, ALTER, DROP, TRUNCATE)을 실행하면 그 전의 DML까지 함께 자동 COMMIT된다. 정상 종료 시 COMMIT, 비정상 종료 시 ROLLBACK된다 |
| SQL Server | 기본이 자동 커밋(Auto Commit) 모드라 문장마다 바로 COMMIT된다. `BEGIN TRANSACTION`으로 명시적 트랜잭션을 시작하면 COMMIT이나 ROLLBACK을 직접 해야 한다 |

## 3. SAVEPOINT

긴 트랜잭션 중간에 저장점을 두고, 오류가 나면 전체가 아니라 그 지점까지만 되돌린다.

```sql
SAVEPOINT SP1;          -- Oracle
ROLLBACK TO SP1;

SAVE TRANSACTION SP1;   -- SQL Server
ROLLBACK TRANSACTION SP1;
```

{{< mermaid >}}
flowchart TB
  A["INSERT A"] --> S1(["SAVEPOINT SP1"])
  S1 --> B["INSERT B"] --> S2(["SAVEPOINT SP2"])
  S2 --> C["DELETE A"]
  C -.->|"ROLLBACK TO SP2"| S2
  C -.->|"ROLLBACK TO SP1"| S1
{{< /mermaid >}}

### 예제로 따라가기

빈 테이블 T에서 시작한다.

```sql
INSERT INTO T VALUES ('A');
SAVEPOINT SP1;
INSERT INTO T VALUES ('B');
SAVEPOINT SP2;
DELETE FROM T WHERE COL = 'A';
ROLLBACK TO SP2;      -- DELETE만 취소 → A, B
COMMIT;               -- A, B 확정
```

| 시점 | T의 내용 |
|---|---|
| INSERT A 후 | A |
| INSERT B 후 | A, B |
| DELETE A 후 | B |
| ROLLBACK TO SP2 후 | A, B |
| COMMIT 후 | A, B (확정) |

- 마지막 줄이 `ROLLBACK TO SP1`이었다면 INSERT B와 DELETE가 취소되어 A만 남는다.
- 그냥 `ROLLBACK`이었다면 모든 작업이 취소되어 테이블이 빈다.
- 같은 이름의 SAVEPOINT를 다시 만들면 나중 것이 앞의 것을 대신한다.
- `ROLLBACK TO SP1`을 한 뒤에는 SP1 뒤에 만든 SP2로는 되돌아갈 수 없다.

> **쉬운 설명**
>
> 게임의 저장 기능과 같다. COMMIT은 '저장하고 끄기'라 다시 켜도 그 상태가 남는다. SAVEPOINT는 중간 체크포인트, ROLLBACK TO는 '체크포인트부터 다시 하기', 그냥 ROLLBACK은 '마지막 저장 시점으로 돌아가기'이다. 저장하지 않은 진행 상황은 친구(다른 사용자)가 내 화면을 봐도 보이지 않는다.

## 4. 격리 수준과 이상 현상

여러 트랜잭션이 동시에 실행될 때 고립성이 충분하지 않으면 다음 문제가 생긴다.

| 현상 | 설명 |
|---|---|
| Dirty Read | 다른 트랜잭션이 아직 COMMIT하지 않은 데이터를 읽는다. 그 트랜잭션이 ROLLBACK하면 없는 데이터를 읽은 셈이 된다 |
| Non-Repeatable Read | 한 트랜잭션 안에서 같은 행을 두 번 읽었는데, 그 사이 다른 트랜잭션이 수정하고 COMMIT해서 값이 달라진다 |
| Phantom Read | 한 트랜잭션 안에서 같은 조건으로 두 번 조회했는데, 그 사이 다른 트랜잭션이 행을 추가해 없던 행이 나타난다 |

| 격리 수준 | Dirty Read | Non-Repeatable Read | Phantom Read |
|---|---|---|---|
| READ UNCOMMITTED | 발생 | 발생 | 발생 |
| READ COMMITTED | 방지 | 발생 | 발생 |
| REPEATABLE READ | 방지 | 방지 | 발생 |
| SERIALIZABLE | 방지 | 방지 | 방지 |

Oracle과 SQL Server의 기본 격리 수준은 READ COMMITTED이다. 격리 수준을 높일수록 데이터는 정확해지지만 동시에 처리할 수 있는 양(동시성)은 줄어든다.

## 헷갈렸던 것들

- COMMIT 전의 변경은 변경한 사용자만 볼 수 있고, 다른 사용자는 볼 수 없다.
- Oracle에서 DDL을 실행하면 앞선 DML까지 자동 COMMIT된다.
- SQL Server는 기본이 자동 커밋이다. 명시적 트랜잭션 안에서는 TRUNCATE도 ROLLBACK할 수 있다.
- ROLLBACK TO 저장점은 그 저장점 이후의 작업만 취소한다. 그냥 ROLLBACK은 마지막 COMMIT 이후 전체를 취소한다.
- Oracle은 `SAVEPOINT`, SQL Server는 `SAVE TRANSACTION`이다.
- Dirty Read는 COMMIT되지 않은 데이터를 읽는 것이다.

## 용어 정리

| 용어 | 뜻 |
|---|---|
| 트랜잭션 | 논리적인 작업 단위 |
| COMMIT / ROLLBACK | 변경 확정 / 변경 취소 |
| SAVEPOINT | 트랜잭션 중간의 저장점 |
| 자동 커밋 | 문장마다 자동으로 COMMIT하는 모드 |
| 격리 수준 | 트랜잭션끼리 서로 영향을 주지 않는 정도 |
| 잠금(LOCK) | 다른 트랜잭션의 동시 변경을 막는 장치 |

## 복습 문제

빈 테이블 T에서 다음을 실행했다(Oracle).

```sql
INSERT INTO T VALUES (1);
SAVEPOINT SV1;
INSERT INTO T VALUES (2);
SAVEPOINT SV2;
INSERT INTO T VALUES (3);
ROLLBACK TO SV1;
INSERT INTO T VALUES (4);
COMMIT;
```

**1.** 최종적으로 T에 남은 값은?

① 1 ② 1, 2, 4 ③ 1, 4 ④ 1, 2, 3, 4

**2.** Oracle에서 다음을 실행한 뒤 남는 데이터는? (T는 비어 있음)

```sql
INSERT INTO T VALUES (1);
CREATE TABLE T2 (C NUMBER);
ROLLBACK;
```

① 없음 ② 1 ③ 오류 ④ T2만 사라진다

**3.** 다른 트랜잭션이 COMMIT하지 않은 데이터를 읽는 현상은?

① Non-Repeatable Read ② Dirty Read ③ Phantom Read ④ Deadlock

## 답과 풀이

1. ③ ROLLBACK TO SV1로 2와 3이 취소되고, 4를 넣은 뒤 COMMIT했으므로 1, 4가 남는다.
2. ② CREATE TABLE(DDL)을 실행하면서 앞의 INSERT가 자동 COMMIT되었으므로 ROLLBACK해도 1이 남는다.
3. ② Dirty Read이다.

## 참고 자료

- 한국데이터산업진흥원 데이터자격검정, SQLD 출제기준: <https://www.dataq.or.kr>
- Oracle Database Concepts, Transactions: <https://docs.oracle.com/en/database/oracle/oracle-database/23/cncpt/transactions.html>

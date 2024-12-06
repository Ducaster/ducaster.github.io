---
title: '[SQLD] DCL: GRANT, REVOKE, 권한과 롤'
date: '2024-12-06T21:09:00+09:00'
categories:
- SQLD
tags:
- sqld
- sql
- dcl
- grant
- revoke
- 권한
- role
- with-grant-option
- with-admin-option
- 관리 구문
series:
- SQLD
series_order: 31
---

관리 구문 마지막이자 SQLD 정리의 마지막 글, DCL. WITH GRANT OPTION과 WITH ADMIN OPTION의 차이, 롤(ROLE)을 쓰는 이유가 자주 나온다.

## 요약

- DCL은 사용자에게 권한을 주고(GRANT) 회수하는(REVOKE) 명령어다.
- 권한은 데이터베이스 전체에 대한 시스템 권한과, 특정 객체(테이블 등)에 대한 오브젝트 권한으로 나뉜다.
- WITH GRANT OPTION(오브젝트 권한)으로 받은 권한을 회수하면 그 사용자가 남에게 준 권한도 함께 회수되고, WITH ADMIN OPTION(시스템 권한)은 함께 회수되지 않는다.
- 롤은 여러 권한을 묶은 것으로, 많은 사용자의 권한을 쉽게 관리하게 해 준다.

## 1. 사용자와 권한

Oracle에서는 사용자를 만들어도 권한이 없으면 접속조차 할 수 없다.

```sql
CREATE USER SCOTT2 IDENTIFIED BY "Pass1234";   -- 사용자 생성(DBA 권한 필요)
GRANT CREATE SESSION TO SCOTT2;                 -- 접속 권한
GRANT CREATE TABLE TO SCOTT2;                   -- 테이블 생성 권한
```

| 사용자 | 설명 |
|---|---|
| SYS | 최고 관리자. 데이터 딕셔너리를 소유한다 |
| SYSTEM | 데이터베이스의 모든 시스템 권한을 가진 관리자 |

SQL Server는 서버에 접속하는 **로그인(Login)** 과 데이터베이스 안의 **사용자(User)** 를 따로 만든다.

### 시스템 권한과 오브젝트 권한

| 구분 | 설명 | 예 |
|---|---|---|
| 시스템 권한 | 데이터베이스에서 특정 작업을 할 수 있는 권한 | CREATE SESSION, CREATE TABLE, CREATE VIEW, CREATE USER |
| 오브젝트 권한 | 특정 객체(테이블, 뷰, 시퀀스 등)에 대한 권한 | SELECT, INSERT, UPDATE, DELETE, ALTER, REFERENCES, INDEX, ALL |

다른 사용자의 테이블은 소유자가 권한을 줘야 쓸 수 있고, 쓸 때는 `소유자.테이블` 형식으로 부른다.

```sql
-- SCOTT 사용자가 자기 EMP 테이블의 조회와 수정 권한을 SCOTT2에게 준다
GRANT SELECT, UPDATE ON EMP TO SCOTT2;

-- SCOTT2는 이렇게 조회한다
SELECT * FROM SCOTT.EMP;

-- 권한 회수
REVOKE UPDATE ON EMP FROM SCOTT2;
```

`GRANT ... TO`, `REVOKE ... FROM`이라는 전치사 차이를 기억해 두자. `TO PUBLIC`으로 주면 모든 사용자에게 권한이 간다.

## 2. WITH GRANT OPTION과 WITH ADMIN OPTION

받은 권한을 다른 사람에게 다시 줄 수 있게 하는 옵션이다.

| 옵션 | 대상 | 받은 사람이 할 수 있는 일 | 원래 권한을 회수하면 |
|---|---|---|---|
| WITH GRANT OPTION | 오브젝트 권한 | 받은 권한을 다른 사용자에게 줄 수 있다 | 그 사람이 다른 사용자에게 준 권한도 함께 회수된다(연쇄 회수) |
| WITH ADMIN OPTION | 시스템 권한, 롤 | 받은 권한을 다른 사용자에게 주고 회수할 수 있다 | 그 사람이 다른 사용자에게 준 권한은 그대로 남는다 |

{{< mermaid >}}
flowchart LR
  subgraph G["WITH GRANT OPTION (오브젝트 권한)"]
    direction LR
    GA["A"] -->|"GRANT SELECT<br>WITH GRANT OPTION"| GB["B"] -->|"GRANT SELECT"| GC["C"]
  end
  subgraph AD["WITH ADMIN OPTION (시스템 권한)"]
    direction LR
    AA["A"] -->|"GRANT CREATE TABLE<br>WITH ADMIN OPTION"| AB["B"] -->|"GRANT CREATE TABLE"| AC["C"]
  end
{{< /mermaid >}}

A가 B의 권한을 회수하면, 위쪽(GRANT OPTION)에서는 C의 SELECT 권한도 함께 사라지고, 아래쪽(ADMIN OPTION)에서는 C의 CREATE TABLE 권한이 남는다.

## 3. 롤(ROLE)

사용자가 많으면 권한을 하나하나 주고 회수하기 번거롭다. **롤**은 여러 권한을 묶어 이름을 붙인 것이다. 롤에 권한을 주고, 사용자에게는 롤을 준다.

{{< mermaid >}}
flowchart LR
  P1["CREATE SESSION"] --> R["롤: DEV_ROLE"]
  P2["CREATE TABLE"] --> R
  P3["SELECT ON EMP"] --> R
  R --> U1["사용자 A"]
  R --> U2["사용자 B"]
  R --> U3["사용자 C"]
{{< /mermaid >}}

```sql
CREATE ROLE DEV_ROLE;
GRANT CREATE SESSION, CREATE TABLE TO DEV_ROLE;
GRANT SELECT ON SCOTT.EMP TO DEV_ROLE;
GRANT DEV_ROLE TO SCOTT2;          -- 사용자에게 롤 부여
REVOKE DEV_ROLE FROM SCOTT2;       -- 롤 회수
```

롤에서 권한 하나를 빼면 그 롤을 가진 모든 사용자에게서 한 번에 빠진다.

| Oracle 기본 롤 | 포함된 권한 |
|---|---|
| CONNECT | 접속에 필요한 권한(CREATE SESSION) |
| RESOURCE | 객체를 만드는 권한(CREATE TABLE, CREATE SEQUENCE, CREATE PROCEDURE 등) |
| DBA | 거의 모든 시스템 권한 |

> **쉬운 설명**
>
> 회사 출입증과 같다. 출입증 하나하나에 '1층 출입', '회의실 사용', '서버실 출입'을 따로 적어 주는 게 개별 권한 부여, '신입 사원용', '개발팀용' 출입증 종류를 정해 두고 나눠 주는 게 롤이다. WITH GRANT OPTION은 '이 출입증을 복사해 남에게 줘도 됨'인데, 원본을 회수하면 복사본도 함께 무효가 된다.

## 헷갈렸던 것들

- 권한 부여는 `GRANT 권한 ON 객체 TO 사용자`, 회수는 `REVOKE 권한 ON 객체 FROM 사용자`이다.
- 사용자를 만들어도 CREATE SESSION 권한이 없으면 접속할 수 없다.
- WITH GRANT OPTION은 오브젝트 권한에 쓰고, 회수하면 연쇄적으로 회수된다.
- WITH ADMIN OPTION은 시스템 권한과 롤에 쓰고, 회수해도 연쇄 회수되지 않는다.
- 롤은 권한의 묶음이고, 롤에도 롤을 줄 수 있다.
- 다른 사용자의 테이블은 `소유자.테이블명`으로 부른다.

## 용어 정리

| 용어 | 뜻 |
|---|---|
| DCL | 데이터 제어어. GRANT, REVOKE |
| 시스템 권한 | 데이터베이스 작업 권한(CREATE TABLE 등) |
| 오브젝트 권한 | 특정 객체에 대한 권한(SELECT ON EMP 등) |
| WITH GRANT OPTION | 오브젝트 권한을 다시 줄 수 있게 하는 옵션. 연쇄 회수 |
| WITH ADMIN OPTION | 시스템 권한을 다시 줄 수 있게 하는 옵션. 연쇄 회수 없음 |
| 롤(ROLE) | 여러 권한을 묶은 것 |

## 복습 문제

**1.** SCOTT2에게 EMP 테이블 조회 권한을 주는 SQL로 옳은 것은?

① `GRANT SELECT ON EMP FROM SCOTT2;` ② `REVOKE SELECT ON EMP TO SCOTT2;` ③ `GRANT SELECT TO SCOTT2 ON EMP;` ④ `GRANT SELECT ON EMP TO SCOTT2;`

**2.** A가 B에게 `GRANT SELECT ON T TO B WITH GRANT OPTION`으로 권한을 주고, B가 C에게 같은 권한을 줬다. A가 B의 권한을 회수하면?

① B와 C의 권한이 모두 회수된다 ② B의 권한만 회수된다 ③ C의 권한만 회수된다 ④ 회수할 수 없다

**3.** 여러 권한을 묶어 사용자들에게 한 번에 부여하고 관리하기 위한 것은?

① VIEW ② ROLE ③ SYNONYM ④ SEQUENCE

**4.** 새로 만든 Oracle 사용자가 데이터베이스에 접속하려면 반드시 필요한 권한은?

① CREATE TABLE ② SELECT ANY TABLE ③ CREATE VIEW ④ CREATE SESSION

## 답과 풀이

1. ④ `GRANT ... ON ... TO`이다.
2. ① WITH GRANT OPTION으로 준 오브젝트 권한은 연쇄적으로 회수된다.
3. ② ROLE이다.
4. ④ CREATE SESSION이 있어야 접속할 수 있다.

## 참고 자료

- 한국데이터산업진흥원 데이터자격검정, SQLD 출제기준: <https://www.dataq.or.kr>
- Oracle Database SQL Language Reference, GRANT: <https://docs.oracle.com/en/database/oracle/oracle-database/23/sqlrf/GRANT.html>

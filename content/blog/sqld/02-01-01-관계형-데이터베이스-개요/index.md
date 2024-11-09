---
title: '[SQLD] 관계형 데이터베이스 개요: 테이블, SQL의 종류, 관계 연산'
date: '2024-11-09T21:40:00+09:00'
categories:
- SQLD
tags:
- sqld
- sql
- 관계형데이터베이스
- ddl
- dml
- dcl
- tcl
- 관계대수
- SQL 기본
series:
- SQLD
series_order: 12
---

SQLD 2과목 'SQL 기본 및 활용' 시작. 첫 단원은 관계형 데이터베이스 개요다. SQL 명령어를 DDL, DML, DCL, TCL로 나누는 문제와 관계 연산 종류가 자주 나온다.

## 요약

- 관계형 데이터베이스는 데이터를 행과 열로 된 테이블(관계)에 저장하고, 테이블끼리의 관계로 데이터를 연결한다.
- SQL은 관계형 데이터베이스를 다루는 표준 언어이고, 명령어는 DDL, DML, DCL, TCL로 나뉜다.
- 관계 대수의 연산은 일반 집합 연산(합집합, 교집합, 차집합, 곱집합)과 순수 관계 연산(선택, 투영, 조인, 나누기)으로 나뉜다.

## 1. 관계형 데이터베이스

**데이터베이스(Database)** 는 여러 사람이 함께 쓰려고 체계적으로 모아 둔 데이터의 집합이고, 이를 관리하는 소프트웨어를 **DBMS(Database Management System)** 라고 한다. 1970년 영국의 수학자 코드(E. F. Codd)가 제안한 **관계형 데이터 모델**을 바탕으로 한 것이 관계형 데이터베이스(RDB)이고, 이를 관리하는 소프트웨어가 Oracle, SQL Server, MySQL, PostgreSQL 같은 **RDBMS**이다.

관계형 데이터베이스의 장점은 다음과 같다.

- 정규화로 이상현상과 중복을 줄일 수 있다.
- 동시성 관리와 병행 제어로 여러 사용자가 동시에 데이터를 다룰 수 있다.
- 메타데이터를 총괄 관리할 수 있어 데이터의 성격과 속성을 표준화하기 쉽다.
- 제약 조건으로 데이터 무결성을 보장한다.

### 테이블의 용어

| 용어 | 다른 이름 | 뜻 |
|---|---|---|
| 테이블(Table) | 관계(Relation) | 데이터를 행과 열로 저장하는 단위 |
| 행(Row) | 튜플(Tuple), 레코드 | 가로 한 줄. 한 개체의 데이터 |
| 열(Column) | 속성(Attribute), 필드 | 세로 한 줄. 같은 성격의 데이터 |
| 차수(Degree) | | 열(속성)의 개수 |
| 카디널리티(Cardinality) | | 행(튜플)의 개수 |
| 도메인(Domain) | | 한 열이 가질 수 있는 값의 범위 |
| 기본키(Primary Key) | | 행을 유일하게 구분하는 열 |
| 외래키(Foreign Key) | | 다른 테이블의 기본키를 참조하는 열 |

예제의 EMP 테이블은 열이 8개, 행이 10개이므로 차수는 8, 카디널리티는 10이다.

## 2. SQL과 명령어의 종류

**SQL(Structured Query Language)** 은 관계형 데이터베이스에서 데이터를 정의하고, 조회하고, 조작하고, 제어하는 표준 언어다. ANSI/ISO 표준이 있고, 각 DBMS가 표준에 자기만의 문법을 더해 쓴다.

| 종류 | 이름 | 명령어 | 하는 일 |
|---|---|---|---|
| DML(Data Manipulation Language) | 데이터 조작어 | SELECT, INSERT, UPDATE, DELETE, MERGE | 데이터를 조회하고 넣고 고치고 지운다 |
| DDL(Data Definition Language) | 데이터 정의어 | CREATE, ALTER, DROP, RENAME, TRUNCATE | 테이블 같은 구조를 만들고 바꾸고 지운다 |
| DCL(Data Control Language) | 데이터 제어어 | GRANT, REVOKE | 권한을 주고 회수한다 |
| TCL(Transaction Control Language) | 트랜잭션 제어어 | COMMIT, ROLLBACK, SAVEPOINT | 변경 내용을 확정하거나 취소한다 |

SELECT를 따로 **DQL(Data Query Language)** 이라고 부르는 자료도 있지만, SQLD에서는 보통 DML에 포함한다. TRUNCATE는 데이터를 지우지만 DML이 아니라 **DDL**이라는 점도 자주 나온다.

> **쉬운 설명**
>
> 엑셀로 비유하면, 새 시트와 열 제목을 만드는 것이 DDL, 칸에 값을 넣고 고치고 지우는 것이 DML, 다른 사람에게 파일 편집 권한을 주는 것이 DCL, '저장'이나 '실행 취소'를 누르는 것이 TCL이다.

## 3. 관계 연산

관계형 데이터베이스의 연산은 관계 대수로 설명하고, SQL의 각 문법과 대응한다.

### 일반 집합 연산

| 연산 | 뜻 | SQL |
|---|---|---|
| 합집합(UNION) | 두 관계의 행을 합친다(중복 제거) | UNION |
| 교집합(INTERSECTION) | 두 관계에 공통으로 있는 행 | INTERSECT |
| 차집합(DIFFERENCE) | 한 관계에는 있고 다른 관계에는 없는 행 | MINUS(Oracle), EXCEPT(SQL Server) |
| 곱집합(CARTESIAN PRODUCT) | 두 관계의 모든 행을 서로 조합 | CROSS JOIN |

### 순수 관계 연산

| 연산 | 뜻 | SQL |
|---|---|---|
| 선택(SELECT) | 조건에 맞는 행을 고른다 | WHERE 절 |
| 투영(PROJECT) | 원하는 열만 고른다 | SELECT 절 |
| 조인(JOIN) | 공통 속성으로 두 관계를 합친다 | JOIN |
| 나누기(DIVIDE) | 한 관계의 모든 값과 관계있는 행을 찾는다 | 직접 대응하는 SQL 문법은 없다 |

관계 대수의 '선택(SELECT)'은 SQL의 SELECT 절이 아니라 **WHERE 절**에 대응한다는 점이 헷갈리기 쉽다.

{{< mermaid >}}
flowchart LR
  T["EMP 테이블"] -->|"선택: WHERE DEPTNO = 20<br>행을 고른다"| S["개발부 4행"]
  T -->|"투영: SELECT ENAME, SAL<br>열을 고른다"| P["2개 열"]
{{< /mermaid >}}

## 헷갈렸던 것들

- TRUNCATE는 DDL, MERGE는 DML이다.
- 권한 관련 GRANT, REVOKE는 DCL, COMMIT, ROLLBACK은 TCL이다.
- 차수는 열의 개수, 카디널리티는 행의 개수다(모델링의 관계 카디널리티와 다른 뜻이다).
- 관계 대수의 선택 연산은 WHERE 절, 투영 연산은 SELECT 절에 해당한다.
- 차집합은 Oracle에서 MINUS, SQL Server에서 EXCEPT이다.

## 용어 정리

| 용어 | 뜻 |
|---|---|
| RDBMS | 관계형 데이터베이스 관리 시스템 |
| 튜플 / 속성 | 행 / 열 |
| 차수 / 카디널리티 | 열의 수 / 행의 수 |
| DDL / DML / DCL / TCL | 정의어 / 조작어 / 제어어 / 트랜잭션 제어어 |
| 선택 / 투영 | 행을 고르는 연산 / 열을 고르는 연산 |

## 복습 문제

**1.** 다음 중 DDL에 해당하지 않는 것은?

① CREATE ② ALTER ③ MERGE ④ TRUNCATE

**2.** 열이 5개, 행이 100개인 테이블의 차수와 카디널리티는?

① 100, 5 ② 5, 5 ③ 5, 100 ④ 100, 100

**3.** 관계 대수의 연산 가운데 SQL의 WHERE 절에 해당하는 것은?

① 선택 ② 투영 ③ 조인 ④ 나누기

**4.** 권한을 부여하는 GRANT는 어떤 종류의 명령어인가?

① DCL ② DML ③ DDL ④ TCL

## 답과 풀이

1. ③ MERGE는 DML이다.
2. ③ 차수는 열의 수 5, 카디널리티는 행의 수 100이다.
3. ① 선택 연산은 조건에 맞는 행을 고르는 WHERE 절에 해당한다.
4. ① GRANT와 REVOKE는 DCL이다.

## 참고 자료

- 한국데이터산업진흥원 데이터자격검정, SQLD 출제기준: <https://www.dataq.or.kr>
- Codd, E. F., 'A Relational Model of Data for Large Shared Data Banks', Communications of the ACM, 1970

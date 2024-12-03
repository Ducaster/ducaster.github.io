---
title: '[SQLD] DDL: CREATE, ALTER, DROP, TRUNCATE와 제약 조건'
date: '2024-12-03T19:13:00+09:00'
categories:
- SQLD
tags:
- sqld
- sql
- ddl
- create-table
- alter-table
- 제약조건
- primary-key
- foreign-key
- ctas
- 관리 구문
series:
- SQLD
series_order: 30
---

관리 구문 세 번째, DDL. 제약 조건 종류와 특징, ALTER TABLE 문법의 Oracle·SQL Server 차이, CTAS로 복사할 때 어떤 제약 조건이 따라오는지가 자주 나온다.

## 요약

- DDL은 테이블 같은 데이터베이스 객체의 구조를 만들고(CREATE), 바꾸고(ALTER), 지우는(DROP) 명령어다. RENAME, TRUNCATE도 DDL이다.
- 데이터 타입은 문자(CHAR, VARCHAR2), 숫자(NUMBER), 날짜(DATE)가 기본이다. CHAR는 고정 길이, VARCHAR2는 가변 길이다.
- 제약 조건은 PRIMARY KEY, UNIQUE, NOT NULL, CHECK, FOREIGN KEY가 있다.
- CREATE TABLE ... AS SELECT(CTAS)로 테이블을 복사하면 NOT NULL 제약만 따라온다.
- Oracle에서 DDL은 실행하는 순간 자동으로 COMMIT된다.

## 1. CREATE TABLE

```sql
CREATE TABLE PRODUCT (
  PROD_ID   NUMBER(5)     CONSTRAINT PK_PRODUCT PRIMARY KEY,
  PROD_NAME VARCHAR2(50)  NOT NULL,
  PRICE     NUMBER(8)     DEFAULT 0 CONSTRAINT CK_PRICE CHECK (PRICE >= 0),
  CATEGORY  CHAR(1),
  DEPTNO    NUMBER(2)     CONSTRAINT FK_PROD_DEPT REFERENCES DEPT(DEPTNO),
  REG_DATE  DATE          DEFAULT SYSDATE,
  CONSTRAINT UQ_PROD_NAME UNIQUE (PROD_NAME)
);
```

### 테이블과 열 이름 규칙

- 문자로 시작해야 한다(숫자로 시작할 수 없다).
- A-Z, a-z, 0-9, _, $, # 문자만 쓸 수 있다.
- 예약어(SELECT, TABLE 등)는 쓸 수 없다.
- 한 테이블 안에서 열 이름이 겹치면 안 된다.
- 길이 제한이 있다(Oracle 12.2 이전 30바이트, 이후 128바이트).

### 주요 데이터 타입

| 타입 | 설명 |
|---|---|
| CHAR(L) | 고정 길이 문자열. 짧은 값을 넣으면 나머지를 공백으로 채운다 |
| VARCHAR2(L) | 가변 길이 문자열. 넣은 길이만큼만 저장한다(SQL Server는 VARCHAR) |
| NUMBER(L, D) | 숫자. L은 전체 자릿수, D는 소수점 아래 자릿수. NUMBER(8, 2)는 정수 6자리와 소수 2자리(SQL Server는 NUMERIC, DECIMAL, INT 등) |
| DATE | 날짜와 시각(초 단위까지). SQL Server는 DATETIME |

## 2. 제약 조건

| 제약 조건 | 뜻 | NULL 허용 | 테이블당 개수 |
|---|---|---|---|
| PRIMARY KEY | 행을 유일하게 식별한다. UNIQUE + NOT NULL | 불가 | 하나 |
| UNIQUE | 값이 겹치지 않아야 한다 | 가능(NULL은 여러 개여도 된다) | 여러 개 |
| NOT NULL | NULL을 넣을 수 없다 | 불가 | 여러 개 |
| CHECK | 값이 조건을 만족해야 한다 | | 여러 개 |
| FOREIGN KEY | 다른 테이블의 PK(또는 UNIQUE) 값만 넣을 수 있다. 참조 무결성 | 가능 | 여러 개 |

- PRIMARY KEY와 UNIQUE 제약을 만들면 DBMS가 자동으로 인덱스를 만든다.
- DEFAULT는 제약 조건이 아니라, 값을 넣지 않았을 때 들어갈 기본값이다.
- 제약 조건에 이름(CONSTRAINT 이름)을 붙이지 않으면 Oracle이 SYS_C0001234 같은 이름을 자동으로 붙인다.

### 외래키의 참조 동작

부모 행(DEPT)을 지우거나 바꿀 때 자식 행(EMP)을 어떻게 할지 정한다.

| 옵션 | 부모 행을 지우면 |
|---|---|
| (기본, NO ACTION / RESTRICT) | 자식 행이 있으면 지울 수 없다 |
| ON DELETE CASCADE | 자식 행도 함께 지운다 |
| ON DELETE SET NULL | 자식 행의 외래키를 NULL로 바꾼다 |

자식 테이블에 넣을 때는 부모에 없는 값을 넣을 수 없다(외래키가 NULL인 것은 허용).

{{< mermaid >}}
flowchart LR
  P["DEPT 40 삭제 시도"] --> Q{"EMP에 DEPTNO 40인<br>행이 있나?"}
  Q -->|"없음"| OK["삭제됨"]
  Q -->|"있음 + 기본"| ERR["오류: 자식 레코드 존재"]
  Q -->|"있음 + CASCADE"| C["EMP 행도 함께 삭제"]
  Q -->|"있음 + SET NULL"| N["EMP.DEPTNO를 NULL로"]
{{< /mermaid >}}

## 3. ALTER TABLE

| 작업 | Oracle | SQL Server |
|---|---|---|
| 열 추가 | `ALTER TABLE T ADD (COL3 NUMBER);` | `ALTER TABLE T ADD COL3 INT;` |
| 열 수정 | `ALTER TABLE T MODIFY (COL3 VARCHAR2(20) NOT NULL);` | `ALTER TABLE T ALTER COLUMN COL3 VARCHAR(20) NOT NULL;` |
| 열 삭제 | `ALTER TABLE T DROP COLUMN COL3;` | `ALTER TABLE T DROP COLUMN COL3;` |
| 열 이름 변경 | `ALTER TABLE T RENAME COLUMN COL3 TO COL4;` | `sp_rename 'T.COL3', 'COL4', 'COLUMN';` |
| 제약 조건 추가 | `ALTER TABLE T ADD CONSTRAINT PK_T PRIMARY KEY (COL1);` | 같음 |
| 제약 조건 삭제 | `ALTER TABLE T DROP CONSTRAINT PK_T;` | 같음 |

- 추가한 열은 테이블의 **마지막**에 붙고, 위치를 정할 수 없다.
- 열을 한 번에 여러 개 추가하거나 수정할 수 있다(Oracle은 괄호 안에 쉼표로).

### MODIFY의 규칙

- 열의 크기를 **늘리는 것**은 언제나 된다.
- 크기를 줄이거나 타입을 바꾸는 것은 데이터가 없거나(모두 NULL) 바꿀 크기에 맞을 때만 된다.
- DEFAULT 값을 바꾸면 그 **이후에 넣는 행**부터 적용된다.
- NOT NULL로 바꾸려면 그 열에 NULL인 행이 없어야 한다.

## 4. RENAME, DROP, TRUNCATE

```sql
RENAME PRODUCT TO GOODS;                 -- Oracle 테이블 이름 변경 (SQL Server는 sp_rename)
DROP TABLE GOODS;                        -- 구조와 데이터 모두 삭제
DROP TABLE DEPT CASCADE CONSTRAINTS;     -- DEPT를 참조하는 외래키 제약까지 함께 삭제
TRUNCATE TABLE EMP_COPY;                 -- 구조는 남기고 데이터만 모두 삭제
```

다른 테이블이 참조하는 부모 테이블은 그냥 DROP할 수 없다. `CASCADE CONSTRAINTS`를 붙이면 자식 테이블의 외래키 제약 조건이 함께 지워지고, 자식 테이블의 데이터는 그대로 남는다.

## 5. CTAS(CREATE TABLE AS SELECT)

```sql
CREATE TABLE EMP_BAK AS SELECT * FROM EMP;          -- 구조와 데이터 복사
CREATE TABLE EMP_EMPTY AS SELECT * FROM EMP WHERE 1 = 2;   -- 구조만 복사
```

CTAS로 복사하면 열 이름과 타입, 데이터가 복사되지만, 제약 조건은 **NOT NULL만** 따라온다. PRIMARY KEY, UNIQUE, CHECK, FOREIGN KEY, DEFAULT는 복사되지 않으니 필요하면 ALTER TABLE로 다시 추가해야 한다. SQL Server에서는 `SELECT * INTO EMP_BAK FROM EMP;`로 같은 일을 한다.

> **쉬운 설명**
>
> DDL은 서랍장을 만드는 일이고, DML은 서랍에 물건을 넣는 일이다. 제약 조건은 서랍마다 붙인 규칙이다. '이 칸은 비워 두면 안 됨'(NOT NULL), '같은 이름표 두 개 금지'(UNIQUE), '가격은 0 이상만'(CHECK), '부서 서랍에 있는 부서 번호만 적기'(FOREIGN KEY)처럼. CTAS로 서랍장을 복사하면 서랍과 물건은 그대로 오지만, 규칙표는 '비우면 안 됨' 하나만 따라온다.

## 헷갈렸던 것들

- PRIMARY KEY는 테이블에 하나만 있고, UNIQUE와 NOT NULL을 합친 것과 같다.
- UNIQUE 열에는 NULL이 들어갈 수 있다.
- 외래키는 NULL을 허용하고, ON DELETE CASCADE는 부모를 지우면 자식도 지운다.
- CTAS는 NOT NULL 제약만 복사한다.
- Oracle은 `MODIFY`, SQL Server는 `ALTER COLUMN`이다.
- 테이블 이름은 숫자로 시작할 수 없다.
- DDL은 Oracle에서 자동 COMMIT되어 ROLLBACK할 수 없다.
- 열의 크기를 줄이려면 기존 데이터가 그 크기에 맞아야 한다.

## 용어 정리

| 용어 | 뜻 |
|---|---|
| DDL | 데이터 정의어. CREATE, ALTER, DROP, RENAME, TRUNCATE |
| 제약 조건 | 잘못된 데이터가 들어오지 않게 막는 규칙 |
| 참조 무결성 | 외래키 값은 부모 테이블에 있는 값이어야 한다는 규칙 |
| ON DELETE CASCADE | 부모 삭제 시 자식도 삭제 |
| CTAS | SELECT 결과로 새 테이블을 만드는 문법 |

## 복습 문제

**1.** PRIMARY KEY 제약에 대한 설명으로 옳지 않은 것은?

① UNIQUE 제약처럼 NULL을 여러 개 넣을 수 있다 ② 테이블에 하나만 만들 수 있다 ③ NULL을 허용하지 않는다 ④ 값이 중복될 수 없다

**2.** `CREATE TABLE T2 AS SELECT * FROM T1;`을 실행했을 때 T2에 복사되는 제약 조건은?

① PRIMARY KEY ② NOT NULL ③ FOREIGN KEY ④ CHECK

**3.** Oracle에서 열의 데이터 타입이나 크기를 바꾸는 문법은?

① `ALTER TABLE T MODIFY (C VARCHAR2(20));` ② `ALTER TABLE T ALTER COLUMN C VARCHAR2(20);` ③ `ALTER TABLE T CHANGE C VARCHAR2(20);` ④ `UPDATE TABLE T SET C VARCHAR2(20);`

**4.** 부모 테이블의 행을 지우면 그 행을 참조하는 자식 테이블의 외래키 값을 NULL로 바꾸는 옵션은?

① ON DELETE CASCADE ② ON DELETE SET NULL ③ ON DELETE RESTRICT ④ ON DELETE NO ACTION

**5.** 다음 가운데 테이블 이름으로 쓸 수 없는 것은?

① 2024_EMP ② EMP_2024 ③ T$TEMP ④ EMP#1

## 답과 풀이

1. ① PRIMARY KEY는 NULL을 허용하지 않는다.
2. ② CTAS는 NOT NULL 제약만 복사한다.
3. ① Oracle은 MODIFY, SQL Server는 ALTER COLUMN이다.
4. ② ON DELETE SET NULL이다.
5. ① 테이블 이름은 숫자로 시작할 수 없다.

## 참고 자료

- 한국데이터산업진흥원 데이터자격검정, SQLD 출제기준: <https://www.dataq.or.kr>
- Oracle Database SQL Language Reference, CREATE TABLE: <https://docs.oracle.com/en/database/oracle/oracle-database/23/sqlrf/CREATE-TABLE.html>

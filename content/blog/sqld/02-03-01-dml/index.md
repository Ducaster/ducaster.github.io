---
title: '[SQLD] DML: INSERT, UPDATE, DELETE, MERGE'
date: '2024-11-30T23:44:00+09:00'
categories:
- SQLD
tags:
- sqld
- sql
- dml
- insert
- update
- delete
- merge
- truncate
- 관리 구문
series:
- SQLD
series_order: 28
---

2과목 '관리 구문' 첫 번째, DML. MERGE의 동작과 DELETE, TRUNCATE, DROP의 차이가 자주 나온다. 예제는 EMP에서 개발부 사원만 복사한 EMP_COPY 테이블로 실행했다.

## 요약

- DML은 테이블의 데이터를 넣고(INSERT), 고치고(UPDATE), 지우고(DELETE), 합치는(MERGE) 명령어다. 넓게는 SELECT도 DML에 넣는다.
- Oracle에서는 DML을 실행한 뒤 COMMIT해야 변경이 확정되고, 그 전에는 ROLLBACK으로 되돌릴 수 있다.
- MERGE는 조건에 맞는 행이 있으면 UPDATE, 없으면 INSERT를 한 문장으로 처리한다.
- DELETE는 DML이라 되돌릴 수 있지만, TRUNCATE와 DROP은 DDL이라 자동으로 COMMIT된다.

## 1. 실습 테이블

```sql
CREATE TABLE EMP_COPY AS
SELECT EMPNO, ENAME, DEPTNO, SAL FROM EMP WHERE DEPTNO = 20;
```

| EMPNO | ENAME | DEPTNO | SAL |
|---|---|---|---|
| 1002 | 이부장 | 20 | 6000 |
| 1004 | 최과장 | 20 | 4500 |
| 1005 | 정대리 | 20 | 3500 |
| 1006 | 강사원 | 20 | 3000 |

## 2. INSERT

```sql
-- 열 목록을 쓰는 방식
INSERT INTO EMP_COPY (EMPNO, ENAME, DEPTNO, SAL) VALUES (1011, '한신입', 20, 2500);
```

아래 두 문장은 다른 형식을 보여 주는 예다. 이어지는 예제 결과에는 위의 한신입 한 행만 반영했다.

```sql
-- 열 목록을 생략하는 방식: 테이블의 모든 열에 정의 순서대로 값을 넣어야 한다
INSERT INTO EMP_COPY VALUES (1013, '서인턴', 20, 2000);

-- 서브쿼리로 여러 행을 한 번에
INSERT INTO EMP_COPY SELECT EMPNO, ENAME, DEPTNO, SAL FROM EMP WHERE DEPTNO = 10;
```

- 열 목록을 쓰면 목록에 없는 열에는 NULL(또는 DEFAULT 값)이 들어간다. 단, NOT NULL 열을 빼면 오류다.
- 열 목록과 VALUES의 개수, 순서, 타입이 맞아야 한다.
- 문자와 날짜 값은 작은따옴표로 감싼다.
- 서브쿼리 INSERT에는 VALUES를 쓰지 않는다.

Oracle에서는 `INSERT ALL`로 한 번에 여러 테이블이나 여러 행에 넣을 수도 있다.

## 3. UPDATE

```sql
UPDATE EMP_COPY SET SAL = SAL * 1.1 WHERE SAL < 4000;   -- 3행 수정
```

| EMPNO | ENAME | DEPTNO | SAL |
|---|---|---|---|
| 1002 | 이부장 | 20 | 6000 |
| 1004 | 최과장 | 20 | 4500 |
| 1005 | 정대리 | 20 | 3850 |
| 1006 | 강사원 | 20 | 3300 |
| 1011 | 한신입 | 20 | 2750 |

- 여러 열을 한 번에 바꿀 때는 쉼표로 잇는다(`SET SAL = 4000, DEPTNO = 30`).
- **WHERE 절을 빠뜨리면 모든 행이 바뀐다.**
- SET 절과 WHERE 절에 서브쿼리를 쓸 수 있다(`SET SAL = (SELECT AVG(SAL) FROM EMP)`).

## 4. DELETE

```sql
DELETE FROM EMP_COPY WHERE EMPNO = 1011;   -- 1행 삭제
```

- `FROM`은 Oracle에서 생략할 수 있다(`DELETE EMP_COPY WHERE ...`).
- WHERE 절을 빠뜨리면 모든 행이 지워지지만, 테이블 구조는 남는다.
- DELETE는 행을 지워도 테이블이 차지한 저장 공간을 바로 돌려주지 않는다.

## 5. MERGE

새로 들어온 데이터(NEW_DATA)를 EMP_COPY에 반영한다. 같은 사원번호가 있으면 급여를 고치고, 없으면 새로 넣는다.

| NEW_DATA의 EMPNO | ENAME | DEPTNO | SAL |
|---|---|---|---|
| 1004 | 최과장 | 20 | 5000 |
| 1012 | 오경력 | 20 | 4200 |

```sql
MERGE INTO EMP_COPY T                        -- 대상 테이블
USING NEW_DATA S                             -- 원본(테이블, 뷰, 서브쿼리)
   ON (T.EMPNO = S.EMPNO)                    -- 일치 조건
 WHEN MATCHED THEN                           -- 일치하면
      UPDATE SET T.SAL = S.SAL
 WHEN NOT MATCHED THEN                       -- 일치하지 않으면
      INSERT (EMPNO, ENAME, DEPTNO, SAL)
      VALUES (S.EMPNO, S.ENAME, S.DEPTNO, S.SAL);
```

| EMPNO | ENAME | DEPTNO | SAL |
|---|---|---|---|
| 1002 | 이부장 | 20 | 6000 |
| 1004 | 최과장 | 20 | 5000 |
| 1005 | 정대리 | 20 | 3850 |
| 1006 | 강사원 | 20 | 3300 |
| 1012 | 오경력 | 20 | 4200 |

최과장(1004)은 일치해서 급여가 4500에서 5000으로 바뀌었고, 오경력(1012)은 일치하는 행이 없어 새로 들어갔다.

- ON 절에 쓴 열은 UPDATE SET 절에서 바꿀 수 없다.
- WHEN MATCHED와 WHEN NOT MATCHED 가운데 하나만 써도 된다.
- Oracle은 `WHEN MATCHED THEN UPDATE ... DELETE WHERE 조건`으로, 수정한 뒤 조건에 맞는 행을 지울 수도 있다.

## 6. DELETE, TRUNCATE, DROP 비교

| 구분 | DELETE | TRUNCATE | DROP |
|---|---|---|---|
| 명령어 종류 | DML | DDL | DDL |
| 지우는 범위 | 조건에 맞는 행(WHERE 사용 가능) | 모든 행 | 테이블 전체(구조와 데이터) |
| 테이블 구조 | 남는다 | 남는다 | 없어진다 |
| COMMIT | 직접 해야 한다 | 자동(Auto Commit) | 자동(Auto Commit) |
| ROLLBACK | 가능 | 불가 | 불가 |
| 저장 공간 | 바로 반환하지 않는다 | 반환한다(최초 상태로) | 모두 반환한다 |
| 속도 | 행마다 로그를 남겨 느리다 | 빠르다 | 빠르다 |

SQL Server는 기본이 자동 커밋 모드라 DML도 실행 즉시 확정된다. 명시적 트랜잭션(`BEGIN TRAN`)을 열면 TRUNCATE도 ROLLBACK할 수 있다.

> **쉬운 설명**
>
> 공책으로 비유하면 DELETE는 지우개로 원하는 줄만 지우기(아직 볼펜으로 덮어쓰지 않아 되살릴 수 있음), TRUNCATE는 공책의 모든 페이지를 뜯어내고 표지는 남기기, DROP은 공책을 통째로 버리기다. MERGE는 출석부를 새 명단과 비교해, 이미 있는 학생은 정보를 고치고 없는 학생은 새로 적는 일이다.

## 헷갈렸던 것들

- UPDATE와 DELETE에서 WHERE 절을 빠뜨리면 모든 행이 대상이 된다.
- INSERT에서 열 목록을 생략하면 모든 열에 값을 줘야 한다.
- MERGE는 일치하면 UPDATE, 일치하지 않으면 INSERT이다. ON 절의 열은 UPDATE할 수 없다.
- TRUNCATE는 DDL이라 Oracle에서 ROLLBACK할 수 없다.
- DELETE는 구조를 남기고 데이터만, DROP은 구조까지 지운다.

## 용어 정리

| 용어 | 뜻 |
|---|---|
| INSERT | 행을 넣는 명령어 |
| UPDATE | 행의 값을 고치는 명령어 |
| DELETE | 행을 지우는 명령어 |
| MERGE | 조건에 따라 UPDATE와 INSERT를 한 번에 하는 명령어 |
| TRUNCATE | 테이블의 모든 행을 지우는 DDL |

## 복습 문제

**1.** 다음 가운데 ROLLBACK으로 되돌릴 수 있는 것은? (Oracle 기준)

① DELETE ② TRUNCATE ③ DROP ④ CREATE

**2.** MERGE 문에 대한 설명으로 옳지 않은 것은?

① 일치하는 행이 있으면 UPDATE한다 ② ON 절에 쓴 열도 UPDATE SET에서 바꿀 수 있다 ③ 일치하는 행이 없으면 INSERT한다 ④ USING 절에 서브쿼리를 쓸 수 있다

**3.** 테이블 구조는 남기고 모든 데이터를 빠르게 지우며, 저장 공간도 반환하는 명령어는?

① TRUNCATE ② DELETE ③ DROP ④ UPDATE

**4.** EMP_COPY에 4행이 있을 때 다음을 실행한 뒤의 행 수는?

```sql
INSERT INTO EMP_COPY VALUES (2001, 'A', 20, 1000);
DELETE FROM EMP_COPY WHERE SAL > 5000;
```

(기존 4행 가운데 SAL이 5000을 넘는 행은 1행)

① 3 ② 4 ③ 5 ④ 6

## 답과 풀이

1. ① DELETE는 DML이라 COMMIT 전에 ROLLBACK할 수 있다.
2. ② ON 절에 쓴 열은 UPDATE할 수 없다.
3. ① TRUNCATE이다.
4. ② 4 + 1 − 1 = 4행이다.

## 참고 자료

- 한국데이터산업진흥원 데이터자격검정, SQLD 출제기준: <https://www.dataq.or.kr>
- Oracle Database SQL Language Reference, MERGE: <https://docs.oracle.com/en/database/oracle/oracle-database/23/sqlrf/MERGE.html>

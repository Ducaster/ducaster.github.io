---
title: '[SQLD] GROUP BY, HAVING 절: 집계 함수와 SELECT 문의 실행 순서'
date: '2024-11-15T19:04:00+09:00'
categories:
- SQLD
tags:
- sqld
- sql
- group-by
- having
- 집계함수
- count
- 실행순서
- SQL 기본
series:
- SQLD
series_order: 16
---

SQL 기본 다섯 번째, GROUP BY와 HAVING. WHERE와 HAVING의 차이, SELECT 문의 논리적 실행 순서, 집계 함수가 NULL과 빈 집합을 처리하는 방식이 자주 나온다. 결과는 예제 테이블로 직접 돌려 본 것.

## 요약

- 집계 함수는 여러 행을 묶어 하나의 결과를 낸다. COUNT(*)를 빼면 NULL은 계산에서 빠진다.
- GROUP BY는 행을 그룹으로 나누고, 집계 함수는 그룹마다 결과를 낸다.
- WHERE는 그룹을 만들기 **전에** 행을 거르고, HAVING은 그룹을 만든 **뒤에** 그룹을 거른다.
- SELECT 문은 FROM → WHERE → GROUP BY → HAVING → SELECT → ORDER BY 순서로 실행된다.

## 1. 집계 함수

| 함수 | 뜻 |
|---|---|
| COUNT(*) | NULL을 포함한 행의 개수 |
| COUNT(열) | 열 값이 NULL이 아닌 행의 개수 |
| SUM(열), AVG(열) | 합계, 평균(NULL 제외) |
| MAX(열), MIN(열) | 최댓값, 최솟값. 문자와 날짜에도 쓸 수 있다 |
| STDDEV(열), VARIANCE(열) | 표준편차, 분산(SQL Server는 STDEV, VAR) |

집계 함수 안에 `DISTINCT`를 쓰면 중복을 뺀 값으로 계산한다.

```sql
SELECT COUNT(*) AS A, COUNT(DISTINCT JOB) AS B, COUNT(DISTINCT DEPTNO) AS C FROM EMP;
```

| A | B | C |
|---|---|---|
| 10 | 6 | 3 |

부서번호는 10, 20, 30, NULL 네 종류지만 `COUNT(DISTINCT DEPTNO)`는 NULL을 빼고 3이다.

## 2. GROUP BY

```sql
SELECT DEPTNO, COUNT(*) AS 인원, SUM(SAL) AS 합계, ROUND(AVG(SAL), 1) AS 평균,
       MAX(SAL) AS 최대, MIN(SAL) AS 최소
  FROM EMP
 GROUP BY DEPTNO
 ORDER BY DEPTNO;
```

| DEPTNO | 인원 | 합계 | 평균 | 최대 | 최소 |
|---|---|---|---|---|---|
| 10 | 1 | 9000 | 9000 | 9000 | 9000 |
| 20 | 4 | 17000 | 4250 | 6000 | 3000 |
| 30 | 4 | 15800 | 3950 | 5800 | 2800 |
| (NULL) | 1 | 2800 | 2800 | 2800 | 2800 |

- GROUP BY의 기준 열에 NULL이 있으면, NULL끼리 하나의 그룹이 된다(임사원).
- SELECT 절에는 **GROUP BY에 쓴 열**과 **집계 함수**만 쓸 수 있다. 위 쿼리에 `ENAME`을 넣으면 그룹마다 이름이 여러 개라 오류가 난다.
- GROUP BY 절에는 SELECT 절의 별칭을 쓸 수 없다.

## 3. HAVING

```sql
SELECT DEPTNO, COUNT(*) AS 인원
  FROM EMP
 WHERE SAL >= 3000          -- ① 그룹을 만들기 전에 행을 거른다
 GROUP BY DEPTNO
HAVING COUNT(*) >= 2        -- ② 그룹을 만든 뒤 그룹을 거른다
 ORDER BY DEPTNO;
```

| DEPTNO | 인원 |
|---|---|
| 20 | 4 |
| 30 | 3 |

1. WHERE로 급여 3000 미만인 장사원과 임사원(각 2800)을 먼저 뺀다.
2. 남은 행을 부서별로 묶는다. 10번은 1명, 20번은 4명, 30번은 3명이다.
3. HAVING으로 2명 이상인 그룹만 남긴다.

```sql
SELECT JOB, SUM(SAL) AS 합계 FROM EMP GROUP BY JOB HAVING SUM(SAL) > 8000 ORDER BY 합계 DESC;
```

| JOB | 합계 |
|---|---|
| MANAGER | 11800 |
| SALESMAN | 10000 |
| PRESIDENT | 9000 |

| 구분 | WHERE | HAVING |
|---|---|---|
| 대상 | 개별 행 | 그룹 |
| 실행 시점 | GROUP BY 전 | GROUP BY 후 |
| 집계 함수 | 쓸 수 없다 | 쓸 수 있다 |

집계 함수가 필요 없는 조건(예: `DEPTNO = 20`)은 HAVING보다 WHERE에 쓰는 것이 좋다. 미리 행을 줄여 두면 그룹을 만드는 작업이 가벼워지기 때문이다. GROUP BY 없이 HAVING만 써도 되는데, 이때는 테이블 전체가 하나의 그룹이 된다.

## 4. 빈 집합과 집계

```sql
SELECT COUNT(*) AS CNT, SUM(SAL) AS S, MAX(SAL) AS M FROM EMP WHERE DEPTNO = 40;
```

| CNT | S | M |
|---|---|---|
| 0 | (NULL) | (NULL) |

조건에 맞는 행이 하나도 없어도 GROUP BY가 없으면 결과는 **한 행**이 나온다. COUNT는 0, 나머지 집계 함수는 NULL이다. 그런데 같은 조건에 `GROUP BY DEPTNO`를 붙이면 만들 그룹이 없어서 결과가 **0행**이다.

## 5. SELECT 문의 논리적 실행 순서

{{< mermaid >}}
flowchart LR
  F["① FROM<br>테이블 가져오기"] --> W["② WHERE<br>행 거르기"]
  W --> G["③ GROUP BY<br>그룹 만들기"]
  G --> H["④ HAVING<br>그룹 거르기"]
  H --> S["⑤ SELECT<br>열 고르고 계산"]
  S --> O["⑥ ORDER BY<br>정렬"]
{{< /mermaid >}}

이 순서 때문에 SELECT 절의 별칭은 ORDER BY에서만 쓸 수 있고, WHERE와 GROUP BY와 HAVING에서는 쓸 수 없다. WHERE 절에 집계 함수를 쓸 수 없는 이유도 그룹이 아직 만들어지지 않았기 때문이다.

> **쉬운 설명**
>
> 반별 시험 평균을 구하는 과정과 같다. 결시생을 먼저 빼고(WHERE), 학생을 반별로 모으고(GROUP BY), 평균을 계산한 뒤 '평균 80점 이상인 반'만 남기고(HAVING), 보여 줄 칸을 정해(SELECT), 순서대로 정렬한다(ORDER BY). 결시생 빼기는 반을 나누기 전에, 반 평균으로 거르기는 반을 나눈 뒤에만 할 수 있다.

## 헷갈렸던 것들

- GROUP BY를 쓰면 SELECT 절에는 GROUP BY 열과 집계 함수만 쓸 수 있다.
- WHERE 절에는 집계 함수를 쓸 수 없다. 집계 조건은 HAVING에 쓴다.
- 실행 순서는 FROM → WHERE → GROUP BY → HAVING → SELECT → ORDER BY이다.
- GROUP BY 열의 NULL은 하나의 그룹이 된다.
- `COUNT(DISTINCT 열)`은 NULL을 세지 않는다.
- 조건에 맞는 행이 없을 때 GROUP BY가 없으면 COUNT는 0을 돌려주지만, GROUP BY가 있으면 결과 행이 없다.

## 용어 정리

| 용어 | 뜻 |
|---|---|
| 집계 함수 | 여러 행을 묶어 하나의 값을 내는 함수 |
| GROUP BY | 행을 그룹으로 나누는 절 |
| HAVING | 그룹에 조건을 거는 절 |
| 논리적 실행 순서 | FROM → WHERE → GROUP BY → HAVING → SELECT → ORDER BY |

## 복습 문제

**1.** 다음 SQL 가운데 오류가 나는 것은?

① `SELECT DEPTNO, COUNT(*) FROM EMP GROUP BY DEPTNO;` ② `SELECT DEPTNO, ENAME, COUNT(*) FROM EMP GROUP BY DEPTNO;` ③ `SELECT COUNT(*) FROM EMP HAVING COUNT(*) > 5;` ④ `SELECT JOB, MAX(SAL) FROM EMP GROUP BY JOB HAVING MAX(SAL) > 3000;`

**2.** SELECT 문의 논리적 실행 순서로 옳은 것은?

① SELECT → FROM → WHERE → GROUP BY ② FROM → GROUP BY → WHERE → HAVING → SELECT ③ FROM → WHERE → GROUP BY → HAVING → SELECT → ORDER BY ④ FROM → WHERE → HAVING → GROUP BY → SELECT

**3.** COL1 값이 10, NULL, 10, 20인 테이블에서 `SELECT COUNT(DISTINCT COL1) FROM T;`의 결과는?

① 3 ② 4 ③ 2 ④ NULL

**4.** 행이 하나도 없는 테이블 T에서 `SELECT COUNT(*), SUM(COL1) FROM T;`의 결과는?

① 0, NULL ② 결과 행이 없다 ③ 0, 0 ④ NULL, NULL

## 답과 풀이

1. ② ENAME은 GROUP BY에도 없고 집계 함수도 아니어서 오류다. ③은 테이블 전체를 한 그룹으로 보는 HAVING이라 정상이다.
2. ③ FROM → WHERE → GROUP BY → HAVING → SELECT → ORDER BY이다.
3. ③ NULL을 빼고 10, 20 두 가지다.
4. ① GROUP BY가 없으면 한 행이 나오고, COUNT는 0, SUM은 NULL이다.

## 참고 자료

- 한국데이터산업진흥원 데이터자격검정, SQLD 출제기준: <https://www.dataq.or.kr>
- Oracle Database SQL Language Reference, Aggregate Functions: <https://docs.oracle.com/en/database/oracle/oracle-database/23/sqlrf/Aggregate-Functions.html>

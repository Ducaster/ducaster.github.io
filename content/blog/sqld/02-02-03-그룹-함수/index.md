---
title: '[SQLD] 그룹 함수: ROLLUP, CUBE, GROUPING SETS, GROUPING'
date: '2024-11-23T21:45:00+09:00'
categories:
- SQLD
tags:
- sqld
- sql
- 그룹함수
- rollup
- cube
- grouping-sets
- grouping
- 소계
- SQL 활용
series:
- SQLD
series_order: 22
---

ROLLUP, CUBE, GROUPING SETS가 각각 어떤 소계를 만들고 결과가 몇 행인지 묻는 문제가 많다. 행 수를 세기 쉽게 EMP에서 개발부(20)와 영업부(30)만 뽑아서 돌렸다.

## 요약

- 그룹 함수는 GROUP BY 한 번으로 여러 수준의 소계와 총계를 만든다.
- ROLLUP(A, B)는 (A, B), (A), 전체의 계층적 소계를 만든다. 인수 순서가 바뀌면 결과도 바뀐다.
- CUBE(A, B)는 가능한 모든 조합 (A, B), (A), (B), 전체를 만든다.
- GROUPING SETS(A, B)는 지정한 그룹(A), (B)별 집계만 만들고, 총계는 넣지 않는다.
- GROUPING(열)은 그 열이 소계를 위해 묶였으면 1, 아니면 0을 돌려준다.

## 1. 기준 데이터

| DEPTNO | JOB | SAL 합계 |
|---|---|---|
| 20 | ANALYST | 4500 |
| 20 | DEVELOPER | 6500 |
| 20 | MANAGER | 6000 |
| 30 | MANAGER | 5800 |
| 30 | SALESMAN | 10000 |

일반 `GROUP BY DEPTNO, JOB`은 위의 5행만 만든다. 그룹 함수를 쓰면 여기에 소계 행이 붙는다.

## 2. ROLLUP

```sql
SELECT DEPTNO, JOB, SUM(SAL) AS SUM_SAL
  FROM EMP
 WHERE DEPTNO IN (20, 30)
 GROUP BY ROLLUP(DEPTNO, JOB)
 ORDER BY DEPTNO, JOB;
```

| DEPTNO | JOB | SUM_SAL |
|---|---|---|
| 20 | ANALYST | 4500 |
| 20 | DEVELOPER | 6500 |
| 20 | MANAGER | 6000 |
| 20 | (NULL) | 17000 |
| 30 | MANAGER | 5800 |
| 30 | SALESMAN | 10000 |
| 30 | (NULL) | 15800 |
| (NULL) | (NULL) | 32800 |

- (DEPTNO, JOB)별 집계 5행, DEPTNO별 소계 2행, 전체 총계 1행으로 모두 8행이다.
- 소계 행에서 묶인 열(JOB)은 NULL로 표시된다.
- ROLLUP은 **계층 구조**라 인수 순서가 중요하다. `ROLLUP(JOB, DEPTNO)`로 바꾸면 직무별 소계가 만들어진다.
- 인수가 N개면 N + 1가지 수준의 집계가 만들어진다.

## 3. CUBE

```sql
SELECT DEPTNO, JOB, SUM(SAL) AS SUM_SAL
  FROM EMP
 WHERE DEPTNO IN (20, 30)
 GROUP BY CUBE(DEPTNO, JOB)
 ORDER BY DEPTNO, JOB;
```

| DEPTNO | JOB | SUM_SAL |
|---|---|---|
| 20 | ANALYST | 4500 |
| 20 | DEVELOPER | 6500 |
| 20 | MANAGER | 6000 |
| 20 | (NULL) | 17000 |
| 30 | MANAGER | 5800 |
| 30 | SALESMAN | 10000 |
| 30 | (NULL) | 15800 |
| (NULL) | ANALYST | 4500 |
| (NULL) | DEVELOPER | 6500 |
| (NULL) | MANAGER | 11800 |
| (NULL) | SALESMAN | 10000 |
| (NULL) | (NULL) | 32800 |

ROLLUP 결과에 **직무별 소계 4행**(MANAGER는 두 부서 합 11800)이 더해져 12행이다. CUBE는 모든 조합을 만들기 때문에 인수 순서를 바꿔도 결과 집합이 같다. 인수가 N개면 2ᴺ가지 조합의 집계가 만들어지고, 그만큼 계산 부담이 크다.

## 4. GROUPING SETS

```sql
SELECT DEPTNO, JOB, SUM(SAL) AS SUM_SAL
  FROM EMP
 WHERE DEPTNO IN (20, 30)
 GROUP BY GROUPING SETS(DEPTNO, JOB)
 ORDER BY DEPTNO, JOB;
```

| DEPTNO | JOB | SUM_SAL |
|---|---|---|
| 20 | (NULL) | 17000 |
| 30 | (NULL) | 15800 |
| (NULL) | ANALYST | 4500 |
| (NULL) | DEVELOPER | 6500 |
| (NULL) | MANAGER | 11800 |
| (NULL) | SALESMAN | 10000 |

부서별 집계와 직무별 집계만 나오고, (DEPTNO, JOB) 조합과 전체 총계는 없다. 원하는 그룹을 직접 고르는 방식이라 인수 순서는 결과 집합에 영향을 주지 않는다. 총계가 필요하면 빈 괄호를 넣는다(`GROUPING SETS(DEPTNO, JOB, ())`).

| 표현 | 같은 뜻 |
|---|---|
| ROLLUP(A, B) | GROUPING SETS((A, B), (A), ()) |
| CUBE(A, B) | GROUPING SETS((A, B), (A), (B), ()) |
| GROUPING SETS(A, B) | GROUP BY A의 결과 UNION ALL GROUP BY B의 결과 |

## 5. GROUPING 함수

소계 행의 NULL과 원래 데이터의 NULL을 구분하고, '소계', '전체' 같은 이름을 붙일 때 쓴다.

```sql
SELECT CASE GROUPING(DEPTNO) WHEN 1 THEN '전체' ELSE TO_CHAR(DEPTNO) END AS 부서,
       CASE GROUPING(JOB)    WHEN 1 THEN '소계' ELSE JOB END            AS 직무,
       GROUPING(DEPTNO) AS GD, GROUPING(JOB) AS GJ,
       SUM(SAL) AS SUM_SAL
  FROM EMP
 WHERE DEPTNO IN (20, 30)
 GROUP BY ROLLUP(DEPTNO, JOB)
 ORDER BY DEPTNO, JOB;
```

| 부서 | 직무 | GD | GJ | SUM_SAL |
|---|---|---|---|---|
| 20 | ANALYST | 0 | 0 | 4500 |
| 20 | DEVELOPER | 0 | 0 | 6500 |
| 20 | MANAGER | 0 | 0 | 6000 |
| 20 | 소계 | 0 | 1 | 17000 |
| 30 | MANAGER | 0 | 0 | 5800 |
| 30 | SALESMAN | 0 | 0 | 10000 |
| 30 | 소계 | 0 | 1 | 15800 |
| 전체 | 소계 | 1 | 1 | 32800 |

GROUPING(JOB)이 1인 행은 JOB을 묶어 만든 소계 행이다. Oracle에서는 `DECODE(GROUPING(JOB), 1, '소계', JOB)`처럼 DECODE로도 쓴다.

> **쉬운 설명**
>
> 가계부를 정리할 때 '월별, 항목별 지출' 아래에 '월 합계'를 붙이고 맨 아래에 '1년 총합'을 붙이는 게 ROLLUP이다. 여기에 '항목별 1년 합계'까지 붙이면 CUBE, '월 합계'와 '항목 합계'만 따로 뽑으면 GROUPING SETS이다.

## 헷갈렸던 것들

- ROLLUP(A, B)는 (A, B), (A), 전체다. (B)만의 소계는 없다.
- ROLLUP은 인수 순서에 따라 결과가 달라지고, CUBE와 GROUPING SETS는 결과 집합이 같다.
- CUBE(A, B)는 (A, B), (A), (B), 전체를 모두 만든다.
- GROUPING SETS(A, B)에는 전체 총계가 없다.
- GROUPING 함수는 소계를 위해 묶인 열이면 1을 돌려준다.
- 그룹 함수의 결과는 정렬이 보장되지 않으니 필요하면 ORDER BY를 쓴다.

## 용어 정리

| 용어 | 뜻 |
|---|---|
| ROLLUP | 계층적 소계와 총계 |
| CUBE | 모든 조합의 소계와 총계 |
| GROUPING SETS | 지정한 그룹별 집계 |
| GROUPING | 소계 행 여부를 0과 1로 알려 주는 함수 |

## 복습 문제

**1.** `GROUP BY ROLLUP(A, B)`가 만드는 집계 수준이 아닌 것은?

① (A, B) ② (A) ③ 전체 ④ (B)

**2.** `GROUP BY CUBE(A, B, C)`가 만드는 집계 수준의 개수는?

① 3 ② 4 ③ 6 ④ 8

**3.** 다음 가운데 인수의 순서를 바꾸면 결과가 달라지는 것은?

① ROLLUP ② CUBE ③ GROUPING SETS ④ 모두 같다

**4.** `GROUP BY GROUPING SETS(DEPTNO, JOB)`과 같은 결과를 내는 것은?

① `GROUP BY DEPTNO, JOB` ② `GROUP BY ROLLUP(DEPTNO, JOB)` ③ `GROUP BY CUBE(DEPTNO, JOB)` ④ `GROUP BY DEPTNO` 결과 UNION ALL `GROUP BY JOB` 결과

## 답과 풀이

1. ④ ROLLUP(A, B)는 (A, B), (A), 전체만 만든다.
2. ④ 2³ = 8가지다.
3. ① ROLLUP은 계층적이라 순서가 중요하다.
4. ④ GROUPING SETS는 지정한 그룹별 집계를 합친 것과 같다.

## 참고 자료

- 한국데이터산업진흥원 데이터자격검정, SQLD 출제기준: <https://www.dataq.or.kr>
- Oracle Database Data Warehousing Guide, SQL for Aggregation in Data Warehouses: <https://docs.oracle.com/en/database/oracle/oracle-database/23/dwhsg/sql-aggregation-data-warehouses.html>

---
title: '[SQLD] ORDER BY 절: 정렬 방법과 NULL의 정렬 순서'
date: '2024-11-15T19:52:00+09:00'
categories:
- SQLD
tags:
- sqld
- sql
- order-by
- 정렬
- nulls-first
- nulls-last
- SQL 기본
series:
- SQLD
series_order: 17
---

SQL 기본 여섯 번째, ORDER BY. 정렬 기준을 지정하는 세 가지 방법, Oracle과 SQL Server에서 NULL이 어디로 정렬되는지가 단골이다. 결과는 예제 테이블로 직접 실행한 것.

## 요약

- ORDER BY는 결과를 정렬하고, SELECT 문에서 가장 마지막에 실행된다.
- 정렬 기준은 열 이름, SELECT 절의 별칭, SELECT 절의 열 순서 번호로 지정할 수 있다.
- 기본은 오름차순(ASC)이고, 내림차순은 DESC이다.
- Oracle은 NULL을 가장 큰 값으로, SQL Server는 가장 작은 값으로 정렬한다.

## 1. 기본 문법

```sql
SELECT ...
  FROM ...
 ORDER BY 기준1 [ASC | DESC], 기준2 [ASC | DESC], ...;
```

```sql
SELECT ENAME, DEPTNO, SAL FROM EMP ORDER BY DEPTNO, SAL DESC;
```

| ENAME | DEPTNO | SAL |
|---|---|---|
| 김대표 | 10 | 9000 |
| 이부장 | 20 | 6000 |
| 최과장 | 20 | 4500 |
| 정대리 | 20 | 3500 |
| 강사원 | 20 | 3000 |
| 박부장 | 30 | 5800 |
| 조과장 | 30 | 4000 |
| 윤대리 | 30 | 3200 |
| 장사원 | 30 | 2800 |
| 임사원 | (NULL) | 2800 |

부서번호 오름차순으로 먼저 정렬하고, 부서번호가 같으면 급여 내림차순으로 정렬했다. ASC, DESC는 바로 앞의 기준 하나에만 적용된다. `ORDER BY DEPTNO, SAL DESC`에서 DEPTNO는 기본값인 ASC이다.

## 2. 정렬 기준을 지정하는 방법

| 방법 | 예 |
|---|---|
| 열 이름 | `ORDER BY SAL` |
| SELECT 절의 별칭 | `ORDER BY 연봉` |
| SELECT 절의 열 순서 번호 | `ORDER BY 3` (세 번째 열) |

```sql
SELECT ENAME, SAL * 12 AS 연봉 FROM EMP WHERE DEPTNO = 20 ORDER BY 연봉;
```

| ENAME | 연봉 |
|---|---|
| 강사원 | 36000 |
| 정대리 | 42000 |
| 최과장 | 54000 |
| 이부장 | 72000 |

```sql
SELECT ENAME, JOB, SAL FROM EMP WHERE DEPTNO = 30 ORDER BY 3 DESC, 1;
```

| ENAME | JOB | SAL |
|---|---|---|
| 박부장 | MANAGER | 5800 |
| 조과장 | SALESMAN | 4000 |
| 윤대리 | SALESMAN | 3200 |
| 장사원 | SALESMAN | 2800 |

세 방법은 섞어 쓸 수 있다. 열 순서 번호는 SELECT 절에 있는 열 개수 안에서만 쓸 수 있다. `SELECT ENAME, SAL ... ORDER BY 3`은 오류다.

SELECT 절에 없는 열로도 정렬할 수 있다(`SELECT ENAME FROM EMP ORDER BY SAL`). 단, GROUP BY를 쓴 쿼리에서는 GROUP BY 열이나 집계 함수로만 정렬할 수 있다.

## 3. NULL의 정렬 순서

| DBMS | NULL을 보는 방식 | 오름차순(ASC) | 내림차순(DESC) |
|---|---|---|---|
| Oracle | 가장 큰 값 | 맨 뒤 | 맨 앞 |
| SQL Server | 가장 작은 값 | 맨 앞 | 맨 뒤 |

```sql
SELECT ENAME, DEPTNO FROM EMP ORDER BY DEPTNO DESC, EMPNO;
```

| ENAME | DEPTNO |
|---|---|
| 임사원 | (NULL) |
| 박부장 | 30 |
| 조과장 | 30 |
| 윤대리 | 30 |
| 장사원 | 30 |
| 이부장 | 20 |
| 최과장 | 20 |
| 정대리 | 20 |
| 강사원 | 20 |
| 김대표 | 10 |

Oracle에서 내림차순이라 NULL이 맨 앞에 왔다. 위치를 직접 정하려면 Oracle의 `NULLS FIRST` 또는 `NULLS LAST`를 쓴다.

```sql
SELECT ENAME, DEPTNO FROM EMP ORDER BY DEPTNO NULLS FIRST, EMPNO;
```

| ENAME | DEPTNO |
|---|---|
| 임사원 | (NULL) |
| 김대표 | 10 |
| 이부장 | 20 |
| 최과장 | 20 |
| 정대리 | 20 |
| 강사원 | 20 |
| 박부장 | 30 |
| 조과장 | 30 |
| 윤대리 | 30 |
| 장사원 | 30 |

## 4. ORDER BY와 실행 순서

ORDER BY는 SELECT 다음, 가장 마지막에 실행된다. 그래서 SELECT 절의 별칭을 쓸 수 있다. 대신 정렬은 결과 전체를 모아야 할 수 있어 데이터가 많으면 비용이 크다. 꼭 필요할 때만 쓰는 것이 좋다.

> **쉬운 설명**
>
> 반 학생들을 '번호순으로, 번호가 같으면 키 큰 순으로' 세우는 것과 같다. Oracle은 키를 안 잰 학생(NULL)을 '가장 큰 학생'으로 보고 작은 순 줄의 맨 뒤에 세우고, SQL Server는 '가장 작은 학생'으로 보고 맨 앞에 세운다.

## 헷갈렸던 것들

- 기본 정렬은 오름차순(ASC)이고, ASC/DESC는 바로 앞 기준에만 적용된다.
- 별칭과 열 순서 번호로 정렬할 수 있다. 순서 번호는 SELECT 절 열 개수를 넘을 수 없다.
- Oracle은 NULL이 가장 크다고 보고, SQL Server는 가장 작다고 본다.
- ORDER BY는 가장 마지막에 실행된다.
- GROUP BY가 있으면 ORDER BY에는 GROUP BY 열이나 집계 함수만 쓸 수 있다.

## 용어 정리

| 용어 | 뜻 |
|---|---|
| ASC / DESC | 오름차순 / 내림차순 |
| NULLS FIRST / NULLS LAST | NULL을 맨 앞 / 맨 뒤에 정렬(Oracle) |

## 복습 문제

**1.** Oracle에서 COL1 값이 3, NULL, 1, 2일 때 `ORDER BY COL1 DESC`의 결과 순서는?

① 3, 2, 1, NULL ② 1, 2, 3, NULL ③ NULL, 3, 2, 1 ④ NULL, 1, 2, 3

**2.** 다음 SQL에서 오류가 나는 것은?

① `SELECT ENAME, SAL FROM EMP ORDER BY 3;` ② `SELECT ENAME, SAL FROM EMP ORDER BY 2;` ③ `SELECT ENAME, SAL AS 급여 FROM EMP ORDER BY 급여;` ④ `SELECT ENAME FROM EMP ORDER BY SAL;`

**3.** SQL Server에서 COL1 값이 3, NULL, 1일 때 `ORDER BY COL1`의 결과 순서는?

① 1, 3, NULL ② 3, 1, NULL ③ NULL, 1, 3 ④ NULL, 3, 1

## 답과 풀이

1. ③ Oracle은 NULL을 가장 큰 값으로 보므로 내림차순에서 맨 앞이다.
2. ① SELECT 절의 열은 두 개뿐이라 3번째 열이 없다.
3. ③ SQL Server는 NULL을 가장 작은 값으로 보므로 오름차순에서 맨 앞이다.

## 참고 자료

- 한국데이터산업진흥원 데이터자격검정, SQLD 출제기준: <https://www.dataq.or.kr>
- Oracle Database SQL Language Reference, SELECT(order_by_clause): <https://docs.oracle.com/en/database/oracle/oracle-database/23/sqlrf/SELECT.html>

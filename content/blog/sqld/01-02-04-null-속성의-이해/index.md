---
title: '[SQLD] NULL 속성의 이해: NULL의 연산, 비교, 집계'
date: '2024-11-06T22:32:00+09:00'
categories:
- SQLD
tags:
- sqld
- sql
- null
- is-null
- nvl
- 집계함수
- 삼치논리
- 데이터 모델링의 이해
series:
- SQLD
series_order: 10
---

데이터 모델과 SQL 네 번째, NULL 속성. NULL이 산술 연산, 비교, 집계 함수에서 어떻게 동작하는지는 2과목 SQL 문제에서도 계속 쓰이는 기본기라 여기서 확실히 잡고 넘어갔다. 예제는 '실습 환경과 예제 데이터' 편의 EMP 테이블이고, COMM은 7명이 NULL, 1명이 0, 2명이 300과 500이다.

## 요약

- NULL은 '값이 없음' 또는 '아직 모르는 값'이다. 0이나 공백 문자와 다르다.
- NULL이 들어간 산술 연산의 결과는 NULL이다.
- NULL과의 비교는 참도 거짓도 아닌 UNKNOWN이라, `= NULL`로는 찾을 수 없고 `IS NULL`을 써야 한다.
- 집계 함수는 NULL을 빼고 계산한다. 단, `COUNT(*)`는 NULL이 있는 행도 센다.
- 모델링할 때 NULL을 허용할지(선택 속성) 막을지(NOT NULL, 필수 속성) 정해야 한다.

## 1. NULL이란

**NULL**은 값이 정해지지 않았거나 알 수 없는 상태다.

| 값 | 뜻 | 예제 데이터에서 |
|---|---|---|
| NULL | 값이 없다, 해당 없다, 모른다 | 영업 사원이 아니어서 커미션이 없음 |
| 0 | 숫자 0이라는 값이 있다 | 영업 사원인데 성과가 없어 커미션 0 |
| ' '(공백) | 공백 문자라는 값이 있다 | |

Oracle에서는 빈 문자열 `''`을 NULL로 취급한다. SQL Server는 빈 문자열과 NULL을 구분한다.

## 2. NULL과 산술 연산

NULL에 어떤 값을 더하거나 곱해도 결과는 NULL이다.

```sql
SELECT ENAME, SAL, COMM,
       SAL + COMM         AS TOTAL,
       SAL + NVL(COMM, 0) AS TOTAL_NVL
  FROM EMP
 WHERE DEPTNO = 30 OR EMPNO = 1001
 ORDER BY EMPNO;
```

| ENAME | SAL | COMM | TOTAL | TOTAL_NVL |
|---|---|---|---|---|
| 김대표 | 9000 | (NULL) | (NULL) | 9000 |
| 박부장 | 5800 | (NULL) | (NULL) | 5800 |
| 조과장 | 4000 | 500 | 4500 | 4500 |
| 윤대리 | 3200 | 300 | 3500 | 3500 |
| 장사원 | 2800 | 0 | 2800 | 2800 |

`NVL(COMM, 0)`은 COMM이 NULL이면 0으로 바꿔 준다(Oracle 함수, SQL Server는 `ISNULL`). NULL 관련 함수는 '함수' 편에서 자세히 다룬다.

## 3. NULL과 비교

NULL과 무엇을 비교하든 결과는 TRUE도 FALSE도 아닌 **UNKNOWN**이다. WHERE 절은 TRUE인 행만 돌려주므로 UNKNOWN인 행은 빠진다.

```sql
SELECT COUNT(*) FROM EMP WHERE COMM = NULL;     -- 0
SELECT COUNT(*) FROM EMP WHERE COMM IS NULL;    -- 7
SELECT COUNT(*) FROM EMP WHERE COMM <> 0;       -- 2
```

- `COMM = NULL`은 모든 행에서 UNKNOWN이라 결과가 0건이다. NULL을 찾을 때는 반드시 `IS NULL`, 아닌 것은 `IS NOT NULL`을 쓴다.
- `COMM <> 0`은 300, 500인 2명만 나온다. COMM이 NULL인 7명은 '0이 아니다'가 아니라 UNKNOWN이라 빠졌다.

### NOT IN과 NULL

```sql
SELECT ENAME, DEPTNO FROM EMP WHERE DEPTNO NOT IN (10, 20) ORDER BY EMPNO;
```

| ENAME | DEPTNO |
|---|---|
| 박부장 | 30 |
| 조과장 | 30 |
| 윤대리 | 30 |
| 장사원 | 30 |

DEPTNO가 NULL인 임사원은 나오지 않는다. 그리고 목록 안에 NULL이 들어가면 결과가 아예 비어 버린다.

```sql
SELECT ENAME FROM EMP WHERE DEPTNO NOT IN (10, NULL);   -- 0건
```

`NOT IN (10, NULL)`은 `DEPTNO <> 10 AND DEPTNO <> NULL`과 같고, 뒤쪽이 항상 UNKNOWN이라 전체가 TRUE가 될 수 없기 때문이다. 서브쿼리 결과에 NULL이 섞여 있을 때 자주 생기는 함정이다.

### 삼치 논리

| A | B | A AND B | A OR B |
|---|---|---|---|
| TRUE | UNKNOWN | UNKNOWN | TRUE |
| FALSE | UNKNOWN | FALSE | UNKNOWN |
| UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |

NOT UNKNOWN도 UNKNOWN이다.

## 4. NULL과 집계 함수

집계 함수는 NULL을 **제외**하고 계산한다.

```sql
SELECT COUNT(*)                     AS CNT_ALL,
       COUNT(COMM)                  AS CNT_COMM,
       SUM(COMM)                    AS SUM_COMM,
       ROUND(AVG(COMM), 2)          AS AVG_COMM,
       ROUND(AVG(NVL(COMM, 0)), 2)  AS AVG_NVL
  FROM EMP;
```

| CNT_ALL | CNT_COMM | SUM_COMM | AVG_COMM | AVG_NVL |
|---|---|---|---|---|
| 10 | 3 | 800 | 266.67 | 80 |

- `COUNT(*)`는 행 전체를 세서 10, `COUNT(COMM)`은 NULL이 아닌 3개만 센다.
- `AVG(COMM)`은 NULL을 뺀 3명의 평균(800 ÷ 3)이고, `AVG(NVL(COMM, 0))`은 10명 전체의 평균(800 ÷ 10)이다. 같은 데이터인데 결과가 세 배 넘게 다르다.

### 합계를 어떻게 구하느냐에 따라 달라지는 결과

```sql
SELECT SUM(SAL) AS S, SUM(COMM) AS C,
       SUM(SAL) + SUM(COMM) AS A,
       SUM(SAL + COMM)      AS B
  FROM EMP;
```

| S | C | A | B |
|---|---|---|---|
| 44600 | 800 | 45400 | 10800 |

A는 열마다 따로 합한 뒤 더해서 45,400이다. B는 행마다 `SAL + COMM`을 먼저 계산하는데, COMM이 NULL인 7명은 그 결과가 NULL이 되어 합계에서 빠진다. 그래서 커미션이 있는 3명의 합(4,500 + 3,500 + 2,800)인 10,800만 남는다.

## 5. NULL과 정렬, 모델링

| 항목 | Oracle | SQL Server |
|---|---|---|
| 정렬(ORDER BY) | NULL을 가장 큰 값으로 본다. 오름차순이면 마지막 | NULL을 가장 작은 값으로 본다. 오름차순이면 처음 |
| 빈 문자열 '' | NULL로 취급 | NULL과 다른 값 |

모델링할 때는 속성마다 NULL을 허용할지 정한다. 반드시 있어야 하는 속성(예: 사원명)은 `NOT NULL` 제약으로 막고, 없을 수 있는 속성(예: 커미션)은 NULL을 허용한다. 주식별자(PK)는 존재성 때문에 NULL일 수 없다.

> **쉬운 설명**
>
> NULL은 시험지의 '빈칸'이다. 0점이 아니라 '아직 채점 안 함'이다. 빈칸이 있는 학생의 총점은 계산할 수 없으니 NULL이 되고, '빈칸인 학생이 80점인가?'라고 물으면 '모른다'(UNKNOWN)가 답이다. 평균을 낼 때 빈칸을 빼고 나누느냐(AVG), 0점으로 치고 나누느냐(AVG(NVL))에 따라 평균이 달라진다.

## 헷갈렸던 것들

- NULL은 0이나 공백과 다르다.
- NULL이 들어간 산술 연산은 NULL이다.
- `= NULL`은 항상 결과가 없다. `IS NULL`을 쓴다.
- `COUNT(*)`는 NULL 행도 세고, `COUNT(컬럼)`은 NULL을 뺀다.
- `AVG(컬럼)`은 NULL을 뺀 개수로 나눈다.
- `SUM(A) + SUM(B)`와 `SUM(A + B)`는 NULL이 있으면 결과가 다르다.
- `NOT IN` 목록에 NULL이 있으면 결과는 0건이다.
- Oracle은 오름차순 정렬에서 NULL이 마지막, SQL Server는 처음이다.

## 용어 정리

| 용어 | 뜻 |
|---|---|
| NULL | 값이 없거나 알 수 없는 상태 |
| UNKNOWN | NULL과 비교했을 때의 결과 |
| IS NULL / IS NOT NULL | NULL 여부를 확인하는 조건 |
| NVL | NULL을 다른 값으로 바꾸는 Oracle 함수 |
| NOT NULL 제약 | 컬럼에 NULL을 허용하지 않는 제약 |

## 복습 문제

COL1 값이 10, 20, NULL, 30인 테이블 T가 있다.

**1.** `SELECT COUNT(COL1) FROM T`의 결과는?

① 1 ② 4 ③ NULL ④ 3

**2.** `SELECT AVG(COL1) FROM T`의 결과는?

① 15 ② 20 ③ 60 ④ NULL

**3.** `SELECT COUNT(*) FROM T WHERE COL1 <> 20`의 결과는?

① 1 ② 2 ③ 3 ④ 4

**4.** NULL에 대한 설명으로 옳지 않은 것은?

① NULL과 숫자를 더하면 NULL이다 ② Oracle은 빈 문자열을 NULL로 취급한다 ③ `COL1 = NULL`로 NULL인 행을 찾을 수 있다 ④ 집계 함수는 NULL을 빼고 계산한다

## 답과 풀이

1. ④ NULL을 뺀 3개다.
2. ② (10 + 20 + 30) ÷ 3 = 20이다. NULL은 개수에서도 빠진다.
3. ② 10과 30만 나온다. NULL은 UNKNOWN이라 빠진다.
4. ③ NULL은 `IS NULL`로 찾아야 한다.

## 참고 자료

- 한국데이터산업진흥원 데이터자격검정, SQLD 출제기준: <https://www.dataq.or.kr>
- Oracle Database SQL Language Reference, Nulls: <https://docs.oracle.com/en/database/oracle/oracle-database/23/sqlrf/Nulls.html>

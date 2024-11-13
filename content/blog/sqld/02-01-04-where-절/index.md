---
title: '[SQLD] WHERE 절: 비교, SQL 연산자, 논리 연산자의 우선순위'
date: '2024-11-13T20:09:00+09:00'
categories:
- SQLD
tags:
- sqld
- sql
- where
- between
- in
- like
- is-null
- 연산자우선순위
- SQL 기본
series:
- SQLD
series_order: 15
---

SQL 기본 네 번째, WHERE 절. AND와 OR의 우선순위, LIKE 와일드카드, NULL 비교가 자주 나온다. 결과는 예제 테이블로 실행한 그대로다.

## 요약

- WHERE 절은 조건에 맞는 행만 고른다. 관계 대수의 선택 연산에 해당한다.
- 연산자는 비교 연산자, SQL 연산자(BETWEEN, IN, LIKE, IS NULL), 논리 연산자(NOT, AND, OR)가 있다.
- 논리 연산자의 우선순위는 NOT → AND → OR이다. 헷갈리면 괄호를 쓰자.
- 문자열을 비교할 때 CHAR와 VARCHAR2는 공백을 다루는 방식이 다르다.

## 1. 연산자의 종류

| 구분 | 연산자 | 뜻 |
|---|---|---|
| 비교 연산자 | = , > , >= , < , <= | 같다, 크다, 크거나 같다, 작다, 작거나 같다 |
| SQL 연산자 | BETWEEN a AND b | a 이상 b 이하(양 끝 포함) |
| | IN (목록) | 목록 가운데 하나와 같다 |
| | LIKE '패턴' | 패턴과 일치한다 |
| | IS NULL | NULL이다 |
| 논리 연산자 | AND, OR, NOT | 그리고, 또는, 아니다 |
| 부정 연산자 | !=, ^=, <> | 같지 않다(<>가 ANSI 표준) |
| | NOT BETWEEN a AND b, NOT IN (목록), IS NOT NULL | 각 연산자의 부정 |

### 연산자의 우선순위

| 순위 | 연산자 |
|---|---|
| 1 | 괄호 ( ) |
| 2 | 산술 연산자 |
| 3 | 연결 연산자 |
| 4 | 비교 연산자 |
| 5 | IS NULL, LIKE, IN |
| 6 | BETWEEN |
| 7 | NOT |
| 8 | AND |
| 9 | OR |

위 표는 Oracle 문서의 순서다. SQLD 수험서는 '괄호 → NOT → 비교 연산자 → AND → OR'로 줄여 정리하기도 한다. 어느 쪽으로 외우든 시험의 핵심은 **NOT → AND → OR** 순서다.

## 2. SQL 연산자

### BETWEEN

```sql
SELECT ENAME, SAL FROM EMP WHERE SAL BETWEEN 3000 AND 4000 ORDER BY SAL;
```

| ENAME | SAL |
|---|---|
| 강사원 | 3000 |
| 윤대리 | 3200 |
| 정대리 | 3500 |
| 조과장 | 4000 |

양 끝 값 3000과 4000이 모두 포함된다. `BETWEEN 4000 AND 3000`처럼 작은 값을 뒤에 쓰면 결과가 0건이다.

### IN

```sql
SELECT ENAME, JOB FROM EMP WHERE JOB IN ('ANALYST', 'CLERK') ORDER BY EMPNO;
```

| ENAME | JOB |
|---|---|
| 최과장 | ANALYST |
| 임사원 | CLERK |

`JOB = 'ANALYST' OR JOB = 'CLERK'`과 같다. 여러 열을 함께 비교할 수도 있다(`WHERE (JOB, DEPTNO) IN (('MANAGER', 20), ('SALESMAN', 30))`).

### LIKE

| 와일드카드 | 뜻 |
|---|---|
| % | 0개 이상의 아무 문자 |
| _ | 정확히 1개의 아무 문자 |

```sql
SELECT ENAME FROM EMP WHERE ENAME LIKE '%사원' ORDER BY EMPNO;   -- '사원'으로 끝남
SELECT ENAME FROM EMP WHERE ENAME LIKE '_대%' ORDER BY EMPNO;    -- 두 번째 글자가 '대'
```

| ENAME |
|---|
| 강사원 |
| 장사원 |
| 임사원 |

| ENAME |
|---|
| 김대표 |
| 정대리 |
| 윤대리 |

%나 _ 문자 자체를 찾으려면 ESCAPE로 이스케이프 문자를 지정한다. `WHERE COL LIKE '%\_%' ESCAPE '\'`는 밑줄(_)이 들어간 값을 찾는다.

### IS NULL

NULL은 `= NULL`로 찾을 수 없고 `IS NULL`로 찾아야 한다. 자세한 내용은 'NULL 속성의 이해' 편에 있다.

## 3. 논리 연산자의 우선순위

AND가 OR보다 먼저 계산된다는 점이 가장 많이 나오는 함정이다.

```sql
SELECT ENAME, DEPTNO, SAL FROM EMP
 WHERE DEPTNO = 20 OR DEPTNO = 30 AND SAL >= 4000
 ORDER BY EMPNO;
```

| ENAME | DEPTNO | SAL |
|---|---|---|
| 이부장 | 20 | 6000 |
| 박부장 | 30 | 5800 |
| 최과장 | 20 | 4500 |
| 정대리 | 20 | 3500 |
| 강사원 | 20 | 3000 |
| 조과장 | 30 | 4000 |

이 조건은 `DEPTNO = 20 OR (DEPTNO = 30 AND SAL >= 4000)`으로 해석된다. 그래서 개발부는 급여와 관계없이 4명 모두 나왔다.

```sql
SELECT ENAME, DEPTNO, SAL FROM EMP
 WHERE (DEPTNO = 20 OR DEPTNO = 30) AND SAL >= 4000
 ORDER BY EMPNO;
```

| ENAME | DEPTNO | SAL |
|---|---|---|
| 이부장 | 20 | 6000 |
| 박부장 | 30 | 5800 |
| 최과장 | 20 | 4500 |
| 조과장 | 30 | 4000 |

괄호로 묶으면 '개발부나 영업부 가운데 급여 4000 이상'이 된다.

> **쉬운 설명**
>
> 수학에서 곱셈을 덧셈보다 먼저 하듯이, SQL에서는 AND를 OR보다 먼저 한다. '사과 또는 배이면서 빨간 것'이라고 말하면 SQL은 '사과 전부, 또는 빨간 배'로 알아듣는다. '빨간 사과 또는 빨간 배'를 원했다면 '(사과 또는 배)이면서 빨간 것'처럼 괄호를 쳐야 한다.

## 4. 문자열 비교 규칙

| 비교 대상 | 규칙 |
|---|---|
| CHAR와 CHAR(또는 문자 상수) | 길이가 다르면 짧은 쪽 뒤에 공백을 채워 같은 길이로 만든 뒤 비교한다. 그래서 `'AB'`와 `'AB '`는 같다 |
| VARCHAR2가 포함된 비교 | 공백을 채우지 않고 그대로 비교한다. 끝의 공백도 문자로 보므로 `'AB'`와 `'AB '`는 다르다 |
| 숫자와 문자 | 문자를 숫자로 암시적 변환해 비교한다 |

CHAR(5) 열에 'AB'를 저장하면 실제로는 'AB   '(공백 3개)로 저장된다. 이 열을 `WHERE COL = 'AB'`로 찾으면 CHAR 비교 규칙 덕분에 찾을 수 있다.

## 5. 부정 연산자와 NULL

```sql
SELECT ENAME, DEPTNO FROM EMP WHERE DEPTNO NOT IN (10, 20) ORDER BY EMPNO;
```

결과는 영업부 4명뿐이고 DEPTNO가 NULL인 임사원은 빠진다. `NOT IN` 목록에 NULL이 섞이면 결과가 0건이 된다는 점도 기억해 두자.

## 헷갈렸던 것들

- BETWEEN은 양 끝 값을 포함하고, 작은 값을 앞에 써야 한다.
- `_`는 정확히 한 글자, `%`는 0글자 이상이다. `LIKE 'A%'`는 'A' 하나만 있는 값도 찾는다.
- AND가 OR보다 먼저 계산된다. NOT은 AND보다 먼저다.
- `<>`, `!=`, `^=`는 모두 '같지 않다'이다.
- CHAR끼리 비교할 때는 공백을 채워 비교하고, VARCHAR2가 섞이면 공백까지 그대로 비교한다.
- NULL과의 비교는 UNKNOWN이라 부정 조건에서도 빠진다.

## 용어 정리

| 용어 | 뜻 |
|---|---|
| BETWEEN | 범위 조건(양 끝 포함) |
| IN | 목록 가운데 하나와 같은지 |
| LIKE | 와일드카드 패턴 비교 |
| ESCAPE | 와일드카드 문자 자체를 찾을 때 쓰는 이스케이프 지정 |
| 연산자 우선순위 | 괄호 → 산술 → 비교 → NOT → AND → OR |

## 복습 문제

**1.** 다음 WHERE 절과 같은 결과를 내는 것은?

```sql
WHERE SAL BETWEEN 3000 AND 4000
```

① `SAL > 3000 AND SAL < 4000` ② `SAL >= 3000 OR SAL <= 4000` ③ `SAL >= 3000 AND SAL <= 4000` ④ `SAL IN (3000, 4000)`

**2.** `WHERE ENAME LIKE '__원'`에 맞는 값은?

① 원 ② 사원 ③ 강사원 ④ 강사원님

**3.** 다음 조건과 같은 뜻은?

```sql
WHERE A = 1 OR B = 2 AND C = 3
```

① `(A = 1 OR B = 2) AND C = 3` ② `(A = 1 AND C = 3) OR B = 2` ③ `A = 1 AND B = 2 AND C = 3` ④ `A = 1 OR (B = 2 AND C = 3)`

**4.** CHAR(4) 열 COL에 'AB'가 저장되어 있을 때, `WHERE COL = 'AB'`의 결과는?

① 행이 조회되지 않는다 ② 오류가 난다 ③ 행이 조회된다 ④ NULL이 조회된다

## 답과 풀이

1. ③ BETWEEN은 양 끝을 포함한다.
2. ③ `_` 두 개와 '원'으로 정확히 세 글자인 값이다.
3. ④ AND가 먼저 계산된다.
4. ③ CHAR와 문자 상수의 비교는 공백을 채워 비교하므로 같다고 판단한다.

## 참고 자료

- 한국데이터산업진흥원 데이터자격검정, SQLD 출제기준: <https://www.dataq.or.kr>
- Oracle Database SQL Language Reference, Blank-Padded and Nonpadded Comparison Semantics: <https://docs.oracle.com/en/database/oracle/oracle-database/23/sqlrf/Data-Type-Comparison-Rules.html>

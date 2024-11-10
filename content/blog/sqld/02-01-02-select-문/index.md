---
title: '[SQLD] SELECT 문: DISTINCT, 별칭, 산술 연산자, 합성 연산자'
date: '2024-11-10T20:42:00+09:00'
categories:
- SQLD
tags:
- sqld
- sql
- select
- distinct
- alias
- 연결연산자
- dual
- SQL 기본
series:
- SQLD
series_order: 13
---

SQL 기본 두 번째, SELECT 문. 예제는 '실습 환경과 예제 데이터' 편 테이블로 직접 실행했고, 결과 표도 실행 결과 그대로다.

## 요약

- SELECT 문은 테이블에서 원하는 열과 행을 조회한다.
- DISTINCT는 중복된 행을 하나로 줄이고, 별칭(ALIAS)은 열에 다른 이름을 붙인다.
- 산술 연산자는 곱셈·나눗셈이 덧셈·뺄셈보다 먼저 계산되고, NULL이 들어가면 결과도 NULL이다.
- 문자열을 이을 때 Oracle은 `||`, SQL Server는 `+`를 쓴다.

## 1. 기본 문법

```sql
SELECT [ALL | DISTINCT] 열1, 열2, ...
  FROM 테이블명;
```

- `*`는 모든 열을 뜻한다(`SELECT * FROM EMP`).
- `ALL`은 중복을 그대로 보여 주는 기본값이다.
- SQL 키워드는 대소문자를 구분하지 않지만, 문자열 값(`'SALESMAN'`)은 구분한다.

## 2. DISTINCT

```sql
SELECT DISTINCT JOB FROM EMP ORDER BY JOB;
```

| JOB |
|---|
| ANALYST |
| CLERK |
| DEVELOPER |
| MANAGER |
| PRESIDENT |
| SALESMAN |

10명의 직무에서 중복을 없애 6개만 남았다. DISTINCT는 뒤에 오는 **모든 열의 조합**을 기준으로 중복을 없앤다.

```sql
SELECT DISTINCT DEPTNO, JOB FROM EMP WHERE DEPTNO = 20 ORDER BY 1, 2;
```

| DEPTNO | JOB |
|---|---|
| 20 | ANALYST |
| 20 | DEVELOPER |
| 20 | MANAGER |

개발부의 DEVELOPER 두 명(정대리, 강사원)이 (20, DEVELOPER) 한 줄로 합쳐졌다. `SELECT DEPTNO, DISTINCT JOB`처럼 중간에 DISTINCT를 쓰면 문법 오류다.

## 3. 별칭(ALIAS)

```sql
SELECT ENAME AS 이름, SAL * 12 AS 연봉, SAL * 12 + 100 * 2 AS 계산
  FROM EMP
 WHERE EMPNO IN (1005, 1006)
 ORDER BY EMPNO;
```

| 이름 | 연봉 | 계산 |
|---|---|---|
| 정대리 | 42000 | 42200 |
| 강사원 | 36000 | 36200 |

- `AS`는 생략할 수 있다(`SAL * 12 연봉`).
- 별칭에 공백이나 특수문자가 있거나 대소문자를 구분하려면 큰따옴표로 감싼다(`AS "월 급여"`).
- 별칭은 SELECT 절보다 나중에 실행되는 ORDER BY 절에서는 쓸 수 있지만, 먼저 실행되는 WHERE 절이나 GROUP BY 절에서는 쓸 수 없다.

## 4. 산술 연산자

| 연산자 | 뜻 | 우선순위 |
|---|---|---|
| ( ) | 괄호 | 1 |
| *, / | 곱하기, 나누기 | 2 |
| +, − | 더하기, 빼기 | 3 |

위 예제에서 `SAL * 12 + 100 * 2`는 `(SAL × 12) + (100 × 2)`로 계산되었다. 정대리는 42,000 + 200 = 42,200이다. SQL Server는 나머지 연산자 `%`도 쓰고, Oracle은 `MOD()` 함수를 쓴다.

NULL이 들어간 산술 연산은 결과가 NULL이다. `SAL + COMM`은 COMM이 NULL인 사원에게 NULL을 돌려준다. 0으로 나누면 오류가 나지만, NULL로 나누면 결과는 NULL이다.

## 5. 합성(연결) 연산자

```sql
SELECT ENAME || '(' || JOB || ')' AS 사원 FROM EMP WHERE DEPTNO = 10;
```

| 사원 |
|---|
| 김대표(PRESIDENT) |

- Oracle: `||` 또는 `CONCAT(문자1, 문자2)`
- SQL Server: `+` 또는 `CONCAT()`

Oracle의 `CONCAT`은 인수를 **두 개만** 받는다. 셋 이상을 이으려면 `CONCAT`을 겹쳐 쓰거나 `||`를 쓴다. Oracle에서는 `'A' || NULL`의 결과가 `'A'`이다(NULL을 빈 문자열로 취급).

## 6. DUAL 테이블

Oracle에서 테이블 없이 계산만 하고 싶을 때는 `DUAL`이라는 가상 테이블을 쓴다. `SELECT 1 + 1 FROM DUAL;`처럼. DUAL은 SYS 사용자가 소유하고, 모든 사용자가 쓸 수 있으며, DUMMY라는 열 하나와 값 'X'인 행 하나만 있다. SQL Server와 Oracle 23ai부터는 FROM 절 없이 `SELECT 1 + 1;`도 쓸 수 있다.

> **쉬운 설명**
>
> SELECT는 '표에서 이 칸들만 보여 줘'라는 주문서다. DISTINCT는 '같은 줄은 한 번만', 별칭은 '이 칸 이름은 이렇게 바꿔서', `||`는 '이 칸과 저 칸을 붙여서 한 칸으로'라는 추가 요청이다.

## 헷갈렸던 것들

- DISTINCT는 SELECT 바로 뒤에 한 번만 쓰고, 뒤의 모든 열 조합으로 중복을 판단한다.
- 별칭은 ORDER BY에서는 쓸 수 있지만 WHERE, GROUP BY, HAVING에서는 쓸 수 없다.
- 별칭에 공백이 있으면 큰따옴표가 필요하다. 작은따옴표는 문자열 값이다.
- 곱셈, 나눗셈이 덧셈, 뺄셈보다 먼저 계산된다.
- Oracle의 연결 연산자는 `||`, SQL Server는 `+`이다. Oracle CONCAT은 인수 두 개만 받는다.

## 용어 정리

| 용어 | 뜻 |
|---|---|
| DISTINCT | 중복 행을 하나로 줄이는 키워드 |
| 별칭(ALIAS) | 열이나 테이블에 붙이는 다른 이름 |
| 합성 연산자 | 문자열을 잇는 연산자 |
| DUAL | Oracle의 가상 테이블 |

## 복습 문제

**1.** 다음 중 문법 오류가 나는 SQL은?

① `SELECT ENAME, DISTINCT JOB FROM EMP;` ② `SELECT DISTINCT JOB FROM EMP;` ③ `SELECT ENAME 이름 FROM EMP;` ④ `SELECT ENAME AS "사원 이름" FROM EMP;`

**2.** `SELECT 10 + 2 * 3 FROM DUAL;`의 결과는?

① 36 ② 16 ③ 18 ④ 15

**3.** 다음 SQL에서 오류가 나는 부분은?

```sql
SELECT ENAME, SAL * 12 AS 연봉
  FROM EMP
 WHERE 연봉 > 50000
 ORDER BY 연봉;
```

① SELECT 절 ② FROM 절 ③ ORDER BY 절 ④ WHERE 절

## 답과 풀이

1. ① DISTINCT는 SELECT 바로 뒤에만 쓸 수 있다.
2. ② 곱셈이 먼저라 10 + 6 = 16이다.
3. ④ WHERE 절은 SELECT 절보다 먼저 실행되어 별칭을 알 수 없다. `WHERE SAL * 12 > 50000`으로 써야 한다.

## 참고 자료

- 한국데이터산업진흥원 데이터자격검정, SQLD 출제기준: <https://www.dataq.or.kr>
- Oracle Database SQL Language Reference, SELECT: <https://docs.oracle.com/en/database/oracle/oracle-database/23/sqlrf/SELECT.html>

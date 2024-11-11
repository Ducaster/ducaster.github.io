---
title: '[SQLD] 함수: 문자, 숫자, 날짜, 변환, CASE, NULL 관련 함수'
date: '2024-11-11T20:14:00+09:00'
categories:
- SQLD
tags:
- sqld
- sql
- 함수
- substr
- round
- trunc
- to_char
- case
- decode
- nvl
- coalesce
- nullif
- SQL 기본
series:
- SQLD
series_order: 14
---

SQL 기본 세 번째, 함수. 함수 결과값을 묻는 문제가 많아서 함수마다 입력과 결과를 표로 정리했다. 결과는 '실습 환경과 예제 데이터' 편 테이블로 직접 돌려 본 값이다.

## 요약

- 함수는 단일행 함수(행마다 결과 하나)와 다중행 함수(여러 행을 묶어 결과 하나, 집계 함수 등)로 나뉜다.
- 단일행 함수는 문자, 숫자, 날짜, 변환, NULL 관련 함수가 있고, SELECT, WHERE, ORDER BY 절에 쓸 수 있다.
- CASE 표현식과 Oracle의 DECODE 함수로 조건에 따라 다른 값을 돌려줄 수 있다.
- NULL 관련 함수 NVL, NVL2, NULLIF, COALESCE의 결과를 구분해야 한다.

## 1. 함수의 종류

| 구분 | 특징 | 예 |
|---|---|---|
| 단일행 함수 | 각 행에 하나씩 적용되어 행마다 결과를 하나 돌려준다. 함수를 겹쳐 쓸 수 있다 | UPPER, ROUND, TO_CHAR, NVL |
| 다중행 함수 | 여러 행을 묶어 결과 하나를 돌려준다 | 집계 함수(SUM, COUNT), 그룹 함수(ROLLUP), 윈도우 함수 |

## 2. 문자 함수

```sql
SELECT LOWER('SQL Expert'), UPPER('sql'), ASCII('A'), CHR(65), CONCAT('SQL', 'D'),
       SUBSTR('SQL Expert', 5, 3), LENGTH('SQL Expert'), INSTR('SQL Expert', 'e')
  FROM DUAL;
```

| 함수 | 설명 | 결과 |
|---|---|---|
| LOWER('SQL Expert') | 소문자로 | sql expert |
| UPPER('sql') | 대문자로 | SQL |
| ASCII('A') | 문자의 아스키 코드 | 65 |
| CHR(65) | 아스키 코드의 문자(SQL Server는 CHAR) | A |
| CONCAT('SQL', 'D') | 두 문자열 연결 | SQLD |
| SUBSTR('SQL Expert', 5, 3) | 5번째부터 3글자(SQL Server는 SUBSTRING) | Exp |
| LENGTH('SQL Expert') | 글자 수, 공백 포함(SQL Server는 LEN) | 10 |
| INSTR('SQL Expert', 'e') | 문자가 처음 나오는 위치, 대소문자 구분 | 8 |

```sql
SELECT LTRIM('xxSQLxx', 'x'), RTRIM('xxSQLxx', 'x'), TRIM('x' FROM 'xxSQLxx'),
       LPAD('SQL', 6, '*'), RPAD('SQL', 6, '*'), REPLACE('SQL Expert', 'Expert', 'Developer')
  FROM DUAL;
```

| 함수 | 설명 | 결과 |
|---|---|---|
| LTRIM('xxSQLxx', 'x') | 왼쪽에서 지정 문자 제거(생략하면 공백) | SQLxx |
| RTRIM('xxSQLxx', 'x') | 오른쪽에서 지정 문자 제거 | xxSQL |
| TRIM('x' FROM 'xxSQLxx') | 양쪽에서 지정 문자 제거 | SQL |
| LPAD('SQL', 6, '*') | 전체 6자리가 되도록 왼쪽을 채움 | \*\*\*SQL |
| RPAD('SQL', 6, '*') | 오른쪽을 채움 | SQL\*\*\* |
| REPLACE('SQL Expert', 'Expert', 'Developer') | 문자열 바꾸기. 세 번째 인수를 생략하면 지운다 | SQL Developer |

Oracle의 `TRIM`은 제거할 문자로 **한 글자**만 지정할 수 있다. SUBSTR의 시작 위치가 음수면 뒤에서부터 센다(`SUBSTR('SQL Expert', -3)` → `ert`).

## 3. 숫자 함수

| 함수 | 설명 | 결과 |
|---|---|---|
| ABS(-15) | 절댓값 | 15 |
| SIGN(-15) | 양수 1, 0이면 0, 음수 −1 | −1 |
| MOD(10, 3) | 나머지(SQL Server는 `10 % 3`) | 1 |
| CEIL(12.3) | 올림한 정수(SQL Server는 CEILING) | 13 |
| FLOOR(12.7) | 내림한 정수 | 12 |
| FLOOR(-12.3) | 음수의 내림 | −13 |
| ROUND(123.456, 1) | 소수 첫째 자리까지 반올림 | 123.5 |
| ROUND(123.456, -1) | 일의 자리에서 반올림 | 120 |
| ROUND(123.5) | 자릿수를 생략하면 정수로 반올림 | 124 |
| TRUNC(123.456, 1) | 소수 첫째 자리까지 남기고 버림 | 123.4 |
| TRUNC(123.456, -1) | 일의 자리에서 버림 | 120 |

ROUND와 TRUNC의 두 번째 인수가 양수면 소수점 아래 자리, 음수면 소수점 위 자리를 뜻한다. FLOOR(−12.3)이 −12가 아니라 −13이라는 점이 함정이다.

## 4. 날짜 함수

Oracle의 DATE 타입은 날짜와 시각(시, 분, 초)을 함께 저장하고, 숫자처럼 더하고 뺄 수 있다. 1은 하루, 1/24는 한 시간이다.

```sql
SELECT ENAME, HIREDATE, HIREDATE + 30, EXTRACT(YEAR FROM HIREDATE), LAST_DAY(HIREDATE)
  FROM EMP
 WHERE EMPNO = 1005;
```

| ENAME | HIREDATE | HIREDATE + 30 | EXTRACT(YEAR ...) | LAST_DAY |
|---|---|---|---|---|
| 정대리 | 2020-09-01 | 2020-10-01 | 2020 | 2020-09-30 |

| 함수, 연산 | 설명 | 정대리(2020-09-01)의 결과 |
|---|---|---|
| SYSDATE | 현재 날짜와 시각(SQL Server는 GETDATE()) | |
| 날짜 + 숫자 | 숫자만큼 일수를 더한 날짜 | HIREDATE + 30 → 2020-10-01 |
| 날짜 − 날짜 | 두 날짜 사이의 일수 | DATE '2020-10-01' − HIREDATE → 30 |
| ADD_MONTHS(날짜, n) | n개월 뒤 날짜 | ADD_MONTHS(HIREDATE, 3) → 2020-12-01 |
| MONTHS_BETWEEN(날짜1, 날짜2) | 두 날짜 사이의 개월 수 | MONTHS_BETWEEN(DATE '2021-03-01', HIREDATE) → 6 |
| LAST_DAY(날짜) | 그 달의 마지막 날 | 2020-09-30 |
| EXTRACT(YEAR FROM 날짜) | 연, 월, 일을 숫자로 꺼냄(SQL Server는 YEAR(), DATEPART()) | 2020 |

화면에 날짜가 어떤 모양으로 보이는지는 세션의 날짜 형식 설정(NLS_DATE_FORMAT)에 따라 다르다. 이 글에서는 읽기 쉽게 YYYY-MM-DD로 적었다.

## 5. 변환 함수

| 구분 | 설명 |
|---|---|
| 명시적 변환 | 변환 함수로 직접 데이터 타입을 바꾼다 |
| 암시적 변환 | DBMS가 알아서 바꾼다. 예상과 다르게 바뀌거나 인덱스를 못 쓰는 성능 문제가 생길 수 있어 명시적 변환을 권장한다 |

| Oracle | SQL Server | 설명 | 예 |
|---|---|---|---|
| TO_CHAR(숫자/날짜, 형식) | CONVERT, CAST | 문자로 변환 | TO_CHAR(HIREDATE, 'YYYY/MM/DD') → '2020/09/01' |
| TO_NUMBER(문자) | CONVERT, CAST | 숫자로 변환 | TO_NUMBER('123') → 123 |
| TO_DATE(문자, 형식) | CONVERT, CAST | 날짜로 변환 | TO_DATE('20200901', 'YYYYMMDD') |
| CAST(값 AS 타입) | CAST | 표준 변환 | CAST('123' AS NUMBER) |

## 6. CASE 표현식과 DECODE

조건에 따라 다른 값을 돌려준다. CASE는 ANSI 표준, DECODE는 Oracle 전용 함수다.

### 검색 CASE(Searched CASE)

```sql
SELECT ENAME, SAL,
       CASE WHEN SAL >= 5000 THEN '고급'
            WHEN SAL >= 3000 THEN '중급'
            ELSE '초급'
       END AS 등급
  FROM EMP
 WHERE DEPTNO = 30
 ORDER BY EMPNO;
```

| ENAME | SAL | 등급 |
|---|---|---|
| 박부장 | 5800 | 고급 |
| 조과장 | 4000 | 중급 |
| 윤대리 | 3200 | 중급 |
| 장사원 | 2800 | 초급 |

WHEN 조건은 위에서부터 차례로 검사하고, 처음 맞는 조건에서 멈춘다. 박부장은 5000 이상이라 '고급'에서 끝나고 아래 조건은 보지 않는다.

### 단순 CASE(Simple CASE)와 DECODE

```sql
SELECT ENAME, DEPTNO,
       CASE DEPTNO WHEN 10 THEN '기획' WHEN 20 THEN '개발' ELSE '기타' END AS 부서
  FROM EMP
 WHERE EMPNO IN (1001, 1005, 1007, 1010)
 ORDER BY EMPNO;

-- Oracle DECODE로 같은 결과
SELECT ENAME, DEPTNO, DECODE(DEPTNO, 10, '기획', 20, '개발', '기타') AS 부서
  FROM EMP
 WHERE EMPNO IN (1001, 1005, 1007, 1010)
 ORDER BY EMPNO;
```

| ENAME | DEPTNO | 부서 |
|---|---|---|
| 김대표 | 10 | 기획 |
| 정대리 | 20 | 개발 |
| 조과장 | 30 | 기타 |
| 임사원 | (NULL) | 기타 |

ELSE를 생략하면 맞는 조건이 없을 때 NULL을 돌려준다. 단순 CASE는 `DEPTNO = 10`처럼 같음(=) 비교만 하므로 NULL은 어느 WHEN에도 맞지 않는다. 반면 DECODE는 NULL과 NULL을 같다고 봐서 `DECODE(DEPTNO, NULL, '미배정', '배정')`은 임사원에게 '미배정'을 돌려준다.

## 7. NULL 관련 함수

```sql
SELECT ENAME, COMM,
       NVL(COMM, 0),
       NVL2(COMM, '있음', '없음'),
       NULLIF(COMM, 0),
       COALESCE(COMM, MGR, 0)
  FROM EMP
 WHERE EMPNO IN (1001, 1002, 1007, 1009)
 ORDER BY EMPNO;
```

| ENAME | COMM | NVL(COMM, 0) | NVL2(COMM, '있음', '없음') | NULLIF(COMM, 0) | COALESCE(COMM, MGR, 0) |
|---|---|---|---|---|---|
| 김대표 | (NULL) | 0 | 없음 | (NULL) | 0 |
| 이부장 | (NULL) | 0 | 없음 | (NULL) | 1001 |
| 조과장 | 500 | 500 | 있음 | 500 | 500 |
| 장사원 | 0 | 0 | 있음 | (NULL) | 0 |

| 함수 | 설명 |
|---|---|
| NVL(A, B) | A가 NULL이면 B, 아니면 A. SQL Server는 ISNULL(A, B) |
| NVL2(A, B, C) | A가 NULL이 아니면 B, NULL이면 C(Oracle 전용) |
| NULLIF(A, B) | A와 B가 같으면 NULL, 다르면 A |
| COALESCE(A, B, C, ...) | 인수 가운데 처음으로 NULL이 아닌 값 |

- 장사원의 COMM은 0이라 NULL이 아니므로 NVL2는 '있음'이다. 그런데 NULLIF(0, 0)은 두 값이 같아 NULL이 된다.
- 이부장은 COMM이 NULL이고 MGR이 1001이라, COALESCE가 두 번째 인수인 1001을 돌려준다. 김대표는 COMM과 MGR이 모두 NULL이라 0이다.

> **쉬운 설명**
>
> NVL은 '비어 있으면 이걸로 채워 줘', NVL2는 '비어 있는지 아닌지에 따라 다른 답을 줘', NULLIF는 '두 값이 같으면 비워 줘', COALESCE는 '앞에서부터 보다가 처음으로 값이 있는 걸 줘'이다.

## 헷갈렸던 것들

- `SUBSTR('SQL Expert', 5, 3)`은 5번째 글자부터 3글자 `Exp`이다. 인덱스는 1부터 시작한다.
- LENGTH는 공백도 센다.
- ROUND, TRUNC의 자릿수가 음수면 소수점 왼쪽 자리다. FLOOR(−12.3)은 −13이다.
- 날짜 − 날짜는 일수, 날짜 + 1/24는 한 시간 뒤다.
- NVL2(A, B, C)는 A가 NULL이 **아닐 때** B이다.
- NULLIF(A, B)는 같으면 NULL이다.
- 단순 CASE는 NULL과 비교할 수 없지만, DECODE는 NULL끼리 같다고 본다.
- CASE의 ELSE를 생략하면 NULL이다.

## 용어 정리

| 용어 | 뜻 |
|---|---|
| 단일행 함수 | 행마다 결과 하나를 돌려주는 함수 |
| 다중행 함수 | 여러 행을 묶어 결과 하나를 돌려주는 함수 |
| 명시적 / 암시적 변환 | 함수로 직접 / DBMS가 자동으로 타입 변환 |
| CASE | 조건에 따라 다른 값을 돌려주는 표준 표현식 |
| DECODE | Oracle의 조건 함수 |
| COALESCE | 처음으로 NULL이 아닌 값을 돌려주는 함수 |

## 복습 문제

**1.** `SELECT SUBSTR('DATABASE', 3, 4) FROM DUAL;`의 결과는?

① TABA ② DATA ③ ATAB ④ BASE

**2.** `SELECT ROUND(456.789, -2), TRUNC(456.789, 1) FROM DUAL;`의 결과는?

① 500, 456.7 ② 460, 456.8 ③ 500, 456.8 ④ 400, 456.7

**3.** COMM이 NULL인 행에서 `NVL2(COMM, 1, 2)`의 결과는?

① NULL ② 2 ③ 0 ④ 1

**4.** `SELECT COALESCE(NULL, NULLIF(5, 5), 7, 9) FROM DUAL;`의 결과는?

① 7 ② NULL ③ 5 ④ 9

**5.** 다음 SQL의 결과로 옳은 것은? (COL1은 NULL)

```sql
SELECT CASE COL1 WHEN NULL THEN 'A' ELSE 'B' END FROM T;
```

① A ② NULL ③ 오류 ④ B

## 답과 풀이

1. ① 3번째 글자부터 4글자: D-A-**T-A-B-A**-S-E → TABA이다.
2. ① 백의 자리까지 반올림하면 500, 소수 첫째 자리까지 버리면 456.7이다.
3. ② NULL이면 세 번째 인수다.
4. ① NULLIF(5, 5)는 NULL이라 처음으로 NULL이 아닌 값은 7이다.
5. ④ 단순 CASE는 `COL1 = NULL`로 비교하므로 항상 UNKNOWN이 되어 ELSE로 간다. NULL을 검사하려면 `CASE WHEN COL1 IS NULL THEN ...`을 써야 한다.

## 참고 자료

- 한국데이터산업진흥원 데이터자격검정, SQLD 출제기준: <https://www.dataq.or.kr>
- Oracle Database SQL Language Reference, Functions: <https://docs.oracle.com/en/database/oracle/oracle-database/23/sqlrf/Functions.html>

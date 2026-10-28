---
title: '[SQLD] PIVOT 절과 UNPIVOT 절: 행을 열로, 열을 행으로'
date: '2024-11-30T20:14:00+09:00'
categories:
- SQLD
tags:
- sqld
- sql
- pivot
- unpivot
- 행열전환
- decode
- case
- SQL 활용
series:
- SQLD
series_order: 26
---

PIVOT 절과 UNPIVOT 절은 2024년 출제기준 개편 때 새로 들어온 내용이다. PIVOT이 어떤 열로 그룹을 만드는지(암묵적 GROUP BY)만 잡으면 나머지는 문법이다. 결과는 실제 실행 결과.

## 요약

- PIVOT은 행 값을 열로 바꿔 가로로 펼치고, UNPIVOT은 열을 행으로 바꿔 세로로 쌓는다.
- PIVOT 절은 집계 함수, FOR 절(열로 바꿀 기준 열), IN 절(만들 열의 값 목록)로 이루어진다.
- PIVOT은 PIVOT 절에 쓰지 않은 나머지 열로 자동 그룹을 만든다. 그래서 보통 인라인 뷰로 필요한 열만 골라 넣는다.
- UNPIVOT은 기본적으로 NULL인 값을 결과에서 빼고, INCLUDE NULLS를 쓰면 남긴다.
- PIVOT이 없는 DBMS에서는 CASE나 DECODE와 집계 함수로 같은 결과를 만든다.

{{< mermaid >}}
flowchart LR
  L["세로(긴) 형태<br>JOB, DEPTNO, SAL"] -->|"PIVOT"| W["가로(넓은) 형태<br>JOB, 10, 20, 30"]
  W -->|"UNPIVOT"| L
{{< /mermaid >}}

## 1. PIVOT

직무별, 부서별 급여 합계를 직무는 행으로, 부서는 열로 펼쳐 본다.

```sql
SELECT *
  FROM (SELECT JOB, DEPTNO, SAL FROM EMP)      -- ① 필요한 열만 고른 인라인 뷰
 PIVOT (SUM(SAL)                               -- ② 집계 함수
        FOR DEPTNO                             -- ③ 열로 바꿀 기준 열
        IN (10, 20, 30))                       -- ④ 만들 열의 값
 ORDER BY JOB;
```

| JOB | 10 | 20 | 30 |
|---|---|---|---|
| ANALYST | (NULL) | 4500 | (NULL) |
| CLERK | (NULL) | (NULL) | (NULL) |
| DEVELOPER | (NULL) | 6500 | (NULL) |
| MANAGER | (NULL) | 6000 | 5800 |
| PRESIDENT | 9000 | (NULL) | (NULL) |
| SALESMAN | (NULL) | (NULL) | 10000 |

- 인라인 뷰의 열 가운데 PIVOT 절에 나오지 않은 **JOB**이 자동으로 그룹 기준이 되었다(암묵적 GROUP BY).
- IN 목록에 없는 부서(NULL인 임사원)는 열이 만들어지지 않아서, CLERK 행은 모두 NULL이다. CLERK 행 자체는 JOB 그룹으로 남는다.
- IN 절에는 값을 직접 적어야 하고, 서브쿼리는 쓸 수 없다(XML 형식 출력인 PIVOT XML은 예외).

### 인라인 뷰를 쓰지 않으면

`SELECT * FROM EMP PIVOT (SUM(SAL) FOR DEPTNO IN (10, 20, 30))`처럼 테이블을 바로 쓰면 EMPNO, ENAME, JOB, MGR, HIREDATE, COMM이 모두 그룹 기준이 된다. 사원마다 한 행씩 나와서 피벗한 의미가 없어진다. 그래서 PIVOT은 인라인 뷰로 그룹 기준 열, FOR 열, 집계 대상 열만 골라 넣는 것이 정석이다.

### 열 이름 정하기와 여러 집계

```sql
SELECT *
  FROM (SELECT JOB, DEPTNO, SAL FROM EMP WHERE JOB IN ('MANAGER', 'SALESMAN'))
 PIVOT (SUM(SAL) AS SAL, COUNT(*) AS CNT
        FOR DEPTNO IN (20 AS D20, 30 AS D30))
 ORDER BY JOB;
```

IN 목록에 별칭을 주면 열 이름이 D20, D30이 되고, 집계 함수가 여러 개면 'IN 별칭_집계 별칭' 형식(D20_SAL, D20_CNT, D30_SAL, D30_CNT)으로 열이 만들어진다. 별칭이 없으면 열 이름이 숫자(10, 20, 30)라서 따로 부를 때 큰따옴표가 필요하다(`"10"`).

### CASE로 같은 결과 만들기

PIVOT 절이 없던 시절이나 다른 DBMS에서는 CASE(또는 Oracle의 DECODE)와 집계 함수로 피벗한다.

```sql
SELECT JOB,
       SUM(CASE WHEN DEPTNO = 10 THEN SAL END) AS "10",
       SUM(CASE WHEN DEPTNO = 20 THEN SAL END) AS "20",
       SUM(CASE WHEN DEPTNO = 30 THEN SAL END) AS "30"
  FROM EMP
 GROUP BY JOB
 ORDER BY JOB;
```

결과는 위의 PIVOT과 같다. 이 방식에서는 GROUP BY가 눈에 보이니, PIVOT의 암묵적 GROUP BY를 이해하는 데에도 도움이 된다.

## 2. UNPIVOT

가로로 펼친 표를 다시 세로로 쌓는다. 먼저 피벗된 테이블을 하나 만들어 둔다.

```sql
CREATE TABLE PV AS
SELECT *
  FROM (SELECT JOB, DEPTNO, SAL FROM EMP WHERE JOB IN ('MANAGER', 'PRESIDENT'))
 PIVOT (SUM(SAL) FOR DEPTNO IN (10 AS D10, 20 AS D20, 30 AS D30));
```

| JOB | D10 | D20 | D30 |
|---|---|---|---|
| MANAGER | (NULL) | 6000 | 5800 |
| PRESIDENT | 9000 | (NULL) | (NULL) |

```sql
SELECT JOB, DEPTNO, SAL
  FROM PV
UNPIVOT (SAL                              -- ① 값이 들어갈 새 열
         FOR DEPTNO                       -- ② 원래 열 이름(또는 별칭)이 들어갈 새 열
         IN (D10 AS 10, D20 AS 20, D30 AS 30))   -- ③ 행으로 바꿀 열
 ORDER BY JOB, DEPTNO;
```

| JOB | DEPTNO | SAL |
|---|---|---|
| MANAGER | 20 | 6000 |
| MANAGER | 30 | 5800 |
| PRESIDENT | 10 | 9000 |

- 열 3개 × 행 2개 = 6개 칸 가운데 NULL인 3칸은 빠졌다. UNPIVOT의 기본값은 `EXCLUDE NULLS`이다.
- `UNPIVOT INCLUDE NULLS (...)`로 쓰면 NULL 칸도 남아 6행이 나온다.
- IN 절에 별칭(AS 10)을 주지 않으면 DEPTNO 열에 원래 열 이름 'D10', 'D20', 'D30'이 문자로 들어간다.
- PIVOT으로 집계한 데이터를 UNPIVOT해도 원래의 상세 행으로 돌아오지는 않는다. 합계로 합쳐진 값은 나눌 수 없기 때문이다.

SQL Server에서도 PIVOT과 UNPIVOT을 쓰지만, IN 목록의 값을 대괄호로 감싸고(`IN ([10], [20], [30])`) 결과에 별칭을 붙여야 하는 등 문법이 조금 다르다.

> **쉬운 설명**
>
> 엑셀의 '피벗 테이블'과 같다. '직무, 부서, 급여'가 세로로 길게 적힌 장부를, 직무는 줄로, 부서는 칸으로 놓고 교차하는 칸에 급여 합계를 적은 표로 바꾸는 것이 PIVOT이다. 그 표를 다시 '직무, 부서, 급여' 세 칸짜리 긴 장부로 되돌리는 것이 UNPIVOT이다.

## 헷갈렸던 것들

- PIVOT은 PIVOT 절에 쓰지 않은 모든 열로 암묵적 GROUP BY를 한다. 불필요한 열이 섞이면 행이 많아진다.
- PIVOT의 IN 절에는 값 목록을 직접 써야 한다.
- IN 별칭이 없으면 열 이름이 IN의 값 그대로다.
- UNPIVOT은 기본으로 NULL을 제외하고, INCLUDE NULLS를 쓰면 포함한다.
- PIVOT은 CASE나 DECODE와 집계 함수, GROUP BY로 바꿔 쓸 수 있다.

## 용어 정리

| 용어 | 뜻 |
|---|---|
| PIVOT | 행 값을 열로 바꾸는 절 |
| UNPIVOT | 열을 행으로 바꾸는 절 |
| FOR 절 | 열로 바꿀 기준 열(PIVOT), 열 이름이 들어갈 새 열(UNPIVOT) |
| IN 절 | 만들 열의 값(PIVOT), 행으로 바꿀 열(UNPIVOT) |
| INCLUDE NULLS | UNPIVOT에서 NULL 값도 행으로 남기는 옵션 |

## 복습 문제

**1.** 다음 SQL의 결과 행 수는? (EMP의 JOB은 6종류)

```sql
SELECT * FROM (SELECT JOB, DEPTNO, SAL FROM EMP)
 PIVOT (SUM(SAL) FOR DEPTNO IN (10, 20, 30));
```

① 3 ② 4 ③ 6 ④ 10

**2.** PIVOT 절에 대한 설명으로 옳지 않은 것은?

① IN 절에 서브쿼리를 쓸 수 있다 ② 집계 함수가 필요하다 ③ FOR 절에 열로 바꿀 기준 열을 쓴다 ④ PIVOT 절에 쓰지 않은 열로 암묵적 그룹이 만들어진다

**3.** 값이 NULL인 칸이 2개 있는 3열 × 2행 표를 UNPIVOT했을 때, 옵션을 주지 않으면 결과 행 수는?

① 2 ② 4 ③ 6 ④ 8

## 답과 풀이

1. ③ 남은 열 JOB으로 그룹이 만들어지므로 직무 수인 6행이다.
2. ① 일반 PIVOT의 IN 절에는 값 목록을 직접 써야 한다.
3. ② 6칸 가운데 NULL 2칸이 빠져 4행이다.

## 참고 자료

- 한국데이터산업진흥원 데이터자격검정, SQLD 출제기준: <https://www.dataq.or.kr>
- Oracle Database SQL Language Reference, SELECT(pivot_clause, unpivot_clause): <https://docs.oracle.com/en/database/oracle/oracle-database/23/sqlrf/SELECT.html>

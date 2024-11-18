---
title: '[SQLD] 조인: 등가 조인, 비등가 조인, 3개 이상 테이블 조인, Oracle 외부 조인'
date: '2024-11-18T21:06:00+09:00'
categories:
- SQLD
tags:
- sqld
- sql
- 조인
- equi-join
- non-equi-join
- outer-join
- oracle
- SQL 기본
series:
- SQLD
series_order: 18
---

SQL 기본 일곱 번째, 조인. 여기서는 WHERE 절에 조인 조건을 쓰는 Oracle 방식만 보고, ANSI 표준 문법(INNER JOIN, OUTER JOIN 등)은 다음 글 '표준 조인'에서 따로 정리했다. 결과는 예제 테이블로 직접 실행한 것.

## 요약

- 조인은 두 개 이상의 테이블을 연결해 데이터를 함께 조회하는 것이다.
- 같은 값으로 잇는 등가 조인(EQUI JOIN)과, 범위 같은 다른 조건으로 잇는 비등가 조인(Non-EQUI JOIN)이 있다.
- N개의 테이블을 조인하려면 조인 조건이 최소 N − 1개 필요하다.
- Oracle에서는 조인 조건에 `(+)`를 붙여 외부 조인을 표현한다.

## 1. 등가 조인(EQUI JOIN)

두 테이블의 열 값이 **같은(=)** 행끼리 잇는다. 대부분 PK와 FK 관계로 조인한다.

```sql
-- Oracle 방식: FROM에 테이블을 나열하고 WHERE에 조인 조건
SELECT E.ENAME, D.DNAME
  FROM EMP E, DEPT D
 WHERE E.DEPTNO = D.DEPTNO
   AND E.DEPTNO = 20;
```

- 테이블 별칭(E, D)을 쓰면 SQL이 짧아지고, 두 테이블에 같은 이름의 열(DEPTNO)이 있을 때 어느 쪽인지 구분할 수 있다.
- FROM 절에 별칭을 정했으면 SELECT, WHERE 절에서도 **별칭으로만** 불러야 한다. `EMP.ENAME`처럼 원래 테이블명을 쓰면 오류다.
- 두 테이블에 모두 있는 열을 별칭 없이 쓰면 '열의 정의가 애매하다'는 오류가 난다.

조인 조건을 빠뜨리면 두 테이블의 모든 행이 서로 조합되는 **카티션 곱(Cartesian Product)** 이 생긴다. EMP 10행 × DEPT 4행 = 40행이 나온다.

## 2. 비등가 조인(Non-EQUI JOIN)

`=`가 아닌 BETWEEN, >, < 같은 조건으로 잇는다. 급여가 급여등급의 범위 안에 드는지로 조인해 본다.

```sql
SELECT E.ENAME, E.SAL, S.GRADE
  FROM EMP E, SALGRADE S
 WHERE E.SAL BETWEEN S.LOSAL AND S.HISAL
   AND E.DEPTNO = 20
 ORDER BY E.SAL DESC;
```

| ENAME | SAL | GRADE |
|---|---|---|
| 이부장 | 6000 | 4 |
| 최과장 | 4500 | 3 |
| 정대리 | 3500 | 2 |
| 강사원 | 3000 | 2 |

EMP와 SALGRADE에는 공통 열이 없지만, 급여 범위로 연결할 수 있다.

## 3. 3개 이상 테이블 조인

```sql
SELECT E.ENAME, D.DNAME, S.GRADE
  FROM EMP E, DEPT D, SALGRADE S
 WHERE E.DEPTNO = D.DEPTNO                  -- 조인 조건 1
   AND E.SAL BETWEEN S.LOSAL AND S.HISAL    -- 조인 조건 2
   AND D.LOC = '부산'                        -- 일반 조건
 ORDER BY E.EMPNO;
```

| ENAME | DNAME | GRADE |
|---|---|---|
| 박부장 | 영업부 | 4 |
| 조과장 | 영업부 | 3 |
| 윤대리 | 영업부 | 2 |
| 장사원 | 영업부 | 1 |

테이블이 3개이므로 조인 조건이 최소 2개 필요하다. 하나라도 빠지면 그 테이블과 카티션 곱이 생긴다.

{{< mermaid >}}
flowchart LR
  E["EMP"] -->|"E.DEPTNO = D.DEPTNO"| D["DEPT"]
  E -->|"E.SAL BETWEEN LOSAL AND HISAL"| S["SALGRADE"]
{{< /mermaid >}}

## 4. Oracle의 외부 조인 (+)

등가 조인은 양쪽 모두에 맞는 값이 있는 행만 보여 준다. 그래서 사원이 없는 인사부(40)와 부서가 없는 임사원은 빠진다. 짝이 없는 행도 보이게 하는 것이 **외부 조인(OUTER JOIN)** 이다.

Oracle에서는 **데이터가 부족한 쪽**(짝이 없을 수 있는 쪽)의 열에 `(+)`를 붙인다.

```sql
-- 모든 부서를 보여 주고, 사원이 없으면 NULL
SELECT D.DEPTNO, D.DNAME, E.ENAME
  FROM DEPT D, EMP E
 WHERE D.DEPTNO = E.DEPTNO(+)
   AND D.DEPTNO IN (10, 40)
 ORDER BY D.DEPTNO;
```

| DEPTNO | DNAME | ENAME |
|---|---|---|
| 10 | 기획부 | 김대표 |
| 40 | 인사부 | (NULL) |

EMP 쪽에 `(+)`를 붙였으니 'EMP에 짝이 없어도 DEPT 행은 남겨라'는 뜻이다. ANSI의 `DEPT LEFT OUTER JOIN EMP`와 같다.

```sql
-- 모든 사원을 보여 주고, 부서가 없으면 NULL
SELECT E.ENAME, E.DEPTNO, D.DNAME
  FROM EMP E, DEPT D
 WHERE E.DEPTNO = D.DEPTNO(+)
   AND E.EMPNO IN (1001, 1010)
 ORDER BY E.EMPNO;
```

| ENAME | DEPTNO | DNAME |
|---|---|---|
| 김대표 | 10 | 기획부 |
| 임사원 | (NULL) | (NULL) |

`(+)` 방식의 제약도 알아 두자.

- 양쪽에 동시에 `(+)`를 붙일 수 없다. FULL OUTER JOIN은 ANSI 문법으로 써야 한다.
- 외부 조인할 테이블에 일반 조건을 걸 때도 `(+)`를 붙여야 외부 조인이 유지된다. `E.SAL(+) >= 5000`처럼. 빠뜨리면 NULL 행이 조건에서 걸러져 내부 조인처럼 된다.

> **쉬운 설명**
>
> 반 명단(DEPT)과 학생 명단(EMP)을 반 번호로 맞대는 것이 등가 조인이다. 학생이 한 명도 없는 새 반이나, 아직 반 배정을 못 받은 전학생은 짝이 없어서 빠진다. '짝이 없어도 반 이름은 다 보여 줘'라고 하는 것이 외부 조인이고, Oracle은 짝이 모자랄 수 있는 쪽에 (+) 표시를 붙여 '여기는 빈칸으로 채워도 돼'라고 알려 준다.

## 헷갈렸던 것들

- N개 테이블을 조인하려면 조인 조건이 최소 N − 1개 필요하다.
- 조인 조건이 없으면 카티션 곱(행 수 × 행 수)이 생긴다.
- 별칭을 정했으면 원래 테이블명으로 열을 부를 수 없다.
- 비등가 조인은 공통 열 없이 범위 조건으로도 할 수 있다.
- Oracle `(+)`는 **짝이 없을 수 있는 쪽**(NULL로 채워질 쪽)에 붙인다.
- `(+)`는 양쪽에 붙일 수 없어 FULL OUTER JOIN을 표현하지 못한다.

## 용어 정리

| 용어 | 뜻 |
|---|---|
| 등가 조인 | = 조건으로 잇는 조인 |
| 비등가 조인 | BETWEEN, > 같은 조건으로 잇는 조인 |
| 카티션 곱 | 조인 조건 없이 모든 행을 조합한 결과 |
| 외부 조인 | 짝이 없는 행도 남기는 조인 |
| (+) | Oracle의 외부 조인 표시 |

## 복습 문제

**1.** EMP(14행)와 DEPT(4행)를 조인 조건 없이 조인하면 결과는 몇 행인가?

① 4 ② 14 ③ 18 ④ 56

**2.** 테이블 4개를 조인할 때 필요한 최소 조인 조건 수는?

① 2 ② 3 ③ 4 ④ 5

**3.** 다음 SQL과 같은 결과를 내는 ANSI 문법은?

```sql
SELECT D.DNAME, E.ENAME FROM DEPT D, EMP E WHERE D.DEPTNO = E.DEPTNO(+);
```

① `DEPT D INNER JOIN EMP E ON D.DEPTNO = E.DEPTNO` ② `DEPT D RIGHT OUTER JOIN EMP E ON D.DEPTNO = E.DEPTNO` ③ `DEPT D LEFT OUTER JOIN EMP E ON D.DEPTNO = E.DEPTNO` ④ `DEPT D FULL OUTER JOIN EMP E ON D.DEPTNO = E.DEPTNO`

**4.** 다음 SQL의 오류 원인은?

```sql
SELECT EMP.ENAME, D.DNAME FROM EMP E, DEPT D WHERE E.DEPTNO = D.DEPTNO;
```

① 조인 조건이 없다 ② DEPT에 DNAME이 없다 ③ 등가 조인은 WHERE 절에 쓸 수 없다 ④ 별칭을 정한 테이블을 원래 이름으로 불렀다

## 답과 풀이

1. ④ 14 × 4 = 56행의 카티션 곱이다.
2. ② 4 − 1 = 3개다.
3. ③ EMP 쪽에 (+)가 붙었으니 DEPT를 모두 남기는 LEFT OUTER JOIN이다.
4. ④ EMP에 별칭 E를 정했으므로 `E.ENAME`으로 써야 한다.

## 참고 자료

- 한국데이터산업진흥원 데이터자격검정, SQLD 출제기준: <https://www.dataq.or.kr>
- Oracle Database SQL Language Reference, Joins: <https://docs.oracle.com/en/database/oracle/oracle-database/23/sqlrf/Joins.html>

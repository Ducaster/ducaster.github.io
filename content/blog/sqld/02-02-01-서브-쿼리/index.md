---
title: '[SQLD] 서브쿼리: 단일행, 다중행, 다중컬럼, 연관 서브쿼리와 뷰'
date: '2024-11-18T22:37:00+09:00'
categories:
- SQLD
tags:
- sqld
- sql
- 서브쿼리
- 스칼라서브쿼리
- 인라인뷰
- exists
- any
- all
- 뷰
- SQL 활용
series:
- SQLD
series_order: 20
---

SQL 활용 파트는 서브쿼리부터다. 서브쿼리 종류, 다중행 연산자(IN, ANY, ALL, EXISTS), NOT IN과 NULL 함정이 자주 나온다. 결과는 예제 테이블로 직접 돌려 봤다.

## 요약

- 서브쿼리는 SQL 문 안에 들어 있는 또 하나의 SELECT 문이다. 괄호로 감싼다.
- 돌려주는 결과에 따라 단일행, 다중행, 다중컬럼 서브쿼리로 나뉜다.
- 메인쿼리의 값을 참조하면 연관(상관) 서브쿼리, 참조하지 않으면 비연관 서브쿼리다.
- 위치에 따라 SELECT 절의 스칼라 서브쿼리, FROM 절의 인라인 뷰, WHERE·HAVING 절의 중첩 서브쿼리로 부른다.
- 서브쿼리 결과에 NULL이 섞이면 NOT IN은 결과가 0건이 된다. 이럴 때는 NOT EXISTS를 쓴다.

## 1. 서브쿼리의 종류

{{< mermaid >}}
flowchart TB
  M["메인쿼리"] --> S1["SELECT 절<br>스칼라 서브쿼리<br>값 하나"]
  M --> S2["FROM 절<br>인라인 뷰<br>임시 테이블"]
  M --> S3["WHERE · HAVING 절<br>중첩 서브쿼리<br>조건 비교"]
{{< /mermaid >}}

| 결과 형태 | 설명 | 함께 쓰는 연산자 |
|---|---|---|
| 단일행 서브쿼리 | 결과가 1행 이하 | =, <, >, <=, >=, <> |
| 다중행 서브쿼리 | 결과가 여러 행 | IN, ANY, ALL, EXISTS |
| 다중컬럼 서브쿼리 | 결과가 여러 열 | (열1, 열2) IN (서브쿼리) |

| 메인쿼리 참조 | 설명 |
|---|---|
| 비연관 서브쿼리 | 메인쿼리의 열을 쓰지 않는다. 서브쿼리를 먼저 한 번 실행해 결과를 메인쿼리에 넘긴다 |
| 연관(상관) 서브쿼리 | 메인쿼리의 열을 쓴다. 메인쿼리의 행마다 서브쿼리가 다시 실행되는 것처럼 동작한다 |

서브쿼리 안에서는 메인쿼리의 열을 쓸 수 있지만, 메인쿼리에서는 서브쿼리의 열을 쓸 수 없다(인라인 뷰는 예외). 중첩 서브쿼리 안에는 ORDER BY를 쓸 수 없다.

## 2. 단일행 서브쿼리

```sql
SELECT ENAME, SAL
  FROM EMP
 WHERE SAL > (SELECT AVG(SAL) FROM EMP)   -- 전체 평균 4460
 ORDER BY SAL DESC;
```

| ENAME | SAL |
|---|---|
| 김대표 | 9000 |
| 이부장 | 6000 |
| 박부장 | 5800 |
| 최과장 | 4500 |

단일행 연산자(=, > 등)에 여러 행을 돌려주는 서브쿼리를 쓰면 '단일 행 하위 질의에 2개 이상의 행이 리턴되었다' 오류가 난다.

## 3. 다중행 서브쿼리

### IN

```sql
SELECT ENAME, DEPTNO
  FROM EMP
 WHERE DEPTNO IN (SELECT DEPTNO FROM DEPT WHERE LOC IN ('서울', '부산'))
 ORDER BY EMPNO;
```

| ENAME | DEPTNO |
|---|---|
| 김대표 | 10 |
| 박부장 | 30 |
| 조과장 | 30 |
| 윤대리 | 30 |
| 장사원 | 30 |

### ANY와 ALL

영업부(30) 급여는 5800, 4000, 3200, 2800이다.

| 연산자 | 뜻 | `SAL > ...`일 때 |
|---|---|---|
| > ANY (서브쿼리) | 하나라도 만족 | 최솟값(2800)보다 크면 참 |
| > ALL (서브쿼리) | 모두 만족 | 최댓값(5800)보다 크면 참 |
| < ANY | 하나라도 만족 | 최댓값보다 작으면 참 |
| < ALL | 모두 만족 | 최솟값보다 작으면 참 |

```sql
SELECT ENAME, SAL FROM EMP
 WHERE DEPTNO = 20 AND SAL > ALL (SELECT SAL FROM EMP WHERE DEPTNO = 30)
 ORDER BY EMPNO;
```

| ENAME | SAL |
|---|---|
| 이부장 | 6000 |

```sql
SELECT ENAME, SAL FROM EMP
 WHERE DEPTNO = 20 AND SAL > ANY (SELECT SAL FROM EMP WHERE DEPTNO = 30)
 ORDER BY EMPNO;
```

| ENAME | SAL |
|---|---|
| 이부장 | 6000 |
| 최과장 | 4500 |
| 정대리 | 3500 |
| 강사원 | 3000 |

`= ANY`는 IN과 같다.

### EXISTS

EXISTS는 서브쿼리 결과가 **한 행이라도 있으면** 참이다. 결과의 값은 보지 않고 존재 여부만 보기 때문에 SELECT 절에 보통 `1`이나 `'X'`를 쓴다. 조건을 만족하는 행을 하나 찾으면 바로 멈춰서 효율적이다.

```sql
SELECT D.DEPTNO, D.DNAME FROM DEPT D
 WHERE EXISTS (SELECT 1 FROM EMP E WHERE E.DEPTNO = D.DEPTNO)
 ORDER BY 1;
```

| DEPTNO | DNAME |
|---|---|
| 10 | 기획부 |
| 20 | 개발부 |
| 30 | 영업부 |

`NOT EXISTS`로 바꾸면 사원이 없는 인사부(40)만 나온다.

## 4. 다중컬럼 서브쿼리

```sql
SELECT ENAME, DEPTNO, SAL FROM EMP
 WHERE (DEPTNO, SAL) IN (SELECT DEPTNO, MAX(SAL) FROM EMP GROUP BY DEPTNO)
 ORDER BY EMPNO;
```

| ENAME | DEPTNO | SAL |
|---|---|---|
| 김대표 | 10 | 9000 |
| 이부장 | 20 | 6000 |
| 박부장 | 30 | 5800 |

부서별 최고 급여자를 찾았다. 부서가 NULL인 임사원은 (NULL, 2800)이 비교에서 UNKNOWN이라 빠졌다. SQL Server는 다중컬럼 IN을 지원하지 않는다.

## 5. 연관 서브쿼리

```sql
SELECT E.ENAME, E.DEPTNO, E.SAL FROM EMP E
 WHERE E.SAL > (SELECT AVG(S.SAL) FROM EMP S WHERE S.DEPTNO = E.DEPTNO)
 ORDER BY E.EMPNO;
```

| ENAME | DEPTNO | SAL |
|---|---|---|
| 이부장 | 20 | 6000 |
| 박부장 | 30 | 5800 |
| 최과장 | 20 | 4500 |
| 조과장 | 30 | 4000 |

서브쿼리가 메인쿼리의 `E.DEPTNO`를 참조해서, 사원마다 '자기 부서의 평균'과 비교한다. 개발부 평균 4250, 영업부 평균 3950보다 급여가 높은 사원이 나왔다. 기획부는 김대표 혼자라 평균과 같아서 빠졌다.

## 6. NOT IN과 NULL의 함정

'아무도 관리하지 않는 사원(부하가 없는 사원)'을 찾아보자.

```sql
SELECT COUNT(*) FROM EMP WHERE EMPNO NOT IN (SELECT MGR FROM EMP);   -- 0
```

결과가 0건이다. 서브쿼리 결과(MGR 목록)에 김대표의 NULL이 들어 있어서, `EMPNO <> NULL`이 UNKNOWN이 되기 때문이다. NOT EXISTS로 바꾸면 의도대로 나온다.

```sql
SELECT E.ENAME FROM EMP E
 WHERE NOT EXISTS (SELECT 1 FROM EMP S WHERE S.MGR = E.EMPNO)
 ORDER BY E.EMPNO;
```

| ENAME |
|---|
| 정대리 |
| 강사원 |
| 조과장 |
| 윤대리 |
| 장사원 |
| 임사원 |

NOT IN을 꼭 써야 한다면 서브쿼리에 `WHERE MGR IS NOT NULL`을 넣어 NULL을 빼야 한다.

## 7. 스칼라 서브쿼리와 인라인 뷰

### 스칼라 서브쿼리

SELECT 절에 쓰는, **한 행 한 열**만 돌려주는 서브쿼리다.

```sql
SELECT E.ENAME,
       (SELECT D.DNAME FROM DEPT D WHERE D.DEPTNO = E.DEPTNO) AS DNAME
  FROM EMP E
 WHERE E.EMPNO IN (1001, 1005, 1010)
 ORDER BY E.EMPNO;
```

| ENAME | DNAME |
|---|---|
| 김대표 | 기획부 |
| 정대리 | 개발부 |
| 임사원 | (NULL) |

짝이 없으면 NULL을 돌려주므로 외부 조인과 비슷한 결과가 나온다. 두 행 이상을 돌려주면 오류다.

### 인라인 뷰

FROM 절에 쓰는 서브쿼리로, SQL 실행 중에만 존재하는 임시 테이블처럼 쓴다. 인라인 뷰 안에서는 ORDER BY를 쓸 수 있다.

```sql
SELECT D.DNAME, A.AVG_SAL
  FROM (SELECT DEPTNO, ROUND(AVG(SAL)) AS AVG_SAL FROM EMP GROUP BY DEPTNO) A
  JOIN DEPT D ON A.DEPTNO = D.DEPTNO
 ORDER BY A.AVG_SAL DESC;
```

| DNAME | AVG_SAL |
|---|---|
| 기획부 | 9000 |
| 개발부 | 4250 |
| 영업부 | 3950 |

## 8. 뷰(VIEW)

**뷰**는 SELECT 문에 이름을 붙여 저장해 둔 가상 테이블이다. 데이터를 따로 저장하지 않고, 조회할 때마다 정의된 SELECT 문을 실행한다.

```sql
CREATE VIEW V_EMP_DEPT AS
SELECT E.EMPNO, E.ENAME, D.DNAME
  FROM EMP E JOIN DEPT D ON E.DEPTNO = D.DEPTNO;

SELECT * FROM V_EMP_DEPT WHERE DNAME = '개발부';
DROP VIEW V_EMP_DEPT;
```

| 장점 | 설명 |
|---|---|
| 독립성 | 테이블 구조가 바뀌어도 뷰를 쓰는 프로그램은 고치지 않아도 된다 |
| 편리성 | 복잡한 쿼리를 단순하게 쓸 수 있다 |
| 보안성 | 숨기고 싶은 열을 빼고 뷰로 보여 줄 수 있다 |

뷰는 `ALTER VIEW`로 정의를 바꿀 수 없어서, `CREATE OR REPLACE VIEW`로 다시 만들거나 지우고 다시 만든다.

> **쉬운 설명**
>
> 서브쿼리는 질문 안의 작은 질문이다. '우리 반 평균보다 키가 큰 학생은?'이라고 물으면, 먼저 '우리 반 평균 키는?'이라는 작은 질문에 답해야 한다. '반마다 자기 반 평균보다 큰 학생은?'처럼 학생마다 답이 달라지면 연관 서브쿼리다.

## 헷갈렸던 것들

- 단일행 연산자에 여러 행을 돌려주는 서브쿼리를 쓰면 오류다.
- `> ANY`는 최솟값보다 크면, `> ALL`은 최댓값보다 크면 참이다. `= ANY`는 IN과 같다.
- EXISTS는 결과의 존재 여부만 확인한다.
- 서브쿼리 결과에 NULL이 있으면 NOT IN은 0건이다. NOT EXISTS는 NULL의 영향을 받지 않는다.
- 스칼라 서브쿼리는 한 행 한 열만 돌려줘야 하고, 짝이 없으면 NULL을 돌려준다.
- 중첩 서브쿼리에는 ORDER BY를 쓸 수 없지만 인라인 뷰에는 쓸 수 있다.
- 뷰는 독립성, 편리성, 보안성이 장점이고 ALTER VIEW로 정의를 바꿀 수 없다.

## 용어 정리

| 용어 | 뜻 |
|---|---|
| 서브쿼리 | SQL 문 안의 SELECT 문 |
| 연관 서브쿼리 | 메인쿼리의 열을 참조하는 서브쿼리 |
| 스칼라 서브쿼리 | SELECT 절에서 값 하나를 돌려주는 서브쿼리 |
| 인라인 뷰 | FROM 절의 서브쿼리 |
| ANY / ALL | 하나라도 만족 / 모두 만족 |
| EXISTS | 결과가 존재하는지 확인 |
| 뷰 | 이름을 붙여 저장한 가상 테이블 |

## 복습 문제

**1.** 다음 가운데 `SAL > ANY (2000, 3000, 4000)`과 같은 조건은?

① `SAL > 3000` ② `SAL > 4000` ③ `SAL IN (2000, 3000, 4000)` ④ `SAL > 2000`

**2.** 서브쿼리 결과가 (10, 20, NULL)일 때 `WHERE DEPTNO NOT IN (서브쿼리)`의 결과는?

① DEPTNO가 10, 20이 아닌 행 ② DEPTNO가 NULL인 행 ③ 0건 ④ 오류

**3.** SELECT 절에 쓰여 한 행 한 열의 값을 돌려주는 서브쿼리는?

① 인라인 뷰 ② 스칼라 서브쿼리 ③ 중첩 서브쿼리 ④ 다중컬럼 서브쿼리

**4.** 뷰의 장점이 아닌 것은?

① 데이터를 따로 저장해 조회가 항상 빠르다 ② 독립성 ③ 편리성 ④ 보안성

## 답과 풀이

1. ④ ANY는 하나라도 만족하면 되므로 최솟값 2000보다 크면 된다.
2. ③ NULL과의 비교가 UNKNOWN이라 결과가 0건이다.
3. ② 스칼라 서브쿼리다.
4. ① 일반 뷰는 데이터를 저장하지 않고 조회할 때마다 SELECT를 실행한다.

## 참고 자료

- 한국데이터산업진흥원 데이터자격검정, SQLD 출제기준: <https://www.dataq.or.kr>
- Oracle Database SQL Language Reference, Using Subqueries: <https://docs.oracle.com/en/database/oracle/oracle-database/23/sqlrf/Using-Subqueries.html>

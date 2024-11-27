---
title: '[SQLD] Top N 쿼리: ROWNUM, TOP, ROW_NUMBER, FETCH FIRST'
date: '2024-11-27T20:16:00+09:00'
categories:
- SQLD
tags:
- sqld
- sql
- top-n
- rownum
- top
- with-ties
- fetch-first
- row_number
- 페이징
- SQL 활용
series:
- SQLD
series_order: 24
---

SQL 활용 다섯 번째, Top N 쿼리. 문제는 거의 다 ROWNUM과 ORDER BY의 실행 순서 때문에 생기는 함정에서 나온다. 결과는 실제 실행 결과.

## 요약

- Top N 쿼리는 정렬한 결과에서 위쪽 N개 행만 가져온다.
- Oracle의 ROWNUM은 ORDER BY보다 **먼저** 번호가 매겨지므로, 정렬한 인라인 뷰 바깥에서 ROWNUM으로 걸러야 한다.
- SQL Server는 `TOP (N)`, 동점까지 포함하려면 `WITH TIES`를 쓴다.
- Oracle 12c부터는 표준 문법 `FETCH FIRST N ROWS ONLY`와 `OFFSET`을 쓸 수 있다.
- ROW_NUMBER, RANK 같은 윈도우 함수로도 Top N과 페이징을 할 수 있다.

## 1. ROWNUM

**ROWNUM**은 Oracle이 조회 결과의 각 행에 1부터 붙이는 가상 열(Pseudo Column)이다. WHERE 절을 통과한 행에 차례로 번호를 붙인다.

### ROWNUM과 ORDER BY의 순서

{{< mermaid >}}
flowchart LR
  A["FROM"] --> B["WHERE<br>ROWNUM 부여와 비교"] --> C["SELECT"] --> D["ORDER BY<br>정렬"]
{{< /mermaid >}}

ROWNUM은 WHERE 단계에서 매겨지고, ORDER BY는 맨 마지막에 실행된다. 그래서 다음 쿼리는 '급여가 가장 낮은 3명'을 찾지 못한다.

```sql
-- 잘못된 방법: 아무 3명을 먼저 뽑은 뒤 정렬한다
SELECT ENAME, SAL FROM EMP WHERE ROWNUM <= 3 ORDER BY SAL;
```

| ENAME | SAL |
|---|---|
| 박부장 | 5800 |
| 이부장 | 6000 |
| 김대표 | 9000 |

먼저 읽힌 3행(이 예제에서는 입력 순서대로 김대표, 이부장, 박부장)에 ROWNUM이 붙고, 그 3명을 정렬했다. 어떤 행이 먼저 읽히는지는 보장되지 않는다.

```sql
-- 올바른 방법: 인라인 뷰에서 먼저 정렬하고, 바깥에서 ROWNUM으로 자른다
SELECT ENAME, SAL
  FROM (SELECT ENAME, SAL FROM EMP ORDER BY SAL, EMPNO)
 WHERE ROWNUM <= 3;
```

| ENAME | SAL |
|---|---|
| 장사원 | 2800 |
| 임사원 | 2800 |
| 강사원 | 3000 |

### ROWNUM 비교의 규칙

| 조건 | 결과 | 이유 |
|---|---|---|
| `ROWNUM = 1` | 1행 | 첫 행이 1번을 받아 통과한다 |
| `ROWNUM <= 3` | 3행 | 1, 2, 3번이 차례로 통과한다 |
| `ROWNUM = 2` | 0행 | 첫 행이 1번을 받았지만 조건(= 2)에 안 맞아 버려지고, 다음 행이 다시 1번을 받는다. 2번은 끝내 나오지 않는다 |
| `ROWNUM > 1` | 0행 | 같은 이유 |

중간 순위(예: 4~6등)를 가져오려면 ROWNUM에 별칭을 붙여 한 번 더 감싸야 한다.

```sql
SELECT ENAME, SAL
  FROM (SELECT ROWNUM AS RN, ENAME, SAL
          FROM (SELECT ENAME, SAL FROM EMP ORDER BY SAL DESC, EMPNO))
 WHERE RN BETWEEN 4 AND 6;
```

| ENAME | SAL |
|---|---|
| 최과장 | 4500 |
| 조과장 | 4000 |
| 정대리 | 3500 |

## 2. SQL Server의 TOP

```sql
SELECT TOP (3) ENAME, SAL FROM EMP ORDER BY SAL;
SELECT TOP (1) WITH TIES ENAME, SAL FROM EMP ORDER BY SAL;
```

SQL Server의 TOP은 ORDER BY를 **적용한 뒤** 위에서 N개를 자르기 때문에 인라인 뷰가 필요 없다. `WITH TIES`는 마지막 행과 정렬 값이 같은 행까지 함께 보여 준다. 위 두 번째 쿼리는 급여 2800인 장사원과 임사원 두 명을 돌려준다. WITH TIES는 ORDER BY와 함께 써야 한다.

## 3. 윈도우 함수로 Top N

```sql
SELECT ENAME, SAL
  FROM (SELECT ENAME, SAL, RANK() OVER (ORDER BY SAL) AS R FROM EMP)
 WHERE R <= 1
 ORDER BY ENAME;
```

| ENAME | SAL |
|---|---|
| 임사원 | 2800 |
| 장사원 | 2800 |

| 함수 | 동점 처리 |
|---|---|
| ROW_NUMBER() | 동점이어도 정확히 N행 |
| RANK(), DENSE_RANK() | 동점을 모두 포함(TOP WITH TIES와 비슷) |

윈도우 함수는 WHERE 절에 직접 쓸 수 없어서 인라인 뷰로 감쌌다.

## 4. FETCH FIRST와 OFFSET (Oracle 12c 이상)

```sql
SELECT ENAME, SAL FROM EMP ORDER BY SAL, EMPNO FETCH FIRST 3 ROWS ONLY;          -- 상위 3행
SELECT ENAME, SAL FROM EMP ORDER BY SAL FETCH FIRST 1 ROWS WITH TIES;            -- 동점 포함
SELECT ENAME, SAL FROM EMP ORDER BY SAL DESC, EMPNO OFFSET 3 ROWS FETCH NEXT 3 ROWS ONLY;  -- 4~6행
```

ANSI 표준 문법이라 ORDER BY 뒤에 바로 쓰고, 인라인 뷰가 필요 없다. 결과는 각각 위의 인라인 뷰 방식과 같다. SQL Server 2012 이상도 `OFFSET ... FETCH`를 지원한다.

> **쉬운 설명**
>
> ROWNUM은 줄을 서기 전에 번호표를 나눠 주는 방식이다. 아무렇게나 서 있는 사람들에게 번호표를 1, 2, 3 주고 나서 키 순서로 세우면, '키가 작은 3명'이 아니라 '번호표를 받은 3명'이 키순으로 설 뿐이다. 그래서 먼저 키 순서로 줄을 세우고(인라인 뷰의 ORDER BY), 그다음에 번호표를 나눠 줘야 한다.

## 헷갈렸던 것들

- ROWNUM은 ORDER BY보다 먼저 매겨진다. 정렬 후 Top N은 인라인 뷰에서 정렬하고 바깥에서 ROWNUM을 건다.
- `ROWNUM = 1`과 `ROWNUM <= N`은 되지만, `ROWNUM = 2`, `ROWNUM > 1`은 결과가 없다.
- SQL Server의 TOP은 ORDER BY 뒤에 자르고, WITH TIES는 동점을 포함한다.
- ROW_NUMBER는 동점이어도 N행, RANK는 동점을 모두 포함한다.
- FETCH FIRST는 Oracle 12c부터 쓸 수 있는 표준 문법이다.

## 용어 정리

| 용어 | 뜻 |
|---|---|
| Top N 쿼리 | 정렬한 결과에서 위쪽 N개를 가져오는 쿼리 |
| ROWNUM | Oracle이 결과 행에 붙이는 가상 순번 |
| TOP (N) | SQL Server의 Top N 문법 |
| WITH TIES | 마지막 행과 같은 값의 행까지 포함 |
| FETCH FIRST / OFFSET | 표준 Top N과 페이징 문법 |

## 복습 문제

**1.** 다음 SQL의 결과로 옳은 것은?

```sql
SELECT ENAME FROM EMP WHERE ROWNUM = 2;
```

① 두 번째 사원 1명 ② 사원 2명 ③ 오류 ④ 0행

**2.** 급여가 가장 높은 3명을 정확히 구하는 Oracle SQL은?

① `SELECT * FROM EMP WHERE ROWNUM <= 3 ORDER BY SAL DESC;` ② `SELECT * FROM (SELECT * FROM EMP ORDER BY SAL DESC) WHERE ROWNUM <= 3;` ③ `SELECT * FROM EMP ORDER BY SAL DESC WHERE ROWNUM <= 3;` ④ `SELECT TOP 3 * FROM EMP ORDER BY SAL DESC;`

**3.** SQL Server에서 급여 오름차순으로 1명을 뽑을 때, 같은 최저 급여를 받는 사원이 모두 나오게 하는 키워드는?

① DISTINCT ② ALL ③ PERCENT ④ WITH TIES

## 답과 풀이

1. ④ 첫 행이 1번을 받고 조건에 맞지 않아 버려지기를 반복하므로 2번은 나오지 않는다.
2. ② 인라인 뷰에서 먼저 정렬해야 한다. ③은 문법 오류, ④는 SQL Server 문법이다.
3. ④ WITH TIES이다.

## 참고 자료

- 한국데이터산업진흥원 데이터자격검정, SQLD 출제기준: <https://www.dataq.or.kr>
- Oracle Database SQL Language Reference, ROWNUM Pseudocolumn: <https://docs.oracle.com/en/database/oracle/oracle-database/23/sqlrf/ROWNUM-Pseudocolumn.html>

---
title: '[SQLD] 계층형 질의와 셀프 조인: START WITH, CONNECT BY, LEVEL'
date: '2024-11-28T23:02:00+09:00'
categories:
- SQLD
tags:
- sqld
- sql
- 계층형질의
- connect-by
- start-with
- level
- sys_connect_by_path
- 셀프조인
- SQL 활용
series:
- SQLD
series_order: 25
---

`CONNECT BY PRIOR`의 방향(순방향, 역방향)과 LEVEL 값, 가상 열과 함수가 자주 나온다. 예제는 관리자 관계가 4단계인 EMP 테이블이다.

## 요약

- 계층형 데이터는 같은 테이블 안에서 상위와 하위 관계를 갖는 데이터다(사원과 관리자, 상위 메뉴와 하위 메뉴).
- 셀프 조인은 바로 위아래 한 단계를, 계층형 질의는 여러 단계를 한 번에 펼쳐 본다.
- Oracle 계층형 질의는 `START WITH`로 시작점을, `CONNECT BY PRIOR`로 연결 방향을 정한다.
- `PRIOR 자식 = 부모`는 위에서 아래로(순방향), `PRIOR 부모 = 자식`은 아래에서 위로(역방향) 내려간다.
- LEVEL, CONNECT_BY_ISLEAF, SYS_CONNECT_BY_PATH, CONNECT_BY_ROOT로 깊이, 끝 여부, 경로, 시작점을 알 수 있다.

## 1. 예제 데이터의 계층

{{< mermaid >}}
flowchart TB
  K["1001 김대표"] --> L["1002 이부장"]
  K --> P["1003 박부장"]
  K --> I["1010 임사원"]
  L --> C["1004 최과장"]
  C --> J["1005 정대리"]
  C --> G["1006 강사원"]
  P --> O["1007 조과장"]
  P --> Y["1008 윤대리"]
  P --> S["1009 장사원"]
{{< /mermaid >}}

EMP의 MGR(관리자 사원번호)이 같은 테이블의 EMPNO를 가리킨다.

## 2. 셀프 조인

같은 테이블을 별칭으로 두 번 써서 조인한다. 한 단계 위(관리자)를 붙일 때 좋다.

```sql
SELECT E.ENAME AS 사원, M.ENAME AS 관리자
  FROM EMP E
  JOIN EMP M ON E.MGR = M.EMPNO
 WHERE E.DEPTNO = 30
 ORDER BY E.EMPNO;
```

| 사원 | 관리자 |
|---|---|
| 박부장 | 김대표 |
| 조과장 | 박부장 |
| 윤대리 | 박부장 |
| 장사원 | 박부장 |

내부 조인이라 관리자가 없는 김대표는 빠진다. 김대표도 보이게 하려면 LEFT OUTER JOIN을 쓴다. 관리자의 관리자까지 보려면 EMP를 한 번 더 조인해야 해서, 단계가 많아지면 계층형 질의가 편하다.

## 3. 계층형 질의 문법 (Oracle)

```sql
SELECT LEVEL, LPAD(' ', 2 * (LEVEL - 1)) || ENAME AS 조직도, EMPNO, MGR,
       CONNECT_BY_ISLEAF AS ISLEAF,
       SYS_CONNECT_BY_PATH(ENAME, '/') AS PATH
  FROM EMP
 START WITH MGR IS NULL               -- 시작점: 관리자가 없는 김대표
CONNECT BY PRIOR EMPNO = MGR          -- 부모의 EMPNO = 자식의 MGR (위 → 아래)
 ORDER SIBLINGS BY EMPNO;             -- 같은 부모 아래 형제끼리만 정렬
```

| LEVEL | 조직도 | EMPNO | MGR | ISLEAF | PATH |
|---|---|---|---|---|---|
| 1 | 김대표 | 1001 | (NULL) | 0 | /김대표 |
| 2 | 　이부장 | 1002 | 1001 | 0 | /김대표/이부장 |
| 3 | 　　최과장 | 1004 | 1002 | 0 | /김대표/이부장/최과장 |
| 4 | 　　　정대리 | 1005 | 1004 | 1 | /김대표/이부장/최과장/정대리 |
| 4 | 　　　강사원 | 1006 | 1004 | 1 | /김대표/이부장/최과장/강사원 |
| 2 | 　박부장 | 1003 | 1001 | 0 | /김대표/박부장 |
| 3 | 　　조과장 | 1007 | 1003 | 1 | /김대표/박부장/조과장 |
| 3 | 　　윤대리 | 1008 | 1003 | 1 | /김대표/박부장/윤대리 |
| 3 | 　　장사원 | 1009 | 1003 | 1 | /김대표/박부장/장사원 |
| 2 | 　임사원 | 1010 | 1001 | 1 | /김대표/임사원 |

(표에서는 들여쓰기가 보이도록 전각 공백으로 바꿔 적었다.)

| 구문, 가상 열 | 뜻 |
|---|---|
| START WITH 조건 | 계층의 시작점(루트)을 정한다 |
| CONNECT BY PRIOR 조건 | 부모와 자식을 잇는 조건. PRIOR가 붙은 쪽이 앞서 읽은 행(부모 쪽)이다 |
| LEVEL | 루트가 1이고, 한 단계 내려갈 때마다 1씩 커진다 |
| CONNECT_BY_ISLEAF | 자식이 없는 끝 행(리프)이면 1, 아니면 0 |
| SYS_CONNECT_BY_PATH(열, 구분자) | 루트부터 현재 행까지의 경로 |
| CONNECT_BY_ROOT 열 | 현재 행의 루트 값 |
| ORDER SIBLINGS BY | 계층 구조를 유지한 채 형제 행끼리 정렬 |
| NOCYCLE | 데이터에 순환(A → B → A)이 있어도 멈추지 않게 한다. CONNECT_BY_ISCYCLE로 순환 행을 찾는다 |

결과는 깊이 우선으로 펼쳐진다. 이부장 아래를 끝까지 내려간 뒤에 박부장으로 넘어간다. 일반 `ORDER BY`를 쓰면 이 계층 순서가 깨진다.

### 실행 순서

1. START WITH로 루트 행을 고른다.
2. CONNECT BY로 자식 행을 찾아 계층을 펼친다.
3. WHERE 조건으로 행을 거른다.

WHERE 절은 계층을 다 펼친 **뒤에** 적용된다. 예를 들어 `WHERE ENAME <> '최과장'`을 넣으면 최과장 한 행만 빠지고 그 아래 정대리와 강사원은 남는다. 가지 전체를 빼려면 조건을 CONNECT BY 절에 넣는다(`CONNECT BY PRIOR EMPNO = MGR AND ENAME <> '최과장'`).

## 4. 순방향과 역방향

| 방향 | CONNECT BY 조건 | 뜻 |
|---|---|---|
| 순방향(위 → 아래) | `PRIOR EMPNO = MGR` | 앞 행(부모)의 EMPNO를 MGR로 가진 행(자식)을 찾는다 |
| 역방향(아래 → 위) | `PRIOR MGR = EMPNO` | 앞 행(자식)의 MGR을 EMPNO로 가진 행(부모)을 찾는다 |

```sql
SELECT LEVEL, ENAME, EMPNO, MGR
  FROM EMP
 START WITH ENAME = '강사원'
CONNECT BY PRIOR MGR = EMPNO;
```

| LEVEL | ENAME | EMPNO | MGR |
|---|---|---|---|
| 1 | 강사원 | 1006 | 1004 |
| 2 | 최과장 | 1004 | 1002 |
| 3 | 이부장 | 1002 | 1001 |
| 4 | 김대표 | 1001 | (NULL) |

역방향에서는 시작점인 강사원이 LEVEL 1이고, 위로 올라갈수록 LEVEL이 커진다.

```sql
SELECT LEVEL, ENAME, CONNECT_BY_ROOT ENAME AS ROOT
  FROM EMP
 START WITH EMPNO = 1002
CONNECT BY PRIOR EMPNO = MGR;
```

| LEVEL | ENAME | ROOT |
|---|---|---|
| 1 | 이부장 | 이부장 |
| 2 | 최과장 | 이부장 |
| 3 | 정대리 | 이부장 |
| 3 | 강사원 | 이부장 |

시작점을 중간(이부장)으로 잡으면 그 아래만 펼쳐지고, CONNECT_BY_ROOT는 시작점의 값을 돌려준다.

SQL Server는 CONNECT BY가 없어서 재귀 CTE(`WITH ... UNION ALL`)로 계층을 펼친다.

> **쉬운 설명**
>
> 족보를 펼치는 것과 같다. START WITH는 '누구부터 볼까', CONNECT BY PRIOR는 '부모에서 자식으로 내려갈까, 자식에서 부모로 올라갈까'이다. PRIOR는 '방금 본 사람'이라는 뜻이다. `PRIOR EMPNO = MGR`은 '방금 본 사람의 사번을 관리자로 적은 사람', 즉 그 사람의 부하를 찾으라는 말이다.

## 헷갈렸던 것들

- `PRIOR 자식키 = 부모키`(`PRIOR EMPNO = MGR`)는 순방향, `PRIOR 부모키 = 자식키`(`PRIOR MGR = EMPNO`)는 역방향이다.
- 루트의 LEVEL은 1이다. 역방향에서도 시작점이 1이다.
- CONNECT_BY_ISLEAF는 리프면 1이다.
- WHERE 조건은 계층을 펼친 뒤에 적용되어 해당 행만 빠진다. 가지째 빼려면 CONNECT BY에 조건을 넣는다.
- ORDER SIBLINGS BY는 계층을 유지한 채 형제끼리 정렬한다.
- 셀프 조인에는 테이블 별칭이 반드시 필요하다.

## 용어 정리

| 용어 | 뜻 |
|---|---|
| 계층형 질의 | 계층 구조 데이터를 여러 단계로 펼치는 질의 |
| START WITH | 시작점(루트) 지정 |
| CONNECT BY PRIOR | 부모와 자식의 연결 조건 |
| LEVEL | 계층의 깊이 |
| 리프(leaf) | 자식이 없는 끝 노드 |
| 셀프 조인 | 같은 테이블끼리의 조인 |

## 복습 문제

**1.** 김대표(MGR이 NULL)부터 부하 직원 방향으로 펼치는 CONNECT BY 조건은?

① `CONNECT BY PRIOR MGR = EMPNO` ② `CONNECT BY PRIOR EMPNO = MGR` ③ `CONNECT BY EMPNO = MGR` ④ `CONNECT BY PRIOR EMPNO = EMPNO`

**2.** 위 예제의 순방향 계층형 질의에서 정대리의 LEVEL은?

① 1 ② 2 ③ 3 ④ 4

**3.** 계층형 질의에서 자식이 없는 행을 1로 표시하는 가상 열은?

① CONNECT_BY_ISLEAF ② LEVEL ③ CONNECT_BY_ROOT ④ ROWNUM

**4.** 순방향 계층형 질의에 `WHERE ENAME <> '최과장'`을 넣었을 때 결과로 옳은 것은?

① 최과장과 그 아래 정대리, 강사원이 모두 빠진다 ② 오류가 난다 ③ 최과장 한 행만 빠진다 ④ 결과가 0행이다

## 답과 풀이

1. ② 부모(PRIOR)의 EMPNO를 MGR로 가진 자식을 찾는 순방향이다.
2. ④ 김대표(1) → 이부장(2) → 최과장(3) → 정대리(4)이다.
3. ① CONNECT_BY_ISLEAF이다.
4. ③ WHERE는 계층을 펼친 뒤 적용되어 그 행만 빠진다.

## 참고 자료

- 한국데이터산업진흥원 데이터자격검정, SQLD 출제기준: <https://www.dataq.or.kr>
- Oracle Database SQL Language Reference, Hierarchical Queries: <https://docs.oracle.com/en/database/oracle/oracle-database/23/sqlrf/Hierarchical-Queries.html>

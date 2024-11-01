---
title: '[SQLD] 실습 환경과 예제 데이터: 사원, 부서, 급여등급 테이블'
date: '2024-11-01T20:20:00+09:00'
categories:
- SQLD
tags:
- sqld
- sql
- oracle
- 예제데이터
- erd
- 준비
series:
- SQLD
series_order: 1
---

SQLD 정리에서 쓰는 예제 데이터를 모아 둔 글. 시험이 Oracle 문법 기준이라 예제도 Oracle로 만들었다. 아래 스크립트를 한 번 돌려 두면 시리즈의 쿼리를 그대로 따라 쳐 볼 수 있다. 데이터는 전부 연습용으로 지어낸 값이다.

## 실습 환경

| 방법 | 설명 |
|---|---|
| Oracle FreeSQL | 브라우저에서 바로 Oracle SQL을 실행하는 무료 웹 서비스다. 설치가 필요 없다. <https://freesql.com> |
| Oracle Database Free | 내 컴퓨터에 설치하는 무료 Oracle이다. Docker로 띄우면 간단하다. <https://www.oracle.com/database/free/> |

MySQL이나 PostgreSQL에서도 대부분의 쿼리가 돌아가지만, `NVL`, `DECODE`, `ROWNUM`, `CONNECT BY`, `(+)` 같은 Oracle 전용 문법은 실행되지 않는다. 이런 문법이 나오면 글에서 따로 표시하겠다.

## 테이블 구성

회사 하나를 단순하게 표현한 세 테이블이다.

{{< mermaid >}}
erDiagram
  DEPT ||--o{ EMP : "소속된다"
  EMP |o--o{ EMP : "관리한다"
  DEPT {
    NUMBER DEPTNO PK "부서번호"
    VARCHAR2 DNAME "부서명"
    VARCHAR2 LOC "지역"
  }
  EMP {
    NUMBER EMPNO PK "사원번호"
    VARCHAR2 ENAME "사원명"
    VARCHAR2 JOB "직무"
    NUMBER MGR FK "관리자 사원번호"
    DATE HIREDATE "입사일"
    NUMBER SAL "급여"
    NUMBER COMM "커미션"
    NUMBER DEPTNO FK "부서번호"
  }
  SALGRADE {
    NUMBER GRADE PK "급여등급"
    NUMBER LOSAL "최저 급여"
    NUMBER HISAL "최고 급여"
  }
{{< /mermaid >}}

한 부서에는 사원이 여러 명 있을 수 있고(1:N), 사원은 관리자(역시 사원)를 한 명 가질 수 있다. 관리자 관계는 같은 테이블 안에서 이어지는 **자기 참조(순환) 관계**이다. 급여등급(SALGRADE)은 다른 테이블과 키로 이어지지 않고, 급여 범위로 비교해 조인한다(비등가 조인).

### DEPT: 부서

| 컬럼 | 한국어 이름 | 데이터 타입 | 설명 |
|---|---|---|---|
| DEPTNO | 부서번호 | NUMBER(2) | 부서를 구분하는 번호. 기본키(PK) |
| DNAME | 부서명 | VARCHAR2(20) | 부서 이름. 반드시 입력(NOT NULL) |
| LOC | 지역 | VARCHAR2(20) | 부서가 있는 도시 |

### EMP: 사원

| 컬럼 | 한국어 이름 | 데이터 타입 | 설명 |
|---|---|---|---|
| EMPNO | 사원번호 | NUMBER(4) | 사원을 구분하는 번호. 기본키(PK) |
| ENAME | 사원명 | VARCHAR2(20) | 사원 이름. 반드시 입력(NOT NULL) |
| JOB | 직무 | VARCHAR2(20) | PRESIDENT, MANAGER, ANALYST, DEVELOPER, SALESMAN, CLERK |
| MGR | 관리자 사원번호 | NUMBER(4) | 이 사원을 관리하는 사원의 EMPNO. 대표는 관리자가 없어 NULL |
| HIREDATE | 입사일 | DATE | 입사한 날짜 |
| SAL | 급여 | NUMBER(7) | 월 급여(만 원이 아닌 가상의 단위) |
| COMM | 커미션 | NUMBER(7) | 영업 사원의 성과급. 영업 사원이 아니면 NULL, 성과가 없으면 0 |
| DEPTNO | 부서번호 | NUMBER(2) | 소속 부서. DEPT.DEPTNO를 참조하는 외래키(FK). 아직 배치되지 않은 사원은 NULL |

### SALGRADE: 급여등급

| 컬럼 | 한국어 이름 | 데이터 타입 | 설명 |
|---|---|---|---|
| GRADE | 급여등급 | NUMBER(1) | 등급 번호. 기본키(PK) |
| LOSAL | 최저 급여 | NUMBER(7) | 이 등급의 급여 하한 |
| HISAL | 최고 급여 | NUMBER(7) | 이 등급의 급여 상한 |

### 키와 관계 예시

기본키(PK, Primary Key)는 한 행을 다른 행과 구분하는 값이다. EMPNO가 1005인 사원은 한 명뿐이다. 외래키(FK, Foreign Key)는 다른 테이블의 기본키를 가리키는 값이다. 정대리의 DEPTNO 20은 DEPT 테이블에서 DEPTNO가 20인 '개발부'를 가리킨다. DEPT에 없는 부서번호(예: 50)는 EMP.DEPTNO에 넣을 수 없다.

## 생성 스크립트

```sql
CREATE TABLE DEPT (
  DEPTNO NUMBER(2)    PRIMARY KEY,
  DNAME  VARCHAR2(20) NOT NULL,
  LOC    VARCHAR2(20)
);

CREATE TABLE EMP (
  EMPNO    NUMBER(4)    PRIMARY KEY,
  ENAME    VARCHAR2(20) NOT NULL,
  JOB      VARCHAR2(20),
  MGR      NUMBER(4),
  HIREDATE DATE,
  SAL      NUMBER(7),
  COMM     NUMBER(7),
  DEPTNO   NUMBER(2) REFERENCES DEPT(DEPTNO)
);

CREATE TABLE SALGRADE (
  GRADE NUMBER(1) PRIMARY KEY,
  LOSAL NUMBER(7),
  HISAL NUMBER(7)
);

INSERT INTO DEPT VALUES (10, '기획부', '서울');
INSERT INTO DEPT VALUES (20, '개발부', '판교');
INSERT INTO DEPT VALUES (30, '영업부', '부산');
INSERT INTO DEPT VALUES (40, '인사부', '대전');

INSERT INTO EMP VALUES (1001, '김대표', 'PRESIDENT', NULL, DATE '2015-01-05', 9000, NULL, 10);
INSERT INTO EMP VALUES (1002, '이부장', 'MANAGER',   1001, DATE '2016-03-02', 6000, NULL, 20);
INSERT INTO EMP VALUES (1003, '박부장', 'MANAGER',   1001, DATE '2016-07-15', 5800, NULL, 30);
INSERT INTO EMP VALUES (1004, '최과장', 'ANALYST',   1002, DATE '2018-02-01', 4500, NULL, 20);
INSERT INTO EMP VALUES (1005, '정대리', 'DEVELOPER', 1004, DATE '2020-09-01', 3500, NULL, 20);
INSERT INTO EMP VALUES (1006, '강사원', 'DEVELOPER', 1004, DATE '2022-01-03', 3000, NULL, 20);
INSERT INTO EMP VALUES (1007, '조과장', 'SALESMAN',  1003, DATE '2018-05-10', 4000, 500,  30);
INSERT INTO EMP VALUES (1008, '윤대리', 'SALESMAN',  1003, DATE '2021-04-12', 3200, 300,  30);
INSERT INTO EMP VALUES (1009, '장사원', 'SALESMAN',  1003, DATE '2023-03-02', 2800, 0,    30);
INSERT INTO EMP VALUES (1010, '임사원', 'CLERK',     1001, DATE '2023-08-01', 2800, NULL, NULL);

INSERT INTO SALGRADE VALUES (1, 0,    2999);
INSERT INTO SALGRADE VALUES (2, 3000, 3999);
INSERT INTO SALGRADE VALUES (3, 4000, 4999);
INSERT INTO SALGRADE VALUES (4, 5000, 6999);
INSERT INTO SALGRADE VALUES (5, 7000, 9999);

COMMIT;
```

## 데이터 미리 보기

**DEPT**

| DEPTNO | DNAME | LOC |
|---|---|---|
| 10 | 기획부 | 서울 |
| 20 | 개발부 | 판교 |
| 30 | 영업부 | 부산 |
| 40 | 인사부 | 대전 |

**EMP**

| EMPNO | ENAME | JOB | MGR | HIREDATE | SAL | COMM | DEPTNO |
|---|---|---|---|---|---|---|---|
| 1001 | 김대표 | PRESIDENT | (NULL) | 2015-01-05 | 9000 | (NULL) | 10 |
| 1002 | 이부장 | MANAGER | 1001 | 2016-03-02 | 6000 | (NULL) | 20 |
| 1003 | 박부장 | MANAGER | 1001 | 2016-07-15 | 5800 | (NULL) | 30 |
| 1004 | 최과장 | ANALYST | 1002 | 2018-02-01 | 4500 | (NULL) | 20 |
| 1005 | 정대리 | DEVELOPER | 1004 | 2020-09-01 | 3500 | (NULL) | 20 |
| 1006 | 강사원 | DEVELOPER | 1004 | 2022-01-03 | 3000 | (NULL) | 20 |
| 1007 | 조과장 | SALESMAN | 1003 | 2018-05-10 | 4000 | 500 | 30 |
| 1008 | 윤대리 | SALESMAN | 1003 | 2021-04-12 | 3200 | 300 | 30 |
| 1009 | 장사원 | SALESMAN | 1003 | 2023-03-02 | 2800 | 0 | 30 |
| 1010 | 임사원 | CLERK | 1001 | 2023-08-01 | 2800 | (NULL) | (NULL) |

**SALGRADE**

| GRADE | LOSAL | HISAL |
|---|---|---|
| 1 | 0 | 2999 |
| 2 | 3000 | 3999 |
| 3 | 4000 | 4999 |
| 4 | 5000 | 6999 |
| 5 | 7000 | 9999 |

예제를 일부러 이렇게 만들었다.

- 인사부(40)에는 사원이 없고, 임사원은 부서가 없다. 외부 조인의 차이를 보여 주기 위해서다.
- 커미션에는 NULL과 0이 섞여 있다. NULL과 0의 차이, 집계 함수가 NULL을 다루는 방식을 보여 주기 위해서다.
- 장사원과 임사원의 급여가 2800으로 같다. 순위 함수가 동점을 다루는 방식을 보여 주기 위해서다.
- 관리자 관계는 김대표 → 부장 → 과장 → 대리·사원의 4단계다. 계층형 질의와 셀프 조인에 쓴다.

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

## 참고 자료

- 한국데이터산업진흥원 데이터자격검정, SQLD 출제기준: <https://www.dataq.or.kr>
- 이 시리즈의 SQL 결과 표는 위 데이터로 실제 실행해 확인한 결과다. 결과는 DuckDB에서 NULL 정렬 순서를 Oracle과 같게 설정해 확인했고, Oracle 전용 문법은 같은 뜻의 표준 SQL로 바꿔 결과를 확인했다.

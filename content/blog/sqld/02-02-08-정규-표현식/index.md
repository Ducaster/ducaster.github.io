---
title: '[SQLD] 정규 표현식: REGEXP_LIKE, REGEXP_SUBSTR, REGEXP_REPLACE'
date: '2024-11-30T21:24:00+09:00'
categories:
- SQLD
tags:
- sqld
- sql
- 정규표현식
- regexp_like
- regexp_substr
- regexp_replace
- regexp_instr
- regexp_count
- SQL 활용
series:
- SQLD
series_order: 27
---

정규 표현식도 2024년 개편 때 추가됐다. 메타 문자의 뜻과 함수 결과값을 묻는 문제가 나온다. 예제 결과는 직접 실행해서 확인했다.

## 요약

- 정규 표현식은 문자열의 패턴을 기호로 나타내는 방법이다. LIKE보다 훨씬 정교한 검색과 치환을 할 수 있다.
- Oracle은 REGEXP_LIKE(조건), REGEXP_SUBSTR(추출), REGEXP_REPLACE(치환), REGEXP_INSTR(위치), REGEXP_COUNT(개수)를 제공한다.
- `.`은 아무 문자 하나, `*`는 0회 이상, `+`는 1회 이상, `?`는 0회 또는 1회, `{m,n}`은 m회 이상 n회 이하다.
- `^`는 시작, `$`는 끝, `[ ]`는 문자 집합, `[^ ]`는 제외 집합, `|`는 또는, `( )`는 그룹이다.
- 수량자는 기본적으로 가능한 한 길게 맞추고(탐욕적), 뒤에 `?`를 붙이면 가능한 한 짧게 맞춘다(게으른).

## 1. 메타 문자

### 기본 메타 문자

| 기호 | 뜻 | 예 | 맞는 문자열 |
|---|---|---|---|
| . | 아무 문자 하나 | a.c | abc, a1c |
| ^ | 문자열의 시작 | ^김 | 김대표 |
| $ | 문자열의 끝 | 원$ | 강사원 |
| [ ] | 괄호 안의 문자 중 하나 | [abc] | a, b, c |
| [^ ] | 괄호 안에 없는 문자 하나 | [^0-9] | 숫자가 아닌 문자 |
| - | 범위(괄호 안에서) | [a-z], [0-9] | 소문자, 숫자 |
| \| | 또는 | 김\|이 | 김, 이 |
| ( ) | 그룹 | (ab)+ | ab, abab |
| \ | 다음 문자를 문자 그대로 | \\. | 마침표 자체 |
| \n | n번째 그룹이 맞춘 문자열(역참조) | (a)\\1 | aa |

### 수량자

| 기호 | 뜻 |
|---|---|
| * | 앞 패턴이 0회 이상 |
| + | 앞 패턴이 1회 이상 |
| ? | 앞 패턴이 0회 또는 1회 |
| {m} | 정확히 m회 |
| {m,} | m회 이상 |
| {m,n} | m회 이상 n회 이하 |
| *?, +?, ??, {m,n}? | 위와 같지만 가능한 한 짧게(게으른 수량자) |

### 문자 클래스

| Perl 형식 | POSIX 형식 | 뜻 |
|---|---|---|
| `\d` | `[[:digit:]]` | 숫자 |
| `\D` | `[^[:digit:]]` | 숫자가 아닌 문자 |
| `\w` | `[[:alnum:]_]` | 영문자, 숫자, 밑줄 |
| `\W` | | `\w`가 아닌 문자 |
| `\s` | `[[:space:]]` | 공백 문자 |
| `\S` | | 공백이 아닌 문자 |
| | `[[:alpha:]]` | 영문자 |
| | `[[:upper:]]`, `[[:lower:]]` | 대문자, 소문자 |
| | `[[:punct:]]` | 문장 부호 |

## 2. 정규 표현식 함수

| 함수 | 하는 일 |
|---|---|
| REGEXP_LIKE(문자열, 패턴 [, 옵션]) | 패턴과 맞으면 참. WHERE 절의 조건으로 쓴다 |
| REGEXP_SUBSTR(문자열, 패턴 [, 시작 위치 [, n번째 [, 옵션 [, 그룹 번호]]]]) | 패턴에 맞는 부분 문자열을 꺼낸다 |
| REGEXP_REPLACE(문자열, 패턴 [, 바꿀 문자열 [, 시작 위치 [, n번째 [, 옵션]]]]) | 패턴에 맞는 부분을 바꾼다. n번째를 생략하거나 0이면 모두 바꾼다 |
| REGEXP_INSTR(문자열, 패턴 [, 시작 위치 [, n번째 [, 반환 옵션 [, 옵션]]]]) | 패턴이 나오는 위치 |
| REGEXP_COUNT(문자열, 패턴 [, 시작 위치 [, 옵션]]) | 패턴이 나오는 횟수 |

옵션(match parameter)으로는 대소문자를 무시하는 `'i'`, 구분하는 `'c'`, 여러 줄 모드 `'m'`, 마침표가 줄바꿈과도 맞게 하는 `'n'`, 패턴 안의 공백을 무시하는 `'x'`가 있다.

### 함수별 예제

```sql
SELECT REGEXP_SUBSTR('abc123def45', '[0-9]+')        AS A,   -- 첫 번째 숫자 덩어리
       REGEXP_SUBSTR('abc123def45', '[0-9]+', 1, 2)  AS B,   -- 두 번째 숫자 덩어리
       REGEXP_REPLACE('010-1234-5678', '[0-9]', '*') AS C,   -- 숫자를 모두 *로
       REGEXP_REPLACE('010-1234-5678', '-')          AS D,   -- 바꿀 문자열 생략 → 삭제
       REGEXP_INSTR('abc123def45', '[0-9]')          AS E,   -- 첫 숫자의 위치
       REGEXP_COUNT('abc123def45', '[0-9]')          AS F    -- 숫자의 개수
  FROM DUAL;
```

| A | B | C | D | E | F |
|---|---|---|---|---|---|
| 123 | 45 | \*\*\*-\*\*\*\*-\*\*\*\* | 01012345678 | 4 | 5 |

```sql
SELECT REGEXP_SUBSTR('<b>bold</b>', '<.+>')         AS GREEDY,  -- 가능한 한 길게
       REGEXP_SUBSTR('<b>bold</b>', '<.+?>')        AS LAZY,    -- 가능한 한 짧게
       REGEXP_REPLACE('홍 길동', '(.+) (.+)', '\2 \1') AS SWAP,  -- 그룹 순서 바꾸기
       REGEXP_SUBSTR('2024-10-27', '([0-9]{4})-([0-9]{2})-([0-9]{2})', 1, 1, NULL, 2) AS MM
  FROM DUAL;
```

| GREEDY | LAZY | SWAP | MM |
|---|---|---|---|
| &lt;b&gt;bold&lt;/b&gt; | &lt;b&gt; | 길동 홍 | 10 |

- 탐욕적인 `<.+>`는 처음 `<`부터 마지막 `>`까지 길게 맞췄고, 게으른 `<.+?>`는 첫 `>`에서 멈췄다.
- `\1`, `\2`는 첫 번째, 두 번째 괄호 그룹이 맞춘 문자열이다.
- REGEXP_SUBSTR의 마지막 인수 2는 두 번째 그룹(월)을 꺼내라는 뜻이다.

### WHERE 절에서 REGEXP_LIKE

```sql
SELECT ENAME FROM EMP WHERE REGEXP_LIKE(ENAME, '^(김|이|박)') ORDER BY EMPNO;
```

| ENAME |
|---|
| 김대표 |
| 이부장 |
| 박부장 |

```sql
SELECT ENAME, JOB FROM EMP
 WHERE REGEXP_LIKE(JOB, '^(SALES|DEVEL)')
   AND NOT REGEXP_LIKE(ENAME, '사원$')
 ORDER BY EMPNO;
```

| ENAME | JOB |
|---|---|
| 정대리 | DEVELOPER |
| 조과장 | SALESMAN |
| 윤대리 | SALESMAN |

```sql
-- 간단한 이메일 형식 검사
SELECT X, CASE WHEN REGEXP_LIKE(X, '^[a-z0-9._]+@[a-z0-9]+\.[a-z]{2,}$') THEN 'O' ELSE 'X' END AS OK
  FROM (SELECT 'sqld@example.com' AS X FROM DUAL UNION ALL
        SELECT 'sqld@example'          FROM DUAL UNION ALL
        SELECT 'SQLD@EXAMPLE.COM'      FROM DUAL);
```

| X | OK |
|---|---|
| sqld@example.com | O |
| sqld@example | X |
| SQLD@EXAMPLE.COM | X |

`\.`은 마침표 문자 자체다. 기본 설정에서는 대소문자를 구분해서 대문자 주소가 맞지 않았다. `REGEXP_LIKE(X, '...', 'i')`처럼 옵션 `'i'`를 주면 맞다.

> **쉬운 설명**
>
> 정규 표현식은 '글자 모양 설명서'이다. `010-[0-9]{4}-[0-9]{4}`는 '010, 하이픈, 숫자 네 개, 하이픈, 숫자 네 개'라는 전화번호 모양을 뜻한다. LIKE가 '~로 시작하는', '~를 포함하는' 정도만 말할 수 있다면, 정규 표현식은 '숫자가 정확히 네 번 오는'처럼 훨씬 자세하게 말할 수 있다.

## 헷갈렸던 것들

- `*`는 0회 이상, `+`는 1회 이상, `?`는 0회 또는 1회다.
- `^`는 대괄호 밖에서는 '시작', 대괄호 안 첫 자리에서는 '제외'이다.
- 수량자는 기본이 탐욕적이고, `?`를 붙이면 게으르다.
- REGEXP_REPLACE의 바꿀 문자열을 생략하면 맞는 부분을 지운다. n번째 인수를 생략하면 모두 바꾼다.
- REGEXP_SUBSTR의 네 번째 인수는 몇 번째로 맞는 부분인지다.
- REGEXP_LIKE는 조건이라 WHERE 절에 쓰고, 기본적으로 대소문자를 구분한다.

## 용어 정리

| 용어 | 뜻 |
|---|---|
| 정규 표현식 | 문자열 패턴을 기호로 나타낸 식 |
| 메타 문자 | 정규 표현식에서 특별한 뜻을 가진 기호 |
| 수량자 | 앞 패턴의 반복 횟수를 정하는 기호 |
| 탐욕적 / 게으른 수량자 | 가능한 한 길게 / 짧게 맞추는 수량자 |
| 역참조 | 앞 그룹이 맞춘 문자열을 \n으로 다시 쓰는 것 |

## 복습 문제

**1.** `REGEXP_SUBSTR('A1B22C333', '[0-9]+', 1, 3)`의 결과는?

① 1 ② 22 ③ 333 ④ NULL

**2.** `REGEXP_REPLACE('2024-10-27', '[^0-9]')`의 결과는?

① 20241027 ② 2024-10-27 ③ --- ④ NULL

**3.** 다음 패턴 가운데 'colour'와 'color'에 모두 맞는 것은?

① `colou?r` ② `colou+r` ③ `colo[u]r` ④ `col[ou]r`

**4.** `REGEXP_COUNT('banana', 'a')`의 결과는?

① 1 ② 2 ③ 3 ④ 6

## 답과 풀이

1. ③ 숫자 덩어리는 1, 22, 333 순서로 나오고, 세 번째는 333이다.
2. ① 숫자가 아닌 문자(하이픈)를 지운다.
3. ① `?`는 u가 0회 또는 1회라 두 철자 모두 맞다. ②와 ③은 u가 반드시 있어야 하고, ④는 o나 u 한 글자만 허용한다.
4. ③ a가 세 번 나온다.

## 참고 자료

- 한국데이터산업진흥원 데이터자격검정, SQLD 출제기준: <https://www.dataq.or.kr>
- Oracle Database SQL Language Reference, Oracle Regular Expression Support: <https://docs.oracle.com/en/database/oracle/oracle-database/23/sqlrf/Oracle-Regular-Expression-Support.html>

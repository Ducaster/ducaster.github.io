---
title: '[SAA] 데이터 보안 통제: KMS, 서비스별 암호화, Object Lock, AWS Backup'
date: '2024-12-13T21:40:00+09:00'
categories:
- AWS SAA
tags:
- aws
- saa
- kms
- 봉투암호화
- cloudhsm
- sse-kms
- acm
- object-lock
- aws-backup
- 보안 아키텍처 설계
series:
- AWS SAA
series_order: 4
---

보안 도메인의 남은 과제는 1.3 '적절한 데이터 보안 통제 결정'이다. 저장할 때와 전송할 때의 암호화, KMS 키를 누가 관리하는지, 실수나 공격으로 데이터가 지워지지 않게 하는 백업과 삭제 방지를 묶었다.

## 요약

- 암호화는 **저장 중(at rest)** 과 **전송 중(in transit)** 으로 나눈다. 전송 중 암호화는 TLS(HTTPS), 저장 중 암호화는 대부분 KMS 키로 한다.
- KMS 키는 AWS 소유 키, AWS 관리형 키, **고객 관리형 키**가 있고, 키 정책과 교체 주기를 직접 통제하려면 고객 관리형 키를 쓴다.
- KMS는 큰 데이터를 직접 암호화하지 않고 **봉투 암호화**를 쓴다. 데이터 키로 데이터를 암호화하고, KMS 키로 데이터 키를 암호화한다.
- 암호화되지 않은 EBS 볼륨과 RDS 인스턴스는 그 자리에서 암호화할 수 없다. 스냅샷을 암호화해 복사한 뒤 새로 만든다.
- 지우거나 고칠 수 없게 보관해야 하면 S3 Object Lock(규정 준수 모드)이나 AWS Backup Vault Lock을 쓴다. 여러 서비스의 백업은 AWS Backup으로 한곳에서 관리한다.

## 1. 저장 중 암호화와 전송 중 암호화

| 구분 | 뜻 | AWS 방법 |
|---|---|---|
| 저장 중(at rest) | 디스크, 버킷, 백업에 저장된 데이터의 암호화 | KMS 키로 S3, EBS, RDS, DynamoDB, EFS 암호화 |
| 전송 중(in transit) | 네트워크로 오가는 데이터의 암호화 | TLS(HTTPS), ACM 인증서, VPN, MACsec |
| 서버 측 암호화 | AWS 서비스가 저장할 때 암호화 | SSE-S3, SSE-KMS 등 |
| 클라이언트 측 암호화 | 애플리케이션이 보내기 전에 직접 암호화. AWS는 암호문만 본다 | AWS Encryption SDK |

## 2. AWS KMS

**AWS KMS(Key Management Service)** 는 암호화 키를 만들고 관리하는 서비스다. 키는 검증된 하드웨어 보안 모듈(HSM) 밖으로 평문으로 나가지 않고, 모든 키 사용은 CloudTrail에 기록된다.

### 키의 종류

| 종류 | 누가 관리 | 키 정책 수정 | 교체 | 예 |
|---|---|---|---|---|
| AWS 소유 키 | AWS가 여러 계정에 걸쳐 관리 | 불가. 계정에서 보이지도 않는다 | AWS가 관리 | DynamoDB 기본 암호화 |
| AWS 관리형 키 | 서비스가 고객 계정에 만든다 | 불가 | 매년 자동 | `aws/s3`, `aws/ebs`, `aws/rds` |
| 고객 관리형 키 | 고객이 만들고 관리 | 가능 | 자동 교체를 켤 수 있다(기본 1년, 90~2,560일에서 선택). 필요할 때 즉시 교체도 가능 | 감사, 접근 통제, 다른 계정과 공유가 필요할 때 |

- **키 정책:** 모든 KMS 키에는 키 정책이 하나 있고, 키 정책이 허용하지 않으면 IAM 정책만으로는 키를 쓸 수 없다. 다른 계정이 키를 쓰게 하려면 키 정책에서 그 계정을 허용하고, 그 계정의 IAM 정책도 허용해야 한다.
- **리전 범위:** KMS 키는 리전에 속한다. 다른 리전에서 같은 키로 복호화해야 하면 **다중 리전 키**를 쓴다.
- **삭제 대기:** 키를 지우면 7~30일(기본 30일) 대기 기간을 거친 뒤 삭제된다. 그 사이 취소할 수 있다. 키가 지워지면 그 키로 암호화한 데이터는 복구할 수 없다.
- **대칭 키와 비대칭 키:** 기본은 대칭 키(AES-256)이고, 서명이나 외부와의 공개 키 암호화가 필요하면 비대칭 키(RSA, ECC)를 쓴다.

### 봉투 암호화

KMS의 `Encrypt` API로 직접 암호화할 수 있는 데이터는 **최대 4KB**이다. 그래서 큰 데이터는 다음과 같이 암호화한다.

{{< mermaid >}}
sequenceDiagram
  participant App as 애플리케이션 (또는 S3, EBS)
  participant KMS as AWS KMS
  App->>KMS: GenerateDataKey(KMS 키 지정)
  KMS-->>App: 평문 데이터 키 + 암호화된 데이터 키
  Note over App: 평문 데이터 키로 데이터 암호화<br/>평문 데이터 키는 메모리에서 지움<br/>암호화된 데이터 키를 데이터 옆에 저장
  App->>KMS: 복호화할 때: Decrypt(암호화된 데이터 키)
  KMS-->>App: 평문 데이터 키
  Note over App: 데이터 복호화
{{< /mermaid >}}

큰 데이터는 데이터 키로 로컬에서 빠르게 암호화하고, KMS는 작은 데이터 키만 다뤄서 빠르고 안전하다. S3, EBS, RDS도 내부적으로 이 방식을 쓴다.

> **쉬운 설명**
>
> 금고 안에 넣을 서류(데이터)를 상자에 넣고 자물쇠(데이터 키)로 잠근다. 그 자물쇠의 열쇠는 다시 은행 대여금고(KMS 키)에 맡기는 열쇠 봉투에 넣어 봉한다. 상자 옆에는 '봉해진 열쇠 봉투'만 붙여 두니, 은행(KMS)이 봉투를 열어 주지 않으면 아무도 상자를 열 수 없다. 은행은 열쇠 봉투 크기의 작은 물건만 다루면 되니 빠르다.

### CloudHSM

| 구분 | AWS KMS | AWS CloudHSM |
|---|---|---|
| 형태 | 여러 고객이 쓰는 관리형 서비스 | 고객 VPC에 배치되는 전용(싱글 테넌트) HSM |
| 키 통제 | AWS가 운영, 고객은 정책으로 통제 | 고객이 HSM 사용자와 키를 독점 관리. AWS는 키에 접근할 수 없다 |
| 연동 | 대부분의 AWS 서비스와 통합 | PKCS#11, JCE, CNG 같은 표준 인터페이스. 오라클 TDE, SSL 오프로드 |
| 쓰는 때 | 일반적인 경우 | 규제상 전용 HSM이나 키의 완전한 독점 통제가 필요할 때 |

KMS의 **사용자 지정 키 스토어**를 쓰면 KMS의 편리함은 유지하면서 키 자료를 CloudHSM 클러스터에 둘 수 있다.

## 3. 서비스별 암호화

### S3

| 방식 | 키 관리 | 특징 |
|---|---|---|
| SSE-S3 | S3가 관리하는 키 | 2023년 1월부터 모든 새 객체에 기본 적용. 추가 비용 없음 |
| SSE-KMS | KMS 키(AWS 관리형 또는 고객 관리형) | 키 정책으로 접근 통제, CloudTrail로 키 사용 감사. 요청마다 KMS를 호출하므로 S3 버킷 키를 켜면 KMS 요청과 비용이 크게 줄어든다 |
| DSSE-KMS | KMS 키로 두 겹 암호화 | 두 겹 암호화를 요구하는 규정 대응 |
| SSE-C | 고객이 요청마다 키를 보낸다 | AWS는 키를 저장하지 않는다. HTTPS 필수 |
| 클라이언트 측 암호화 | 고객이 직접 | S3는 암호문만 받는다 |

HTTPS로만 접근하게 하려면 버킷 정책에 다음처럼 `aws:SecureTransport`가 false인 요청을 거부한다.

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "DenyInsecureTransport",
    "Effect": "Deny",
    "Principal": "*",
    "Action": "s3:*",
    "Resource": ["arn:aws:s3:::example-bucket", "arn:aws:s3:::example-bucket/*"],
    "Condition": { "Bool": { "aws:SecureTransport": "false" } }
  }]
}
```

S3 **퍼블릭 액세스 차단(Block Public Access)** 은 계정이나 버킷 단위로 실수로 인한 공개를 막는다. 새 버킷은 기본으로 켜져 있다.

### EBS와 RDS

| 서비스 | 규칙 |
|---|---|
| EBS | 볼륨을 만들 때 KMS로 암호화한다. 리전마다 '기본 암호화'를 켜면 새 볼륨이 자동으로 암호화된다. 암호화된 볼륨의 스냅샷과, 그 스냅샷으로 만든 볼륨도 암호화된다 |
| RDS, Aurora | 인스턴스(클러스터)를 만들 때 암호화를 켠다. 암호화된 DB의 읽기 전용 복제본, 스냅샷, 백업도 암호화된다. 전송 중에는 TLS 연결을 강제할 수 있다 |
| DynamoDB | 저장 데이터가 항상 암호화된다. 키를 AWS 소유, AWS 관리형, 고객 관리형 가운데 고른다 |
| EFS | 파일 시스템을 만들 때 저장 중 암호화를 켠다. 전송 중 암호화는 TLS 마운트 옵션으로 |

암호화되지 않은 EBS 볼륨이나 RDS 인스턴스를 암호화하려면 다음 순서를 거친다.

{{< mermaid >}}
flowchart LR
  A["암호화 안 된<br>볼륨 · DB"] --> B["스냅샷 생성"]
  B --> C["스냅샷 복사<br>(이때 KMS 키로 암호화)"]
  C --> D["암호화된 스냅샷으로<br>새 볼륨 · DB 생성"]
  D --> E["애플리케이션을<br>새 볼륨 · DB로 전환"]
{{< /mermaid >}}

### 전송 중 암호화와 ACM

**AWS Certificate Manager(ACM)** 는 TLS 인증서를 발급하고 자동으로 갱신한다. ACM이 발급한 퍼블릭 인증서는 ELB, CloudFront, API Gateway 같은 통합 서비스에 붙여 쓰는 것이 기본이다.

- **CloudFront에 쓸 인증서는 반드시 us-east-1(버지니아 북부) 리전의 ACM에서** 요청하거나 가져와야 한다.
- ALB에서 TLS를 끝내면(TLS 종료) 인스턴스는 암호화 처리 부담을 던다. 끝까지 암호화가 필요하면 ALB에서 대상까지 다시 HTTPS로 보낸다.

## 4. 삭제와 변조로부터 데이터 지키기

| 기능 | 설명 |
|---|---|
| S3 버전 관리 | 덮어쓰거나 지워도 이전 버전이 남는다. 지우면 '삭제 마커'가 생길 뿐이다 |
| MFA Delete | 버전을 영구 삭제하거나 버전 관리를 끌 때 MFA를 요구한다. 버킷 소유자의 루트 사용자만 켤 수 있다 |
| S3 Object Lock | 객체를 정해진 기간 동안 지우거나 덮어쓸 수 없게 한다(WORM, 한 번 쓰고 여러 번 읽기). 버전 관리가 필요하다 |
| S3 복제(CRR, SRR) | 다른 리전(CRR) 또는 같은 리전(SRR)의 버킷으로 객체를 비동기 복제. 원본과 대상 모두 버전 관리가 필요하다. 기본으로 설정 이후의 새 객체만 복제되고, 기존 객체는 S3 배치 복제로 옮긴다 |
| AWS Backup | EC2, EBS, RDS, Aurora, DynamoDB, EFS, FSx, S3 등의 백업을 백업 계획으로 한곳에서 자동화. 다른 리전과 다른 계정으로 복사, Organizations로 조직 전체에 적용 |
| Backup Vault Lock | 백업 볼트의 복구 지점을 지우거나 보존 기간을 줄이지 못하게 잠근다 |
| EBS 스냅샷 관리 | Data Lifecycle Manager로 스냅샷 생성과 삭제를 자동화하고, 휴지통(Recycle Bin)으로 실수로 지운 스냅샷을 되살린다 |

### Object Lock의 두 모드

| 모드 | 보존 기간 안에 지울 수 있는 사람 |
|---|---|
| 거버넌스(Governance) 모드 | 특별 권한(`s3:BypassGovernanceRetention`)이 있는 사용자는 지우거나 설정을 바꿀 수 있다 |
| 규정 준수(Compliance) 모드 | 아무도 없다. 루트 사용자도 보존 기간이 끝날 때까지 지우거나 기간을 줄일 수 없다 |

보존 기간과 별개로 **법적 보존(Legal hold)** 을 걸면, 해제할 때까지 기한 없이 지울 수 없다.

> **쉬운 설명**
>
> 버전 관리는 문서를 고칠 때마다 이전 판을 서랍에 남겨 두는 것이고, Object Lock은 문서를 투명 아크릴 상자에 넣고 '2033년까지 개봉 금지' 봉인을 붙이는 것이다. 거버넌스 모드는 관리자 열쇠로 열 수 있는 봉인, 규정 준수 모드는 사장님(루트)도 열 수 없는 봉인이다.

## 5. 규정 준수 지원

| 서비스 | 하는 일 |
|---|---|
| AWS Artifact | AWS의 규정 준수 보고서(SOC, PCI DSS, ISO 인증서)와 계약서를 내려받는다 |
| AWS Config 규칙 | 'EBS가 암호화되어 있는가', 'S3 버킷에 기본 암호화가 있는가' 같은 규칙을 계속 점검 |
| Amazon Macie | S3에서 민감 데이터를 찾아 분류 |
| AWS Audit Manager | 감사 증거를 자동으로 모아 규정 준수 평가를 돕는다 |

## 헷갈렸던 것들

- 키 정책을 직접 통제하고, 키 사용을 감사하고, 교체 주기를 정하려면 **고객 관리형 키**이다. AWS 관리형 키는 정책을 고칠 수 없다.
- KMS 직접 암호화는 4KB까지다. 큰 데이터는 데이터 키를 쓰는 봉투 암호화다.
- 암호화되지 않은 RDS·EBS는 그 자리에서 암호화할 수 없다. 스냅샷 → 암호화 복사 → 복원 순서다.
- SSE-KMS를 쓰는 버킷에 요청이 많아 KMS 요청 한도나 비용이 문제면 **S3 버킷 키**를 켠다.
- CloudFront용 ACM 인증서는 us-east-1에서 만들어야 한다.
- '루트 사용자를 포함해 누구도 기간 안에 지울 수 없다'는 Object Lock **규정 준수 모드**이다. 거버넌스 모드는 특별 권한으로 풀 수 있다.
- S3 복제는 양쪽 버킷 모두 버전 관리가 필요하고, 켜기 전에 있던 객체는 자동으로 복제되지 않는다.
- 여러 서비스와 계정의 백업을 한곳에서 정책으로 관리하려면 AWS Backup이다.
- 전용 HSM과 키의 독점 통제가 필요하면 CloudHSM이다.

## 용어 정리

| 용어 | 뜻 |
|---|---|
| 고객 관리형 키 | 고객이 키 정책, 교체, 삭제를 통제하는 KMS 키 |
| 키 정책 | KMS 키에 붙는 리소스 기반 정책. 키 접근의 출발점 |
| 봉투 암호화 | 데이터 키로 데이터를, KMS 키로 데이터 키를 암호화하는 방식 |
| S3 버킷 키 | SSE-KMS의 KMS 호출을 줄이는 버킷 단위 키 |
| CloudHSM | 고객 전용 하드웨어 보안 모듈 |
| ACM | TLS 인증서 발급과 자동 갱신 서비스 |
| Object Lock | 객체를 기간 동안 지우거나 덮어쓰지 못하게 하는 WORM 기능 |
| AWS Backup | 여러 서비스의 백업을 한곳에서 자동화하는 서비스 |

## 복습 문제

**1.** A company must encrypt the data that it stores in Amazon S3. The company also must audit who used the key and when, and must manage the key policy itself. Which solution meets these requirements?

- A. SSE-KMS with a customer managed KMS key
- B. SSE-S3
- C. SSE-C
- D. No encryption, with a stricter bucket policy

**2.** A production Amazon RDS for PostgreSQL DB instance is not encrypted. How can the company move the data to an encrypted DB instance?

- A. Modify the instance in the console to turn on encryption.
- B. Create an encrypted read replica directly.
- C. Create a snapshot, copy the snapshot with encryption by using a KMS key, and restore a new DB instance from the encrypted copy.
- D. Turn on an encryption option in the parameter group.

**3.** Financial regulations require a company to keep transaction logs for 7 years. During that period, no one, including the root user, can delete or modify the logs. Which configuration meets these requirements?

- A. Turn on S3 Versioning only.
- B. S3 Object Lock in governance mode with a 7-year retention period
- C. S3 Object Lock in compliance mode with a 7-year retention period
- D. Deny s3:DeleteObject in the bucket policy.

**4.** Regulations require a company to generate encryption keys on dedicated hardware that is not shared with other customers. AWS must not be able to access the keys. Which service meets these requirements?

- A. AWS managed KMS keys
- B. AWS Secrets Manager
- C. AWS CloudHSM
- D. SSE-S3

**5.** A security team wants every request to an S3 bucket to use HTTPS. Which solution is MOST appropriate?

- A. Change the bucket's default encryption to SSE-KMS.
- B. Turn on S3 Block Public Access.
- C. Turn on S3 Versioning.
- D. In the bucket policy, deny requests where aws:SecureTransport is false.

**6.** A company must automatically create daily backups of Amazon EBS, Amazon RDS, and Amazon DynamoDB resources in multiple accounts. For disaster recovery, copies must be kept in another Region. Which solution has the LEAST operational overhead?

- A. Create snapshots with an AWS Lambda script in each account.
- B. Back up each service manually from its console every day.
- C. Create an AWS Backup plan with a cross-Region copy rule, and apply it to all accounts with an AWS Organizations backup policy.
- D. Use S3 Lifecycle rules.

## 답과 풀이

1. **A** 고객 관리형 키는 키 정책을 직접 관리하고, 키 사용이 CloudTrail에 기록된다.
2. **C** 기존 인스턴스는 그 자리에서 암호화할 수 없어 스냅샷 암호화 복사 후 복원한다.
3. **C** 규정 준수 모드는 루트 사용자도 보존 기간 안에 지울 수 없다. 버킷 정책은 권한 있는 사용자가 바꿀 수 있다.
4. **C** CloudHSM은 고객 전용 HSM이고 키를 고객이 독점 관리한다.
5. **D** aws:SecureTransport 조건으로 HTTP 요청을 거부한다.
6. **C** AWS Backup은 여러 서비스와 계정의 백업을 계획 하나로 자동화하고 리전 간 복사를 지원한다.

## 참고 자료

- AWS KMS 개발자 안내서, 개념: <https://docs.aws.amazon.com/kms/latest/developerguide/concepts.html>
- AWS KMS 개발자 안내서, 키 교체: <https://docs.aws.amazon.com/kms/latest/developerguide/rotate-keys.html>
- Amazon S3 사용 설명서, 서버 측 암호화로 데이터 보호: <https://docs.aws.amazon.com/AmazonS3/latest/userguide/serv-side-encryption.html>
- Amazon S3 사용 설명서, Object Lock: <https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lock.html>
- AWS Backup 개발자 안내서: <https://docs.aws.amazon.com/aws-backup/latest/devguide/whatisbackup.html>

---
title: '[KCSA] 컴플라이언스와 보안 프레임워크: CIS, NIST, NSA·CISA, STRIDE와 ATT&CK, 공급망 컴플라이언스, 자동화 도구'
date: '2026-10-24T16:00:00+09:00'
categories:
- KCSA
tags:
- kubernetes
- kcsa
- compliance
- cis-benchmark
- nist-800-190
- nsa-cisa
- nist-csf
- stride
- mitre-attack
- slsa
- sbom
- ssdf
- kube-bench
- kubescape
- trivy
- policy-as-code
- Compliance and Security Frameworks
series:
- KCSA
series_order: 8
---

Compliance and Security Frameworks는 10%로 가장 작은 도메인이고 항목은 네 개다. Compliance Frameworks, Threat Modeling Frameworks, Supply Chain Compliance, Automation and Tooling이다. 이름이 비슷한 문서와 도구가 많아서, 무엇이 법이고 무엇이 업계 표준이고 무엇이 설정 점검표인지, 어떤 도구가 어느 기준으로 점검하는지를 표로 갈라 두었다.

## 요약

- CIS Kubernetes Benchmark는 구성 요소별 설정 점검표다. kube-bench가 자동으로 점검한다.
- NIST SP 800-190은 컨테이너 보안 지침, NSA·CISA Kubernetes Hardening Guide는 쿠버네티스 하드닝 지침, NIST CSF는 조직 전체의 보안 프레임워크다.
- GDPR, HIPAA는 법, PCI DSS는 카드 업계 표준, SOC 2와 ISO/IEC 27001은 감사와 인증 체계다. 쿠버네티스를 쓴다고 이것들을 저절로 만족하지는 않는다.
- 위협 모델링 프레임워크는 STRIDE(위협 분류), MITRE ATT&CK과 Microsoft Threat Matrix for Kubernetes(실제 공격 기법), PASTA(위험 중심 절차)가 있다.
- 공급망 컴플라이언스는 SLSA(빌드 무결성 수준), SBOM(SPDX, CycloneDX), NIST SSDF(SP 800-218), OpenSSF Scorecard로 따진다.
- 자동화 도구는 단계별로 다르다. CI에서 매니페스트와 이미지 스캔, 배포할 때 정책 엔진, 운영 중에는 kube-bench와 Kubescape 정기 점검, Falco 탐지, 감사 로그다.

## 1. 컴플라이언스 프레임워크

| 이름 | 종류 | 내용 |
|---|---|---|
| CIS Kubernetes Benchmark | 설정 기준 | 컨트롤 플레인, etcd, 워커 노드, 정책별로 권고 설정을 나열한다. Level 1(기본), Level 2(더 엄격) 프로필이 있다 |
| NIST SP 800-190 | 지침 | Application Container Security Guide. 이미지, 저장소, 오케스트레이터, 컨테이너, 호스트 OS의 위험과 대응 |
| NSA·CISA Kubernetes Hardening Guide | 지침 | 위협 모델, 파드 보안, 네트워크 분리와 하드닝, 인증과 인가, 감사 로그와 위협 탐지, 업그레이드와 애플리케이션 보안. 최신판은 2022년 8월 v1.2 |
| NIST CSF 2.0 | 조직 보안 프레임워크 | Govern, Identify, Protect, Detect, Respond, Recover 여섯 기능 |
| NIST SP 800-53 | 통제 목록 | 미국 연방 정보 시스템의 보안 통제 카탈로그 |
| PCI DSS | 업계 표준 | 카드 데이터를 다루는 시스템의 요구 사항 |
| HIPAA | 법(미국) | 의료 정보 보호 |
| GDPR | 법(EU) | 개인정보 보호 |
| SOC 2 | 감사 보고 | 보안, 가용성 등 신뢰 서비스 기준에 대한 외부 감사 |
| ISO/IEC 27001 | 인증 | 정보보호 관리체계(ISMS) 국제 인증 |
| FedRAMP | 인증(미국) | 연방 정부가 쓰는 클라우드 서비스 인증 |

컴플라이언스는 '기준에 맞췄다는 증거'를 내는 일이다. 쿠버네티스 쪽에서 증거가 되는 것은 RBAC 설정, 감사 로그, 암호화 설정, 정책 엔진의 위반 보고서, 정기 점검 결과다. 그리고 감사를 통과했다고 안전하다는 뜻은 아니다. 기준은 최소한이다.

### NSA·CISA Kubernetes Hardening Guide 원문

PDF 원문(66쪽)을 받아서 목차와 섹션별 권고 요약을 읽었다. 2021년 8월에 1.0, 2022년 3월에 1.1, 2022년 8월에 1.2가 나왔다. 1.2에서는 automountServiceAccountToken 설명과 부록의 ClusterRoleBinding 예시를 고쳤다.

| 섹션 | 권고 요약 |
|---|---|
| 파드 보안 | non-root로 실행, 가능하면 불변(읽기 전용) 파일 시스템, 이미지 취약점과 설정 오류 스캔. privileged, hostPID, hostIPC, hostNetwork, allowedHostPath를 막고 root 실행과 root로의 권한 상승을 거부한다. SELinux, AppArmor, seccomp로 앱을 하드닝한다 |
| 네트워크 분리와 하드닝 | 방화벽과 RBAC로 컨트롤 플레인 접근을 막고 컨트롤 플레인과 노드의 네트워크를 나눈다. etcd 접근을 더 좁히고 저장 암호화, 별도 TLS 인증서를 쓴다. 구성 요소 사이는 TLS로 인증하고 암호화한다. NetworkPolicy로 격리하고 명시적인 거부 정책을 둔다. 자격 증명은 설정 파일이 아니라 암호화한 Secret에 둔다 |
| 인증과 인가 | 익명 로그인을 끈다. 강한 사용자 인증을 쓰고, 사용자, 관리자, 개발자, ServiceAccount, 인프라 팀마다 따로 만든 RBAC 역할을 준다 |
| 감사 로그와 위협 탐지 | 감사 로그를 켠다. 노드나 파드, 컨테이너가 죽어도 남도록 로그를 보존하고 클러스터 밖에 모은다. 환경 전체(API 감사, 메트릭, 앱 로그, seccomp 로그, 저장소 감사 로그)에서 로그를 남기고 모니터링과 알림을 붙인다 |
| 업그레이드와 애플리케이션 보안 | 보안 패치를 바로 적용하고, 취약점 스캔과 침투 테스트를 정기적으로 하고, 안 쓰는 구성 요소는 지운다. CIS Benchmark를 따르라고도 적혀 있다 |

가이드가 기본값을 짚은 곳이 세 군데 있어서 따로 적어 둔다. 익명 로그인은 기본으로 켜져 있고(enabled by default), 감사 로그는 기본으로 꺼져 있고(disabled by default), Secret은 기본으로 암호화되지 않는다. 다른 네임스페이스의 파드와 서비스도 따로 막지 않으면 서로 통신된다는 점도 같이 나온다.

2022년 문서라서 지금과 다른 부분이 있다. Pod Security Admission을 1.23에서 기본으로 켜진 beta 기능으로 소개하고, 부록 C와 D에 PodSecurityPolicy 설명과 예시를 싣고 있다. PSA는 1.25에서 GA가 됐고 PSP는 같은 1.25에서 제거됐다. 그래서 PSP 부록은 어떤 필드를 막아야 하는지 보는 용도로만 읽었다. 컨트롤 플레인 포트 표(6443, 2379-2380, 10250, 10259, 10257)와 워커 노드 포트 표(10250, 30000-32767)는 지금 문서와 같다.

## 2. 위협 모델링 프레임워크

위협 모델링의 큰 틀은 네 가지 질문이다. 무엇을 만들고 있나, 무엇이 잘못될 수 있나, 그래서 무엇을 할까, 잘했나. 시스템을 데이터 흐름도로 그리고 신뢰 경계를 표시한 다음, 요소마다 위협을 찾는다.

| 프레임워크 | 성격 |
|---|---|
| STRIDE | 위협을 여섯 종류로 나눠 빠짐없이 찾게 하는 분류. Microsoft가 만들었다 |
| MITRE ATT&CK(Containers 매트릭스) | 실제 공격에서 관찰된 전술과 기법의 지식 베이스 |
| Microsoft Threat Matrix for Kubernetes | ATT&CK 형식으로 쿠버네티스 공격 기법을 정리한 것 |
| PASTA | 비즈니스 목표에서 시작해 공격을 시뮬레이션하는 7단계 위험 중심 절차 |
| 공격 트리 | 공격 목표를 뿌리에 두고 달성 방법을 가지로 펼친 그림 |

STRIDE를 쿠버네티스에 대 보면 이렇다.

| STRIDE | 위반하는 성질 | 쿠버네티스 예 | 대응 |
|---|---|---|---|
| Spoofing(위장) | 인증 | 훔친 ServiceAccount 토큰으로 다른 앱인 척 | 짧은 수명 토큰, mTLS |
| Tampering(변조) | 무결성 | 저장소의 이미지 바꿔치기, etcd 직접 수정 | 서명 검증, etcd 접근 차단 |
| Repudiation(부인) | 부인 방지 | '내가 지우지 않았다', 증거 없음 | 감사 로그를 밖에 보관 |
| Information disclosure(정보 노출) | 기밀성 | Secret 유출, 메타데이터 자격 증명 | 저장 암호화, RBAC, 이그레스 차단 |
| Denial of service(서비스 거부) | 가용성 | 자원 고갈, API 서버 폭주 | limits, 쿼터, API Priority and Fairness |
| Elevation of privilege(권한 상승) | 인가 | privileged 파드로 노드 장악 | PSS Restricted, RBAC 모범 사례 |

## 3. 공급망 컴플라이언스

| 기준 | 내용 |
|---|---|
| SLSA | 빌드 무결성 수준. L1 출처 증명, L2 호스팅된 빌드 플랫폼의 서명된 출처 증명, L3 강화된 빌드 플랫폼 |
| SBOM | 구성 요소 목록. 형식은 SPDX(Linux Foundation, ISO/IEC 5962)와 CycloneDX(OWASP). 미국 행정명령 14028 이후 정부 납품에 요구되기 시작했다 |
| NTIA SBOM 최소 요소 | 공급자, 구성 요소 이름, 버전, 고유 식별자, 의존 관계, SBOM 작성자, 작성 시각 |
| NIST SSDF(SP 800-218) | 안전한 소프트웨어 개발 프레임워크. 조직 준비(PO), 소프트웨어 보호(PS), 안전한 소프트웨어 생산(PW), 취약점 대응(RV) |
| OpenSSF Scorecard | 오픈소스 저장소의 보안 습관(브랜치 보호, 의존성 고정, 코드 리뷰 등)을 자동으로 점수 매긴다 |
| VEX | 'SBOM에 이 취약 구성 요소가 있지만 이 제품은 영향받지 않는다'를 알리는 형식 |

SBOM은 취약점을 고쳐 주지 않는다. 새 CVE가 나왔을 때 어느 이미지에 그 구성 요소가 들어 있는지 바로 찾게 해 주는 목록이다. 라이선스 확인에도 쓴다.

## 4. 자동화와 도구

{{< mermaid >}}
flowchart LR
  CI["CI<br>매니페스트 정적 검사,<br>이미지 스캔, SBOM, 서명"] --> AD["배포 시점<br>어드미션 정책,<br>서명 검증"]
  AD --> RUN["운영<br>kube-bench, Kubescape 정기 점검,<br>Falco 탐지, 감사 로그"]
  RUN --> REP["보고<br>정책 위반 보고서,<br>대시보드, 감사 증거"]
  REP -.->|"고칠 것"| CI
{{< /mermaid >}}

| 도구 | 하는 일 | 기준 | CNCF |
|---|---|---|---|
| kube-bench | 노드와 컨트롤 플레인 설정을 CIS Benchmark로 점검 | CIS | 아님(Aqua Security) |
| Kubescape | 클러스터, 매니페스트, 이미지를 여러 프레임워크로 점검하고 위험 점수를 낸다 | NSA·CISA, MITRE ATT&CK, CIS 등 | Incubating(2025년 1월) |
| Trivy | 이미지 취약점, 설정 오류, 비밀값, SBOM, 클러스터 스캔 | CVE 데이터베이스, 설정 규칙 | 아님(Aqua Security) |
| Falco | 런타임 이상 행동 탐지 | 규칙(일부는 컴플라이언스 태그가 붙어 있다) | Graduated |
| OPA Gatekeeper, Kyverno | 정책 코드화. 배포를 막고, 이미 있는 리소스의 위반도 감사해 보고한다 | 직접 쓴 정책 | OPA·Kyverno Graduated |
| KubeLinter, Polaris 같은 정적 분석기 | 배포 전 매니페스트 검사 | 모범 사례 규칙 | 아님 |

```bash
kubectl apply -f https://raw.githubusercontent.com/aquasecurity/kube-bench/main/job.yaml   # 노드에서 CIS 점검 Job 실행
kubectl logs job/kube-bench                      # PASS, FAIL, WARN 목록
kubescape scan framework nsa                     # NSA·CISA 기준으로 클러스터 점검
trivy image registry.example.com/shop/api:1.4.2  # 이미지 취약점
trivy config ./manifests                         # 매니페스트 설정 오류
```

도구는 단계마다 역할이 다르다. CI의 검사는 일찍 잡고(shift left), 어드미션은 막고, 정기 점검은 시간이 지나며 생기는 어긋남(드리프트)을 찾고, 런타임 탐지는 실제 공격을 알린다. 어느 하나로 다른 것을 대신하지 않는다.

> **쉬운 설명**
>
> 컴플라이언스는 건물의 법규 준수와 소방 점검이다. 건축법(GDPR, HIPAA)은 지켜야 하는 법이고, 업계 협회 기준(PCI DSS)은 그 업종에서 장사하려면 맞춰야 하는 기준이며, 항목별 점검표(CIS Benchmark)는 소방관이 들고 다니는 체크리스트다. 위협 모델링 프레임워크는 도둑 입장에서 쓰는 질문지라서, STRIDE의 여섯 질문을 하나씩 던지면 빠뜨린 문이 보인다. 공급망 컴플라이언스는 식품의 원산지 표시(SBOM)와 위생 인증(SLSA) 같은 것이다. 자동화 도구는 매일 아침 점검표를 대신 체크해 주는 기계다.

## 헷갈렸던 것들

- kube-bench는 CIS만, Kubescape는 NSA·CISA, MITRE, CIS 등 여러 프레임워크로 점검한다.
- NSA·CISA 가이드가 짚은 기본값: 익명 로그인은 켜져 있고, 감사 로그는 꺼져 있고, Secret은 암호화되지 않는다.
- NSA·CISA 가이드의 PSP 부록은 1.25에서 제거된 기능 이야기다. 지금은 PSA를 쓴다.
- STRIDE의 R은 Repudiation(부인)이고 감사 로그로 막는다.
- GDPR과 HIPAA는 법, PCI DSS는 업계 표준, CIS Benchmark는 설정 기준이다.
- NIST SP 800-190은 컨테이너, SP 800-218은 안전한 개발(SSDF), SP 800-53은 통제 목록이다.
- SBOM은 목록일 뿐 취약점을 고치지 않는다.
- 감사를 통과해도 안전하다는 보장은 없다.
- Trivy와 kube-bench는 CNCF 프로젝트가 아니고, Kubescape는 incubating이다.

## 용어 정리

| 용어 | 뜻 |
|---|---|
| 컴플라이언스 | 법, 표준, 내부 규정을 지키고 그 증거를 내는 일 |
| 벤치마크 | 권고 설정을 항목별로 정리한 점검 기준 |
| STRIDE | 위장, 변조, 부인, 정보 노출, 서비스 거부, 권한 상승의 여섯 위협 분류 |
| PASTA | 위험 중심의 7단계 위협 모델링 절차 |
| SSDF | NIST의 안전한 소프트웨어 개발 프레임워크(SP 800-218) |
| VEX | 제품이 특정 취약점의 영향을 받는지 알리는 형식 |
| 정책 코드화 | 보안과 운영 규칙을 코드로 적어 자동으로 검사하는 방식 |
| shift left | 보안 검사를 개발 흐름의 앞쪽으로 당기는 것 |

## 복습 문제

**1.** Which tool checks a cluster's configuration against the CIS Kubernetes Benchmark?

- A. Falco
- B. cert-manager
- C. kube-bench
- D. Harbor

**2.** In STRIDE, which threat category is mainly addressed by audit logs that prove who performed an action?

- A. Repudiation
- B. Spoofing
- C. Tampering
- D. Elevation of privilege

**3.** Which NIST publication provides security guidance specifically for application containers?

- A. SP 800-53
- B. SP 800-218
- C. SP 800-63
- D. SP 800-190

**4.** Which framework defines levels of build integrity for software artifacts, such as signed provenance from a hosted build platform?

- A. STRIDE
- B. SLSA
- C. PCI DSS
- D. The CIS Benchmark

**5.** Which CNCF incubating project scans clusters and manifests against several frameworks, including the NSA-CISA guidance and MITRE ATT&CK?

- A. kube-bench
- B. Trivy
- C. Kubescape
- D. Polaris

**6.** Which knowledge base describes adversary tactics and techniques observed in real-world attacks, including a matrix for containers?

- A. SBOM
- B. SSDF
- C. SLSA
- D. MITRE ATT&CK

**7.** Which statement about compliance is correct?

- A. Passing a compliance audit does not by itself guarantee that a cluster is secure.
- B. Kubernetes is PCI DSS compliant by default.
- C. CIS Benchmarks are laws.
- D. An SBOM automatically fixes vulnerabilities.

**8.** According to the NSA and CISA Kubernetes Hardening Guide, which of the following is disabled by default and should be enabled?

- A. Anonymous requests to the API server
- B. Audit logging
- C. Communication between Pods in different namespaces
- D. Automatic mounting of ServiceAccount tokens into Pods

## 답과 풀이

1. **C** kube-bench가 CIS Benchmark 항목을 점검한다.
2. **A** 부인 방지는 '누가 했는지 증명'이다. 감사 로그가 그 증거다.
3. **D** SP 800-190이 Application Container Security Guide다. 800-53은 통제 목록, 800-218은 SSDF, 800-63은 디지털 신원 지침이다.
4. **B** SLSA다.
5. **C** Kubescape다. kube-bench와 Trivy는 Aqua Security의 도구이고 CNCF 프로젝트가 아니다.
6. **D** MITRE ATT&CK이다.
7. **A** 기준은 최소한이다. 쿠버네티스가 기본으로 어떤 인증을 만족하지도 않는다.
8. **B** 가이드는 감사 로그가 기본으로 꺼져 있다고 적고 켜라고 권한다. 익명 요청, 다른 네임스페이스 파드 사이의 통신, ServiceAccount 토큰 자동 마운트는 기본으로 허용돼 있어서 오히려 막거나 줄일 대상이다.

## 참고 자료

- CIS Kubernetes Benchmark: <https://www.cisecurity.org/benchmark/kubernetes>
- NIST SP 800-190, Application Container Security Guide: <https://csrc.nist.gov/pubs/sp/800/190/final>
- NSA·CISA, Kubernetes Hardening Guide v1.2(PDF): <https://media.defense.gov/2022/Aug/29/2003066362/-1/-1/0/CTR_KUBERNETES_HARDENING_GUIDANCE_1.2_20220829.PDF>
- NIST Cybersecurity Framework: <https://www.nist.gov/cyberframework>
- NIST SP 800-218, SSDF: <https://csrc.nist.gov/pubs/sp/800/218/final>
- Microsoft, STRIDE 위협 분류: <https://learn.microsoft.com/en-us/azure/security/develop/threat-modeling-tool-threats>
- MITRE ATT&CK, Containers 매트릭스: <https://attack.mitre.org/matrices/enterprise/containers/>
- Microsoft, Threat Matrix for Kubernetes: <https://microsoft.github.io/Threat-Matrix-for-Kubernetes/>
- SLSA: <https://slsa.dev/>
- NTIA, SBOM 최소 요소: <https://www.ntia.gov/report/2021/minimum-elements-software-bill-materials-sbom>
- SPDX: <https://spdx.dev/>
- CycloneDX: <https://cyclonedx.org/>
- OpenSSF Scorecard: <https://securityscorecards.dev/>
- kube-bench: <https://github.com/aquasecurity/kube-bench>
- Kubescape: <https://kubescape.io/>
- Trivy: <https://trivy.dev/>
- OWASP Kubernetes Top Ten: <https://owasp.org/www-project-kubernetes-top-ten/>


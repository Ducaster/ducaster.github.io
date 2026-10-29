---
title: '[KCSA] 모의 문제 30문항: 도메인 비중대로 섞어서'
date: '2026-10-27T21:30:00+09:00'
categories:
- KCSA
tags:
- kubernetes
- kcsa
- security
- 모의문제
- 복습
- 시험 준비
series:
- KCSA
series_order: 9
---

KCSA 범위 42개 항목을 다 정리하고 나서 도메인 비중대로 30문항을 만들었다. 실제 시험(60문항, 90분)의 절반 분량이라 45분을 잡고 푼다. 글마다 붙인 복습 문제와 겹치지 않게 했고, 포트 번호, 설정 이름, 프로젝트 단계처럼 보기에서 바꿔 넣기 쉬운 것들을 일부러 섞었다.

## 문제 구성

| 도메인 | 비중 | 문항 수 |
|---|---:|---:|
| Overview of Cloud Native Security | 14% | 4 |
| Kubernetes Cluster Component Security | 22% | 7 |
| Kubernetes Security Fundamentals | 22% | 7 |
| Kubernetes Threat Model | 16% | 5 |
| Platform Security | 16% | 4 |
| Compliance and Security Frameworks | 10% | 3 |

## 문제

**1.** On which port does the kubelet API listen by default?

- A. 6443
- B. 10250
- C. 2379
- D. 10259

**2.** A Deployment's Pod template violates the Restricted profile, and its namespace has the label `pod-security.kubernetes.io/enforce: restricted`. What happens when the Deployment is applied?

- A. The Deployment is rejected.
- B. The Pods are created with a warning.
- C. The namespace label is removed.
- D. The Deployment is created, but its ReplicaSet cannot create Pods.

**3.** Which mechanism maps root inside a container to an unprivileged user on the host?

- A. User namespaces (`hostUsers: false`)
- B. NetworkPolicy
- C. ResourceQuota
- D. Pod priority

**4.** An attacker writes a manifest file into `/etc/kubernetes/manifests` on a control plane node. Why is this hard to stop with admission policies?

- A. Admission webhooks run only on worker nodes.
- B. The manifest file is encrypted.
- C. The kubelet starts static Pods directly from local files, so admission decisions on the API server do not stop them from running.
- D. Static Pods cannot run privileged containers.

**5.** Which etcd setting ensures that only clients with a certificate signed by the trusted CA can connect?

- A. `--auto-tls=true`
- B. `--listen-client-urls=http://0.0.0.0:2379`
- C. `--client-cert-auth=true`
- D. `--enable-v2=true`

**6.** How should the rules in an audit policy be ordered?

- A. Put the catch-all rule first.
- B. Put specific rules first and the catch-all rule last, because the first matching rule applies.
- C. Rule order does not matter.
- D. An audit policy supports only one rule.

**7.** Which three items answer "who built it", "what is in it", and "how was it built" for a container image?

- A. A tag, a label, and an annotation
- B. A Dockerfile, a README, and a LICENSE file
- C. A digest, a layer, and a manifest
- D. A signature, an SBOM, and a provenance attestation

**8.** Which kubelet setting closes the unauthenticated read-only port?

- A. `readOnlyPort: 0`
- B. `readOnlyPort: 10255`
- C. `authentication.webhook.enabled: false`
- D. `authorization.mode: AlwaysAllow`

**9.** Which RBAC verb lets a subject act as another user, group, or ServiceAccount?

- A. escalate
- B. impersonate
- C. bind
- D. proxy

**10.** A cryptominer in one Pod consumes all CPU on shared nodes. Which threat category does this fall under most directly?

- A. Persistence
- B. Repudiation
- C. Denial of service
- D. Spoofing

**11.** In the 4C model, image scanning and running containers as non-root belong mainly to which layer?

- A. Cloud
- B. Cluster
- C. Code
- D. Container

**12.** A Pod only needs to read ConfigMaps in its own namespace through the API. What is the best approach?

- A. Create a dedicated ServiceAccount, grant it a Role that allows get and list on ConfigMaps, and bind the Role to it.
- B. Use the default ServiceAccount and bind it to cluster-admin.
- C. Mount the admin.conf file into the Pod.
- D. Disable RBAC for that namespace.

**13.** Which statement about the `ipBlock` field in a NetworkPolicy is correct?

- A. It is the recommended way to select Pods.
- B. It matches Service names.
- C. It is meant for IP ranges outside the cluster, and `except` can exclude ranges such as the metadata endpoint.
- D. It works without a CNI plugin that supports NetworkPolicy.

**14.** Which document lists recommended configuration settings for Kubernetes components and is checked by tools such as kube-bench?

- A. STRIDE
- B. The CIS Kubernetes Benchmark
- C. SLSA
- D. The NIST Cybersecurity Framework

**15.** Why should security-critical validating webhooks usually use `failurePolicy: Fail`?

- A. It makes the webhook faster.
- B. It deletes noncompliant objects.
- C. It disables auditing.
- D. It prevents requests from bypassing the policy when the webhook is unavailable.

**16.** Since v1.29, which group does kubeadm use for the certificate in `admin.conf`, so that RBAC still applies?

- A. `kubeadm:cluster-admins`
- B. `system:masters`
- C. `system:nodes`
- D. `system:anonymous`

**17.** A compromised Pod scans the cluster network and connects to an unauthenticated Redis instance in another namespace. Which threat category is this?

- A. Persistence
- B. Denial of service
- C. Attacker on the network, moving laterally
- D. Supply chain compromise

**18.** Which Pod Security Standards profile requires the seccomp profile to be set to RuntimeDefault or Localhost?

- A. Privileged
- B. Restricted
- C. Baseline
- D. All profiles

**19.** On a managed Kubernetes service, which of these is the customer's responsibility?

- A. Backing up the control plane etcd
- B. NetworkPolicies and Pod security settings for workloads
- C. Patching the kube-apiserver
- D. Physical security of the hosts

**20.** Why must Pods be prevented from mounting the container runtime socket?

- A. It leaks DNS queries.
- B. It disables container logging.
- C. It reduces node performance.
- D. It allows creating privileged containers on the node, which is equivalent to root access to the node.

**21.** Which identity format do service meshes such as Istio commonly use for workloads?

- A. UUIDs stored in Pod annotations
- B. Kubernetes node names
- C. SPIFFE IDs such as `spiffe://<trust-domain>/ns/<namespace>/sa/<serviceaccount>`
- D. Pod IP addresses

**22.** Which audit level should be used for Secrets so that their values are not written to the log?

- A. Metadata
- B. Request
- C. RequestResponse
- D. Body

**23.** Which control most directly blocks a container escape through a hostPath mount of the node's root file system?

- A. Increasing the replica count
- B. Using a headless Service
- C. Enabling the HorizontalPodAutoscaler
- D. Enforcing Pod Security Baseline or Restricted, which disallow hostPath volumes

**24.** In STRIDE, which category describes stealing a ServiceAccount token and using it to pretend to be another workload?

- A. Tampering
- B. Repudiation
- C. Spoofing
- D. Denial of service

**25.** Which statement about Kubernetes client certificates is correct?

- A. They can be revoked individually with a certificate revocation list.
- B. They stay valid until they expire, because Kubernetes does not support certificate revocation.
- C. They always expire after one hour.
- D. They are stored in etcd.

**26.** Which runtime runs containers on an application kernel in user space to strengthen isolation?

- A. gVisor
- B. runc
- C. containerd
- D. CRI-O

**27.** Which authentication method is recommended for human users in a production cluster?

- A. A static token file
- B. A shared admin.conf file
- C. OIDC with short-lived tokens from an identity provider
- D. Anonymous access

**28.** Which CNCF graduated project produces attestations showing that each step of a software supply chain was performed as expected?

- A. Harbor
- B. Falco
- C. Notary
- D. in-toto

**29.** Which control best detects an attacker who opens an interactive shell in a running container?

- A. A ResourceQuota
- B. Runtime security detection such as Falco
- C. A PodDisruptionBudget
- D. A default StorageClass

**30.** Which are standard formats for SBOMs?

- A. SPDX and CycloneDX
- B. STRIDE and PASTA
- C. SLSA and SSDF
- D. CIS and NIST CSF

## 답과 풀이

| 번호 | 답 | 도메인 | 풀이 |
|---|---|---|---|
| 1 | B | Cluster Component Security | 6443은 API 서버, 2379는 etcd, 10259는 스케줄러다 |
| 2 | D | Security Fundamentals | enforce는 파드에만 걸린다. 워크로드 리소스는 만들어지고, 파드 생성이 거절된다 |
| 3 | A | Overview | 사용자 네임스페이스다. v1.36에서 GA가 됐다 |
| 4 | C | Threat Model | 스태틱 파드는 kubelet이 파일을 보고 직접 띄운다. 그래서 노드 파일 시스템 접근(hostPath)을 막는 게 중요하다 |
| 5 | C | Cluster Component Security | `--client-cert-auth`와 `--trusted-ca-file`을 같이 쓴다. auto-tls는 자체 서명 인증서라 신원을 보장하지 않는다 |
| 6 | B | Security Fundamentals | 처음 맞는 규칙의 수준을 쓴다 |
| 7 | D | Platform Security | 서명은 누가, SBOM은 무엇이, 출처 증명은 어떻게를 말한다 |
| 8 | A | Cluster Component Security | 10255는 인증 없는 읽기 전용 포트다. 0이면 닫힌다 |
| 9 | B | Security Fundamentals | impersonate가 사칭 권한이다 |
| 10 | C | Threat Model | 다른 워크로드가 쓸 자원을 빼앗는 서비스 거부다. limits와 쿼터로 막는다 |
| 11 | D | Overview | 이미지와 컨테이너 실행 설정은 Container 층이다 |
| 12 | A | Cluster Component Security | 전용 ServiceAccount와 최소 권한 Role이다 |
| 13 | C | Security Fundamentals | 파드 IP는 바뀌어서 ipBlock으로 고르지 않는다. 클러스터 밖 주소용이다 |
| 14 | B | Compliance | CIS Benchmark는 항목별 설정 점검표다 |
| 15 | D | Platform Security | Ignore면 웹훅이 죽었을 때 검사 없이 통과한다 |
| 16 | A | Cluster Component Security | `system:masters`는 RBAC를 우회해서 super-admin.conf에만 쓴다 |
| 17 | C | Threat Model | 평평한 파드 네트워크에서의 측면 이동이다. NetworkPolicy 기본 거부와 내부 서비스 인증으로 막는다 |
| 18 | B | Security Fundamentals | Baseline은 Unconfined만 막고, Restricted가 설정을 요구한다 |
| 19 | B | Overview | 클러스터 안의 정책과 워크로드는 사용자 몫이다 |
| 20 | D | Cluster Component Security | 런타임 소켓은 노드의 마스터키다 |
| 21 | C | Platform Security | SPIFFE ID가 인증서에 들어간다. IP는 바뀌어서 신원이 될 수 없다 |
| 22 | A | Security Fundamentals | Request 이상은 본문을 남긴다. Body라는 수준은 없다 |
| 23 | D | Threat Model | hostPath는 Baseline부터 막힌다 |
| 24 | C | Compliance | 다른 신원인 척하는 위장이다 |
| 25 | B | Cluster Component Security | 그래서 사람에게는 짧은 수명 토큰이나 OIDC가 낫다 |
| 26 | A | Overview | gVisor는 사용자 공간 커널로 시스템 콜을 가로챈다. runc는 일반 저수준 런타임이다 |
| 27 | C | Security Fundamentals | 외부 IdP의 짧은 수명 토큰이다. 그룹도 IdP에서 관리한다 |
| 28 | D | Platform Security | in-toto는 2025년 2월에 graduated가 됐다. Notary는 서명 도구이고 incubating이다 |
| 29 | B | Threat Model | 런타임 탐지가 시스템 콜을 보고 알린다 |
| 30 | A | Compliance | B는 위협 모델링, C는 공급망 무결성과 개발 프레임워크, D는 설정 기준과 조직 프레임워크다 |

## 틀리기 쉬운 짝

- 6443 API 서버, 2379-2380 etcd, 10250 kubelet, 10255 kubelet 읽기 전용(닫는다), 10257 컨트롤러 매니저, 10259 스케줄러
- Node는 인가 모드, NodeRestriction은 어드미션 플러그인. 둘이 같이 kubelet을 자기 노드에 묶는다
- Secret 저장 암호화는 etcd가 아니라 API 서버의 EncryptionConfiguration이 한다
- PSA enforce는 파드에만, warn과 audit는 워크로드 템플릿에도 걸린다
- Baseline은 root 실행을 허용하고, Restricted가 막는다
- 감사 수준 Metadata는 본문 없음, Request는 요청 본문, RequestResponse는 응답 본문까지
- `system:masters`는 RBAC를 우회한다. kubeadm admin.conf는 v1.29부터 `kubeadm:cluster-admins`
- 웹훅 `failurePolicy: Ignore`는 fail open, `Fail`은 fail closed
- 서명은 누가, SBOM은 무엇이, 출처 증명은 어떻게
- kube-bench는 CIS만, Kubescape는 여러 프레임워크
- Falco는 탐지, Gatekeeper와 Kyverno는 막기와 감사

## 참고 자료

- CNCF, KCSA 출제 범위 PDF: <https://github.com/cncf/curriculum/blob/master/KCSA%20Curriculum.pdf>
- Kubernetes 문서, 보안 체크리스트: <https://kubernetes.io/docs/concepts/security/security-checklist/>
- CNCF, Cloud Native Security Whitepaper: <https://www.cncf.io/reports/cloud-native-security-whitepaper/>
- CNCF 클라우드 네이티브 용어집: <https://glossary.cncf.io/>


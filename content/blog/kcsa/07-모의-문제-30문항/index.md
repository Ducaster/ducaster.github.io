---
title: '[KCSA] 복습 문제 30문항'
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

6개 도메인을 다 정리한 뒤, 글마다 붙인 복습 문제와 겹치지 않게 도메인 비중대로 30문항을 만들었다. 시험의 절반 분량이라 45분 안에 푸는 걸 목표로 했다. 60문항짜리는 [실전 모의고사 60문항](../08-실전-모의고사-60문항/)에 따로 모았다.

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

- A. 10259
- B. 10250
- C. 6443
- D. 2379

**2.** A Deployment's Pod template violates the Restricted profile, and its namespace has the label `pod-security.kubernetes.io/enforce: restricted`. What happens when the Deployment is applied?

- A. The namespace label is removed so that the Deployment can run.
- B. The Deployment is created, but its Pods are rejected.
- C. The Pods are created, and the API server returns a warning.
- D. The Deployment is rejected before it is stored.

**3.** Which mechanism maps root inside a container to an unprivileged user on the host?

- A. Seccomp (`seccompProfile: RuntimeDefault`)
- B. NetworkPolicy (`podSelector: {}`)
- C. PriorityClass (`priorityClassName`)
- D. User namespaces (`hostUsers: false`)

**4.** An attacker writes a manifest file into `/etc/kubernetes/manifests` on a control plane node. Why is this hard to stop with admission policies?

- A. The manifest file is encrypted, so admission webhooks cannot read its contents.
- B. Admission webhooks run only on worker nodes, not on control plane nodes.
- C. Static Pods cannot run privileged containers, so admission has nothing to check.
- D. The kubelet runs them from local files, so API server admission cannot stop them.

**5.** Which etcd setting ensures that only clients with a certificate signed by the trusted CA can connect?

- A. `--listen-client-urls=http://0.0.0.0:2379`
- B. `--auto-tls=true`
- C. `--client-cert-auth=true`
- D. `--enable-v2=true`

**6.** How should the rules in an audit policy be ordered?

- A. An audit policy supports only one rule, so ordering is not configurable.
- B. Specific rules first and the catch-all last; the first match wins.
- C. Put the catch-all rule first so that every request is logged at least once.
- D. Order does not matter, because the most detailed matching level always wins.

**7.** Which three items answer "who signed it", "what is in it", and "which builder and process produced it" for a container image?

- A. A signature, an SBOM, and a provenance attestation
- B. A Dockerfile, a README, and a LICENSE file in the repository
- C. A tag, a label, and an annotation
- D. A digest, a layer, and a manifest

**8.** Which kubelet setting closes the unauthenticated read-only port?

- A. `authentication.webhook.enabled: false`
- B. `readOnlyPort: 10255`
- C. `authorization.mode: AlwaysAllow`
- D. `readOnlyPort: 0`

**9.** Which RBAC verb lets a subject act as another user, group, or ServiceAccount?

- A. impersonate
- B. escalate
- C. proxy
- D. bind

**10.** A cryptominer in one Pod consumes all CPU on shared nodes. Which threat category does this fall under most directly?

- A. Spoofing
- B. Denial of service
- C. Repudiation
- D. Persistence

**11.** In the 4C model, image scanning and running containers as non-root belong mainly to which layer?

- A. Cluster
- B. Container
- C. Cloud
- D. Code

**12.** A Pod only needs to read ConfigMaps in its own namespace through the API. What is the best approach?

- A. Use the namespace's default ServiceAccount and bind it to the cluster-admin ClusterRole.
- B. Disable RBAC checks for that namespace with an annotation on the Namespace.
- C. Create a dedicated ServiceAccount bound to a Role with get and list on ConfigMaps.
- D. Mount the control plane's admin.conf into the Pod as a read-only Secret volume.

**13.** Which statement about the `ipBlock` field in a NetworkPolicy is correct?

- A. It is enforced by kube-proxy, so it works without a NetworkPolicy-capable CNI.
- B. It matches Service names and resolves them to ClusterIPs when the policy is applied.
- C. It is meant for cluster-external CIDRs, and `except` can exclude ranges inside them.
- D. It is the recommended way to select Pods, because Pod IPs stay stable.

**14.** Which document lists recommended configuration settings for Kubernetes components and is checked by tools such as kube-bench?

- A. SLSA
- B. STRIDE
- C. The CIS Kubernetes Benchmark
- D. The NIST Cybersecurity Framework

**15.** Why should security-critical validating webhooks usually use `failurePolicy: Fail`?

- A. It lets the API server cache the last decision while the webhook is down.
- B. It disables audit logging for requests that the webhook rejects.
- C. It deletes existing objects that no longer comply with the policy.
- D. Requests cannot skip the policy while the webhook is unavailable.

**16.** Since v1.29, which group does kubeadm use for the certificate in `admin.conf`, so that RBAC still applies?

- A. `system:masters`
- B. `kubeadm:cluster-admins`
- C. `system:anonymous`
- D. `system:nodes`

**17.** A compromised Pod scans the cluster network and connects to an unauthenticated Redis instance in another namespace. Which threat category is this?

- A. Denial of service against the Redis instance
- B. Persistence through a modified container image
- C. Supply chain compromise of the Redis image
- D. Attacker on the network, moving laterally

**18.** Which Pod Security Standards profile requires the seccomp profile to be set to RuntimeDefault or Localhost?

- A. Restricted
- B. Privileged
- C. All profiles
- D. Baseline

**19.** On a managed Kubernetes service, which of these is the customer's responsibility?

- A. Physical security of the data center hosts
- B. Backing up and restoring the control plane etcd
- C. Patching the kube-apiserver and kube-scheduler
- D. Workload NetworkPolicies and Pod security settings

**20.** Why must Pods be prevented from mounting the container runtime socket?

- A. It lets the Pod start privileged containers, which equals node root.
- B. It disables container logging for every other Pod on that node.
- C. It exposes the DNS queries of other Pods on the node.
- D. It slows the node, because the runtime must serialize every image pull.

**21.** Which identity format do service meshes such as Istio commonly use for workloads?

- A. SPIFFE IDs such as `spiffe://<trust-domain>/ns/<ns>/sa/<sa>`
- B. Pod IP addresses recorded in the mesh control plane's endpoint registry
- C. Kubernetes node names combined with the container ID
- D. UUIDs that the sidecar injector stores in Pod annotations

**22.** Which audit level should be used for Secrets so that their values are not written to the log?

- A. Body
- B. Request
- C. RequestResponse
- D. Metadata

**23.** Which control most directly blocks a container escape through a hostPath mount of the node's root file system?

- A. Enabling the HorizontalPodAutoscaler so the Pod is replaced quickly
- B. Increasing the replica count so one escape does not take down the app
- C. Enforcing Pod Security Baseline, which disallows hostPath volumes
- D. Using a headless Service so the Pod has no ClusterIP

**24.** In STRIDE, which category describes stealing a ServiceAccount token and using it to pretend to be another workload?

- A. Spoofing
- B. Denial of service
- C. Tampering
- D. Repudiation

**25.** Which statement about Kubernetes client certificates is correct?

- A. They always expire after one hour, so a leaked certificate is short-lived.
- B. They stay valid until expiry; Kubernetes has no certificate revocation.
- C. They can be revoked individually by publishing a certificate revocation list.
- D. They are stored in etcd, so an administrator can delete one to revoke it.

**26.** Which runtime runs containers on an application kernel in user space to strengthen isolation?

- A. containerd
- B. gVisor
- C. runc
- D. CRI-O

**27.** Which authentication method is recommended for human users in a production cluster?

- A. OIDC with short-lived tokens from an IdP
- B. A static token file distributed to each engineer
- C. A shared admin.conf file stored in a password manager
- D. Anonymous access restricted by NetworkPolicy

**28.** Which CNCF graduated project produces attestations showing that each step of a software supply chain was performed as expected?

- A. Notary
- B. Harbor
- C. in-toto
- D. Falco

**29.** Which control best detects an attacker who opens an interactive shell in a running container?

- A. A ResourceQuota on the number of Pods
- B. A PodDisruptionBudget covering the workload's Pods
- C. Runtime security detection such as Falco
- D. A default StorageClass with encryption

**30.** Which are standard formats for SBOMs?

- A. SPDX and CycloneDX
- B. SLSA and SSDF
- C. STRIDE and PASTA
- D. CIS and NIST CSF

## 답과 풀이

<details>
<summary>정답과 해설 펼치기</summary>

| 번호 | 답 | 도메인 | 풀이 |
|---|---|---|---|
| 1 | B | Cluster Component Security | 6443은 API 서버, 2379는 etcd, 10259는 스케줄러다 |
| 2 | B | Security Fundamentals | enforce는 파드에만 걸린다. 워크로드 리소스는 만들어지고, 파드 생성이 거절된다 |
| 3 | D | Overview | 사용자 네임스페이스다. v1.36에서 GA가 됐다 |
| 4 | D | Threat Model | 스태틱 파드는 kubelet이 파일을 보고 직접 띄운다. 그래서 노드 파일 시스템 접근(hostPath)을 막는 게 중요하다 |
| 5 | C | Cluster Component Security | `--client-cert-auth`와 `--trusted-ca-file`을 같이 쓴다. auto-tls는 자체 서명 인증서라 신원을 보장하지 않는다 |
| 6 | B | Security Fundamentals | 처음 맞는 규칙의 수준을 쓴다 |
| 7 | A | Platform Security | 서명은 서명자와 무결성, SBOM은 구성 요소, 출처 증명은 빌드 시스템과 과정을 보여 준다 |
| 8 | D | Cluster Component Security | 10255는 인증 없는 읽기 전용 포트다. 0이면 닫힌다 |
| 9 | A | Security Fundamentals | impersonate가 사칭 권한이다 |
| 10 | B | Threat Model | 다른 워크로드가 쓸 자원을 빼앗는 서비스 거부다. limits와 쿼터로 막는다 |
| 11 | B | Overview | 이미지와 컨테이너 실행 설정은 Container 층이다 |
| 12 | C | Cluster Component Security | 전용 ServiceAccount와 최소 권한 Role이다 |
| 13 | C | Security Fundamentals | 파드 IP는 바뀌어서 ipBlock으로 고르지 않는다. 클러스터 밖 주소용이다 |
| 14 | C | Compliance | CIS Benchmark는 항목별 설정 점검표다 |
| 15 | D | Platform Security | Ignore면 웹훅이 죽었을 때 검사 없이 통과한다 |
| 16 | B | Cluster Component Security | `system:masters`는 RBAC를 우회해서 super-admin.conf에만 쓴다 |
| 17 | D | Threat Model | 평평한 파드 네트워크에서의 측면 이동이다. NetworkPolicy 기본 거부와 내부 서비스 인증으로 막는다 |
| 18 | A | Security Fundamentals | Baseline은 Unconfined만 막고, Restricted가 설정을 요구한다 |
| 19 | D | Overview | 클러스터 안의 정책과 워크로드는 사용자 몫이다 |
| 20 | A | Cluster Component Security | 런타임 소켓은 노드의 마스터키다 |
| 21 | A | Platform Security | SPIFFE ID가 인증서에 들어간다. IP는 바뀌어서 신원이 될 수 없다 |
| 22 | D | Security Fundamentals | `Request`는 요청 본문, `RequestResponse`는 응답 본문까지 남길 수 있다. Body라는 수준은 없다 |
| 23 | C | Threat Model | hostPath는 Baseline부터 막힌다 |
| 24 | A | Compliance | 다른 신원인 척하는 위장이다 |
| 25 | B | Cluster Component Security | 그래서 사람에게는 짧은 수명 토큰이나 OIDC가 낫다 |
| 26 | B | Overview | gVisor는 사용자 공간 커널로 시스템 콜을 가로챈다. runc는 일반 저수준 런타임이다 |
| 27 | A | Security Fundamentals | 외부 IdP의 짧은 수명 토큰이다. 그룹도 IdP에서 관리한다 |
| 28 | C | Platform Security | in-toto는 2025년 2월에 graduated가 됐다. Notary는 서명 도구이고 incubating이다 |
| 29 | C | Threat Model | 런타임 탐지가 시스템 콜을 보고 알린다 |
| 30 | A | Compliance | SPDX와 CycloneDX는 SBOM 형식이다. SLSA와 SSDF는 공급망과 안전한 개발을 위한 프레임워크다 |

</details>

## 틀리기 쉬운 짝

- 6443 API 서버, 2379-2380 etcd, 10250 kubelet, 10255 kubelet 읽기 전용(닫는다), 10257 컨트롤러 매니저, 10259 스케줄러
- Node는 인가 모드, NodeRestriction은 어드미션 플러그인. 둘이 같이 kubelet을 자기 노드에 묶는다
- Secret 저장 암호화는 etcd가 아니라 API 서버의 EncryptionConfiguration이 한다
- PSA enforce는 파드에만, warn과 audit는 워크로드 템플릿에도 걸린다
- Baseline은 root 실행을 허용하고, Restricted가 막는다
- 감사 수준 Metadata는 본문 없음, Request는 요청 본문, RequestResponse는 응답 본문까지
- `system:masters`는 RBAC를 우회한다. kubeadm admin.conf는 v1.29부터 `kubeadm:cluster-admins`
- 웹훅 `failurePolicy: Ignore`는 fail open, `Fail`은 fail closed
- 서명은 서명자와 무결성, SBOM은 구성 요소, 출처 증명은 빌드 시스템과 과정
- kube-bench는 CIS만, Kubescape는 여러 프레임워크
- Falco는 탐지, Gatekeeper와 Kyverno는 막기와 감사

## 참고 자료

- CNCF, KCSA 출제 범위 PDF: <https://github.com/cncf/curriculum/blob/master/KCSA%20Curriculum.pdf>
- Kubernetes 문서, 보안 체크리스트: <https://kubernetes.io/docs/concepts/security/security-checklist/>
- CNCF, Cloud Native Security Whitepaper: <https://www.cncf.io/reports/cloud-native-security-whitepaper/>
- CNCF 클라우드 네이티브 용어집: <https://glossary.cncf.io/>


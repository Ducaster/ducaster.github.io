---
title: '[KCSA] 클라우드 네이티브 보안 개요: 4C와 심층 방어, 인프라 보안, 통제, 격리, 이미지와 워크로드 보안'
date: '2026-10-06T21:40:00+09:00'
categories:
- KCSA
tags:
- kubernetes
- kcsa
- 4c
- defense-in-depth
- shared-responsibility
- cloud-security
- isolation
- seccomp
- apparmor
- user-namespaces
- image-security
- workload-security
- Overview of Cloud Native Security
series:
- KCSA
series_order: 2
---

Overview of Cloud Native Security(14%)의 여섯 항목을 한 글에 묶었다. 4C, 클라우드·인프라 보안, 통제와 프레임워크, 격리 기법, 아티팩트 저장소와 이미지 보안, 워크로드와 앱 코드 보안이다. 뒤 도메인에서 깊게 볼 내용의 지도 같은 범위라, 층마다 무엇을 지키는지와 용어를 먼저 잡았다.

## 요약

- 4C는 Cloud, Cluster, Container, Code다. 층마다 통제를 겹쳐 두어서 하나가 뚫려도 다음 층이 막게 하는 게 심층 방어다.
- 관리형 쿠버네티스에서는 컨트롤 플레인과 etcd 운영을 제공자가 맡고, RBAC, 네트워크 정책, 워크로드 설정, 이미지는 사용자가 맡는다(공동 책임 모델).
- 인프라 쪽은 API 서버 엔드포인트를 숨기고, 노드 포트를 막고, 노드 OS를 최소화하고, 클라우드 메타데이터 서비스와 노드 IAM 권한을 좁힌다.
- 통제는 예방(막기), 탐지(알아채기), 교정(되돌리기)으로 나뉜다.
- 격리 수준은 네임스페이스(약함)부터 전용 노드, 샌드박스 런타임, 사용자 네임스페이스, 별도 클러스터(강함)까지 단계가 있다.
- 이미지는 신뢰할 수 있는 저장소에서, 작은 베이스로, 스캔하고 서명해서, 다이제스트로 고정해 쓴다.
- 워크로드는 최소 권한 securityContext로 돌리고, 코드는 의존성과 비밀값을 관리한다.

## 1. 4C와 심층 방어

| 층 | 위협의 예 | 통제의 예 |
|---|---|---|
| Cloud(인프라) | 공개된 API 서버, 열린 노드 포트, 과한 클라우드 IAM 권한, 패치 안 된 노드 OS | 사설 엔드포인트, 방화벽과 보안 그룹, 최소 권한 IAM, 노드 이미지 패치 |
| Cluster | 익명 접근, 과한 RBAC, 암호화되지 않은 etcd, 막힘 없는 파드 간 통신 | 인증과 RBAC, 어드미션 정책, Secret 저장 암호화, NetworkPolicy, 감사 로그 |
| Container | 취약한 이미지, root 실행, privileged 컨테이너, 탈출 | 스캔과 서명, securityContext, seccomp, 샌드박스 런타임 |
| Code | 취약한 의존성, 코드 안의 비밀값, 입력 검증 누락 | 의존성 스캔, 비밀값 외부화, 서비스 간 TLS, 정적·동적 분석 |

안쪽 층은 바깥 층을 믿고 있다. 노드가 장악되면 그 위 컨테이너 설정이 아무리 좋아도 의미가 약해진다. 그래서 한 층에 기대지 않고 모든 층에 통제를 둔다.

CNCF Cloud Native Security Whitepaper는 같은 내용을 수명 주기로 나눈다. 개발(Develop), 배포 준비(Distribute), 배포(Deploy), 운영(Runtime)이다.

{{< mermaid >}}
flowchart LR
  D["개발<br>코드 리뷰, 의존성 스캔,<br>IaC와 매니페스트 검사"] --> S["배포 준비<br>이미지 빌드, 스캔, 서명,<br>SBOM, 저장소"]
  S --> P["배포<br>서명 검증, 어드미션 정책,<br>설정 검사"]
  P --> R["운영<br>RBAC, NetworkPolicy,<br>런타임 탐지, 감사 로그"]
{{< /mermaid >}}

## 2. 클라우드와 인프라 보안

| 영역 | 관리형(EKS, GKE, AKS) | 직접 설치(kubeadm) |
|---|---|---|
| 컨트롤 플레인, etcd 운영과 패치 | 제공자 | 사용자 |
| 노드 OS 패치 | 사용자(관리형 노드 그룹이면 일부 제공자) | 사용자 |
| RBAC, 어드미션 정책, NetworkPolicy | 사용자 | 사용자 |
| 이미지, 워크로드 설정, 비밀값 | 사용자 | 사용자 |

관리형이라도 클러스터 안의 권한과 워크로드는 내 책임이다. 인프라 쪽에서 챙길 것은 이렇다.

- **API 서버 엔드포인트**: 인터넷에 열지 않거나 허용 IP를 좁힌다.
- **포트**: 노드 사이에서도 필요한 포트만 연다.

| 포트 | 구성 요소 |
|---|---|
| 6443 | kube-apiserver |
| 2379-2380 | etcd(클라이언트, 피어) |
| 10250 | kubelet API |
| 10257 | kube-controller-manager |
| 10259 | kube-scheduler |
| 10256 | kube-proxy 상태 확인 |
| 30000-32767 | NodePort 서비스 기본 범위 |

- **노드 OS**: 컨테이너 실행에 필요한 것만 든 최소 OS를 쓰고, 노드에 SSH로 들어갈 일을 줄인다.
- **클라우드 메타데이터 서비스**: 파드가 `169.254.169.254`에 접근해 노드의 클라우드 자격 증명을 가져갈 수 있다. NetworkPolicy로 막거나 IMDSv2 같은 보호를 켠다.
- **클라우드 IAM**: 노드 역할에는 최소 권한만 주고, 파드마다 필요한 클라우드 권한은 워크로드 아이덴티티(파드의 ServiceAccount를 클라우드 IAM 역할에 연결)로 따로 준다.
- **디스크와 백업**: 노드 디스크와 etcd 백업을 암호화한다.

## 3. 통제와 프레임워크

| 통제 종류 | 하는 일 | 예 |
|---|---|---|
| 예방(Preventive) | 나쁜 일이 생기지 않게 막는다 | RBAC, Pod Security Admission, NetworkPolicy, 어드미션 정책, 서명 검증 |
| 탐지(Detective) | 생긴 일을 알아챈다 | 감사 로그, Falco 같은 런타임 탐지, 취약점 스캔, 설정 점검 |
| 교정(Corrective) | 생긴 일을 되돌리거나 복구한다 | 패치, 파드 교체, 자격 증명 폐기, 백업 복구, GitOps 셀프 힐 |

어떤 통제를 어떤 기준으로 둘지는 프레임워크를 따른다. CIS Kubernetes Benchmark, NIST SP 800-190, NSA·CISA Kubernetes Hardening Guide 같은 것들이고, 컴플라이언스 도메인에서 따로 정리한다.

## 4. 격리 기법

| 기법 | 격리 수준 | 메모 |
|---|---|---|
| 네임스페이스 + RBAC + ResourceQuota | 약함(논리적) | 이름, 권한, 자원을 나눈다. 같은 노드와 커널을 같이 써서 그 자체로는 보안 경계가 약하다 |
| NetworkPolicy | 네트워크 | 네임스페이스나 파드 사이 트래픽을 막는다 |
| 전용 노드(테인트, 어피니티) | 중간 | 민감한 워크로드를 다른 노드에서만 돌린다. 커널을 같이 쓰는 이웃이 줄어든다 |
| seccomp, AppArmor, SELinux, capabilities | 프로세스 | 시스템 콜, 파일과 자원 접근, root 권한 일부를 제한한다 |
| 사용자 네임스페이스(`hostUsers: false`) | 프로세스 | 컨테이너 안의 root가 호스트에서는 권한 없는 사용자다. v1.36에서 GA |
| 샌드박스 런타임(gVisor, Kata Containers) | 강함 | 커널 호출을 가로채거나 가벼운 VM으로 커널을 나눈다 |
| 별도 클러스터 | 가장 강함 | 컨트롤 플레인까지 나눈다. 운영 비용이 든다 |

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: isolated
spec:
  hostUsers: false              # 사용자 네임스페이스
  runtimeClassName: gvisor      # 샌드박스 런타임
  securityContext:
    seccompProfile:
      type: RuntimeDefault      # 런타임 기본 seccomp 프로필
    appArmorProfile:
      type: RuntimeDefault
  containers:
  - name: api
    image: registry.example.com/shop/api:1.4.2
    securityContext:
      allowPrivilegeEscalation: false
      capabilities:
        drop: ["ALL"]
```

리눅스 보안 기능은 막는 대상이 다르다.

| 기능 | 막는 것 |
|---|---|
| seccomp | 프로세스가 부를 수 있는 시스템 콜 |
| AppArmor, SELinux | 파일, 네트워크, 자원 접근(강제 접근 통제). 프로필이나 라벨로 정한다 |
| capabilities | root 권한을 쪼갠 것. `NET_ADMIN`, `SYS_ADMIN` 같은 것을 빼거나 더한다 |

멀티 테넌시 문서는 서로 믿는 팀끼리 나눠 쓰는 소프트 멀티 테넌시와, 서로 믿지 않는 고객끼리 나눠 쓰는 하드 멀티 테넌시를 구분한다. 하드 멀티 테넌시에는 네임스페이스만으로 부족하고 샌드박스 런타임이나 별도 클러스터가 필요하다.

## 5. 아티팩트 저장소와 이미지 보안

| 대상 | 할 일 |
|---|---|
| 저장소 | 사설 저장소를 쓰고 접근 권한을 나눈다. 올릴 때 스캔하고, 태그를 덮어쓰지 못하게(immutable) 한다. Harbor(CNCF graduated)가 이런 기능을 가진 저장소다 |
| 이미지 내용 | distroless처럼 작은 베이스, 비밀값 넣지 않기, root가 아닌 사용자 |
| 무결성 | 서명(Sigstore cosign, Notary)하고 배포할 때 어드미션에서 서명을 검증한다 |
| 고정 | 태그 대신 다이제스트로 참조한다 |
| 투명성 | SBOM(이미지에 든 패키지 목록)을 만들어 둔다 |

멀티 테넌트 클러스터에서는 AlwaysPullImages 어드미션 플러그인을 켜기도 한다. 노드에 이미 받아 둔 사설 이미지를, 인증 정보가 없는 다른 테넌트의 파드가 그냥 쓰는 걸 막는다. 이미지 스캔은 알려진 취약점(CVE)만 찾는다는 한계도 기억해 둔다.

## 6. 워크로드와 애플리케이션 코드 보안

| 대상 | 할 일 |
|---|---|
| 워크로드 | root가 아닌 사용자, 권한 상승 금지, capabilities 모두 제거, 읽기 전용 루트 파일 시스템, 자원 limits, 필요 없으면 ServiceAccount 토큰 자동 마운트 끄기 |
| 비밀값 | 코드와 이미지에 넣지 않는다. Secret이나 외부 비밀 저장소를 파일로 받는다 |
| 의존성 | 의존성 취약점 스캔(SCA), 버전 고정, 신뢰할 수 있는 출처 |
| 코드 | 정적 분석(SAST), 동적 분석(DAST), 저장소의 비밀값 스캔, 입력 검증 |
| 통신 | 서비스 간에도 TLS. 서비스 메시의 mTLS를 쓸 수 있다 |

> **쉬운 설명**
>
> 4C는 성을 지키는 방식과 같다. 해자(Cloud), 성벽(Cluster), 건물 문(Container), 금고(Code)가 겹겹이 있다. 해자가 말라도 성벽이 막고, 성벽을 넘어도 문이 잠겨 있다. 이게 심층 방어다. 격리는 같은 건물의 다른 사무실(네임스페이스)과 아예 다른 건물(별도 클러스터)의 차이다. 같은 건물이면 벽이 얇고 환기구(커널)를 같이 쓴다.

## 헷갈렸던 것들

- 네임스페이스는 그 자체로는 약한 보안 경계다. 커널을 같이 쓴다.
- 관리형 쿠버네티스라도 RBAC와 워크로드 보안은 사용자 책임이다.
- 감사 로그와 런타임 탐지는 탐지 통제다. 막지는 못한다.
- seccomp는 시스템 콜, AppArmor와 SELinux는 파일·자원 접근, capabilities는 root 권한 조각이다.
- 이미지 스캔은 알려진 취약점만 찾는다.
- 4C는 바깥부터 Cloud, Cluster, Container, Code 순서다.

## 용어 정리

| 용어 | 뜻 |
|---|---|
| 심층 방어 | 독립된 통제를 여러 층에 겹쳐 하나가 뚫려도 버티게 하는 방식 |
| 공동 책임 모델 | 클라우드 제공자와 사용자가 보안 책임을 나누는 방식 |
| 메타데이터 서비스 | 클라우드 인스턴스가 자기 정보와 자격 증명을 받는 내부 엔드포인트 |
| 워크로드 아이덴티티 | 파드의 ServiceAccount를 클라우드 IAM 역할에 연결하는 방식 |
| seccomp | 프로세스가 부를 수 있는 시스템 콜을 제한하는 리눅스 기능 |
| 사용자 네임스페이스 | 컨테이너 안의 사용자 ID를 호스트의 다른 ID로 매핑하는 리눅스 기능 |
| SBOM | 소프트웨어를 이루는 구성 요소 목록 |

## 복습 문제

**1.** Which approach layers several independent security controls so that the failure of one control does not expose the whole system?

- A. Least privilege
- B. Defense in depth
- C. Zero trust
- D. Security through obscurity

**2.** On a managed Kubernetes service, which task is usually the customer's responsibility?

- A. Patching the etcd servers
- B. Operating the kube-apiserver
- C. Physical security of the data center
- D. RBAC configuration and the security settings of workloads

**3.** Which Linux feature restricts the system calls that a container process can make?

- A. seccomp
- B. cgroups
- C. User namespaces
- D. Mount namespaces

**4.** Which option provides the strongest isolation between tenants that do not trust each other?

- A. Separate namespaces
- B. NetworkPolicies between namespaces
- C. Separate clusters
- D. Separate ServiceAccounts

**5.** Which of the following is a detective control?

- A. A default-deny NetworkPolicy
- B. Runtime threat detection with Falco
- C. Pod Security Admission in enforce mode
- D. Dropping all Linux capabilities

**6.** Why should container images be referenced by digest instead of by tag?

- A. A digest always identifies the same image content.
- B. Digests make images smaller.
- C. Digests encrypt the image.
- D. containerd does not support tags.

**7.** Pods on cloud nodes can reach the instance metadata endpoint `169.254.169.254` and obtain the node's cloud credentials. Which mitigation helps?

- A. Increase the CPU limits of the Pods.
- B. Use a headless Service.
- C. Add PodDisruptionBudgets.
- D. Block egress to the metadata endpoint with NetworkPolicy and limit the IAM permissions of the node role.

## 답과 풀이

1. **B** 심층 방어다. 최소 권한은 권한을 좁히는 원칙이고, 제로 트러스트는 위치를 믿지 않고 매번 검증하는 원칙이다.
2. **D** 컨트롤 플레인과 etcd, 데이터 센터는 제공자 몫이다.
3. **A** seccomp가 시스템 콜을 거른다. cgroup은 자원 양을 제한한다.
4. **C** 별도 클러스터는 컨트롤 플레인과 노드까지 나눈다.
5. **B** Falco는 이상 행동을 찾아 알린다. 나머지는 막는 예방 통제다.
6. **A** 다이제스트는 내용의 해시다. 태그는 다른 이미지를 가리키도록 바뀔 수 있다.
7. **D** 메타데이터 엔드포인트 접근을 막고, 노드 역할 권한을 좁히고, 파드에는 워크로드 아이덴티티로 따로 권한을 준다.

## 참고 자료

- CNCF, KCSA 출제 범위 PDF: <https://github.com/cncf/curriculum/blob/master/KCSA%20Curriculum.pdf>
- CNCF, Cloud Native Security Whitepaper: <https://www.cncf.io/reports/cloud-native-security-whitepaper/>
- Kubernetes 문서, 클라우드 네이티브 보안과 쿠버네티스: <https://kubernetes.io/docs/concepts/security/cloud-native-security/>
- Kubernetes 문서, 보안 체크리스트: <https://kubernetes.io/docs/concepts/security/security-checklist/>
- Kubernetes 문서, 포트와 프로토콜: <https://kubernetes.io/docs/reference/networking/ports-and-protocols/>
- Kubernetes 문서, 멀티 테넌시: <https://kubernetes.io/docs/concepts/security/multi-tenancy/>
- Kubernetes 문서, 리눅스 커널 보안 제약: <https://kubernetes.io/docs/concepts/security/linux-kernel-security-constraints/>
- Kubernetes 문서, 사용자 네임스페이스: <https://kubernetes.io/docs/concepts/workloads/pods/user-namespaces/>
- Kubernetes 문서, RuntimeClass: <https://kubernetes.io/docs/concepts/containers/runtime-class/>
- Harbor: <https://goharbor.io/>
- Sigstore: <https://www.sigstore.dev/>


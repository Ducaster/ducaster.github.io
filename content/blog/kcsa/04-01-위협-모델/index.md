---
title: '[KCSA] 쿠버네티스 위협 모델: 신뢰 경계, 지속성, 서비스 거부, 컨테이너 안의 악성 코드, 네트워크 공격자, 민감 데이터, 권한 상승'
date: '2026-10-18T15:40:00+09:00'
categories:
- KCSA
tags:
- kubernetes
- kcsa
- threat-model
- trust-boundary
- persistence
- denial-of-service
- container-escape
- lateral-movement
- privilege-escalation
- mitre-attack
- falco
- Kubernetes Threat Model
series:
- KCSA
series_order: 6
---

Kubernetes Threat Model(16%)의 일곱 항목은 모두 '공격자가 무엇을 하나'의 관점이다. 앞에서 정리한 설정들이 어떤 공격을 막는지 거꾸로 이어 보는 범위라서, 항목마다 공격 예, 쿠버네티스에서 생기는 모양, 막는 법을 같은 틀로 적었다. 분류는 MITRE ATT&CK Containers 매트릭스와 Microsoft Threat Matrix for Kubernetes를 같이 봤다.

## 요약

- 신뢰 경계는 권한이나 신뢰 수준이 바뀌는 선이다. 인터넷과 클러스터, 파드와 노드, 워크로드와 컨트롤 플레인, 클러스터와 외부(저장소, CI/CD, 클라우드 API) 사이에 있다. 경계를 넘는 흐름마다 인증, 인가, 암호화를 확인한다.
- 지속성은 재시작이나 파드 삭제 뒤에도 접근을 유지하는 것이다. 백도어 DaemonSet, CronJob, 스태틱 파드, 변경 어드미션 웹훅, 새 RBAC 바인딩, 기한 없는 토큰이 예다.
- 서비스 거부는 CPU, 메모리, PID, 디스크, API 서버, etcd를 고갈시킨다. limits, 쿼터, PID 제한, API Priority and Fairness로 막는다.
- 컨테이너 안의 악성 코드는 취약한 앱이나 악성 이미지로 들어와서, ServiceAccount 토큰으로 API를 부르거나 컨테이너 탈출을 노린다.
- 네트워크 위의 공격자는 평평한 파드 네트워크에서 엿듣고 옆으로 옮겨 간다. NetworkPolicy 기본 거부와 mTLS로 막는다.
- 민감 데이터는 Secret, 환경 변수, 로그, etcd 백업, 노드 디스크, 클라우드 메타데이터에서 샌다.
- 권한 상승은 RBAC 상승, 컨테이너에서 노드로, 노드에서 클러스터로 이어진다.

## 1. 신뢰 경계와 데이터 흐름

{{< mermaid >}}
flowchart TB
  U["사용자, 인터넷"] -->|"HTTPS"| LB["로드 밸런서, 인그레스"]
  subgraph cluster["클러스터"]
    subgraph wl["워크로드 경계: 네임스페이스와 파드"]
      P1["앱 파드"] --> P2["DB 파드"]
    end
    subgraph nb["노드 경계"]
      KL["kubelet, 컨테이너 런타임"]
    end
    subgraph cpb["컨트롤 플레인 경계"]
      API["kube-apiserver"] --> ETCD[("etcd")]
    end
  end
  LB --> P1
  ADM["관리자 kubectl"] -->|"인증, RBAC"| API
  CI["CI/CD"] -->|"배포 자격 증명"| API
  REG[("이미지 저장소")] -->|"이미지"| KL
  P1 -.->|"ServiceAccount 토큰"| API
  KL <-->|"TLS"| API
  P1 -.->|"메타데이터 엔드포인트"| CLOUD["클라우드 API"]
{{< /mermaid >}}

위협 모델링은 이런 그림을 그려 놓고, 경계를 넘는 화살표마다 질문한다. 누가 무엇으로 인증하나, 그 요청은 인가되나, 넘어가는 데이터는 암호화되나, 넘어가는 게 무엇인가(이미지, 토큰, 자격 증명). 점선이 공격자가 자주 쓰는 길이다. 파드 안에서 ServiceAccount 토큰으로 API 서버에 닿고, 메타데이터 엔드포인트로 클라우드 자격 증명에 닿는다. CI/CD도 경계다. 배포 자격 증명이 털리면 클러스터에 무엇이든 올릴 수 있다.

## 2. 공격이 이어지는 경로

{{< mermaid >}}
flowchart TB
  A["취약한 앱, 악성 이미지<br>(초기 접근)"] --> B["컨테이너 안 코드 실행"]
  B -->|"마운트된 ServiceAccount 토큰<br>막기: 토큰 자동 마운트 끄기, 최소 RBAC"| C["API 서버 호출"]
  B -->|"privileged, hostPath, 커널 취약점<br>막기: PSS Restricted, seccomp, 샌드박스"| D["노드 장악"]
  D -->|"kubelet 자격 증명, 다른 파드의 Secret<br>막기: Node 인가, NodeRestriction"| E["클러스터 권한 확대"]
  C -->|"pods create, bind, escalate<br>막기: RBAC 모범 사례"| E
  E -->|"DaemonSet, 웹훅, RBAC 바인딩<br>탐지: 감사 로그 알림"| F["지속성"]
{{< /mermaid >}}

MITRE ATT&CK Containers 매트릭스의 전술 이름과 KCSA 항목을 맞춰 보면 이렇다.

| ATT&CK 전술 | KCSA 항목 |
|---|---|
| 초기 접근, 실행 | 컨테이너 안의 악성 코드와 털린 앱 |
| 지속성 | Persistence |
| 권한 상승, 방어 회피 | Privilege Escalation |
| 자격 증명 접근, 수집 | Access to Sensitive Data |
| 탐색, 측면 이동 | Attacker on the Network |
| 영향(Impact) | Denial of Service, 크립토마이닝 |

## 3. 지속성

| 공격 | 쿠버네티스에서의 모양 | 막는 법, 찾는 법 |
|---|---|---|
| 컨트롤러로 되살아나는 백도어 | 악성 컨테이너가 든 DaemonSet, CronJob, Deployment. 파드를 지워도 다시 생긴다 | 워크로드 생성 권한 최소화, 감사 로그 알림, GitOps 드리프트 감지 |
| 스태틱 파드 | 노드의 `/etc/kubernetes/manifests`에 매니페스트를 쓴다. API 서버를 거치지 않는다 | hostPath 금지, 노드 파일 무결성 감시 |
| 변경 어드미션 웹훅 | 새로 만들어지는 모든 파드에 악성 사이드카를 넣는 웹훅 등록 | 웹훅 설정 수정 권한 최소화, 감사 로그 알림 |
| 자격 증명 심기 | 기한 없는 ServiceAccount 토큰 Secret 생성, CSR 승인으로 인증서 발급, 새 ClusterRoleBinding | RBAC로 막고, 감사 로그로 RBAC 변경과 CSR 승인을 감시 |
| 이미지 백도어 | 저장소의 이미지를 바꿔치기 | 서명 검증, 다이제스트 고정 |
| 노드 직접 변경 | hostPath로 노드의 cron, systemd 수정 | PSS Baseline 이상, 읽기 전용 노드 OS |

## 4. 서비스 거부

| 공격 | 대응 |
|---|---|
| 컨테이너가 CPU, 메모리를 다 씀 | requests와 limits, LimitRange 기본값, ResourceQuota |
| 포크 폭탄(프로세스를 끝없이 만듦) | 파드 PID 제한(kubelet `podPidsLimit`), 노드 PID 예약 |
| 로그와 임시 파일로 노드 디스크를 채움 | `ephemeral-storage` requests와 limits, 로그 로테이션, 축출 기준 |
| API 서버에 요청 폭주 | API Priority and Fairness, 인증된 클라이언트별 제한 |
| 오브젝트를 마구 만들어 etcd를 키움 | ResourceQuota의 오브젝트 개수 제한(`count/configmaps` 등) |
| 높은 우선순위로 남의 파드를 밀어냄 | ResourceQuota의 scopeSelector로 PriorityClass 사용 제한 |
| 외부 트래픽 폭주 | 인그레스와 로드 밸런서의 요청 제한, 오토스케일링, PodDisruptionBudget |

## 5. 컨테이너 안의 악성 코드와 털린 애플리케이션

들어오는 길은 세 가지다. 앱 취약점으로 원격 코드 실행, 악성 이미지(이름이 비슷한 가짜 이미지, 채굴기가 든 이미지), 공급망에서 오염된 의존성이다. 일단 컨테이너 안에서 코드가 돌면 공격자가 노리는 것은 정해져 있다.

- 마운트된 ServiceAccount 토큰(`/var/run/secrets/kubernetes.io/serviceaccount/token`)으로 API 서버 호출
- 컨테이너 탈출: privileged, hostPath, hostPID, 위험한 capabilities, 커널이나 런타임 취약점(예: cgroup release_agent를 이용한 CVE-2022-0492)
- 크립토마이닝으로 자원 도용
- 다른 서비스로 옮겨 가기

막는 법은 앞에서 정리한 것들이 모인다. 셸과 도구가 없는 작은 이미지, 읽기 전용 루트 파일 시스템, root가 아닌 사용자, capabilities 모두 제거, seccomp RuntimeDefault, 토큰 자동 마운트 끄기, 이그레스 NetworkPolicy, 이미지 스캔과 서명 검증이다. 그래도 뚫렸을 때 알아채는 건 런타임 탐지다. Falco(CNCF graduated)는 시스템 콜을 보고 '컨테이너 안에서 셸이 떴다', '`/etc` 아래에 파일을 썼다', '예상 밖의 외부 연결'처럼 규칙에 맞는 행동을 알린다.

## 6. 네트워크 위의 공격자

| 공격 | 대응 |
|---|---|
| 암호화되지 않은 파드 트래픽 엿보기, 중간자 공격 | 서비스 메시 mTLS, CNI 암호화(WireGuard, IPsec) |
| 평평한 네트워크에서 측면 이동 | NetworkPolicy 기본 거부, 네임스페이스 분리 |
| 인증 없는 내부 서비스(DB, 캐시) 접근 | 내부 서비스에도 인증, NetworkPolicy |
| 파드에서 kubelet(10250), etcd(2379), API 서버로 직접 접근 | 컨트롤 플레인 포트를 파드 대역에서 막고, kubelet 익명 인증 끄기 |
| 패킷 위조(`NET_RAW` capability) | capabilities 모두 제거 |
| DNS로 내부 서비스 목록 파악 | 이그레스 제한, 필요한 서비스만 노출 |

## 7. 민감 데이터 접근

| 새는 곳 | 대응 |
|---|---|
| Secret을 읽을 수 있는 RBAC(get, list, watch) | 최소 권한, 감사 로그 |
| 환경 변수로 넣은 값 | 볼륨 파일 마운트, ConfigMap에 비밀값 넣지 않기 |
| 애플리케이션 로그, 크래시 덤프 | 로그에 비밀값 출력 금지, 로그 접근 권한 |
| etcd와 etcd 백업 | 저장 암호화, 백업 암호화, etcd 접근 차단 |
| 노드 디스크(kubelet이 마운트한 볼륨) | 노드 접근 통제, 노드 탈출 방지 |
| 클라우드 메타데이터 엔드포인트 | NetworkPolicy로 `169.254.169.254` 차단, IMDSv2, 노드 IAM 최소화 |
| 이미지 레이어, Git 기록 | 비밀값을 넣지 않고 스캔 |

## 8. 권한 상승

| 단계 | 경로 | 대응 |
|---|---|---|
| 클러스터 안(RBAC) | 높은 권한 ServiceAccount로 파드 만들기, `bind`, `escalate`, `impersonate`, 토큰 발급 | RBAC 모범 사례, 감사 |
| 컨테이너에서 노드로 | privileged, `hostPID` + nsenter, hostPath `/`, `SYS_ADMIN`, 런타임 소켓, 커널 취약점 | PSS Restricted, 사용자 네임스페이스, 샌드박스 런타임 |
| 노드에서 클러스터로 | kubelet 자격 증명, 그 노드 파드들의 ServiceAccount 토큰과 Secret, 노드의 클라우드 자격 증명 | Node 인가와 NodeRestriction, 민감한 워크로드 전용 노드 |

권한 상승 방지에는 `allowPrivilegeEscalation: false`도 있다. 이 설정은 컨테이너 안 프로세스가 setuid 바이너리 등으로 부모보다 높은 권한을 얻지 못하게 한다(커널의 no_new_privs). 컨테이너가 privileged이거나 `CAP_SYS_ADMIN`을 가지면 항상 권한 상승이 허용된 것으로 본다.

> **쉬운 설명**
>
> 위협 모델은 도둑의 동선을 미리 그려 보는 일이다. 도둑은 대개 허술한 창문(취약한 앱)으로 들어와서, 집 안에 걸린 열쇠 꾸러미(ServiceAccount 토큰)를 찾고, 벽을 뚫어 옆집(노드)으로 넘어가고, 관리실 마스터키(클러스터 관리자 권한)를 노린다. 그리고 다시 들어올 수 있게 몰래 문을 하나 더 달아 둔다(지속성). 방어는 그 동선의 길목마다 문을 잠그고(예방), CCTV를 다는(탐지) 것이다.

## 헷갈렸던 것들

- 신뢰 경계는 '권한이나 신뢰 수준이 바뀌는 선'이다. 같은 파드 안의 컨테이너 사이는 경계가 아니다.
- 지속성의 예는 DaemonSet, CronJob, 스태틱 파드, 웹훅, RBAC 바인딩, 기한 없는 토큰이다.
- 포크 폭탄은 CPU limits로는 못 막고 PID 제한이 필요하다.
- 스태틱 파드는 API 서버를 거치지 않아서 어드미션 정책이 걸리지 않는다.
- Falco는 탐지 도구다. 막지는 않는다.
- privileged 컨테이너는 `allowPrivilegeEscalation: false`를 줘도 권한 상승이 허용된 것으로 본다.

## 용어 정리

| 용어 | 뜻 |
|---|---|
| 위협 모델링 | 시스템을 그려 놓고 공격자가 무엇을 노리고 어디로 들어올지 찾는 작업 |
| 신뢰 경계 | 권한이나 신뢰 수준이 바뀌는 지점 |
| 지속성 | 재시작이나 삭제 뒤에도 접근을 유지하는 공격 단계 |
| 측면 이동 | 장악한 곳에서 같은 망의 다른 시스템으로 옮겨 가는 것 |
| 컨테이너 탈출 | 컨테이너 격리를 깨고 호스트에 접근하는 것 |
| 포크 폭탄 | 프로세스를 끝없이 만들어 시스템을 멈추게 하는 공격 |
| MITRE ATT&CK | 실제 공격 전술과 기법을 정리한 지식 베이스 |

## 복습 문제

**1.** An attacker registers a mutating admission webhook that injects a malicious sidecar into every new Pod. Which threat category does this represent?

- A. Persistence
- B. Denial of service
- C. Attacker on the network
- D. Access to sensitive data

**2.** Which control best limits the impact of a fork bomb inside a container?

- A. A NetworkPolicy
- B. Pod Security Admission in warn mode
- C. A dedicated ServiceAccount
- D. A Pod PID limit together with container resource limits

**3.** An attacker controls a container in a Pod that sets `hostPID: true` and `privileged: true`. What can the attacker most likely do?

- A. Nothing beyond the container
- B. Access processes on the node and escape to the host
- C. Only read ConfigMaps in the namespace
- D. Only change the Pod's labels

**4.** Traffic between Pods on different nodes is not encrypted. Which mitigation helps against an attacker who can sniff the node network?

- A. A ResourceQuota
- B. Pod Security Admission
- C. Mutual TLS from a service mesh, or CNI encryption such as WireGuard
- D. A higher replica count

**5.** Which of the following is a trust boundary in a Kubernetes cluster?

- A. Between two containers in the same Pod
- B. Between two replicas of the same Deployment
- C. Between labels and annotations
- D. Between workloads in the Pod network and the control plane API

**6.** A compromised Pod on a cloud node can reach `169.254.169.254`. Which threat does this mainly create?

- A. Access to sensitive data, such as the node's cloud credentials
- B. Denial of service against etcd
- C. Persistence through static Pods
- D. Tampering with container images

**7.** Which tool detects suspicious runtime behavior, such as a shell started inside a container?

- A. kube-bench
- B. Trivy
- C. Falco
- D. Helm

**8.** A user can create Pods in a namespace that contains a ServiceAccount bound to cluster-admin. What is the main risk?

- A. Denial of service
- B. Privilege escalation by running a Pod as that ServiceAccount
- C. Sniffing network traffic
- D. Tampering with images

## 답과 풀이

1. **A** 새 파드마다 백도어를 심어 접근을 유지하는 지속성이다.
2. **D** 포크 폭탄은 프로세스 수를 늘린다. PID 제한이 필요하다.
3. **B** 노드의 프로세스를 보고, privileged 권한으로 nsenter 등을 써서 호스트로 넘어갈 수 있다.
4. **C** 전송 구간을 암호화한다.
5. **D** 워크로드와 컨트롤 플레인 사이는 신뢰 수준이 바뀌는 경계다. 같은 파드의 컨테이너는 네트워크와 볼륨을 같이 쓰는 한 단위다.
6. **A** 메타데이터 엔드포인트에서 노드의 클라우드 자격 증명을 가져갈 수 있다.
7. **C** Falco는 런타임 탐지 도구다. kube-bench는 CIS 설정 점검, Trivy는 취약점과 설정 스캐너다.
8. **B** 파드를 만들 수 있으면 그 네임스페이스의 아무 ServiceAccount로나 돌릴 수 있다.

## 참고 자료

- MITRE ATT&CK, Containers 매트릭스: <https://attack.mitre.org/matrices/enterprise/containers/>
- Microsoft, Threat Matrix for Kubernetes: <https://microsoft.github.io/Threat-Matrix-for-Kubernetes/>
- Kubernetes 문서, 보안 체크리스트: <https://kubernetes.io/docs/concepts/security/security-checklist/>
- Kubernetes 문서, RBAC 모범 사례: <https://kubernetes.io/docs/concepts/security/rbac-good-practices/>
- Kubernetes 문서, API 서버 우회 위험: <https://kubernetes.io/docs/concepts/security/api-server-bypass-risks/>
- Kubernetes 문서, 프로세스 ID 제한: <https://kubernetes.io/docs/concepts/policy/pid-limiting/>
- Kubernetes 문서, 리소스 쿼터: <https://kubernetes.io/docs/concepts/policy/resource-quotas/>
- Kubernetes 문서, API Priority and Fairness: <https://kubernetes.io/docs/concepts/cluster-administration/flow-control/>
- Kubernetes 문서, 보안 컨텍스트: <https://kubernetes.io/docs/tasks/configure-pod-container/security-context/>
- CNCF, Cloud Native Security Whitepaper: <https://www.cncf.io/reports/cloud-native-security-whitepaper/>
- Falco: <https://falco.org/>


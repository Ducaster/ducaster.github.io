---
title: '[KCNA] 복습 문제 30문항'
date: '2026-09-26T15:00:00+09:00'
categories:
- KCNA
tags:
- kubernetes
- kcna
- 모의문제
- 복습
- 시험 준비
series:
- KCNA
series_order: 13
---

13개 항목을 다 정리한 뒤, 글마다 붙인 복습 문제와 겹치지 않게 도메인 비중대로 30문항을 만들었다. 시험의 절반 분량이라 45분 안에 푸는 걸 목표로 했다. 60문항짜리는 [실전 모의고사 60문항](../06-실전-모의고사-60문항/)에 따로 모았다.

## 문제 구성

| 도메인 | 비중 | 문항 수 |
|---|---:|---:|
| Kubernetes Fundamentals | 44% | 13 |
| Container Orchestration | 28% | 9 |
| Cloud Native Application Delivery | 16% | 5 |
| Cloud Native Architecture | 12% | 3 |

## 문제

**1.** Which component stores the cluster state, including every API object?

- A. etcd
- B. kubelet
- C. kube-proxy
- D. kube-scheduler

**2.** A Pod using the default ClusterFirst DNS configuration in namespace `web` must reach the Service `db` in namespace `data`. Which short name works from that Pod?

- A. `db.web.svc`
- B. `data.db`
- C. `db`
- D. `db.data`

**3.** Which statement about kube-proxy is correct?

- A. It schedules Pods onto nodes based on Service load.
- B. It assigns IP addresses to Pods when they start on a node.
- C. It resolves Service names to ClusterIPs for Pods on its node.
- D. It maintains node rules that route Service traffic to Pods.

**4.** All manifests are stored in Git. Someone changes the replica count of a Deployment with `kubectl scale`. Argo CD has automated sync and self-heal enabled. What happens?

- A. Argo CD commits the new replica count back to Git.
- B. Argo CD deletes the Deployment.
- C. The change stays until someone syncs manually.
- D. Argo CD restores the replica count from Git.

**5.** The containers in a Pod set CPU and memory requests but no limits. Which QoS class does the Pod get?

- A. Guaranteed
- B. Restricted
- C. Burstable
- D. BestEffort

**6.** Which statement about NetworkPolicy is true?

- A. NetworkPolicies select nodes, and every Pod on the node inherits them.
- B. A NetworkPolicy can explicitly deny specific traffic.
- C. NetworkPolicies are enforced by kube-proxy on each node.
- D. They take effect only if the CNI plugin supports them.

**7.** `kubectl get pods` returns Pods from the wrong cluster. What should you check first?

- A. The kube-scheduler configuration
- B. The current context in your kubeconfig
- C. The CoreDNS ConfigMap
- D. The taints on the nodes

**8.** Which CNCF graduated project provides vendor-neutral APIs, SDKs, and a Collector to generate and export traces, metrics, and logs?

- A. Jaeger
- B. Thanos
- C. OpenTelemetry
- D. Fluentd

**9.** Which object keeps a minimum number of replicas available during voluntary disruptions such as node drains?

- A. ResourceQuota
- B. PriorityClass
- C. PodDisruptionBudget
- D. LimitRange

**10.** A PersistentVolumeClaim requests the ReadWriteMany access mode. Which storage can most likely satisfy it?

- A. An emptyDir volume
- B. A shared file system such as NFS
- C. A single cloud block disk such as Amazon EBS
- D. A hostPath volume

**11.** Which Helm command shows the rendered manifests without installing anything?

- A. `helm template`
- B. `helm rollback`
- C. `helm repo update`
- D. `helm history`

**12.** Which statement about container images is correct?

- A. Images can be built only with Docker, because OCI defines Docker's format.
- B. An image contains its own kernel, which the container boots at start.
- C. An image has read-only layers; a container adds a writable one.
- D. A tag always refers to the same image content.

**13.** Which Pod Security Admission mode rejects Pods that violate the selected profile?

- A. warn
- B. dry-run
- C. audit
- D. enforce

**14.** Which mechanism lets you add a new API type such as `Database` and manage it with kubectl?

- A. A CustomResourceDefinition
- B. An ExternalName Service
- C. An annotation
- D. A ConfigMap

**15.** A Deployment rollout is stuck. Only one new replica is available, and the new Pods are in ImagePullBackOff. What is the fastest way to return to the previous working version?

- A. `kubectl rollout undo deployment/<name>`
- B. `kubectl scale deployment/<name> --replicas=0`
- C. `kubectl delete deployment/<name>`
- D. `kubectl rollout restart deployment/<name>`

**16.** A node has the taint `node-role.kubernetes.io/control-plane:NoSchedule`. Which Pods can be scheduled on it?

- A. No Pods, not even DaemonSet Pods
- B. All Pods
- C. Pods with a matching toleration
- D. Only Pods that have a nodeSelector

**17.** A Pod is Running with zero restarts but shows READY 0/1. Its labels match the Service selector, but the Service sends no traffic to it. What is the most likely reason?

- A. The readiness probe fails.
- B. The image tag is wrong.
- C. The node is NotReady.
- D. The liveness probe fails, and the container keeps restarting.

**18.** The kube-apiserver runs v1.37. Which kubectl version is within the supported version skew?

- A. v1.33
- B. v1.39
- C. v1.36
- D. v1.34

**19.** Which autoscaler adjusts the CPU and memory requests of Pods based on their historical usage?

- A. KEDA
- B. Cluster Autoscaler
- C. VerticalPodAutoscaler
- D. HorizontalPodAutoscaler

**20.** Which component translates Service names into IP addresses inside the cluster?

- A. etcd
- B. CoreDNS
- C. kubelet
- D. kube-proxy

**21.** Which workload resource gives each Pod a stable identity such as `web-0` and its own PersistentVolumeClaim?

- A. StatefulSet
- B. ReplicaSet
- C. Deployment
- D. DaemonSet

**22.** Which of the following is one of the OpenGitOps principles?

- A. Every deployment must be approved manually.
- B. Changes are pushed from the CI system to the cluster.
- C. The desired state is stored only in the cluster.
- D. The desired state is versioned and immutable.

**23.** Which Gateway API resource defines listeners, ports, and TLS settings and is usually managed by cluster operators?

- A. Gateway
- B. ReferenceGrant
- C. HTTPRoute
- D. GatewayClass

**24.** Which component starts static Pods from manifest files on a node?

- A. kube-apiserver
- B. kubelet
- C. kube-scheduler
- D. kube-controller-manager

**25.** A container exits with code 1 right after it starts, and the Pod alternates between Error and CrashLoopBackOff. Where are you most likely to find the cause?

- A. In the scheduler's FailedScheduling events
- B. In the previous container's logs
- C. In the Pod object stored in etcd
- D. In the kernel log of the node that ran it

**26.** Which interface does Kubernetes use to attach networking to Pods?

- A. CRI
- B. OCI
- C. CSI
- D. CNI

**27.** Which deployment strategy runs two complete environments and switches all traffic from the old one to the new one at once?

- A. Rolling update
- B. Blue/green
- C. Canary
- D. Recreate

**28.** In the Kubernetes contributor ladder, which role can approve code changes for the files it is responsible for?

- A. Reviewer
- B. Approver
- C. Member
- D. Non-member contributor

**29.** Which statement about Kubernetes Secrets is correct?

- A. Anyone who can create Pods in a namespace can mount and read its Secrets.
- B. Each Secret is limited to 1 KiB, so large certificates go in ConfigMaps.
- C. They cannot be mounted as files and are exposed only as environment variables.
- D. They are always encrypted in etcd with a key managed by the API server.

**30.** Which object sets default CPU and memory requests for containers in a namespace that do not specify them?

- A. PriorityClass
- B. LimitRange
- C. ResourceQuota
- D. HorizontalPodAutoscaler

## 답과 풀이

<details>
<summary>정답과 해설 펼치기</summary>

| 번호 | 답 | 도메인 | 풀이 |
|---|---|---|---|
| 1 | A | Kubernetes Fundamentals | 모든 오브젝트는 etcd에 저장되고, etcd를 직접 읽고 쓰는 건 API 서버뿐이다 |
| 2 | D | Container Orchestration | 검색 도메인에 `svc.cluster.local`이 있어서 `<서비스>.<네임스페이스>`면 된다. `db`만 쓰면 자기 네임스페이스(web)에서 찾는다 |
| 3 | D | Kubernetes Fundamentals | 파드 IP는 CNI, 배치는 스케줄러, 이름 풀이는 CoreDNS다 |
| 4 | D | Application Delivery | GitOps에서는 Git이 기준이다. 셀프 힐이 켜져 있으면 드리프트를 Git 상태로 되돌린다 |
| 5 | C | Kubernetes Fundamentals | requests가 있지만 limits와 같지 않으니 Burstable이다. Restricted는 Pod Security 단계 이름이다 |
| 6 | D | Container Orchestration | NetworkPolicy는 허용 규칙만 있고, 실제로 막는 건 CNI 플러그인이다 |
| 7 | B | Kubernetes Fundamentals | 어느 클러스터에 누구로 붙을지는 kubeconfig의 현재 컨텍스트가 정한다 |
| 8 | C | Cloud Native Architecture | OpenTelemetry는 2026년 5월 graduated다. Jaeger는 트레이스 백엔드, Fluentd는 로그 수집, Thanos는 incubating인 Prometheus 장기 저장소다 |
| 9 | C | Kubernetes Fundamentals | PDB는 Eviction API를 사용하는 drain에서 중단 가능한 파드 수를 제한한다. 노드 장애나 파드 직접 삭제는 막지 못한다 |
| 10 | B | Container Orchestration | NFS처럼 여러 노드에서 동시에 읽고 쓰는 모드를 지원하는 볼륨이 필요하다. 일반적인 클라우드 블록 디스크는 RWO로 쓴다 |
| 11 | A | Application Delivery | `helm template`은 렌더링만 한다. 차트 오류를 찾을 때 쓴다 |
| 12 | C | Kubernetes Fundamentals | 태그는 바뀔 수 있고, 컨테이너는 호스트 커널을 쓴다. Buildah, Podman으로도 OCI 이미지를 만든다 |
| 13 | D | Container Orchestration | enforce만 거절한다. warn은 경고, audit는 감사 로그 기록이다 |
| 14 | A | Kubernetes Fundamentals | CRD로 새 종류를 등록한다. 동작은 그걸 맡는 컨트롤러(오퍼레이터)가 만든다 |
| 15 | A | Application Delivery | undo가 바로 전 ReplicaSet으로 되돌린다. restart는 같은 잘못된 이미지로 다시 띄울 뿐이다 |
| 16 | C | Kubernetes Fundamentals | 톨러레이션이 있는 파드만 들어간다. 컨트롤 플레인에 뜨는 DaemonSet 파드도 톨러레이션으로 들어간다 |
| 17 | A | Container Orchestration | readiness에 실패하면 엔드포인트에서 빠진다. liveness 실패라면 재시작 횟수가 늘고, 이미지 오류라면 Running이 될 수 없다 |
| 18 | C | Kubernetes Fundamentals | kubectl은 API 서버 위아래 한 마이너, 즉 v1.36에서 v1.38까지다 |
| 19 | C | Cloud Native Architecture | VPA는 파드 크기, HPA와 KEDA는 파드 수, Cluster Autoscaler는 노드 수다 |
| 20 | B | Container Orchestration | 이름 풀이는 CoreDNS, 서비스 IP에서 파드로 보내는 규칙은 kube-proxy다 |
| 21 | A | Kubernetes Fundamentals | StatefulSet은 순서 있는 이름과 volumeClaimTemplates로 파드마다 PVC를 준다 |
| 22 | D | Application Delivery | 네 원칙은 선언적, 버전 관리되고 바뀌지 않음, 자동으로 끌어옴, 계속 조정이다 |
| 23 | A | Container Orchestration | Gateway가 리스너를 정한다. GatewayClass는 구현 종류, HTTPRoute는 앱 개발자의 라우팅 규칙이다 |
| 24 | B | Kubernetes Fundamentals | 스태틱 파드는 API 서버와 스케줄러를 거치지 않고 kubelet이 파일을 보고 띄운다 |
| 25 | B | Container Orchestration | 앱이 오류로 끝난 것이라 `kubectl logs --previous`에 이유가 남는다 |
| 26 | D | Kubernetes Fundamentals | CNI가 네트워크, CRI가 런타임, CSI가 스토리지다. OCI는 컨테이너 표준이다 |
| 27 | B | Application Delivery | 블루/그린은 두 벌을 다 띄우고 한 번에 넘긴다. 카나리는 조금씩 늘린다 |
| 28 | B | Cloud Native Architecture | reviewer는 리뷰하고, approver가 승인한다. 그 위가 subproject owner다 |
| 29 | A | Container Orchestration | 저장 암호화는 따로 설정해야 하고, 크기 한도는 1MiB다. 파드 생성 권한이 사실상 Secret 읽기 권한이 될 수 있다는 점이 함정이다 |
| 30 | B | Kubernetes Fundamentals | LimitRange의 defaultRequest와 default가 기본값을 넣는다. ResourceQuota는 네임스페이스 총량이다 |

</details>

## 틀리기 쉬운 짝

- 노드를 정하는 건 스케줄러, 컨테이너를 띄우는 건 kubelet
- 서비스 이름 풀이는 CoreDNS, 서비스 트래픽 규칙은 kube-proxy, 파드 IP는 CNI
- 자리 계산은 requests, 실행 중 상한은 limits
- 톨러레이션은 허락, 노드로 끌어당기는 건 어피니티와 nodeSelector
- readiness 실패는 트래픽에서 빠짐, liveness 실패는 재시작
- ResourceQuota는 네임스페이스 총량, LimitRange는 컨테이너 하나의 기본값과 범위
- RWO는 노드 하나, RWOP는 파드 하나
- PSA의 enforce만 거절하고 warn, audit는 통과시킨다
- HPA는 파드 수, VPA는 파드 크기, Cluster Autoscaler는 노드 수
- CNCF 성숙도는 Sandbox, Incubating, Graduated. 쿠버네티스 기능 단계는 alpha, beta, stable

## 참고 자료

- CNCF, KCNA 출제 범위 PDF: <https://github.com/cncf/curriculum/blob/master/KCNA_Curriculum.pdf>
- Linux Foundation, KCNA 범위 변경 안내: <https://training.linuxfoundation.org/kcna-program-changes/>
- CNCF 클라우드 네이티브 용어집: <https://glossary.cncf.io/>
- Kubernetes 문서, 용어집: <https://kubernetes.io/docs/reference/glossary/>


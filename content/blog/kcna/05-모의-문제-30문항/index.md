---
title: '[KCNA] 모의 문제 30문항: 도메인 비중대로 섞어서'
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

출제 범위 13개 항목을 다 정리하고 나서, 정리한 내용을 섞어 도메인 비중대로 30문항을 만들었다. 실제 시험(60문항, 90분)의 절반 분량이라 45분을 잡고 푼다. 글마다 붙인 복습 문제와 겹치지 않게, 비슷한 것끼리 헷갈리게 만드는 보기를 일부러 많이 넣었다.

## 문제 구성

| 도메인 | 비중 | 문항 수 |
|---|---:|---:|
| Kubernetes Fundamentals | 44% | 13 |
| Container Orchestration | 28% | 9 |
| Cloud Native Application Delivery | 16% | 5 |
| Cloud Native Architecture | 12% | 3 |

## 문제

**1.** Which component stores the cluster state, including every API object?

- A. kube-scheduler
- B. kubelet
- C. etcd
- D. kube-proxy

**2.** A Pod in the namespace `web` must reach the Service `db` in the namespace `data`. Which short name works from that Pod?

- A. `db.data`
- B. `db`
- C. `data.db`
- D. `db.web.svc`

**3.** Which statement about kube-proxy is correct?

- A. It assigns IP addresses to Pods.
- B. It schedules Pods onto nodes.
- C. It resolves Service names to IP addresses.
- D. It programs node-level rules that route Service traffic to backend Pods.

**4.** All manifests are stored in Git. Someone changes the replica count of a Deployment with `kubectl scale`. Argo CD has self-heal enabled. What happens?

- A. Argo CD commits the new value to Git.
- B. Argo CD reverts the Deployment to the state in Git.
- C. The change stays until someone syncs manually.
- D. Argo CD deletes the Deployment.

**5.** The containers in a Pod set CPU and memory requests but no limits. Which QoS class does the Pod get?

- A. Guaranteed
- B. Burstable
- C. BestEffort
- D. Restricted

**6.** Which statement about NetworkPolicy is true?

- A. A NetworkPolicy can explicitly deny specific traffic.
- B. NetworkPolicies are enforced by kube-proxy.
- C. NetworkPolicies select nodes, not Pods.
- D. NetworkPolicies take effect only if the CNI plugin supports them.

**7.** `kubectl get pods` returns Pods from the wrong cluster. What should you check first?

- A. The current context in your kubeconfig
- B. The kube-scheduler configuration
- C. The CoreDNS ConfigMap
- D. The taints on the nodes

**8.** Which CNCF graduated project provides vendor-neutral APIs, SDKs, and a Collector to generate and export traces, metrics, and logs?

- A. Jaeger
- B. Fluentd
- C. OpenTelemetry
- D. Thanos

**9.** Which object keeps a minimum number of replicas available during voluntary disruptions such as node drains?

- A. ResourceQuota
- B. LimitRange
- C. PriorityClass
- D. PodDisruptionBudget

**10.** A PersistentVolumeClaim requests the ReadWriteMany access mode. Which storage can most likely satisfy it?

- A. A single cloud block disk such as Amazon EBS
- B. A shared file system such as NFS
- C. An emptyDir volume
- D. A hostPath volume

**11.** Which Helm command shows the rendered manifests without installing anything?

- A. `helm template`
- B. `helm rollback`
- C. `helm history`
- D. `helm repo update`

**12.** Which statement about container images is correct?

- A. A tag always refers to the same image content.
- B. An image contains its own kernel.
- C. An image is made of read-only layers, and a running container adds a writable layer.
- D. Images can be built only with Docker.

**13.** Which Pod Security Admission mode rejects Pods that violate the selected profile?

- A. audit
- B. enforce
- C. warn
- D. dry-run

**14.** Which mechanism lets you add a new API type such as `Database` and manage it with kubectl?

- A. A ConfigMap
- B. An annotation
- C. An ExternalName Service
- D. A CustomResourceDefinition

**15.** A Deployment rollout is stuck. Only one new replica is available, and the new Pods are in ImagePullBackOff. What is the fastest way to return to the previous working version?

- A. `kubectl rollout undo deployment/<name>`
- B. `kubectl delete deployment/<name>`
- C. `kubectl rollout restart deployment/<name>`
- D. `kubectl scale deployment/<name> --replicas=0`

**16.** A node has the taint `node-role.kubernetes.io/control-plane:NoSchedule`. Which Pods can be scheduled on it?

- A. All Pods
- B. No Pods, not even DaemonSet Pods
- C. Pods with a matching toleration
- D. Only Pods that have a nodeSelector

**17.** A Pod is Running but shows READY 0/1, and its Service sends no traffic to it. What is the most likely reason?

- A. The liveness probe fails, and the container keeps restarting.
- B. The image tag is wrong.
- C. The node is NotReady.
- D. The readiness probe fails.

**18.** The kube-apiserver runs v1.37. Which kubectl version is within the supported version skew?

- A. v1.34
- B. v1.36
- C. v1.39
- D. v1.33

**19.** Which autoscaler adjusts the CPU and memory requests of Pods based on their historical usage?

- A. VerticalPodAutoscaler
- B. HorizontalPodAutoscaler
- C. Cluster Autoscaler
- D. KEDA

**20.** Which component translates Service names into IP addresses inside the cluster?

- A. kube-proxy
- B. kubelet
- C. CoreDNS
- D. etcd

**21.** Which workload resource gives each Pod a stable identity such as `web-0` and its own PersistentVolumeClaim?

- A. Deployment
- B. StatefulSet
- C. DaemonSet
- D. ReplicaSet

**22.** Which of the following is one of the OpenGitOps principles?

- A. Changes are pushed from the CI system to the cluster.
- B. The desired state is stored only in the cluster.
- C. Every deployment must be approved manually.
- D. The desired state is versioned and immutable.

**23.** Which Gateway API resource defines listeners, ports, and TLS settings and is usually managed by cluster operators?

- A. HTTPRoute
- B. GatewayClass
- C. Gateway
- D. ReferenceGrant

**24.** Which component starts static Pods from manifest files on a node?

- A. kubelet
- B. kube-scheduler
- C. kube-controller-manager
- D. kube-apiserver

**25.** A container exits with code 1 right after it starts, and the Pod alternates between Error and CrashLoopBackOff. Where are you most likely to find the cause?

- A. In the scheduler events
- B. In the kernel log of the node
- C. In etcd
- D. In the logs of the previous container instance

**26.** Which interface does Kubernetes use to attach networking to Pods?

- A. CRI
- B. CNI
- C. CSI
- D. OCI

**27.** Which deployment strategy runs two complete environments and switches all traffic from the old one to the new one at once?

- A. Canary
- B. Rolling update
- C. Blue/green
- D. Recreate

**28.** In the Kubernetes contributor ladder, which role can approve code changes for the files it is responsible for?

- A. Approver
- B. Member
- C. Reviewer
- D. Non-member contributor

**29.** Which statement about Kubernetes Secrets is correct?

- A. They are always encrypted in etcd.
- B. They cannot be mounted as files.
- C. Each Secret is limited to 1 KiB.
- D. A user who can create Pods in a namespace can read that namespace's Secrets by mounting them into a Pod.

**30.** Which object sets default CPU and memory requests for containers in a namespace that do not specify them?

- A. ResourceQuota
- B. LimitRange
- C. PriorityClass
- D. HorizontalPodAutoscaler

## 답과 풀이

| 번호 | 답 | 도메인 | 풀이 |
|---|---|---|---|
| 1 | C | Kubernetes Fundamentals | 모든 오브젝트는 etcd에 저장되고, etcd를 직접 읽고 쓰는 건 API 서버뿐이다 |
| 2 | A | Container Orchestration | 검색 도메인에 `svc.cluster.local`이 있어서 `<서비스>.<네임스페이스>`면 된다. `db`만 쓰면 자기 네임스페이스(web)에서 찾는다 |
| 3 | D | Kubernetes Fundamentals | 파드 IP는 CNI, 배치는 스케줄러, 이름 풀이는 CoreDNS다 |
| 4 | B | Application Delivery | GitOps에서는 Git이 기준이다. 셀프 힐이 켜져 있으면 드리프트를 Git 상태로 되돌린다 |
| 5 | B | Kubernetes Fundamentals | requests가 있지만 limits와 같지 않으니 Burstable이다. Restricted는 Pod Security 단계 이름이다 |
| 6 | D | Container Orchestration | NetworkPolicy는 허용 규칙만 있고, 실제로 막는 건 CNI 플러그인이다 |
| 7 | A | Kubernetes Fundamentals | 어느 클러스터에 누구로 붙을지는 kubeconfig의 현재 컨텍스트가 정한다 |
| 8 | C | Cloud Native Architecture | OpenTelemetry는 2026년 5월 graduated다. Jaeger는 트레이스 백엔드, Fluentd는 로그 수집, Thanos는 incubating인 Prometheus 장기 저장소다 |
| 9 | D | Kubernetes Fundamentals | PDB는 drain 같은 자발적 중단에서만 지켜진다. 노드 장애는 막지 못한다 |
| 10 | B | Container Orchestration | 여러 노드에서 읽기쓰기는 파일 스토리지여야 한다. 블록 디스크는 보통 RWO다 |
| 11 | A | Application Delivery | `helm template`은 렌더링만 한다. 차트 오류를 찾을 때 쓴다 |
| 12 | C | Kubernetes Fundamentals | 태그는 바뀔 수 있고, 컨테이너는 호스트 커널을 쓴다. Buildah, Podman으로도 OCI 이미지를 만든다 |
| 13 | B | Container Orchestration | enforce만 거절한다. warn은 경고, audit는 감사 로그 기록이다 |
| 14 | D | Kubernetes Fundamentals | CRD로 새 종류를 등록한다. 동작은 그걸 맡는 컨트롤러(오퍼레이터)가 만든다 |
| 15 | A | Application Delivery | undo가 바로 전 ReplicaSet으로 되돌린다. restart는 같은 잘못된 이미지로 다시 띄울 뿐이다 |
| 16 | C | Kubernetes Fundamentals | 톨러레이션이 있는 파드만 들어간다. 컨트롤 플레인에 뜨는 DaemonSet 파드도 톨러레이션으로 들어간다 |
| 17 | D | Container Orchestration | readiness에 실패하면 엔드포인트에서 빠진다. liveness 실패라면 재시작 횟수가 늘고, 이미지 오류라면 Running이 될 수 없다 |
| 18 | B | Kubernetes Fundamentals | kubectl은 API 서버 위아래 한 마이너, 즉 v1.36에서 v1.38까지다 |
| 19 | A | Cloud Native Architecture | VPA는 파드 크기, HPA와 KEDA는 파드 수, Cluster Autoscaler는 노드 수다 |
| 20 | C | Container Orchestration | 이름 풀이는 CoreDNS, 서비스 IP에서 파드로 보내는 규칙은 kube-proxy다 |
| 21 | B | Kubernetes Fundamentals | StatefulSet은 순서 있는 이름과 volumeClaimTemplates로 파드마다 PVC를 준다 |
| 22 | D | Application Delivery | 네 원칙은 선언적, 버전 관리되고 바뀌지 않음, 자동으로 끌어옴, 계속 조정이다 |
| 23 | C | Container Orchestration | Gateway가 리스너를 정한다. GatewayClass는 구현 종류, HTTPRoute는 앱 개발자의 라우팅 규칙이다 |
| 24 | A | Kubernetes Fundamentals | 스태틱 파드는 API 서버와 스케줄러를 거치지 않고 kubelet이 파일을 보고 띄운다 |
| 25 | D | Container Orchestration | 앱이 오류로 끝난 것이라 `kubectl logs --previous`에 이유가 남는다 |
| 26 | B | Kubernetes Fundamentals | CNI가 네트워크, CRI가 런타임, CSI가 스토리지다. OCI는 컨테이너 표준이다 |
| 27 | C | Application Delivery | 블루/그린은 두 벌을 다 띄우고 한 번에 넘긴다. 카나리는 조금씩 늘린다 |
| 28 | A | Cloud Native Architecture | reviewer는 리뷰하고, approver가 승인한다. 그 위가 subproject owner다 |
| 29 | D | Container Orchestration | 저장 암호화는 따로 설정해야 하고, 크기 한도는 1MiB다. 파드 생성 권한이 사실상 Secret 읽기 권한이 될 수 있다는 점이 함정이다 |
| 30 | B | Kubernetes Fundamentals | LimitRange의 defaultRequest와 default가 기본값을 넣는다. ResourceQuota는 네임스페이스 총량이다 |

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


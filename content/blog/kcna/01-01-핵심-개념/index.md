---
title: '[KCNA] 쿠버네티스 핵심 개념: 구성 요소, 오브젝트, 원하는 상태'
date: '2026-08-05T21:40:00+09:00'
categories:
- KCNA
tags:
- kubernetes
- kcna
- control-plane
- kube-apiserver
- etcd
- kubelet
- api-group
- crd
- controller
- Kubernetes Fundamentals
series:
- KCNA
series_order: 2
---

Kubernetes Fundamentals는 44%로 시험의 절반 가까이 되어서 네 편으로 나눴고, 이 글은 그중 Core Concepts다. 구성 요소와 오브젝트는 CKA 때 손으로 익혔지만, 객관식은 '이 일을 하는 구성 요소는 무엇인가'처럼 구분을 묻는다. 그래서 구성 요소마다 하는 일과 하지 않는 일을 나눠 적었다.

## 요약

- 컨트롤 플레인은 kube-apiserver, etcd, kube-scheduler, kube-controller-manager, cloud-controller-manager다. 노드에는 kubelet, kube-proxy, 컨테이너 런타임이 돈다.
- etcd와 직접 이야기하는 건 kube-apiserver뿐이다. 다른 구성 요소는 모두 API 서버를 거친다.
- 오브젝트는 apiVersion, kind, metadata, spec, status로 이루어진다. spec은 내가 원하는 상태, status는 컨트롤러가 채우는 실제 상태다.
- 컨트롤러는 spec과 실제 상태의 차이를 계속 줄인다. 이걸 조정 루프(reconciliation loop)라고 한다.
- API는 그룹과 버전으로 나뉜다. Pod, Service는 core 그룹(`v1`), Deployment는 `apps/v1`이다. 내장 alpha, beta API는 기본으로 꺼져 있다.
- CRD로 새 리소스 종류를 추가하고, 그 리소스를 맡는 컨트롤러를 붙이면 오퍼레이터가 된다.

## 1. 클러스터 구성 요소

{{< mermaid >}}
flowchart LR
  U["kubectl,<br>다른 클라이언트"] --> API
  subgraph cp["컨트롤 플레인"]
    API["kube-apiserver"]
    ETCD[("etcd")]
    SCH["kube-scheduler"]
    KCM["kube-controller-manager"]
    CCM["cloud-controller-manager"]
  end
  subgraph node["워커 노드"]
    KL["kubelet"]
    KP["kube-proxy"]
    CR["컨테이너 런타임<br>containerd, CRI-O"]
  end
  API <--> ETCD
  API <-->|"watch, 바인딩"| SCH
  API <-->|"watch, 오브젝트 수정"| KCM
  API <-->|"watch"| CCM
  API <-->|"watch, 상태 보고"| KL
  API <-->|"watch"| KP
  KL -->|"CRI"| CR
  CCM -.->|"로드 밸런서, 노드 정보"| CLOUD["클라우드 API"]
{{< /mermaid >}}

모든 선이 API 서버로 모인다는 게 그림의 요점이다. 스케줄러도, 컨트롤러도, kubelet도 API 서버를 지켜보다가(watch) 자기 일이 생기면 API 서버에 결과를 쓴다. 서로 직접 부르지 않는다.

| 구성 요소 | 하는 일 | 헷갈리기 쉬운 점 |
|---|---|---|
| kube-apiserver | 모든 요청의 입구. 인증, 인가, 어드미션을 통과한 요청만 etcd에 쓴다 | etcd와 직접 통신하는 유일한 구성 요소. 상태를 들고 있지 않아서 여러 대 띄워 수평 확장한다 |
| etcd | 클러스터의 모든 오브젝트를 저장하는 분산 키-값 저장소 | Raft 합의로 과반이 살아 있어야 쓸 수 있다. 그래서 3대, 5대처럼 홀수로 둔다. 백업 대상이다 |
| kube-scheduler | 노드가 정해지지 않은 파드에 노드를 골라 적는다(바인딩) | 컨테이너를 띄우지 않는다. 파드의 `nodeName`만 정한다 |
| kube-controller-manager | Deployment, ReplicaSet, Job, Node, EndpointSlice, ServiceAccount 같은 내장 컨트롤러를 한 프로세스로 돌린다 | 컨트롤러마다 바이너리가 따로 있는 게 아니다 |
| cloud-controller-manager | 클라우드 API와 이어 준다. LoadBalancer 서비스에 클라우드 로드 밸런서를 붙이고, 노드 정보와 라우트를 맞춘다 | 클라우드가 아닌 환경(kind, 온프레미스)에는 없을 수 있다 |
| kubelet | 노드마다 하나. 자기 노드에 배정된 파드를 런타임으로 띄우고, 프로브를 돌리고, 상태를 보고한다 | 컨트롤 플레인 노드에서도 돈다. 쿠버네티스가 만들지 않은 컨테이너는 관리하지 않는다 |
| kube-proxy | 노드마다 하나. 서비스 주소로 온 트래픽을 파드로 보내는 규칙(iptables, nftables)을 만든다 | 패킷을 직접 중계하지 않고 커널 규칙만 만든다. Cilium 같은 CNI가 같은 일을 대신하면 없어도 된다 |
| 컨테이너 런타임 | 이미지를 받아 컨테이너를 실행한다 | kubelet과 CRI로 이야기한다. Docker Engine을 직접 쓰던 dockershim은 v1.24에서 빠졌다 |

노드가 살아 있다는 신호는 kubelet이 `kube-node-lease` 네임스페이스의 Lease 오브젝트를 주기적으로 갱신하는 걸로 보낸다. 갱신이 끊기면 노드 컨트롤러가 노드의 Ready 조건을 Unknown으로 바꾼다. `kubectl get nodes`에서는 이게 NotReady로 보인다.

> **쉬운 설명**
>
> 쿠버네티스를 식당으로 보면 API 서버는 주문 접수 창구다. 손님(kubectl)도, 직원들도 모두 이 창구를 통해서만 일한다. etcd는 창구 뒤의 주문 장부이고, 장부를 직접 만지는 건 창구 직원뿐이다. 스케줄러는 '이 주문은 3번 주방'이라고 배정만 하고 요리는 하지 않는다. 컨트롤러 매니저는 장부와 홀 상태를 계속 비교하는 매니저들이다. 각 주방의 팀장이 kubelet이고, 실제 불과 냄비가 컨테이너 런타임이다.

## 2. 오브젝트: spec과 status

모든 오브젝트는 같은 뼈대를 가진다.

```yaml
apiVersion: apps/v1          # 그룹/버전
kind: Deployment             # 종류
metadata:
  name: web
  namespace: shop
  labels:
    app: web
  annotations:
    team: platform           # 셀렉터로는 고를 수 없는 메모
spec:                        # 내가 원하는 상태
  replicas: 3
  selector:
    matchLabels:
      app: web
  template:
    metadata:
      labels:
        app: web
    spec:
      containers:
      - name: web
        image: nginx:1.29
        ports:
        - containerPort: 80
```

이걸 적용하면 Deployment 컨트롤러가 status를 채운다. 사용자가 쓰는 칸이 아니다. 모양은 대략 이렇다.

```yaml
status:
  observedGeneration: 1
  replicas: 3
  updatedReplicas: 3
  readyReplicas: 3
  availableReplicas: 3
  conditions:
  - type: Available
    status: "True"
  - type: Progressing
    status: "True"
```

metadata에서 시험에 나올 만한 필드를 모았다.

| 필드 | 뜻 |
|---|---|
| name, namespace | 이름과 소속. 같은 네임스페이스 안에서 종류별로 이름이 겹치면 안 된다 |
| labels | 셀렉터로 고를 수 있는 키-값. 서비스와 디플로이먼트가 파드를 찾을 때 쓴다 |
| annotations | 셀렉터로 고를 수 없는 키-값. 도구가 쓰는 설정이나 메모를 담는다 |
| uid | 클러스터 전체에서 유일한 ID. 같은 이름으로 다시 만들면 바뀐다 |
| resourceVersion | 오브젝트가 바뀔 때마다 바뀌는 값. 동시 수정 충돌을 막는 데 쓴다 |
| generation | spec이 바뀔 때마다 1씩 오른다. status의 observedGeneration과 비교해 컨트롤러가 최신 spec을 봤는지 안다 |
| ownerReferences | 이 오브젝트의 주인. 파드의 주인은 ReplicaSet, ReplicaSet의 주인은 Deployment다 |
| finalizers | 지우기 전에 끝내야 할 작업 목록. 남아 있으면 삭제가 멈춘다 |

주인을 지우면 딸린 오브젝트도 지워진다(가비지 컬렉션). 그래서 Deployment를 지우면 ReplicaSet과 파드가 같이 사라진다. `kubectl delete --cascade=orphan`을 주면 딸린 오브젝트는 남긴다.

### 조정 루프

{{< mermaid >}}
flowchart LR
  O["관찰<br>API 서버를 watch"] --> C{"원하는 상태와<br>실제 상태가 같은가"}
  C -->|"같다"| O
  C -->|"다르다"| A["조치<br>오브젝트 생성, 삭제, 수정"]
  A --> O
{{< /mermaid >}}

컨트롤러는 '파드가 하나 죽었다'는 사건 하나하나에 반응하기보다, 지금 상태를 다시 보고 원하는 상태와 맞춘다. 그래서 사건을 놓쳐도 다음에 볼 때 맞춰진다. 사용자는 무엇을 원하는지만 적고(선언형), 어떻게 맞출지는 컨트롤러가 정한다.

> **쉬운 설명**
>
> 보일러 온도 조절기와 같다. 설정 온도 22도가 spec, 지금 방 온도가 status다. 조절기는 '누가 창문을 열었다'를 기억하지 않는다. 그냥 계속 온도를 재고, 낮으면 보일러를 켜고 높으면 끈다. 나는 22도라고만 적어 두면 된다.

## 3. API 그룹과 버전

`apiVersion`은 '그룹/버전'이다. core 그룹은 이름이 없어서 `v1`만 쓴다. URL로는 core 그룹이 `/api/v1`, 나머지가 `/apis/<그룹>/<버전>`이다.

| 그룹 | apiVersion | 대표 리소스 |
|---|---|---|
| core | v1 | Pod, Service, ConfigMap, Secret, Namespace, Node, PersistentVolume, PersistentVolumeClaim, ServiceAccount, Event |
| apps | apps/v1 | Deployment, ReplicaSet, StatefulSet, DaemonSet |
| batch | batch/v1 | Job, CronJob |
| networking.k8s.io | networking.k8s.io/v1 | Ingress, IngressClass, NetworkPolicy |
| rbac.authorization.k8s.io | rbac.authorization.k8s.io/v1 | Role, ClusterRole, RoleBinding, ClusterRoleBinding |
| storage.k8s.io | storage.k8s.io/v1 | StorageClass, CSIDriver, VolumeAttachment |
| autoscaling | autoscaling/v2 | HorizontalPodAutoscaler |
| policy | policy/v1 | PodDisruptionBudget |
| discovery.k8s.io | discovery.k8s.io/v1 | EndpointSlice |
| coordination.k8s.io | coordination.k8s.io/v1 | Lease |

버전에는 단계가 있다.

| 단계 | 버전 이름 예 | 기본 상태 | 특징 |
|---|---|---|---|
| alpha | v1alpha1 | 꺼짐 | 바뀌거나 예고 없이 사라질 수 있다. 운영에서 쓰지 않는다 |
| beta | v1beta1 | 꺼짐 | 잘 테스트됐지만 바뀔 수 있다. 지원 중단 뒤 일정 기간 남았다가 지워진다 |
| stable(GA) | v1, v2 | 켜짐 | 오래 유지된다 |

내장 beta API가 기본으로 꺼진 건 v1.24부터의 규칙이다. 그전에 이미 켜져 있던 beta API들은 그대로 켜진 채로 남았다. API 버전과 별개로 기능에도 alpha, beta, stable 단계가 있다(feature gate). 문서 맨 위의 `FEATURE STATE: Kubernetes v1.35 [stable]` 같은 표시가 그것이고, beta 기능은 보통 기본으로 켜져 있다. 'beta API'와 'beta 기능'의 기본값이 다르다는 점이 헷갈렸다.

리소스는 네임스페이스에 속하는 것과 클러스터 전체 범위인 것으로 나뉜다. Node, PersistentVolume, StorageClass, Namespace, ClusterRole, CustomResourceDefinition은 클러스터 범위다.

```bash
kubectl api-resources                     # 리소스 이름, 짧은 이름, 그룹, 네임스페이스 여부
kubectl api-resources --namespaced=false  # 클러스터 범위 리소스만
kubectl api-versions                      # 서버가 제공하는 그룹/버전 목록
kubectl explain deployment.spec.strategy  # 필드 설명
```

## 4. 워크로드와 기본 리소스

| 리소스 | 언제 쓰나 |
|---|---|
| Pod | 컨테이너 하나 이상을 같은 노드, 같은 네트워크 네임스페이스로 묶은 가장 작은 배포 단위. 보통 직접 만들지 않는다 |
| ReplicaSet | 같은 파드를 지정한 개수만큼 유지한다. 보통 Deployment가 만든다 |
| Deployment | 상태 없는 앱. 롤링 업데이트와 롤백을 한다 |
| StatefulSet | 이름(web-0, web-1)과 저장소가 고정돼야 하는 앱. 데이터베이스 같은 것 |
| DaemonSet | 노드마다 하나씩. 로그 수집기, 모니터링 에이전트, CNI |
| Job | 끝까지 실행되고 끝나는 작업. 실패하면 다시 시도한다 |
| CronJob | 정해진 시간마다 Job을 만든다 |
| Service | 바뀌는 파드 IP 앞에 고정된 주소와 이름을 둔다 |
| ConfigMap, Secret | 설정과 민감한 값을 이미지 밖에 둔다 |
| Namespace | 이름과 권한, 쿼터를 나누는 단위 |

처음부터 있는 네임스페이스는 네 개다. `default`(지정하지 않으면 여기), `kube-system`(쿠버네티스 구성 요소), `kube-public`(모두가 읽을 수 있는 정보), `kube-node-lease`(노드 하트비트용 Lease).

라벨 셀렉터는 두 가지다. 같음 기반(`app=web`, `tier!=db`)과 집합 기반(`env in (prod, stage)`, `!canary`)이다. 매니페스트에서는 `matchLabels`가 같음 기반, `matchExpressions`가 집합 기반이다.

## 5. API 확장: CRD, 오퍼레이터, API 애그리게이션

쿠버네티스 소스를 고치지 않고도 API를 늘릴 수 있다.

- **CRD(CustomResourceDefinition)**: 새 리소스 종류를 등록한다. 만든 커스텀 리소스는 다른 오브젝트처럼 etcd에 저장되고 kubectl로 다룬다. 컨트롤러가 없으면 그냥 저장된 데이터일 뿐이다.
- **오퍼레이터**: CRD와 그걸 맡는 컨트롤러를 묶어, 사람이 하던 운영 지식(설치, 백업, 장애 조치)을 코드로 옮긴 것이다. Prometheus Operator의 ServiceMonitor, cert-manager의 Certificate가 예다.
- **API 애그리게이션**: 별도의 API 서버를 APIService로 API 서버 뒤에 붙인다. metrics-server가 `metrics.k8s.io`를 이렇게 제공한다.

Gateway API도 쿠버네티스에 내장된 게 아니라 CRD로 설치한다. 시험에서 'Gateway API는 어떻게 클러스터에 들어오나'를 물으면 CRD다.

## 6. 릴리스 주기

쿠버네티스는 1년에 세 번 마이너 버전을 낸다. 한 마이너 버전은 약 14개월 동안 패치를 받는다(12개월 정식 지원 뒤 2개월 유지보수). 이 글을 쓰는 지금 최신은 v1.36이고, v1.37은 8월 26일에 나올 예정이다.

## 헷갈렸던 것들

- 스케줄러는 컨테이너를 띄우지 않는다. 노드만 정하고, 띄우는 건 그 노드의 kubelet이다.
- etcd를 직접 읽고 쓰는 건 API 서버뿐이다.
- kubelet은 노드 구성 요소지만 컨트롤 플레인 노드에서도 돈다.
- status는 사용자가 쓰는 곳이 아니다. 컨트롤러가 채운다.
- Deployment는 파드를 직접 만들지 않는다. ReplicaSet을 만들고, ReplicaSet이 파드를 만든다.
- 어노테이션은 셀렉터로 고를 수 없다.
- 내장 beta API는 기본으로 꺼져 있지만, beta 기능(feature gate)은 보통 켜져 있다.

## 용어 정리

| 용어 | 뜻 |
|---|---|
| 컨트롤 플레인 | 클러스터 상태를 저장하고 결정을 내리는 구성 요소 묶음 |
| 원하는 상태 | spec에 적은 상태. 컨트롤러가 실제 상태를 여기에 맞춘다 |
| 조정 루프 | 원하는 상태와 실제 상태를 계속 비교해 차이를 줄이는 컨트롤러의 반복 |
| API 그룹 | 관련 리소스를 묶은 이름. core 그룹은 이름이 없다 |
| CRD | 새 리소스 종류를 API에 등록하는 오브젝트 |
| 오퍼레이터 | CRD와 전용 컨트롤러로 앱 운영을 자동화하는 패턴 |
| Lease | 노드 하트비트와 리더 선출에 쓰는 가벼운 오브젝트 |

## 복습 문제

**1.** Which Kubernetes component is the only one that communicates directly with etcd?

- A. kube-scheduler
- B. kubelet
- C. kube-apiserver
- D. kube-controller-manager

**2.** A new Pod has been created, but its `spec.nodeName` is still empty. Which component is responsible for setting it?

- A. kube-proxy
- B. kube-scheduler
- C. kubelet
- D. cloud-controller-manager

**3.** Which part of a Kubernetes object describes the desired state set by the user?

- A. spec
- B. status
- C. metadata.annotations
- D. kind

**4.** In recent Kubernetes releases, what is the default state of a built-in beta API version?

- A. It is enabled and cannot be disabled.
- B. It is enabled only on managed clusters.
- C. It is removed in the next minor release.
- D. It is disabled until it is explicitly enabled on the kube-apiserver.

**5.** Which workload resource runs one copy of a Pod on each eligible node?

- A. StatefulSet
- B. Job
- C. DaemonSet
- D. ReplicaSet

**6.** A team wants to add a new resource kind, `Backup`, to their cluster without changing the Kubernetes source code. What should they create?

- A. A ConfigMap named backup
- B. A CustomResourceDefinition
- C. An annotation on every namespace
- D. A namespace called backup

**7.** Which namespace contains the Lease objects that kubelets renew as node heartbeats?

- A. kube-node-lease
- B. kube-system
- C. kube-public
- D. default

## 답과 풀이

1. **C** 다른 구성 요소는 모두 API 서버를 거친다.
2. **B** 스케줄러가 노드를 골라 바인딩하면 `nodeName`이 채워진다. 그다음 그 노드의 kubelet이 컨테이너를 띄운다.
3. **A** spec이 원하는 상태, status가 실제 상태다.
4. **D** 지금 문서는 내장 alpha와 beta API가 모두 기본으로 꺼져 있고, API 서버 설정에서 켜야 쓸 수 있다고 적는다.
5. **C** DaemonSet은 노드마다 하나씩 파드를 둔다. 노드가 늘면 파드도 따라 생긴다.
6. **B** CRD로 새 종류를 등록한다. 동작까지 원하면 그걸 맡는 컨트롤러(오퍼레이터)를 같이 둔다.
7. **A** kube-node-lease에 노드마다 Lease가 하나씩 있다.

## 참고 자료

- Kubernetes 문서, 쿠버네티스 구성 요소: <https://kubernetes.io/docs/concepts/overview/components/>
- Kubernetes 문서, 쿠버네티스 오브젝트: <https://kubernetes.io/docs/concepts/overview/working-with-objects/>
- Kubernetes 문서, 컨트롤러: <https://kubernetes.io/docs/concepts/architecture/controller/>
- Kubernetes 문서, 가비지 컬렉션: <https://kubernetes.io/docs/concepts/architecture/garbage-collection/>
- Kubernetes 문서, API 개요: <https://kubernetes.io/docs/reference/using-api/>
- Kubernetes 문서, 커스텀 리소스: <https://kubernetes.io/docs/concepts/extend-kubernetes/api-extension/custom-resources/>
- Kubernetes 문서, 오퍼레이터 패턴: <https://kubernetes.io/docs/concepts/extend-kubernetes/operator/>
- Kubernetes 문서, Lease: <https://kubernetes.io/docs/concepts/architecture/leases/>
- Kubernetes 릴리스: <https://kubernetes.io/releases/>


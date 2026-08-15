---
title: '[KCNA] 스케줄링: 필터와 점수, 리소스 요청, 어피니티와 테인트, 우선순위'
date: '2026-08-15T16:00:00+09:00'
categories:
- KCNA
tags:
- kubernetes
- kcna
- scheduler
- requests
- limits
- qos
- node-affinity
- taints
- tolerations
- topology-spread
- priorityclass
- Kubernetes Fundamentals
series:
- KCNA
series_order: 4
---

스케줄링은 예전 범위에도 있던 항목이다. CKA 때는 YAML 필드 이름을 외우는 게 일이었는데, 이번에는 '왜 이 파드가 이 노드에 갔나, 왜 못 갔나'를 말로 설명할 수 있게 정리했다. 객관식 보기에서 헷갈리게 만드는 지점도 대부분 여기 있다. requests와 limits, 톨러레이션과 어피니티, NoSchedule과 NoExecute 같은 것들이다.

## 요약

- 스케줄러는 노드가 정해지지 않은 파드마다 필터링(맞지 않는 노드 거르기), 점수 매기기, 바인딩 순서로 노드를 정한다.
- 자원이 맞는지는 requests로 판단한다. limits도, 지금 실제 사용량도 아니다.
- nodeSelector와 노드 어피니티는 파드가 노드를 고르는 조건, 테인트는 노드가 파드를 밀어내는 조건이다. 톨러레이션은 밀어내는 걸 견딘다는 표시일 뿐, 그 노드로 가라는 뜻은 아니다.
- QoS 클래스는 Guaranteed, Burstable, BestEffort다. 노드 메모리가 모자라면 BestEffort부터 쫓겨난다.
- PriorityClass로 우선순위를 주면, 자리가 없을 때 낮은 파드를 밀어내고(선점) 들어갈 수 있다.
- topologySpreadConstraints로 존이나 노드에 고르게 퍼뜨린다.

## 1. 스케줄러가 노드를 고르는 순서

{{< mermaid >}}
flowchart TB
  Q["스케줄링 대기열<br>nodeName이 빈 파드"] --> F["필터링<br>requests, nodeSelector, 어피니티,<br>테인트, 포트, 볼륨 위치"]
  F --> N{"남은 노드가 있나"}
  N -->|"없다"| P["선점 시도<br>안 되면 Pending,<br>이벤트 FailedScheduling"]
  N -->|"있다"| S["점수 매기기<br>자원 여유, 선호 어피니티,<br>이미지 유무, 분산"]
  S --> B["바인딩<br>가장 높은 노드를 nodeName에 기록"]
  B --> K["그 노드의 kubelet이<br>컨테이너 실행"]
{{< /mermaid >}}

스케줄러 안쪽은 플러그인 구조(스케줄링 프레임워크)라서 필터와 점수 기준을 플러그인으로 켜고 끈다. PreFilter, Filter, PostFilter(선점이 여기서 돈다), Score, Reserve, Permit, Bind 같은 확장 지점이 있다.

스케줄러를 거치지 않는 경우도 있다. 파드에 `nodeName`을 직접 적으면 스케줄러가 건너뛰고 그 노드의 kubelet이 바로 띄운다. 스태틱 파드도 스케줄러와 상관없다. `schedulerName`을 주면 기본 스케줄러 대신 다른 스케줄러가 맡는다. 반대로 `schedulingGates`를 걸어 두면 게이트가 다 풀릴 때까지 스케줄링 대기열에 들어가지 않는다(v1.30 stable).

## 2. requests, limits, QoS

| 항목 | 쓰이는 곳 | 넘으면 |
|---|---|---|
| requests | 스케줄링 기준. 노드의 할당 가능 자원(allocatable)에서 이미 배정된 requests 합을 뺀 만큼 남아야 들어간다 | 넘어서 써도 된다(limits까지) |
| limits | 실행 중 상한 | CPU는 스로틀(느려짐), 메모리는 OOM으로 컨테이너가 죽는다 |

노드의 allocatable은 전체 용량에서 시스템 예약, kube 예약, 축출 기준치를 뺀 값이다. `kubectl describe node`의 Allocatable과 Allocated resources를 비교하면 왜 Pending인지 보인다.

QoS 클래스는 자원 설정으로 자동으로 정해진다.

| QoS | 조건 | 메모리 부족으로 쫓겨나는 순서 |
|---|---|---|
| Guaranteed | 모든 컨테이너가 CPU와 메모리 둘 다 requests와 limits를 같게 적었다 | 가장 나중 |
| Burstable | Guaranteed는 아니지만 requests나 limits가 하나라도 있다 | 중간 |
| BestEffort | 어떤 컨테이너에도 requests, limits가 없다 | 가장 먼저 |

kubelet은 노드 메모리가 기준치 아래로 떨어지면 파드를 축출한다. 사용량이 requests를 넘는지, 우선순위, requests 대비 사용량 순으로 고르기 때문에 결과적으로 BestEffort가 먼저 나가고 Guaranteed가 마지막에 나간다.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: api
spec:
  containers:
  - name: api
    image: nginx:1.29
    resources:              # requests와 limits가 같으면 Guaranteed
      requests:
        cpu: 500m
        memory: 256Mi
      limits:
        cpu: 500m
        memory: 256Mi
```

## 3. 파드가 노드를 고르는 조건

nodeSelector는 라벨이 정확히 맞는 노드만 고른다. 노드 어피니티는 연산자(In, NotIn, Exists, Gt, Lt)를 쓸 수 있고, 꼭 지켜야 하는 조건과 되도록 지키는 조건을 나눌 수 있다.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: db
spec:
  affinity:
    nodeAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:    # 꼭: SSD 노드만
        nodeSelectorTerms:
        - matchExpressions:
          - key: disktype
            operator: In
            values: ["ssd"]
      preferredDuringSchedulingIgnoredDuringExecution:   # 되도록: 존 a
      - weight: 50
        preference:
          matchExpressions:
          - key: topology.kubernetes.io/zone
            operator: In
            values: ["ap-northeast-2a"]
  containers:
  - name: db
    image: postgres:18
```

이름 뒤의 `IgnoredDuringExecution`은 '이미 떠 있는 파드는 나중에 노드 라벨이 바뀌어도 그대로 둔다'는 뜻이다.

파드 어피니티와 안티어피니티는 노드 라벨이 아니라 '이미 떠 있는 다른 파드'를 기준으로 한다. `topologyKey`로 같은 범위를 정한다. `kubernetes.io/hostname`이면 같은 노드, `topology.kubernetes.io/zone`이면 같은 존이다. 캐시를 앱 옆에 붙이려면 어피니티, 같은 앱의 복제본을 다른 노드로 떨어뜨리려면 안티어피니티다.

## 4. 노드가 파드를 밀어내는 조건: 테인트와 톨러레이션

```bash
kubectl taint nodes gpu-1 dedicated=gpu:NoSchedule     # 테인트 걸기
kubectl taint nodes gpu-1 dedicated=gpu:NoSchedule-    # 끝에 -를 붙이면 지운다
```

| 효과 | 새 파드 | 이미 떠 있는 파드 |
|---|---|---|
| NoSchedule | 톨러레이션이 없으면 안 받는다 | 그대로 둔다 |
| PreferNoSchedule | 되도록 안 받는다 | 그대로 둔다 |
| NoExecute | 안 받는다 | 톨러레이션이 없으면 내보낸다. `tolerationSeconds`만큼 버틸 수 있다 |

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: trainer
spec:
  tolerations:
  - key: dedicated
    operator: Equal
    value: gpu
    effect: NoSchedule
  containers:
  - name: trainer
    image: python:3.13
```

톨러레이션만 있는 파드는 GPU 노드에 갈 수 있을 뿐, 일반 노드로도 간다. 'GPU 노드에는 GPU 파드만, GPU 파드는 GPU 노드에만' 두려면 테인트와 톨러레이션에 노드 어피니티까지 같이 쓴다.

쿠버네티스가 알아서 거는 테인트도 있다. 컨트롤 플레인 노드의 `node-role.kubernetes.io/control-plane:NoSchedule`, 노드에 문제가 생겼을 때의 `node.kubernetes.io/not-ready`, `node.kubernetes.io/unreachable`(NoExecute)이다. 파드에는 이 두 NoExecute 테인트를 300초 견디는 톨러레이션이 기본으로 붙는다. 노드가 끊기고 5분쯤 지나야 파드가 다른 노드로 옮겨 가는 이유다.

## 5. 고르게 퍼뜨리기: topologySpreadConstraints

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
spec:
  replicas: 6
  selector:
    matchLabels:
      app: web
  template:
    metadata:
      labels:
        app: web
    spec:
      topologySpreadConstraints:
      - maxSkew: 1                               # 존 사이 개수 차이는 1까지
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: DoNotSchedule         # 못 지키면 Pending (ScheduleAnyway면 점수에만 반영)
        labelSelector:
          matchLabels:
            app: web
      containers:
      - name: web
        image: nginx:1.29
```

안티어피니티는 '같은 곳에 두지 마라'라서 노드 수보다 복제본이 많으면 남는 파드가 Pending이 된다. 분산 제약은 '차이를 얼마 이하로'라서 복제본이 많아도 고르게 나눠 담는다.

## 6. 우선순위와 선점

```yaml
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: business-critical
value: 100000                  # 클수록 먼저
globalDefault: false
preemptionPolicy: PreemptLowerPriority   # Never면 줄은 앞에 서되 남을 밀어내지 않는다
description: "결제처럼 먼저 떠야 하는 서비스"
```

파드에 `priorityClassName: business-critical`을 주면, 자리가 없을 때 스케줄러가 더 낮은 우선순위 파드를 내보내고 그 자리에 넣는다. PodDisruptionBudget은 가능하면 지키지만 보장하지는 않는다. `system-cluster-critical`과 `system-node-critical`은 쿠버네티스가 미리 만들어 둔 가장 높은 우선순위로, CoreDNS나 CNI 같은 구성 요소용이다.

## 7. 스케줄러 밖에서 배치에 영향을 주는 것

- **DaemonSet**: DaemonSet 컨트롤러가 노드마다 파드를 만들고, 노드 어피니티를 붙여 기본 스케줄러가 배치한다.
- **Cluster Autoscaler, Karpenter**: Pending 파드를 보고 노드를 늘린다. 스케줄러는 노드를 만들지 않는다. 노드가 생기면 스케줄러가 다시 배치한다.
- **Descheduler**: 이미 배치된 파드 중 규칙에 안 맞게 된 것을 내보내 다시 배치되게 한다. 스케줄러는 한 번 배치한 파드를 옮기지 않기 때문에 따로 있는 도구다.

> **쉬운 설명**
>
> 교실 자리 배정과 같다. 선생님(스케줄러)은 학생(파드)마다 먼저 앉을 수 없는 자리를 거르고(필터링), 남은 자리 중 가장 나은 곳을 골라(점수) 자리표에 적는다(바인딩). 책상에 붙은 '반장 전용' 스티커가 테인트, 반장 배지가 톨러레이션이다. 배지가 있으면 그 자리에 앉아도 되지만, 꼭 거기 앉으라는 뜻은 아니다. '창가 자리가 좋다'는 희망이 어피니티다. 우선순위가 높은 학생이 왔는데 자리가 없으면, 선생님이 다른 학생을 일으켜 세우기도 한다(선점).

## 헷갈렸던 것들

- 필터는 limits가 아니라 requests로 판단한다. 실제 사용량도 보지 않는다.
- 톨러레이션은 허락이지 끌어당기는 힘이 아니다.
- NoSchedule은 기존 파드를 남기고, NoExecute는 기존 파드도 내보낸다.
- CPU limits를 넘으면 스로틀, 메모리 limits를 넘으면 OOMKilled다.
- Guaranteed는 모든 컨테이너가 CPU와 메모리 둘 다 requests와 limits가 같아야 한다.
- Pending의 이유는 `kubectl describe pod`의 Events에서 FailedScheduling 메시지로 본다.
- 스케줄러는 노드를 만들지도, 배치한 파드를 옮기지도 않는다.

## 용어 정리

| 용어 | 뜻 |
|---|---|
| 바인딩 | 스케줄러가 고른 노드를 파드의 nodeName에 기록하는 일 |
| allocatable | 노드에서 파드에 줄 수 있는 자원. 전체 용량에서 예약분을 뺀 값 |
| QoS 클래스 | requests와 limits 설정으로 정해지는 파드 등급. 축출 순서에 쓰인다 |
| 노드 어피니티 | 노드 라벨로 파드가 갈 노드를 고르는 조건 |
| 테인트 | 노드에 걸어 파드를 밀어내는 표시 |
| 톨러레이션 | 파드에 붙여 테인트를 견디게 하는 표시 |
| 선점 | 높은 우선순위 파드를 위해 낮은 파드를 내보내는 일 |
| topologyKey | 같은 범위로 볼 노드 라벨. hostname이면 노드, zone이면 존 |

## 복습 문제

**1.** Which value does the kube-scheduler use to decide whether a Pod fits on a node?

- A. Container limits
- B. Container requests
- C. The current CPU usage reported by metrics-server
- D. The number of containers in the Pod

**2.** A node has the taint `dedicated=gpu:NoSchedule`. A Pod has a matching toleration but no nodeSelector or node affinity. What happens when the Pod is scheduled?

- A. The Pod must be placed on that node.
- B. The API server rejects the Pod.
- C. Existing Pods on that node are evicted.
- D. The Pod can be placed on that node or on any other suitable node.

**3.** Every container in a Pod sets CPU and memory requests equal to their limits. Which QoS class does the Pod get?

- A. Guaranteed
- B. Burstable
- C. BestEffort
- D. Critical

**4.** Which taint effect also evicts Pods that are already running on the node if they do not tolerate the taint?

- A. NoSchedule
- B. PreferNoSchedule
- C. NoExecute
- D. NoAdmit

**5.** A high-priority Pod cannot be scheduled because every node is full. What can the scheduler do?

- A. Create a new node in the cloud provider.
- B. Evict lower-priority Pods to make room for it.
- C. Lower the Pod's resource requests.
- D. Ignore the Pod's resource requests.

**6.** Which Pod field spreads replicas evenly across zones while limiting the difference in Pod counts between zones?

- A. podAntiAffinity with weight 100
- B. nodeSelector
- C. priorityClassName
- D. topologySpreadConstraints

**7.** A container uses more memory than its memory limit. What usually happens?

- A. The container is OOM-killed and may be restarted.
- B. The container's CPU is throttled.
- C. The Pod is automatically moved to a bigger node.
- D. Nothing happens, because limits are only advisory.

## 답과 풀이

1. **B** 스케줄러는 requests 합으로 자리를 계산한다. 실제 사용량은 보지 않는다.
2. **D** 톨러레이션은 테인트를 견딜 수 있다는 뜻일 뿐이다. 그 노드로 보내려면 노드 어피니티나 nodeSelector를 같이 쓴다.
3. **A** 모든 컨테이너가 CPU와 메모리 모두 requests와 limits를 같게 적으면 Guaranteed다.
4. **C** NoExecute는 이미 떠 있는 파드도 내보낸다. tolerationSeconds만큼은 버틸 수 있다.
5. **B** 선점이다. 노드를 새로 만드는 건 Cluster Autoscaler 같은 별도 도구의 일이다.
6. **D** maxSkew로 범위 사이 개수 차이를 제한한다.
7. **A** 메모리는 압축할 수 없는 자원이라 limits를 넘으면 컨테이너가 죽는다. CPU를 넘으면 스로틀이다.

## 참고 자료

- Kubernetes 문서, kube-scheduler: <https://kubernetes.io/docs/concepts/scheduling-eviction/kube-scheduler/>
- Kubernetes 문서, 스케줄링 프레임워크: <https://kubernetes.io/docs/concepts/scheduling-eviction/scheduling-framework/>
- Kubernetes 문서, 파드를 노드에 배정하기: <https://kubernetes.io/docs/concepts/scheduling-eviction/assign-pod-node/>
- Kubernetes 문서, 테인트와 톨러레이션: <https://kubernetes.io/docs/concepts/scheduling-eviction/taint-and-toleration/>
- Kubernetes 문서, 파드 토폴로지 분배 제약: <https://kubernetes.io/docs/concepts/scheduling-eviction/topology-spread-constraints/>
- Kubernetes 문서, 파드 우선순위와 선점: <https://kubernetes.io/docs/concepts/scheduling-eviction/pod-priority-preemption/>
- Kubernetes 문서, 파드 스케줄링 준비성: <https://kubernetes.io/docs/concepts/scheduling-eviction/pod-scheduling-readiness/>
- Kubernetes 문서, 컨테이너 자원 관리: <https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/>
- Kubernetes 문서, 파드 QoS 클래스: <https://kubernetes.io/docs/concepts/workloads/pods/pod-qos/>
- Kubernetes 문서, 노드 압박 축출: <https://kubernetes.io/docs/concepts/scheduling-eviction/node-pressure-eviction/>


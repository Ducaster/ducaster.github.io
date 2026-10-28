---
title: '[K8s 소식] HPA 0까지 줄이기 beta, kubelet rootless 모드 beta, etcd RangeStream'
date: '2026-09-19T15:00:00+09:00'
categories:
- Kubernetes
tags:
- kubernetes
- v1.37
- hpa
- scale-to-zero
- external-metrics
- rootless
- user-namespaces
- etcd
- rangestream
- watch-cache
- 소식
series:
- Kubernetes 소식
series_order: 24
---

v1.37 후속 글이 9월 초부터 쏟아졌다. 릴리스 정리에서 표 한 줄로 넘긴 기능들이 하나씩 자세히 나왔는데, 그중 HPA로 워크로드를 0개까지 줄였다가 다시 늘리는 기능과 kubelet을 포함한 노드 구성 요소 전체를 root가 아닌 사용자로 돌리는 rootless 모드를 읽었다. etcd 3.7부터 따라온 RangeStream이 API 서버에서 실제로 무엇을 줄이는지 설명한 글도 있었다.

## 요약

- HPA의 0까지 줄이기가 v1.37에서 beta로 기본 켜짐이 됐다. minReplicas: 0과 함께 Object나 External 지표가 하나 이상 있어야 하고, CPU, 메모리만 있는 HPA는 API 서버가 거절한다.
- HPA가 줄인 0과 사람이 멈춘 0을 ScaledToZero 조건으로 구분한다. 사람이 replicas를 0으로 만든 워크로드는 HPA가 깨우지 않는다.
- KubeletInUserNamespace(rootless 모드)가 beta가 됐다. kubelet, 런타임, CNI, kube-proxy까지 노드 구성 요소를 호스트의 일반 사용자로 돌린다. 파드용 User Namespaces(hostUsers: false)와는 다른 기능이고 같이 쓸 수 있다.
- EtcdRangeStream이 beta로 기본 켜짐이다. etcd 3.7과 짝을 이루면 API 서버가 큰 목록을 조각으로 받아 바로 풀고 버려서, 양쪽 모두 메모리 최고점이 낮고 예측 가능해진다.

## 1. HPA로 0개까지

CPU나 메모리로 확장하는 HPA는 0까지 줄일 수가 없다. 파드가 0개면 잴 사용량도 없어서 다시 늘릴 신호가 사라진다. 큐 길이 같은 외부 지표는 일하는 파드가 없어도 존재하니, 그걸 보고 0에서 다시 깨울 수 있다.

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: queue-worker
  annotations:
    kubernetes.io/description: "Scales queue-worker based on the number of queued tasks"
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: queue-worker
  minReplicas: 0
  maxReplicas: 10
  metrics:
  - type: External
    external:
      metric:
        name: queue_consumer_lag
        selector:
          matchLabels:
            name: worker_tasks
      target:
        type: Value
        value: "30"
```

큐에 쌓인 작업 30개마다 파드 하나, 최대 10개다. 지표는 Prometheus Adapter 같은 어댑터가 External Metrics API로 내보내야 하고, HPA를 만들기 전에 kubectl get --raw로 값이 읽히는지 먼저 보라고 했다. 지표를 못 읽으면 0에서 깨어날 수 없기 때문이다.

{{< mermaid >}}
stateDiagram-v2
  direction LR
  Running: 1개 이상 실행 중
  Zero: 0개 (ScaledToZero=True)
  Paused: 0개, 조건 없음 (사람이 멈춤)
  Running --> Zero: 큐가 비고 축소 안정화 5분 경과
  Zero --> Running: 큐에 작업이 쌓임 (ScaledToZero=False, NotScaledToZero)
  Running --> Paused: 사람이 replicas를 0으로
  Paused --> Running: 사람이 다시 늘림
{{< /mermaid >}}

| 알아 둘 점 | 내용 |
|---|---|
| 처음 만들 때 | 디플로이먼트는 1개 이상으로 시작한다. 처음부터 0이면 '사람이 멈춘 것'으로 본다 |
| 축소 안정화 | 기본 5분. 큐가 잠깐 비었다고 일꾼을 다 없애지 않는다. spec.behavior.scaleDown으로 조정 |
| 지표를 못 읽으면 | ScalingActive=False, reason FailedGetExternalMetric. 지표를 고치거나 손으로 늘려야 한다 |
| 업그레이드 중 | API 서버와 컨트롤러 매니저 둘 다 기능이 켜진 뒤에 minReplicas: 0 HPA를 만든다. 컨트롤러 매니저가 모르면 0을 '멈춤'으로 보고 그대로 둔다 |
| 되돌릴 때 | 기능을 끄거나 버전을 내리기 전에 minReplicas를 1 이상으로 바꾸고, 0에 있는 워크로드를 손으로 늘린다 |
| 맞는 워크로드 | 큐 소비자, 배치. 서비스는 파드가 없으면 요청을 쌓아 두지 않으니 HTTP는 앞에 버퍼링 계층이 따로 필요하다 |

GPU를 잡고 있는 워커가 밤새 놀고 있는 경우를 생각하면 꽤 큰 절약이다. 대신 깨어날 때 스케줄, 이미지, 앱 기동 시간만큼 늦다. 6월에 정리한 Knative가 HTTP 쪽에서 이 버퍼링 역할을 해 왔던 것이다.

## 2. kubelet rootless 모드 beta

4월에 GA가 된 User Namespaces는 파드를 사용자 네임스페이스에 넣는 것이었다. 이번 건 그 반대편이다. kubelet, containerd 같은 런타임, CNI 플러그인, kube-proxy가 호스트의 일반 사용자(예: UID 1000)로 돌고, 사용자 네임스페이스 안에서만 root처럼 보인다.

| 비교 | 파드 User Namespaces | kubelet rootless 모드 |
|---|---|---|
| 기능 게이트 | UserNamespacesSupport, v1.36 GA | KubeletInUserNamespace, v1.37 beta |
| 사용자 네임스페이스에 들어가는 것 | 파드 | 노드 구성 요소 전체 |
| 노드 구성 요소 | 여전히 root | 일반 사용자 |
| 켜는 법 | 파드에 hostUsers: false | 사용자 네임스페이스를 쿠버네티스 밖에서 만들어 그 안에서 노드를 띄운다(예: rootless Docker 위의 kind) |
| 같이 쓰면 | privileged: true 없이 쿠버네티스 안에 쿠버네티스를 띄울 수 있다 | |

공식 글은 노드 구성 요소에서 실제로 나왔던 탈출 취약점을 줄줄이 예로 들었다. CRI-O에서 임의 sysctl을 설정하게 만든 cr8escape(CVE-2022-0811), runc의 procfs 노출(CVE-2023-27561, CVE-2025-31133), 그리고 gitRepo 볼륨으로 kubelet이 root로 명령을 실행하게 만든 CVE-2024-10220이다. 4월에 v1.36에서 gitRepo 볼륨이 완전히 막혔다고 정리했는데, 그 이유가 여기 있었다. rootless라면 이런 일이 터져도 피해가 그 일반 사용자 계정에 갇힌다. 다만 커널 자체의 취약점은 막지 못하니 seccomp 같은 기존 보호와 같이 쓰라고 한다.

| beta에서 바뀐 것 | 내용 |
|---|---|
| 기본 켜짐 | 게이트를 켠다고 kubelet이 사용자 네임스페이스로 들어가지는 않는다. 기존 rootful 클러스터는 그대로다 |
| 노드 상태 | kubectl get nodes -o yaml에 runningInUserNamespace가 나온다. 진짜 root가 필요한 워크로드(일부 CNI 설치기 등)를 라벨이나 테인트로 피하게 할 수 있다 |
| 테스트 | 쿠버네티스 CI의 노드 적합성 테스트가 rootless kind 클러스터에서 돈다 |

게이트가 하는 일 자체는 '심심하다'고 적혀 있었다. 사용자 네임스페이스 안에서는 vm.overcommit_memory 같은 일부 sysctl 설정과 /dev/kmsg 감시가 권한 오류를 내는데, 그걸 무시하게 해 주는 게 거의 전부라고 한다. 쓰임새 중에 'AI 코딩 에이전트와 테스트 클러스터를 전용 일반 사용자 계정에서 돌려서, 에이전트가 인터넷의 나쁜 정보에 속아도 호스트를 망가뜨리지 못하게 한다'는 항목이 요즘답다고 느꼈다. 노트북의 VPN용 iptables 규칙을 로컬 클러스터가 건드리지 못하게 하는 용도도 있었다. 내 kind는 맥의 Docker Desktop 위라 이미 VM 안에서 돌고 있어서, rootless Docker 방식은 리눅스 머신에서 따로 해 봐야 한다.

## 3. etcd RangeStream이 API 서버에서 하는 일

etcd 3.7 정식 출시 때 RangeStream을 적었고, v1.37 릴리스 때 kube-apiserver에서 기본으로 켜진다고 적었다. 이번 글은 그게 실제로 무엇을 줄이는지 설명했다.

{{< mermaid >}}
flowchart TB
  subgraph old["예전: 키 개수로 나눈 페이지"]
    direction LR
    A1["etcd가 한 페이지(키 N개)를<br>메모리에 다 만든다"] --> A2["API 서버가 그 페이지를<br>통째로 받아 디코딩"]
    A2 --> A3["큰 오브젝트가 몰리면<br>양쪽 메모리가 한꺼번에 튐"]
  end
  subgraph new["RangeStream: 바이트 기준 조각"]
    direction LR
    B1["etcd가 값 크기를 보며<br>조각 크기를 조절해 흘려보냄"] --> B2["API 서버가 조각마다<br>디코딩하고 바로 해제"]
    B2 --> B3["양쪽 모두 전체 목록을<br>한 번에 들고 있지 않음"]
  end
  old --> new
{{< /mermaid >}}

API 서버는 대부분의 list, watch를 메모리의 watch 캐시로 처리하는데, 그 캐시를 채우려면 시작할 때와 다시 초기화할 때마다 etcd에서 리소스 전체를 읽는다. 지금까지도 페이지로 나눠 읽었지만 기준이 '키 개수'라서, 큰 파드 오브젝트가 몰린 페이지는 여전히 컸다. 키 개수는 같아도 크기는 제각각이니 메모리 사용을 예측하기 어려웠고, 동시에 여러 개가 겹치면 OOM까지 갔다고 한다.

| 알아 둘 점 | 내용 |
|---|---|
| 조건 | 쿠버네티스 v1.37 이상, etcd v3.7 이상. EtcdRangeStream은 kube-apiserver 기능 게이트이고 beta로 기본 켜짐 |
| 오래된 etcd | API 서버가 시작할 때 지원 여부를 보고, 실행 중에도 Unimplemented가 오면 예전 페이지 방식으로 알아서 돌아간다 |
| 쓰는 곳 | watch 캐시 초기화, 캐시로 처리하지 못해 etcd를 직접 읽는 list 요청 |
| 확인 | API 서버 지표 etcd_request_duration_seconds_count{operation="listStream"}이 0보다 크면 쓰고 있는 것 |
| 끄기 | --feature-gates=EtcdRangeStream=false |

## 내 클러스터에서 확인할 것

```bash
kubectl get hpa -A -o custom-columns=NS:.metadata.namespace,HPA:.metadata.name,MIN:.spec.minReplicas,METRIC:.spec.metrics[*].type
kubectl describe hpa queue-worker | sed -n '/Conditions:/,/Events:/p'
kubectl get nodes -o yaml | grep -n runningInUserNamespace
kubectl get --raw /metrics | grep 'etcd_request_duration_seconds_count{.*operation="listStream"' | head -3
```

- METRIC이 Resource뿐인 HPA는 minReplicas를 0으로 바꿀 수 없다. 큐 길이 같은 외부 지표가 있는 워크로드부터 본다.
- Conditions에 ScaledToZero가 없는데 레플리카가 0이면 누군가 손으로 멈춘 것이다. HPA가 깨워 주지 않는다.
- listStream 지표가 안 나오면 etcd가 3.7보다 오래된 것이다. 컨트롤 플레인 etcd 이미지 버전부터 본다.

> **쉬운 설명**
>
> HPA 0까지 줄이기는 손님이 없을 때 가게 불을 다 끄는 것이다. 매장 안 손님 수(CPU)로 판단하면 불을 끈 뒤엔 손님 수를 셀 수가 없으니, 가게 밖 대기 줄(큐 길이)을 보고 다시 불을 켠다. 사장님이 직접 '임시 휴업' 팻말을 건 날(사람이 0으로 만든 것)은 줄이 생겨도 멋대로 문을 열지 않는다. rootless 모드는 건물 관리인(kubelet)에게 마스터키 대신 일반 직원 카드를 주는 것이다. 관리인이 속아서 문을 열어 줘도 자기 층까지만 열린다. RangeStream은 이삿짐을 트럭 한 대에 다 싣고 한꺼번에 내리던 걸, 상자 크기를 보며 조금씩 나르고 바로바로 정리하는 방식으로 바꾼 것이다.

## 용어 정리

| 용어 | 뜻 |
|---|---|
| External 지표 | 클러스터 밖이나 파드와 무관한 값(큐 길이 등). external.metrics.k8s.io로 제공된다 |
| ScaledToZero | HPA가 직접 0으로 줄였음을 나타내는 조건 |
| 축소 안정화 창 | 지표가 내려가도 이 시간 동안은 줄이지 않는 HPA 설정. 기본 5분 |
| KubeletInUserNamespace | 노드 구성 요소를 사용자 네임스페이스 안에서 돌리는 기능 게이트(rootless 모드) |
| watch 캐시 | API 서버가 list, watch 요청을 etcd 대신 처리하려고 메모리에 들고 있는 리소스 상태 |
| listStream | API 서버 etcd 지표에서 RangeStream으로 읽은 요청에 붙는 operation 라벨 |

## 참고 자료

- Kubernetes 블로그, Scale Workloads to Zero with HorizontalPodAutoscaler: <https://kubernetes.io/blog/2026/09/02/kubernetes-v1-37-hpa-scale-to-zero-beta/>
- Kubernetes 블로그, KubeletInUserNamespace (aka Rootless mode) Graduates to Beta: <https://kubernetes.io/blog/2026/09/04/kubernetes-v1-37-rootless-beta/>
- Kubernetes 블로그, etcd RangeStream Cuts Memory Use on Large List Reads: <https://kubernetes.io/blog/2026/09/01/kubernetes-v1-37-etcd-range-stream/>
- Kubernetes 문서, HorizontalPodAutoscaler: <https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/>
- Kubernetes 문서, 노드 구성 요소를 일반 사용자로 실행하기: <https://kubernetes.io/docs/tasks/administer-cluster/kubelet-in-userns/>

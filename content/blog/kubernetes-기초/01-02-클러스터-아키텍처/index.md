---
title: '[K8s 기초] 클러스터 아키텍처: 디플로이먼트 하나가 파드가 되기까지'
date: '2024-10-19T15:40:00+09:00'
categories:
- Kubernetes
tags:
- kubernetes
- control-plane
- kube-apiserver
- etcd
- kube-scheduler
- kube-controller-manager
- kubelet
- kube-proxy
- reconciliation
- 기초 개념
series:
- Kubernetes 기초
series_order: 3
---

기초 개념 두 번째. 구성 요소 이름을 외우는 것보다, 디플로이먼트 하나를 만들었을 때 누가 어떤 순서로 움직이는지 따라가는 게 이해가 빨랐다. kind 클러스터에서 이벤트를 지켜보면서 그 순서를 직접 확인했다.

## 요약

- 클러스터는 컨트롤 플레인(두뇌)과 워커 노드(손발)로 나뉜다.
- 모든 구성 요소는 API 서버를 거쳐서만 이야기한다. etcd에 직접 읽고 쓰는 건 API 서버뿐이다.
- 컨트롤러는 '원하는 상태(spec)'와 '지금 상태(status)'를 계속 비교해서 차이를 메운다. 이걸 조정 루프(reconciliation loop)라고 한다.
- 디플로이먼트를 만들면 디플로이먼트 컨트롤러가 레플리카셋을, 레플리카셋 컨트롤러가 파드를 만들고, 스케줄러가 노드를 정하고, 그 노드의 kubelet이 컨테이너를 띄운다.
- 스케줄러는 노드만 정하고, 실제 실행은 kubelet이 컨테이너 런타임에 맡긴다.

## 1. 컨트롤 플레인과 노드

| 구성 요소 | 위치 | 하는 일 |
|---|---|---|
| kube-apiserver | 컨트롤 플레인 | 모든 요청의 입구. 인증·인가·어드미션을 거쳐 etcd에 저장한다 |
| etcd | 컨트롤 플레인 | 클러스터의 모든 상태를 저장하는 키-값 저장소 |
| kube-scheduler | 컨트롤 플레인 | 노드가 정해지지 않은 파드를 보고 어느 노드에 둘지 정한다 |
| kube-controller-manager | 컨트롤 플레인 | 디플로이먼트, 레플리카셋, 노드, 잡 등 컨트롤러 묶음. 상태를 계속 맞춘다 |
| cloud-controller-manager | 컨트롤 플레인(클라우드) | 로드 밸런서, 노드 정보 등 클라우드 API와 연결한다. kind에는 없다 |
| kubelet | 모든 노드 | 자기 노드에 배정된 파드를 런타임에 실행시키고 상태를 보고한다 |
| kube-proxy | 모든 노드 | 서비스 주소로 온 트래픽이 파드로 가도록 노드의 네트워크 규칙을 만든다 |
| 컨테이너 런타임 | 모든 노드 | containerd 등. 실제로 컨테이너를 실행한다 |
| 애드온 | 클러스터 | CoreDNS(이름 찾기), CNI 플러그인(파드 네트워크) 등 |

## 2. 디플로이먼트 하나가 파드가 되기까지

{{< mermaid >}}
sequenceDiagram
  participant U as kubectl
  participant A as API 서버
  participant E as etcd
  participant C as 컨트롤러 매니저
  participant S as 스케줄러
  participant K as kubelet (노드)
  U->>A: Deployment 생성 요청
  A->>E: 저장
  C-->>A: 지켜보다가 새 Deployment 발견
  C->>A: ReplicaSet 생성
  C->>A: Pod 2개 생성 (nodeName 비어 있음)
  S-->>A: 노드 없는 Pod 발견
  S->>A: Pod마다 노드 지정 (바인딩)
  K-->>A: 내 노드에 배정된 Pod 발견
  K->>K: containerd로 이미지 받고 컨테이너 실행
  K->>A: Pod 상태 보고 (Running, Ready)
{{< /mermaid >}}

그림에서 점선 화살표는 '지켜보다가(watch) 알아챈다'는 뜻이다. 누가 누구를 직접 부르지 않는다. 다들 API 서버에 있는 상태를 지켜보다가 자기 일이 생기면 처리하고, 결과를 다시 API 서버에 쓴다. 덕분에 구성 요소 하나가 잠깐 멈췄다가 돌아와도 상태를 다시 읽고 이어서 일한다.

kind에서 이벤트를 지켜보면서 디플로이먼트를 만들어 봤다.

```bash
kubectl get events -w                     # 터미널 1
kubectl create deployment web --image=nginx:1.27 --replicas=2   # 터미널 2
```

| 이벤트 이유 | 보낸 쪽 | 뜻 |
|---|---|---|
| ScalingReplicaSet | deployment-controller | 레플리카셋 web-xxxx를 2개로 늘렸다 |
| SuccessfulCreate | replicaset-controller | 파드 web-xxxx-yyyy를 만들었다(2번) |
| Scheduled | default-scheduler | 파드를 study-worker(또는 study-worker2)에 배정했다 |
| Pulling, Pulled | kubelet | 이미지를 받았다 |
| Created, Started | kubelet | 컨테이너를 만들고 시작했다 |

그림의 순서와 이벤트 순서가 그대로 맞았다.

## 3. kind에서 구성 요소 직접 보기

```bash
kubectl get pods -n kube-system -o wide
```

열은 이름, 준비 상태, 상태, 노드만 남기고 이름 뒤 해시는 x로 줄였다.

```
NAME                                          READY   STATUS    NODE
coredns-xxxxxxxxxx-xxxxx                      1/1     Running   study-control-plane
coredns-xxxxxxxxxx-xxxxx                      1/1     Running   study-control-plane
etcd-study-control-plane                      1/1     Running   study-control-plane
kindnet-xxxxx                                 1/1     Running   study-control-plane
kindnet-xxxxx                                 1/1     Running   study-worker
kindnet-xxxxx                                 1/1     Running   study-worker2
kube-apiserver-study-control-plane            1/1     Running   study-control-plane
kube-controller-manager-study-control-plane   1/1     Running   study-control-plane
kube-proxy-xxxxx                              1/1     Running   study-control-plane
kube-proxy-xxxxx                              1/1     Running   study-worker
kube-proxy-xxxxx                              1/1     Running   study-worker2
kube-scheduler-study-control-plane            1/1     Running   study-control-plane
```

이름 뒤에 노드 이름이 붙은 네 개(etcd, apiserver, controller-manager, scheduler)는 스태틱 파드다. API 서버가 만든 게 아니라, 컨트롤 플레인 노드의 kubelet이 디렉터리에 있는 YAML을 보고 직접 띄운다. kindnet은 kind의 기본 CNI 플러그인이다.

```bash
docker exec study-control-plane ls /etc/kubernetes/manifests
# etcd.yaml  kube-apiserver.yaml  kube-controller-manager.yaml  kube-scheduler.yaml
docker exec study-worker systemctl is-active kubelet   # active. kubelet은 파드가 아니라 노드의 서비스다
kubectl get --raw='/readyz?verbose' | tail -3          # API 서버 상태 점검 항목
```

## 4. 하나가 멈추면 무슨 일이 생기나

| 멈춘 것 | 생기는 일 |
|---|---|
| kube-apiserver | kubectl이 안 된다. 이미 떠 있는 파드는 그대로 돈다 |
| etcd | API 서버가 상태를 읽고 쓰지 못한다. 데이터를 잃으면 클러스터 상태 전체를 잃으니 백업이 중요하다 |
| kube-scheduler | 새 파드가 노드를 못 받아 Pending에 머문다 |
| kube-controller-manager | 파드가 죽어도 다시 안 만들어지고, 복제본 수를 바꿔도 반영이 안 된다 |
| 워커의 kubelet | 노드가 NotReady가 되고, 기본으로 약 5분 뒤 그 노드의 파드가 다른 노드로 옮겨질 준비를 한다 |

> **쉬운 설명**
>
> 클러스터는 큰 식당이다. API 서버는 주문 접수 창구라서 모든 주문과 보고가 여기로만 오간다. etcd는 창구 뒤의 주문 장부다. 컨트롤러 매니저는 장부를 계속 넘겨 보며 '테이블 3번에 접시 2개여야 하는데 1개뿐이네' 하고 부족한 걸 다시 주문하는 매니저들이다. 스케줄러는 '이 요리는 2번 주방에서' 하고 배정만 하는 사람이고, 실제 요리는 각 주방(노드)의 주방장(kubelet)이 조리 기구(containerd)로 한다. 누구도 서로 직접 부르지 않고 장부만 보고 움직여서, 한 사람이 잠깐 자리를 비워도 돌아와서 장부를 보면 이어서 일할 수 있다.

## 헷갈렸던 것들

- 구성 요소끼리 직접 통신하지 않는다. 다 API 서버를 거치고, etcd에 붙는 건 API 서버뿐이다.
- 스케줄러는 파드를 실행하지 않는다. 파드의 nodeName만 정한다.
- kubelet은 파드가 아니라 노드의 시스템 서비스(systemd)다. kubectl get pods로는 안 보인다.
- 컨트롤 플레인 구성 요소가 파드로 보이는 건 kind(kubeadm 방식)가 스태틱 파드로 띄우기 때문이다. 관리형 클러스터(EKS 등)에서는 아예 안 보인다.
- 디플로이먼트가 파드를 직접 만들지 않는다. 디플로이먼트 → 레플리카셋 → 파드의 세 단계다.

## 용어 정리

| 용어 | 뜻 |
|---|---|
| 컨트롤 플레인 | 클러스터 상태를 저장하고 결정하는 구성 요소 묶음 |
| 워커 노드 | 애플리케이션 파드가 실제로 도는 서버 |
| 조정 루프 | 원하는 상태와 실제 상태를 비교해 차이를 메우는 반복 |
| watch | API 서버의 변경을 계속 받아 보는 방식 |
| 스태틱 파드 | API 서버가 아니라 kubelet이 로컬 YAML을 보고 직접 띄우는 파드 |
| 바인딩 | 스케줄러가 파드에 노드를 지정하는 것 |

## 복습 문제

**1.** kube-system의 파드 중 스태틱 파드를 골라내고, 그 YAML이 어디 있는지 확인해라.

**2.** 디플로이먼트 api(nginx:1.27, 복제본 3개)를 만들면서 이벤트를 지켜보고, 어떤 컨트롤러가 무엇을 했는지 순서대로 적어라.

**3.** 스케줄러를 잠깐 멈춘 상태에서 파드를 만들면 어떻게 되는지 kind로 확인하고 원래대로 돌려라.

## 답과 풀이

1. 스태틱 파드는 이름 끝에 노드 이름이 붙고, ownerReferences가 Node다.

```bash
kubectl get pod -n kube-system kube-scheduler-study-control-plane -o jsonpath='{.metadata.ownerReferences[0].kind}'   # Node
docker exec study-control-plane ls /etc/kubernetes/manifests
```

2. ScalingReplicaSet(deployment-controller) → SuccessfulCreate 3번(replicaset-controller) → Scheduled 3번(default-scheduler) → Pulling·Pulled·Created·Started(kubelet).

```bash
kubectl get events -w &
kubectl create deployment api --image=nginx:1.27 --replicas=3
```

3. 스태틱 파드 YAML을 디렉터리 밖으로 옮기면 kubelet이 스케줄러를 내린다. 그동안 만든 파드는 Pending이고, 되돌리면 바로 배정된다.

```bash
docker exec study-control-plane mv /etc/kubernetes/manifests/kube-scheduler.yaml /tmp/
kubectl run wait --image=nginx:1.27
kubectl get pod wait                    # Pending, NODE 없음
docker exec study-control-plane mv /tmp/kube-scheduler.yaml /etc/kubernetes/manifests/
kubectl get pod wait -w                 # 곧 Running
```

## 참고 자료

- Kubernetes 문서, 클러스터 구성 요소: <https://kubernetes.io/docs/concepts/overview/components/>
- Kubernetes 문서, 클러스터 아키텍처: <https://kubernetes.io/docs/concepts/architecture/>
- Kubernetes 문서, 컨트롤러: <https://kubernetes.io/docs/concepts/architecture/controller/>
- Kubernetes 문서, 스케줄러: <https://kubernetes.io/docs/concepts/scheduling-eviction/kube-scheduler/>
- Kubernetes 문서, 스태틱 파드: <https://kubernetes.io/docs/tasks/configure-pod-container/static-pod/>

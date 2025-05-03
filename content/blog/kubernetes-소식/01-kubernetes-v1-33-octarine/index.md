---
title: '[K8s 소식] Kubernetes v1.33 Octarine: 사이드카 정식, in-place 리사이즈 beta, Endpoints 지원 중단'
date: '2025-05-03T15:00:00+09:00'
categories:
- Kubernetes
tags:
- kubernetes
- release
- v1.33
- sidecar
- in-place-resize
- endpointslice
- user-namespaces
- kuberc
- nftables
- 소식
series:
- Kubernetes 소식
series_order: 1
---

4월 23일에 Kubernetes v1.33 Octarine이 나왔다. 3월에 CKA와 CKAD를 v1.32로 봤는데 벌써 한 버전이 올라갔다. 시험 공부하면서 외운 것 중에 무엇이 바뀌었는지 위주로 릴리스 글과 관련 글 두 편을 읽고 정리했다.

## 요약

- 기능 개선 64개다. 18개가 stable, 20개가 beta, 24개가 alpha가 됐고, 2개는 지원 중단되거나 철회됐다.
- 사이드카 컨테이너(restartPolicy: Always인 init 컨테이너)가 stable이 됐다. CKAD 때 beta로 공부한 그 기능이다.
- 파드를 재시작하지 않고 CPU·메모리를 바꾸는 in-place 리사이즈가 beta가 됐다. v1.27에 alpha로 들어온 기능이다.
- Endpoints API가 공식적으로 지원 중단됐다. 읽거나 쓰면 경고가 나오고, EndpointSlice를 쓰라고 한다.
- 사용자 네임스페이스 지원이 기본으로 켜졌다. 파드에 hostUsers: false를 주면 컨테이너의 root가 노드에서는 일반 사용자로 매핑된다.

## 1. 눈에 띈 변화

| 기능 | 단계 | 한 줄 정리 |
|---|---|---|
| 사이드카 컨테이너 | stable | 메인 컨테이너보다 먼저 시작하고, 끝까지 돌고, 메인이 끝나면 알아서 종료된다 |
| in-place 파드 리사이즈 | beta | 실행 중인 파드의 resources를 바꿔도 파드를 다시 만들지 않는다 |
| kubectl .kuberc | alpha | 별칭, 기본 옵션 같은 개인 설정을 kubeconfig와 분리한다. KUBECTL_KUBERC=true로 켠다 |
| kube-proxy nftables 백엔드 | stable | 성능이 좋아졌지만 호환성 때문에 리눅스 기본값은 여전히 iptables다 |
| trafficDistribution: PreferClose | stable | 서비스 트래픽을 가까운(같은 존) 엔드포인트로 먼저 보낸다 |
| 여러 Service CIDR | stable | 서비스 IP 대역을 나중에 늘릴 수 있다 |
| 인덱스별 backoffLimit, Job 성공 정책 | stable | 인덱스 잡에서 인덱스마다 재시도 횟수와 성공 조건을 정한다 |
| 사용자 네임스페이스 | beta, 기본 켜짐 | hostUsers: false인 파드에 적용된다 |
| 이미지를 볼륨으로 마운트 | beta | OCI 이미지를 읽기 전용 볼륨으로 붙인다 |

사이드카는 v1.29부터 beta로 기본 켜져 있어서 실제로 쓰는 방법은 그대로다. stable이 됐다는 건 이제 바뀌지 않는다고 믿고 써도 된다는 뜻이다.

in-place 리사이즈는 지금까지 '파드의 resources는 바꿀 수 없고, 바꾸려면 파드를 다시 만든다'고 외웠던 부분을 바꾼다. 상태가 있는 프로세스를 끊지 않고 늘리거나, 기동할 때만 크게 줬다가 나중에 줄이는 식으로 쓸 수 있다고 한다. 실제로 써 보는 건 beta 상세 글이 나오면 따로 정리하기로 했다.

## 2. 지원 중단과 제거

| 항목 | 내용 |
|---|---|
| Endpoints API 지원 중단 | EndpointSlice가 v1.21에 GA된 뒤로 사실상 대체됐다. 듀얼 스택이나 trafficDistribution 같은 새 기능은 EndpointSlice에만 있다 |
| 노드 상태의 kubeProxyVersion 필드 제거 | v1.31에 지원 중단, v1.33에 제거 |
| 트리 안 gitRepo 볼륨 드라이버 제거 | v1.11부터 지원 중단이었고, 노드에서 root로 코드 실행이 가능한 보안 문제가 있었다. 기능 게이트로 세 버전 동안 다시 켤 수 있고, v1.39에 완전히 없앨 예정 |
| 윈도우 파드의 host network 지원 제거 | alpha였던 기능을 철회했다. HostProcess 컨테이너는 그대로다 |

Endpoints 지원 중단은 내가 쓰는 명령에도 바로 걸린다. 서비스가 안 붙을 때 kubectl get endpoints를 습관처럼 쳤는데, 이제 이렇게 경고가 나온다(공식 글의 예).

```
$ kubectl get endpoints myservice
Warning: v1 Endpoints is deprecated in v1.33+; use discovery.k8s.io/v1 EndpointSlice
NAME        ENDPOINTS         AGE
myservice   10.180.3.17:443   1h
```

공식 글에 따르면 지원 중단 정책상 Endpoints 타입 자체가 완전히 없어지지는 않을 것 같지만, 장기적으로는 적합성(Conformance) 기준에서 Endpoints 컨트롤러를 빼는 게 목표라고 한다. 서비스 하나에 Endpoints는 하나지만 EndpointSlice는 여러 개일 수 있다는 점이 스크립트를 고칠 때 가장 큰 차이다.

## 내 클러스터에서 확인할 것

```bash
kubectl get endpointslices -l kubernetes.io/service-name=web     # 습관을 이걸로 바꾼다
kubectl get pods -A -o json | grep -c '"gitRepo"'                   # gitRepo 볼륨을 쓰는 파드가 있나
kubectl get nodes -o jsonpath='{.items[*].status.nodeInfo.kubeProxyVersion}'   # 이 필드에 기대는 도구가 있나
```

- 모니터링이나 스크립트가 Endpoints API를 읽는다면 EndpointSlice로 옮긴다.
- gitRepo 볼륨을 쓰고 있으면 git-sync 사이드카나 init 컨테이너로 바꾼다.
- 사용자 네임스페이스는 노드 커널과 파일시스템이 idmap 마운트를 지원해야 한다. 쓰기 전에 노드 커널 버전부터 확인한다.

> **쉬운 설명**
>
> 쿠버네티스는 넉 달마다 새 판이 나오는 교과서다. 이번 판에서 '부록'이던 사이드카 장(章)이 본문으로 올라왔고(stable), '옷을 갈아입으려면 집을 새로 지어야 한다'던 내용이 '방에서 옷만 갈아입어도 된다'로 바뀌는 중이다(in-place 리사이즈 beta). 옛날 주소록(Endpoints)은 '이제 새 주소록(EndpointSlice)을 쓰세요'라는 스티커가 붙었다. 당장 버리지는 않지만, 새로 생기는 정보는 새 주소록에만 적힌다.

## 용어 정리

| 용어 | 뜻 |
|---|---|
| KEP | Kubernetes Enhancement Proposal. 기능 하나의 제안·설계 문서 |
| alpha, beta, stable | 기능의 성숙 단계. beta부터 대부분 기본으로 켜지고, stable은 바뀌지 않는다 |
| 지원 중단(deprecation) | 앞으로 없앨 예정이라 경고를 내는 상태 |
| in-place 리사이즈 | 파드를 다시 만들지 않고 컨테이너 resources를 바꾸는 기능 |
| 사용자 네임스페이스 | 컨테이너 안의 uid를 노드의 다른 uid로 매핑하는 리눅스 기능 |

## 참고 자료

- Kubernetes 블로그, v1.33 Octarine: <https://kubernetes.io/blog/2025/04/23/kubernetes-v1-33-release/>
- Kubernetes 블로그, Endpoints에서 EndpointSlice로: <https://kubernetes.io/blog/2025/04/24/endpoints-deprecation/>
- Kubernetes 블로그, 사용자 네임스페이스 기본 켜짐: <https://kubernetes.io/blog/2025/04/25/userns-enabled-by-default/>
- Kubernetes 문서, 사이드카 컨테이너: <https://kubernetes.io/docs/concepts/workloads/pods/sidecar-containers/>

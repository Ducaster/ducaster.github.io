---
title: '[K8s 소식] in-place 파드 리사이즈 beta 써 보기, 이미지 풀 정책 보안 수정, etcd v3.6.0'
date: '2025-05-24T16:00:00+09:00'
categories:
- Kubernetes
tags:
- kubernetes
- v1.33
- in-place-resize
- resize-subresource
- imagepullpolicy
- etcd
- etcdutl
- kind
- 소식
series:
- Kubernetes 소식
series_order: 2
---

v1.33 후속 글들이 이어서 나왔다. 그중 세 가지를 골랐다. 지난번에 '상세 글이 나오면 써 보겠다'고 한 in-place 리사이즈 beta, 10년 묵은 이미지 풀 정책 보안 문제의 수정, 그리고 CKA 때 외운 백업·복구 명령을 바꾸는 etcd v3.6.0이다. 5월 16일에 나온 kind v0.28.0의 기본 노드가 v1.33.1이라 리사이즈는 직접 해 봤다.

## 요약

- in-place 리사이즈는 v1.33에서 beta가 되면서 기본으로 켜졌다. 리소스는 파드의 resize 서브리소스로만 바꿀 수 있고, kubectl v1.32 이상이 필요하다.
- spec의 resources는 '원하는 값', status.containerStatuses[].resources는 '실제 적용된 값'이 됐다. 진행 상황은 PodResizePending, PodResizeInProgress 조건으로 본다.
- imagePullPolicy: IfNotPresent일 때 다른 파드가 받아 둔 비공개 이미지를 자격 증명 없이 쓸 수 있던 문제를 고치는 기능이 v1.33에 alpha로 들어왔다(KubeletEnsureSecretPulledImages).
- etcd v3.6.0은 3.5 이후 4년 만의 마이너 릴리스다. 평균 메모리를 50% 이상 줄였고, etcdctl snapshot restore·status가 빠져 etcdutl로 옮겨 갔다.
- etcd 3.5에서 3.6으로 올리려면 먼저 3.5.20 이상으로 올려야 한다.

## 1. in-place 리사이즈 써 보기

{{< mermaid >}}
flowchart TB
  U["kubectl patch<br>--subresource resize"] --> S["spec.containers[].resources<br>(원하는 값)"]
  S --> K["kubelet이<br>cgroup 값 변경"]
  K --> T["status.containerStatuses[].resources<br>(실제 값)"]
  K -.->|"바로 못 하면"| P["조건 PodResizePending<br>(Deferred 또는 Infeasible)"]
  K -.->|"적용 중"| I["조건 PodResizeInProgress"]
{{< /mermaid >}}

```bash
kind create cluster --name resize        # kind v0.28.0 → 노드 v1.33.1
kubectl run rz --image=nginx:1.27 --overrides='{"spec":{"containers":[{"name":"rz","image":"nginx:1.27","resources":{"requests":{"cpu":"100m","memory":"64Mi"},"limits":{"cpu":"200m","memory":"128Mi"}}}]}}'
kubectl patch pod rz --subresource resize --patch \
  '{"spec":{"containers":[{"name":"rz","resources":{"requests":{"cpu":"300m"},"limits":{"cpu":"500m"}}}]}}'
kubectl get pod rz -o jsonpath='{.status.containerStatuses[0].resources}{"\n"}'   # cpu 300m / 500m
kubectl get pod rz -o jsonpath='{.status.containerStatuses[0].restartCount}{"\n"}' # 0
```

파드 이름도 IP도 그대로이고 재시작 횟수도 0이었다. 시험 공부할 때 '실행 중인 파드의 resources는 못 바꾼다, replace --force로 다시 만든다'고 외웠는데, 이제는 그게 정답이 아니게 됐다. 다만 --subresource resize 없이 그냥 kubectl edit이나 patch를 하면 예전처럼 거절된다.

| 알아 둘 점 | 내용 |
|---|---|
| 바꿀 수 있는 것 | CPU와 메모리의 requests·limits |
| 재시작 여부 | 컨테이너의 resizePolicy로 정한다. 기본은 NotRequired(재시작 없이), RestartContainer도 고를 수 있다 |
| 아직 안 되는 것 | 메모리 limit 줄이기 등 제약이 있고, beta에서 풀어 가는 중이라고 한다 |
| 사이드카 | 사이드카 컨테이너도 리사이즈된다 |
| 디플로이먼트 템플릿 | 템플릿의 resources를 바꾸면 예전처럼 새 파드로 교체된다. in-place는 파드에 직접 하는 것이다 |
| 다음 계획 | VPA에 InPlaceOrRecreate 모드를 넣어, 먼저 in-place로 시도하고 안 되면 다시 만드는 방식을 준비 중 |

## 2. 이미지 풀 정책의 오래된 구멍

10년 동안 열려 있던 이슈(#18787)라고 해서 놀랐다. 상황은 이렇다.

| 순서 | 일어나는 일 |
|---|---|
| 1 | 네임스페이스 X의 파드 A가 imagePullSecrets로 비공개 이미지 Foo를 노드 1에 받는다 |
| 2 | 네임스페이스 Y의 파드 B가 같은 노드에 오고, 같은 이미지를 IfNotPresent로 쓴다. 자격 증명은 없다 |
| 3 | 예전: 노드에 이미지가 있으니 kubelet이 그냥 실행해 준다. 권한 없는 파드가 비공개 이미지를 쓴다 |
| 4 | v1.33 alpha: kubelet이 '이 이미지를 받을 때 쓴 자격 증명'을 기록해 두고, 파드 B가 같은 자격 증명(또는 같은 Secret)을 주지 않으면 레지스트리에 다시 확인한다 |

그동안은 이걸 막으려고 어드미션으로 모든 파드에 imagePullPolicy: Always를 강제하는 방법을 썼다고 한다. 그러면 파드가 뜰 때마다 레지스트리가 살아 있어야 해서 레지스트리 장애가 곧 배포 장애가 된다. 새 기능은 노드에 성공한 풀 기록을 파일로 남겨, 같은 자격 증명이면 다시 확인하지 않는다. v1.33에서는 kubelet의 KubeletEnsureSecretPulledImages 기능 게이트를 켜야 동작한다.

## 3. etcd v3.6.0

| 항목 | 내용 |
|---|---|
| 의미 | 2021년 6월 v3.5.0 이후 첫 마이너 릴리스. etcd가 쿠버네티스의 SIG(sig-etcd)가 됐다 |
| 메모리 | 평균 사용량을 50% 이상 줄였다. --snapshot-count 기본값이 100,000에서 10,000으로 바뀌었다 |
| 처리량 | 읽기·쓰기가 평균 약 10% 빨라졌다 |
| 다운그레이드 | 처음으로 공식 지원. etcdctl downgrade validate, enable 후 순차 다운그레이드 |
| 기능 게이트 | --experimental 접두어 대신 쿠버네티스식 기능 게이트를 쓴다 |
| v2store | --enable-v2가 없어지고 멤버십 정보도 v3store가 기준이 됐다 |

CKA 공부할 때 가장 신경 쓴 게 etcd 백업과 복구였는데, 명령이 바뀌었다.

| 하던 일 | 3.5까지 | 3.6부터 |
|---|---|---|
| 스냅샷 저장 | etcdctl snapshot save | 그대로(온라인 작업) |
| 스냅샷 상태 확인 | etcdctl snapshot status | etcdutl snapshot status |
| 스냅샷 복구 | etcdctl snapshot restore | etcdutl snapshot restore |
| 오프라인 조각 모음 | etcdctl defrag --data-dir | etcdutl defrag --data-dir |

정리하면 etcdctl은 네트워크로 살아 있는 etcd와 이야기하는 도구, etcdutl은 데이터 파일을 직접 다루는 오프라인 도구로 경계가 분명해졌다. 3.5에서도 etcdutl로 복구하는 게 권장이었으니 습관을 그쪽으로 굳히면 된다.

또 하나, 피어 엔드포인트(2380)가 클라이언트 요청을 더는 받지 않는다. 3.4와 3.5에서는 실수로 받아 주던 것이라 잘못 연결해 둔 설정이 있으면 3.6에서 깨진다.

## 내 클러스터에서 확인할 것

```bash
kubectl version --client          # resize 서브리소스에는 kubectl v1.32 이상
kubectl get pods -A -o jsonpath='{range .items[*]}{.spec.containers[*].imagePullPolicy}{"\n"}{end}' | sort | uniq -c
etcdctl version                   # 3.5.20 미만이면 3.6으로 바로 올리지 말고 3.5.20 이상부터
```

- 백업·복구 스크립트에 etcdctl snapshot restore가 있으면 etcdutl로 바꾼다.
- etcd 클라이언트 설정이 2380(피어 포트)을 가리키고 있지 않은지 본다.
- 비공개 이미지를 여러 네임스페이스가 같은 노드에서 쓰는 클러스터라면 KubeletEnsureSecretPulledImages가 beta가 될 때를 지켜본다.

> **쉬운 설명**
>
> in-place 리사이즈는 이사 가지 않고 방을 넓히는 리모델링이다. 예전에는 더 큰 방이 필요하면 짐을 싸서 새 집(새 파드)으로 이사해야 했다. 이미지 풀 정책 문제는 공용 사물함에 비유할 수 있다. 누군가 비밀번호로 사물함(노드)에 물건(비공개 이미지)을 넣어 두면, 예전에는 비밀번호를 모르는 사람도 그 물건을 꺼내 쓸 수 있었다. 이제는 넣을 때 쓴 비밀번호를 적어 두고 확인한다. etcd 3.6은 장부 보관소의 새 규칙이라, 장부를 복원하는 일은 창구(etcdctl)가 아니라 금고실 직원(etcdutl)만 한다.

## 용어 정리

| 용어 | 뜻 |
|---|---|
| resize 서브리소스 | 파드의 resources만 바꾸는 전용 API 경로 |
| resizePolicy | 리소스를 바꿀 때 컨테이너를 재시작할지 정하는 필드 |
| VPA | Vertical Pod Autoscaler. 파드의 requests·limits를 사용량에 맞춰 바꿔 주는 도구 |
| etcdutl | etcd 데이터 파일을 직접 다루는 오프라인 도구 |
| 피어 엔드포인트 | etcd 멤버끼리 통신하는 주소(보통 2380) |

## 참고 자료

- Kubernetes 블로그, in-place 파드 리사이즈 beta: <https://kubernetes.io/blog/2025/05/16/kubernetes-v1-33-in-place-pod-resize-beta/>
- Kubernetes 문서, 컨테이너 CPU·메모리 리사이즈: <https://kubernetes.io/docs/tasks/configure-pod-container/resize-container-resources/>
- Kubernetes 블로그, 이미지 풀 정책: <https://kubernetes.io/blog/2025/05/12/kubernetes-v1-33-ensure-secret-pulled-images-alpha/>
- Kubernetes 블로그, etcd v3.6.0 발표: <https://kubernetes.io/blog/2025/05/15/announcing-etcd-3.6/>
- etcd 문서, v3.5에서 v3.6으로 업그레이드: <https://etcd.io/docs/v3.6/upgrades/upgrade_3_6/>
- kind v0.28.0 릴리스: <https://github.com/kubernetes-sigs/kind/releases/tag/v0.28.0>

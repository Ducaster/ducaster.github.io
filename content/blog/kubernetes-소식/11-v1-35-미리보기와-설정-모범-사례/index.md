---
title: '[K8s 소식] v1.35 미리보기(cgroup v1 제거, ipvs 지원 중단)와 설정 모범 사례'
date: '2025-12-06T15:00:00+09:00'
categories:
- Kubernetes
tags:
- kubernetes
- v1.35
- cgroup-v2
- kube-proxy
- ipvs
- nftables
- containerd
- configuration
- labels
- yaml
- 소식
series:
- Kubernetes 소식
series_order: 11
---

v1.35가 12월 17일에 나올 예정이라 미리보기 글이 올라왔다. 이번엔 빠지는 것이 굵직하다. cgroup v1 지원이 아예 빠지고, kube-proxy의 ipvs 모드가 지원 중단되고, containerd 1.x를 지원하는 마지막 버전이 된다. 하루 전에는 '설정 모범 사례' 글도 올라왔는데, 아는 내용 사이에 처음 보는 습관이 몇 개 섞여 있어서 같이 정리했다.

## 요약

- v1.35에서 cgroup v1 지원이 빠진다. cgroup v2를 못 쓰는 오래된 리눅스 노드에서는 kubelet이 아예 시작하지 않는다.
- kube-proxy의 ipvs 모드가 지원 중단된다. 리눅스 노드의 권장 모드는 이미 nftables다.
- v1.35는 containerd 1.x(1.7 등)를 지원하는 마지막 버전이다. 다음 버전으로 올리기 전에 containerd 2.0 이상으로 바꿔야 한다. kubelet_cri_losing_support 지표로 확인할 수 있다.
- 기능 쪽은 in-place 파드 리소스 변경 GA, 파드 인증서 beta, 노드가 지원 기능을 알리는 declaredFeatures(alpha), 숫자 비교 테인트(Gt, Lt) 등이 예정돼 있다. 확정은 아니다.
- 설정 모범 사례 글에서 새로 안 것은 세 가지다. YAML의 yes, no, on, off는 불리언이 될 수 있어서 따옴표를 쳐야 하고, kubernetes.io/description 어노테이션은 API에 남는 주석이고, 라벨을 떼면 파드를 컨트롤러에서 떼어 내 격리할 수 있다.

## 1. v1.35에서 빠지는 것

| 변경 | 영향 | 해야 할 일 |
|---|---|---|
| cgroup v1 지원 제거 | cgroup v2를 지원하지 않는 오래된 배포판 노드에서 kubelet이 시작하지 않는다 | 노드를 cgroup v2가 켜진 OS로 옮긴다. v2는 v1.25부터 stable이었다 |
| kube-proxy ipvs 모드 지원 중단 | 당장 빠지지는 않지만 지원 중단 경고 대상이다. 다른 모드와 기능을 맞추기 어려워 기술 부채가 됐다고 한다 | 리눅스 노드는 nftables 모드로 옮길 계획을 세운다 |
| containerd 1.x 지원 마지막 | v1.35까지는 containerd 1.7 같은 LTS가 되지만 다음 버전부터는 안 된다 | 쿠버네티스를 다음 버전으로 올리기 전에 containerd 2.0 이상으로 바꾼다 |

CKA 공부 때 kube-proxy 모드를 iptables와 ipvs 두 가지로 외웠는데, 1년도 안 돼서 ipvs가 지원 중단 목록에 올라왔다. 내 kind 클러스터는 kube-proxy 기본값(iptables)이었으니 직접 영향은 없다. 기초 공부 때 정리한 표에도 ipvs를 '서비스가 아주 많을 때 쓰던 방식'이라고 적어 두긴 했는데, 지원 중단까지 갈 줄은 몰랐다.

## 2. 들어올 예정인 기능

| 기능 | 목표 단계 | 내용 |
|---|---|---|
| in-place 파드 리소스 변경 | GA | 재시작 없이 CPU와 메모리 requests, limits를 바꾼다. v1.27 alpha, v1.33 beta |
| 파드 인증서 | beta | kubelet이 파드용 짧은 수명 인증서를 받아 projected volume으로 넣어 준다. 파드끼리 mTLS를 SPIFFE/SPIRE나 cert-manager 없이 할 수 있다 |
| 노드 선언 기능(declaredFeatures) | alpha | 노드가 지원하는 기능을 .status.declaredFeatures에 적는다. 업그레이드 중 버전이 섞일 때 맞지 않는 노드로 파드가 가는 걸 막는다 |
| 숫자 테인트 비교 | 글에 단계 표시 없음 | 톨러레이션에 Gt, Lt 연산자. 예를 들어 SLA 값이 950보다 큰 노드에만 간다. NoExecute와 같이 쓰면 값이 떨어질 때 축출도 된다 |
| User Namespaces | beta 계속 | 컨테이너 안의 root(UID 0)를 노드에서는 권한 없는 높은 UID로 매핑한다 |
| OCI 이미지 볼륨 | beta, 기본 켜짐 예정 | 레지스트리의 OCI 아티팩트를 볼륨으로 마운트한다. 데이터나 ML 모델을 이미지와 따로 배포할 수 있다 |

in-place 리사이즈는 5월에 beta 글을 정리할 때 직접 kind에서 해 봤던 기능이라 GA가 반가웠다. 정식 릴리스가 나오면 바뀐 점을 다시 확인할 생각이다.

## 3. 설정 모범 사례에서 건진 것

글의 습관들을 내 기준으로 다시 묶었다.

| 습관 | 내용 |
|---|---|
| 최신 안정 API 버전 | kubectl api-resources로 확인하고 쓴다 |
| 매니페스트는 Git에 | 내 컴퓨터에서 바로 apply하지 않는다. 롤백과 비교가 쉬워진다 |
| 최소한만 적기 | 쿠버네티스가 알아서 넣는 기본값은 굳이 쓰지 않는다 |
| 관련 오브젝트는 한 파일에 | Deployment, Service, ConfigMap을 한 파일로 두고 디렉터리째 apply한다(--server-side 권장) |
| 맨 파드 쓰지 않기 | 컨트롤러 없는 파드는 노드가 죽으면 같이 사라진다. 계속 돌 앱은 Deployment, 끝나야 할 일은 Job |
| 서비스를 먼저 만들기 | 파드가 뜰 때 이미 있는 서비스만 FOO_SERVICE_HOST 같은 환경 변수로 들어간다. DNS로 찾으면 상관없다 |
| hostPort, hostNetwork 피하기 | 파드가 노드에 묶여 스케줄이 어려워진다. 테스트는 port-forward, 외부 노출은 NodePort 서비스로 |
| 의미 있는 라벨 | app.kubernetes.io/name, tier, phase처럼 무엇인지를 적고, 셀렉터로 묶어서 조회하고 지운다 |

### YAML 불리언 함정

on, off, yes, no는 YAML 버전에 따라 불리언으로 읽힌다. 진짜 그런지 ConfigMap으로 확인해 봤다.

```yaml
data:
  FEATURE_X: yes      # 따옴표가 없어서 불리언 true로 읽힌다
  DEBUG: "on"         # 따옴표가 있어서 문자열
```

이 ConfigMap을 kubeconform(v1.34 스키마)으로 검사하니 이렇게 나왔다.

```text
ConfigMap flags is invalid: ... '/data/FEATURE_X' does not validate with ...
#/properties/data/additionalProperties/type: expected string or null, but got boolean
```

ConfigMap의 data 값은 문자열이어야 하는데 yes가 불리언이 돼 버린 것이다. 환경 변수나 플래그 값으로 yes, no, on, off를 쓸 때는 따옴표를 치는 게 맞다.

### kubernetes.io/description 어노테이션

YAML의 # 주석은 apply하면 사라진다. kubernetes.io/description 어노테이션에 적으면 API에 그대로 남아서, 매니페스트를 안 본 사람도 kubectl describe로 이 리소스가 왜 있는지 볼 수 있다. 지난번 실수 7가지 글의 owner 라벨과 같이 쓰면 좋겠다.

```yaml
metadata:
  name: web
  labels:
    app.kubernetes.io/name: web
    owner: me
  annotations:
    kubernetes.io/description: "블로그 실습용 nginx. 12월 말에 지운다"
```

### 라벨을 떼서 파드 격리하기

이번 글에서 제일 쓸모 있어 보인 요령이다. 컨트롤러는 라벨 셀렉터로 자기 파드를 찾으니, 이상한 파드 하나에서 라벨을 떼면 컨트롤러가 그 파드를 놓아주고 새 파드를 하나 더 만든다. 서비스 셀렉터도 같은 라벨이라 트래픽도 끊긴다. 남은 파드는 로그를 보고 exec로 들어가 살펴본 뒤 직접 지운다.

{{< mermaid >}}
flowchart LR
  subgraph before["떼기 전"]
    direction TB
    RS1["ReplicaSet web<br>selector app=web<br>원하는 수 3"] --> P1["web-a<br>app=web"]
    RS1 --> P2["web-b<br>app=web"]
    RS1 --> P3["web-c<br>app=web<br>(이상함)"]
  end
  subgraph after["kubectl label pod web-c app- 뒤"]
    direction TB
    RS2["ReplicaSet web<br>2개만 보인다"] --> Q1["web-a"]
    RS2 --> Q2["web-b"]
    RS2 -->|"새로 만든다"| Q4["web-d<br>app=web"]
    Q3["web-c<br>라벨 없음, 주인 없음<br>서비스 트래픽도 끊김"]
  end
  before --> after
{{< /mermaid >}}

```bash
kubectl label pod web-c app-                       # 키 뒤에 -를 붙이면 그 라벨을 지운다
kubectl get pods -L app                            # web-c의 APP 칸이 비고 web-d가 새로 생긴다
kubectl logs web-c; kubectl exec -it web-c -- sh   # 살펴보기
kubectl delete pod web-c                           # 다 봤으면 직접 지운다
```

기초 공부 때 레플리카셋이 ownerReferences로 파드를 잡고 있다고 정리했는데, 라벨이 안 맞으면 컨트롤러가 그 연결을 풀어 버린다. 그 성질을 디버깅에 쓰는 셈이다.

## 내 클러스터에서 확인할 것

```bash
stat -fc %T /sys/fs/cgroup/          # 노드에서. cgroup2fs면 v2, tmpfs면 v1
kubectl get nodes -o wide            # CONTAINER-RUNTIME 칸에서 containerd 버전
kubectl -n kube-system get cm kube-proxy -o jsonpath='{.data.config\.conf}' | grep '^mode'
kubectl get pods -A -o custom-columns=NS:.metadata.namespace,POD:.metadata.name,OWNER:.metadata.ownerReferences[0].kind | grep '<none>'
```

- cgroup v1 노드가 있으면 v1.35로 올리기 전에 OS부터 바꾼다.
- containerd가 1.x면 v1.35 다음 버전으로 가기 전에 2.0 이상으로 바꾼다. kubelet_cri_losing_support 지표로도 볼 수 있다고 한다.
- kube-proxy mode가 ipvs면 nftables로 옮길 계획을 세운다. 빈 값이면 리눅스에서 iptables다.
- 마지막 명령에 나오는 파드는 주인이 없는 맨 파드다. 스태틱 파드는 주인이 Node라 여기 안 나온다.

> **쉬운 설명**
>
> v1.35는 이사를 앞두고 오래된 짐을 정리하는 버전이다. cgroup v1은 오래된 전기 배선 같은 것이라, 새 집(v1.35)에서는 아예 꽂을 콘센트가 없다. ipvs는 쓸 수는 있지만 '곧 버릴 가구' 딱지가 붙었고, containerd 1.x는 이번 집까지만 데려갈 수 있다. 설정 모범 사례의 라벨 떼기 요령은 반 아이들 이름표를 보고 출석을 부르는 선생님(컨트롤러)과 비슷하다. 아픈 아이의 이름표를 떼면 선생님은 '한 명이 없네' 하고 다른 아이를 데려오고, 이름표 없는 아이는 보건실에서 천천히 살펴볼 수 있다.

## 용어 정리

| 용어 | 뜻 |
|---|---|
| cgroup v1, v2 | 리눅스가 프로세스 묶음의 CPU, 메모리 사용을 제한하는 기능의 옛 버전과 새 버전. v2는 계층이 하나로 통일됐다 |
| kube-proxy 모드 | 서비스 규칙을 노드에 심는 방식. iptables, ipvs, nftables |
| kubelet_cri_losing_support | 곧 지원이 끊길 런타임 버전을 쓰는 노드를 알려 주는 kubelet 지표 |
| 맨 파드(naked Pod) | 디플로이먼트나 잡 같은 컨트롤러 없이 직접 만든 파드 |
| kubernetes.io/description | 리소스 설명을 적는 공식 어노테이션. API에 남는다 |
| 권장 라벨 | app.kubernetes.io/name, instance, version, component, part-of, managed-by 같은 공통 라벨 |

## 참고 자료

- Kubernetes 블로그, Kubernetes v1.35 Sneak Peek: <https://kubernetes.io/blog/2025/11/26/kubernetes-v1-35-sneak-peek/>
- Kubernetes 블로그, Kubernetes Configuration Good Practices: <https://kubernetes.io/blog/2025/11/25/configuration-good-practices/>
- Kubernetes 문서, 설정 모범 사례: <https://kubernetes.io/docs/concepts/configuration/overview/>
- Kubernetes 문서, cgroup v2: <https://kubernetes.io/docs/concepts/architecture/cgroups/>
- Kubernetes 문서, 권장 라벨: <https://kubernetes.io/docs/concepts/overview/working-with-objects/common-labels/>
- KEP-5573, cgroup v1 지원 제거: <https://github.com/kubernetes/enhancements/issues/5573>
- KEP-5495, kube-proxy ipvs 모드 지원 중단: <https://github.com/kubernetes/enhancements/issues/5495>

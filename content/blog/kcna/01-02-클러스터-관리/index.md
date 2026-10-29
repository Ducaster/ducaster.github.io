---
title: '[KCNA] 클러스터 관리: kubectl과 kubeconfig, 설치 방법, 업그레이드와 버전 차이'
date: '2026-08-11T22:10:00+09:00'
categories:
- KCNA
tags:
- kubernetes
- kcna
- kubectl
- kubeconfig
- kubeadm
- upgrade
- version-skew
- drain
- resourcequota
- limitrange
- etcd
- Kubernetes Fundamentals
series:
- KCNA
series_order: 3
---

Administration은 이번 개편에서 새로 이름이 붙은 항목이다. 설명이 없어서 범위를 짐작해야 하는데, '클러스터에 접속하고, 만들고, 올리고, 나눠 쓰는 일'로 보고 묶었다. kubectl과 kubeconfig, 클러스터를 만드는 방법, 업그레이드와 버전 차이, 노드 유지보수, 네임스페이스별 자원 제한, etcd 백업이다. CKA 때 손으로 했던 것들을 객관식 문제로 나올 법한 형태로 다시 봤다.

## 요약

- kubectl은 kubeconfig 파일의 context(클러스터 + 사용자 + 기본 네임스페이스)로 어디에 누구로 접속할지 정한다.
- 오브젝트를 다루는 방식은 세 가지다. 명령형 명령(`kubectl create`, `run`), 명령형 오브젝트 구성(`create -f`, `replace -f`), 선언형 오브젝트 구성(`apply -f`).
- 클러스터를 만드는 길은 관리형 서비스(EKS, GKE, AKS), 직접 설치(kubeadm), 학습용 도구(kind, minikube, k3s)로 나뉜다.
- 업그레이드는 컨트롤 플레인 먼저, 노드 나중이다. 마이너 버전은 하나씩만 올린다.
- kubelet과 kube-proxy는 API 서버보다 새로우면 안 되고, 세 마이너 버전 낮은 것까지 된다. kubectl은 API 서버 위아래 한 마이너다.
- 노드 작업은 cordon, drain, 작업, uncordon 순서다.
- ResourceQuota는 네임스페이스 전체 총량을, LimitRange는 컨테이너 하나의 기본값과 범위를 정한다.

## 1. kubectl과 kubeconfig

kubectl은 kubeconfig를 이 순서로 찾는다. `--kubeconfig` 플래그, `KUBECONFIG` 환경 변수(콜론으로 여러 파일을 이어 쓰면 합쳐서 읽는다), 마지막으로 `~/.kube/config`다.

```yaml
apiVersion: v1
kind: Config
clusters:                  # 어디로
- name: dev
  cluster:
    server: https://dev.example.com:6443
    certificate-authority-data: <CA 인증서 base64>
users:                     # 누구로
- name: me
  user:
    client-certificate-data: <클라이언트 인증서 base64>
    client-key-data: <클라이언트 키 base64>
contexts:                  # 둘을 묶고 기본 네임스페이스를 붙인 것
- name: dev-me
  context:
    cluster: dev
    user: me
    namespace: shop
current-context: dev-me
```

```bash
kubectl config get-contexts                        # 컨텍스트 목록
kubectl config use-context dev-me                  # 컨텍스트 바꾸기
kubectl config set-context --current --namespace=shop
kubectl get pods -o wide                           # 노드, IP까지
kubectl get deploy web -o yaml                     # 전체 오브젝트
kubectl apply -f web.yaml --dry-run=server         # 서버에서 검증만
kubectl diff -f web.yaml                           # 적용하면 무엇이 바뀌는지
```

쿠버네티스에는 '사용자' 오브젝트가 없다. kubeconfig의 users는 인증서나 토큰을 담을 뿐이고, 그 사람이 누구인지는 API 서버가 인증서의 CN이나 토큰으로 판단한다. v1.34부터는 kubeconfig와 따로 kubectl 별칭과 기본 옵션을 담는 kuberc 파일(beta)도 생겼다. kubeconfig는 '어디에 누구로', kuberc는 '내 습관'이다.

## 2. 오브젝트를 다루는 세 가지 방식

| 방식 | 예 | 특징 |
|---|---|---|
| 명령형 명령 | `kubectl create deployment web --image=nginx`, `kubectl scale`, `kubectl expose` | 빠르다. 기록이 남지 않아 다시 만들기 어렵다 |
| 명령형 오브젝트 구성 | `kubectl create -f web.yaml`, `kubectl replace -f web.yaml` | 파일로 관리한다. replace는 파일에 없는 필드를 지운다 |
| 선언형 오브젝트 구성 | `kubectl apply -f web.yaml`, `kubectl apply -f dir/` | 파일이 원하는 상태다. kubectl이 무엇을 만들고 고칠지 계산한다 |

문서는 한 오브젝트에 방식을 섞어 쓰지 말라고 한다. 예를 들어 apply로 만든 디플로이먼트를 `kubectl scale`로 바꾸면, 다음 apply 때 파일의 replicas로 되돌아간다. GitOps 도구들이 선언형을 쓰는 이유도 파일(깃)이 기준이 되기 때문이다.

apply에는 두 가지가 있다. 기본(client-side) apply는 마지막으로 적용한 내용을 `kubectl.kubernetes.io/last-applied-configuration` 어노테이션에 남겨 비교하고, `--server-side`를 주면 API 서버가 필드마다 누가 관리하는지(field manager) 기록하며 병합한다.

## 3. 클러스터를 만드는 방법

| 방법 | 예 | 누가 무엇을 관리하나 |
|---|---|---|
| 관리형 서비스 | Amazon EKS, Google GKE, Azure AKS | 컨트롤 플레인과 etcd는 클라우드가 운영한다. 나는 노드와 워크로드를 본다(노드까지 맡기는 모드도 있다) |
| 직접 설치 | kubeadm | 전부 내가 한다. kubeadm은 컨트롤 플레인을 띄우고 노드를 붙이는 일까지만 하고, CNI는 따로 설치한다 |
| 학습·개발용 | kind, minikube, k3s | kind는 컨테이너를 노드로 쓰고, minikube는 기본으로 단일 노드 클러스터를 띄우고, k3s는 가벼운 배포판이다 |

kubeadm으로 만든 클러스터는 kube-apiserver, etcd, 스케줄러, 컨트롤러 매니저가 `/etc/kubernetes/manifests`의 스태틱 파드로 돈다. 스태틱 파드는 API 서버가 아니라 그 노드의 kubelet이 파일을 보고 직접 띄우는 파드다. 고가용성 컨트롤 플레인은 보통 컨트롤 플레인 노드 3대를 로드 밸런서 뒤에 두고, etcd를 같은 노드에 두거나(stacked) 따로 둔다(external).

배포판이 쿠버네티스 API를 제대로 구현했는지는 CNCF의 적합성 프로그램(Certified Kubernetes)으로 확인한다. 적합성 테스트를 통과한 배포판과 관리형 서비스는 이 이름을 쓸 수 있다.

## 4. 업그레이드와 버전 차이

공식 버전 차이 정책을 표로 옮겼다. 기준은 kube-apiserver다.

| 구성 요소 | API 서버보다 새로워도 되나 | 낮아도 되는 범위 |
|---|---|---|
| 다른 kube-apiserver(고가용성) | 가장 새것과 가장 오래된 것이 한 마이너 안 | |
| kubelet | 안 된다 | 세 마이너까지 |
| kube-proxy | 안 된다 | 세 마이너까지. 같은 노드의 kubelet과는 위아래 세 마이너까지 |
| kube-controller-manager, kube-scheduler, cloud-controller-manager | 안 된다 | 한 마이너까지 |
| kubectl | 한 마이너 위까지 된다 | 한 마이너까지 |

API 서버가 v1.36이면 kubelet은 v1.33부터 v1.36까지 된다. v1.37 kubelet은 안 된다. 그래서 순서가 정해진다.

{{< mermaid >}}
flowchart TB
  A["1. 첫 번째 컨트롤 플레인 노드<br>kubeadm upgrade plan, kubeadm upgrade apply v1.37.x"] --> B["2. 나머지 컨트롤 플레인 노드<br>kubeadm upgrade node"]
  B --> C["3. 컨트롤 플레인 노드의 kubelet, kubectl 패키지"]
  C --> D["4. 워커 노드 하나씩<br>drain → kubeadm upgrade node → kubelet 패키지 → kubelet 재시작 → uncordon"]
{{< /mermaid >}}

마이너 버전은 건너뛸 수 없다. v1.35에서 v1.37로 가려면 v1.36을 먼저 거친다. 패치 버전(v1.36.2에서 v1.36.6)은 건너뛰어도 된다. 관리형 서비스에서는 1번과 2번을 클라우드가 대신하고, 노드 그룹 업그레이드를 내가 누른다.

## 5. 노드 유지보수

| 명령 | 하는 일 |
|---|---|
| `kubectl cordon node1` | 노드를 스케줄 불가로 표시한다. 이미 떠 있는 파드는 그대로다 |
| `kubectl drain node1 --ignore-daemonsets` | cordon하고 파드를 내보낸다(eviction). PodDisruptionBudget을 지킨다 |
| `kubectl uncordon node1` | 다시 스케줄 가능으로 되돌린다. 내보냈던 파드가 저절로 돌아오지는 않는다 |

drain은 DaemonSet 파드를 내보낼 수 없어서(어차피 다시 생긴다) `--ignore-daemonsets`가 필요하다. emptyDir를 쓰는 파드는 데이터가 사라지니 `--delete-emptydir-data`를 줘야 진행한다. 컨트롤러 없이 직접 만든 파드는 내보내면 다시 생기지 않아서 `--force`가 필요하다.

PodDisruptionBudget은 '이 앱은 자발적인 중단(drain 같은) 중에도 최소 몇 개는 살아 있어야 한다'를 적는다. 노드가 갑자기 죽는 건 막지 못한다.

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: web-pdb
  namespace: shop
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: web
```

## 6. 네임스페이스와 자원 제한

```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: team-a
  namespace: team-a
spec:
  hard:                    # 네임스페이스 전체 합계의 상한
    requests.cpu: "4"
    requests.memory: 8Gi
    limits.memory: 16Gi
    pods: "20"
---
apiVersion: v1
kind: LimitRange
metadata:
  name: defaults
  namespace: team-a
spec:
  limits:
  - type: Container        # 컨테이너 하나 기준
    defaultRequest:        # requests를 안 적으면 넣어 줄 값
      cpu: 100m
      memory: 256Mi
    default:               # limits를 안 적으면 넣어 줄 값
      memory: 512Mi
    max:
      memory: 2Gi
```

ResourceQuota에 `requests.cpu` 같은 자원 항목이 있으면, 그 네임스페이스의 파드는 해당 값을 반드시 적어야 한다. 안 적으면 생성이 거절된다. 그래서 LimitRange의 기본값을 같이 두는 경우가 많다. 둘 다 어드미션 단계에서 확인하기 때문에, 이미 떠 있는 파드에는 소급되지 않는다.

## 7. etcd 백업과 인증서

```bash
# 백업: 살아 있는 etcd에 접속해서 스냅숏을 받는다
ETCDCTL_API=3 etcdctl --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key \
  snapshot save /backup/etcd.db

# 복구: 파일을 직접 다루는 오프라인 도구 etcdutl로 새 데이터 디렉터리를 만든다
etcdutl snapshot restore /backup/etcd.db --data-dir=/var/lib/etcd-restore

# kubeadm 인증서 만료일 확인과 갱신
kubeadm certs check-expiration
kubeadm certs renew all
```

etcd v3.6부터 `etcdctl snapshot restore`는 없어지고 etcdutl로 옮겨 갔다. CKA 때 외운 명령이 바뀐 부분이다. kubeadm이 만든 인증서는 기본 1년짜리라서, 1년 안에 업그레이드를 한 번도 안 하면 만료된다. `kubeadm upgrade apply`는 인증서도 같이 갱신한다.

> **쉬운 설명**
>
> 업그레이드는 아파트 리모델링과 같다. 관리사무소(컨트롤 플레인)부터 공사하고, 세대(노드)는 한 집씩 비우고(drain) 공사한 뒤 다시 들인다(uncordon). 규정집은 관리사무소 것이 늘 가장 최신이어야 한다. 세대에 비치된 안내문(kubelet)은 세 판 전 것까지는 봐주지만, 관리사무소보다 새 판이면 안 된다. 그리고 공사는 층을 건너뛰지 않고 한 층씩 올라간다(마이너 버전 하나씩).

## 헷갈렸던 것들

- kubectl은 API 서버 위아래로 한 마이너, kubelet은 아래로만 세 마이너다.
- 마이너 버전은 건너뛰어 올릴 수 없다. 패치 버전은 건너뛰어도 된다.
- cordon은 새 파드만 막는다. 이미 떠 있는 파드를 내보내는 건 drain이다.
- uncordon해도 내보낸 파드가 원래 노드로 돌아오지 않는다.
- ResourceQuota는 네임스페이스 총량, LimitRange는 컨테이너 하나 기준이다.
- apply로 관리하는 오브젝트를 명령형으로 바꾸면 다음 apply 때 되돌아간다.
- 관리형 서비스에서는 etcd와 컨트롤 플레인을 클라우드가 운영한다.

## 용어 정리

| 용어 | 뜻 |
|---|---|
| kubeconfig | 클러스터 주소, 사용자 인증 정보, 컨텍스트를 담은 kubectl 설정 파일 |
| context | 클러스터, 사용자, 기본 네임스페이스의 묶음 |
| kubeadm | 클러스터를 만들고 노드를 붙이고 업그레이드하는 공식 도구 |
| 스태틱 파드 | API 서버를 거치지 않고 kubelet이 매니페스트 파일을 보고 띄우는 파드 |
| 버전 차이 정책 | 구성 요소끼리 몇 마이너 버전까지 달라도 되는지 정한 규칙 |
| drain | 노드를 스케줄 불가로 만들고 파드를 내보내는 작업 |
| PodDisruptionBudget | 자발적 중단 중에도 유지할 최소 파드 수 |
| ResourceQuota | 네임스페이스 전체가 쓸 수 있는 자원과 오브젝트 수의 상한 |
| LimitRange | 컨테이너나 파드 하나의 기본값과 최소·최대 범위 |
| Certified Kubernetes | CNCF 적합성 테스트를 통과한 배포판과 서비스에 주는 인증 |

## 복습 문제

**1.** The kube-apiserver in a cluster runs v1.36. Which kubelet version is NOT allowed to join the cluster?

- A. v1.33
- B. v1.34
- C. v1.36
- D. v1.37

**2.** Which command marks a node as unschedulable and evicts its Pods before maintenance?

- A. `kubectl drain`
- B. `kubectl cordon`
- C. `kubectl taint`
- D. `kubectl delete node`

**3.** A cluster runs Kubernetes v1.35, and the team wants v1.37. What is the supported upgrade path?

- A. Upgrade the worker nodes to v1.37 first, then the control plane.
- B. Upgrade the control plane directly from v1.35 to v1.37.
- C. Upgrade to v1.36 first and then to v1.37, upgrading the control plane before the nodes each time.
- D. Reinstall the cluster, because minor version upgrades are not supported.

**4.** Which kubeconfig entry combines a cluster, a user, and an optional default namespace?

- A. cluster
- B. context
- C. user
- D. preferences

**5.** The total memory requests of all Pods in a namespace must not exceed 8 GiB. Which object enforces this limit?

- A. LimitRange
- B. PodDisruptionBudget
- C. PriorityClass
- D. ResourceQuota

**6.** Which approach keeps the desired configuration in files and lets kubectl work out which changes to make?

- A. Declarative object configuration with `kubectl apply`
- B. Imperative commands such as `kubectl run`
- C. Imperative object configuration with `kubectl replace`
- D. Writing directly to etcd

**7.** In a cluster created with kubeadm, how do control plane components such as the kube-apiserver usually run?

- A. As systemd services installed from packages
- B. As a Deployment in the default namespace
- C. As static Pods that the kubelet starts from manifests in `/etc/kubernetes/manifests`
- D. As CronJobs in the kube-system namespace

## 답과 풀이

1. **D** kubelet은 API 서버보다 새로우면 안 된다. v1.33(세 마이너 아래)부터 v1.36까지 된다.
2. **A** drain은 cordon과 파드 내보내기를 함께 한다. cordon만으로는 기존 파드가 그대로 남는다.
3. **C** 마이너 버전은 하나씩, 그리고 매번 컨트롤 플레인을 먼저 올린다.
4. **B** context가 cluster와 user를 묶고 기본 네임스페이스를 붙인다.
5. **D** 네임스페이스 전체 합계는 ResourceQuota다. LimitRange는 컨테이너 하나 기준이다.
6. **A** 선언형 방식이다. replace도 파일을 쓰지만 무엇을 할지(교체)는 내가 정하는 명령형이다.
7. **C** kubeadm은 컨트롤 플레인을 스태틱 파드로 띄운다. 시스템 서비스로 도는 건 kubelet과 컨테이너 런타임이다.

## 참고 자료

- Kubernetes 문서, kubectl 개요: <https://kubernetes.io/docs/reference/kubectl/>
- Kubernetes 문서, kubeconfig로 클러스터 접근 구성하기: <https://kubernetes.io/docs/concepts/configuration/organize-cluster-access-kubeconfig/>
- Kubernetes 문서, 오브젝트 관리 방식: <https://kubernetes.io/docs/concepts/overview/working-with-objects/object-management/>
- Kubernetes, 버전 차이 정책: <https://kubernetes.io/releases/version-skew-policy/>
- Kubernetes 문서, kubeadm 클러스터 업그레이드: <https://kubernetes.io/docs/tasks/administer-cluster/kubeadm/kubeadm-upgrade/>
- Kubernetes 문서, 노드를 안전하게 drain하기: <https://kubernetes.io/docs/tasks/administer-cluster/safely-drain-node/>
- Kubernetes 문서, 스태틱 파드: <https://kubernetes.io/docs/tasks/configure-pod-container/static-pod/>
- Kubernetes 문서, 리소스 쿼터: <https://kubernetes.io/docs/concepts/policy/resource-quotas/>
- Kubernetes 문서, LimitRange: <https://kubernetes.io/docs/concepts/policy/limit-range/>
- Kubernetes 문서, etcd 운영: <https://kubernetes.io/docs/tasks/administer-cluster/configure-upgrade-etcd/>
- CNCF, Certified Kubernetes 적합성 프로그램: <https://www.cncf.io/training/certification/software-conformance/>


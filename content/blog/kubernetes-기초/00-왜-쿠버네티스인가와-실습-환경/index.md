---
title: '[K8s 기초] 왜 쿠버네티스인가, kind로 실습 클러스터 만들기'
date: '2024-10-05T15:30:00+09:00'
categories:
- Kubernetes
tags:
- kubernetes
- k8s
- kind
- kubectl
- 컨테이너 오케스트레이션
- 실습 환경
- 시작하기
series:
- Kubernetes 기초
series_order: 1
---

컨테이너는 도커로 몇 번 띄워 본 게 전부라서, 쿠버네티스를 기초부터 제대로 공부해 보기로 했다. 첫날은 쿠버네티스가 왜 필요한지 정리하고, 노트북에 kind로 노드 3개짜리 실습 클러스터를 만들었다. 기준 버전은 8월에 나온 v1.31이다.

## 요약

- 컨테이너 한두 개는 docker run으로 충분하지만, 서버 여러 대에 컨테이너 수십 개를 띄우면 배치, 재시작, 확장, 무중단 업데이트, 서로 찾기를 사람이 다 할 수 없다. 이걸 대신해 주는 게 컨테이너 오케스트레이터이고, 쿠버네티스가 사실상 표준이다.
- 쿠버네티스는 '이 상태로 만들어 줘'라고 적어 두면 계속 그 상태를 맞춰 주는 선언형 시스템이다.
- 마이너 버전은 1년에 세 번 나오고, 버전마다 패치를 약 1년 동안 받는다.
- 실습은 kind로 했다. 노드가 VM이 아니라 Docker 컨테이너라서 몇십 초 만에 만들고 지울 수 있고, 노드를 여러 개 두기도 쉽다.
- kubectl은 클러스터의 API 서버와 이야기하는 명령줄 도구다. 어느 클러스터를 볼지는 kubeconfig의 컨텍스트로 정한다.

## 1. 왜 쿠버네티스인가

컨테이너를 서버 한 대에서 몇 개 돌릴 때는 docker run과 docker compose로 충분했다. 서버가 여러 대가 되고 컨테이너가 수십 개가 되면 이런 일이 생긴다.

| 해야 하는 일 | 사람이 하면 | 쿠버네티스는 |
|---|---|---|
| 어느 서버에 띄울지 | 서버마다 남은 CPU·메모리를 보고 고른다 | 스케줄러가 자원을 보고 노드를 고른다 |
| 컨테이너가 죽으면 | 알림을 받고 다시 띄운다 | 정해 둔 개수보다 적으면 알아서 다시 만든다 |
| 손님이 몰리면 | 서버에 들어가 하나씩 더 띄운다 | 복제본 수만 바꾸면 되고, 자동 확장도 된다 |
| 새 버전 배포 | 하나씩 내리고 올리다 실수한다 | 롤링 업데이트와 롤백을 해 준다 |
| 서로 찾기 | IP를 설정 파일에 적어 둔다 | 서비스 이름으로 찾는다(IP가 바뀌어도 된다) |

쿠버네티스는 선언형이다. '웹 서버 컨테이너 3개'라고 적어 두면, 쿠버네티스가 지금 상태를 계속 보면서 3개가 아니면 맞춰 준다. 명령을 하나하나 내리는 게 아니라 원하는 상태를 적어 두는 방식이라 처음에는 낯설었다.

몇 가지 배경도 찾아봤다.

| 항목 | 내용 |
|---|---|
| 시작 | 구글이 사내 시스템 Borg를 운영한 경험을 바탕으로 2014년에 공개했다. v1.0은 2015년 7월 |
| 관리 | 2015년 CNCF가 생기면서 첫 프로젝트로 기증됐고, 2018년 CNCF 첫 졸업 프로젝트가 됐다 |
| 이름 | 그리스어로 배의 조타수라는 뜻이다. K와 s 사이 글자 8개를 줄여 K8s라고 쓴다 |
| 릴리스 | 마이너 버전이 1년에 세 번 나온다(2024년 8월 v1.31, 12월에 v1.32 예정) |
| 지원 기간 | 최근 마이너 세 개를 유지하고, 버전마다 패치를 약 1년 받는다 |

## 2. 실습 환경 고르기

로컬에서 쓸 수 있는 선택지를 비교했다.

| 도구 | 노드가 뭔가 | 장점 | 아쉬운 점 |
|---|---|---|---|
| kind | Docker 컨테이너 | 빠르다, 노드 여러 개 쉽다, 지우고 다시 만들기 쉽다 | LoadBalancer 같은 클라우드 기능은 따로 붙여야 한다 |
| minikube | VM 또는 컨테이너 | 애드온(대시보드, 인그레스 등)이 많다 | 기본이 노드 1개라 여러 노드 실습은 덜 자연스럽다 |
| k3d / k3s | 가벼운 배포판(k3s) | 아주 가볍다 | 표준 쿠버네티스와 구성 요소가 조금 다르다 |
| Docker Desktop 내장 | 단일 노드 | 체크 하나로 켠다 | 노드를 늘리거나 버전을 고르기 어렵다 |
| EKS, GKE, AKS | 클라우드 VM | 실제 운영 환경과 같다 | 돈이 든다, 컨트롤 플레인을 직접 볼 수 없다 |

kind를 골랐다. 노드가 컨테이너라 노트북 하나로 '컨트롤 플레인 1개 + 워커 2개'를 바로 만들 수 있고, 망가뜨려도 지우고 다시 만들면 끝이다. kind v0.24.0의 기본 노드 이미지가 kindest/node:v1.31.0이라 버전도 최신이다.

## 3. kind로 3노드 클러스터 만들기

노드 구성을 파일로 적었다.

```yaml
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
- role: control-plane
- role: worker
- role: worker
```

```bash
brew install kind kubectl                               # macOS. Docker Desktop은 먼저 켜 둔다
kind create cluster --name study --config kind-3node.yaml
kubectl cluster-info --context kind-study
kubectl get nodes
```

```
NAME                  STATUS   ROLES           AGE   VERSION
study-control-plane   Ready    control-plane   75s   v1.31.0
study-worker          Ready    <none>          55s   v1.31.0
study-worker2         Ready    <none>          55s   v1.31.0
```

노드가 정말 컨테이너인지 docker ps로 보면 study-control-plane, study-worker, study-worker2라는 컨테이너 세 개가 kindest/node 이미지로 떠 있다. 각 노드 컨테이너 안에서 kubelet과 containerd가 돌고, 내가 만드는 파드는 그 안의 containerd가 실행한다. 컨테이너 안에서 컨테이너가 도는 구조다.

{{< mermaid >}}
flowchart LR
  K["kubectl<br>(노트북)"] -->|"127.0.0.1:임의 포트<br>→ 6443"| CP
  subgraph D["Docker (노트북)"]
    CP["study-control-plane<br>컨테이너<br>API 서버, etcd,<br>스케줄러, 컨트롤러"]
    W1["study-worker<br>컨테이너<br>kubelet, containerd → 파드"]
    W2["study-worker2<br>컨테이너<br>kubelet, containerd → 파드"]
  end
  CP --- W1
  CP --- W2
{{< /mermaid >}}

kind는 클러스터를 만들면서 ~/.kube/config에 kind-study라는 컨텍스트를 추가하고, 그걸 현재 컨텍스트로 바꿔 둔다. 다 쓰면 kind delete cluster --name study로 지운다.

## 4. kubectl 첫걸음

| 하고 싶은 것 | 명령 |
|---|---|
| 지금 어느 클러스터를 보고 있나 | kubectl config current-context |
| 클러스터 목록과 전환 | kubectl config get-contexts, kubectl config use-context kind-study |
| 목록 보기 | kubectl get nodes, kubectl get pods -A |
| 자세히 보기(이벤트 포함) | kubectl describe pod hello |
| 파일로 만들기·고치기 | kubectl apply -f app.yaml |
| 지우기 | kubectl delete pod hello |
| 로그, 안으로 들어가기 | kubectl logs hello, kubectl exec -it hello -- sh |
| 필드 설명 | kubectl explain pod.spec.containers |

파드 하나를 띄워 보고 바로 지웠다.

```bash
kubectl run hello --image=nginx:1.27 --port=80
kubectl get pods -o wide                    # NODE 열에 study-worker나 study-worker2가 나온다
kubectl port-forward pod/hello 8080:80      # 다른 터미널에서 curl localhost:8080 → Welcome to nginx!
kubectl delete pod hello
```

kubectl을 매번 치기 귀찮아서 별칭과 자동 완성을 걸었다.

```bash
echo 'source <(kubectl completion zsh)' >> ~/.zshrc
echo 'alias k=kubectl' >> ~/.zshrc
echo 'compdef __start_kubectl k' >> ~/.zshrc
```

> **쉬운 설명**
>
> 쿠버네티스는 항구의 관제탑이다. 컨테이너는 화물 상자, 노드는 상자를 싣는 배다. 관제탑에 '이 화물 3개는 항상 바다에 떠 있어야 한다'고 적어 두면, 배 한 척이 고장 나도 관제탑이 다른 배에 화물을 다시 싣는다. 나는 배마다 돌아다니지 않고 관제탑에 주문서(YAML)만 낸다. kind는 이 항구 전체를 장난감 크기로 줄여 책상 위(노트북의 Docker)에 올려 둔 모형이다.

## 헷갈렸던 것들

- kind의 노드는 VM이 아니라 Docker 컨테이너다. docker ps에 노드가 보인다.
- 쿠버네티스가 컨테이너를 직접 실행하지 않는다. 노드의 컨테이너 런타임(kind에서는 containerd)이 실행하고, kubelet이 그걸 시킨다.
- v1.24에서 Docker Engine을 런타임으로 쓰는 dockershim이 빠졌지만, Docker로 만든 이미지는 그대로 쓴다. 이미지는 표준(OCI) 형식이라서다.
- kubectl은 서버와 마이너 버전이 하나 차이까지만 공식 지원된다.
- 클러스터가 여러 개면 kubectl이 지금 어디를 보고 있는지(current-context)부터 확인한다.

## 용어 정리

| 용어 | 뜻 |
|---|---|
| 컨테이너 오케스트레이션 | 여러 서버의 컨테이너 배치, 재시작, 확장, 업데이트를 자동으로 관리하는 것 |
| 선언형 | 원하는 상태를 적어 두면 시스템이 그 상태로 맞추는 방식 |
| 노드 | 파드가 실제로 도는 서버(kind에서는 컨테이너) |
| kubectl | 쿠버네티스 API 서버에 요청을 보내는 명령줄 도구 |
| kubeconfig | 클러스터 주소, 인증 정보, 컨텍스트를 담은 파일(~/.kube/config) |
| 컨텍스트 | kubeconfig에서 '어느 클러스터에 누구로 접속할지'를 묶은 이름 |
| kind | Kubernetes IN Docker. Docker 컨테이너를 노드로 쓰는 로컬 클러스터 도구 |

## 참고 자료

- Kubernetes 문서, 개요: <https://kubernetes.io/docs/concepts/overview/>
- Kubernetes 문서, 도구 설치(kubectl, kind, minikube): <https://kubernetes.io/docs/tasks/tools/>
- Kubernetes 문서, 버전 차이 정책: <https://kubernetes.io/releases/version-skew-policy/>
- Kubernetes 릴리스 정보: <https://kubernetes.io/releases/>
- kind 빠른 시작: <https://kind.sigs.k8s.io/docs/user/quick-start/>
- kind v0.24.0 릴리스: <https://github.com/kubernetes-sigs/kind/releases/tag/v0.24.0>
- Kubernetes 블로그, dockershim 제거 FAQ: <https://kubernetes.io/blog/2022/02/17/dockershim-faq/>

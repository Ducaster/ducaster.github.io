---
title: '[KCNA] 애플리케이션 배포와 디버깅: CI/CD, GitOps, Helm과 Kustomize, 배포 전략'
date: '2026-09-09T21:20:00+09:00'
categories:
- KCNA
tags:
- kubernetes
- kcna
- cicd
- gitops
- argo-cd
- flux
- helm
- kustomize
- rolling-update
- canary
- blue-green
- rollout
- debugging
- Cloud Native Application Delivery
series:
- KCNA
series_order: 10
---

Cloud Native Application Delivery는 이번 개편에서 8%에서 16%로 두 배가 됐다. 항목은 Application Delivery와 Debugging 두 개뿐인데, 예전 범위의 GitOps와 CI/CD가 Application Delivery에 들어간다고 보고 같이 정리했다. 디버깅은 앞의 트러블슈팅 글과 겹치는 부분을 빼고, 배포하다가 생기는 문제(멈춘 롤아웃, 렌더링 오류, 설정 드리프트)에 맞췄다.

## 요약

- CI는 코드를 빌드하고 테스트해서 이미지를 레지스트리에 올리는 단계, CD는 그 이미지를 환경에 배포하는 단계다.
- GitOps는 원하는 상태를 Git에 선언하고, 클러스터 안의 에이전트가 그걸 끌어와(pull) 계속 맞추는 방식이다. OpenGitOps 원칙은 선언적, 버전 관리되고 바뀌지 않음, 자동으로 끌어옴, 계속 조정 네 가지다.
- Argo CD와 Flux가 대표 GitOps 도구이고, 둘 다 CNCF graduated다.
- Helm은 템플릿과 values로 된 차트를 릴리스로 설치·업그레이드·롤백한다. Helm 4가 2025년 11월에 나왔다.
- Kustomize는 템플릿 없이 base에 overlay 패치를 덧씌운다. kubectl에 내장돼 있다(`kubectl apply -k`).
- 배포 전략은 롤링 업데이트(Deployment 기본), Recreate, 블루/그린, 카나리가 있다.
- 롤아웃이 멈추면 `kubectl rollout status`, ReplicaSet과 새 파드 상태를 본다. Deployment는 기한을 넘겨도 스스로 롤백하지 않는다.

## 1. CI/CD와 GitOps

{{< mermaid >}}
flowchart TB
  subgraph push["파이프라인이 밀어 넣는 방식(push)"]
    direction TB
    A1["코드 커밋"] --> A2["CI: 빌드, 테스트, 이미지 푸시"]
    A2 --> A3["CI가 kubectl apply, helm upgrade 실행<br>CI에 클러스터 자격 증명이 필요하다"]
    A3 --> A4["클러스터"]
  end
  subgraph pull["GitOps(pull)"]
    direction TB
    B1["코드 커밋"] --> B2["CI: 빌드, 테스트, 이미지 푸시"]
    B2 --> B3["설정 저장소의 이미지 태그 변경"]
    B4["클러스터 안의 Argo CD, Flux"] -->|"주기적으로 확인"| B3
    B4 -->|"차이가 있으면 적용"| B5["클러스터"]
  end
{{< /mermaid >}}

push 방식은 CI 도구가 클러스터 밖에서 배포 명령을 실행한다. 그러려면 CI에 클러스터 자격 증명을 줘야 한다. GitOps는 클러스터 안의 에이전트가 Git을 보고 스스로 맞춘다. 자격 증명이 클러스터 밖으로 나가지 않고, 누가 `kubectl edit`으로 몰래 바꾼 설정(드리프트)도 Git 상태로 되돌린다. 배포 기록은 Git 커밋 기록 그대로이고, 롤백은 커밋을 되돌리면 된다.

CNCF GitOps 워킹 그룹이 만든 OpenGitOps 원칙은 이렇다.

| 원칙 | 뜻 |
|---|---|
| 선언적(Declarative) | 시스템의 원하는 상태를 선언적으로 적는다 |
| 버전 관리되고 바뀌지 않음(Versioned and Immutable) | 원하는 상태는 버전이 남고 고칠 수 없는 방식으로 저장한다. 기록이 다 남는다 |
| 자동으로 끌어옴(Pulled Automatically) | 에이전트가 원하는 상태를 자동으로 가져온다 |
| 계속 조정(Continuously Reconciled) | 에이전트가 실제 상태를 계속 보고 원하는 상태에 맞춘다 |

| | Argo CD | Flux |
|---|---|---|
| 형태 | 웹 UI가 있는 하나의 애플리케이션 | 여러 컨트롤러를 모은 도구 모음(GitOps Toolkit) |
| 주요 리소스 | Application, ApplicationSet | GitRepository, Kustomization, HelmRelease |
| CNCF | graduated(Argo 프로젝트, 2022년 12월) | graduated(2022년 11월) |

CI 쪽 도구는 GitHub Actions, GitLab CI, Jenkins, Tekton 등이 있다. Tekton은 CNCF가 아니라 CD Foundation 프로젝트다.

## 2. Helm

Helm은 쿠버네티스 패키지 관리자다(CNCF graduated).

| 용어 | 뜻 |
|---|---|
| 차트 | 템플릿 YAML, 기본값(values.yaml), 메타데이터(Chart.yaml)를 묶은 패키지 |
| 저장소 | 차트를 올려 두는 곳. HTTP 저장소나 OCI 레지스트리 |
| 릴리스 | 차트를 클러스터에 설치한 하나의 인스턴스. 업그레이드할 때마다 리비전이 쌓인다 |
| values | 설치할 때 바꾸는 값. `-f values-prod.yaml`이나 `--set image.tag=1.4.2` |

```text
shop/
├── Chart.yaml          # 이름, 버전, apiVersion: v2
├── values.yaml         # 기본값
└── templates/
    ├── deployment.yaml # {{ .Values.image.tag }} 같은 Go 템플릿
    └── service.yaml
```

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install shop ./shop -n shop -f values-prod.yaml   # 릴리스 shop 설치
helm upgrade --install shop ./shop -n shop --set image.tag=1.4.3
helm history shop -n shop                              # 리비전 목록
helm rollback shop 2 -n shop                           # 리비전 2로 되돌리기
helm template shop ./shop -f values-prod.yaml          # 렌더링 결과만 보기
helm lint ./shop
```

릴리스 정보는 그 네임스페이스의 Secret에 저장된다. Helm 2 때 있던 클러스터 쪽 구성 요소(Tiller)는 Helm 3부터 없다. Helm 4는 2025년 11월 12일에 나왔다. 대부분의 Helm 3 차트(apiVersion v2)는 그대로 쓰고, WASM 플러그인, Server-Side Apply, kstatus 기반의 준비 상태 대기가 들어왔다.

## 3. Kustomize

Kustomize는 템플릿 문법 없이 YAML 원본(base)에 환경별 차이(overlay)를 덧씌운다. kubectl에 들어 있다.

```text
app/
├── base/
│   ├── kustomization.yaml
│   ├── deployment.yaml
│   └── service.yaml
└── overlays/
    ├── dev/kustomization.yaml
    └── prod/kustomization.yaml
```

```yaml
# overlays/prod/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
- ../../base
namespace: shop-prod
namePrefix: prod-
images:
- name: registry.example.com/shop/api
  newTag: "1.4.3"
patches:
- target:
    kind: Deployment
    name: api
  patch: |-
    - op: replace
      path: /spec/replicas
      value: 5
configMapGenerator:
- name: api-config
  literals:
  - LOG_LEVEL=info
```

```bash
kubectl kustomize overlays/prod      # 결과 YAML만 출력
kubectl apply -k overlays/prod       # 적용
```

configMapGenerator로 만든 ConfigMap은 이름 뒤에 내용의 해시가 붙는다. 내용이 바뀌면 이름이 바뀌고, 그걸 참조하는 Deployment가 롤링 업데이트된다.

| | Helm | Kustomize |
|---|---|---|
| 방식 | Go 템플릿 + values | base + overlay 패치 |
| 배포 단위 | 버전이 붙은 차트, 릴리스와 리비전 | 디렉터리 |
| 롤백 | `helm rollback` | Git이나 kubectl로 |
| 남이 만든 앱 설치 | 공개 차트가 많다 | 적다 |

둘을 같이 쓰기도 한다. Kustomize의 helmCharts 기능이나, Argo CD와 Flux가 둘 다 지원하는 식이다.

## 4. 배포 전략

| 전략 | 방법 | 장단점 |
|---|---|---|
| 롤링 업데이트 | 새 파드를 조금씩 늘리고 옛 파드를 줄인다. Deployment 기본값 | 중단이 없다. 잠깐 두 버전이 섞인다 |
| Recreate | 옛 파드를 모두 지우고 새로 띄운다 | 두 버전이 섞이지 않는다. 그동안 중단된다 |
| 블루/그린 | 새 버전(그린)을 따로 다 띄운 뒤 서비스 셀렉터를 한 번에 바꾼다 | 되돌리기가 빠르다. 자원이 두 배 든다 |
| 카나리 | 새 버전에 트래픽을 조금(예: 10%)만 보내고 지표를 보며 늘린다 | 위험이 작다. 트래픽 분할과 지표 판단이 필요하다 |

롤링 업데이트의 속도는 `maxSurge`(더 띄울 수 있는 수)와 `maxUnavailable`(줄어들어도 되는 수)로 정한다. 기본값은 둘 다 25%다. 새 파드가 Ready가 되어야 다음 단계로 넘어가서, readiness 프로브가 롤아웃 속도와 안전을 함께 쥐고 있다.

![replicas 4, maxSurge와 maxUnavailable 25%일 때 롤링 업데이트](./attachments/k8s-rolling-update.png)
_파드 4개 기준이면 동시에 하나 더 띄우고(5개), 하나까지 줄어들 수 있다(3개)_

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api
spec:
  replicas: 4
  revisionHistoryLimit: 10        # 롤백용으로 남길 ReplicaSet 수(기본 10)
  progressDeadlineSeconds: 600    # 이 시간 안에 진척이 없으면 실패로 표시(기본 600)
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 25%
      maxUnavailable: 25%
  selector:
    matchLabels:
      app: api
  template:
    metadata:
      labels:
        app: api
    spec:
      containers:
      - name: api
        image: registry.example.com/shop/api:1.4.3
```

카나리는 기본 리소스로도 흉내 낼 수 있다. 같은 라벨을 가진 Deployment 두 개를 9:1 복제본으로 띄우면 서비스가 대략 그 비율로 나눈다. 정확한 비율은 Gateway API나 서비스 메시의 가중치로 나누고, 지표를 보고 자동으로 늘리거나 되돌리는 건 Argo Rollouts나 Flagger 같은 도구가 한다.

## 5. 배포하다 생기는 문제

```bash
kubectl rollout status deploy/api -n shop        # 진행 상황
kubectl rollout history deploy/api -n shop       # 리비전 목록
kubectl rollout undo deploy/api -n shop          # 바로 전 리비전으로
kubectl rollout undo deploy/api --to-revision=3 -n shop
kubectl rollout restart deploy/api -n shop       # 같은 설정으로 파드를 새로 띄움
kubectl get rs -n shop -l app=api                # 새 ReplicaSet과 옛 ReplicaSet
kubectl diff -f api.yaml                         # 적용 전에 차이 보기
```

| 증상 | 원인 | 확인 |
|---|---|---|
| 롤아웃이 '1 of 4 updated replicas are available'에서 멈춤 | 새 파드가 Ready가 안 된다(이미지 오류, readiness 실패, CrashLoopBackOff) | 새 ReplicaSet의 파드를 describe, logs |
| Deployment 조건에 ProgressDeadlineExceeded | progressDeadlineSeconds 안에 진척이 없었다 | 위와 같음. 자동 롤백은 없어서 `rollout undo`를 직접 한다 |
| `helm upgrade`가 렌더링 오류로 실패 | 템플릿 문법, values 이름 오타 | `helm template`, `helm lint` |
| `helm upgrade`가 다른 작업이 진행 중이라며 실패 | 앞선 설치나 업그레이드가 중간에 끊겨 릴리스가 pending 상태로 남았다 | `helm history`로 상태를 보고 롤백 |
| Argo CD 앱이 OutOfSync | 누가 클러스터에서 직접 고쳤거나, Git에 새 커밋이 있다 | 앱의 diff 화면. 자동 동기화와 셀프 힐을 켜 두면 되돌린다 |
| ConfigMap을 바꿨는데 앱이 그대로 | 환경 변수로 넣은 값은 파드가 다시 떠야 바뀐다 | `kubectl rollout restart` |
| 환경마다 동작이 다름 | values나 overlay 차이 | `helm get values`, `kubectl kustomize` 결과 비교 |

> **쉬운 설명**
>
> GitOps는 레시피북과 주방장이다. 레시피북(Git)에 적힌 대로만 요리가 나가고, 주방장(Argo CD, Flux)은 수시로 레시피북을 펴서 지금 요리와 다르면 다시 만든다. 손님이 주방에 몰래 들어와 소금을 넣어도(kubectl edit) 레시피대로 되돌린다. Helm은 '맵기 1~5단계' 같은 옵션 칸(values)이 있는 밀키트이고, Kustomize는 기본 레시피 위에 '매운맛 버전은 고추 두 개 추가'라는 메모를 붙이는 방식이다. 카나리는 신메뉴를 몇 테이블에만 먼저 내보고 반응이 좋으면 늘리는 것이다.

## 헷갈렸던 것들

- CI가 `kubectl apply`를 실행하는 건 GitOps가 아니다. GitOps는 클러스터 안 에이전트가 끌어오는 방식이다.
- Deployment는 ProgressDeadlineExceeded가 돼도 스스로 롤백하지 않는다.
- 롤링 업데이트 기본값은 maxSurge 25%, maxUnavailable 25%다.
- Kustomize에는 템플릿 언어가 없다. Helm은 Go 템플릿이다.
- Helm 3부터 Tiller가 없고, 릴리스 정보는 네임스페이스의 Secret에 있다.
- 환경 변수로 넣은 ConfigMap 값은 파드를 다시 띄워야 바뀐다.
- 블루/그린은 두 벌을 다 띄워 두니 자원이 두 배 든다.

## 용어 정리

| 용어 | 뜻 |
|---|---|
| CI | 코드 변경을 자주 합치고 빌드, 테스트하는 과정 |
| CD | 빌드한 결과를 환경에 자동으로 배포하는 과정 |
| GitOps | Git을 원하는 상태의 기준으로 두고, 에이전트가 끌어와 계속 맞추는 운영 방식 |
| 드리프트 | 실제 클러스터 상태가 Git에 선언된 상태와 달라진 것 |
| 차트 | Helm의 패키지. 템플릿과 기본값의 묶음 |
| 릴리스 | 차트를 설치한 인스턴스. 리비전 기록을 가진다 |
| overlay | Kustomize에서 base 위에 덧씌우는 환경별 변경 |
| 카나리 배포 | 새 버전에 일부 트래픽만 보내며 점점 늘리는 배포 |
| 블루/그린 배포 | 두 환경을 다 띄워 두고 트래픽을 한 번에 넘기는 배포 |

## 복습 문제

**1.** Which statement best describes GitOps?

- A. A CI pipeline pushes manifests to the cluster with kubectl after each build.
- B. An agent in the cluster pulls the desired state from Git and continuously reconciles the cluster with it.
- C. Developers change live objects with `kubectl edit` and then commit the result.
- D. Configuration is stored only in etcd.

**2.** What is the default update strategy of a Deployment?

- A. Recreate
- B. Blue/green
- C. Canary
- D. RollingUpdate

**3.** Which tool customizes Kubernetes YAML with bases and overlays, does not use a templating language, and is built into kubectl?

- A. Kustomize
- B. Helm
- C. Argo CD
- D. Flux

**4.** A new version should receive about 10% of the traffic first and then more traffic if its metrics stay healthy. Which deployment strategy is this?

- A. Recreate
- B. Blue/green
- C. Canary
- D. Rolling restart

**5.** In Helm, what is a release?

- A. A chart repository
- B. An installed instance of a chart in a cluster, with its own revision history
- C. A values file
- D. A Kubernetes API version

**6.** A Deployment rollout exceeds its `progressDeadlineSeconds`. What does Kubernetes do automatically?

- A. It rolls back to the previous revision.
- B. It deletes the Deployment.
- C. It scales the Deployment to zero.
- D. It sets the Progressing condition to False with the reason ProgressDeadlineExceeded, without rolling back.

**7.** Which two projects are graduated CNCF GitOps tools?

- A. Jenkins and Tekton
- B. Helm and Kustomize
- C. Argo CD and Flux
- D. Prometheus and Grafana

## 답과 풀이

1. **B** 에이전트가 끌어와 계속 맞추는 게 GitOps다. A는 push 방식 CD다.
2. **D** RollingUpdate가 기본이고, 다른 하나는 Recreate다. 블루/그린과 카나리는 Deployment 전략 타입이 아니다.
3. **A** Kustomize는 `kubectl apply -k`로 바로 쓴다.
4. **C** 일부 트래픽으로 시작해 늘리는 게 카나리다.
5. **B** 같은 차트로 릴리스를 여러 개 설치할 수 있고, 릴리스마다 리비전이 쌓인다.
6. **D** 실패로 표시만 하고, 되돌리는 건 사람이나 도구의 몫이다.
7. **C** Argo(2022년 12월)와 Flux(2022년 11월) 모두 graduated다. Tekton은 CD Foundation 프로젝트이고, Helm은 GitOps 도구가 아니라 패키지 관리자다.

## 참고 자료

- Kubernetes 문서, 디플로이먼트: <https://kubernetes.io/docs/concepts/workloads/controllers/deployment/>
- Kubernetes 문서, Kustomize로 오브젝트 관리: <https://kubernetes.io/docs/tasks/manage-kubernetes-objects/kustomization/>
- Helm 문서: <https://helm.sh/docs/>
- Helm 블로그, Helm 4 출시: <https://helm.sh/blog/helm-4-released/>
- OpenGitOps: <https://opengitops.dev/>
- Argo CD 문서: <https://argo-cd.readthedocs.io/en/stable/>
- Flux 문서: <https://fluxcd.io/flux/>
- Argo Rollouts: <https://argoproj.github.io/rollouts/>
- Flagger: <https://flagger.app/>


---
title: '[K8s 기초] Helm으로 앱 배포해 보기: 차트, 값, 릴리스'
date: '2025-02-01T16:20:00+09:00'
categories:
- Kubernetes
tags:
- kubernetes
- helm
- chart
- values
- release
- rollback
- helm-template
- podinfo
- 보안과 운영 맛보기
series:
- Kubernetes 기초
series_order: 16
---

앱 하나를 올리는 데도 디플로이먼트, 서비스, ConfigMap, 인그레스 YAML이 줄줄이 필요했다. 환경마다 복제본 수나 이미지 태그만 다른데 파일을 통째로 복사하는 것도 이상하다. Helm은 이 YAML 묶음을 템플릿으로 만들고 값만 바꿔 설치·업그레이드·롤백하게 해 주는 패키지 관리자다. 공개 차트를 설치해 보고 내 차트도 만들어 봤다.

## 요약

- 차트는 템플릿 YAML과 기본값(values.yaml)을 묶은 패키지다. 설치한 결과 하나하나를 릴리스라고 한다.
- 값은 --set이나 -f 파일로 덮어쓴다. Helm이 템플릿에 값을 채워 매니페스트를 만들고 API 서버에 적용한다.
- 업그레이드할 때마다 리비전이 올라가고, helm rollback으로 이전 리비전으로 돌아간다. 릴리스 기록은 그 네임스페이스의 Secret에 저장된다.
- helm template으로 실제로 어떤 YAML이 만들어지는지 설치 전에 볼 수 있다.
- Helm 3는 클러스터에 따로 서버(Tiller)를 두지 않고 kubeconfig 권한으로 바로 동작한다.

## 1. Helm의 세 단어

| 단어 | 뜻 | 예 |
|---|---|---|
| 차트(chart) | 템플릿 + 기본값 + 메타데이터 묶음 | podinfo/podinfo |
| 값(values) | 템플릿에 채울 설정 | replicaCount, image.tag |
| 릴리스(release) | 차트를 클러스터에 설치한 한 번의 결과. 이름이 있다 | demo |
| 저장소(repository) | 차트를 모아 둔 곳 | https://stefanprodan.github.io/podinfo |

{{< mermaid >}}
flowchart LR
  T["차트 템플릿<br>templates/*.yaml"] --> R["helm이 렌더링"]
  V["values.yaml<br>(기본값)"] --> R
  O["--set, -f my-values.yaml<br>(덮어쓰기)"] --> R
  R --> M["완성된 매니페스트"]
  M --> A["API 서버에 적용"]
  A --> H["릴리스 기록<br>revision 1, 2, 3...<br>(네임스페이스의 Secret)"]
{{< /mermaid >}}

## 2. 공개 차트 설치하고 올리고 되돌리기

실습용으로 많이 쓰는 podinfo 차트를 썼다. 작은 웹 앱이라 화면에 메시지와 버전이 나온다.

```bash
helm repo add podinfo https://stefanprodan.github.io/podinfo
helm repo update
helm search repo podinfo
helm show values podinfo/podinfo | head -30          # 바꿀 수 있는 값 목록
helm install demo podinfo/podinfo -n apps --create-namespace --set replicaCount=2
helm list -n apps
kubectl -n apps get deploy,svc,pods
kubectl -n apps port-forward svc/demo-podinfo 9898:9898   # 브라우저로 localhost:9898
```

값을 바꿔 업그레이드하고, 기록을 보고, 되돌렸다.

```bash
helm upgrade demo podinfo/podinfo -n apps --set replicaCount=3 --set ui.message="hello helm"
helm history demo -n apps          # REVISION 1, 2
helm get values demo -n apps       # 지금 덮어쓴 값
helm rollback demo 1 -n apps       # 1로 돌아가면서 REVISION 3이 생긴다
kubectl -n apps get secret -l owner=helm   # sh.helm.release.v1.demo.v1, v2, v3
```

upgrade할 때 --set을 다시 다 적지 않으면 이전에 준 값이 기본값으로 돌아간다는 걸 처음에 몰랐다. 값이 많아지면 파일(-f values-prod.yaml)로 관리하는 게 낫다.

## 3. 내 차트 만들어 보기

```bash
helm create mychart
tree mychart
```

```
mychart/
├── Chart.yaml          # 이름, 버전(차트 버전 version, 앱 버전 appVersion)
├── values.yaml         # 기본값
├── charts/             # 의존 차트
└── templates/
    ├── _helpers.tpl    # 이름 짓기 같은 공용 함수
    ├── deployment.yaml
    ├── service.yaml
    ├── ingress.yaml, hpa.yaml, serviceaccount.yaml ...
    └── NOTES.txt       # 설치 후 보여 줄 안내
```

템플릿 안에서는 값을 이렇게 꺼낸다.

```yaml
spec:
  replicas: {{ .Values.replicaCount }}
  template:
    spec:
      containers:
      - name: {{ .Chart.Name }}
        image: "{{ .Values.image.repository }}:{{ .Values.image.tag | default .Chart.AppVersion }}"
```

```bash
helm lint ./mychart
helm template test ./mychart --set replicaCount=5 | grep -n 'replicas'   # replicas: 5
helm install mine ./mychart -n apps --dry-run=server                     # 서버 검증까지만
```

helm template은 클러스터에 아무것도 만들지 않고 결과 YAML만 보여 줘서, 템플릿을 고칠 때 제일 많이 썼다.

> **쉬운 설명**
>
> Helm 차트는 가구 조립 세트다. 설명서와 부품(템플릿)이 들어 있고, 색깔이나 칸 수(값)는 주문할 때 고른다. helm install은 그 세트를 방(네임스페이스)에 조립하는 것이고, 조립한 결과물 하나가 릴리스다. 칸을 하나 더 달면(upgrade) 조립 기록에 2번이 남고, 마음에 안 들면 1번 상태로 되돌린다(rollback). 되돌린 것도 새 기록(3번)으로 남는다.

## 헷갈렸던 것들

- 차트와 릴리스는 다르다. 같은 차트로 이름이 다른 릴리스를 여러 개 설치할 수 있다.
- upgrade 때 --set을 빠뜨리면 그 값은 기본값으로 돌아간다. 이전 값을 유지하려면 다시 주거나 파일로 관리한다.
- rollback은 리비전 번호를 되돌리지 않고 새 리비전을 만든다. 디플로이먼트의 rollout undo와 같다.
- Chart.yaml의 version은 차트 버전, appVersion은 앱 버전이다.
- 릴리스 기록은 그 네임스페이스의 Secret에 있다. 네임스페이스를 지우면 기록도 사라진다.
- 설치할 때 -n을 빼면 현재 컨텍스트의 네임스페이스에 들어간다. list, upgrade, uninstall도 같은 -n을 줘야 찾는다.

## 용어 정리

| 용어 | 뜻 |
|---|---|
| Helm | 쿠버네티스 패키지 관리자 |
| 차트 | 템플릿과 기본값을 묶은 패키지 |
| 릴리스 | 차트를 클러스터에 설치한 한 번의 결과 |
| values | 템플릿에 채우는 설정 값 |
| 리비전 | 릴리스의 설치·업그레이드·롤백마다 올라가는 번호 |
| helm template | 클러스터 없이 렌더링 결과만 보여 주는 명령 |

## 복습 문제

**1.** podinfo 차트를 네임스페이스 lab에 릴리스 이름 web으로, 복제본 1개로 설치해라.

**2.** web의 ui.message를 바꿔 업그레이드하고, 실제로 덮어쓴 값과 리비전 목록을 확인해라.

**3.** 설치하지 않고 podinfo 차트가 만드는 디플로이먼트 YAML만 파일로 뽑아라.

## 답과 풀이

1. --create-namespace를 붙이면 네임스페이스도 만든다.

```bash
helm install web podinfo/podinfo -n lab --create-namespace --set replicaCount=1
helm list -n lab
```

2. get values는 덮어쓴 값만, history는 리비전 목록을 보여 준다.

```bash
helm upgrade web podinfo/podinfo -n lab --set replicaCount=1 --set ui.message="from lab"
helm get values web -n lab
helm history web -n lab
```

3. helm template에 --show-only로 템플릿 파일 하나만 고른다.

```bash
helm template web podinfo/podinfo --show-only templates/deployment.yaml > podinfo-deploy.yaml
```

## 참고 자료

- Helm 문서, 빠른 시작: <https://helm.sh/docs/intro/quickstart/>
- Helm 문서, 사용법: <https://helm.sh/docs/intro/using_helm/>
- Helm 문서, 차트 템플릿 가이드: <https://helm.sh/docs/chart_template_guide/getting_started/>
- podinfo: <https://github.com/stefanprodan/podinfo>

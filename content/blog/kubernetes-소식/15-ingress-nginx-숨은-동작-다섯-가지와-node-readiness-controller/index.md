---
title: '[K8s 소식] 옮기기 전에 알아야 할 Ingress-NGINX의 숨은 동작 다섯 가지, 그리고 Node Readiness Controller'
date: '2026-02-28T15:30:00+09:00'
categories:
- Kubernetes
tags:
- kubernetes
- ingress-nginx
- gateway-api
- httproute
- regex
- rewrite-target
- migration
- node-readiness-controller
- taints
- 소식
series:
- Kubernetes 소식
series_order: 15
---

Ingress-NGINX 은퇴가 다음 달이다. 어제 공식 블로그에 '옮기기 전에 알아야 할 Ingress-NGINX의 놀라운 동작 다섯 가지' 글이 올라왔다. 11월에 내 Ingress를 Gateway API로 옮기면서 '어노테이션이 없어서 1대 1로 옮겨졌다'고 적었는데, 이 글을 읽고 나니 어노테이션이 있으면 왜 1대 1이 안 되는지 알 것 같다. 겉보기엔 맞게 옮겨도 Ingress-NGINX의 기본 동작에 기대던 요청이 404가 되는 경우들이다. 2월 초에 나온 Node Readiness Controller 소개 글도 같이 정리했다.

## 요약

- Ingress-NGINX의 정규식 경로는 앞부분만 맞으면 되고(prefix) 대소문자를 구분하지 않는다. Envoy 기반 Gateway API 구현체 다수는 전체를 대소문자 구분해서 맞춘다.
- use-regex 어노테이션은 그 Ingress만이 아니라 같은 호스트의 모든 Ingress 경로를 정규식으로 바꾼다. rewrite-target 어노테이션도 몰래 use-regex를 켠 것과 같다.
- 끝에 슬래시가 없는 요청은 슬래시를 붙인 경로로 301 리다이렉트된다. Gateway API 구현체는 이런 리다이렉트를 알아서 만들지 않는다.
- Ingress-NGINX는 매칭 전에 URL을 정규화한다(., .., 연속 슬래시). 구현체마다 정규화 범위가 다르다.
- Node Readiness Controller는 노드 조건(Condition)을 보고 테인트를 자동으로 붙이고 떼서, CNI나 GPU 드라이버 같은 준비가 끝난 노드에만 파드가 가게 한다. NodeReadinessRule이라는 CRD로 선언한다.

## 1. Ingress-NGINX의 숨은 동작 다섯 가지

글은 Ingress-NGINX(쿠버네티스 커뮤니티, 3월 은퇴)와 NGINX Ingress(F5 제품)는 이름만 비슷한 다른 프로젝트라는 말로 시작한다. 이 글은 앞쪽 이야기다.

| 동작 | Ingress-NGINX에서는 | 그대로 옮기면 | 유지하려면 |
|---|---|---|---|
| 정규식이 prefix, 대소문자 무시 | /[A-Z]{3}이 /uuid에도 맞는다 | 대소문자 구분 전체 매칭이라 /uuid가 404 | RegularExpression에 (?i)/[a-z]{3}.* 처럼 쓴다 |
| use-regex가 호스트 전체로 번짐 | 같은 호스트의 다른 Ingress의 Exact /Header도 정규식이 돼서 /headers가 맞는다 | Exact는 Exact라 /headers가 404 | 오타를 고치거나 (?i)/Header 정규식으로 |
| rewrite-target이 정규식을 켬 | use-regex가 없어도 같은 호스트 전체가 정규식 취급 | URLRewrite 필터는 매칭 방식을 바꾸지 않아 404 | (?i)/IP.* 처럼 정규식으로 바꾸거나 오타 수정 |
| 끝 슬래시 리다이렉트 | /my-path/만 있어도 /my-path가 301로 /my-path/에 간다 | 리다이렉트가 없어 404 | RequestRedirect 필터로 직접 만든다 |
| URL 정규화 | /ip/abc/../../uuid, ////uuid가 /uuid로 맞는다 | 구현체마다 정규화 범위가 다르다 | 구현체 문서를 확인한다. Istio, Envoy Gateway, kgateway는 ., ..를 기본으로 정리한다 |

제일 무서운 건 두 번째와 세 번째다. 내가 고친 적 없는 다른 팀의 Ingress 하나에 use-regex나 rewrite-target이 붙어 있으면, 같은 호스트를 쓰는 내 Ingress까지 동작이 바뀐다.

{{< mermaid >}}
flowchart LR
  subgraph host["같은 호스트 regex-match.example.com"]
    direction TB
    A["Ingress A<br>use-regex: true<br>(또는 rewrite-target)"]
    B["Ingress B<br>path /Header, Exact<br>(어노테이션 없음)"]
  end
  host --> N["Ingress-NGINX가 만든 설정<br>호스트의 모든 경로를<br>대소문자 무시<br>prefix 정규식으로"]
  N --> R["GET /headers<br>→ /Header에 맞아 200"]
  host -.->|"그대로 HTTPRoute로 옮기면"| G["Exact /Header<br>→ /headers는 404"]
{{< /mermaid >}}

기초 공부 때 겪은 일도 생각났다. TLS를 건 호스트에 HTTP로 요청하니 ingress-nginx가 기본으로 HTTPS 주소로 308 리다이렉트를 돌려줘서 한참 헤맸다. 그것도 이 글에 나온 것과 같은 부류의, 설정에 안 적혀 있는 기본 동작이었다.

### 끝 슬래시 리다이렉트를 HTTPRoute로

공식 글의 예제를 옮기다가 filters 아래 type이 빠져 있는 것 같아서 type: RequestRedirect를 넣었다. 그래야 스키마 검사를 통과했다.

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: trailing-slash-route
spec:
  hostnames:
  - trailing-slash.example.com
  parentRefs:
  - name: gateway
    namespace: gateway-infra
  rules:
  - name: add-slash
    matches:
    - path:
        type: Exact
        value: /my-path
    filters:
    - type: RequestRedirect
      requestRedirect:
        statusCode: 301
        path:
          type: ReplaceFullPath
          replaceFullPath: /my-path/
  - name: my-path
    matches:
    - path:
        type: Exact
        value: /my-path/
    backendRefs:
    - name: httpbin
      port: 8000
```

parentRefs는 지난번 kind 실습의 Gateway로 바꿨고, 규칙에 이름도 붙였다. 다만 cloud-provider-kind의 Gateway 구현이 RequestRedirect까지 지원하는지는 확인하지 못했다. GatewayClass status의 supportedFeatures 목록에서 봐야 한다.

이 글의 요지는 '옮기기 전에 지금 실제로 들어오는 요청을 봐라'였다. 설정 파일만 보고 옮기면 오타였던 /Header가 사실은 /headers 요청을 받고 있었다는 걸 알 수 없다. SIG Network는 이런 어노테이션과 동작 일부를 Ingress2Gateway 변환 도구에 넣고 있다고 한다. 글 끝에는 2월 27일 Gateway API 1.5가 나왔고 ListenerSet과 HTTPRoute CORS 필터가 정식이 됐다는 소식도 덧붙어 있었다.

## 2. Node Readiness Controller

노드의 Ready 조건은 kubelet과 런타임이 준비됐다는 뜻일 뿐, CNI 에이전트나 스토리지 드라이버, GPU 펌웨어까지 준비됐다는 뜻은 아니다. 그래서 노드가 막 붙었을 때 네트워크가 아직 안 된 노드에 파드가 먼저 가서 실패하는 일이 생긴다. Node Readiness Controller는 이 틈을 테인트로 막는다.

{{< mermaid >}}
flowchart LR
  J["노드 합류<br>테인트<br>network-unavailable<br>(pending, NoSchedule)"] --> C{"노드 조건<br>NetworkReady = True?"}
  R["NPD나<br>조건 보고 에이전트가<br>노드 조건 갱신"] --> C
  C -->|"아직"| J
  C -->|"True"| T["컨트롤러가 테인트 제거"]
  T --> P["이제 파드가 스케줄됨"]
{{< /mermaid >}}

```yaml
apiVersion: readiness.node.x-k8s.io/v1alpha1
kind: NodeReadinessRule
metadata:
  name: network-readiness-rule
spec:
  conditions:
  - type: "cniplugin.example.net/NetworkReady"
    requiredStatus: "True"
  taint:
    key: "readiness.k8s.io/acme.com/network-unavailable"
    effect: "NoSchedule"
    value: "pending"
  enforcementMode: "bootstrap-only"
  nodeSelector:
    matchLabels:
      node-role.kubernetes.io/worker: ""
```

| 개념 | 내용 |
|---|---|
| NodeReadinessRule | 어떤 노드(nodeSelector)가 어떤 조건(conditions)을 만족할 때까지 어떤 테인트를 붙일지 선언한다 |
| bootstrap-only | 처음 한 번만. 조건을 만족하면 그 노드에서는 규칙 감시를 멈춘다. 큰 이미지 미리 받기 같은 초기화에 |
| continuous | 노드 수명 내내. 나중에 드라이버가 죽어도 다시 테인트를 붙여 새 파드를 막는다 |
| 조건 보고 | 컨트롤러는 직접 검사하지 않고 노드 Condition만 본다. NPD나 프로젝트가 주는 경량 에이전트가 조건을 갱신한다 |
| dry run | 테인트를 실제로 붙이지 않고, 어느 노드가 영향받을지 로그와 규칙 status에만 남긴다 |

CKA 때 테인트와 톨러레이션을 '파드를 밀어내는 것'으로만 외웠는데, 이건 테인트를 '아직 준비 중' 표시로 쓰는 방식이다. 노드 쪽 상태(Condition)와 스케줄링(Taint)을 컨트롤러 하나로 이어 준다고 보면 된다. 쿠버네티스 본체 기능이 아니라 SIG 하위 프로젝트(alpha API)라서 따로 설치해야 한다.

## 내 클러스터에서 확인할 것

```bash
kubectl get ingress -A -o custom-columns='NS:.metadata.namespace,NAME:.metadata.name,HOSTS:.spec.rules[*].host,REGEX:.metadata.annotations.nginx\.ingress\.kubernetes\.io/use-regex,REWRITE:.metadata.annotations.nginx\.ingress\.kubernetes\.io/rewrite-target'
kubectl -n ingress-nginx logs deploy/ingress-nginx-controller --since=24h | awk '$9 == 301' | head
kubectl get nodes -o custom-columns=NAME:.metadata.name,TAINTS:.spec.taints[*].key
```

- REGEX나 REWRITE 칸이 채워진 Ingress가 있으면, 같은 호스트(HOSTS)를 쓰는 다른 Ingress까지 모두 정규식 매칭이라고 보고 옮겨야 한다.
- 접근 로그에서 301이 많이 보이면 끝 슬래시 리다이렉트에 기대는 클라이언트가 있다는 뜻이다. 실제로 들어오는 경로 목록을 뽑아 새 라우트에서 같은 응답이 나오는지 비교한다.
- 노드가 붙자마자 파드가 실패하는 일이 잦다면, 그 노드의 준비 조건을 Node Readiness Controller 규칙으로 만들 수 있는지 본다.

> **쉬운 설명**
>
> Ingress-NGINX는 눈치가 너무 좋은 안내 직원이었다. 손님이 '/headers'라고 말해도 안내판에 '/Header'(오타)라고 적혀 있으면 '아, 이거 찾으시죠' 하고 보내 줬다. 문 앞에서 '/my-path'라고 하면 '/my-path/' 쪽으로 데려다줬다. 새 안내 직원(Gateway API)은 안내판에 적힌 그대로만 안내한다. 그래서 예전 직원의 눈치에 기대던 손님은 갑자기 '그런 곳 없어요(404)'를 듣게 된다. Node Readiness Controller는 새로 문 연 가게 앞에 '준비 중' 팻말을 걸어 두는 직원이다. 수도, 전기(CNI, 드라이버)가 다 들어왔다는 확인이 오면 그때 팻말을 뗀다.

## 용어 정리

| 용어 | 뜻 |
|---|---|
| use-regex | Ingress-NGINX에서 경로를 정규식으로 해석하게 하는 어노테이션. 같은 호스트 전체에 적용된다 |
| rewrite-target | 백엔드로 보내기 전에 경로를 바꾸는 Ingress-NGINX 어노테이션. 정규식 매칭도 같이 켠다 |
| RequestRedirect, URLRewrite | Gateway API HTTPRoute의 리다이렉트 필터와 경로 재작성 필터 |
| URL 정규화 | ., .., 연속 슬래시 같은 것을 정리해 URL을 표준 형태로 바꾸는 것 |
| Node Condition | 노드 상태 항목. Ready, MemoryPressure 같은 기본 조건 외에 사용자 조건도 넣을 수 있다 |
| NodeReadinessRule | 노드 조건에 따라 테인트를 관리하는 규칙 CRD |

## 참고 자료

- Kubernetes 블로그, Before You Migrate: Five Surprising Ingress-NGINX Behaviors You Need to Know: <https://kubernetes.io/blog/2026/02/27/ingress-nginx-before-you-migrate/>
- Kubernetes 블로그, Introducing Node Readiness Controller: <https://kubernetes.io/blog/2026/02/03/introducing-node-readiness-controller/>
- Gateway API 문서, HTTP 리다이렉트와 재작성: <https://gateway-api.sigs.k8s.io/guides/http-redirect-rewrite/>
- Node Readiness Controller: <https://github.com/kubernetes-sigs/node-readiness-controller>
- ingress2gateway: <https://github.com/kubernetes-sigs/ingress2gateway>

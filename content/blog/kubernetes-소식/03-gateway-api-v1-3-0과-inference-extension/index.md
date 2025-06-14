---
title: '[K8s 소식] Gateway API v1.3.0과 Inference Extension: 비율 미러링, X 접두어, LLM용 라우팅'
date: '2025-06-14T15:30:00+09:00'
categories:
- Kubernetes
tags:
- kubernetes
- gateway-api
- httproute
- request-mirroring
- cors
- listenerset
- retry-budget
- inference-extension
- llm
- 소식
series:
- Kubernetes 소식
series_order: 3
---

CKA 때 Gateway API는 v1.2.1 기준으로 공부했다. 6월 2일에 v1.3.0 GA 소식이 올라왔고(릴리스 자체는 4월 24일), 사흘 뒤에는 LLM 추론 트래픽을 위한 Gateway API Inference Extension 소개 글이 나왔다. 둘 다 '인그레스 다음'으로 공부해 두기로 한 Gateway API 이야기라 같이 정리했다.

## 요약

- v1.3.0에서 비율 기반 요청 미러링이 Standard 채널(GA)로 올라왔다. 요청의 일부만 다른 백엔드로 복사해 보낼 수 있다.
- Experimental 채널에 CORS 필터, XListenerSet(여러 Gateway의 리스너 합치기), 재시도 예산(XBackendTrafficPolicy)이 들어왔다.
- v1.3.0부터 새 실험 리소스는 이름 앞에 X가 붙고 API 그룹도 gateway.networking.x-k8s.io로 따로 쓴다. 나중에 Standard로 옮길 때는 다시 만들어야 한다.
- Gateway API는 쿠버네티스 본체와 따로 배포되는 CRD라, 쿠버네티스 1.26 이상이면 v1.3.0을 바로 설치할 수 있다.
- Inference Extension은 InferencePool과 InferenceModel이라는 CRD로, 모델 서버의 대기열·메모리 같은 실시간 지표를 보고 가장 알맞은 파드로 요청을 보낸다.

## 1. v1.3.0에서 바뀐 것

| 기능 | 채널 | 내용 |
|---|---|---|
| 비율 기반 요청 미러링 | Standard | RequestMirror 필터에 percent(정수)나 fraction(분자/분모)을 준다 |
| CORS 필터 | Experimental | HTTPRoute 필터 타입 CORS로 교차 출처 요청 헤더를 처리한다 |
| XListenerSet | Experimental | 리스너 목록을 따로 정의해 여러 Gateway에 붙인다. 다른 네임스페이스 앱이 자기 TLS 리스너를 관리할 수 있다 |
| 재시도 예산 | Experimental | XBackendTrafficPolicy로 '재시도는 전체 요청의 20%까지' 같은 상한을 건다. 기존 BackendLBPolicy를 대체했다 |

미러링은 블루/그린 배포에서 새 버전에 실제 트래픽을 흘려 보되, 응답은 기존 버전 것만 돌려줄 때 쓴다. 지금까지는 전부 복사하거나 안 하거나였는데, 이제 일부만 복사할 수 있다. 공식 글의 예제는 foo-v1으로 가는 요청의 42%를 foo-v2에도 보낸다.

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: http-filter-mirror
  labels:
    gateway: mirror-gateway
spec:
  parentRefs:
  - name: mirror-gateway
  hostnames:
  - mirror.example
  rules:
  - backendRefs:
    - name: foo-v1
      port: 8080
    filters:
    - type: RequestMirror
      requestMirror:
        backendRef:
          name: foo-v2
          port: 8080
        percent: 42
```

percent 대신 fraction: {numerator: 5, denominator: 1000}처럼 1000건 중 5건 같은 식으로도 줄 수 있다.

Standard와 Experimental 채널의 차이가 이번에 더 분명해졌다. Standard는 하위 호환을 보장하는 GA 채널이고, Experimental은 바뀌거나 빠질 수 있다. 실험 리소스를 쓰려면 Experimental 채널 YAML을 따로 설치해야 하고, X가 붙은 이름과 다른 API 그룹이라 Standard 리소스와 섞일 일은 없다.

## 2. Gateway API Inference Extension

LLM 추론 요청은 일반 웹 요청과 다르다. 오래 걸리고, GPU 메모리를 많이 쓰고, 모델 서버마다 대기열 길이와 캐시 상태가 다르다. 라운드 로빈으로 나누면 한 서버에 몰려 지연이 커진다. 이 확장은 기존 Gateway와 HTTPRoute 모델을 그대로 두고 중간에 '어느 파드가 지금 가장 여유 있나'를 고르는 단계를 넣는다.

{{< mermaid >}}
flowchart LR
  C["클라이언트<br>POST /completions"] --> G["Gateway<br>(Envoy 등)"]
  G -->|"HTTPRoute 매칭"| P["InferencePool<br>(모델 서버 파드 묶음)"]
  P --> E["Endpoint Selection Extension<br>대기열 길이, 메모리, 로드된 어댑터 확인"]
  E -->|"가장 알맞은 파드"| M["모델 서버 파드"]
{{< /mermaid >}}

| CRD | 누가 관리 | 내용 |
|---|---|---|
| InferencePool | 플랫폼 관리자 | GPU 노드에서 도는 모델 서버 파드 묶음. 서비스와 비슷하지만 모델 서빙 프로토콜을 안다 |
| InferenceModel | AI·ML 담당자 | 공개 모델 이름(예: gpt-4-chat)을 풀 안의 실제 모델과 연결하고, 트래픽 분할과 우선순위를 정한다 |

공식 글의 벤치마크에서는 처리량은 일반 서비스와 비슷하면서, 초당 요청이 400~500을 넘는 구간부터 p90 지연이 눈에 띄게 낮았다고 한다. 앞으로 접두어 캐시를 고려한 분산, LoRA 어댑터 배포, 모델별 지표로 HPA 하기 등을 넣을 계획이라고 한다.

## 내 클러스터에서 확인할 것

```bash
kubectl get crd | grep gateway.networking
kubectl get crd gateways.gateway.networking.k8s.io \
  -o jsonpath='{.metadata.annotations.gateway\.networking\.k8s\.io/bundle-version}{"\n"}'
kubectl apply -f https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.3.0/standard-install.yaml
```

- 지금 설치된 Gateway API 번들 버전을 확인하고, 쓰는 구현체(Envoy Gateway, Istio, Cilium 등)가 v1.3을 지원하는지 본다. 공식 글 작성 시점에 Experimental 기능까지 적합성을 통과한 구현체는 Airlock Microgateway, Cilium, Envoy Gateway, Istio 네 곳이었다.
- 실험 기능을 쓰려면 Experimental 채널 YAML을 설치해야 하고, 나중에 Standard로 옮길 때 다시 만들어야 한다는 걸 기억한다.

> **쉬운 설명**
>
> Gateway API는 건물 안내 데스크(인그레스)를 새로 짜는 일이다. 이번 판(v1.3)에서는 '손님 100명 중 42명에게는 시식 코너(새 버전)도 들러 보게 하되, 계산은 원래 매장에서'가 정식 기능이 됐다. 실험 중인 기능에는 이름 앞에 X를 붙여 '시범 운영' 딱지를 달았다. Inference Extension은 AI 상담 창구 전용 안내원이다. 상담원(모델 서버)마다 줄이 얼마나 긴지, 누가 어떤 자료(어댑터)를 펼쳐 두고 있는지 보고 가장 빨리 응대할 창구로 보낸다.

## 용어 정리

| 용어 | 뜻 |
|---|---|
| Standard 채널 | Gateway API의 GA 채널. 하위 호환을 보장한다 |
| Experimental 채널 | 실험 기능 채널. 바뀌거나 빠질 수 있다 |
| 요청 미러링 | 요청을 복사해 다른 백엔드에도 보내되, 그 응답은 버리는 것 |
| 재시도 예산 | 재시도가 전체 요청에서 차지할 수 있는 상한 |
| InferencePool | 모델 서버 파드 묶음을 나타내는 Inference Extension CRD |

## 참고 자료

- Kubernetes 블로그, Gateway API v1.3.0: <https://kubernetes.io/blog/2025/06/02/gateway-api-v1-3/>
- Kubernetes 블로그, Gateway API Inference Extension 소개: <https://kubernetes.io/blog/2025/06/05/introducing-gateway-api-inference-extension/>
- Gateway API v1.3.0 릴리스: <https://github.com/kubernetes-sigs/gateway-api/releases/tag/v1.3.0>
- Gateway API 버전 정책: <https://gateway-api.sigs.k8s.io/docs/concepts/versioning/>

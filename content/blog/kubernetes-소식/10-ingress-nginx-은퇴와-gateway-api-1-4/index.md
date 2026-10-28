---
title: '[K8s 소식] Ingress NGINX 은퇴 발표, 그리고 Gateway API 1.4'
date: '2025-11-15T16:00:00+09:00'
categories:
- Kubernetes
tags:
- kubernetes
- ingress-nginx
- ingress
- gateway-api
- httproute
- backendtlspolicy
- migration
- cve-2025-1974
- 소식
series:
- Kubernetes 소식
series_order: 10
---

11월 11일 공식 블로그에 Ingress NGINX 은퇴 발표가 올라왔다. 작년 12월 기초 공부 때 kind에 ingress-nginx를 깔고 /foo, /bar를 나눠 본 게 내 첫 인그레스 실습이었고, 지난달에 정리한 '흔한 실수 7가지' 글에서도 처음엔 Ingress-NGINX 같은 기본 컨트롤러로 시작하라고 했다. 그래서 더 놀랐다. 닷새 전에는 Gateway API 1.4 소개 글도 나와서, 옮겨 갈 곳으로 꼽히는 Gateway API까지 같이 정리했다.

## 요약

- Ingress NGINX는 2026년 3월까지만 best-effort로 유지보수한다. 그 뒤로는 릴리스, 버그 수정, 보안 수정이 없고 GitHub 저장소는 읽기 전용이 된다.
- 이미 깔린 ingress-nginx는 계속 동작하고, Helm 차트와 컨테이너 이미지도 남는다. 대체로 만들던 InGate도 같이 은퇴한다.
- 이유는 두 가지다. snippets 어노테이션처럼 예전엔 편의 기능이던 것이 지금은 보안 결함이 됐고, 몇 년 동안 유지보수자가 한두 명뿐이었다.
- 공식 권고는 Gateway API로 옮기거나, 인그레스를 계속 써야 하면 다른 인그레스 컨트롤러로 바로 옮기기 시작하라는 것이다.
- Gateway API v1.4.0(10월 6일 출시)에서 BackendTLSPolicy, GatewayClass의 supportedFeatures, 라우트 규칙 이름이 Standard 채널로 올라왔다. 쿠버네티스 1.26 이상이면 설치할 수 있다.

## 1. Ingress NGINX 은퇴

공식 글을 읽고 흐름을 시간순으로 정리했다.

{{< mermaid >}}
flowchart LR
  A["2024년<br>유지보수자들이<br>단계적 종료와<br>InGate 개발 발표"] --> B["2025-03-24<br>IngressNightmare<br>CVE-2025-1974 (CVSS 9.8)<br>v1.12.1, v1.11.5로 패치"]
  B --> C["2025-11-11<br>은퇴 발표<br>best-effort 유지보수만"]
  C --> D["2026년 3월<br>유지보수 중단<br>저장소 읽기 전용"]
{{< /mermaid >}}

| 항목 | 내용 |
|---|---|
| 2026년 3월 이후 | 릴리스, 버그 수정, 보안 수정 없음. 저장소는 참고용으로 읽기 전용 |
| 이미 쓰는 클러스터 | 갑자기 멈추지 않는다. Helm 차트와 이미지도 계속 받을 수 있다 |
| InGate | 대체 컨트롤러로 개발하던 프로젝트. 충분히 자라지 못해 같이 은퇴 |
| 권고 | Gateway API로 옮기거나, 문서에 있는 다른 인그레스 컨트롤러로 옮긴다. 지금 바로 시작하라고 했다 |

글에서 제일 오래 남은 문장은 '어제의 유연성이 오늘은 감당할 수 없는 기술 부채가 됐다'였다. snippets 어노테이션으로 NGINX 설정을 마음대로 넣을 수 있다는 게 ingress-nginx의 장점이었는데, 지금 기준으로는 심각한 보안 결함이다. 올해 3월의 IngressNightmare가 그 예다. 그때 공식 글에 따르면 특수하게 만든 Ingress 오브젝트로 ingress-nginx가 볼 수 있는 Secret 값을 빼낼 수 있었고, ingress-nginx는 기본으로 클러스터 전체 Secret을 읽을 수 있어서 클러스터 장악까지 이어질 수 있었다. 가장 심각한 CVE-2025-1974는 검증 어드미션 웹훅을 통해 파드 네트워크에 닿기만 하면 인증 없이 공격할 수 있었다. 그 글은 ingress-nginx가 쿠버네티스 클러스터의 40% 넘게 깔려 있다고도 했다.

또 하나는 사람 문제다. 그렇게 널리 쓰이는 프로젝트를 몇 년 동안 한두 명이 퇴근 후와 주말에 개발했다고 한다. 작년에 종료 계획을 발표했는데도 도우려는 사람이 늘지 않았다. 내가 공부할 때 아무 생각 없이 apply 한 줄로 깔던 게 그런 사정 위에 있었다는 걸 이번에 알았다.

## 2. 내 인그레스를 Gateway API로 옮겨 보면

기초 공부 때 쓴 Ingress는 /foo와 /bar를 다른 서비스로 보내는 단순한 규칙이었다. Gateway API로 옮기면 입구(Gateway)와 규칙(HTTPRoute)이 나뉜다. 아직 구현체를 고르지 않아서 gatewayClassName은 example로 두고 매니페스트만 옮겼다.

| Ingress | Gateway API |
|---|---|
| IngressClass | GatewayClass |
| Ingress 하나에 입구와 규칙이 같이 | Gateway(입구, 리스너)와 HTTPRoute(규칙)로 나뉨 |
| spec.tls | Gateway 리스너의 tls |
| pathType Prefix, Exact | path.type PathPrefix, Exact |
| 컨트롤러마다 다른 어노테이션(rewrite, 리다이렉트 등) | HTTPRoute 표준 필터(URLRewrite, RequestRedirect 등) |
| 없음 | 게이트웨이에서 백엔드까지 TLS를 거는 BackendTLSPolicy |

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: demo-gw
spec:
  gatewayClassName: example
  listeners:
  - name: http
    protocol: HTTP
    port: 80
---
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: demo
spec:
  parentRefs:
  - name: demo-gw
  rules:
  - name: foo
    matches:
    - path:
        type: PathPrefix
        value: /foo
    backendRefs:
    - name: foo
      port: 80
  - name: bar
    matches:
    - path:
        type: PathPrefix
        value: /bar
    backendRefs:
    - name: bar
      port: 80
```

rules에 붙인 name이 v1.4에서 Standard가 된 규칙 이름이다. 없어도 되지만, 있으면 상태 메시지나 로그, 정책에서 '두 번째 규칙' 대신 foo 규칙이라고 가리킬 수 있다. 내 Ingress는 어노테이션이 하나도 없어서 이렇게 1대 1로 옮겨졌지만, rewrite-target이나 snippet 어노테이션을 많이 쓴 Ingress는 이렇게 간단하지 않을 것 같다. Ingress를 Gateway API 리소스로 바꿔 주는 ingress2gateway라는 도구가 있다고 해서 다음에 써 볼 생각이다.

## 3. Gateway API 1.4에서 바뀐 것

| 기능 | 채널 | 내용 |
|---|---|---|
| BackendTLSPolicy | Standard | 게이트웨이에서 백엔드 파드까지 가는 구간에 TLS를 건다. hostname은 SNI와 인증서 검증에 쓰고, CA는 caCertificateRefs(최대 8개)나 wellKnownCACertificates: System으로 준다 |
| supportedFeatures | Standard | 구현체가 지원하는 기능을 GatewayClass 상태에 적는다. 적합성 테스트도 이 목록을 보고 돈다 |
| 라우트 규칙 이름 | Standard | rules[].name. 정책이 sectionName으로 특정 규칙만 가리킬 수 있다 |
| ExternalAuth 필터 | Experimental | 요청마다 외부 인증 서비스(HTTP나 gRPC)에 물어서 200이면 통과, 403이면 거절. Envoy ext_authz 기반 |
| XMesh | Experimental | 서비스 메시 전체 설정과 지원 기능을 보는 클러스터 범위 리소스 |
| 기본 게이트웨이 | Experimental | Route에 useDefaultGateways: All, Gateway에 defaultScope: All. 연결 결과는 Route의 status.parents에만 적고 spec은 건드리지 않는다 |
| 클라이언트 인증서 검증 | Experimental | Gateway spec.tls에 기본값과 포트별 설정을 둔다. TLS 연결 재사용으로 리스너별 mTLS를 우회하던 문제를 막는다 |

BackendTLSPolicy 예제 중 시스템 CA를 쓰는 쪽을 옮겼다. dev 서비스의 btls 포트로 갈 때 백엔드가 dev.example.com 인증서를 내야 연결된다.

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: BackendTLSPolicy
metadata:
  name: tls-upstream-dev
spec:
  targetRefs:
  - kind: Service
    name: dev
    group: ""
    sectionName: "btls"
  validation:
    wellKnownCACertificates: "System"
    hostname: dev.example.com
```

지금까지는 인그레스든 게이트웨이든 TLS는 클러스터 입구에서 풀고, 안쪽은 평문으로 가는 게 보통이었다. 이걸 표준 API로 막을 수 있게 됐다.

호환이 깨지는 변경도 두 가지 있었다. Standard GRPCRoute는 이제 spec 필드가 꼭 있어야 하고, Experimental CORS의 allowCredentials는 불리언 값만 받는다. 글을 쓸 당시 v1.4.0 적합성을 통과한 구현체는 Agent Gateway(kgateway와 함께), Airlock Microgateway, Envoy Gateway, GKE Gateway, Istio, kgateway, Traefik Proxy 일곱 개였다.

## 내 클러스터에서 확인할 것

```bash
kubectl get pods --all-namespaces --selector app.kubernetes.io/name=ingress-nginx
kubectl get ingressclass
kubectl get ingress -A -o yaml | grep -o 'nginx.ingress.kubernetes.io/[a-z-]*' | sort | uniq -c
kubectl get crd gateways.gateway.networking.k8s.io -o jsonpath='{.metadata.annotations.gateway\.networking\.k8s\.io/bundle-version}'
```

- 첫 줄에 파드가 나오면 ingress-nginx를 쓰는 것이다. 공식 글도 이 명령을 알려 줬다. 2026년 3월 전에 옮길 곳을 정한다.
- 어노테이션 목록이 옮기는 작업량이다. configuration-snippet 같은 snippet 계열은 다른 컨트롤러에 그대로 대응하는 게 없을 수 있다.
- Gateway API CRD가 깔려 있으면 마지막 줄에 번들 버전(v1.4.0 등)이 나온다. 없으면 구현체를 고른 뒤 같이 설치한다.

> **쉬운 설명**
>
> ingress-nginx는 큰 건물 1층 안내 데스크다. 손님이 오면 어느 층 어느 사무실로 갈지 알려 준다. 이 데스크는 뭐든 부탁하면 다 들어주는 게 장점이었는데(snippets), 나쁜 사람도 그 친절을 이용할 수 있었다. 게다가 데스크를 지키는 사람은 10년 가까이 퇴근 후에 나와 주던 자원봉사자 한두 명뿐이었다. 그래서 내년 3월에 데스크 운영을 끝낸다. 데스크가 갑자기 없어지지는 않지만, 고장 나도 고쳐 줄 사람이 없다. Gateway API는 정문 경비실(Gateway)과 층별 안내판(HTTPRoute)을 나눠서, 건물 관리인은 정문을, 입주사는 자기 안내판만 고치게 하는 새 방식이다.

## 용어 정리

| 용어 | 뜻 |
|---|---|
| 인그레스 컨트롤러 | Ingress 규칙을 읽고 실제로 요청을 받아 전달하는 프로그램 |
| snippets 어노테이션 | Ingress 어노테이션으로 NGINX 설정 조각을 직접 넣는 ingress-nginx 기능 |
| best-effort 유지보수 | 할 수 있는 만큼만 고치는 상태. 보장은 없다 |
| Gateway, HTTPRoute | Gateway API에서 입구(리스너)와 라우팅 규칙을 맡는 리소스 |
| BackendTLSPolicy | 게이트웨이에서 백엔드까지의 TLS 설정을 정하는 Gateway API 리소스 |
| Standard, Experimental 채널 | Gateway API의 GA 채널과 바뀔 수 있는 실험 채널 |

## 참고 자료

- Kubernetes 블로그, Ingress NGINX Retirement: What You Need to Know: <https://kubernetes.io/blog/2025/11/11/ingress-nginx-retirement/>
- Kubernetes 블로그, Ingress-nginx CVE-2025-1974: What You Need to Know: <https://kubernetes.io/blog/2025/03/24/ingress-nginx-cve-2025-1974/>
- Kubernetes 블로그, Gateway API 1.4: New Features: <https://kubernetes.io/blog/2025/11/06/gateway-api-v1-4/>
- Kubernetes 문서, 인그레스 컨트롤러: <https://kubernetes.io/docs/concepts/services-networking/ingress-controllers/>
- Gateway API 문서: <https://gateway-api.sigs.k8s.io/>
- ingress2gateway: <https://github.com/kubernetes-sigs/ingress2gateway>

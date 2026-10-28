---
title: '[K8s 소식] Ingress2Gateway 1.0으로 내 Ingress 변환해 보기, 그리고 Agent Sandbox'
date: '2026-03-28T15:00:00+09:00'
categories:
- Kubernetes
tags:
- kubernetes
- ingress2gateway
- ingress-nginx
- gateway-api
- httproute
- migration
- agent-sandbox
- sig-apps
- gvisor
- kata-containers
- 소식
series:
- Kubernetes 소식
series_order: 16
---

Ingress-NGINX가 3월 24일 예정대로 은퇴했다. GitHub 저장소는 읽기 전용이 됐고, 3월 19일에 나온 controller v1.15.1, v1.14.5, v1.13.9가 마지막 릴리스로 남았다. 그 다음 날 Ingress2Gateway 1.0이 나왔다. 11월부터 '써 볼 생각'이라고만 적어 뒀던 도구라 이번에는 v1.0.0 바이너리를 받아서 내 Ingress와 지난달 글의 함정 예제를 직접 변환해 봤다. 같은 날 나온 Agent Sandbox 소개 글도 짧게 정리했다.

## 요약

- Ingress2Gateway 1.0은 Ingress-NGINX 어노테이션을 30개 넘게 지원한다. 1.0 전에는 3개뿐이었다. CORS, 백엔드 TLS, 정규식 매칭, 경로 재작성 등이 들어갔다.
- 지원하는 어노테이션마다 실제 Ingress-NGINX와 Gateway API 컨트롤러를 띄워 동작이 같은지 비교하는 통합 테스트가 붙었다.
- 직접 돌려 보니 rewrite-target이 붙은 호스트의 다른 Ingress 경로까지 (?i) 정규식으로 바꿔 줬다. 지난달 글의 '같은 호스트 전체가 정규식이 되는' 동작을 도구가 알고 있었다.
- 변환은 끝이 아니다. 경고를 읽고 고친 뒤 개발 클러스터에서 확인하고, 기존 Ingress 옆에 띄워 트래픽을 조금씩 옮기라고 한다.
- Agent Sandbox는 SIG Apps가 만드는 프로젝트로, AI 에이전트처럼 혼자 오래 살고 상태가 있고 대부분 놀고 있는 워크로드를 Sandbox라는 CRD 하나로 다룬다.

## 1. Ingress2Gateway 1.0 써 보기

macOS arm64용 바이너리를 받아 체크섬을 맞춰 보고 실행했다. 클러스터 없이 파일만 넣어도 된다.

```bash
ingress2gateway print --input-file demo-ingress.yaml --providers=ingress-nginx > demo-gw.yaml
ingress2gateway print --providers=ingress-nginx --all-namespaces > gwapi.yaml   # 클러스터에서 바로 읽기
```

### 내 Ingress

기초 공부 때 만든 /foo, /bar Ingress를 넣었다. HTTPRoute 부분만 옮긴다.

```yaml
spec:
  parentRefs:
  - name: nginx
  rules:
  - backendRefs:
    - name: foo
      port: 80
    matches:
    - path:
        type: PathPrefix
        value: /foo
    name: rule-0
  - backendRefs:
    - name: bar
      port: 80
    matches:
    - path:
        type: PathPrefix
        value: /bar
    name: rule-1
```

11월에 손으로 옮긴 것과 거의 같았다. 다른 점은 Gateway 이름과 gatewayClassName이 둘 다 nginx로 나오고, 규칙 이름이 rule-0, rule-1로 자동으로 붙는다는 것이다. 경고는 'Gateway API로는 URL 정규화를 설정할 수 없으니 구현체를 확인하라'는 것 하나였다. 지난달 정리한 다섯 번째 동작이다.

### 지난달의 함정 예제

다섯 가지 동작 글의 세 번째 예제를 그대로 넣었다. rewrite-target이 붙은 Ingress(Exact /IP)와 같은 호스트의 다른 Ingress(Exact /Header, 어노테이션 없음)다.

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  annotations:
    gateway.networking.k8s.io/generator: ingress2gateway-dev
  name: rewrite-target-ingress-rewrite-target-example-com
  namespace: default
spec:
  hostnames:
  - rewrite-target.example.com
  parentRefs:
  - name: nginx
  rules:
  - backendRefs:
    - name: httpbin
      port: 8000
    filters:
    - type: URLRewrite
      urlRewrite:
        path:
          replaceFullPath: /uuid
          type: ReplaceFullPath
    matches:
    - path:
        type: RegularExpression
        value: (?i)/IP.*
    name: rule-0
  - backendRefs:
    - name: httpbin
      port: 8000
    matches:
    - path:
        type: RegularExpression
        value: (?i)/Header.*
    name: rule-1
```

어노테이션이 없던 두 번째 Ingress의 Exact /Header까지 (?i)/Header.* 로 바뀌었고, 두 Ingress가 HTTPRoute 하나로 합쳐졌다. Ingress-NGINX가 실제로 하던 대로(대소문자 무시, prefix, 호스트 전체) 옮겨 준 것이다. 그리고 이렇게 알려 줬다.

| 수준 | 메시지 요지 |
|---|---|
| INFO | 대소문자 무시 정규식 매칭을 쓰고 있다. 바꾸고 싶을 수 있다 |
| WARN | Ingress-NGINX는 이 호스트에 자체 서명 인증서로 TLS도 서비스하는데, 이건 옮기지 않는다. HTTPS로는 접근할 수 없게 된다 |
| WARN | Gateway API는 URL 정규화 설정을 지원하지 않는다 |

두 번째 경고는 생각도 못 했다. Ingress에 tls를 안 적어도 Ingress-NGINX는 기본 가짜 인증서로 443을 열어 두니, 혹시 누가 https로 부르고 있었다면 옮긴 뒤 끊긴다. 생성된 매니페스트는 스키마 검사를 모두 통과했다.

### 공식 글이 권하는 순서

{{< mermaid >}}
flowchart TB
  subgraph s1["준비"]
    direction LR
    A["ingress2gateway print<br>매니페스트와 경고 출력"] --> B["경고 읽고 고치기<br>(?i)와 .* 정리, 타임아웃,<br>필요 없는 80 리스너"]
    B --> C["개발 클러스터에서<br>동작 확인"]
  end
  subgraph s2["전환"]
    direction LR
    D["기존 Ingress 옆에<br>Gateway 같이 띄우기"] --> E["가중치 DNS나 LB로<br>트래픽 조금씩 이동"]
    E --> F["다 옮긴 뒤 Ingress와<br>Ingress 컨트롤러 삭제"]
  end
  s1 --> s2
{{< /mermaid >}}

공식 글의 예제에서는 proxy-read-timeout, proxy-send-timeout(TCP 수준 타임아웃)을 HTTPRoute의 timeouts.request 10s로 '최선을 다해' 바꾸고 확인하라고 경고했고, proxy-body-size는 대응하는 표준 필드가 없어 옮기지 않았다. configuration-snippet은 지원하지 않는다는 경고만 나온다. TLS가 있는 Ingress는 Ingress-NGINX 기본 동작대로 80 리스너와 HTTPS 308 리다이렉트 라우트를 같이 만들어 준다. 기초 공부 때 나를 헤매게 한 그 308이다. --emitter로 agentgateway, envoy-gateway, kgateway를 고르면 구현체 전용 확장으로 더 많이 옮겨 준다고 한다.

## 2. Agent Sandbox

AI 에이전트는 웹 서버와 성격이 다르다. 혼자 돌고(싱글턴), 작업 공간과 상태가 있고, 직접 만든 코드를 실행하니 격리가 필요하고, 몇 시간씩 놀다가 잠깐 일한다. StatefulSet(레플리카 1)과 헤드리스 서비스, PVC를 에이전트마다 조합하면 비슷하게는 되지만 수가 많아지면 관리가 안 된다. 그래서 SIG Apps가 Sandbox라는 CRD를 만들고 있다.

| 기능 | 내용 |
|---|---|
| Sandbox | 쿠버네티스 기본 요소 위에 만든 가벼운 단일 컨테이너 환경 |
| 격리 | gVisor나 Kata Containers 같은 런타임을 골라 커널, 네트워크 수준으로 격리한다 |
| 수명 주기 | 놀고 있는 샌드박스를 0으로 줄였다가 하던 곳부터 다시 시작한다 |
| 고정된 식별자 | 샌드박스마다 고정 호스트 이름과 네트워크 식별자. 에이전트끼리 찾을 수 있다 |
| 확장(Extensions) | SandboxTemplate으로 틀을 정하고, SandboxClaim으로 요청하면 SandboxWarmPool에 미리 띄워 둔 파드를 바로 넘겨준다 |

파드 하나를 새로 띄우는 데 1초쯤 걸리는데, 에이전트가 대화 중에 1초씩 멈추면 흐름이 끊긴다. 그래서 웜 풀을 둔다고 한다. 설치는 릴리스의 manifest.yaml(핵심)과 extensions.yaml(확장)을 kubectl apply하면 되고, 파이썬 SDK(k8s-agent-sandbox)도 있다. 아직 개발 중인 프로젝트라 최신 릴리스를 쓰라고 한다.

## 내 클러스터에서 확인할 것

```bash
kubectl -n ingress-nginx get deploy ingress-nginx-controller -o jsonpath='{..image}{"\n"}'
ingress2gateway print --providers=ingress-nginx --all-namespaces > gwapi.yaml 2> i2g.log
grep -c WARN i2g.log
```

- 컨트롤러 이미지가 v1.15.1, v1.14.5, v1.13.9보다 낮으면 옮기는 동안이라도 마지막 패치까지는 올린다.
- i2g.log의 WARN이 옮길 때 사람이 결정해야 하는 목록이다. configuration-snippet 경고가 있으면 그 호스트부터 본다.
- 생성된 HTTPRoute의 (?i)와 끝의 .* 는 Ingress-NGINX 동작을 그대로 옮긴 것이다. 원래 의도가 정확 매칭이었다면 지금 고칠 기회다.

> **쉬운 설명**
>
> Ingress2Gateway는 옛날 안내 직원의 습관까지 아는 통역사다. 안내판(Ingress)을 새 안내판(Gateway API)으로 옮겨 적으면서, '예전 직원은 대소문자를 안 가렸고 이 층 전체를 그렇게 안내했어요'를 그대로 적어 주고, 옮길 수 없는 습관(설정 조각, 자체 서명 인증서)은 쪽지로 남긴다. 쪽지를 안 읽고 새 안내판만 걸면 손님이 길을 잃는다. Agent Sandbox는 AI 비서마다 내주는 개인 작업실이다. 작업실은 잠겨 있어 옆방에 피해를 주지 않고(격리), 비서가 쉬는 동안엔 불을 꺼 두었다가 부르면 하던 그대로 다시 켜지고, 바로 쓸 수 있게 빈 작업실 몇 개를 미리 청소해 둔다(웜 풀).

## 용어 정리

| 용어 | 뜻 |
|---|---|
| Ingress2Gateway | Ingress와 구현체 어노테이션을 Gateway API 리소스로 바꾸고 못 옮긴 것을 경고하는 도구 |
| provider, emitter | 읽어 들일 Ingress 구현체(ingress-nginx 등)와 출력할 Gateway API 구현체 전용 확장 |
| timeouts.request | HTTPRoute 규칙의 요청 전체 타임아웃 |
| Sandbox | 에이전트용 단일 컨테이너 상태 유지 환경을 정의하는 CRD |
| SandboxWarmPool | 미리 띄워 둔 샌드박스 파드 풀. 콜드 스타트를 없앤다 |
| gVisor, Kata Containers | 컨테이너를 더 강하게 격리하는 런타임. 사용자 공간 커널, 경량 VM |

## 참고 자료

- Kubernetes 블로그, Announcing Ingress2Gateway 1.0: <https://kubernetes.io/blog/2026/03/20/ingress2gateway-1-0-release/>
- Kubernetes 블로그, Running Agents on Kubernetes with Agent Sandbox: <https://kubernetes.io/blog/2026/03/20/running-agents-on-kubernetes-with-agent-sandbox/>
- ingress2gateway v1.0.0 릴리스: <https://github.com/kubernetes-sigs/ingress2gateway/releases/tag/v1.0.0>
- ingress-nginx 릴리스: <https://github.com/kubernetes/ingress-nginx/releases>
- agent-sandbox: <https://github.com/kubernetes-sigs/agent-sandbox>

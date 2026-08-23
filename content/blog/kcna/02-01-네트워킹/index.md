---
title: '[KCNA] 네트워킹: 파드 네트워크 모델, 서비스와 DNS, Ingress와 Gateway API, 서비스 메시'
date: '2026-08-23T15:40:00+09:00'
categories:
- KCNA
tags:
- kubernetes
- kcna
- cni
- service
- kube-proxy
- coredns
- ingress
- gateway-api
- networkpolicy
- service-mesh
- istio
- linkerd
- Container Orchestration
series:
- KCNA
series_order: 6
---

Container Orchestration은 28%로 두 번째로 큰 도메인이다. 네트워킹은 예전 범위의 Networking과 Service Mesh를 합쳐서 봤다. 올해 3월에 Ingress NGINX가 은퇴했고 Gateway API는 v1.6까지 나와서, 인그레스 쪽은 예전 자료와 달라진 내용이 많다. 쿠버네티스 소식에서 따라온 내용을 시험 범위 관점으로 다시 묶었다.

## 요약

- 모든 파드는 고유한 IP를 받고, 다른 파드와 NAT 없이 통신한다. 이 모델을 실제로 만드는 건 CNI 플러그인(Cilium, Calico, Flannel 등)이다.
- 서비스 타입은 ClusterIP(기본), NodePort(30000-32767), LoadBalancer, ExternalName이 있고, `clusterIP: None`이면 헤드리스 서비스다.
- kube-proxy가 노드마다 서비스 규칙을 만든다. 모드는 iptables(기본), nftables(v1.33 stable), ipvs(지원 중단)다.
- CoreDNS가 `<서비스>.<네임스페이스>.svc.cluster.local`을 서비스 IP로 풀어 준다.
- 클러스터 밖 HTTP 트래픽은 Ingress나 Gateway API로 받는다. Ingress API는 그대로지만, Ingress NGINX 프로젝트는 2026년 3월에 은퇴했다.
- NetworkPolicy는 기본이 전부 허용이다. 파드를 고르는 정책이 생기면 그 방향은 허용한 것만 통한다. CNI가 지원해야 동작한다.
- 서비스 메시는 서비스 사이의 mTLS, 재시도, 트래픽 분할, 관찰을 앱 코드 밖에서 처리한다. Istio, Linkerd가 CNCF graduated다.

## 1. 파드 네트워크 모델

쿠버네티스는 네트워크가 지켜야 할 규칙만 정하고, 구현은 CNI 플러그인에 맡긴다.

- 파드마다 클러스터에서 고유한 IP가 있다.
- 파드는 다른 노드의 파드와도 NAT 없이 그 IP로 통신한다.
- 노드의 에이전트(kubelet 등)는 그 노드의 모든 파드와 통신할 수 있다.
- 한 파드 안의 컨테이너들은 네트워크 네임스페이스를 같이 써서 `localhost`로 통신한다.

파드가 생길 때 컨테이너 런타임이 CNI 플러그인을 불러 네트워크 인터페이스를 만들고 IP를 붙인다. CNI 자체는 CNCF 프로젝트인 표준 규격이다.

| CNI 플러그인 | 특징 |
|---|---|
| Cilium | eBPF로 동작한다. NetworkPolicy, kube-proxy 대체, 관찰(Hubble)까지 한다. CNCF graduated |
| Calico | BGP 라우팅이나 오버레이를 쓰고, NetworkPolicy를 지원한다 |
| Flannel | 단순한 오버레이 네트워크. 이것만으로는 NetworkPolicy를 지원하지 않는다 |
| 클라우드 VPC CNI | AWS VPC CNI처럼 파드에 VPC 주소를 직접 준다 |

파드 IP 대역과 서비스 IP 대역은 따로 잡는다. IPv4와 IPv6를 같이 쓰는 듀얼 스택도 지원한다.

## 2. 서비스

파드 IP는 파드가 다시 만들어질 때마다 바뀐다. 서비스는 그 앞에 바뀌지 않는 가상 IP와 이름을 둔다.

{{< mermaid >}}
flowchart LR
  C["클라이언트 파드"] -->|"api.shop.svc.cluster.local"| D["CoreDNS"]
  D -->|"10.96.0.20"| C
  C -->|"10.96.0.20:80"| R["노드의 커널 규칙<br>kube-proxy가 만든 iptables, nftables"]
  R --> P1["api 파드 1"]
  R --> P2["api 파드 2"]
  R --> P3["api 파드 3"]
  ES["EndpointSlice<br>준비된 파드 IP 목록"] -.-> R
{{< /mermaid >}}

| 타입 | 닿는 곳 | 특징 |
|---|---|---|
| ClusterIP | 클러스터 안 | 기본값. 클러스터 밖에서는 닿지 않는다 |
| NodePort | 모든 노드의 같은 포트 | 기본 범위 30000-32767. ClusterIP도 같이 생긴다 |
| LoadBalancer | 클라우드 로드 밸런서 | cloud-controller-manager가 로드 밸런서를 만든다. NodePort와 ClusterIP도 같이 생긴다 |
| ExternalName | 바깥 DNS 이름 | 프록시 없이 CNAME만 돌려준다 |
| 헤드리스(`clusterIP: None`) | 파드 IP 직접 | 가상 IP 없이 DNS가 파드 IP 목록을 돌려준다. StatefulSet과 같이 쓴다 |

```yaml
apiVersion: v1
kind: Service
metadata:
  name: api
  namespace: shop
spec:
  type: ClusterIP
  selector:            # 이 라벨을 가진, 준비된 파드로 보낸다
    app: api
  ports:
  - name: http
    port: 80           # 서비스 포트
    targetPort: 8080   # 파드의 컨테이너 포트
```

서비스 뒤의 파드 목록은 EndpointSlice에 담긴다. 예전 Endpoints API는 v1.33에서 지원 중단됐다. readiness 프로브에 실패한 파드는 목록에서 빠져서 트래픽을 받지 않는다.

kube-proxy 모드는 세 가지다. 기본은 iptables이고, nftables 모드가 v1.33에서 stable이 됐으며, ipvs 모드는 지원 중단됐다. Cilium 같은 CNI는 eBPF로 kube-proxy 역할을 대신하기도 한다.

## 3. DNS

CoreDNS(CNCF graduated)가 클러스터 DNS를 맡는다. kube-system 네임스페이스에 Deployment로 뜨고, 서비스 이름은 역사적인 이유로 `kube-dns`다.

| 이름 | 돌려주는 것 |
|---|---|
| `api.shop.svc.cluster.local` | 서비스의 ClusterIP |
| 헤드리스 서비스 이름 | 준비된 파드 IP들 |
| `web-0.web.shop.svc.cluster.local` | StatefulSet 파드 web-0의 IP(헤드리스 서비스 web 기준) |
| `_http._tcp.api.shop.svc.cluster.local` | 이름 붙은 포트의 SRV 레코드 |

파드의 `/etc/resolv.conf`에는 `shop.svc.cluster.local svc.cluster.local cluster.local` 같은 검색 도메인이 들어 있어서, 같은 네임스페이스면 `api`, 다른 네임스페이스면 `api.shop`만 써도 된다. 파드의 기본 `dnsPolicy`는 ClusterFirst다.

## 4. 클러스터 밖에서 들어오는 HTTP: Ingress와 Gateway API

Ingress는 호스트와 경로를 보고 서비스로 보내는 규칙이다. 규칙만으로는 아무 일도 안 일어나고, Ingress 컨트롤러가 있어야 동작한다. 컨트롤러는 쿠버네티스에 내장되어 있지 않다.

2025년 11월에 쿠버네티스 SIG Network와 보안대응위원회가 Ingress NGINX 은퇴를 발표했고, 2026년 3월 24일에 실제로 은퇴했다. 저장소는 읽기 전용이 됐고 더 이상 릴리스나 보안 패치가 없다. 헷갈리기 쉬운데, 없어진 건 ingress-nginx라는 컨트롤러 프로젝트이고 Ingress API(networking.k8s.io/v1)는 그대로 있다. 옮겨 갈 곳은 다른 Ingress 컨트롤러나 Gateway API다.

Gateway API는 역할에 따라 리소스를 나눈다.

{{< mermaid >}}
flowchart LR
  GC["GatewayClass<br>인프라 제공자<br>어떤 구현을 쓸지"] --> GW["Gateway<br>클러스터 운영자<br>리스너, 포트, TLS"]
  GW --> RT["HTTPRoute<br>앱 개발자<br>호스트, 경로, 가중치"]
  RT --> S1["서비스 api-v1"]
  RT --> S2["서비스 api-v2"]
{{< /mermaid >}}

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: shop
  namespace: shop
spec:
  parentRefs:
  - name: public-gw          # 다른 네임스페이스의 Gateway에 붙는다
    namespace: infra
  hostnames: ["shop.example.com"]
  rules:
  - matches:
    - path:
        type: PathPrefix
        value: /api
    backendRefs:             # 가중치로 트래픽을 나눈다
    - name: api-v1
      port: 80
      weight: 90
    - name: api-v2
      port: 80
      weight: 10
```

| | Ingress | Gateway API |
|---|---|---|
| 상태 | stable, 더 이상 기능이 늘지 않는다(frozen) | 활발히 개발 중. 2026년 8월 기준 v1.6 |
| 설치 | 쿠버네티스에 내장된 API | CRD로 설치한다 |
| 역할 분리 | 리소스 하나에 다 적는다 | GatewayClass, Gateway, Route로 나눈다 |
| 표현력 | 호스트와 경로. 나머지는 컨트롤러별 어노테이션 | 헤더 매칭, 가중치 분할, 미러링, 리다이렉트를 표준 필드로 |
| 프로토콜 | HTTP, HTTPS | HTTPRoute, GRPCRoute, TLSRoute, TCPRoute, UDPRoute |

TLSRoute는 v1.5에서, TCPRoute와 UDPRoute는 v1.6에서 Standard 채널로 올라왔다.

## 5. NetworkPolicy

기본값은 모든 트래픽 허용이다. 어떤 파드를 고르는 정책이 생기면, 그 파드는 정책에 적힌 방향(Ingress, Egress)에서 허용한 트래픽만 받는다. 정책은 허용 규칙만 있고 합집합으로 더해진다. '이건 막아라'라는 규칙은 없다.

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-ingress
  namespace: shop
spec:
  podSelector: {}            # 네임스페이스의 모든 파드
  policyTypes: ["Ingress"]   # 들어오는 트래픽은 아무것도 허용하지 않는다
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-from-frontend
  namespace: shop
spec:
  podSelector:
    matchLabels:
      app: api
  policyTypes: ["Ingress"]
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: frontend
    ports:
    - protocol: TCP
      port: 8080
```

고르는 기준은 podSelector, namespaceSelector, ipBlock이다. NetworkPolicy는 API 서버에 저장될 뿐이고, 실제로 막는 건 CNI 플러그인이다. 지원하지 않는 CNI에서는 만들어도 아무 효과가 없다.

## 6. 서비스 메시

서비스가 많아지면 서비스 사이의 암호화, 재시도, 타임아웃, 카나리 분할, 호출 지표를 앱마다 넣기 힘들다. 서비스 메시는 이걸 앱 밖의 프록시에 맡긴다.

| 구성 | 하는 일 |
|---|---|
| 데이터 플레인 | 실제 트래픽이 지나가는 프록시. 파드마다 붙는 사이드카(Envoy, linkerd2-proxy) 방식과, 노드마다 하나씩 두는 사이드카 없는 방식(Istio ambient 모드)이 있다 |
| 컨트롤 플레인 | 프록시에 설정과 인증서를 나눠 준다(Istio의 istiod 등) |

| 기능 | 예 |
|---|---|
| 보안 | 서비스 사이 mTLS, 서비스 신원 기반 접근 제어 |
| 트래픽 관리 | 재시도, 타임아웃, 서킷 브레이커, 가중치 분할 |
| 관찰 | 요청 수, 오류율, 지연 시간 같은 지표와 분산 트레이싱 |

Istio(2023년)와 Linkerd(2021년)는 CNCF graduated이고, 둘 다 쓰는 Envoy도 graduated다. 서비스 메시 설정을 Gateway API로 맞추려는 작업(GAMMA)도 진행 중이다.

> **쉬운 설명**
>
> 아파트 단지로 보면 파드 IP는 각 집의 호수다. 이사하면 호수가 바뀐다. 서비스는 바뀌지 않는 대표 전화번호이고, CoreDNS는 '관리사무소'라는 이름을 대표 번호로 바꿔 주는 전화번호부다. Ingress와 Gateway는 단지 정문 경비실이다. 손님이 어느 동에 가는지 보고 안내한다. NetworkPolicy는 동 출입문 카드 규칙인데, 아무 규칙이 없으면 누구나 드나들고, 규칙이 생기면 적힌 사람만 들어온다. 서비스 메시는 집집마다 붙은 비서다. 집끼리 통화할 때 비서가 대신 걸어서 암호화하고, 안 받으면 다시 걸고, 통화 기록을 남긴다.

## 헷갈렸던 것들

- ClusterIP는 클러스터 밖에서 닿지 않는다.
- NodePort 기본 범위는 30000-32767이다.
- LoadBalancer 타입은 NodePort와 ClusterIP도 같이 만든다.
- ExternalName은 프록시가 아니라 DNS CNAME이다.
- kube-proxy는 DNS를 하지 않는다. 이름 풀이는 CoreDNS다.
- NetworkPolicy에는 거부 규칙이 없다. 그리고 CNI가 지원해야 동작한다.
- 은퇴한 건 ingress-nginx 컨트롤러다. Ingress API는 남아 있다.
- Gateway API는 쿠버네티스에 내장되지 않고 CRD로 설치한다.

## 용어 정리

| 용어 | 뜻 |
|---|---|
| CNI | 파드에 네트워크를 붙이는 플러그인의 표준 인터페이스 |
| 서비스 | 파드 묶음 앞에 고정 IP와 이름을 두는 오브젝트 |
| EndpointSlice | 서비스 뒤의 파드 IP와 포트 목록 |
| 헤드리스 서비스 | 가상 IP 없이 DNS로 파드 IP를 직접 돌려주는 서비스 |
| Ingress 컨트롤러 | Ingress 규칙을 읽어 실제 프록시를 설정하는 프로그램 |
| Gateway API | Ingress의 뒤를 잇는 역할 기반 트래픽 라우팅 API |
| NetworkPolicy | 파드 단위로 들어오고 나가는 트래픽을 허용하는 규칙 |
| 서비스 메시 | 서비스 간 통신을 프록시로 다루는 인프라 계층 |
| mTLS | 양쪽이 서로 인증서로 신원을 확인하는 TLS |

## 복습 문제

**1.** Which Service type exposes an application on a static port on every node's IP address?

- A. ClusterIP
- B. NodePort
- C. ExternalName
- D. A headless Service

**2.** A cluster uses the default cluster domain. What is the fully qualified DNS name of the Service `api` in the namespace `shop`?

- A. `api.shop.cluster.local`
- B. `api.svc.shop.cluster.local`
- C. `shop.api.svc.cluster.local`
- D. `api.shop.svc.cluster.local`

**3.** Which component implements the Pod network so that every Pod gets its own IP address?

- A. A CNI plugin
- B. kube-proxy
- C. CoreDNS
- D. kube-scheduler

**4.** No NetworkPolicy exists in a namespace. Which traffic can reach the Pods in that namespace?

- A. No traffic
- B. Only traffic from Pods in the same namespace
- C. All traffic
- D. Only traffic from the kube-system namespace

**5.** In the Gateway API, which resource is typically owned by application developers to define routing rules for their Services?

- A. GatewayClass
- B. Gateway
- C. IngressClass
- D. HTTPRoute

**6.** Which Service setting makes DNS return the IP addresses of the backing Pods instead of a single virtual IP?

- A. `type: LoadBalancer`
- B. `clusterIP: None`
- C. `sessionAffinity: ClientIP`
- D. `externalTrafficPolicy: Local`

**7.** What is a primary reason to adopt a service mesh?

- A. To add mutual TLS and traffic management between services without changing application code
- B. To schedule Pods onto nodes
- C. To store container images
- D. To provision persistent volumes

## 답과 풀이

1. **B** NodePort는 모든 노드의 같은 포트(기본 30000-32767)를 연다.
2. **D** `<서비스>.<네임스페이스>.svc.cluster.local` 순서다.
3. **A** CNI 플러그인이 파드에 인터페이스와 IP를 붙이고 노드 사이 경로를 만든다. kube-proxy는 서비스 규칙만 만든다.
4. **C** NetworkPolicy가 하나도 없으면 전부 허용이다.
5. **D** HTTPRoute는 앱 개발자, Gateway는 클러스터 운영자, GatewayClass는 인프라 제공자의 몫이다.
6. **B** 헤드리스 서비스다.
7. **A** mTLS, 재시도, 트래픽 분할, 지표를 프록시가 처리해서 앱 코드를 고치지 않아도 된다.

## 참고 자료

- Kubernetes 문서, 서비스, 로드 밸런싱, 네트워킹: <https://kubernetes.io/docs/concepts/services-networking/>
- Kubernetes 문서, 클러스터 네트워킹: <https://kubernetes.io/docs/concepts/cluster-administration/networking/>
- Kubernetes 문서, 서비스: <https://kubernetes.io/docs/concepts/services-networking/service/>
- Kubernetes 문서, 가상 IP와 서비스 프록시: <https://kubernetes.io/docs/reference/networking/virtual-ips/>
- Kubernetes 문서, 서비스와 파드의 DNS: <https://kubernetes.io/docs/concepts/services-networking/dns-pod-service/>
- Kubernetes 문서, 인그레스: <https://kubernetes.io/docs/concepts/services-networking/ingress/>
- Kubernetes 블로그, Ingress NGINX 은퇴: <https://kubernetes.io/blog/2025/11/11/ingress-nginx-retirement/>
- Gateway API: <https://gateway-api.sigs.k8s.io/>
- Kubernetes 문서, 네트워크 정책: <https://kubernetes.io/docs/concepts/services-networking/network-policies/>
- Istio, Istio란: <https://istio.io/latest/docs/overview/what-is-istio/>
- Linkerd, 서비스 메시란: <https://linkerd.io/what-is-a-service-mesh/>


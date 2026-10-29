---
title: '[K8s 기초] DNS와 서비스 디스커버리: 서비스 이름이 IP로 바뀌는 과정'
date: '2024-12-14T15:30:00+09:00'
categories:
- Kubernetes
tags:
- kubernetes
- dns
- coredns
- service-discovery
- resolv-conf
- ndots
- headless-service
- dnspolicy
- 네트워크
series:
- Kubernetes 기초
series_order: 10
---

서비스 실습에서 wget hostnames만 쳤는데도 서비스에 연결됐다. IP를 쓰지 않았는데 어떻게 찾아갔는지 궁금해서, 파드 안의 DNS 설정과 CoreDNS가 이름을 푸는 순서를 따라가 봤다.

## 요약

- 클러스터 DNS는 kube-system의 CoreDNS가 맡는다. 서비스 이름은 kube-dns로 남아 있고, kind에서는 10.96.0.10이다.
- 서비스는 <서비스>.<네임스페이스>.svc.cluster.local 이름을 받는다. 같은 네임스페이스면 서비스 이름만, 다른 네임스페이스면 서비스.네임스페이스까지 쓰면 된다.
- 짧은 이름이 되는 이유는 파드의 /etc/resolv.conf에 search 도메인이 들어 있어서다.
- ndots:5 때문에 점이 5개 미만인 이름은 search 도메인을 붙여 먼저 물어본다. 외부 도메인도 몇 번 헛걸음을 한 뒤에 찾는다.
- 헤드리스 서비스는 가상 IP 대신 파드 IP들을 돌려준다.

## 1. 클러스터 DNS의 모습

```bash
kubectl -n kube-system get deployment coredns
kubectl -n kube-system get service kube-dns          # CLUSTER-IP 10.96.0.10, 53/UDP 53/TCP
kubectl -n kube-system get configmap coredns -o yaml  # Corefile
kubectl run tmp --image=busybox:1.36 --rm -it --restart=Never -- cat /etc/resolv.conf
```

```
search default.svc.cluster.local svc.cluster.local cluster.local
nameserver 10.96.0.10
options ndots:5
```

kubelet이 파드를 만들 때 이 파일을 넣어 준다. nameserver는 CoreDNS 서비스 주소이고, search 줄 덕분에 짧은 이름을 쓸 수 있다. Corefile에서는 kubernetes 플러그인이 클러스터 안 이름을 답하고, 나머지는 forward로 노드의 DNS에 넘긴다.

| 이름 | 무엇을 돌려주나 |
|---|---|
| web.default.svc.cluster.local | 서비스 web의 ClusterIP |
| web.shop | 다른 네임스페이스 shop의 서비스 web(search가 뒤를 붙여 준다) |
| 헤드리스 서비스 이름 | Ready인 파드 IP 전부 |
| web-0.web.default.svc.cluster.local | 스테이트풀셋 파드 web-0의 IP(헤드리스 서비스와 함께일 때) |
| 10-244-1-5.default.pod.cluster.local | 파드 IP를 이름처럼(점을 -로) |
| _http._tcp.web.default.svc.cluster.local | 이름 붙은 포트의 SRV 레코드(포트 번호까지) |

## 2. 짧은 이름이 풀리는 순서

shop 네임스페이스에서 다른 네임스페이스 서비스를 web.blog으로 불렀을 때를 따라가 봤다. 점이 하나뿐이라 ndots:5보다 적으니, 파드의 resolver가 search 도메인을 하나씩 붙여 본다.

{{< mermaid >}}
sequenceDiagram
  participant P as 파드 (shop 네임스페이스)
  participant D as CoreDNS (10.96.0.10)
  P->>D: web.blog.shop.svc.cluster.local ?
  D-->>P: 없음 (NXDOMAIN)
  P->>D: web.blog.svc.cluster.local ?
  D-->>P: 10.96.42.7 (서비스 web의 ClusterIP)
  Note over P: 찾았으니 여기서 멈춘다
{{< /mermaid >}}

같은 방식이라 api.github.com처럼 점이 2개인 외부 이름도 api.github.com.shop.svc.cluster.local, api.github.com.svc.cluster.local, api.github.com.cluster.local을 먼저 물어보고 나서야 원래 이름을 묻는다. 외부 호출이 아주 많은 앱이면 이름 끝에 점을 붙이거나(api.github.com.) dnsConfig로 ndots를 낮추는 방법이 있다.

```bash
kubectl create namespace blog
kubectl -n blog create deployment web --image=nginx:1.27
kubectl -n blog expose deployment web --port=80
kubectl run q --image=busybox:1.36 --rm -it --restart=Never -- nslookup web.blog
kubectl run q --image=busybox:1.36 --rm -it --restart=Never -- nslookup web.blog.svc.cluster.local
```

## 3. 파드의 DNS 정책

| dnsPolicy | 동작 |
|---|---|
| ClusterFirst(기본) | 클러스터 DNS(CoreDNS)를 쓴다. 클러스터 이름이 아니면 CoreDNS가 위로 넘긴다 |
| Default | 이름과 달리 기본값이 아니다. 노드의 DNS 설정을 그대로 물려받는다 |
| ClusterFirstWithHostNet | hostNetwork 파드인데 클러스터 DNS를 쓰고 싶을 때 |
| None | resolv.conf를 dnsConfig로 직접 채운다 |

서비스를 찾는 다른 방법으로 환경 변수도 있다. 파드가 만들어질 때 같은 네임스페이스에 있던 서비스마다 WEB_SERVICE_HOST, WEB_SERVICE_PORT 같은 변수가 들어간다. 파드보다 나중에 만든 서비스는 안 들어가서, 보통은 DNS를 쓴다.

> **쉬운 설명**
>
> CoreDNS는 회사 내선 전화번호부다. 같은 부서(네임스페이스) 사람은 이름만 말하면 연결되고, 다른 부서는 '이름.부서'로 말해야 한다. search 도메인은 교환원이 짧게 말한 이름 뒤에 '우리 부서', '회사 전체'를 차례로 붙여 번호부를 찾아 주는 습관이다. ndots:5는 그 습관이 너무 열심이라, 바깥 회사 이름을 말해도 먼저 사내 번호부를 몇 번 뒤져 본 뒤에 바깥으로 건다는 뜻이다.

## 헷갈렸던 것들

- 서비스 이름은 kube-dns인데 실제로 도는 건 CoreDNS다. 예전 이름을 그대로 둔 것이다.
- 다른 네임스페이스 서비스는 이름만으로 안 된다. 서비스.네임스페이스까지 쓴다.
- dnsPolicy: Default는 기본값이 아니다. 기본값은 ClusterFirst다.
- busybox의 nslookup은 search 도메인 처리 결과가 헷갈리게 나올 때가 있어서, 확실히 보려면 전체 이름으로 한 번 더 확인했다.
- 서비스 ClusterIP는 ping이 안 되지만 DNS 조회는 된다. 조회가 되는데 접속이 안 되면 DNS가 아니라 서비스나 파드 쪽 문제다.

## 용어 정리

| 용어 | 뜻 |
|---|---|
| CoreDNS | 클러스터 안 이름을 답하는 DNS 서버 |
| 서비스 디스커버리 | 앱이 다른 서비스의 위치를 찾는 방법 |
| search 도메인 | 짧은 이름 뒤에 차례로 붙여 보는 도메인 목록 |
| ndots | 이름에 점이 몇 개 미만이면 search 도메인부터 붙여 볼지 정하는 값 |
| FQDN | 끝까지 다 쓴 이름. 끝에 점을 붙이면 search를 건너뛴다 |
| SRV 레코드 | 서비스의 호스트와 포트 번호를 같이 담은 DNS 레코드 |

## 참고 자료

- Kubernetes 문서, 서비스와 파드의 DNS: <https://kubernetes.io/docs/concepts/services-networking/dns-pod-service/>
- Kubernetes 문서, DNS 문제 디버깅: <https://kubernetes.io/docs/tasks/administer-cluster/dns-debugging-resolution/>
- Kubernetes 문서, DNS 서비스 사용자화: <https://kubernetes.io/docs/tasks/administer-cluster/dns-custom-nameservers/>
- CoreDNS kubernetes 플러그인: <https://coredns.io/plugins/kubernetes/>

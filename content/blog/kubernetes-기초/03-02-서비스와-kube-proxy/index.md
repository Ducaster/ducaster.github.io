---
title: '[K8s 기초] 서비스와 kube-proxy: 바뀌는 파드 IP 앞에 고정 주소 두기'
date: '2024-12-08T16:00:00+09:00'
categories:
- Kubernetes
tags:
- kubernetes
- service
- clusterip
- nodeport
- loadbalancer
- endpointslice
- kube-proxy
- iptables
- 네트워크
series:
- Kubernetes 기초
series_order: 9
---

앞 글에서 파드 IP는 파드가 다시 만들어지면 바뀐다는 걸 확인했다. 그래서 파드 앞에 바뀌지 않는 주소를 하나 세워 두는 게 서비스다. 공식 문서의 서비스 디버깅 예제를 비슷하게 따라 하면서, 서비스 주소로 보낸 요청이 어떻게 파드 셋에 나눠지는지 노드의 iptables 규칙까지 열어 봤다.

## 요약

- 서비스는 셀렉터로 고른 파드들 앞에 고정 가상 IP(ClusterIP)와 DNS 이름을 준다.
- 서비스 뒤의 실제 파드 목록은 EndpointSlice에 있다. Ready인 파드만 들어간다.
- 실제 전달은 노드마다 도는 kube-proxy가 만든 규칙(기본은 iptables)이 한다. ClusterIP는 어떤 인터페이스에도 붙어 있지 않은 가상 주소다.
- 종류는 ClusterIP(안에서만), NodePort(노드 포트로 밖에서), LoadBalancer(클라우드 LB), ExternalName(외부 이름 별칭) 네 가지다.
- port는 서비스가 받는 포트, targetPort는 파드 포트, nodePort는 노드에서 여는 포트다.

## 1. 만들어 보기

```bash
kubectl create deployment hostnames --image=registry.k8s.io/e2e-test-images/agnhost:2.40 --replicas=3 -- /agnhost serve-hostname
kubectl expose deployment hostnames --port=80 --target-port=9376
kubectl get service hostnames
kubectl get endpointslices -l kubernetes.io/service-name=hostnames
```

```
NAME        TYPE        CLUSTER-IP     EXTERNAL-IP   PORT(S)   AGE
hostnames   ClusterIP   10.96.150.42   <none>        80/TCP    5s
```

agnhost는 쿠버네티스 테스트용 이미지인데, serve-hostname으로 실행하면 9376 포트에서 자기 파드 이름을 돌려준다. 문서 예제는 serve_hostname 이미지를 쓰는데, 맥(arm64)에서도 도는 agnhost로 바꿨다. 임시 파드에서 서비스 이름으로 여러 번 불러 봤다.

```bash
kubectl run tmp --image=busybox:1.36 --rm -it --restart=Never -- \
  sh -c 'for i in 1 2 3 4 5 6; do wget -qO- hostnames; echo; done'
# hostnames-xxxxxxxxxx-aaaaa
# hostnames-xxxxxxxxxx-ccccc
# hostnames-xxxxxxxxxx-aaaaa
# hostnames-xxxxxxxxxx-bbbbb ...
```

요청이 세 파드에 무작위로 나뉘었다. 파드 하나를 지워도 새 파드가 셀렉터에 맞으니 EndpointSlice가 자동으로 바뀌고, 서비스 주소는 그대로다.

## 2. 요청이 가는 길

{{< mermaid >}}
flowchart LR
  C["클라이언트 파드"] -->|"hostnames:80<br>(10.96.150.42:80)"| R["보낸 노드의 iptables 규칙<br>(kube-proxy가 만든 것)"]
  R -->|"1/3"| P1["파드 a:9376"]
  R -->|"1/3"| P2["파드 b:9376"]
  R -->|"1/3"| P3["파드 c:9376"]
  ES["EndpointSlice<br>Ready 파드 IP 목록"] -.->|"kube-proxy가 지켜봄"| R
{{< /mermaid >}}

kube-proxy는 이름과 달리 트래픽을 직접 받지 않는다(iptables 모드 기준). 서비스와 EndpointSlice를 지켜보다가 '이 가상 IP:포트로 오면 이 파드 IP들 중 하나로 목적지를 바꿔라(DNAT)'라는 규칙을 노드마다 써 둔다. 패킷은 보낸 쪽 노드에서 바로 목적지가 바뀌어 파드 네트워크로 간다.

```bash
docker exec study-worker iptables -t nat -L KUBE-SERVICES -n | grep hostnames
# KUBE-SVC-XXXXXXXXXXXXXXXX  tcp  --  0.0.0.0/0  10.96.150.42  /* default/hostnames cluster IP */ tcp dpt:80
docker exec study-worker iptables -t nat -L KUBE-SVC-XXXXXXXXXXXXXXXX -n
# statistic mode random probability 0.33333 → KUBE-SEP-... (파드 하나씩)
```

| kube-proxy 모드 | 방식 | 상태(v1.31) |
|---|---|---|
| iptables | 리눅스 iptables 규칙 | 기본값 |
| ipvs | 커널 IPVS 로드 밸런서 | 서비스가 아주 많을 때 쓰던 방식 |
| nftables | iptables의 후속 nftables | beta |

ClusterIP로 ping을 보내면 응답이 없다. 인터페이스가 아니라 TCP·UDP 포트 규칙으로만 존재하는 주소이기 때문이다.

## 3. 서비스 종류

| 종류 | 어디서 부르나 | kind에서 해 보니 |
|---|---|---|
| ClusterIP(기본) | 클러스터 안 | 위 실습 그대로 |
| NodePort | 노드IP:30000~32767 | 노드 컨테이너 안에서 curl localhost:노드포트로 확인했다 |
| LoadBalancer | 클라우드 LB 주소 | EXTERNAL-IP가 pending으로 남았다. 클라우드 컨트롤러가 없어서다 |
| ExternalName | 클러스터 안 | DNS가 외부 이름(CNAME)을 돌려줄 뿐 프록시는 없다 |
| 헤드리스(clusterIP: None) | 클러스터 안 | 가상 IP 없이 DNS가 파드 IP들을 바로 준다(스테이트풀셋 글) |

```bash
kubectl expose deployment hostnames --name=hostnames-np --type=NodePort --port=80 --target-port=9376
kubectl get svc hostnames-np                                  # 80:3xxxx/TCP
docker exec study-worker curl -s localhost:<노드포트>          # 어느 노드로 와도 된다
kubectl expose deployment hostnames --name=hostnames-lb --type=LoadBalancer --port=80 --target-port=9376
kubectl get svc hostnames-lb                                  # EXTERNAL-IP <pending>
```

kind에서 LoadBalancer를 쓰려면 cloud-provider-kind 같은 도구를 따로 띄워야 한다고 해서, 그건 나중으로 미뤘다.

> **쉬운 설명**
>
> 서비스는 회사 대표 전화번호다. 상담원(파드)이 바뀌어도 고객은 같은 번호로 건다. 상담원 명단(EndpointSlice)은 출근해서 응대 준비가 된(Ready) 사람만 올라간다. kube-proxy는 교환원인데, 전화를 직접 받아 넘기는 게 아니라 층마다 '대표번호로 오면 명단 중 아무에게나 연결' 규칙표를 붙여 두는 사람이다. 그래서 전화는 건 사람 자리에서 바로 상담원에게 연결된다. NodePort는 건물 1층마다 둔 직통 내선이고, LoadBalancer는 통신사가 주는 외부 대표번호라 통신사(클라우드)가 없으면 개통이 안 된다.

## 헷갈렸던 것들

- port(서비스), targetPort(파드), nodePort(노드)를 자꾸 섞었다. expose의 --port와 --target-port 순서도 헷갈렸다.
- ClusterIP는 ping이 안 된다. 서비스가 고장 난 게 아니다.
- 서비스는 라벨로 파드를 찾는다. EndpointSlice가 비어 있으면 셀렉터와 라벨이 안 맞거나 파드가 Ready가 아니다.
- kube-proxy는 프록시라는 이름이지만 iptables 모드에서는 규칙만 만들고 트래픽을 받지 않는다.
- NodePort는 아무 노드로 와도 된다. 그 노드에 파드가 없어도 다른 노드의 파드로 넘겨준다.
- kind에서 LoadBalancer가 pending인 건 정상이다.

## 용어 정리

| 용어 | 뜻 |
|---|---|
| 서비스 | 파드 묶음 앞에 고정 주소와 이름을 주는 오브젝트 |
| ClusterIP | 서비스의 가상 IP. 클러스터 안에서만 쓴다 |
| EndpointSlice | 서비스 뒤의 실제 파드 IP·포트 목록 |
| kube-proxy | 노드마다 돌며 서비스 주소를 파드로 보내는 규칙을 만드는 구성 요소 |
| DNAT | 패킷의 목적지 주소를 바꾸는 것 |
| NodePort | 모든 노드의 같은 포트로 서비스를 여는 방식 |

## 참고 자료

- Kubernetes 문서, 서비스: <https://kubernetes.io/docs/concepts/services-networking/service/>
- Kubernetes 문서, 서비스 디버깅: <https://kubernetes.io/docs/tasks/debug/debug-application/debug-service/>
- Kubernetes 문서, 가상 IP와 서비스 프록시: <https://kubernetes.io/docs/reference/networking/virtual-ips/>
- Kubernetes 문서, EndpointSlice: <https://kubernetes.io/docs/concepts/services-networking/endpoint-slices/>
- Kubernetes 튜토리얼, 서비스로 앱 연결하기: <https://kubernetes.io/docs/tutorials/services/connect-applications-service/>
- cloud-provider-kind: <https://github.com/kubernetes-sigs/cloud-provider-kind>

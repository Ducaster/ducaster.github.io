---
title: '[K8s 소식] v1.37 미리보기와 Gateway API v1.6(TCPRoute, UDPRoute 정식)'
date: '2026-08-08T15:00:00+09:00'
categories:
- Kubernetes
tags:
- kubernetes
- v1.37
- kube-proxy
- ipvs
- static-pod
- cgroup-v1
- selinux
- metrics-api
- gateway-api
- tcproute
- udproute
- 소식
series:
- Kubernetes 소식
series_order: 22
---

v1.37이 8월 26일에 나올 예정이라 미리보기 글이 올라왔다. 내가 CKA 때 외운 것들(스태틱 파드, kube-proxy 모드, kubectl run)이 줄줄이 바뀌어서 꼼꼼히 읽었다. 사흘 뒤에는 Gateway API v1.6 소개 글이 나왔다. 실제 출시는 6월 30일이었고, TCPRoute와 UDPRoute가 정식이 됐다.

## 요약

- kubectl run의 --filename(-f)이 지원 중단된다. 어차피 파드는 이름과 --image 같은 CLI 인자로만 만들어졌다.
- 스태틱 파드가 Secret이나 ConfigMap을 참조하던 버그가 막힌다. 예외를 허용하던 PreventStaticPodAPIReferences 기능 게이트도 없어졌다.
- kube-proxy ipvs 모드는 v1.35부터 경고를 냈고, 빠르면 v1.40에 기본으로 꺼지고 v1.43에 제거된다. ipvs 모드도 결국 밑에서 iptables를 쓰기 때문이다.
- cgroup v1은 v1.35부터 kubelet 설정 failCgroupV1 기본값이 true라 시작하지 않지만, failCgroupV1: false로 임시로 우회할 수는 있다.
- metrics.k8s.io API가 9년 가까운 beta를 마치고 GA가 될 예정이다. Gateway API v1.6에서는 TCPRoute, UDPRoute가 v1으로 Standard가 됐고, 실험 리소스는 이제 X 접두사와 별도 API 그룹을 쓴다.

## 1. v1.37 미리보기

| 구분 | 변경 | 내 메모 |
|---|---|---|
| 지원 중단 | kubectl run -f | 시험 때 kubectl run으로 뼈대를 뽑고 -o yaml로 고쳤지 -f를 쓴 적은 없다 |
| 버그 수정(호환 깨짐) | 스태틱 파드의 Secret, ConfigMap 참조 금지 | 스태틱 파드는 API 서버를 거치지 않으니 API 리소스를 읽으면 안 된다. 그동안 configMapRef, secretRef가 버그로 통했다 |
| 지원 중단 일정 | kube-proxy ipvs | v1.35 경고, 빠르면 v1.40 기본 꺼짐(기능 게이트로 선택 가능), v1.43 제거 |
| 진행 중 | cgroup v1 | v1.35부터 failCgroupV1 기본 true. KubeletConfiguration에 failCgroupV1: false를 주면 임시로 뜬다 |
| 호환 깨짐 | SELinuxMount GA | CSI 드라이버가 seLinuxMount: true로 동의한 볼륨은 재귀 라벨링 대신 마운트 옵션으로 라벨을 붙인다. 한 노드에서 SELinux 라벨이 다른 파드가 볼륨을 같이 쓰면 시작에 실패할 수 있다 |
| 기능 | metrics.k8s.io GA | kubectl top과 HPA가 쓰는 API. 기능 변화는 없고 v1과 v1beta1을 같이 쓸 수 있다 |
| 기능 | kubelet rootless 모드 beta | kubelet 같은 노드 구성 요소 자체를 사용자 네임스페이스 안에서 권한 없는 사용자로 돌린다 |
| 기능 | 볼륨 상태 모니터 alpha(재시작) | CSI RPC 4개로 볼륨 상태를 PVC status.healthStatus, 파드 status.volumeHealth, CSINode status.storageHealth에 남긴다 |

ipvs 지원 중단은 v1.35 때 이미 정리했는데, 이번 글에 근거가 한 줄 더 붙었다. 커널 IPVS API만으로는 쿠버네티스 서비스를 다 구현할 수 없어서 ipvs 모드도 밑에서 iptables를 같이 쓴다는 것이다. KEP-3866의 제목이 'ipvs 모드는 우리를 구해 주지 못한다'라고 한다. 기초 공부 때 '서비스가 아주 많을 때 쓰던 방식'이라고만 적어 둔 게 이렇게 정리된다.

{{< mermaid >}}
flowchart LR
  A["v1.8<br>ipvs 모드 도입<br>iptables 성능 문제 해결용"] --> B["v1.35<br>지원 중단<br>시작할 때 경고"]
  B --> C["빠르면 v1.40<br>기본으로 꺼짐<br>기능 게이트로 선택 가능"]
  C --> D["빠르면 v1.43<br>완전히 제거"]
{{< /mermaid >}}

cgroup v1은 내가 잘못 알고 있던 부분을 고쳤다. v1.35 미리보기를 정리할 때 'cgroup v2를 못 쓰는 노드에서는 kubelet이 시작하지 않는다'고 적었는데, 정확히는 failCgroupV1 기본값이 true가 된 것이고 아래처럼 끌 수 있다. 다만 in-place 리사이즈나 계층형 메모리 보호 같은 기능은 cgroup v2가 있어야만 되니 잠깐 버티는 용도라고 한다.

```yaml
apiVersion: kubelet.config.k8s.io/v1beta1
kind: KubeletConfiguration
failCgroupV1: false   # 임시 우회. 언젠가 cgroup v1 지원 자체가 빠진다
```

스태틱 파드 변경도 CKA와 바로 이어진다. 시험 때 /etc/kubernetes/manifests에 YAML을 넣어 스태틱 파드를 만들면서 'API 서버가 없어도 kubelet이 띄운다'는 걸 외웠는데, 그렇다면 API에만 있는 Secret, ConfigMap을 읽는 게 애초에 말이 안 됐던 것이다.

## 2. Gateway API v1.6

| 변경 | 내용 |
|---|---|
| TCPRoute, UDPRoute Standard | 프로토콜과 포트만 보고 L4 트래픽을 보낸다. v1 API가 되고 v1alpha2는 지원 중단 |
| XBackend(Experimental) | Service를 꾸며 주는 Gateway API 전용 백엔드 리소스. 첫 기능은 클러스터 밖 호스트 이름(ExternalHostname)으로 나가는 트래픽 |
| 실험 리소스 분리 | 새 실험 리소스는 gateway.networking.x-k8s.io 그룹에 X 접두사(XBackend, XMesh). Standard가 되면 X를 떼고 정식 그룹으로 옮긴다. TCPRoute, UDPRoute가 옛 방식의 마지막 졸업생이다 |
| 적합성 통과(글 기준) | Agentgateway, Airlock Microgateway, GKE Gateway, kgateway, NGINX Gateway Fabric, Traefik Proxy |

지금까지 데이터베이스, DNS, 게임 서버처럼 HTTP가 아닌 TCP, UDP 서비스는 Gateway에 표준 방식으로 붙일 방법이 없어서 Service type LoadBalancer를 쓰거나 구현체 전용 CRD를 써야 했다. 이제 Gateway에 TCP 리스너를 열고 TCPRoute로 붙인다.

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: example-gateway
spec:
  gatewayClassName: example-gateway-class
  listeners:
  - name: foo
    protocol: TCP
    port: 12345
    allowedRoutes:
      kinds:
      - kind: TCPRoute
---
apiVersion: gateway.networking.k8s.io/v1
kind: TCPRoute
metadata:
  name: tcp-app
spec:
  parentRefs:
  - name: example-gateway
    sectionName: foo
  rules:
  - backendRefs:
    - name: my-foo-service
      port: 6000
```

Gateway 12345 포트로 들어온 연결이 my-foo-service의 6000 포트로 간다. parentRefs에서 sectionName을 빼면 Gateway의 모든 TCP 리스너에 붙는다. UDP는 리스너 protocol과 라우트 kind만 바꾸면 된다.

작년 6월 v1.3부터 Gateway API 릴리스를 계속 따라왔는데, 이번으로 L4부터 L7까지 라우트 종류가 다 Standard에 들어왔다. 그동안 정리한 걸 이어 보면 이렇다.

{{< mermaid >}}
flowchart TB
  subgraph r1[" "]
    direction LR
    A["v1.0 (2023-10)<br>Gateway, GatewayClass,<br>HTTPRoute GA"] --> B["v1.1 (2024-05)<br>GRPCRoute"]
    B --> C["v1.4 (2025-10)<br>BackendTLSPolicy"]
  end
  subgraph r2[" "]
    direction LR
    D["v1.5 (2026-02)<br>TLSRoute, ListenerSet,<br>ReferenceGrant v1"] --> E["v1.6 (2026-06)<br>TCPRoute, UDPRoute"]
  end
  r1 --> r2
{{< /mermaid >}}

XBackend의 첫 용도가 에이전트 워크로드가 바깥 AI API로 나가는 이그레스라는 점도 눈에 띄었다. 3월에 정리한 Agent Sandbox와 같은 흐름이다. 다만 Service에서는 혼동된 대리인(confused deputy) 공격 위험 때문에 외부 호스트 이름을 막아 왔고, XBackend에서도 선택 기능이라 위험을 이해하고 켜라고 했다.

## 내 클러스터에서 확인할 것

```bash
kubectl -n kube-system get configmap kube-proxy -o jsonpath='{.data.config\.conf}' | grep 'mode:'
grep -l -E 'configMapRef|secretRef|configMapKeyRef|secretKeyRef' /etc/kubernetes/manifests/*.yaml   # 컨트롤 플레인 노드에서
kubectl get crd tcproutes.gateway.networking.k8s.io udproutes.gateway.networking.k8s.io -o custom-columns=NAME:.metadata.name,VERSIONS:.spec.versions[*].name
kubectl get apiservice v1beta1.metrics.k8s.io
```

- kube-proxy mode가 ipvs면 nftables로 옮길 계획에 기한이 생겼다. 빠르면 v1.40이다.
- 스태틱 파드 매니페스트에 Secret, ConfigMap 참조가 있으면 v1.37에서 뜨지 않는다. 값은 파일로 넣는 식으로 바꾼다.
- TCPRoute, UDPRoute CRD가 v1alpha2만 있으면 Gateway API v1.6 CRD로 올리고 매니페스트의 apiVersion을 v1으로 바꾼다.
- metrics-server가 v1beta1만 제공하면, GA 뒤에도 당분간은 문제없지만 v1을 제공하는 버전이 나오면 올린다.

> **쉬운 설명**
>
> v1.37 미리보기는 학교 규칙 개정 공지 같다. '교무실 열쇠(Secret)를 학생회 사물함(스태틱 파드)에서 꺼내 쓰던 구멍'을 막고, '옛날 통로(ipvs)는 몇 년 뒤 폐쇄'라고 날짜를 박았다. 옛 건물(cgroup v1)은 이미 출입 금지 팻말이 붙었지만, 급하면 팻말을 잠깐 치울 수는 있다. Gateway API v1.6은 우체국이 편지(HTTP)만 받다가 이제 소포(TCP)와 엽서(UDP)도 정식으로 받는 것이다. 받을 창구(리스너)를 열고, 어디로 보낼지(TCPRoute, UDPRoute)만 적으면 된다.

## 용어 정리

| 용어 | 뜻 |
|---|---|
| 스태틱 파드 | API 서버가 아니라 kubelet이 노드의 매니페스트 파일을 보고 직접 띄우는 파드 |
| failCgroupV1 | cgroup v1 노드에서 kubelet 시작을 실패시킬지 정하는 kubelet 설정. v1.35부터 기본 true |
| SELinuxMount | 볼륨을 마운트할 때 -o context= 옵션으로 SELinux 라벨을 붙이는 기능 |
| metrics.k8s.io | 파드와 노드의 CPU, 메모리 사용량을 주는 API. metrics-server가 제공한다 |
| TCPRoute, UDPRoute | Gateway API의 L4 라우트. 프로토콜과 포트로 백엔드를 고른다 |
| XBackend | Gateway API 실험 리소스. 외부 호스트 이름 같은 백엔드를 정의한다 |

## 참고 자료

- Kubernetes 블로그, Kubernetes v1.37 Sneak Peek: <https://kubernetes.io/blog/2026/07/31/kubernetes-v1-37-sneak-peek/>
- Kubernetes 블로그, Gateway API v1.6: TCPRoute and UDPRoute Graduate to Standard: <https://kubernetes.io/blog/2026/08/03/gateway-api-v1-6-release/>
- KEP-5495, kube-proxy ipvs 모드 지원 중단: <https://github.com/kubernetes/enhancements/issues/5495>
- KEP-5573, cgroup v1 지원 제거: <https://github.com/kubernetes/enhancements/issues/5573>
- Gateway API 문서: <https://gateway-api.sigs.k8s.io/>

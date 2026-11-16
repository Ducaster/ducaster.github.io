---
title: '[K8s 소식] 코드 프리즈 전에 보는 v1.38, Gateway API v1.7, 고치지 않는 ingress-nginx CVE'
date: '2026-11-14T15:00:00+09:00'
categories:
- Kubernetes
tags:
- kubernetes
- v1.38
- kep
- kuberc
- websocket
- statefulset
- gang-scheduling
- dra
- seccomp
- gateway-api
- httproute-retry
- ingress-nginx
- cve
- 소식
series:
- Kubernetes 소식
series_order: 27
---

v1.38은 12월 16일에 나올 예정이다. v1.37 때는 출시 4주쯤 전에 공식 미리보기 글이 올라왔는데, 이번에는 코드 프리즈(11월 17일)도 오기 전이라 아직 없다. 기다리는 대신 릴리스 팀이 추적하는 KEP 목록과 지금까지 나온 CHANGELOG(v1.38.0-beta.0까지)를 직접 읽고 예상을 적어 봤다. 코드 프리즈에서 빠지는 기능이 매번 나오니, 출시 뒤에 이 글과 맞춰 볼 생각이다. 그 사이 10월 29일에 Gateway API v1.7.0이 나왔고, 11월 5일에는 은퇴한 ingress-nginx에 고치지 않는 CVE가 하나 더 붙었다.

## 요약

- 릴리스 일정은 코드 프리즈 11월 17일 21시(한국 시간), 지원 중단·제거 안내 글 11월 23일, 출시 12월 16일이다.
- v1.38 마일스톤에 올라간 KEP는 87개(alpha 42, beta 29, stable 13, 단계 표시 없음 3)다. 이슈 라벨과 kep.yaml의 목표 단계가 다른 것도 있어서 kep.yaml을 기준으로 봤다.
- beta.0 CHANGELOG에 이미 들어간 것: kuberc stable(kubectl.config.k8s.io/v1), kubectl exec·attach·port-forward의 WebSocket 전환 GA, StatefulSet Recreate 전략 beta, DRA 남은 기능 GA, OCI 레지스트리에서 받는 seccomp 프로필 alpha.
- 업그레이드 전에 볼 것: kube-controller-manager의 SeparateTaintEvictionController 기능 게이트가 없어졌다. --feature-gates에 남아 있으면 지운다. kubelet은 env 파일의 KEY='value'#suffix 같은 줄을 이제 거부한다.
- Gateway API v1.7에서 HTTPRoute 재시도(retry)가 Standard가 됐다. ingress-nginx CVE-2026-116472는 심각도 Low지만 고쳐 주지 않는다.

## 1. v1.38 미리보기 (코드 프리즈 전 예상)

### 일정

| 날짜(2026년) | 단계 |
|---|---|
| 9월 30일 | Enhancements Freeze. 이번 릴리스에 넣을 KEP 목록을 닫는다 |
| 11월 4일 | v1.38.0-beta.0 (GitHub 릴리스는 11월 6일에 올라왔다) |
| 11월 17일 21:00 | Code Freeze, Test Freeze (12:00 UTC) |
| 11월 23일 | 지원 중단·제거 안내 글 |
| 12월 3일 | release-1.38 브랜치, v1.38.0-rc.0 |
| 12월 16일 | v1.38.0 출시 |

KEP 목록은 kubernetes/enhancements에서 v1.38 마일스톤과 lead-opted-in 라벨이 붙은 이슈를 모아 봤다. 그런데 갱 스케줄링 이슈에는 stage/beta 라벨이 붙어 있고 kep.yaml에는 stable 목표가 적혀 있었다. 라벨은 늦게 고쳐지기도 해서, 아래 표는 kep.yaml의 stage와 latest-milestone을 기준으로 정리했다.

### 이미 CHANGELOG에 들어간 것

beta.0까지의 CHANGELOG에 들어간 항목은 코드가 이미 머지된 것이라 빠질 가능성이 낮다.

| 구분 | 변경 | 내 메모 |
|---|---|---|
| stable | kuberc. kubectl.config.k8s.io/v1 Preference | 작년 9월 v1.34 beta 때 v1beta1로 써 본 파일이다 |
| GA | kubectl exec, attach, port-forward의 WebSocket 전환(KEP-4006). 관련 기능 게이트 네 개가 켜진 채로 잠긴다 | 시험 때 매일 쓴 명령인데 쓰는 법은 그대로고 통신 방식만 SPDY에서 바뀐다 |
| beta | StatefulSet updateStrategy Recreate | 8월 v1.37에서 alpha. 파드를 모두 지우고 다 끝날 때까지 기다린 뒤 podManagementPolicy 순서대로 새로 만든다 |
| GA | DRA 장치 바인딩 조건, 분할 가능한 장치, 소비형 용량(consumable capacity) | 작년 v1.34에서 DRA 기본 기능이 GA가 된 뒤 남아 있던 기능들 |
| alpha | OCI 레지스트리에서 seccomp 프로필 받기(SecurityProfileOCI) | seccompProfile.type: OCI에 다이제스트로 고정한 oci.ref를 적는다. 노드마다 Localhost 프로필을 깔아 둘 필요가 줄어든다 |
| alpha | EvictionRequest, Eviction API(lifecycle 그룹)와 evictionrequest-controller | 지금의 Eviction API와 PDB만으로는 부족한 협조형 축출을 선언형 API로 |
| GA | 컨테이너 env 파일(EnvFiles, valueFrom.fileKeyRef) | 파일에서 환경 변수 값을 읽는 기능. 파싱이 엄격해졌다(아래) |
| GA | HPA status.observedGeneration | |
| 제거 | metrics.k8s.io/v1alpha1 | 8월에 v1이 GA가 됐고, 쓰는 곳이 없던 v1alpha1이 빠졌다 |
| 변경 | kubectl이 /openapi/v2를 받지 않는다 | 클라이언트 쪽 검증, apply, diff, explain이 v3만 쓴다. explain의 --output=plaintext-openapiv2는 지원 중단 |

WebSocket 전환에는 KCSA 공부와 이어지는 부분이 있었다. WebSocket 핸드셰이크는 HTTP GET이라, 그대로 두면 get만 준 읽기 전용 역할로도 kubectl exec가 되는 구멍이 생긴다. 그래서 API 서버가 pods/exec, pods/attach, pods/portforward로 오는 WebSocket 업그레이드 요청에 create 권한을 한 번 더 확인한다(AuthorizePodWebsocketUpgradeCreatePermission). v1.35부터 기본으로 켜져 있던 이 확인이 이번에 잠겨서 끌 수 없게 된다. pods/exec에는 create 권한이 필요하다고 외운 내용이 프로토콜이 바뀌어도 그대로 맞는다.

StatefulSet Recreate는 KEP에 실린 예가 익숙한 상황이었다. 이미지 태그를 잘못 적으면 RollingUpdate가 첫 파드에서 멈추고, 이미지를 고쳐도 컨트롤러가 망가진 파드를 바꿔 주지 않아서 손으로 지워야 했다. Recreate는 잠깐 다 내려가도 되는 워크로드용이다.

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: web
spec:
  updateStrategy:
    type: Recreate        # OnDelete, RollingUpdate에 이어 세 번째 전략
  podManagementPolicy: OrderedReady
  # serviceName, selector, template은 생략
```

kuberc는 작년 9월에 v1beta1 예제를 그대로 옮겨 써 봤다. v1에서 필드가 달라졌는지는 아직 문서가 없어서 출시 뒤에 확인할 생각이다.

### KEP 목표에는 있지만 아직 CHANGELOG에 없는 것

아래는 kep.yaml에 v1.38 목표가 적혀 있지만 beta.0 CHANGELOG에서는 찾지 못한 KEP다. 코드 프리즈까지 머지되지 않으면 다음 릴리스로 밀린다.

| 목표 | KEP | 내용 |
|---|---|---|
| stable | 파드 단위 리소스(KEP-2837), 파드 단위 리소스의 in-place 리사이즈(KEP-5419) | 파드 전체에 spec.resources를 준다. 작년 10월에 beta를 정리했다 |
| stable | suspend된 Job의 파드 리소스 바꾸기(KEP-5440) | 실행 전에 멈춰 둔 Job의 requests, limits를 바꾼다 |
| stable(조건부) | 갱 스케줄링(KEP-4671) | KEP는 stable이 목표지만, 같은 기능 게이트를 쓰는 워크로드 단위 선점(KEP-5710)과 함께 올라가야 한다고 적혀 있다. KEP-5710은 v1.38 목록에 beta로 올라 있다 |
| beta | 컨테이너 종료 시그널(KEP-4960) | lifecycle.stopSignal. v1.33에서 alpha |
| beta | in-place 리사이즈를 위한 스케줄러 선점(KEP-5836) | v1.37에서 alpha |
| beta | h2c 프로브(KEP-5999), volumeMounts의 noexec·nodev·nosuid(KEP-5855) | 둘 다 v1.37에서 alpha |
| alpha | 실행 중인 파드의 프로브 바꾸기(KEP-6318) | liveness, readiness, startup 프로브를 파드를 다시 만들지 않고 고친다. 컨트롤러의 파드 템플릿에는 반영되지 않는다 |
| alpha | 파드 단위 PID 제한(KEP-6063) | spec.resources.limits.pids. 노드의 podPidsLimit과 둘 중 작은 값이 적용된다 |
| alpha | root로 도는 컨테이너 경고(KEP-2172) | runAsNonRoot 같은 의도 표시 없이 root로 도는 컨테이너에 파드 조건, 경고 이벤트, 지표를 남긴다 |
| alpha | 네트워크 격리 파드(KEP-6313) | 루프백만 있는 네트워크 네임스페이스로 뜨는 파드 |
| alpha | 워크로드가 정하는 swap(KEP-5359) | 컨테이너나 파드마다 swap 양을 직접 정한다. 적지 않으면 swap을 안 쓴다 |

suspend된 Job의 리소스를 바꾸는 KEP-5440은 지난 글의 Kueue처럼 Job을 suspend로 잡아 두는 큐와 같이 쓰일 것 같다.

종료 시그널은 이미지를 다시 빌드하지 않고 STOPSIGNAL을 바꾸는 기능이다. 우선순위는 파드 스펙, 이미지의 STOPSIGNAL, 런타임 기본값(containerd, CRI-O는 SIGTERM) 순이다. spec.os.name을 꼭 적어야 하고, Windows 파드는 SIGTERM, SIGKILL만 된다.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: worker
spec:
  os:
    name: linux                # stopSignal을 쓰려면 필수
  resources:
    limits:
      pids: "2048"             # KEP-6063, alpha 예정. 파드 전체 프로세스 수 상한
  containers:
  - name: app
    image: my-app:1.0
    lifecycle:
      stopSignal: SIGINT       # 이미지의 STOPSIGNAL보다 우선
```

지난 글에서 failCgroupV1: false 우회가 v1.38에서 없어질 예정이라고 적었는데, 고쳐 둘 게 있다. cgroup v1 제거 KEP(KEP-5573)는 v1.38 마일스톤 목록에 없고, kep.yaml의 latest-milestone도 v1.35 그대로다. 블로그 글에 적힌 일정이 실제 추적 목록과 다를 수 있어서, 11월 23일 지원 중단·제거 안내 글에서 다시 확인해야겠다.

### 업그레이드 전에 볼 것

CHANGELOG의 Urgent Upgrade Notes에서 내 클러스터와 관계있을 만한 것만 골랐다.

| 변경 | 할 일 |
|---|---|
| kube-controller-manager에서 SeparateTaintEvictionController 기능 게이트 제거 | --feature-gates에 남아 있으면 업그레이드 전에 지운다. 테인트 기반 축출은 별도 컨트롤러가 계속 맡고, --controllers=-taint-eviction-controller로 끌 수 있다 |
| kubelet이 env 파일의 KEY='value'#suffix를 거부 | 주석이면 # 앞에 공백을 넣고, 값이면 작은따옴표 안으로 넣는다. 고치기 전까지 해당 컨테이너가 시작하지 않을 수 있다 |
| 사용자 네임스페이스(hostUsers: false) ID 범위 버그 수정 | /etc/subuid, /etc/subgid의 kubelet 범위가 4294967295에 닿으면 kubelet이 시작하지 않는다. idsPerPod(기본 65536)만큼 줄인다 |
| 스케줄러 alpha 지표의 type 라벨이 entity로 바뀜 | scheduler_queued_entities 등을 대시보드에서 쓰면 필터를 고친다 |
| 잠겨 있던 GA 기능 게이트 제거 | NodeSwap, ExecProbeTimeout, SystemdWatchdog, KubeletTracing 등. 설정 파일에 남아 있으면 지운다 |

## 2. Gateway API v1.7

10월 29일에 나왔다. 8월에 정리한 v1.6에서 L4 라우트까지 Standard에 들어왔고, 이번에는 HTTPRoute 기능이 하나 더 올라왔다.

| 구분 | 변경 | 내용 |
|---|---|---|
| Standard | HTTPRoute 재시도(GEP-1731) | retry의 codes, attempts, backoff. backoff 동작(특히 지터)은 구현마다 다르다 |
| Standard | 라우트 규칙 name 중복 검사 | HTTPRoute, GRPCRoute 규칙 이름이 겹치면 거절 |
| Standard | BackendTLSPolicy SAN과 TLS 옵션, TLSRoute 혼합 모드 | |
| Experimental | 라우팅 전 필터(GEP-5224) | 라우팅을 정하기 전에 리스너에서 도는 필터. 외부 인증 같은 용도. Gateway와 ListenerSet 리스너 둘 다 |
| Experimental | caCertificateRefs에 ClusterTrustBundle(GEP-5075) | BackendTLSPolicy와 Gateway 프런트엔드 TLS 검증이 CA 묶음을 네임스페이스마다 복사하지 않고 참조한다 |
| Experimental | XTelemetryPolicy(GEP-4768) | Gateway의 분산 트레이싱 설정 표준. 지표와 액세스 로그는 아직 없다 |
| Experimental | Gateway 주소 routability(GEP-5093) | 주소마다 Cluster 같은 범위를 적어서 한 Gateway가 범위가 다른 주소를 함께 쓴다 |
| Experimental | 세션 유지를 XBackend로(GEP-1619, GEP-4894) | 라우트 안이나 BackendTrafficPolicy에 쓰던 세션 유지는 지원 중단 |

Ingress NGINX에서는 proxy-next-upstream 같은 어노테이션으로 하던 재시도가 이제 표준 필드가 됐다. GEP에 실린 예를 옮겼다.

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: retry-example
spec:
  parentRefs:
  - name: example-gateway
  rules:
  - backendRefs:
    - name: some-service
      port: 8080
    retry:
      codes: [500, 502, 503, 504]
      attempts: 2
      backoff: 100ms
```

ClusterTrustBundle은 8월 v1.37에서 GA가 된 걸 정리했는데, Gateway API가 바로 받아 쓰기 시작했다. 실험 채널 쪽은 깨지는 변경이 있다. XBackend의 spec.port.port가 spec.port.number로 바뀌었고, 세션 유지 필드 이름(sessionName, cookieConfig)도 바뀌었다. 적합성 기능 이름 HTTPRouteRetry도 없어지고 HTTPRouteRetryCodes가 생겼다.

{{< mermaid >}}
flowchart LR
  A["v1.5 (2026-02)<br>TLSRoute, ListenerSet"] --> B["v1.6 (2026-06)<br>TCPRoute, UDPRoute"]
  B --> C["v1.7 (2026-10)<br>HTTPRoute 재시도"]
{{< /mermaid >}}

## 3. 고치지 않는 ingress-nginx CVE

11월 5일에 CVE-2026-116472가 공식 CVE 피드에 올라왔다. ingress-nginx의 mirror-target 어노테이션에 검사가 빠져 있어서, Ingress를 만들 수 있는 사용자가 컨트롤러 안의 인증 없는 설정 API에 쓰기 명령을 보낼 수 있다. 그 데이터가 망가지면 Ingress 설정이 바뀌거나 컨트롤러가 재시작될 때까지 ingress-nginx로 가는 트래픽이 모두 버려진다.

| 항목 | 내용 |
|---|---|
| 심각도 | CVSS 2.7, Low. Ingress 생성 권한이 있어야 한다 |
| 영향 | ingress-nginx 데이터 플레인 서비스 거부. 다른 Ingress 트래픽 가로채기도 이론상 되지만 내부 상태 정보가 필요하고, 같은 컨트롤러를 쓰는 사용자는 원래 그럴 수 있어서 추가 위험은 작다고 했다 |
| 수정 | 쿠버네티스 프로젝트는 고치지 않는다. 유지보수가 2026년 3월에 끝났다. SUSE가 자체 포크 1.15.2-prime1에서 고쳤다 |
| 완화 | 어드미션 컨트롤러로 mirror-target 어노테이션이 있는 Ingress를 거절하거나, 컨트롤러 ConfigMap의 annotations-risk-level을 Medium이나 Low로 둔다 |
| 탐지 | mirror-target에 localhost 주소가 있으면 공격 시도일 수 있다 |

6월에 '고치지 않는 CVE 네 개'를 정리할 때는 설계상 못 고치는 오래된 문제들이었는데, 이번에는 프로젝트가 끝나서 고치지 않는 경우다. 3월 은퇴 공지 때 예고된 상황이 실제로 왔다. 요즘 KCSA를 보고 있어서인지, Ingress 생성 권한만 있는 사용자가 어노테이션 하나로 공유 컨트롤러를 멈추는 경로가 위협 모델에서 정리한 서비스 거부 항목의 예로 그대로 쓸 만해 보였다.

## 내 클러스터에서 확인할 것

```bash
# 컨트롤 플레인 노드에서. 없어진 기능 게이트가 남아 있나
grep -n 'feature-gates' /etc/kubernetes/manifests/kube-controller-manager.yaml
# Gateway API CRD 버전과 채널
kubectl get crd gateways.gateway.networking.k8s.io -o yaml | grep -E 'bundle-version|channel'
# ingress-nginx가 있나, mirror-target을 쓰는 Ingress가 있나
kubectl get pods -A -l app.kubernetes.io/name=ingress-nginx
kubectl get ingress -A -o json | jq -r '.items[]
  | select(.metadata.annotations["nginx.ingress.kubernetes.io/mirror-target"] != null)
  | "\(.metadata.namespace)/\(.metadata.name)\t\(.metadata.annotations["nginx.ingress.kubernetes.io/mirror-target"])"'
```

- --feature-gates에 SeparateTaintEvictionController나 잠긴 GA 게이트가 있으면 v1.38 전에 지운다.
- env 파일을 쓰는 파드가 있으면 작은따옴표 바로 뒤에 #이 붙은 줄이 없는지 본다.
- ingress-nginx가 아직 있으면 mirror-target을 막는 어드미션 규칙부터 넣고, Ingress2Gateway로 옮기는 계획을 앞당긴다.
- Gateway API 실험 채널에서 XBackend나 세션 유지를 쓰고 있으면 v1.7로 올릴 때 필드 이름을 바꾼다.

> **쉬운 설명**
>
> 코드 프리즈 전 미리보기는 영화 개봉 전에 촬영 목록을 보고 이번 편에 나올 장면을 짐작하는 것과 같다. CHANGELOG에 이미 들어간 것은 촬영이 끝난 장면이라 거의 나오고, KEP 목록에만 있는 것은 촬영 예정 장면이라 편집에서 잘릴 수 있다. ingress-nginx CVE는 문 닫은 가게에서 산 자물쇠의 결함이다. 가게가 없어져서 아무도 고쳐 주지 않으니, 계속 쓰려면 문 앞에 직접 경비를 세우거나(어드미션으로 어노테이션 막기) 다른 자물쇠로 바꿔야(Gateway API) 한다.

## 용어 정리

| 용어 | 뜻 |
|---|---|
| Code Freeze | 이 날 이후로는 새 기능 코드를 머지하지 않는 릴리스 단계 |
| Enhancements Freeze | 이번 릴리스에 넣을 KEP 목록을 닫는 단계 |
| kep.yaml | KEP마다 현재 단계, 목표 버전, 기능 게이트를 적은 파일 |
| kuberc | kubectl 개인 설정 파일. 별칭과 기본 옵션을 kubeconfig와 따로 둔다 |
| Recreate(StatefulSet) | 파드를 모두 지운 뒤 새로 만드는 업데이트 전략 |
| HTTPRoute retry | 백엔드 응답 코드에 따라 요청을 다시 보내는 Gateway API 설정 |
| mirror-target | 요청을 다른 주소로 복사해 보내는 ingress-nginx 어노테이션 |

## 참고 자료

- Kubernetes v1.38 릴리스 일정: <https://github.com/kubernetes/sig-release/blob/master/releases/release-1.38/README.md>
- Kubernetes v1.38 CHANGELOG: <https://github.com/kubernetes/kubernetes/blob/master/CHANGELOG/CHANGELOG-1.38.md>
- v1.38 마일스톤 KEP 이슈 목록: <https://github.com/kubernetes/enhancements/issues?q=is%3Aissue+milestone%3Av1.38+label%3Alead-opted-in>
- KEP-4006, SPDY에서 WebSocket으로: <https://github.com/kubernetes/enhancements/issues/4006>
- KEP-4671, 갱 스케줄링: <https://github.com/kubernetes/enhancements/issues/4671>
- KEP-4960, 컨테이너 종료 시그널: <https://github.com/kubernetes/enhancements/issues/4960>
- KEP-5573, cgroup v1 지원 제거: <https://github.com/kubernetes/enhancements/issues/5573>
- Gateway API v1.7.0 릴리스: <https://github.com/kubernetes-sigs/gateway-api/releases/tag/v1.7.0>
- GEP-1731, HTTPRoute 재시도: <https://gateway-api.sigs.k8s.io/geps/gep-1731/>
- CVE-2026-116472: <https://github.com/kubernetes/kubernetes/issues/143852>


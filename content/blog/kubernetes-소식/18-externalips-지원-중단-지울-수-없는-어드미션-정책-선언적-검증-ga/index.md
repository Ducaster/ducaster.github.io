---
title: '[K8s 소식] Service externalIPs 지원 중단 일정, 지울 수 없는 어드미션 정책, 선언적 검증 GA'
date: '2026-05-16T15:00:00+09:00'
categories:
- Kubernetes
tags:
- kubernetes
- v1.36
- service
- externalips
- cve-2020-8554
- metallb
- admission
- validatingadmissionpolicy
- declarative-validation
- 소식
series:
- Kubernetes 소식
series_order: 18
---

v1.36 후속 글이 4월 말부터 거의 매일 올라오고 있다. 이번에는 세 편을 골랐다. 3주 전에 표 한 줄로만 적은 Service externalIPs 지원 중단의 자세한 일정과 대안, API로는 지울 수 없게 파일로 넣는 어드미션 정책, 그리고 쿠버네티스 내장 타입의 검증 코드를 태그로 바꾼 선언적 검증 GA다.

## 요약

- Service의 spec.externalIPs는 클러스터의 모든 사용자를 믿는다는 전제로 만든 필드라, 서비스를 만들 수 있는 사람이면 남의 트래픽을 가로챌 수 있다(CVE-2020-8554). v1.36에서 지원 중단됐다.
- 일정은 v1.36 경고, 빠르면 v1.40에 kube-proxy에서 기본으로 꺼짐(다시 켤 수 있음), 빠르면 v1.43에 완전히 꺼짐이다.
- 노드의 ExternalIP 주소나 kubectl get svc의 EXTERNAL-IP 칸과는 다른 이야기다. spec.externalIPs를 안 쓰면 해당이 없다.
- v1.36 alpha인 매니페스트 기반 어드미션은 정책을 API 서버 디스크의 파일로 넣는다. 이름은 .static.k8s.io로 끝나야 하고, API로는 지울 수 없고, 다른 어드미션 정책을 지우지 못하게 막는 데도 쓸 수 있다.
- 선언적 검증이 GA가 됐다. 손으로 쓴 검증 코드 약 18,000줄을 types.go의 +k8s: 태그와 validation-gen 생성기로 바꾸는 작업이다. 바꾸지 않은 필드는 새 검증 규칙을 건너뛴다.

## 1. Service externalIPs, 왜 없애나

기초 공부 때 kind에서 LoadBalancer 서비스를 만들면 EXTERNAL-IP가 pending으로 남았다. 그 칸은 이번 이야기와 관계가 없다. 이번에 지원 중단된 건 Service spec에 직접 IP를 적는 externalIPs 필드다. 클라우드가 없는 클러스터에서 로드밸런서처럼 쓰려고 만든 초기 기능인데, 문제는 아무 확인 없이 아무 IP나 적을 수 있다는 점이다.

{{< mermaid >}}
flowchart LR
  A["자기 네임스페이스에서<br>서비스만 만들 수 있는 사용자"] -->|"spec.externalIPs:<br>203.0.113.10"| S["Service evil"]
  S --> KP["모든 노드의 kube-proxy가<br>203.0.113.10행 트래픽을<br>evil 파드로 보내는<br>규칙 추가"]
  P["다른 팀 파드가<br>외부 203.0.113.10에 요청"] --> KP
  KP --> E["evil 파드가<br>요청을 가로챔"]
{{< /mermaid >}}

그래서 v1.21부터 끄라고 권했고, 막아 주는 DenyServiceExternalIPs 어드미션 플러그인도 넣었다. 그때는 기본으로 막으면 호환이 너무 많이 깨진다고 봤는데, '기본이 안전하지 않은' 상태를 더 두지 않기로 했다고 한다.

{{< mermaid >}}
flowchart LR
  A["v1.21<br>끄라고 권고<br>DenyServiceExternalIPs 추가"] --> B["v1.36<br>지원 중단<br>쓰면 경고"]
  B --> C["빠르면 v1.40<br>kube-proxy에서 기본 꺼짐<br>다시 켤 방법은 남김"]
  C --> D["빠르면 v1.43<br>완전히 꺼짐"]
{{< /mermaid >}}

| 대안 | 방법 | 평가 |
|---|---|---|
| 손으로 관리하는 LoadBalancer | 없는 loadBalancerClass로 서비스를 만들고, status에 IP를 kubectl patch --subresource=status로 넣는다 | 가장 쉽지만 가장 나쁘다고 했다. status는 RBAC상 일반 사용자가 못 고친다는 점만 낫다 |
| 클라우드 밖 LB 컨트롤러(MetalLB 등) | 관리자가 IPAddressPool로 쓸 IP 범위를 정하고, 사용자는 type: LoadBalancer만 만든다 | 컨트롤러가 IP 중복을 막는다. loadBalancerIP로 특정 IP를 요청할 수도 있다 |
| Gateway API | 관리자가 Gateway의 spec.addresses에 IP를 붙이고, 앱은 HTTPRoute로 붙는다 | Gateway를 만들 권한을 RBAC로 관리자에게만 줄 수 있다 |

kubectl patch --subresource=status 방식이 재미있었다. 작년 5월에 in-place 리사이즈를 하면서 --subresource resize를 처음 썼는데, 같은 옵션으로 status만 따로 고칠 수 있다.

## 2. 지울 수 없는 어드미션 정책

ValidatingAdmissionPolicy나 웹훅 설정은 API 오브젝트라서 두 가지 틈이 있다. 클러스터가 막 뜨거나 백업에서 복구할 때 정책을 만들기 전까지는 정책이 없고, 권한이 큰 사용자는 정책 자체를 지울 수 있다. 웹훅과 정책은 자기 설정 리소스에 대한 요청은 검사하지 않기 때문이다(자기를 고치는 요청까지 막으면 아무도 못 고치게 되니까).

v1.36 alpha인 매니페스트 기반 어드미션은 정책을 API 서버가 읽는 디렉터리의 파일로 둔다. AdmissionConfiguration에 staticManifestsDir를 적으면 API 서버가 요청을 받기 전에 그 파일들을 먼저 읽는다.

```yaml
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingAdmissionPolicy
metadata:
  name: "deny-privileged.static.k8s.io"
  annotations:
    kubernetes.io/description: "Deny launching privileged pods, anywhere this policy is applied"
spec:
  failurePolicy: Fail
  matchConstraints:
    resourceRules:
    - apiGroups: [""]
      apiVersions: ["v1"]
      operations: ["CREATE", "UPDATE"]
      resources: ["pods"]
  variables:
  - name: allContainers
    expression: >-
      object.spec.containers +
      (has(object.spec.initContainers) ? object.spec.initContainers : []) +
      (has(object.spec.ephemeralContainers) ? object.spec.ephemeralContainers : [])
  validations:
  - expression: >-
      !variables.allContainers.exists(c,
        has(c.securityContext) && has(c.securityContext.privileged) &&
        c.securityContext.privileged == true)
    message: "Privileged containers are not allowed"
---
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingAdmissionPolicyBinding
metadata:
  name: "deny-privileged-binding.static.k8s.io"
spec:
  policyName: "deny-privileged.static.k8s.io"
  validationActions:
  - Deny
  matchResources:
    namespaceSelector:
      matchExpressions:
      - key: "kubernetes.io/metadata.name"
        operator: NotIn
        values: ["kube-system"]
```

이 예제를 보면서 작년 12월에 정리한 설정 모범 사례 글의 kubernetes.io/description 어노테이션이 여기서도 쓰인 게 눈에 들어왔다. 파일에만 있는 정책이라 설명을 어노테이션에 남겨 두는 게 더 의미가 있다.

| 알아 둘 점 | 내용 |
|---|---|
| 켜는 법 | kube-apiserver에 ManifestBasedAdmissionControlConfig 기능 게이트, AdmissionConfiguration에 staticManifestsDir |
| 이름 | 모든 오브젝트 이름이 .static.k8s.io로 끝나야 한다. 감사 로그나 지표에서 어디서 온 결정인지 바로 보인다 |
| 정책을 지키는 정책 | 파일 기반 정책은 어드미션 설정 리소스에 대한 요청도 검사할 수 있다. 특정 라벨이 붙은 정책, 웹훅 설정의 수정과 삭제를 막는 예제가 있다 |
| 제약 | 클러스터 상태 없이 동작해야 해서 paramKind를 못 쓰고, 웹훅은 서비스 참조 없이 URL만, 바인딩은 같은 파일 묶음의 정책만 가리킨다 |
| 여러 API 서버 | 서버마다 자기 파일을 읽는다. 동기화는 없고, 지표 라벨의 설정 해시로 어긋남을 찾는다 |
| 바꿀 때 | 파일을 감시하다가 새 설정이 유효하면 통째로 바꾸고, 아니면 이전 설정을 유지하고 로그를 남긴다 |
| 처음 시작할 때 | 파일 하나라도 잘못되면 API 서버가 아예 뜨지 않는다. 정책 없이 도는 것보다 낫다는 판단이다 |

CKA 공부 때 /etc/kubernetes/manifests의 스태틱 파드를 API로 지워도 kubelet이 다시 띄우는 걸 보고 신기했는데, 같은 생각을 어드미션 정책에 적용한 셈이다. 고칠 때는 API가 아니라 노드의 파일을 고친다.

## 3. 선언적 검증 GA

사용자 입장에서는 눈에 잘 안 띄는 변화지만 규모가 크다. 쿠버네티스 내장 타입(Pod, Service 같은)의 검증은 지금까지 Go로 손으로 짠 함수였고, 그게 약 18,000줄이었다고 한다. 이제는 types.go의 필드 위에 태그를 달면 validation-gen이 검증 코드를 만들어 준다.

```go
type ReplicationControllerSpec struct {
	// +k8s:optional
	// +k8s:minimum=0
	Replicas *int32 `json:"replicas,omitempty"`
}
```

| 태그 종류 | 예 |
|---|---|
| 있어야 하나 | +k8s:optional, +k8s:required |
| 기본 제약 | +k8s:minimum=0, +k8s:maximum=100, +k8s:maxLength=16, +k8s:format=k8s-short-name |
| 목록 | +k8s:listType=map, +k8s:listMapKey=type |
| 유니언 | +k8s:unionMember, +k8s:unionDiscriminator |
| 변경 불가 | +k8s:immutable, +k8s:update=[NoSet, NoModify, NoClear] |

제일 좋아 보인 건 '앰비언트 래칫팅'이다. 이미 있는 오브젝트를 고칠 때, 사용자가 바꾸지 않은 필드는 새로 강화된 검증을 건너뛴다. 예전에는 검증을 조이려면 래칫팅 코드를 먼저 넣고 한 릴리스를 기다려야 했는데, 이제는 기본으로 된다. 나중에는 이 규칙들을 OpenAPI 스키마로 내보내서 kubectl이나 IDE가 요청을 보내기 전에 검사할 수 있게 하고, Kubebuilder로 만드는 CRD에도 같은 방식을 쓰게 하는 게 목표라고 한다. 그렇게 되면 작년 12월에 kubeconform으로 YAML 불리언 함정을 잡은 것 같은 검사를 kubectl이 직접 해 줄 수도 있겠다.

## 내 클러스터에서 확인할 것

```bash
kubectl get svc -A -o custom-columns=NS:.metadata.namespace,SVC:.metadata.name,EXTERNAL_IPS:.spec.externalIPs | grep -v '<none>'
kubectl -n kube-system get pod -l component=kube-apiserver -o yaml | grep -o 'enable-admission-plugins=[^"]*'
kubectl get validatingadmissionpolicies,validatingadmissionpolicybindings
```

- EXTERNAL_IPS 칸이 채워진 서비스가 없으면 enable-admission-plugins에 DenyServiceExternalIPs를 넣어 앞으로도 못 쓰게 막아 둔다.
- 있으면 MetalLB 같은 LB 컨트롤러나 Gateway API로 옮긴다. 빠르면 v1.40부터 kube-proxy가 기본으로 무시한다.
- 꼭 지켜야 하는 정책(특권 컨테이너 금지 같은)이 API 오브젝트로만 있다면, 누가 지울 수 있는지 RBAC부터 본다. 파일 기반은 아직 alpha다.

> **쉬운 설명**
>
> externalIPs는 아파트 게시판에 '이 주소로 오는 택배는 우리 집으로'라고 아무나 붙일 수 있는 것과 같다. 경비실(kube-proxy)은 확인 없이 그대로 따라서, 남의 택배가 엉뚱한 집으로 간다. 그래서 게시판을 없애고, 관리사무소(관리자, MetalLB, Gateway)가 주소를 배정하게 바꾸는 중이다. 파일 기반 어드미션 정책은 아파트 규약을 관리사무소 서랍이 아니라 건물 벽에 새겨 두는 것이다. 서랍 속 규약은 열쇠를 가진 사람이 꺼내 버릴 수 있지만, 벽에 새긴 규약은 건물을 고쳐야만 바뀐다.

## 용어 정리

| 용어 | 뜻 |
|---|---|
| spec.externalIPs | Service에 추가로 응답할 IP를 직접 적는 필드. v1.36에서 지원 중단 |
| CVE-2020-8554 | externalIPs와 LoadBalancer status를 이용한 클러스터 내 중간자 공격 취약점 |
| DenyServiceExternalIPs | externalIPs 사용을 막는 어드미션 플러그인 |
| MetalLB | 클라우드 밖 클러스터에서 LoadBalancer 서비스에 IP를 주는 컨트롤러 |
| staticManifestsDir | API 서버가 시작할 때 읽는 어드미션 정책 파일 디렉터리 |
| 선언적 검증 | +k8s: 태그로 내장 타입의 검증 규칙을 적고 코드를 생성하는 방식 |
| 래칫팅 | 기존 오브젝트의 바뀌지 않은 값에는 새로 강화된 검증을 적용하지 않는 것 |

## 참고 자료

- Kubernetes 블로그, Deprecation and removal of Service ExternalIPs: <https://kubernetes.io/blog/2026/05/14/kubernetes-v1-36-deprecation-and-removal-of-service-externalips/>
- Kubernetes 블로그, Admission Policies That Can't Be Deleted: <https://kubernetes.io/blog/2026/05/04/kubernetes-v1-36-manifest-based-admission-control/>
- Kubernetes 블로그, Declarative Validation Graduates to GA: <https://kubernetes.io/blog/2026/05/05/kubernetes-v1-36-declarative-validation-ga/>
- Kubernetes 문서, 서비스(외부 IP 항목): <https://kubernetes.io/docs/concepts/services-networking/service/>
- Kubernetes 문서, ValidatingAdmissionPolicy: <https://kubernetes.io/docs/reference/access-authn-authz/validating-admission-policy/>
- CVE-2020-8554 이슈: <https://github.com/kubernetes/kubernetes/issues/97076>

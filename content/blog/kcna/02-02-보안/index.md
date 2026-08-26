---
title: '[KCNA] 보안: 4C, 인증과 인가와 어드미션, RBAC, ServiceAccount, Pod Security, Secret'
date: '2026-08-26T22:00:00+09:00'
categories:
- KCNA
tags:
- kubernetes
- kcna
- security
- 4c
- authentication
- authorization
- rbac
- admission
- serviceaccount
- pod-security-standards
- pod-security-admission
- securitycontext
- secret
- Container Orchestration
series:
- KCNA
series_order: 7
---

보안은 KCSA에서 따로 깊게 다루는 범위라, KCNA에서는 '무엇이 무엇을 막는가'를 구분하는 데까지 정리했다. 401과 403, Role과 ClusterRole, PSS와 PSA, base64와 암호화처럼 짝으로 묻기 좋은 것들이 많다. CKA 때 RBAC와 NetworkPolicy는 손으로 많이 해 봤는데, 어드미션과 Pod Security는 이름만 알고 있었다.

## 요약

- 4C는 Cloud, Cluster, Container, Code다. 바깥 층이 뚫리면 안쪽 층만으로는 지킬 수 없다.
- API 요청은 인증(누구인가), 인가(해도 되나), 어드미션(고치거나 거절) 순서로 지난다. 인증에 실패하면 401, 인가에 실패하면 403이다.
- 쿠버네티스에는 사용자 오브젝트가 없다. 사람은 인증서나 OIDC 같은 외부 수단으로, 앱은 ServiceAccount로 인증한다.
- RBAC는 Role·ClusterRole(무엇을 할 수 있나)과 RoleBinding·ClusterRoleBinding(누구에게)으로 이루어진다. 허용 규칙만 있고, 적히지 않은 건 모두 거부다.
- Pod Security Standards는 Privileged, Baseline, Restricted 세 단계이고, Pod Security Admission이 네임스페이스 라벨을 보고 enforce, audit, warn으로 적용한다.
- securityContext로 root 실행 금지, 권한 상승 금지, 읽기 전용 루트 파일 시스템, capabilities 제거, seccomp를 건다.
- Secret 값은 base64로 인코딩될 뿐 암호화되지 않는다. etcd 저장 암호화와 RBAC로 지킨다.

## 1. 4C

{{< mermaid >}}
flowchart TB
  subgraph cloud["Cloud: 클라우드 계정, 네트워크, 노드 OS"]
    subgraph cluster["Cluster: API 서버 접근, RBAC, etcd, NetworkPolicy"]
      subgraph container["Container: 이미지, 런타임, securityContext"]
        code["Code: 앱 코드, 의존성, TLS, 비밀값 다루기"]
      end
    end
  end
{{< /mermaid >}}

| 층 | 지킬 것의 예 |
|---|---|
| Cloud | 클라우드 IAM, 컨트롤 플레인 엔드포인트를 인터넷에 열지 않기, 노드 OS 패치, etcd 접근 제한 |
| Cluster | API 서버 인증과 RBAC, NetworkPolicy, Secret 암호화, 감사 로그 |
| Container | 신뢰할 수 있는 작은 이미지, 취약점 스캔, root가 아닌 사용자, 강한 격리가 필요하면 샌드박스 런타임 |
| Code | 입력 검증, 의존성 취약점 관리, 서비스 간 TLS, 비밀값을 코드에 넣지 않기 |

안쪽 층은 바깥 층을 믿고 있다. 노드 OS가 뚫리면 그 위의 컨테이너 설정은 의미가 약해진다.

## 2. API 요청이 지나는 관문

{{< mermaid >}}
flowchart TB
  R["요청<br>kubectl, 파드 안의 앱, 컨트롤러"] --> A1{"인증<br>누구인가"}
  A1 -->|"실패"| X1["401 Unauthorized"]
  A1 -->|"성공"| A2{"인가<br>이 동작을 해도 되나"}
  A2 -->|"거부"| X2["403 Forbidden"]
  A2 -->|"허용"| M["변경 어드미션<br>기본값 채우기, 사이드카 넣기"]
  M --> V{"검증 어드미션<br>쿼터, Pod Security, 정책"}
  V -->|"위반"| X3["거절"]
  V -->|"통과"| E[("etcd에 저장")]
{{< /mermaid >}}

| 단계 | 방법 |
|---|---|
| 인증 | X.509 클라이언트 인증서, 베어러 토큰(ServiceAccount 토큰), OIDC, 웹훅 토큰 인증, 인증 프록시. 아무것도 없으면 `system:anonymous` |
| 인가 | Node(kubelet용), RBAC, Webhook, ABAC. kubeadm 기본은 Node와 RBAC |
| 어드미션 | 내장 플러그인(NamespaceLifecycle, LimitRanger, ResourceQuota, PodSecurity 등), 웹훅(MutatingAdmissionWebhook, ValidatingAdmissionWebhook), CEL로 적는 ValidatingAdmissionPolicy(v1.30 stable) |

변경 어드미션이 먼저 돌고 검증 어드미션이 나중에 돈다. 고친 결과를 검증해야 하기 때문이다. OPA Gatekeeper와 Kyverno 같은 정책 엔진은 어드미션 웹훅으로 붙는다. Kyverno는 올해 3월에 CNCF graduated가 됐다.

## 3. RBAC

| 오브젝트 | 범위 | 하는 일 |
|---|---|---|
| Role | 네임스페이스 | 그 네임스페이스 안의 리소스에 대한 권한 목록 |
| ClusterRole | 클러스터 | 클러스터 범위 리소스(Node 등) 권한, 또는 여러 네임스페이스에 재사용할 권한 목록 |
| RoleBinding | 네임스페이스 | Role이나 ClusterRole을 사용자, 그룹, ServiceAccount에 그 네임스페이스 안에서만 준다 |
| ClusterRoleBinding | 클러스터 | ClusterRole을 클러스터 전체에 준다 |

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: pod-reader
  namespace: shop
rules:
- apiGroups: [""]              # core 그룹
  resources: ["pods", "pods/log"]
  verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: ci-reads-pods
  namespace: shop
subjects:
- kind: ServiceAccount
  name: ci
  namespace: shop
roleRef:
  kind: Role
  name: pod-reader
  apiGroup: rbac.authorization.k8s.io
```

```bash
kubectl auth can-i list pods -n shop --as=system:serviceaccount:shop:ci   # yes
kubectl auth can-i delete pods -n shop --as=system:serviceaccount:shop:ci # no
```

미리 만들어진 ClusterRole로 cluster-admin, admin, edit, view가 있다. RBAC에는 거부 규칙이 없어서, 권한은 필요한 것만 더해 가는 방식(최소 권한)으로 준다. `*` 와일드카드와 cluster-admin 바인딩은 꼭 필요할 때만 쓴다.

## 4. ServiceAccount

파드 안의 앱이 API 서버를 부를 때 쓰는 신원이다. 네임스페이스마다 `default` ServiceAccount가 있고, 파드에 따로 적지 않으면 이걸 쓴다. API 서버 입장에서 이름은 `system:serviceaccount:<네임스페이스>:<이름>`이다.

토큰은 projected 볼륨으로 파드에 들어간다. 유효 기간과 대상(audience)이 있고 파드에 묶여 있어서, 파드가 지워지면 쓸 수 없다. v1.24부터는 ServiceAccount마다 만료 없는 토큰 Secret을 자동으로 만들지 않는다. API를 부를 일이 없는 앱은 `automountServiceAccountToken: false`로 토큰을 아예 안 넣는다.

## 5. 파드 보안: PSS, PSA, securityContext

Pod Security Standards는 파드 설정의 안전 수준을 세 단계로 정의한 표준이다.

| 단계 | 뜻 | 막는 것의 예 |
|---|---|---|
| Privileged | 제한 없음 | 없음. 시스템 구성 요소용 |
| Baseline | 알려진 권한 상승을 막는 최소 기준 | privileged 컨테이너, hostNetwork, hostPID, hostPath, 위험한 capabilities 추가 |
| Restricted | 강하게 조인 모범 사례 | Baseline에 더해 root 실행, 권한 상승 허용, capabilities 남기기(ALL drop 필요), seccomp 미설정 |

Pod Security Admission은 이 표준을 적용하는 내장 어드미션 컨트롤러다(v1.25 stable). 네임스페이스에 라벨을 붙여 쓴다.

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: shop
  labels:
    pod-security.kubernetes.io/enforce: restricted   # 어기면 파드 생성 거절
    pod-security.kubernetes.io/warn: restricted      # 어기면 사용자에게 경고
    pod-security.kubernetes.io/audit: restricted     # 어기면 감사 로그에 기록
```

| 모드 | 위반하면 |
|---|---|
| enforce | 파드 생성을 거절한다 |
| warn | 생성은 되고 사용자에게 경고를 보여 준다 |
| audit | 생성은 되고 감사 로그에 표시한다 |

예전의 PodSecurityPolicy는 v1.25에서 제거됐고, 그 자리를 PSA가 이어받았다. 더 세밀한 규칙이 필요하면 Kyverno나 Gatekeeper를 쓴다.

Restricted를 통과하는 파드는 이렇게 생겼다.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: hardened
  namespace: shop
spec:
  securityContext:
    runAsNonRoot: true
    seccompProfile:
      type: RuntimeDefault
  containers:
  - name: api
    image: registry.example.com/shop/api:1.4.2
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      capabilities:
        drop: ["ALL"]
```

## 6. Secret

| 타입 | 쓰임 |
|---|---|
| Opaque | 일반 키-값 |
| kubernetes.io/tls | TLS 인증서와 키 |
| kubernetes.io/dockerconfigjson | 비공개 레지스트리 인증 정보 |
| kubernetes.io/service-account-token | 예전 방식의 ServiceAccount 토큰 |

Secret 값은 base64로 인코딩해서 저장할 뿐 암호화가 아니다. Secret을 get할 수 있는 사람이나 etcd에 접근하는 사람은 그대로 읽는다. 지키는 방법은 이렇다.

- etcd에 저장할 때 암호화한다(API 서버의 EncryptionConfiguration, 외부 KMS 연동).
- Secret 읽기 권한을 RBAC로 좁힌다. 네임스페이스에 파드를 만들 수 있는 사람은 그 파드에 Secret을 마운트해서 읽을 수 있다는 점도 기억한다.
- 바뀌면 안 되는 값은 `immutable: true`로 둔다.
- 외부 저장소(HashiCorp Vault, 클라우드 비밀 관리자)를 External Secrets Operator나 Secrets Store CSI Driver로 연결한다.

Secret 하나의 크기는 1MiB까지다.

> **쉬운 설명**
>
> 회사 건물 출입으로 보면 인증은 사원증 확인이고, 인가는 '이 사원증으로 7층에 갈 수 있나' 확인이다. 어드미션은 검색대다. 이름표를 붙여 주기도 하고(변경), 반입 금지 물품이 있으면 돌려보낸다(검증). RBAC의 Role은 '7층 회의실 사용 가능' 같은 권한 목록이고, RoleBinding은 그 목록을 누구 사원증에 연결할지다. Pod Security Admission은 층마다 붙은 복장 규정이다. restricted 층에는 정장(root 금지, 권한 상승 금지)이 아니면 못 들어간다. Secret은 봉투에 넣은 쪽지일 뿐 금고가 아니다. 금고로 만들려면 따로 잠가야(저장 암호화) 한다.

## 헷갈렸던 것들

- 401은 인증 실패, 403은 인가 실패다.
- RBAC에는 거부 규칙이 없다. 적히지 않은 건 다 거부다.
- ClusterRole을 RoleBinding으로 묶으면 그 네임스페이스 안에서만 권한이 생긴다.
- base64는 인코딩이지 암호화가 아니다.
- PodSecurityPolicy는 v1.25에서 없어졌다. 지금은 PSA다.
- PSA의 warn과 audit는 파드를 거절하지 않는다. 거절은 enforce만 한다.
- 변경 어드미션이 검증 어드미션보다 먼저 돈다.

## 용어 정리

| 용어 | 뜻 |
|---|---|
| 4C | Cloud, Cluster, Container, Code로 나눈 클라우드 네이티브 보안의 층 |
| 인증 | 요청한 쪽이 누구인지 확인하는 단계 |
| 인가 | 그 사람이 그 동작을 해도 되는지 판단하는 단계 |
| 어드미션 컨트롤러 | 인가 뒤에 요청을 고치거나 거절하는 플러그인 |
| RBAC | 역할 기반 접근 제어. Role과 Binding으로 권한을 준다 |
| ServiceAccount | 파드 안의 프로세스가 쓰는 쿠버네티스 신원 |
| Pod Security Standards | Privileged, Baseline, Restricted 세 단계 파드 보안 기준 |
| Pod Security Admission | 네임스페이스 라벨로 PSS를 적용하는 내장 어드미션 컨트롤러 |
| securityContext | 파드나 컨테이너의 사용자, 권한, 커널 기능 설정 |

## 복습 문제

**1.** A request to the API server fails with HTTP 401 Unauthorized. Which stage rejected the request?

- A. Authentication
- B. Authorization
- C. Mutating admission
- D. Validating admission

**2.** Which pair of objects grants permissions within a single namespace?

- A. ClusterRole and ClusterRoleBinding
- B. ServiceAccount and Secret
- C. Role and RoleBinding
- D. NetworkPolicy and Namespace

**3.** By default, which statement about Kubernetes Secrets is true?

- A. Their values are encrypted with AES in etcd.
- B. Their values are only base64-encoded, which is not encryption.
- C. Only the cluster-admin role can read them.
- D. They are stored outside etcd.

**4.** Which Pod Security Standards profile is the most restrictive?

- A. Privileged
- B. Baseline
- C. Default
- D. Restricted

**5.** How does Pod Security Admission decide which profile to apply to a Pod?

- A. From labels on the Pod's namespace
- B. From annotations on each container
- C. From a PodSecurityPolicy object
- D. From the taints on the node

**6.** Which identity should an application running in a Pod use to call the Kubernetes API?

- A. A User object
- B. The node's kubeconfig file
- C. A ServiceAccount
- D. The cluster-admin client certificate

**7.** In the 4C model of cloud native security, which layer is the outermost?

- A. Code
- B. Cloud
- C. Cluster
- D. Container

## 답과 풀이

1. **A** 인증에 실패하면 401, 인증은 됐지만 권한이 없으면 403이다.
2. **C** Role과 RoleBinding은 네임스페이스 범위다.
3. **B** 기본으로는 base64 인코딩만 된다. 저장 암호화는 따로 설정해야 한다.
4. **D** Restricted가 가장 엄격하다. 'Default'라는 단계는 없다.
5. **A** `pod-security.kubernetes.io/<모드>` 네임스페이스 라벨로 정한다.
6. **C** 쿠버네티스에는 User 오브젝트가 없다. 파드 안의 앱은 ServiceAccount 토큰으로 인증한다.
7. **B** 바깥부터 Cloud, Cluster, Container, Code 순서다.

## 참고 자료

- Kubernetes 문서, 클라우드 네이티브 보안과 쿠버네티스: <https://kubernetes.io/docs/concepts/security/cloud-native-security/>
- Kubernetes 문서, API 접근 제어: <https://kubernetes.io/docs/concepts/security/controlling-access/>
- Kubernetes 문서, 인증: <https://kubernetes.io/docs/reference/access-authn-authz/authentication/>
- Kubernetes 문서, RBAC: <https://kubernetes.io/docs/reference/access-authn-authz/rbac/>
- Kubernetes 문서, 어드미션 컨트롤러: <https://kubernetes.io/docs/reference/access-authn-authz/admission-controllers/>
- Kubernetes 문서, ValidatingAdmissionPolicy: <https://kubernetes.io/docs/reference/access-authn-authz/validating-admission-policy/>
- Kubernetes 문서, ServiceAccount: <https://kubernetes.io/docs/concepts/security/service-accounts/>
- Kubernetes 문서, Pod Security Standards: <https://kubernetes.io/docs/concepts/security/pod-security-standards/>
- Kubernetes 문서, Pod Security Admission: <https://kubernetes.io/docs/concepts/security/pod-security-admission/>
- Kubernetes 문서, 보안 컨텍스트: <https://kubernetes.io/docs/tasks/configure-pod-container/security-context/>
- Kubernetes 문서, Secret: <https://kubernetes.io/docs/concepts/configuration/secret/>
- Kubernetes 문서, 저장된 Secret 암호화: <https://kubernetes.io/docs/tasks/administer-cluster/encrypt-data/>


---
title: '[KCSA] Pod Security Standards와 Admission, 인증, RBAC: 무엇을 막고 누구에게 무엇을 허락하나'
date: '2026-10-13T21:30:00+09:00'
categories:
- KCSA
tags:
- kubernetes
- kcsa
- pod-security-standards
- pod-security-admission
- authentication
- oidc
- serviceaccount
- rbac
- system-masters
- privilege-escalation
- Kubernetes Security Fundamentals
series:
- KCSA
series_order: 4
---

Kubernetes Security Fundamentals(22%)는 항목이 일곱 개라 두 편으로 나눴고, 이 글은 Pod Security Standards, Pod Security Admission, Authentication이다. 범위에 Authorization이라는 항목은 따로 없지만, 인증한 뒤에 무엇을 허락하느냐가 빠지면 이야기가 안 돼서 RBAC도 여기 넣었다. KCNA 때는 세 단계 이름만 외웠는데, 이번에는 단계마다 정확히 무엇을 막는지와 RBAC에서 위험한 권한이 무엇인지를 봤다.

## 요약

- PSS는 Privileged(제한 없음), Baseline(알려진 권한 상승 막기), Restricted(강하게 조인 모범 사례) 세 단계다.
- PSA는 네임스페이스 라벨로 enforce, audit, warn을 고른다. enforce는 파드에만 걸리고, audit와 warn은 Deployment 같은 워크로드 리소스의 파드 템플릿에도 걸린다.
- 인증 수단은 X.509 클라이언트 인증서, ServiceAccount 토큰, OIDC, 웹훅, 인증 프록시다. 인증이 끝나면 사용자 이름과 그룹만 남고, 인가는 그걸 보고 판단한다.
- `system:masters` 그룹은 RBAC를 건너뛴다.
- RBAC는 허용만 있다. 위험한 권한은 Secret의 get, list, watch, 파드 생성, `pods/exec`, `nodes/proxy`, `escalate`, `bind`, `impersonate`, ServiceAccount 토큰 생성이다.

## 1. Pod Security Standards

| 단계 | 막는 것 |
|---|---|
| Privileged | 없다. CNI, 로그 수집기처럼 노드 권한이 필요한 시스템 구성 요소용 |
| Baseline | privileged 컨테이너, hostNetwork·hostPID·hostIPC, hostPath 볼륨, hostPort, 기본 목록 밖의 capabilities 추가(`SYS_ADMIN` 등), AppArmor·SELinux 해제, `/proc` 마운트 변경, seccomp `Unconfined`, 안전하지 않은 sysctl, Windows HostProcess |
| Restricted | Baseline 전부에 더해 허용된 볼륨 종류만(configMap, secret, emptyDir, PVC, projected 등), 권한 상승 금지(`allowPrivilegeEscalation: false`), root 실행 금지(`runAsNonRoot: true`), seccomp `RuntimeDefault`나 `Localhost` 필수, capabilities `ALL` 제거(`NET_BIND_SERVICE`만 다시 더할 수 있다) |

Baseline은 '아무 설정 안 한 평범한 파드는 통과하되, 노드로 넘어가는 길은 막는다'는 수준이다. 그래서 root 실행은 Baseline에서 허용되고 Restricted에서 막힌다.

## 2. Pod Security Admission

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: payments
  labels:
    pod-security.kubernetes.io/enforce: baseline
    pod-security.kubernetes.io/enforce-version: v1.36   # 이 버전의 기준으로 고정
    pod-security.kubernetes.io/warn: restricted
    pod-security.kubernetes.io/audit: restricted
```

| 모드 | 위반하면 | 어디에 걸리나 |
|---|---|---|
| enforce | 파드 생성을 거절한다 | 파드에만 |
| warn | 생성은 되고 kubectl에 경고가 나온다 | 파드와 워크로드 리소스의 파드 템플릿 |
| audit | 생성은 되고 감사 로그 이벤트에 표시된다 | 파드와 워크로드 리소스의 파드 템플릿 |

enforce가 파드에만 걸리기 때문에 생기는 함정이 있다. 규칙을 어기는 Deployment를 만들면 Deployment 자체는 만들어진다. 대신 ReplicaSet이 파드를 만들려다 계속 거절되고, `kubectl get deploy`에서 READY가 0으로 남는다. 원인은 ReplicaSet의 이벤트에 나온다. warn을 같이 걸어 두면 Deployment를 만들 때 바로 경고가 보인다.

- `-version` 라벨을 안 주면 latest다. 쿠버네티스를 올리면 기준이 바뀔 수 있어서 버전을 고정하기도 한다.
- 이미 떠 있는 파드에는 소급되지 않는다. 라벨을 바꾸면 위반하는 기존 파드에 대한 경고만 나온다.
- 라벨을 걸기 전에 `kubectl label --dry-run=server --overwrite ns payments pod-security.kubernetes.io/enforce=restricted`로 어떤 파드가 걸리는지 미리 본다.
- 클러스터 전체 기본값과 예외(특정 사용자 이름, RuntimeClass, 네임스페이스)는 API 서버의 AdmissionConfiguration에서 정한다. kube-system처럼 시스템 구성 요소가 도는 네임스페이스는 보통 privileged로 둔다.

PSA로 표현할 수 없는 규칙(특정 레지스트리만 허용, 라벨 필수 등)은 ValidatingAdmissionPolicy나 Kyverno, OPA Gatekeeper로 더한다.

## 3. 인증

{{< mermaid >}}
flowchart LR
  H["사람<br>OIDC ID 토큰,<br>클라이언트 인증서"] --> A{"인증"}
  P["파드 안의 앱<br>ServiceAccount 토큰"] --> A
  N["kubelet<br>인증서 CN=system:node:이름,<br>O=system:nodes"] --> A
  A --> I["사용자 정보<br>이름, 그룹"]
  I --> Z{"인가<br>Node, RBAC"}
{{< /mermaid >}}

| 방법 | 쓰임 | 주의 |
|---|---|---|
| X.509 클라이언트 인증서 | 구성 요소, 관리자 | CN이 사용자 이름, O가 그룹이다. 하나씩 폐기할 수 없다 |
| ServiceAccount 토큰 | 파드 안의 앱 | TokenRequest API로 받는 기한 있고 파드에 묶인 토큰이 기본이다 |
| OIDC | 사람 | 외부 IdP(Keycloak, 클라우드 IAM 등)에서 받은 짧은 수명 ID 토큰. 그룹을 IdP에서 관리한다 |
| 웹훅 토큰 인증 | 외부 인증 서비스 연동 | 토큰을 외부 서비스에 물어 확인한다 |
| 인증 프록시 | 앞단 프록시가 인증 | 헤더로 사용자를 넘긴다. 프록시 아닌 곳에서 헤더를 못 넣게 해야 한다 |
| 정적 토큰 파일 | 쓰지 않는다 | 바꾸려면 API 서버를 재시작해야 하고 기한이 없다 |
| 부트스트랩 토큰 | 노드 가입 | kubeadm join에 짧게 쓴다 |

인증이 끝나면 남는 건 사용자 이름과 그룹뿐이다. 특별한 그룹이 몇 개 있다.

| 그룹 | 뜻 |
|---|---|
| `system:authenticated` | 인증된 모든 요청 |
| `system:unauthenticated` | 익명 요청 |
| `system:serviceaccounts`, `system:serviceaccounts:<네임스페이스>` | ServiceAccount 전부, 그 네임스페이스의 ServiceAccount |
| `system:nodes` | kubelet. Node 인가 모드가 이 그룹을 본다 |
| `system:masters` | RBAC를 거치지 않고 모든 권한을 가진다. 이 그룹의 인증서는 비상용으로만 둔다 |

ServiceAccount 쪽에서 챙길 것은 이렇다. 파드마다 필요한 권한만 가진 ServiceAccount를 따로 만든다. API를 부르지 않는 파드는 `automountServiceAccountToken: false`로 토큰을 넣지 않는다. 기한 없는 Secret 방식 토큰을 새로 만들지 않는다. default ServiceAccount에는 권한을 주지 않는다.

`--as`로 다른 사용자인 척 요청하는 사칭(impersonation)도 있다. `impersonate` 권한이 있으면 더 높은 사용자로 행동할 수 있어서 위험한 권한으로 분류된다.

## 4. 인가와 RBAC

인가 모드는 Node, RBAC, Webhook, ABAC, AlwaysAllow, AlwaysDeny가 있다. 보통 `Node,RBAC`이고, 여러 모드를 걸면 하나라도 허용하면 허용이다. RBAC 규칙은 apiGroups, resources(하위 리소스 포함), verbs, resourceNames로 적는다.

RBAC에는 거부 규칙이 없어서, 권한이 한번 넓게 나가면 그만큼 열린다. 쿠버네티스 문서의 RBAC 모범 사례가 꼽는 위험한 권한은 이렇다.

| 권한 | 왜 위험한가 |
|---|---|
| secrets의 get, list, watch | list와 watch도 Secret 값을 그대로 돌려준다. get만 막는다고 안전하지 않다 |
| pods의 create(워크로드 리소스 포함) | 그 네임스페이스의 아무 Secret이나 마운트하고, 아무 ServiceAccount나 쓰는 파드를 만들 수 있다. PSA가 없으면 privileged 파드로 노드까지 간다 |
| `pods/exec`, `pods/attach` | 실행 중인 컨테이너 안에서 명령을 실행한다 |
| `nodes/proxy` | kubelet API에 직접 닿아 감사 로그와 어드미션을 건너뛸 수 있다 |
| `escalate`(roles) | 자기에게 없는 권한을 가진 Role을 만들거나 고친다 |
| `bind`(rolebindings) | 자기에게 없는 권한의 Role을 남에게(자기에게도) 묶는다 |
| `impersonate` | 다른 사용자, 그룹, ServiceAccount인 척한다 |
| `serviceaccounts/token`의 create | 다른 ServiceAccount의 토큰을 발급받는다 |
| persistentvolumes의 create | hostPath PV로 노드 파일 시스템에 닿는다 |
| 웹훅 설정 수정 | 모든 요청을 가로채거나 정책을 끈다 |
| `certificatesigningrequests/approval` | 원하는 신원의 인증서를 승인한다 |

```bash
kubectl auth can-i --list -n payments                      # 내 권한 목록
kubectl auth can-i get secrets -n payments --as=system:serviceaccount:payments:api
kubectl get clusterrolebindings -o wide | grep cluster-admin   # cluster-admin을 가진 주체
```

쿠버네티스는 권한 상승을 막는 장치를 RBAC에 넣어 두었다. Role을 만들거나 바인딩하려면, 원래는 그 Role이 담은 권한을 내가 이미 가지고 있어야 한다. `escalate`와 `bind`는 이 검사를 건너뛰게 해 주는 동사라서 위험하다.

> **쉬운 설명**
>
> Pod Security Standards는 건물의 복장 규정이다. Privileged 층은 아무 옷이나 된다. Baseline 층은 작업복(privileged)과 공구 벨트(hostPath)는 안 되지만 사복은 된다. Restricted 층은 정장에 넥타이까지(root 금지, 권한 상승 금지) 맞춰야 한다. PSA는 층 입구의 경비원인데, enforce면 돌려보내고, warn이면 '복장이 안 맞는다'고 말만 하고, audit면 장부에만 적는다. RBAC는 열쇠 꾸러미다. 문제는 열쇠 복사기(bind, escalate)와 남의 신분증(impersonate)을 같이 나눠 주면, 꾸러미에 없던 문도 열 수 있다는 것이다.

## 헷갈렸던 것들

- Baseline은 root 실행을 막지 않는다. Restricted가 막는다.
- enforce는 파드에만 걸린다. 위반하는 Deployment는 만들어지고 파드만 안 생긴다.
- PSA 라벨은 이미 떠 있는 파드에 소급되지 않는다.
- `system:masters`는 RBAC를 건너뛴다.
- Secret의 list와 watch도 값을 돌려준다.
- 파드 생성 권한이 있으면 그 네임스페이스의 Secret과 ServiceAccount를 쓸 수 있다.
- bind는 바인딩, escalate는 Role 자체에 대한 동사다.

## 용어 정리

| 용어 | 뜻 |
|---|---|
| Pod Security Standards | 파드 설정의 보안 수준을 세 단계로 정한 기준 |
| Pod Security Admission | 네임스페이스 라벨로 PSS를 적용하는 내장 어드미션 컨트롤러 |
| OIDC | 외부 IdP가 발급한 ID 토큰으로 사용자를 인증하는 표준 |
| TokenRequest API | 기한과 대상이 있는 ServiceAccount 토큰을 발급하는 API |
| 사칭 | 다른 사용자나 그룹인 척 요청을 보내는 기능 |
| escalate, bind | RBAC 권한 상승 방지 검사를 건너뛰게 하는 동사 |
| system:masters | RBAC를 우회하는 특수 그룹 |

## 복습 문제

**1.** Which Pod Security Standards profile blocks privileged containers and hostPath volumes but still allows containers to run as root?

- A. Privileged
- B. Restricted
- C. Baseline
- D. Default

**2.** A namespace has the labels `enforce: baseline` and `warn: restricted`. A user creates a Pod that meets Baseline but runs as root. What happens?

- A. The Pod is rejected.
- B. The Pod is created, and the user sees a warning.
- C. The Pod is created, and the violation is recorded only in the audit log.
- D. The Pod is created and then evicted.

**3.** Which Pod Security Admission mode is applied only to Pod objects and not to workload resources such as Deployments?

- A. audit
- B. warn
- C. audit and warn
- D. enforce

**4.** Members of which group bypass RBAC authorization checks entirely?

- A. `system:masters`
- B. `system:authenticated`
- C. `system:nodes`
- D. `system:serviceaccounts`

**5.** A user has no `get` permission on Secrets. Which other permission still exposes the contents of all Secrets in the namespace?

- A. `watch` on ConfigMaps
- B. `create` on Events
- C. `list` on Secrets
- D. `get` on Namespaces

**6.** A user can create Pods in a namespace but has no permissions on Secrets. Why is this still risky?

- A. Pods cannot be created without Secrets.
- B. The scheduler grants the user access to Secrets.
- C. Pods always run as cluster-admin.
- D. The user can create a Pod that mounts Secrets or uses a more privileged ServiceAccount in that namespace.

**7.** Which authentication method lets users log in through an external identity provider and present short-lived ID tokens to the API server?

- A. A static token file
- B. OpenID Connect (OIDC)
- C. X.509 client certificates
- D. Bootstrap tokens

**8.** Which RBAC verb allows a user to create RoleBindings that grant permissions the user does not hold?

- A. bind
- B. patch
- C. proxy
- D. deletecollection

## 답과 풀이

1. **C** Baseline은 노드로 넘어가는 길을 막고, root 실행 금지는 Restricted에 있다. 'Default'라는 단계는 없다.
2. **B** Baseline을 지켰으니 enforce는 통과하고, Restricted 위반은 warn으로 경고만 나온다.
3. **D** enforce는 결과 파드에만 걸린다.
4. **A** `system:masters`는 RBAC를 거치지 않고 모든 권한을 가진다.
5. **C** list와 watch도 Secret 값을 돌려준다.
6. **D** 파드는 같은 네임스페이스의 Secret을 마운트하고 아무 ServiceAccount로나 돌 수 있다.
7. **B** OIDC다. 그룹과 사용자는 IdP에서 관리한다.
8. **A** bind다. Role이나 ClusterRole 자체를 넓히는 건 escalate다.

## 참고 자료

- Kubernetes 문서, Pod Security Standards: <https://kubernetes.io/docs/concepts/security/pod-security-standards/>
- Kubernetes 문서, Pod Security Admission: <https://kubernetes.io/docs/concepts/security/pod-security-admission/>
- Kubernetes 문서, 네임스페이스 라벨로 PSS 적용하기: <https://kubernetes.io/docs/tasks/configure-pod-container/enforce-standards-namespace-labels/>
- Kubernetes 문서, 어드미션 컨트롤러 설정으로 PSS 적용하기: <https://kubernetes.io/docs/tasks/configure-pod-container/enforce-standards-admission-controller/>
- Kubernetes 문서, 인증: <https://kubernetes.io/docs/reference/access-authn-authz/authentication/>
- Kubernetes 문서, 인가: <https://kubernetes.io/docs/reference/access-authn-authz/authorization/>
- Kubernetes 문서, RBAC: <https://kubernetes.io/docs/reference/access-authn-authz/rbac/>
- Kubernetes 문서, RBAC 모범 사례: <https://kubernetes.io/docs/concepts/security/rbac-good-practices/>
- Kubernetes 문서, ServiceAccount 관리: <https://kubernetes.io/docs/reference/access-authn-authz/service-accounts-admin/>
- Keycloak: <https://www.keycloak.org/>


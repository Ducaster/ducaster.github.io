---
title: '[K8s 기초] 인증, 인가, 어드미션: API 서버가 요청을 통과시키는 세 관문'
date: '2025-01-18T16:10:00+09:00'
categories:
- Kubernetes
tags:
- kubernetes
- authentication
- authorization
- rbac
- admission-controller
- serviceaccount
- pod-security
- auth-can-i
- 보안과 운영 맛보기
series:
- Kubernetes 기초
series_order: 14
---

지금까지는 kind가 만들어 준 관리자 권한으로 뭐든 했다. 실제 클러스터에서는 사람과 앱마다 할 수 있는 일이 다르다. kubectl 요청 하나가 API 서버 안에서 어떤 관문을 지나 저장되는지 정리하고, 권한이 좁은 ServiceAccount를 만들어 직접 막혀 봤다.

## 요약

- API 서버로 온 요청은 인증(누구인가), 인가(그 일을 해도 되나), 어드미션(내용이 규칙에 맞나)을 차례로 지나야 etcd에 저장된다.
- 사람은 보통 인증서나 OIDC 토큰으로, 파드 안의 앱은 ServiceAccount 토큰으로 인증한다.
- 인가는 대부분 RBAC이다. Role에 '어떤 리소스에 어떤 동사'를 적고, RoleBinding으로 사용자나 ServiceAccount에 붙인다.
- 어드미션 컨트롤러는 요청 내용을 고치거나(변경) 막는다(검증). 기본값 넣기, 쿼터 검사, Pod Security 검사가 여기서 일어난다.
- 권한은 kubectl auth can-i와 --as로 확인한다.

## 1. 요청이 지나는 세 관문

{{< mermaid >}}
flowchart TB
  R["kubectl,<br>파드 안의 앱"] --> A1{"인증<br>누구인가?"}
  A1 -->|"모르는 사람"| X1["401 Unauthorized"]
  A1 -->|"누군지 확인됨"| A2{"인가<br>이 일을 해도 되나?"}
  A2 -->|"권한 없음"| X2["403 Forbidden"]
  A2 -->|"허용"| A3["변경 어드미션<br>기본값 채우기 등"]
  A3 --> A4{"검증 어드미션<br>쿼터, Pod Security 등"}
  A4 -->|"규칙 위반"| X3["거절 (Forbidden 등)"]
  A4 -->|"통과"| E["etcd에 저장"]
{{< /mermaid >}}

| 관문 | 묻는 것 | 대표적인 방법 |
|---|---|---|
| 인증(Authentication) | 이 요청을 보낸 게 누구인가 | 클라이언트 인증서, ServiceAccount 토큰, OIDC |
| 인가(Authorization) | 그 사람이 이 동사를 이 리소스에 해도 되나 | RBAC, Node 인가 |
| 어드미션(Admission) | 요청 내용이 클러스터 규칙에 맞나, 고칠 건 없나 | LimitRanger, ResourceQuota, PodSecurity, 웹훅 |

쿠버네티스에는 '사용자' 오브젝트가 없다는 게 의외였다. 사람은 인증서의 CN(이름)과 O(그룹)처럼 외부에서 확인한 이름일 뿐이고, 클러스터 안에 오브젝트로 있는 건 ServiceAccount뿐이다.

```bash
kubectl auth whoami
# ATTRIBUTE   VALUE
# Username    kubernetes-admin
# Groups      [kubeadm:cluster-admins system:authenticated]
```

kind가 준 kubeconfig는 kubeadm이 만든 관리자 인증서를 쓰고, kubeadm:cluster-admins 그룹이 cluster-admin 권한에 묶여 있어서 뭐든 됐던 것이다.

## 2. RBAC로 권한 좁히기

| 오브젝트 | 범위 | 내용 |
|---|---|---|
| Role | 네임스페이스 하나 | 리소스와 동사(get, list, watch, create, update, patch, delete) 목록 |
| ClusterRole | 클러스터 전체 | 노드처럼 네임스페이스 없는 리소스, 또는 여러 네임스페이스에 재사용할 규칙 |
| RoleBinding | 네임스페이스 하나 | Role(또는 ClusterRole)을 사용자·그룹·ServiceAccount에 붙인다 |
| ClusterRoleBinding | 클러스터 전체 | ClusterRole을 클러스터 전체에 붙인다 |

CI 도구가 쓸 ServiceAccount에 dev 네임스페이스의 파드를 읽는 권한만 줬다.

```bash
kubectl create namespace dev
kubectl -n dev create serviceaccount ci
kubectl auth can-i list pods -n dev --as=system:serviceaccount:dev:ci      # no
kubectl -n dev create role pod-reader --verb=get,list,watch --resource=pods
kubectl -n dev create rolebinding ci-reads-pods --role=pod-reader --serviceaccount=dev:ci
kubectl auth can-i list pods -n dev --as=system:serviceaccount:dev:ci      # yes
kubectl auth can-i delete pods -n dev --as=system:serviceaccount:dev:ci    # no
kubectl auth can-i list pods -n default --as=system:serviceaccount:dev:ci  # no. 다른 네임스페이스
kubectl auth can-i --list -n dev --as=system:serviceaccount:dev:ci         # 할 수 있는 일 전체
```

RBAC은 허용만 적는다. '거부' 규칙은 없고, 적지 않은 건 전부 안 된다. 그래서 필요한 것만 하나씩 더하는 방식이 된다.

## 3. 어드미션: 내용 검사

인가를 통과해도 내용이 규칙에 어긋나면 막힌다. 기본으로 켜져 있는 어드미션 컨트롤러 중 자주 만나는 것들을 정리했다.

| 어드미션 컨트롤러 | 하는 일 |
|---|---|
| NamespaceLifecycle | 지워지는 중이거나 없는 네임스페이스에 만드는 걸 막는다 |
| ServiceAccount | 파드에 serviceAccountName이 없으면 default를 넣는다 |
| LimitRanger | 네임스페이스의 LimitRange대로 requests·limits 기본값을 넣고 범위를 검사한다 |
| ResourceQuota | 네임스페이스 쿼터를 넘으면 막는다 |
| DefaultStorageClass | storageClassName 없는 PVC에 기본 StorageClass를 넣는다 |
| PodSecurity | 네임스페이스 라벨에 정한 수준(privileged, baseline, restricted)에 맞지 않는 파드를 막는다 |
| Mutating·ValidatingAdmissionWebhook | 외부 웹훅을 불러 고치거나 검사한다(OPA Gatekeeper, Kyverno 등) |

PodSecurity를 직접 걸어 봤다.

```bash
kubectl label namespace dev pod-security.kubernetes.io/enforce=restricted
kubectl -n dev run web --image=nginx:1.27
# Error from server (Forbidden): pods "web" is forbidden: violates PodSecurity "restricted:latest":
#   allowPrivilegeEscalation != false ..., unrestricted capabilities ..., runAsNonRoot != true ..., seccompProfile ...
kubectl label namespace dev pod-security.kubernetes.io/enforce-          # 라벨 지우기
```

거절 메시지에 무엇을 고쳐야 하는지가 다 적혀 있어서 오히려 공부가 됐다. 컨테이너 권한 설정(securityContext)은 나중에 따로 보기로 했다.

> **쉬운 설명**
>
> API 서버는 보안이 철저한 회사 건물이다. 인증은 정문에서 사원증을 확인하는 것이라 사원증이 없으면 들어오지도 못한다(401). 인가는 출입 권한표라서 '개발팀은 3층만'처럼 층마다 들어갈 수 있는 사람이 정해져 있고, 표에 없으면 막힌다(403). 어드미션은 보안 검색대다. 반입 물품이 규정에 맞는지 보고, 방문증 같은 빠진 물건은 붙여 주고(변경), 위험한 물건은 돌려보낸다(검증). 이 세 곳을 다 지나야 장부(etcd)에 기록된다.

## 헷갈렸던 것들

- 쿠버네티스에는 User 오브젝트가 없다. 사용자는 인증서나 토큰 속 이름이다. ServiceAccount만 오브젝트다.
- RBAC에는 거부 규칙이 없다. 허용한 것만 된다.
- Role은 네임스페이스 하나, ClusterRole은 클러스터 전체다. ClusterRole을 RoleBinding으로 붙이면 그 네임스페이스에만 적용된다.
- ServiceAccount 이름을 --as에 쓸 때는 system:serviceaccount:<네임스페이스>:<이름> 형식이다.
- 401은 '누군지 모름', 403은 '누군지 알지만 안 됨'이다.
- PodSecurity는 네임스페이스 라벨로 켠다. enforce는 막고, warn은 경고만, audit은 기록만 한다.

## 용어 정리

| 용어 | 뜻 |
|---|---|
| 인증 | 요청을 보낸 주체가 누구인지 확인하는 것 |
| 인가 | 그 주체가 요청한 동작을 해도 되는지 판단하는 것 |
| 어드미션 컨트롤러 | 저장 직전에 요청 내용을 고치거나 막는 플러그인 |
| RBAC | 역할 기반 접근 제어. Role과 RoleBinding으로 권한을 준다 |
| ServiceAccount | 파드 안의 앱이 API 서버에 접근할 때 쓰는 계정 |
| Pod Security Admission | 네임스페이스 라벨에 따라 파드 보안 수준을 검사하는 내장 어드미션 |

## 복습 문제

**1.** 네임스페이스 qa에 ServiceAccount tester를 만들고, qa의 디플로이먼트를 만들고 볼 수 있게(create, get, list) 해라.

**2.** tester가 qa에서 시크릿을 읽을 수 있는지, 다른 네임스페이스에서 디플로이먼트를 만들 수 있는지 확인해라.

**3.** qa 네임스페이스에 baseline 수준을 경고만 하도록(warn) 걸고, privileged: true인 파드를 만들어 경고를 확인해라.

## 답과 풀이

1. 디플로이먼트는 apps 그룹이라 --resource=deployments로 쓰면 된다.

```bash
kubectl create namespace qa
kubectl -n qa create serviceaccount tester
kubectl -n qa create role deployer --verb=create,get,list --resource=deployments
kubectl -n qa create rolebinding tester-deployer --role=deployer --serviceaccount=qa:tester
kubectl auth can-i create deployments -n qa --as=system:serviceaccount:qa:tester    # yes
```

2. 둘 다 no다. Role에 시크릿이 없고, RoleBinding은 qa에만 걸렸다.

```bash
kubectl auth can-i get secrets -n qa --as=system:serviceaccount:qa:tester
kubectl auth can-i create deployments -n default --as=system:serviceaccount:qa:tester
```

3. warn은 만들어 주되 경고를 띄운다.

```bash
kubectl label namespace qa pod-security.kubernetes.io/warn=baseline
kubectl -n qa run priv --image=busybox:1.36 --overrides='{"spec":{"containers":[{"name":"priv","image":"busybox:1.36","command":["sleep","3600"],"securityContext":{"privileged":true}}]}}'
# Warning: would violate PodSecurity "baseline:latest": privileged (container "priv" must not set securityContext.privileged=true)
```

## 참고 자료

- Kubernetes 문서, API 접근 제어: <https://kubernetes.io/docs/concepts/security/controlling-access/>
- Kubernetes 문서, 인증: <https://kubernetes.io/docs/reference/access-authn-authz/authentication/>
- Kubernetes 문서, RBAC 인가: <https://kubernetes.io/docs/reference/access-authn-authz/rbac/>
- Kubernetes 문서, 어드미션 컨트롤러: <https://kubernetes.io/docs/reference/access-authn-authz/admission-controllers/>
- Kubernetes 문서, Pod Security Admission: <https://kubernetes.io/docs/concepts/security/pod-security-admission/>
- Kubernetes 문서, 서비스 어카운트: <https://kubernetes.io/docs/concepts/security/service-accounts/>

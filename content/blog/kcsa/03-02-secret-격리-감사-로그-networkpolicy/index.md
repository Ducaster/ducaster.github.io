---
title: '[KCSA] Secret, 격리와 분할, 감사 로그, NetworkPolicy'
date: '2026-10-15T22:10:00+09:00'
categories:
- KCSA
tags:
- kubernetes
- kcsa
- secret
- external-secrets
- isolation
- multi-tenancy
- audit-logging
- audit-policy
- networkpolicy
- default-deny
- Kubernetes Security Fundamentals
series:
- KCSA
series_order: 5
---

기본 거부 정책을 걸면 앱은 데이터베이스 포트보다 먼저 DNS에서 막힌다. 필요한 통신만 남기는 NetworkPolicy와, 민감한 값은 빼고 누가 무엇을 했는지 남기는 감사 로그를 이 글에 정리했다.

## 요약

- Secret은 base64일 뿐이다. 저장 암호화, 좁은 RBAC, 파일 마운트, 외부 비밀 저장소 연동으로 지킨다.
- 네임스페이스는 이름, RBAC, 쿼터를 나누는 단위일 뿐 커널이나 네트워크를 나누지 않는다. 격리는 RBAC, NetworkPolicy, 쿼터, 전용 노드, 샌드박스 런타임, 별도 클러스터를 겹쳐서 만든다.
- 감사 로그는 기본으로 꺼져 있다. 정책 파일로 수준(None, Metadata, Request, RequestResponse)을 정하고, 로그 파일이나 웹훅으로 보낸다. Secret은 Metadata 수준으로 남긴다.
- 기록 단계는 RequestReceived, ResponseStarted(watch처럼 오래 걸리는 요청만), ResponseComplete, Panic이다.
- NetworkPolicy 기본 거부를 걸면 DNS(53번 포트) 이그레스를 따로 열어야 한다. 한 from 항목 안의 namespaceSelector와 podSelector는 AND, 별도 항목은 OR다.

## 1. Secret

| 위험 | 대응 |
|---|---|
| etcd에 평문 저장 | API 서버 EncryptionConfiguration, KMS v2 |
| RBAC가 넓음 | Secret 접근은 필요한 ServiceAccount에만. list, watch도 값을 보여 준다 |
| 환경 변수로 넣음 | 프로세스 환경, 크래시 덤프, 로그로 새기 쉽다. 볼륨 파일로 넣는다(노드의 tmpfs에 올라간다) |
| 이미지와 Git에 들어감 | 이미지 레이어와 커밋 기록에 남는다. 저장소 비밀값 스캔 |
| 바뀌면 안 되는 값이 바뀜 | `immutable: true` |
| 오래 돌려쓰는 값 | 외부 저장소에서 주기적으로 교체 |

외부 비밀 저장소를 붙이는 방법은 두 가지다.

| 방식 | 동작 |
|---|---|
| External Secrets Operator | 외부 저장소(클라우드 비밀 관리자, Vault 등)의 값을 읽어 쿠버네티스 Secret으로 동기화한다 |
| Secrets Store CSI Driver | 외부 저장소의 값을 CSI 볼륨으로 파드에 바로 마운트한다. 쿠버네티스 Secret을 거치지 않을 수도 있다 |

`kubectl get secret -o yaml`로 보이는 값은 base64로 인코딩된 것이라 `base64 -d` 한 번이면 원래 값이 나온다. Secret 하나의 크기는 1MiB까지다.

## 2. 격리와 분할

| 수단 | 나누는 것 |
|---|---|
| 네임스페이스 | 이름, RBAC 범위, 쿼터, 정책의 단위 |
| RBAC | 누가 어느 네임스페이스에서 무엇을 하나 |
| NetworkPolicy | 파드와 네임스페이스 사이 트래픽 |
| ResourceQuota, LimitRange | 한 테넌트가 자원을 다 쓰지 못하게 |
| PriorityClass 제한 | 한 테넌트가 높은 우선순위로 남의 파드를 밀어내지 못하게 |
| 전용 노드(테인트, 노드 어피니티) | 민감한 워크로드가 커널을 같이 쓰는 이웃 |
| 샌드박스 런타임, 사용자 네임스페이스 | 컨테이너와 호스트 커널 사이 |
| 별도 클러스터 | 컨트롤 플레인까지 |

전용 노드로 보낼 때 함정이 하나 있다. 노드 라벨로 고르는데, kubelet은 자기 노드의 라벨을 스스로 바꿀 수 있다. 털린 노드가 'secure=true' 라벨을 붙이면 민감한 파드를 끌어올 수 있다. 그래서 `node-restriction.kubernetes.io/` 접두어가 붙은 라벨을 쓴다. NodeRestriction 어드미션이 kubelet이 이 접두어의 라벨을 직접 바꾸지 못하게 막는다.

멀티 테넌시는 보통 '테넌트마다 네임스페이스'와 '테넌트마다 클러스터' 사이에서 고른다. 서로 믿지 못하는 테넌트라면 네임스페이스만으로는 부족하다.

## 3. 감사 로그

API 서버는 감사 정책이 없으면 감사 로그를 남기지 않는다. `--audit-policy-file`과 `--audit-log-path`(또는 `--audit-webhook-config-file`)를 줘야 켜진다.

{{< mermaid >}}
flowchart LR
  R["API 요청"] --> S["단계별 이벤트<br>RequestReceived, ResponseStarted,<br>ResponseComplete, Panic"]
  S --> P{"감사 정책<br>규칙을 위에서부터 비교,<br>처음 맞는 규칙의 수준"}
  P -->|"None"| X["기록 안 함"]
  P -->|"Metadata, Request,<br>RequestResponse"| B["백엔드<br>로그 파일(JSON 줄), 웹훅"]
{{< /mermaid >}}

| 수준 | 남기는 것 |
|---|---|
| None | 남기지 않는다 |
| Metadata | 요청한 사용자, 시간, 리소스, 동사 같은 메타데이터. 요청과 응답 본문은 빼고 |
| Request | 메타데이터와 요청 본문. 응답 본문은 빼고 |
| RequestResponse | 메타데이터, 요청 본문, 응답 본문 |

| 단계 | 언제 |
|---|---|
| RequestReceived | 감사 핸들러가 요청을 받자마자 |
| ResponseStarted | 응답 헤더를 보낸 뒤, 본문을 보내기 전. watch처럼 오래 걸리는 요청에만 생긴다 |
| ResponseComplete | 응답 본문까지 다 보낸 뒤 |
| Panic | 처리 중 패닉이 났을 때 |

```yaml
apiVersion: audit.k8s.io/v1
kind: Policy
omitStages: ["RequestReceived"]     # 같은 요청이 두 번 찍히지 않게
rules:
- level: Metadata                   # Secret, ConfigMap은 값이 로그에 남지 않게 Metadata로
  resources:
  - group: ""
    resources: ["secrets", "configmaps"]
- level: RequestResponse            # 권한 변경은 무엇을 바꿨는지까지 남긴다
  resources:
  - group: "rbac.authorization.k8s.io"
    resources: ["roles", "rolebindings", "clusterroles", "clusterrolebindings"]
- level: None                       # 시끄러운 읽기 요청은 뺀다
  users: ["system:kube-proxy"]
  verbs: ["watch"]
- level: Metadata                   # 나머지 전부
```

규칙은 위에서부터 비교해서 처음 맞는 규칙의 수준을 쓴다. 그래서 구체적인 규칙을 위에, 넓은 기본 규칙을 맨 아래에 둔다. `Request`는 Secret 생성·수정처럼 요청 본문에 값이 있을 때 그 값을 남길 수 있다. `RequestResponse`는 조회 응답의 값까지 남길 수 있다. 값을 빼고 접근 기록만 남기려면 `Metadata`로 설정한다. 로그 파일은 `--audit-log-maxage`, `--audit-log-maxbackup`, `--audit-log-maxsize`로 돌린다. 감사 로그는 공격 흔적을 찾는 근거라서 클러스터 밖으로 보내 고칠 수 없게 보관하는 게 좋다.

## 4. NetworkPolicy

기본 거부부터 건다. 들어오는 것과 나가는 것을 모두 막으면 DNS도 막힌다. 그래서 kube-dns로 가는 53번 포트를 따로 연다.

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: payments
spec:
  podSelector: {}
  policyTypes: ["Ingress", "Egress"]
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-dns
  namespace: payments
spec:
  podSelector: {}
  policyTypes: ["Egress"]
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53
```

from이나 to 안에서 셀렉터를 어떻게 적느냐에 따라 뜻이 갈린다.

| 적은 모양 | 뜻 |
|---|---|
| 한 항목(`- namespaceSelector: ...` 아래에 `podSelector: ...`를 같은 들여쓰기로) | AND. 그 네임스페이스들 안의, 그 라벨을 가진 파드 |
| 두 항목(`- namespaceSelector: ...`와 `- podSelector: ...`를 따로) | OR. 그 네임스페이스들의 모든 파드, 또는 같은 네임스페이스의 그 라벨 파드 |

하이픈 하나 차이로 허용 범위가 크게 달라진다. 위 allow-dns는 한 항목이라 kube-system의 kube-dns 파드만 허용한다.

그 밖에 기억할 것들이다.

- NetworkPolicy는 네임스페이스 리소스다. 클러스터 전체에 한 번에 거는 기능은 표준 NetworkPolicy에 없다.
- 서비스 이름이 아니라 파드 라벨, 네임스페이스 라벨, IP 대역(ipBlock)으로 고른다.
- `ipBlock`은 주로 클러스터 밖 주소 대역을 허용할 때 쓴다. `except`로 메타데이터 주소(예: `169.254.169.254/32`)를 그 대역에서 뺄 수 있다. 이 예외는 해당 허용 규칙에만 적용되므로, 같은 파드에 다른 정책이 그 주소를 허용하면 통신할 수 있다.
- 응답 트래픽은 따로 허용하지 않아도 된다. 연결 상태를 따라 허용된다.
- 실제로 막는 건 CNI다. 지원하지 않는 CNI에서는 아무 효과가 없다.

## 헷갈렸던 것들

- 감사 로그는 정책 파일이 없으면 남지 않는다.
- Metadata는 본문을 빼고, Request는 요청 본문까지, RequestResponse는 응답 본문까지다.
- ResponseStarted는 watch 같은 긴 요청에만 생긴다.
- 감사 정책은 처음 맞는 규칙을 쓴다. 넓은 규칙은 맨 아래에 둔다.
- 기본 거부 이그레스를 걸면 DNS가 끊긴다.
- 한 항목 안의 namespaceSelector와 podSelector는 AND, 따로 적으면 OR다.
- kubelet이 바꿀 수 없는 노드 라벨은 `node-restriction.kubernetes.io/` 접두어다.

## 복습 문제

**1.** Which audit level records request metadata but not the request or response body?

- A. None
- B. Metadata
- C. Request
- D. RequestResponse

**2.** Which audit stage is generated only for long-running requests such as watch?

- A. ResponseStarted
- B. RequestReceived
- C. ResponseComplete
- D. Panic

**3.** Why is it good practice to log requests for Secrets at the Metadata level?

- A. Metadata level is faster than any other level.
- B. Request level is not allowed for Secrets.
- C. Secrets cannot be audited.
- D. Higher levels would write Secret values into the audit log.

**4.** A NetworkPolicy selects all Pods in a namespace, sets `policyTypes` to Ingress and Egress, and has no rules. Which traffic is allowed for those Pods?

- A. Only DNS traffic
- B. Only traffic within the namespace
- C. No ingress or egress traffic
- D. All traffic

**5.** After a default-deny egress policy is applied, Pods can no longer resolve Service names. What must you allow?

- A. Egress to the kube-apiserver on port 6443
- B. Egress to the cluster DNS (kube-dns) on port 53 over UDP and TCP
- C. Ingress from the kube-system namespace
- D. Egress to `169.254.169.254`

**6.** In a NetworkPolicy `from` list, a single element contains both a namespaceSelector and a podSelector. Which sources does it match?

- A. Pods that match either selector
- B. All Pods in all namespaces
- C. Pods that match the podSelector in namespaces that match the namespaceSelector
- D. No Pods

**7.** Which statement about namespaces as an isolation mechanism is correct?

- A. Namespaces scope names, RBAC, and quotas, but by themselves they do not isolate the kernel or the network.
- B. Namespaces encrypt traffic between tenants.
- C. Pods in different namespaces cannot communicate by default.
- D. Each namespace runs on separate nodes.

**8.** Which practice reduces the exposure of Secrets to application processes?

- A. Passing Secret values as command-line arguments
- B. Building Secret values into the container image
- C. Storing Secret values in ConfigMaps
- D. Mounting Secrets as files from a volume instead of environment variables, and limiting RBAC access to them

## 답과 풀이

1. **B** Metadata는 본문을 남기지 않는다.
2. **A** 응답 헤더를 보낸 뒤 본문이 이어지는 긴 요청에만 생긴다.
3. **D** Request 이상이면 Secret 본문이 로그에 남는다.
4. **C** 규칙이 없으면 고른 파드는 들어오고 나가는 트래픽이 모두 막힌다.
5. **B** kube-dns로 가는 53번 포트를 UDP와 TCP 둘 다 연다.
6. **C** 한 항목 안에 같이 있으면 AND다.
7. **A** 네임스페이스는 논리적 단위라 커널과 네트워크는 따로 막아야 한다. 다른 네임스페이스끼리도 기본으로 통신된다.
8. **D** 파일 마운트와 좁은 RBAC다. 나머지는 모두 값을 더 쉽게 새게 한다.

## 참고 자료

- Kubernetes 문서, Secret: <https://kubernetes.io/docs/concepts/configuration/secret/>
- Kubernetes 문서, Secret 모범 사례: <https://kubernetes.io/docs/concepts/security/secrets-good-practices/>
- Kubernetes 문서, 저장된 Secret 암호화: <https://kubernetes.io/docs/tasks/administer-cluster/encrypt-data/>
- External Secrets Operator: <https://external-secrets.io/>
- Secrets Store CSI Driver: <https://secrets-store-csi-driver.sigs.k8s.io/>
- Kubernetes 문서, 멀티 테넌시: <https://kubernetes.io/docs/concepts/security/multi-tenancy/>
- Kubernetes 문서, 파드를 노드에 배정하기(노드 격리와 제한): <https://kubernetes.io/docs/concepts/scheduling-eviction/assign-pod-node/>
- Kubernetes 문서, 감사: <https://kubernetes.io/docs/tasks/debug/debug-cluster/audit/>
- Kubernetes 문서, 네트워크 정책: <https://kubernetes.io/docs/concepts/services-networking/network-policies/>
- Kubernetes 문서, 네트워크 정책 선언하기: <https://kubernetes.io/docs/tasks/administer-cluster/declare-network-policy/>


---
title: '[KCSA] 플랫폼 보안: 공급망, 이미지 저장소, 관찰, 서비스 메시, PKI, 연결, 어드미션 제어'
date: '2026-10-21T21:50:00+09:00'
categories:
- KCSA
tags:
- kubernetes
- kcsa
- supply-chain
- slsa
- sbom
- sigstore
- cosign
- in-toto
- harbor
- falco
- service-mesh
- mtls
- spiffe
- pki
- cert-manager
- admission-control
- validatingadmissionpolicy
- kyverno
- gatekeeper
- Platform Security
series:
- KCSA
series_order: 7
---

Platform Security(16%)는 클러스터 자체보다 그 주변에서 보안을 받쳐 주는 것들이다. 이미지가 만들어져 클러스터에 들어오는 길(공급망, 저장소), 무슨 일이 일어나는지 보는 눈(관찰), 서비스끼리의 신원과 암호화(서비스 메시, PKI), 구성 요소 사이의 연결, 들어오는 요청을 거르는 문(어드미션)이다. 프로젝트 이름이 많이 나와서, 이름마다 무엇을 하는 도구인지와 CNCF 단계를 같이 적었다.

## 요약

- 공급망은 소스, 빌드, 아티팩트, 저장소, 배포의 단계마다 공격받는다. SLSA로 빌드 수준을 정하고, SBOM으로 내용을 남기고, 서명(Sigstore cosign, Notary)과 출처 증명(in-toto)으로 무결성을 보이고, 배포할 때 어드미션에서 검증한다.
- 이미지 저장소는 사설로 두고, 올릴 때 스캔하고, 태그를 덮어쓰지 못하게 하고, 허용한 저장소에서만 받게 한다. Harbor가 대표적이다.
- 보안 관찰은 감사 로그(API 수준), 런타임 탐지(Falco, 시스템 콜 수준), 네트워크 흐름을 모아 SIEM으로 보낸다.
- 서비스 메시는 워크로드마다 짧은 수명의 인증서로 신원을 주고 mTLS로 암호화한다. 신원 형식으로 SPIFFE를 쓴다.
- 쿠버네티스에는 클러스터 CA, etcd CA, front-proxy CA와 ServiceAccount 서명 키가 있다. kubeadm 인증서는 1년, CA는 10년이다.
- 어드미션은 변경 다음에 검증 순서로 돈다. 웹훅은 failurePolicy와 가용성을 신경 써야 한다. ValidatingAdmissionPolicy(CEL), Kyverno, OPA Gatekeeper로 정책을 코드로 적는다.

## 1. 공급망 보안

{{< mermaid >}}
flowchart TB
  S["소스<br>위협: 악성 커밋, 유출된 계정<br>통제: 브랜치 보호, 리뷰, 서명 커밋"] --> B["빌드<br>위협: 오염된 빌드 시스템, 의존성 혼동<br>통제: 격리된 일회용 빌드, 의존성 고정"]
  B --> A["아티팩트<br>이미지, SBOM, 서명, 출처 증명"]
  A --> R["저장소<br>위협: 이미지 바꿔치기<br>통제: 접근 제어, 불변 태그, 스캔"]
  R --> D["배포<br>통제: 어드미션에서 서명과 출처 검증,<br>다이제스트 고정"]
{{< /mermaid >}}

| 도구, 표준 | 무엇인가 | CNCF 단계 |
|---|---|---|
| SLSA | 공급망 무결성 수준을 정한 프레임워크. OpenSSF 프로젝트 | CNCF 아님 |
| SBOM(SPDX, CycloneDX) | 소프트웨어에 든 구성 요소 목록의 표준 형식 | CNCF 아님 |
| Sigstore(cosign) | 짧은 수명 인증서로 키 없이 서명하고(keyless), 서명 기록을 투명성 로그(Rekor)에 남긴다. OpenSSF 프로젝트 | CNCF 아님 |
| Notary Project(notation) | OCI 아티팩트 서명과 검증 | Incubating |
| in-toto | 공급망 각 단계가 정해진 대로 수행됐다는 증명(attestation) | Graduated(2025년 2월) |
| TUF | 소프트웨어 업데이트 메타데이터를 안전하게 배포하는 프레임워크 | Graduated(2019년) |

SLSA 빌드 트랙은 수준이 올라갈수록 요구가 세진다. L1은 빌드 과정을 담은 출처 증명(provenance)이 있는 것, L2는 호스팅된 빌드 플랫폼이 서명한 출처 증명, L3는 빌드끼리 서로 영향을 주지 못하고 서명 키에 빌드 단계가 닿지 못하는 강화된 빌드 플랫폼이다.

```bash
cosign sign registry.example.com/shop/api@sha256:<digest>      # 서명
cosign verify registry.example.com/shop/api@sha256:<digest> \
  --certificate-identity=https://github.com/example/shop/.github/workflows/release.yml@refs/heads/main \
  --certificate-oidc-issuer=https://token.actions.githubusercontent.com
```

서명은 '누가 만들었나', SBOM은 '안에 무엇이 들었나', 출처 증명은 '어떻게 만들었나'에 답한다. 셋은 서로 다른 질문이다.

## 2. 이미지 저장소

| 할 일 | 이유 |
|---|---|
| 사설 저장소, 프로젝트별 권한과 로봇 계정 | 아무나 올리고 받지 못하게 |
| 올릴 때 취약점 스캔, 기준 넘으면 받기 차단 | 알려진 취약점이 배포되지 않게 |
| 불변 태그 | 같은 태그로 다른 이미지를 덮어쓰지 못하게 |
| 서명과 SBOM을 이미지 옆에 저장(OCI referrers) | 배포할 때 같이 검증 |
| 프록시 캐시, 복제 | 외부 저장소 장애와 받기 횟수 제한을 피하고, 받는 출처를 한곳으로 |
| 허용 저장소 정책 | 어드미션에서 사내 저장소 이미지만 허용 |

Harbor(CNCF graduated)는 이 기능을 대부분 가진 저장소다. 노드 쪽에서는 imagePullSecrets를 필요한 네임스페이스와 ServiceAccount에만 주고, 멀티 테넌트라면 AlwaysPullImages로 캐시된 사설 이미지 재사용을 막는다.

## 3. 보안 관찰

| 신호 | 보는 것 | 도구 |
|---|---|---|
| 감사 로그 | API에 누가 무엇을 했나 | API 서버 감사 백엔드 |
| 런타임 이벤트 | 컨테이너 안 시스템 콜, 파일, 프로세스, 네트워크 | Falco(graduated), Tetragon(Cilium 하위 프로젝트) |
| 네트워크 흐름 | 누가 누구와 통신하나 | Cilium Hubble, CNI 흐름 로그 |
| 쿠버네티스 이벤트 | 파드 실패, 축출, 스케줄링 | Events, 이벤트 수집기 |

이 신호를 클러스터 밖의 SIEM으로 모으고, 알림 규칙을 건다. 예를 들면 새 ClusterRoleBinding, 파드에 대한 exec, 평소와 다른 주체의 Secret 읽기, privileged 파드 생성, 어드미션 웹훅 설정 변경이다. Falco 규칙은 이런 모양이다(기본 규칙을 줄여서 옮겼다).

```yaml
- rule: Terminal shell in container
  desc: A shell was spawned inside a container
  condition: spawned_process and container and proc.name in (bash, sh, zsh) and proc.tty != 0
  output: "Shell in container (user=%user.name pod=%k8s.pod.name cmd=%proc.cmdline)"
  priority: WARNING
```

## 4. 서비스 메시

서비스 메시는 워크로드마다 신원을 담은 짧은 수명의 인증서를 주고, 서비스끼리 mTLS로 통신하게 한다. 네트워크 위치(IP)가 아니라 신원으로 허용 여부를 정해서 제로 트러스트에 가깝다.

- **신원**: SPIFFE(CNCF graduated) 형식의 ID를 쓴다. Istio라면 `spiffe://<trust-domain>/ns/<네임스페이스>/sa/<ServiceAccount>` 모양이다. SPIRE(graduated)는 SPIFFE ID를 발급하는 구현체다.
- **인증서**: 메시의 CA가 발급하고 자동으로 교체한다. 앱 코드는 바뀌지 않는다.
- **인가**: '주문 서비스는 결제 서비스의 POST /pay만 부를 수 있다' 같은 L7 정책을 건다(Istio AuthorizationPolicy 등).
- **한계**: 메시는 NetworkPolicy(L3/L4)를 대신하지 않는다. 메시 밖으로 나가는 트래픽, 사이드카를 우회하는 트래픽은 따로 막는다. 메시의 컨트롤 플레인과 CA는 그 자체로 가치가 높은 공격 대상이다.

## 5. PKI

kubeadm 클러스터의 인증서는 `/etc/kubernetes/pki`에 있다.

| CA, 키 | 서명하는 것 |
|---|---|
| 클러스터 CA(`ca.crt`, `ca.key`) | API 서버 인증서, kubelet 클라이언트 인증서, 관리자 인증서 등 |
| etcd CA(`etcd/ca.crt`) | etcd 서버, 피어, API 서버의 etcd 클라이언트 인증서 |
| front-proxy CA | API 애그리게이션용 프록시 인증서 |
| ServiceAccount 키 쌍(`sa.key`, `sa.pub`) | CA가 아니다. ServiceAccount 토큰을 서명하고 검증한다 |

kubeadm이 만든 인증서는 기본 1년, CA는 10년이다. kubelet은 클라이언트 인증서를 스스로 갱신한다(`rotateCertificates`). 클러스터 안에서 인증서를 받는 공식 경로는 CertificateSigningRequest API다. 서명자(signer)에 따라 용도가 정해지고, 누가 승인할 수 있는지가 RBAC로 묶여 있다.

| 서명자 | 용도 |
|---|---|
| `kubernetes.io/kube-apiserver-client` | API 서버에 붙는 클라이언트 인증서 |
| `kubernetes.io/kube-apiserver-client-kubelet` | kubelet의 클라이언트 인증서 |
| `kubernetes.io/kubelet-serving` | kubelet의 서버 인증서 |

앱의 TLS 인증서는 cert-manager(CNCF graduated)가 ACME(Let's Encrypt), 사설 CA, Vault 같은 발급자로부터 받아 Secret에 넣고 만료 전에 갱신한다. v1.37에서는 kubelet이 파드마다 인증서를 받아 넣어 주는 Pod 인증서와, CA 묶음을 배포하는 ClusterTrustBundle이 GA가 됐다.

## 6. 연결

| 경로 | 지킬 것 |
|---|---|
| 클라이언트 → API 서버 | 사설 엔드포인트나 허용 IP, TLS, 강한 인증 |
| 노드(kubelet, 파드) → API 서버 | TLS와 클라이언트 인증서, ServiceAccount 토큰 |
| API 서버 → kubelet(logs, exec, port-forward) | `--kubelet-certificate-authority`로 kubelet 서버 인증서 검증. 컨트롤 플레인과 노드 망이 다르면 Konnectivity 터널 |
| API 서버 → etcd | mTLS, 방화벽 |
| 파드 ↔ 파드 | NetworkPolicy, mTLS나 CNI 암호화 |
| 클러스터 → 외부 | 이그레스 제한, 이그레스 게이트웨이 |
| 관리자 접근 | VPN이나 배스천, 짧은 수명 자격 증명 |

API 서버에서 kubelet, 노드, 파드, 서비스로 가는 연결은 기본으로는 인증서를 검증하지 않을 수 있다는 점이 쿠버네티스 문서에 적혀 있다. 그래서 kubelet 서버 인증서 검증을 켜고, 신뢰할 수 없는 망을 지나지 않게 한다.

## 7. 어드미션 제어

{{< mermaid >}}
flowchart LR
  R["인증, 인가를 통과한 요청"] --> M["변경 어드미션<br>내장 플러그인, MutatingAdmissionPolicy,<br>변경 웹훅"]
  M --> V["스키마 검증"]
  V --> C["검증 어드미션<br>내장 플러그인, ValidatingAdmissionPolicy,<br>검증 웹훅"]
  C --> E[("etcd")]
{{< /mermaid >}}

보안과 관련된 내장 어드미션 플러그인이다.

| 플러그인 | 하는 일 |
|---|---|
| NodeRestriction | kubelet이 자기 Node와 자기 노드의 파드만 고치게 |
| PodSecurity | Pod Security Standards 적용 |
| AlwaysPullImages | 매번 이미지를 받아 인증 확인 |
| ImagePolicyWebhook | 외부 서비스에 이미지 허용 여부를 묻는다 |
| DenyServiceExternalIPs | Service의 externalIPs 사용을 막는다(CVE-2020-8554 대응) |
| LimitRanger, ResourceQuota | 자원 기본값과 상한 |

웹훅은 강력하지만 조심할 점이 있다.

- `failurePolicy: Ignore`면 웹훅이 죽었을 때 검사 없이 통과한다(fail open). `Fail`이면 웹훅이 죽었을 때 요청이 막힌다(fail closed). 보안 정책은 보통 Fail로 두고 웹훅을 여러 개 띄운다.
- 웹훅이 kube-system까지 막으면 웹훅 자신이 다시 뜨지 못해 클러스터가 잠길 수 있다. 시스템 네임스페이스는 제외한다.
- 웹훅 설정을 고칠 수 있는 사람은 정책을 끄거나 모든 요청을 볼 수 있다. 권한을 좁힌다.

정책은 코드로 적는다. 웹훅 없이 API 서버 안에서 CEL로 도는 ValidatingAdmissionPolicy(v1.30 stable)가 가볍다.

```yaml
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingAdmissionPolicy
metadata:
  name: require-internal-registry
spec:
  failurePolicy: Fail
  matchConstraints:
    resourceRules:
    - apiGroups: [""]
      apiVersions: ["v1"]
      operations: ["CREATE", "UPDATE"]
      resources: ["pods"]
  validations:
  - expression: "object.spec.containers.all(c, c.image.startsWith('registry.example.com/'))"
    message: "이미지는 사내 저장소에서만 받을 수 있다"
---
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingAdmissionPolicyBinding
metadata:
  name: require-internal-registry
spec:
  policyName: require-internal-registry
  validationActions: ["Deny"]
  matchResources:
    namespaceSelector:
      matchLabels:
        env: prod
```

실제로 쓰려면 initContainers와 ephemeralContainers도 같이 검사해야 한다. 정책 엔진 둘은 이렇게 다르다.

| | OPA Gatekeeper | Kyverno |
|---|---|---|
| 정책 언어 | Rego(ConstraintTemplate, Constraint) | YAML과 CEL |
| 할 수 있는 일 | 검증, 변경 | 검증, 변경, 리소스 생성, 이미지 서명 검증 |
| CNCF | OPA graduated(2021년) | graduated(2026년 3월) |

> **쉬운 설명**
>
> 플랫폼 보안은 식당의 식자재 관리와 주방 출입 관리다. 공급망 보안은 재료가 어느 농장에서 어떻게 왔는지 영수증(출처 증명)과 성분표(SBOM), 봉인 스티커(서명)를 확인하는 일이고, 이미지 저장소는 검수를 마친 재료만 넣는 창고다. 서비스 메시는 직원마다 사진이 박힌 사원증(인증서)을 주고, 주방끼리 주고받는 쪽지를 봉투에 넣어(mTLS) 보내게 하는 것이다. 어드미션 제어는 주방 입구의 검수대다. 검수대 담당이 자리를 비웠을 때 그냥 통과시킬지(Ignore), 아무도 못 들어가게 할지(Fail)를 미리 정해 둬야 한다.

## 헷갈렸던 것들

- 서명은 누가, SBOM은 무엇이, 출처 증명은 어떻게를 말한다.
- Sigstore와 SLSA는 OpenSSF 프로젝트이고, in-toto와 TUF는 CNCF graduated, Notary는 incubating이다.
- ServiceAccount 키 쌍은 CA가 아니다.
- kubeadm 인증서는 1년, CA는 10년이다.
- 웹훅 `failurePolicy: Ignore`는 웹훅이 죽으면 통과(fail open)다.
- 서비스 메시가 NetworkPolicy를 대신하지 않는다.
- 변경 어드미션 다음에 검증 어드미션이다.

## 용어 정리

| 용어 | 뜻 |
|---|---|
| 공급망 보안 | 소스부터 배포까지 소프트웨어가 오염되지 않게 지키는 일 |
| SLSA | 빌드 무결성 수준을 L1부터 L3까지 정한 프레임워크 |
| SBOM | 소프트웨어 구성 요소 목록 |
| 출처 증명(provenance) | 아티팩트가 어디서 어떻게 빌드됐는지 적은 서명된 기록 |
| keyless 서명 | 오래 쓰는 키 대신 OIDC 신원으로 받은 짧은 수명 인증서로 서명하는 방식 |
| SPIFFE | 워크로드 신원 형식과 발급 방식의 표준 |
| CSR | 인증서 서명 요청. 쿠버네티스에서는 CertificateSigningRequest API |
| failurePolicy | 어드미션 웹훅을 부를 수 없을 때 요청을 통과시킬지 막을지 |

## 복습 문제

**1.** Which artifact lists the components and dependencies contained in a container image?

- A. A provenance attestation
- B. A signature
- C. A Dockerfile
- D. A software bill of materials (SBOM)

**2.** Which project provides keyless signing of container images with short-lived certificates and records signatures in a transparency log?

- A. Notary
- B. Harbor
- C. Sigstore (cosign)
- D. Trivy

**3.** A validating admission webhook is configured with `failurePolicy: Ignore`. What happens when the webhook service is unavailable?

- A. Requests are allowed without the policy check.
- B. All requests are rejected.
- C. The API server restarts.
- D. The webhook configuration is deleted.

**4.** In a service mesh, what gives each workload a cryptographic identity for mutual TLS?

- A. A NodePort Service
- B. Certificates issued by the mesh's certificate authority, often in the SPIFFE format
- C. Pod labels
- D. An Ingress resource

**5.** Which SLSA build level requires a hardened build platform?

- A. Level 0
- B. Level 1
- C. Level 2
- D. Level 3

**6.** Which built-in admission plugin forces images to be pulled for every Pod, so that cached private images cannot be reused without credentials?

- A. NodeRestriction
- B. AlwaysPullImages
- C. LimitRanger
- D. DefaultStorageClass

**7.** Which tool issues and renews TLS certificates for applications in Kubernetes from issuers such as ACME?

- A. kube-bench
- B. Falco
- C. cert-manager
- D. Kustomize

**8.** How can the kube-apiserver verify the identity of a kubelet when it connects to the kubelet for logs or exec?

- A. By validating the kubelet's serving certificate against the CA given with `--kubelet-certificate-authority`
- B. It cannot, because this connection is never authenticated.
- C. By checking the node's labels
- D. By using the node's SSH host key

## 답과 풀이

1. **D** SBOM은 구성 요소 목록이다. 출처 증명은 빌드 방법, 서명은 만든 주체를 말한다.
2. **C** Sigstore의 cosign이다. Fulcio가 짧은 수명 인증서를 주고 Rekor가 투명성 로그다.
3. **A** Ignore는 fail open이다.
4. **B** 메시 CA가 SPIFFE 형식 신원이 담긴 인증서를 발급하고 교체한다.
5. **D** L3가 강화된 빌드 플랫폼을 요구한다.
6. **B** AlwaysPullImages다.
7. **C** cert-manager다. kube-bench는 CIS 점검, Falco는 런타임 탐지다.
8. **A** kubelet 서버 인증서를 그 CA로 검증한다. 설정하지 않으면 검증 없이 연결될 수 있다.

## 참고 자료

- SLSA: <https://slsa.dev/>
- Sigstore: <https://www.sigstore.dev/>
- Notary Project: <https://notaryproject.dev/>
- in-toto: <https://in-toto.io/>
- The Update Framework: <https://theupdateframework.io/>
- SPDX: <https://spdx.dev/>
- CycloneDX: <https://cyclonedx.org/>
- Harbor: <https://goharbor.io/>
- Falco: <https://falco.org/>
- SPIFFE: <https://spiffe.io/>
- Istio, 보안 개념: <https://istio.io/latest/docs/concepts/security/>
- cert-manager: <https://cert-manager.io/>
- Kubernetes 문서, PKI 인증서와 요구 사항: <https://kubernetes.io/docs/setup/best-practices/certificates/>
- Kubernetes 문서, 인증서 서명 요청: <https://kubernetes.io/docs/reference/access-authn-authz/certificate-signing-requests/>
- Kubernetes 문서, 컨트롤 플레인과 노드 사이 통신: <https://kubernetes.io/docs/concepts/architecture/control-plane-node-communication/>
- Kubernetes 문서, 어드미션 컨트롤러: <https://kubernetes.io/docs/reference/access-authn-authz/admission-controllers/>
- Kubernetes 문서, 동적 어드미션 제어: <https://kubernetes.io/docs/reference/access-authn-authz/extensible-admission-controllers/>
- Kubernetes 문서, ValidatingAdmissionPolicy: <https://kubernetes.io/docs/reference/access-authn-authz/validating-admission-policy/>
- Kyverno: <https://kyverno.io/>
- OPA Gatekeeper: <https://open-policy-agent.github.io/gatekeeper/website/>


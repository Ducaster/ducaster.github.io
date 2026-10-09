---
title: '[KCSA] 클러스터 구성 요소 보안: API 서버, etcd, kubelet, 런타임, kube-proxy, 파드, 네트워크, 클라이언트, 스토리지'
date: '2026-10-09T22:00:00+09:00'
categories:
- KCSA
tags:
- kubernetes
- kcsa
- kube-apiserver
- etcd
- kubelet
- kube-scheduler
- kube-controller-manager
- container-runtime
- kube-proxy
- kubeconfig
- encryption-at-rest
- noderestriction
- cis-benchmark
- Kubernetes Cluster Component Security
series:
- KCSA
series_order: 3
---

Kubernetes Cluster Component Security는 22%로 가장 큰 도메인이고 항목도 11개로 가장 많다. 구성 요소마다 '무슨 일을 하나, 뚫리면 공격자가 무엇을 얻나, 무엇을 잠그나'를 같은 순서로 정리했다. CIS Kubernetes Benchmark와 쿠버네티스 문서의 '클러스터 보호하기'를 기준으로 삼았다. 플래그 이름 자체보다 그 설정이 막는 위협을 이해하는 데 시간을 썼다.

## 요약

- 구성 요소 사이의 모든 통신은 TLS여야 하고, 서로 인증서로 신원을 확인한다.
- API 서버는 모든 요청의 입구다. 익명 접근을 줄이고, Node와 RBAC로 인가하고(AlwaysAllow 금지), 어드미션(NodeRestriction 등), 감사 로그, Secret 저장 암호화를 켠다.
- etcd에는 Secret을 포함한 클러스터 전부가 있다. 클라이언트 인증서로만 접속하게 하고, API 서버 말고는 닿지 못하게 막는다.
- kubelet API(10250)로는 파드 안 명령 실행까지 된다. 익명 인증을 끄고 Webhook 인가를 쓰고, 인증 없는 읽기 전용 포트(10255)는 닫는다.
- 컨테이너 런타임 소켓을 마운트한 파드는 사실상 노드의 root다.
- kubeconfig는 자격 증명 그 자체다. 쿠버네티스는 클라이언트 인증서를 하나씩 폐기할 수 없어서, 짧은 수명의 토큰이나 OIDC가 낫다.
- 스토리지는 Secret 저장 암호화, 볼륨 암호화, hostPath 제한, PV 정리가 중요하다.

## 1. 구성 요소와 통신 경로

{{< mermaid >}}
flowchart TB
  K["kubectl, 클라이언트"] -->|"6443 TLS<br>인증서, 토큰, OIDC"| API["kube-apiserver"]
  API -->|"2379 mTLS"| ETCD[("etcd")]
  ETCD <-->|"2380 mTLS 피어"| ETCD2[("etcd 다른 멤버")]
  SCH["kube-scheduler<br>10259"] -->|"클라이언트 인증서"| API
  KCM["kube-controller-manager<br>10257"] -->|"클라이언트 인증서"| API
  KL["kubelet<br>10250"] -->|"클라이언트 인증서"| API
  API -->|"10250 HTTPS<br>logs, exec, port-forward"| KL
  KP["kube-proxy"] -->|"ServiceAccount 토큰, kubeconfig"| API
  KL -->|"CRI 유닉스 소켓"| CR["컨테이너 런타임"]
{{< /mermaid >}}

방향이 두 가지라는 점이 중요하다. 대부분은 구성 요소가 API 서버로 붙지만, `kubectl logs`, `exec`, `port-forward`는 API 서버가 kubelet으로 붙는다. 이 연결에서 API 서버가 kubelet의 서버 인증서를 검증하게 하려면 `--kubelet-certificate-authority`를 준다. 컨트롤 플레인이 노드와 다른 네트워크에 있으면 Konnectivity 프록시로 이 연결을 터널링하기도 한다.

## 2. API 서버

뚫리면 클러스터 전체다. 위협은 익명 접근, 너무 넓은 인가, 인터넷 노출, 기록 없는 변경, 과부하다.

| 설정 | 막는 것 |
|---|---|
| `--anonymous-auth=false`(또는 익명 허용 경로 제한) | 인증 없는 요청. 켜 두면 `system:anonymous`로 들어오고 RBAC가 대부분 막지만 실수로 권한을 주면 위험하다 |
| `--authorization-mode=Node,RBAC` | AlwaysAllow처럼 다 허용하는 모드 |
| `--enable-admission-plugins=NodeRestriction,...` | kubelet이 다른 노드의 오브젝트를 고치는 것 |
| `--encryption-provider-config` | etcd에 Secret이 평문으로 저장되는 것 |
| `--audit-policy-file`, `--audit-log-path` | 누가 무엇을 했는지 모르는 것 |
| `--tls-cert-file`, `--client-ca-file`, `--etcd-cafile` 등 | 평문 통신, 신원 위장 |
| `--kubelet-certificate-authority` | 가짜 kubelet으로의 연결 |
| `--profiling=false` | 디버그용 프로파일링 엔드포인트 노출 |
| `--service-account-key-file`, `--service-account-issuer` | ServiceAccount 토큰 위조 |

그 밖에 API 서버 엔드포인트를 인터넷에 열지 않고, API Priority and Fairness로 요청 종류별 동시 처리량을 나눠 한 클라이언트가 API 서버를 독차지하지 못하게 한다. 예전에 있던 인증 없는 HTTP 포트(8080)는 이제 없다.

## 3. etcd

모든 오브젝트와 Secret이 들어 있다. etcd에 직접 접근하면 RBAC와 어드미션을 모두 건너뛴다.

| 설정 | 막는 것 |
|---|---|
| `--client-cert-auth=true`, `--trusted-ca-file` | 인증서 없는 클라이언트 접속 |
| `--peer-client-cert-auth=true` | 가짜 멤버가 클러스터에 끼는 것 |
| TLS(`--cert-file`, `--peer-cert-file`) | 평문 통신 |
| 방화벽으로 2379는 API 서버에서만, 2380은 etcd 멤버끼리만 | 다른 곳에서의 접근 |
| etcd 전용 CA | 쿠버네티스 CA로 서명된 다른 인증서로 etcd에 붙는 것 |
| 백업 파일 암호화와 접근 제한 | 백업에서 Secret이 새는 것 |

Secret을 저장할 때 암호화하는 건 etcd 기능이 아니라 API 서버의 EncryptionConfiguration이다. API 서버가 암호화해서 etcd에 넣는다.

```yaml
apiVersion: apiserver.config.k8s.io/v1
kind: EncryptionConfiguration
resources:
- resources: ["secrets"]
  providers:
  - kms:                      # 외부 KMS가 키를 관리한다(권장)
      apiVersion: v2
      name: cloud-kms
      endpoint: unix:///var/run/kms-plugin.sock
  - identity: {}              # 암호화되기 전에 저장된 값을 읽기 위해 마지막에 둔다
```

providers의 첫 번째 항목으로 새로 쓰고, 읽을 때는 차례로 시도한다. `identity`가 첫 번째면 암호화하지 않는다는 뜻이라 순서가 중요하다. 설정을 바꾼 뒤 이미 저장된 Secret은 다시 써야(`kubectl get secrets -A -o json | kubectl replace -f -`) 암호화된다.

## 4. kubelet

kubelet API(10250)로는 파드 목록 조회, 로그 읽기, 컨테이너 안 명령 실행까지 된다. 익명으로 열려 있으면 네트워크에서 닿는 누구나 그 노드의 컨테이너에서 명령을 실행할 수 있다.

```yaml
apiVersion: kubelet.config.k8s.io/v1beta1
kind: KubeletConfiguration
authentication:
  anonymous:
    enabled: false          # 익명 요청 거부
  webhook:
    enabled: true           # 토큰을 API 서버에 물어 인증
  x509:
    clientCAFile: /etc/kubernetes/pki/ca.crt
authorization:
  mode: Webhook             # 요청마다 API 서버에 SubjectAccessReview로 인가를 묻는다(AlwaysAllow 금지)
readOnlyPort: 0             # 인증 없는 읽기 전용 포트 10255를 닫는다
rotateCertificates: true    # 클라이언트 인증서 자동 갱신
serverTLSBootstrap: true    # 서버 인증서를 CSR로 받는다
protectKernelDefaults: true
seccompDefault: true        # 모든 컨테이너에 RuntimeDefault seccomp 적용
```

kubelet을 묶어 두는 장치가 두 개 더 있다. Node 인가 모드는 kubelet이 자기 노드에 배정된 파드가 쓰는 Secret, ConfigMap만 읽게 한다. NodeRestriction 어드미션은 kubelet이 자기 Node 오브젝트와 자기 노드의 파드만 고치게 한다. 그래서 노드 하나가 털려도 다른 노드의 Secret까지 바로 가져가지는 못한다.

## 5. kube-scheduler와 kube-controller-manager

| 설정 | 이유 |
|---|---|
| `--bind-address=127.0.0.1` | 상태 확인, 지표 엔드포인트(10259, 10257)를 네트워크에 노출하지 않는다 |
| `--profiling=false` | 프로파일링 엔드포인트를 끈다 |
| kubeconfig 파일 권한 600, 소유자 root | 이 파일의 인증서로 API 서버에 높은 권한으로 붙을 수 있다 |
| 컨트롤러 매니저 `--use-service-account-credentials=true` | 컨트롤러마다 따로 ServiceAccount를 써서 권한을 나눈다 |
| 컨트롤러 매니저 `--service-account-private-key-file`, `--root-ca-file` | ServiceAccount 토큰 서명과 CA 배포 |

컨트롤러 매니저는 클러스터 CA의 개인 키(`--cluster-signing-key-file`)로 인증서 서명 요청을 서명할 수 있다. CA 개인 키가 새면 누구로든 위장한 인증서를 만들 수 있으니, 클러스터에서 가장 민감한 파일로 다룬다.

## 6. 컨테이너 런타임

- **소켓**: containerd나 CRI-O의 유닉스 소켓(`/run/containerd/containerd.sock`)에 접근하면 노드에서 아무 컨테이너나 privileged로 띄울 수 있다. 소켓을 마운트한 파드는 노드 root와 같다. hostPath로 소켓을 마운트하는 걸 PSA나 정책으로 막는다.
- **패치**: 런타임 취약점은 곧 컨테이너 탈출이다. runc의 CVE-2019-5736(runc 바이너리 덮어쓰기), CVE-2024-21626(파일 디스크립터 유출, Leaky Vessels)이 대표적이다.
- **기본 제한**: kubelet의 `seccompDefault`로 모든 컨테이너에 RuntimeDefault seccomp를 건다. AppArmor, SELinux를 같이 쓴다.
- **격리 강화**: 믿지 못하는 워크로드는 RuntimeClass로 gVisor, Kata Containers를 쓴다. 사용자 네임스페이스(`hostUsers: false`)로 컨테이너 root를 호스트의 일반 사용자로 매핑한다.

## 7. kube-proxy

kube-proxy는 노드의 iptables, nftables 규칙을 바꿔야 해서 호스트 네트워크와 높은 권한으로 돈다. 그래서 kube-proxy의 kubeconfig와 이미지를 보호하고, 지표 엔드포인트(기본 `127.0.0.1:10249`)를 밖으로 열지 않는다.

서비스 기능 자체가 공격 경로가 되기도 한다. Service의 externalIPs는 아무 IP로 오는 트래픽을 자기 서비스로 가로챌 수 있게 해서 CVE-2020-8554로 알려졌다. 고칠 수 없는 설계 문제라서 어드미션 정책으로 externalIPs 사용을 막고, 쿠버네티스는 이 필드를 지원 중단하는 중이다. NodePort는 모든 노드의 포트를 여니 필요한 곳만 쓴다.

## 8. 파드

공격자가 가장 먼저 닿는 곳이다. 파드 설정 하나로 노드까지 넘어갈 수 있다.

| 위험한 설정 | 공격자가 얻는 것 |
|---|---|
| `privileged: true` | 거의 모든 커널 기능과 장치. 노드 탈출이 쉽다 |
| `hostPID`, `hostIPC`, `hostNetwork` | 노드의 프로세스, IPC, 네트워크를 그대로 본다 |
| hostPath(특히 `/`, `/etc`, 런타임 소켓) | 노드 파일 시스템 읽기·쓰기 |
| `SYS_ADMIN` 같은 capabilities 추가 | 마운트 등 root급 동작 |
| root 실행, 권한 상승 허용 | 커널 취약점과 결합하면 탈출 |
| ServiceAccount 토큰 자동 마운트 | 파드가 털리면 그 권한으로 API 호출 |

이 목록이 Pod Security Standards의 Baseline과 Restricted가 막는 것들이다. 자원 limits가 없으면 한 파드가 노드 자원을 다 써서 서비스 거부가 된다.

## 9. 컨테이너 네트워킹

쿠버네티스 파드 네트워크는 기본으로 평평하다. 모든 파드가 모든 파드와 통신할 수 있어서, 하나가 털리면 옆으로 옮겨 가기(측면 이동) 쉽다.

- NetworkPolicy로 기본 거부를 걸고 필요한 통신만 연다. CNI가 지원해야 동작한다.
- 노드 사이 파드 트래픽은 기본으로 암호화되지 않는다. CNI의 WireGuard, IPsec 암호화나 서비스 메시의 mTLS로 암호화한다.
- 나가는 트래픽(egress)도 막는다. 메타데이터 엔드포인트, 내부 관리 망으로 가는 길을 끊는다.
- CoreDNS도 공격 대상이다. DNS로 내부 서비스 이름을 쉽게 알아낼 수 있다.

## 10. 클라이언트 보안

kubeconfig 파일은 자격 증명 그 자체다. 누가 이 파일을 가져가면 그 사람이 된다.

- 파일 권한을 좁히고, 공유 드라이브나 저장소에 올리지 않는다.
- 쿠버네티스는 클라이언트 인증서 폐기 목록(CRL)을 지원하지 않는다. 인증서가 새면 만료되거나 CA를 바꿀 때까지 쓸 수 있다. 사람에게는 OIDC나 클라우드 IAM과 연결된 짧은 수명 토큰을 주고, client-go의 exec 자격 증명 플러그인으로 그때그때 받는다.
- `system:masters` 그룹은 RBAC를 건너뛴다. kubeadm은 v1.29부터 `admin.conf`를 RBAC가 적용되는 `kubeadm:cluster-admins` 그룹으로 만들고, RBAC를 우회하는 인증서는 `super-admin.conf`로 따로 둔다. super-admin.conf는 비상용으로만 보관한다.
- `insecure-skip-tls-verify`를 쓰지 않는다. 중간자 공격에 열린다.
- `kubectl auth whoami`로 지금 누구로 붙어 있는지 확인한다.

## 11. 스토리지

| 위험 | 대응 |
|---|---|
| etcd의 Secret이 평문 | EncryptionConfiguration, KMS |
| 볼륨 데이터가 디스크에 평문 | 암호화된 스토리지 클래스(클라우드 디스크 암호화, CSI 드라이버 옵션) |
| hostPath로 노드 파일 접근 | Pod Security Baseline으로 막기, 꼭 필요하면 읽기 전용과 경로 제한 |
| Retain 정책 PV의 이전 데이터 | 다시 쓰기 전에 지우기. PV는 클러스터 범위라 만들 권한도 좁힌다 |
| 백업에 든 Secret | 백업 암호화와 접근 제한 |

Secret을 볼륨으로 마운트하면 노드의 tmpfs(메모리)에 올라가서 디스크에 남지 않는다. 환경 변수로 넣으면 프로세스 정보나 로그로 새기 쉬워서 파일 마운트가 낫다.

> **쉬운 설명**
>
> 클러스터를 은행으로 보면 API 서버는 창구다. 신분 확인(인증), 권한 확인(인가), 서류 검사(어드미션)를 하고 기록(감사 로그)을 남긴다. etcd는 금고라서 창구 직원만 들어간다. kubelet은 지점장이라, 본점(API 서버)의 지시를 받아 지점 금고(노드의 컨테이너)를 연다. 지점장 사무실 문을 잠그지 않으면(익명 kubelet API) 지나가던 사람도 금고를 연다. 런타임 소켓은 지점 마스터키다. kubeconfig는 출입증인데, 은행이 출입증을 하나씩 정지할 수 없어서(인증서 폐기 불가) 유효 기간이 짧은 출입증을 쓰는 게 안전하다.

## 헷갈렸던 것들

- kubelet API(10250)로는 exec까지 된다. 익명 인증을 끄고 Webhook 인가를 쓴다.
- 10255는 인증 없는 읽기 전용 포트다. `readOnlyPort: 0`으로 닫는다.
- Secret 저장 암호화는 etcd가 아니라 API 서버의 EncryptionConfiguration이 한다. providers의 첫 항목이 실제 쓰기에 쓰인다.
- 쿠버네티스는 클라이언트 인증서를 하나씩 폐기하지 못한다.
- `system:masters`는 RBAC를 우회한다. kubeadm admin.conf는 v1.29부터 이 그룹이 아니다.
- NodeRestriction은 어드미션, Node는 인가 모드다. 둘이 같이 kubelet을 자기 노드에 묶는다.
- 런타임 소켓을 마운트한 파드는 노드 root와 같다.

## 용어 정리

| 용어 | 뜻 |
|---|---|
| mTLS | 양쪽이 서로 인증서를 확인하는 TLS |
| EncryptionConfiguration | API 서버가 리소스를 etcd에 저장할 때 쓸 암호화 방식을 정하는 설정 |
| KMS 프로바이더 | 암호화 키를 외부 키 관리 시스템이 쥐게 하는 방식 |
| Node 인가 모드 | kubelet의 요청을 자기 노드와 관련된 것으로 제한하는 인가 방식 |
| NodeRestriction | kubelet이 자기 Node와 자기 노드의 파드만 고치게 하는 어드미션 플러그인 |
| API Priority and Fairness | API 서버 요청을 우선순위별로 나눠 과부하를 막는 기능 |
| Konnectivity | 컨트롤 플레인에서 노드로 가는 연결을 터널로 보내는 프록시 |
| system:masters | RBAC를 우회하는 특수 그룹 |

## 복습 문제

**1.** Which kubelet setting stops unauthenticated requests to the kubelet API on port 10250?

- A. `readOnlyPort: 10255`
- B. `rotateCertificates: true`
- C. `serverTLSBootstrap: false`
- D. `authentication.anonymous.enabled: false`

**2.** Which admission plugin limits a kubelet so that it can modify only its own Node object and the Pods bound to its node?

- A. NodeRestriction
- B. AlwaysPullImages
- C. PodSecurity
- D. LimitRanger

**3.** Which component should be the only client allowed to connect to etcd?

- A. kubelet
- B. kube-proxy
- C. kube-apiserver
- D. kube-scheduler

**4.** A Pod mounts `/run/containerd/containerd.sock` from the host. Why is this dangerous?

- A. It slows down image pulls on the node.
- B. It lets the Pod control the container runtime and effectively gain root access to the node.
- C. It disables NetworkPolicy for the Pod.
- D. It stops log rotation on the node.

**5.** Which authorization mode must never be used on a production kube-apiserver?

- A. AlwaysAllow
- B. Node
- C. RBAC
- D. Webhook

**6.** Why are long-lived client certificates in kubeconfig files risky?

- A. They expire after one hour.
- B. They cannot be used together with RBAC.
- C. They are stored in etcd in plain text.
- D. Kubernetes cannot revoke an individual client certificate before it expires.

**7.** Which kube-apiserver flag enables encryption of Secret data at rest in etcd?

- A. `--audit-policy-file`
- B. `--client-ca-file`
- C. `--encryption-provider-config`
- D. `--anonymous-auth`

**8.** Why should kube-scheduler and kube-controller-manager bind to `127.0.0.1`?

- A. To make scheduling faster
- B. To avoid exposing their health, metrics, and profiling endpoints to the network
- C. Because they cannot use TLS
- D. Because etcd requires it

## 답과 풀이

1. **D** 익명 인증을 끈다. 10255는 오히려 인증 없는 포트라 0으로 닫아야 한다.
2. **A** NodeRestriction 어드미션이다. Node 인가 모드와 함께 kubelet을 자기 노드에 묶는다.
3. **C** etcd에는 API 서버만 붙어야 한다. 직접 접근은 RBAC와 어드미션을 모두 건너뛴다.
4. **B** 런타임 소켓으로 privileged 컨테이너를 띄우면 노드를 장악할 수 있다.
5. **A** AlwaysAllow는 모든 요청을 허용한다.
6. **D** CRL을 지원하지 않아서 유출된 인증서를 만료 전에 막을 방법이 마땅치 않다.
7. **C** EncryptionConfiguration 파일을 가리키는 플래그다.
8. **B** 같은 노드 밖에서 이 엔드포인트에 닿지 못하게 한다.

## 참고 자료

- Kubernetes 문서, 클러스터 보호하기: <https://kubernetes.io/docs/tasks/administer-cluster/securing-a-cluster/>
- Kubernetes 문서, 컨트롤 플레인과 노드 사이 통신: <https://kubernetes.io/docs/concepts/architecture/control-plane-node-communication/>
- Kubernetes 문서, kubelet 인증과 인가: <https://kubernetes.io/docs/reference/access-authn-authz/kubelet-authn-authz/>
- Kubernetes 문서, Node 인가: <https://kubernetes.io/docs/reference/access-authn-authz/node/>
- Kubernetes 문서, 어드미션 컨트롤러: <https://kubernetes.io/docs/reference/access-authn-authz/admission-controllers/>
- Kubernetes 문서, 저장된 Secret 암호화: <https://kubernetes.io/docs/tasks/administer-cluster/encrypt-data/>
- Kubernetes 문서, PKI 인증서와 요구 사항: <https://kubernetes.io/docs/setup/best-practices/certificates/>
- Kubernetes 문서, 인증(클라이언트 인증서, OIDC, 자격 증명 플러그인): <https://kubernetes.io/docs/reference/access-authn-authz/authentication/>
- Kubernetes 문서, API 서버 우회 위험: <https://kubernetes.io/docs/concepts/security/api-server-bypass-risks/>
- Kubernetes 문서, etcd 운영: <https://kubernetes.io/docs/tasks/administer-cluster/configure-upgrade-etcd/>
- Kubernetes 문서, API Priority and Fairness: <https://kubernetes.io/docs/concepts/cluster-administration/flow-control/>
- Kubernetes 문서, kubeadm 구현 세부 사항: <https://kubernetes.io/docs/reference/setup-tools/kubeadm/implementation-details/>
- Kubernetes 문서, kubelet 설정 API: <https://kubernetes.io/docs/reference/config-api/kubelet-config.v1beta1/>
- Kubernetes 문서, 포트와 프로토콜: <https://kubernetes.io/docs/reference/networking/ports-and-protocols/>
- CIS Kubernetes Benchmark: <https://www.cisecurity.org/benchmark/kubernetes>


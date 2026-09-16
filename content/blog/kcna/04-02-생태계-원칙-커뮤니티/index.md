---
title: '[KCNA] 클라우드 네이티브 생태계와 원칙, 커뮤니티: 오토스케일링, 서버리스, 오픈 표준, CNCF와 쿠버네티스 거버넌스'
date: '2026-09-16T22:00:00+09:00'
categories:
- KCNA
tags:
- kubernetes
- kcna
- cloud-native
- cncf
- autoscaling
- hpa
- vpa
- cluster-autoscaler
- karpenter
- keda
- serverless
- knative
- cloudevents
- open-standards
- sig
- kep
- governance
- Cloud Native Architecture
series:
- KCNA
series_order: 12
---

Cloud Native Architecture의 남은 두 항목을 한 글에 묶었다. Ecosystem and Principles에는 예전 범위의 오토스케일링, 서버리스, 오픈 표준이, Community and Collaboration에는 커뮤니티와 거버넌스, 역할과 페르소나가 들어간다고 봤다. 실기 시험에서는 한 번도 나오지 않은 내용이라 이번에 처음 제대로 읽었다. 작년에 CNCF TAG 구조가 바뀌었고, 올해 graduated가 된 프로젝트도 있어서 예전 자료와 이름이나 단계가 다른 곳이 있다.

## 요약

- CNCF는 클라우드 네이티브를 '동적인 환경에서 확장 가능한 앱을 만들고 운영하게 해 주는 기술'로 정의하고, 컨테이너, 서비스 메시, 마이크로서비스, 바뀌지 않는 인프라, 선언형 API를 예로 든다.
- 오토스케일링은 층이 나뉜다. HPA는 파드 수, VPA는 파드 크기, Cluster Autoscaler와 Karpenter는 노드 수, KEDA는 이벤트 기반으로 0까지 줄인다.
- 서버리스는 서버를 직접 관리하지 않고 요청이나 이벤트가 올 때 실행해서 쓴 만큼만 내는 방식이다. Knative(2025년 graduated)가 쿠버네티스 위의 서버리스이고, CloudEvents(2024년 graduated)가 이벤트 형식 표준이다.
- 쿠버네티스는 OCI, CRI, CNI, CSI 같은 표준 인터페이스 위에 서 있다.
- CNCF는 Linux Foundation 산하다. TOC가 기술 방향과 프로젝트 성숙도(Sandbox, Incubating, Graduated)를 정한다. TAG는 2025년에 다섯 개로 다시 짜였다.
- 쿠버네티스 프로젝트는 Steering Committee, SIG, WG, KEP로 움직인다. 기여자는 member, reviewer, approver, subproject owner 순으로 올라간다.

## 1. 클라우드 네이티브란

CNCF의 정의를 줄이면 이렇다. 퍼블릭, 프라이빗, 하이브리드 클라우드 같은 동적인 환경에서 확장 가능한 앱을 만들고 운영하는 기술이고, 그 결과 느슨하게 결합되고, 회복력 있고, 관리하기 쉽고, 관찰할 수 있는 시스템이 된다. 자동화와 함께 쓰면 큰 변경을 자주, 예측 가능하게, 적은 노력으로 할 수 있다.

| 원칙 | 뜻 |
|---|---|
| 마이크로서비스 | 기능별로 작게 나눠 따로 배포하고 따로 늘린다 |
| 컨테이너 | 앱과 의존성을 한 이미지로 묶어 어디서나 같게 돈다 |
| 선언형 API | 원하는 상태를 적으면 시스템이 맞춘다 |
| 바뀌지 않는 인프라 | 돌고 있는 서버를 고치지 않고, 새 이미지로 갈아 끼운다 |
| 자동화 | 배포, 복구, 확장을 사람이 아닌 시스템이 한다 |
| 회복력 | 일부가 죽어도 전체가 버틴다. 재시도, 복제, 자가 치유 |
| 관찰 가능성 | 로그, 지표, 트레이스로 안을 들여다본다 |

서버를 이름 붙여 정성껏 돌보는 '애완동물'이 아니라, 아프면 바꾸는 '가축'처럼 다룬다는 비유도 자주 나온다. 앱을 설계할 때는 12-Factor App 원칙을 많이 인용한다. 설정은 환경 변수로, 프로세스는 상태 없이, 로그는 이벤트 스트림으로 내보내고, 빨리 시작하고 우아하게 종료하는 것 같은 내용이다.

| | 모놀리스 | 마이크로서비스 |
|---|---|---|
| 배포 | 전체를 한 번에 | 서비스마다 따로 |
| 확장 | 전체를 같이 | 필요한 서비스만 |
| 장애 범위 | 한 곳 문제가 전체로 번지기 쉽다 | 격리하기 쉽지만 네트워크 호출이 늘어 복잡하다 |

## 2. 오토스케일링

{{< mermaid >}}
flowchart TB
  E["이벤트 소스<br>큐 길이, Kafka 랙"] --> KEDA["KEDA<br>0 ↔ 1, 그 위는 HPA에 맡김"]
  KEDA --> HPA
  M["metrics-server, 사용자 지표"] --> HPA["HPA<br>파드 수"]
  M --> VPA["VPA<br>파드의 requests, limits"]
  HPA --> PEND{"자리가 없어<br>Pending인가"}
  PEND -->|"그렇다"| CA["Cluster Autoscaler, Karpenter<br>노드 추가"]
  CA -.->|"한가한 노드는"| DEL["파드를 옮기고 노드 제거"]
{{< /mermaid >}}

| 도구 | 바꾸는 것 | 기준 | 비고 |
|---|---|---|---|
| HPA | 파드 수 | CPU, 메모리, 사용자 지표, 외부 지표 | 쿠버네티스 내장(`autoscaling/v2`) |
| VPA | 파드의 requests, limits | 과거 사용량 | 별도 설치(kubernetes/autoscaler). Off 모드는 추천만 한다 |
| Cluster Autoscaler | 노드 수 | 자원이 모자라 Pending인 파드 | 노드 그룹 단위로 늘린다 |
| Karpenter | 노드 수와 종류 | Pending 파드에 맞는 노드를 바로 만든다 | SIG Autoscaling 서브프로젝트, CNCF 프로젝트는 아니다 |
| KEDA | 파드 수(0 포함) | 큐 길이 같은 이벤트 소스 | CNCF graduated(2023년). 내부적으로 HPA를 만든다 |

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: api
  namespace: shop
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: api
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 50     # requests 대비 50%
```

HPA는 대략 `원하는 복제본 = 올림(지금 복제본 × 지금 지표 ÷ 목표 지표)`으로 계산한다. CPU 사용률은 requests 대비 퍼센트라서, 파드에 CPU requests가 없으면 계산하지 못한다. 줄일 때는 기본 5분(300초) 동안 지켜본 뒤 줄여서 들쭉날쭉한 변동을 막는다. HPA로 복제본을 0까지 줄이는 기능은 v1.37에서 beta가 됐다. 같은 CPU 지표로 HPA와 VPA를 함께 걸면 서로 싸우니 피한다.

## 3. 서버리스

서버리스는 서버를 없애는 게 아니라, 서버를 관리하는 일을 플랫폼에 맡기는 것이다. 요청이나 이벤트가 올 때만 실행되고, 아무도 안 쓰면 0으로 줄어서 비용도 0에 가깝다. 대신 0에서 깨어날 때 첫 요청이 늦는 콜드 스타트가 있다.

| 형태 | 예 |
|---|---|
| 클라우드 함수(FaaS) | AWS Lambda, Google Cloud Run functions, Azure Functions |
| 쿠버네티스 위의 서버리스 | Knative Serving(요청에 따라 0까지 줄고 늘기, 리비전별 트래픽 분할), Knative Eventing(이벤트 전달) |

Knative는 2025년 9월에 CNCF graduated가 됐다. 이벤트를 주고받는 형식은 CloudEvents라는 CNCF 표준(2024년 1월 graduated)으로 맞춘다. 이벤트 종류, 출처, ID, 시간 같은 공통 속성을 정해 두어서, 어느 시스템이 보낸 이벤트든 같은 방식으로 읽을 수 있다.

## 4. 오픈 표준

| 표준 | 무엇을 정하나 |
|---|---|
| OCI(image, runtime, distribution) | 컨테이너 이미지 형식, 실행 방식, 레지스트리 배포 방식 |
| CRI | kubelet과 컨테이너 런타임 사이 인터페이스 |
| CNI | 컨테이너에 네트워크를 붙이는 플러그인 인터페이스 |
| CSI | 스토리지 드라이버 인터페이스 |
| CloudEvents | 이벤트 데이터 형식 |
| OpenTelemetry(OTLP) | 텔레메트리 수집과 전송 |
| Gateway API | 트래픽 라우팅 API. 서비스 메시 쪽은 GAMMA 작업으로 맞춘다 |

표준이 있어서 특정 업체에 묶이지 않고 구성 요소를 바꿔 끼울 수 있다. 예전에 서비스 메시 표준으로 나왔던 SMI(Service Mesh Interface)는 보관됐고, 그 역할은 Gateway API 쪽으로 넘어갔다.

## 5. CNCF의 구조

{{< mermaid >}}
flowchart TB
  LF["Linux Foundation"] --> CNCF["CNCF"]
  CNCF --> GB["Governing Board<br>예산, 마케팅, 사업"]
  CNCF --> TOC["Technical Oversight Committee<br>기술 방향, 프로젝트 승인과 성숙도"]
  TOC --> TAG["TAG 5개<br>분야별 기술 자문"]
  TOC --> P["프로젝트<br>Sandbox → Incubating → Graduated"]
{{< /mermaid >}}

| 성숙도 | 뜻 | 예 |
|---|---|---|
| Sandbox | 초기 실험 단계. 들어오는 문턱이 낮다 | 새로 들어온 프로젝트들 |
| Incubating | 실제 운영에서 쓰는 곳이 있고 기여자가 늘고 있다 | Backstage, KubeVirt, OpenCost, Thanos, Cortex, Longhorn |
| Graduated | 널리 쓰이고 거버넌스와 보안 감사까지 갖췄다 | Kubernetes, Prometheus, Envoy, CoreDNS, containerd, etcd, Helm, Argo, Flux, Istio, Linkerd, Cilium, Falco, KEDA, Knative, Kyverno, OpenTelemetry, CloudEvents |
| Archived | 더 이상 활발하지 않아 보관됨 | Keptn(2025년 9월) |

올해 graduated가 된 Kyverno(3월)와 OpenTelemetry(5월)는 예전 자료에 incubating으로 나온다. Karpenter, Grafana, Tekton은 CNCF 프로젝트가 아니다. 전체 생태계는 CNCF Landscape(landscape.cncf.io)에 분야별로 모여 있다.

TAG(Technical Advisory Group)는 TOC를 돕는 분야별 그룹이다. 2025년 6월부터 다섯 개로 다시 짜였다.

| 지금 TAG | 다루는 것 | 합쳐진 예전 TAG |
|---|---|---|
| Developer Experience | 마이크로서비스, 메시징, API, 개발 프레임워크 | App Delivery |
| Infrastructure | 스토리지, 네트워킹, DNS, 서비스 메시, IaC | Storage, Network |
| Operational Resilience | 관찰 가능성, 비용 효율, 신뢰성, 카오스 엔지니어링 | Observability, Environmental Sustainability |
| Security and Compliance | 정책 코드화, 컴플라이언스, 위협 모델링, 공급망 보안 | Security |
| Workloads Foundation | 컨테이너, 런타임, 서버리스, 스케줄링, 오토스케일링, CI/CD | Runtime |

## 6. 쿠버네티스 커뮤니티와 협업

| 조직 | 하는 일 |
|---|---|
| Steering Committee | 프로젝트 전체 거버넌스. 선거로 뽑는다 |
| SIG(Special Interest Group) | 분야를 오래 맡는 상설 그룹. SIG Network, SIG Storage, SIG Node, SIG Auth, SIG Apps, SIG Scheduling, SIG Release, SIG Docs 등. 코드와 서브프로젝트를 소유한다 |
| WG(Working Group) | 여러 SIG에 걸친 주제를 잠깐 모여 다루는 임시 그룹. 코드를 소유하지 않는다 |
| Committee | Code of Conduct Committee, Security Response Committee처럼 특정 책임을 맡는 그룹 |
| 릴리스 팀 | 릴리스마다 꾸려져 일정과 기능 추적을 맡는다 |

큰 기능은 KEP(Kubernetes Enhancement Proposal)로 제안한다. 무엇을 왜 바꾸는지, 설계, 테스트 계획, alpha에서 beta, stable로 가는 기준을 적고, 담당 SIG가 승인한다. 기능 단계(alpha, beta, stable)도 KEP를 따라 올라간다.

기여자는 단계를 밟는다. 처음에는 누구나 이슈와 PR을 낼 수 있고, 꾸준히 기여하면 쿠버네티스 GitHub 조직의 member가 된다. 그다음 코드 리뷰를 맡는 reviewer, 변경을 승인하는 approver, 서브프로젝트를 책임지는 subproject owner로 간다. 모든 참여자는 CNCF Code of Conduct를 따르고, 소통은 Slack, 메일링 리스트, SIG 정기 회의(녹화 공개)에서 한다. 6월에 정리했던 것처럼 AI로 만든 기여는 공개하고 사람이 책임지는 규칙도 생겼다. 사람들이 직접 만나는 자리는 KubeCon + CloudNativeCon이다.

## 7. 역할과 페르소나

| 역할 | 주로 하는 일 |
|---|---|
| 애플리케이션 개발자 | 앱을 만들고 컨테이너로 묶고 배포 매니페스트를 쓴다 |
| DevOps 엔지니어 | 개발과 운영 사이의 빌드, 배포 자동화 |
| SRE | 신뢰성 목표(SLO)를 정하고 장애 대응과 자동화로 지킨다 |
| 플랫폼 엔지니어 | 개발자가 셀프 서비스로 쓰는 내부 개발자 플랫폼을 만든다. Backstage 같은 포털을 쓴다 |
| 클러스터 운영자, 관리자 | 클러스터 설치, 업그레이드, 용량, 보안 |
| 보안 엔지니어(DevSecOps) | 공급망, 정책, 런타임 보안을 개발 흐름에 넣는다 |
| 클라우드 아키텍트 | 전체 구조와 기술 선택 |
| FinOps 담당 | 비용을 보이게 하고 줄인다 |

> **쉬운 설명**
>
> CNCF는 프로 스포츠 연맹과 비슷하다. 새로 들어온 팀은 2군(Sandbox)에서 시작해 1군(Incubating)으로 올라가고, 오래 잘한 팀은 명문 구단(Graduated)이 된다. 연맹의 기술위원회(TOC)가 승격을 정하고, 분야별 자문단(TAG)이 돕는다. 쿠버네티스라는 구단 안에는 포지션별 코치진(SIG)이 있고, 새 전술을 쓰려면 전술 제안서(KEP)를 내야 한다. 오토스케일링은 식당 운영으로 보면 된다. HPA는 손님 수에 맞춰 직원 수를, VPA는 직원 한 명이 맡는 일의 양을, Cluster Autoscaler는 매장 크기를 늘리고 줄인다. KEDA는 가게 앞 대기 줄을 보고 문을 열고 닫는다.

## 헷갈렸던 것들

- HPA는 파드 수, VPA는 파드 크기, Cluster Autoscaler는 노드 수다.
- HPA의 CPU 목표는 requests 대비다. requests가 없으면 계산하지 못한다.
- Karpenter는 CNCF 프로젝트가 아니라 SIG Autoscaling 서브프로젝트다.
- 성숙도는 Sandbox, Incubating, Graduated 순이다. alpha, beta, stable은 쿠버네티스 기능 단계라 다른 이야기다.
- SIG는 상설이고 코드를 소유한다. WG는 임시이고 코드를 소유하지 않는다.
- OpenTelemetry와 Kyverno는 2026년에 graduated가 됐다.
- CNCF TAG 이름이 2025년에 바뀌었다.

## 용어 정리

| 용어 | 뜻 |
|---|---|
| 클라우드 네이티브 | 동적인 환경에서 확장 가능한 앱을 만들고 운영하는 기술과 방식 |
| 바뀌지 않는 인프라 | 서버를 고치지 않고 새 것으로 갈아 끼우는 운영 방식 |
| HPA | 지표에 따라 파드 수를 바꾸는 쿠버네티스 내장 오토스케일러 |
| VPA | 파드의 requests와 limits를 조정하는 오토스케일러 |
| KEDA | 이벤트 소스에 따라 0까지 늘리고 줄이는 오토스케일러 |
| 서버리스 | 서버 관리를 플랫폼에 맡기고 요청이 있을 때만 실행하는 방식 |
| CloudEvents | 이벤트 데이터를 기술하는 CNCF 표준 |
| TOC | CNCF의 기술 방향과 프로젝트 성숙도를 정하는 위원회 |
| SIG | 쿠버네티스의 분야별 상설 그룹 |
| KEP | 쿠버네티스 기능 제안과 설계 문서 |

## 복습 문제

**1.** Which component adds nodes to a cluster when Pods cannot be scheduled because of insufficient resources?

- A. HorizontalPodAutoscaler
- B. VerticalPodAutoscaler
- C. kube-scheduler
- D. Cluster Autoscaler

**2.** Which project scales workloads based on event sources such as queue length and can scale them down to zero?

- A. Prometheus
- B. KEDA
- C. Helm
- D. CoreDNS

**3.** What is the correct order of CNCF project maturity levels?

- A. Sandbox, Incubating, Graduated
- B. Incubating, Sandbox, Graduated
- C. Alpha, Beta, Stable
- D. Sandbox, Graduated, Incubating

**4.** In the Kubernetes project, which document proposes and tracks a significant enhancement?

- A. A SIG charter
- B. A Code of Conduct report
- C. A Kubernetes Enhancement Proposal (KEP)
- D. A CNCF due diligence document

**5.** Which kind of group in the Kubernetes community owns an area such as networking or storage on a long-term basis?

- A. A working group
- B. The Steering Committee
- C. The release team
- D. A special interest group (SIG)

**6.** Which CNCF specification defines a common format for describing event data?

- A. CloudEvents
- B. CNI
- C. CSI
- D. The OCI image specification

**7.** Which CNCF body decides the technical vision of the foundation and approves moving projects between maturity levels?

- A. The Governing Board
- B. The Technical Oversight Committee (TOC)
- C. The Kubernetes Steering Committee
- D. The Linux Foundation legal team

**8.** A HorizontalPodAutoscaler targets 50% CPU utilization. What is this percentage calculated against?

- A. The node's total CPU capacity
- B. The container's CPU limit
- C. The container's CPU request
- D. The cluster's total CPU capacity

## 답과 풀이

1. **D** Cluster Autoscaler가 노드를 늘린다. HPA와 VPA는 파드 쪽, 스케줄러는 배치만 한다.
2. **B** KEDA는 이벤트 소스를 보고 0과 1 사이를 직접 오가고, 그 위는 HPA를 만들어 맡긴다.
3. **A** Sandbox, Incubating, Graduated 순이다. C는 쿠버네티스 기능 단계다.
4. **C** KEP로 제안하고, 담당 SIG가 승인하며, 단계별 기준을 추적한다.
5. **D** SIG는 상설이고 코드와 서브프로젝트를 소유한다. WG는 임시다.
6. **A** CloudEvents다. 2024년 1월에 graduated가 됐다.
7. **B** TOC가 기술 방향과 프로젝트 승인, 성숙도를 맡는다. Governing Board는 예산과 사업이다.
8. **C** Utilization은 requests 대비 퍼센트다.

## 참고 자료

- CNCF, 클라우드 네이티브 정의: <https://github.com/cncf/toc/blob/main/DEFINITION.md>
- CNCF Landscape: <https://landscape.cncf.io/>
- CNCF 클라우드 네이티브 용어집: <https://glossary.cncf.io/>
- CNCF, 프로젝트 목록: <https://www.cncf.io/projects/>
- CNCF 블로그, TOC의 기술 그룹 개편: <https://www.cncf.io/blog/2025/05/07/10-years-in-cloud-native-toc-restructures-technical-groups/>
- Kubernetes 문서, 오토스케일링: <https://kubernetes.io/docs/concepts/workloads/autoscaling/>
- Kubernetes 문서, HorizontalPodAutoscaler: <https://kubernetes.io/docs/concepts/workloads/autoscaling/horizontal-pod-autoscale/>
- Kubernetes 문서, 노드 오토스케일링: <https://kubernetes.io/docs/concepts/cluster-administration/node-autoscaling/>
- KEDA: <https://keda.sh/>
- Knative 문서: <https://knative.dev/docs/>
- CloudEvents: <https://cloudevents.io/>
- The Twelve-Factor App: <https://12factor.net/>
- Kubernetes 커뮤니티, 거버넌스: <https://github.com/kubernetes/community/blob/master/governance.md>
- Kubernetes 커뮤니티, SIG 목록: <https://github.com/kubernetes/community/blob/master/sig-list.md>
- Kubernetes 커뮤니티, 기여자 단계: <https://github.com/kubernetes/community/blob/master/community-membership.md>
- Kubernetes Enhancements(KEP): <https://github.com/kubernetes/enhancements>


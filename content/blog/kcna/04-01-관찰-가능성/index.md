---
title: '[KCNA] 관찰 가능성: 로그, 지표, 트레이스, Prometheus와 OpenTelemetry, 비용 관리'
date: '2026-09-13T15:30:00+09:00'
categories:
- KCNA
tags:
- kubernetes
- kcna
- observability
- logging
- metrics
- tracing
- prometheus
- promql
- opentelemetry
- jaeger
- fluent-bit
- metrics-server
- slo
- opencost
- Cloud Native Architecture
series:
- KCNA
series_order: 11
---

Observability는 예전 범위에서 8%짜리 도메인이었다가 Cloud Native Architecture 안의 항목이 됐다. 이름은 하나로 줄었지만 예전의 Prometheus와 Cost Management 항목도 여기 들어간다고 보고 같이 정리했다. OpenTelemetry가 올해 5월에 CNCF graduated가 돼서, 예전 자료에 incubating이라고 적힌 건 지금 기준으로 틀렸다.

## 요약

- 관찰 가능성은 시스템이 밖으로 내보내는 신호로 안쪽 상태를 알아내는 능력이다. 기본 신호는 로그, 지표, 트레이스 세 가지다.
- Prometheus(CNCF graduated)는 대상의 `/metrics`를 주기적으로 긁어 와서(pull) 시계열로 저장하고, PromQL로 묻고, Alertmanager로 알린다. 지표 타입은 counter, gauge, histogram, summary다.
- metrics-server는 지금의 CPU와 메모리만 들고 있다가 `kubectl top`과 HPA에 준다. 저장은 하지 않는다. kube-state-metrics는 오브젝트 상태를 지표로 바꾼다.
- 컨테이너 로그는 stdout, stderr로 내보내고, 노드마다 도는 에이전트(Fluent Bit 등)가 모아서 보낸다. `kubectl logs`는 노드에 남아 있는 것만 보인다.
- 트레이스는 요청 하나가 여러 서비스를 거치는 경로와 단계별 시간이다. OpenTelemetry는 신호를 만들고 내보내는 벤더 중립 표준(API, SDK, Collector, OTLP)이고, Jaeger는 트레이스 백엔드다.
- 목표는 SLI(측정값), SLO(목표치), SLA(약속과 보상)로 나눠 적는다.
- 비용은 실제 사용량보다 requests가 잡아 둔 자리에서 생긴다. 적정 크기, 오토스케일링, 스팟 노드, 라벨별 비용 배분(OpenCost)으로 줄인다.

## 1. 세 가지 신호

| 신호 | 담는 것 | 잘하는 일 | 예 |
|---|---|---|---|
| 로그 | 언제 무슨 일이 있었나(사건 기록) | 오류 원인, 특정 요청의 상세 | `2026-09-13T15:02:11Z ERROR payment timeout order=1042` |
| 지표 | 시간에 따른 숫자 | 추세, 대시보드, 알림. 저장 비용이 싸다 | 초당 요청 수, 오류율, 메모리 사용량 |
| 트레이스 | 요청 하나의 경로와 단계별 시간 | 어느 서비스에서 느려졌나 | 주문 API → 결제 → DB 구간별 지연 |

쿠버네티스 Events와 연속 프로파일링(어느 함수가 CPU를 쓰나)을 신호로 더 꼽기도 한다. 모니터링이 '미리 정한 것을 지켜보는 일'이라면, 관찰 가능성은 '미리 생각하지 못한 질문에도 신호로 답할 수 있는 상태'에 가깝다.

## 2. Prometheus

{{< mermaid >}}
flowchart TB
  G["Grafana 같은 대시보드"] -->|"PromQL"| P["Prometheus<br>시계열 DB, 기록·알림 규칙"]
  P -->|"알림"| AM["Alertmanager<br>묶기, 침묵, 메신저와 메일로"]
  P -->|"주기적으로 긁어 옴(pull)"| targets
  subgraph targets["수집 대상, /metrics"]
    A["앱"]
    N["node-exporter<br>노드 지표"]
    K["kube-state-metrics<br>오브젝트 상태"]
    C["kubelet, cAdvisor<br>컨테이너 지표"]
  end
{{< /mermaid >}}

Prometheus는 2018년에 쿠버네티스 다음으로 CNCF graduated가 된 프로젝트다. 쿠버네티스 API로 서비스 디스커버리를 해서 파드와 서비스를 자동으로 찾는다. 대상이 내보내는 형식은 텍스트다.

```text
# HELP http_requests_total Total HTTP requests.
# TYPE http_requests_total counter
http_requests_total{method="GET",code="200"} 1027
http_requests_total{method="POST",code="500"} 3
```

| 지표 타입 | 특징 | 예 |
|---|---|---|
| counter | 늘기만 한다. 프로세스가 다시 시작하면 0으로 돌아간다 | 요청 수, 오류 수. `rate()`로 초당 값을 본다 |
| gauge | 오르내린다 | 메모리 사용량, 큐 길이, 온도 |
| histogram | 값을 구간(bucket)별로 센다. 서버에서 분위수를 계산한다 | 응답 시간 분포 |
| summary | 분위수를 클라이언트에서 미리 계산한다. 여러 인스턴스를 합치기 어렵다 | 응답 시간 분위수 |

```text
rate(http_requests_total[5m])                                   # 5분 평균 초당 요청 수
sum by (namespace) (container_memory_working_set_bytes)         # 네임스페이스별 메모리
histogram_quantile(0.95, sum by (le) (rate(http_request_duration_seconds_bucket[5m])))  # p95 지연
```

몇 초 만에 끝나는 배치 작업은 긁어 갈 틈이 없어서 Pushgateway로 밀어 넣는다. 쿠버네티스에서는 Prometheus Operator(ServiceMonitor, PodMonitor CRD)나 kube-prometheus-stack 차트로 많이 설치한다. Prometheus 하나로는 오래 저장하거나 여러 클러스터를 합치기 어려워서 Thanos나 Cortex(둘 다 CNCF incubating)를 붙인다. Grafana는 대시보드 도구이고 CNCF 프로젝트가 아니다.

## 3. 쿠버네티스 지표가 오는 곳

| 구성 요소 | 무엇을 주나 | 쓰는 곳 |
|---|---|---|
| metrics-server | 노드와 파드의 현재 CPU, 메모리(`metrics.k8s.io`). 저장하지 않는다 | `kubectl top`, HPA, VPA |
| kube-state-metrics | 오브젝트 상태를 지표로. 원하는 복제본 수, 파드 상태, 재시작 횟수 | Prometheus 대시보드와 알림 |
| node-exporter | 노드 OS 지표. 디스크, 네트워크, 파일 시스템 | Prometheus |
| cAdvisor | 컨테이너별 사용량. kubelet 안에 들어 있다 | Prometheus, metrics-server |
| 구성 요소 `/metrics` | API 서버, 스케줄러, etcd 같은 구성 요소 자체의 지표 | Prometheus |

HPA가 CPU, 메모리가 아닌 지표(큐 길이, 초당 요청 수)로 늘리려면 `custom.metrics.k8s.io`나 `external.metrics.k8s.io`를 제공하는 어댑터(Prometheus Adapter, KEDA)가 필요하다.

## 4. 로그

컨테이너는 로그를 stdout과 stderr로 내보내면 된다. 컨테이너 런타임이 이걸 노드의 파일(`/var/log/pods/...`)로 쓰고, kubelet이 크기를 보고 파일을 돌린다. `kubectl logs`는 kubelet을 통해 이 파일을 읽는다. 그래서 파드가 지워지거나 노드가 사라지면 `kubectl logs`로는 더 볼 수 없다. 로그를 클러스터 밖에 남기는 방식은 세 가지다.

| 방식 | 설명 |
|---|---|
| 노드 에이전트 | DaemonSet으로 노드마다 에이전트(Fluent Bit, Fluentd, OpenTelemetry Collector)를 띄워 노드의 로그 파일을 읽어 보낸다. 가장 흔하다 |
| 사이드카 | 파일로만 로그를 쓰는 앱 옆에 사이드카를 두고 stdout으로 다시 내보내거나 직접 보낸다 |
| 앱이 직접 전송 | 앱이 로그 백엔드로 바로 보낸다 |

Fluentd와 Fluent Bit은 같은 Fluentd 프로젝트(CNCF graduated)에 속한다. Fluent Bit이 더 가볍다. 로그는 키-값이 있는 구조화된 형식(JSON)으로 남기면 나중에 찾기 쉽다.

## 5. 트레이스와 OpenTelemetry

트레이스는 요청 하나에 붙은 trace ID와, 각 구간을 나타내는 span의 나무다. 서비스끼리 요청을 넘길 때 `traceparent` 헤더(W3C Trace Context)로 trace ID를 같이 넘겨서 이어 붙인다.

{{< mermaid >}}
flowchart LR
  A["앱<br>OpenTelemetry SDK,<br>자동 계측"] -->|"OTLP"| C["OpenTelemetry Collector<br>receiver → processor → exporter"]
  C --> M["지표 저장소<br>Prometheus 등"]
  C --> T["트레이스 저장소<br>Jaeger 등"]
  C --> L["로그 저장소"]
{{< /mermaid >}}

OpenTelemetry는 2019년에 OpenTracing과 OpenCensus가 합쳐져 만들어졌고, 2026년 5월 11일에 CNCF graduated가 됐다. 저장소나 대시보드가 아니라, 신호를 만들고 모으고 보내는 표준과 도구다.

- API와 언어별 SDK, 코드를 고치지 않는 자동 계측
- Collector: 받고(receiver), 거르고 가공해서(processor), 원하는 백엔드로 보낸다(exporter)
- OTLP: 신호를 주고받는 프로토콜

백엔드를 바꿔도 계측 코드는 그대로 두고 Collector의 exporter만 바꾸면 된다. Jaeger(CNCF graduated)는 트레이스를 저장하고 보여 주는 백엔드이고, v2부터는 OpenTelemetry Collector를 바탕으로 만들어졌다.

## 6. SLI, SLO, SLA

| 용어 | 뜻 | 예 |
|---|---|---|
| SLI | 서비스 수준을 재는 지표 | 성공한 요청 비율, p99 지연 |
| SLO | SLI의 목표치 | 30일 동안 요청의 99.9%가 성공 |
| SLA | 고객과 맺은 약속. 못 지키면 보상이 따른다 | 월 가용성 99.5% 미만이면 요금 10% 환불 |
| 오류 예산 | SLO가 허락하는 실패의 양 | 99.9%면 30일에 약 43분 |

무엇을 볼지는 Google SRE의 네 가지 골든 시그널(지연, 트래픽, 오류, 포화)이나, 서비스용 RED(요청률, 오류, 지연), 자원용 USE(사용률, 포화, 오류)로 고른다. 알림은 원인(CPU 80%)보다 사용자가 느끼는 증상(오류 예산이 빨리 줄어듦)에 거는 쪽이 낫다고 한다.

## 7. 비용 관리

- **requests가 비용이다**: 스케줄러는 requests로 자리를 잡는다. 실제로 10%만 쓰는 파드라도 requests만큼 노드 자리를 차지하니, 그만큼 노드를 더 사게 된다.
- **적정 크기**: VPA의 추천값이나 실제 사용량 지표를 보고 requests와 limits를 맞춘다.
- **오토스케일링**: HPA로 파드를, Cluster Autoscaler나 Karpenter로 노드를 수요에 맞춘다. 빈 노드가 줄어든다.
- **싼 노드**: 중단돼도 괜찮은 작업은 스팟(선점형) 노드에 둔다.
- **비용 배분**: 네임스페이스와 라벨(팀, 서비스)별로 비용을 나눠 보여 준다. OpenCost(CNCF incubating)가 쿠버네티스 자원 사용량을 비용으로 바꿔 준다. 이런 문화와 실무를 FinOps라고 부르고, Linux Foundation 산하에 FinOps Foundation이 있다.

> **쉬운 설명**
>
> 병원으로 보면 지표는 체온과 혈압 그래프, 로그는 진료 기록, 트레이스는 환자 한 명이 접수, 검사, 진료, 수납을 거친 동선과 단계별 대기 시간이다. Prometheus는 정해진 시간마다 병실을 돌며 수치를 재는 간호사다(pull). OpenTelemetry는 모든 검사 장비가 같은 양식으로 결과지를 내게 하는 표준 서식이라, 결과를 어느 병원 시스템(백엔드)에 넣든 서식을 다시 만들 필요가 없다.

## 헷갈렸던 것들

- metrics-server는 지금 값만 들고 있다. 기록과 알림은 Prometheus 같은 도구가 한다.
- kube-state-metrics는 사용량이 아니라 오브젝트 상태를 지표로 만든다.
- Prometheus는 기본이 pull이다. 짧은 작업만 Pushgateway로 push한다.
- counter는 줄지 않으니 `rate()`로 본다.
- Grafana는 대시보드 도구이고 CNCF 프로젝트가 아니다.
- OpenTelemetry는 저장소가 아니라 수집과 전송의 표준이다. 2026년 5월에 graduated가 됐다.
- `kubectl logs`는 파드가 지워지면 볼 수 없다. 그래서 노드 에이전트로 밖에 모은다.

## 용어 정리

| 용어 | 뜻 |
|---|---|
| 관찰 가능성 | 밖으로 나오는 신호로 시스템 안쪽 상태를 알아내는 능력 |
| 스크레이프 | Prometheus가 대상의 /metrics를 주기적으로 읽어 오는 것 |
| PromQL | Prometheus의 질의 언어 |
| Alertmanager | Prometheus 알림을 묶고 걸러서 보내는 구성 요소 |
| span | 트레이스 안의 한 구간. 시작, 끝, 속성을 가진다 |
| OTLP | OpenTelemetry의 신호 전송 프로토콜 |
| SLO | 서비스 수준 지표의 목표치 |
| 오류 예산 | SLO가 허락하는 실패의 양 |
| FinOps | 클라우드 비용을 엔지니어링과 재무가 같이 관리하는 실무 |

## 복습 문제

**1.** Which CNCF graduated project collects metrics by scraping HTTP endpoints and stores them as time series?

- A. Prometheus
- B. Jaeger
- C. Fluentd
- D. Grafana

**2.** Which Prometheus metric type only increases, except when it resets to zero after a restart?

- A. Gauge
- B. Histogram
- C. Counter
- D. Summary

**3.** Which component provides the current CPU and memory usage that `kubectl top` and the HorizontalPodAutoscaler use?

- A. kube-state-metrics
- B. metrics-server
- C. node-exporter
- D. Alertmanager

**4.** Which signal shows the path of a single request across several microservices and the time spent in each one?

- A. Logs
- B. Metrics
- C. Events
- D. Traces

**5.** What does OpenTelemetry provide?

- A. Vendor-neutral APIs, SDKs, and a Collector to generate, collect, and export telemetry
- B. A time-series database
- C. A dashboard UI
- D. A service mesh data plane

**6.** What is the most common way to collect container logs at the cluster level?

- A. Running `kubectl logs` on a schedule
- B. Running a logging agent such as Fluent Bit as a DaemonSet on every node
- C. Storing logs in etcd
- D. Mounting the same PersistentVolume into every Pod

**7.** A team sets the goal "99.9% of requests succeed over 30 days." What is this goal called?

- A. A service level agreement (SLA)
- B. A service level indicator (SLI)
- C. A service level objective (SLO)
- D. An error budget

## 답과 풀이

1. **A** Prometheus다. Jaeger는 트레이스, Fluentd는 로그다. Grafana는 대시보드 도구이고 CNCF 프로젝트가 아니다.
2. **C** counter는 늘기만 한다. 그래서 값 자체보다 `rate()`로 변화율을 본다.
3. **B** metrics-server가 `metrics.k8s.io`로 제공한다.
4. **D** 트레이스는 span으로 구간별 시간을 보여 준다.
5. **A** OpenTelemetry는 수집·전송 표준과 도구다. 저장소와 화면은 다른 도구가 맡는다.
6. **B** 노드마다 에이전트를 띄우는 방식이 가장 흔하다.
7. **C** 목표치가 SLO다. 측정값(성공 비율)이 SLI, 보상이 걸린 약속이 SLA다.

## 참고 자료

- Kubernetes 문서, 관찰 가능성: <https://kubernetes.io/docs/concepts/cluster-administration/observability/>
- Kubernetes 문서, 로깅 아키텍처: <https://kubernetes.io/docs/concepts/cluster-administration/logging/>
- Kubernetes 문서, 시스템 구성 요소 지표: <https://kubernetes.io/docs/concepts/cluster-administration/system-metrics/>
- Kubernetes 문서, 자원 지표 파이프라인: <https://kubernetes.io/docs/tasks/debug/debug-cluster/resource-metrics-pipeline/>
- kube-state-metrics: <https://github.com/kubernetes/kube-state-metrics>
- Prometheus 문서, 개요: <https://prometheus.io/docs/introduction/overview/>
- Prometheus 문서, 지표 타입: <https://prometheus.io/docs/concepts/metric_types/>
- OpenTelemetry, OpenTelemetry란: <https://opentelemetry.io/docs/what-is-opentelemetry/>
- CNCF, OpenTelemetry 프로젝트: <https://www.cncf.io/projects/opentelemetry/>
- Jaeger: <https://www.jaegertracing.io/>
- Fluent Bit: <https://fluentbit.io/>
- OpenCost: <https://opencost.io/>
- Google SRE 책, 서비스 수준 목표: <https://sre.google/sre-book/service-level-objectives/>


---
title: '[KCNA] 트러블슈팅: 파드 상태별 원인, describe와 logs와 events, 서비스와 노드 문제'
date: '2026-09-01T21:50:00+09:00'
categories:
- KCNA
tags:
- kubernetes
- kcna
- troubleshooting
- pending
- crashloopbackoff
- imagepullbackoff
- oomkilled
- kubectl-describe
- kubectl-logs
- kubectl-debug
- events
- Container Orchestration
series:
- KCNA
series_order: 8
---

Troubleshooting도 이번에 새로 이름이 붙은 항목이다. 객관식이라 명령을 직접 치기보다는 '이 증상이면 원인이 무엇이고 무엇부터 보나'를 고르는 문제가 나올 것 같아서, 증상에서 출발하는 표로 정리했다. 바탕은 CKA 트러블슈팅 정리이고, 상태 이름과 종료 코드처럼 외워야 하는 값을 더 챙겼다.

## 요약

- 보는 순서는 `kubectl get`(상태), `describe`(Events), `logs`(`--previous`), `exec`나 `debug`다.
- Pending은 노드를 못 찾은 상태다. 자원 부족, nodeSelector나 어피니티 불일치, 테인트, PVC 미바인딩이 흔한 원인이고 describe의 FailedScheduling에 이유가 나온다.
- ImagePullBackOff는 이미지 이름이나 태그 오타, 비공개 레지스트리 인증 문제다.
- CrashLoopBackOff는 컨테이너가 계속 죽어서 재시작을 기다리는 상태다. 원인은 이전 컨테이너 로그(`--previous`)와 종료 코드에서 찾는다.
- OOMKilled는 메모리 limits를 넘은 것이다. 종료 코드는 137이다.
- 파드는 Running인데 트래픽이 안 가면 readiness, 서비스 셀렉터, targetPort, NetworkPolicy 순서로 본다.
- Events는 기본 1시간만 남는다.

## 1. 기본 도구

```bash
kubectl get pods -o wide                       # 상태, 재시작 횟수, 노드, IP
kubectl describe pod web-7d4b9                 # 설정, 상태, 마지막 종료 이유, Events
kubectl get events -n shop --sort-by=.lastTimestamp
kubectl logs web-7d4b9 -c app                  # 컨테이너가 여럿이면 -c
kubectl logs web-7d4b9 --previous              # 죽기 전 컨테이너의 로그
kubectl logs deploy/web -f                     # 디플로이먼트의 파드 하나를 골라 따라 보기
kubectl exec -it web-7d4b9 -- sh               # 컨테이너 안에서 셸
kubectl debug -it web-7d4b9 --image=busybox:1.37 --target=app   # 임시 컨테이너로 붙기
kubectl debug node/worker-1 -it --image=busybox:1.37            # 노드 디버깅용 파드
kubectl top pods                               # metrics-server가 있어야 된다
kubectl port-forward svc/api 8080:80           # 내 PC에서 서비스로 바로 붙어 보기
```

셸이 없는 distroless 이미지에는 exec로 들어갈 수 없다. 이때 `kubectl debug`로 도구가 든 임시 컨테이너를 같은 파드에 붙인다. `--target`을 주면 대상 컨테이너의 프로세스까지 볼 수 있다.

## 2. 파드 상태별 원인

| 보이는 상태 | 뜻 | 흔한 원인 | 먼저 볼 것 |
|---|---|---|---|
| Pending | 노드가 정해지지 않았다 | requests가 커서 들어갈 노드가 없다, nodeSelector나 어피니티 불일치, 테인트, PVC가 Pending | describe의 Events(FailedScheduling) |
| ContainerCreating이 오래 감 | 노드는 정해졌는데 컨테이너를 못 만든다 | 볼륨 마운트 실패, CNI 문제, 큰 이미지 | describe의 Events |
| ErrImagePull, ImagePullBackOff | 이미지를 못 받아서 재시도를 기다린다 | 이름이나 태그 오타, 비공개 레지스트리 인증(imagePullSecrets), 레지스트리 접근 불가 | describe의 Events |
| CreateContainerConfigError | 컨테이너 설정을 만들 수 없다 | 참조한 ConfigMap, Secret, 키가 없다 | describe의 Events |
| CrashLoopBackOff | 컨테이너가 계속 종료되어 재시작을 기다린다 | 설정 오류, 잘못된 명령, 의존 서비스 없음, liveness 실패 | `logs --previous`, describe의 Last State |
| Running인데 READY 0/1 | 떠 있지만 준비되지 않았다 | readiness 프로브 실패 | describe의 Events(Readiness probe failed) |
| Terminating이 오래 감 | 지우는 중에 멈췄다 | finalizer가 남음, 노드 연결 끊김 | `get -o yaml`의 finalizers |
| Evicted, Failed | 노드 압박으로 쫓겨났다 | 메모리나 디스크 부족 | describe node의 Conditions |

describe의 Last State에 `Reason: OOMKilled`가 보이면 메모리 limits를 넘은 것이다. 노드 전체 메모리가 모자라서 kubelet이 내보낸 경우(Evicted)와 구분한다.

CrashLoopBackOff 상태에서 재시작 간격은 10초에서 시작해 두 배씩 늘어 최대 5분까지 간다. 컨테이너가 10분 동안 문제없이 돌면 처음으로 돌아간다.

![CrashLoopBackOff 재시작 대기 시간](./attachments/k8s-crashloop-backoff.png)
_재시작마다 대기 시간이 두 배로 늘다가 5분에서 멈춘다_

종료 코드도 원인을 알려 준다.

| 종료 코드 | 뜻 |
|---|---|
| 0 | 정상 종료. Deployment 파드가 이걸 반복하면 앱이 할 일 없이 끝나는 것이다 |
| 1 | 앱이 낸 일반 오류 |
| 126, 127 | 명령을 실행할 수 없음, 명령을 찾을 수 없음 |
| 137 | SIGKILL(128+9). OOMKilled이거나 종료 유예 시간 안에 안 끝나서 강제 종료 |
| 143 | SIGTERM(128+15)을 받고 끝남 |

## 3. 서비스로 트래픽이 안 갈 때

{{< mermaid >}}
flowchart TB
  A["1. 이름이 풀리나<br>debug 파드에서 nslookup api.shop"] --> B["2. 서비스가 있나, 포트가 맞나<br>kubectl get svc api -n shop"]
  B --> C["3. 엔드포인트가 있나<br>kubectl get endpointslices -l kubernetes.io/service-name=api"]
  C --> D["4. 비어 있으면<br>셀렉터와 파드 라벨, 파드 READY"]
  D --> E["5. 있으면<br>targetPort가 컨테이너가 듣는 포트인가"]
  E --> F["6. 그래도 안 되면<br>NetworkPolicy, 앱 로그"]
{{< /mermaid >}}

서비스 셀렉터가 틀리면 에러 없이 엔드포인트만 빈다. 그래서 '연결 거부'나 '타임아웃'만 보이고 원인 메시지는 없다. 이름 풀이가 안 되면 kube-system의 CoreDNS 파드 상태와 로그를 본다.

## 4. 노드와 컨트롤 플레인 문제

| 증상 | 의심할 곳 |
|---|---|
| 노드 NotReady | kubelet이 멈췄거나(`journalctl -u kubelet`), 컨테이너 런타임이 멈췄거나(`crictl ps`), CNI가 없거나, 인증서가 만료됐다 |
| 노드 Conditions에 MemoryPressure, DiskPressure, PIDPressure | 자원 부족. kubelet이 파드를 내보내기 시작한다 |
| kubectl 명령이 전부 connection refused | API 서버가 안 떠 있다. kubeadm 클러스터면 스태틱 파드 매니페스트 오류를 의심한다 |
| 새 파드가 Pending인데 FailedScheduling 이벤트조차 없다 | 스케줄러가 멈췄다 |
| Deployment를 만들었는데 ReplicaSet이나 파드가 안 생긴다 | 컨트롤러 매니저가 멈췄다 |
| `kubectl top`이 Metrics API를 찾을 수 없다고 한다 | metrics-server가 없다 |

노드가 끊기면 `node.kubernetes.io/unreachable` 테인트가 붙고, 파드는 기본 300초 뒤에 다른 노드로 옮겨 간다.

> **쉬운 설명**
>
> 자동차 고장 진단과 같다. `kubectl get`은 계기판 경고등을 보는 것이고, `describe`는 정비 기록(최근에 무슨 일이 있었나)이다. `logs`는 블랙박스 영상인데, 차가 이미 다시 시동이 걸렸으면 사고 직전 영상(`--previous`)을 따로 꺼내야 한다. `exec`는 보닛을 열어 보는 것이고, `debug`는 정비 기사가 장비를 들고 옆자리에 타는 것이다. 정비 기록은 1시간만 보관되니 빨리 봐야 한다.

## 헷갈렸던 것들

- CrashLoopBackOff는 원인이 아니라 결과다. 원인은 이전 컨테이너 로그와 종료 코드에 있다.
- 죽기 전 컨테이너의 로그는 `--previous`로 본다.
- Events는 기본 1시간 뒤 사라진다.
- `kubectl top`은 metrics-server가 있어야 된다.
- 스케줄러가 멈추면 FailedScheduling 이벤트도 안 남는다.
- 엔드포인트가 비어 있으면 셀렉터와 readiness부터 본다.
- 137은 OOM만 뜻하지 않는다. SIGKILL로 끝난 모든 경우다.

## 용어 정리

| 용어 | 뜻 |
|---|---|
| Events | 쿠버네티스 구성 요소가 남기는 사건 기록. 기본 1시간 보관 |
| CrashLoopBackOff | 컨테이너가 반복해서 종료되어 재시작을 기다리는 상태 |
| ImagePullBackOff | 이미지 받기에 실패해 재시도를 기다리는 상태 |
| OOMKilled | 메모리 limits를 넘어 커널이 컨테이너를 종료한 이유 표시 |
| 임시 컨테이너 | 실행 중인 파드에 디버깅용으로 붙이는 컨테이너 |
| metrics-server | 노드와 파드의 CPU, 메모리 사용량을 Metrics API로 제공하는 애드온 |
| finalizer | 오브젝트를 지우기 전에 끝내야 할 작업 표시 |

## 복습 문제

**1.** A Pod is in CrashLoopBackOff. Which command shows the logs of the container instance that crashed?

- A. `kubectl logs <pod> --follow`
- B. `kubectl describe node`
- C. `kubectl get events --watch`
- D. `kubectl logs <pod> --previous`

**2.** A Pod stays Pending, and its events say `0/3 nodes are available: 3 Insufficient memory.` What is the most likely fix?

- A. Increase the container's memory limit.
- B. Lower the Pod's memory request or add node capacity.
- C. Add a readiness probe.
- D. Change the imagePullPolicy.

**3.** A container's last state shows the reason OOMKilled and exit code 137. What does this mean?

- A. The image could not be pulled.
- B. The liveness probe timed out.
- C. The container exceeded its memory limit.
- D. The node ran out of disk space.

**4.** A Service has no endpoints, even though Pods that seem to match it are running. What should you check first?

- A. Whether the Service selector matches the Pod labels and whether the Pods are Ready
- B. The kube-scheduler logs
- C. The health of the etcd cluster
- D. The kernel version of the nodes

**5.** Which status is shown when the kubelet cannot pull a container image and is waiting before it tries again?

- A. CrashLoopBackOff
- B. CreateContainerConfigError
- C. Evicted
- D. ImagePullBackOff

**6.** `kubectl top pods` returns an error saying the Metrics API is not available. What is most likely missing?

- A. CoreDNS
- B. kube-proxy
- C. metrics-server
- D. The container runtime

**7.** A running Pod's image has no shell. You need debugging tools inside the Pod. Which command helps?

- A. `kubectl exec -it <pod> -- sh`
- B. `kubectl debug -it <pod> --image=busybox --target=app`
- C. `kubectl attach <pod>`
- D. `kubectl cp <pod>:/ ./`

## 답과 풀이

1. **D** 재시작된 지금 컨테이너가 아니라 죽기 전 컨테이너의 로그를 봐야 해서 `--previous`다.
2. **B** 스케줄러는 requests로 판단한다. limits를 올려도 Pending은 풀리지 않는다.
3. **C** 137은 128+9(SIGKILL)이고, Reason이 OOMKilled면 메모리 limits 초과다.
4. **A** 셀렉터가 틀리거나 파드가 Ready가 아니면 엔드포인트가 빈다.
5. **D** 받기에 실패하면 ErrImagePull, 재시도를 기다리는 동안은 ImagePullBackOff다.
6. **C** `kubectl top`은 metrics-server가 제공하는 Metrics API를 읽는다.
7. **B** 임시 컨테이너를 붙인다. 셸이 없으니 exec는 실패한다.

## 참고 자료

- Kubernetes 문서, 애플리케이션 디버깅: <https://kubernetes.io/docs/tasks/debug/debug-application/>
- Kubernetes 문서, 파드 디버깅: <https://kubernetes.io/docs/tasks/debug/debug-application/debug-pods/>
- Kubernetes 문서, 실행 중인 파드 디버깅: <https://kubernetes.io/docs/tasks/debug/debug-application/debug-running-pod/>
- Kubernetes 문서, 서비스 디버깅: <https://kubernetes.io/docs/tasks/debug/debug-application/debug-service/>
- Kubernetes 문서, 파드 실패 원인 알아내기: <https://kubernetes.io/docs/tasks/debug/debug-application/determine-reason-pod-failure/>
- Kubernetes 문서, 클러스터 디버깅: <https://kubernetes.io/docs/tasks/debug/debug-cluster/>
- Kubernetes 문서, DNS 이름 풀이 디버깅: <https://kubernetes.io/docs/tasks/administer-cluster/dns-debugging-resolution/>
- Kubernetes 문서, 자원 지표 파이프라인: <https://kubernetes.io/docs/tasks/debug/debug-cluster/resource-metrics-pipeline/>
- Kubernetes 문서, 파드 수명 주기: <https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/>


---
title: '[K8s 소식] 갱 스케줄링과 Workload API, 파드 통째 재시작, etcd v3.6 좀비 멤버'
date: '2026-01-17T15:00:00+09:00'
categories:
- Kubernetes
tags:
- kubernetes
- v1.35
- workload-api
- gang-scheduling
- opportunistic-batching
- restartallcontainers
- etcd
- etcd-v3.6
- upgrade
- 소식
series:
- Kubernetes 소식
series_order: 13
---

연말연시 내내 v1.35 후속 글이 거의 매일 올라왔다. 그중 세 편을 골랐다. 스케줄러가 파드 묶음을 한 단위로 다루기 시작한 워크로드 단위 스케줄링, 파드를 지우지 않고 컨테이너 전체를 처음부터 다시 띄우는 RestartAllContainers, 그리고 etcd v3.6으로 올릴 때 지워진 멤버가 되살아나는 좀비 멤버 문제다. 마지막 건 CKA 때 외운 etcdctl snapshot restore가 원인 중 하나로 나와서 더 눈에 들어왔다.

## 요약

- v1.35에 Workload API(scheduling.k8s.io/v1alpha1)와 갱 스케줄링이 alpha로 들어왔다. podGroup에 minCount를 주면 그 수만큼 한꺼번에 자리가 있을 때만 바인딩한다.
- 같은 스케줄링 조건의 파드를 묶어 계산을 재사용하는 opportunistic batching은 beta로 기본 켜짐이다. 따로 설정할 것은 없다.
- RestartAllContainers(alpha)는 컨테이너 재시작 규칙의 새 동작이다. 지정한 종료 코드가 나오면 파드 UID, IP, 볼륨은 그대로 두고 init 컨테이너부터 전부 다시 실행한다.
- etcd v3.5에서 v3.6으로 바로 올리면, 오래된 클러스터에서는 예전에 지운 멤버가 되살아나 클러스터가 멈출 수 있다. 반드시 v3.5.26 이상을 거쳐서 올린다.
- 좀비 멤버의 원인 중 하나가 v3.4 이하 etcdctl snapshot restore의 버그였다. 기존 멤버를 지우지 않고 새 멤버를 추가했다고 한다.

## 1. 워크로드 단위 스케줄링

지금까지 kube-scheduler는 파드를 하나씩 배치했다. 분산 학습처럼 워커 4개가 다 떠야 의미가 있는 작업은, 2개만 자리를 잡고 나머지 2개가 Pending이면 자원만 붙잡고 아무것도 못 한다. 두 작업이 서로 절반씩 잡고 기다리면 교착 상태가 된다. 그래서 Volcano나 Kueue 같은 별도 스케줄러를 쓰던 영역인데, v1.35부터 기본 스케줄러에 첫 단계가 들어왔다.

{{< mermaid >}}
flowchart TB
  A["파드 생성<br>spec.workloadRef로<br>Workload의 podGroup 연결<br>(Workload가 먼저 있어야 함)"] --> B{"대기 파드 수<br>≥ minCount?"}
  B -->|"아니오"| W["스케줄링 보류"]
  W -.-> B
  B -->|"예"| C["노드를 고르고<br>Permit 단계에서 바인딩 대기"]
  C --> D{"그룹 전체 자리를<br>찾았나?"}
  D -->|"예"| E["모두 한꺼번에 바인딩"]
  D -->|"5분 안에 일부만"| F["그룹 파드를 전부 거절<br>큐로 돌려보내고 자리를 반납"]
{{< /mermaid >}}

```yaml
apiVersion: scheduling.k8s.io/v1alpha1
kind: Workload
metadata:
  name: training-job-workload
  namespace: some-ns
spec:
  podGroups:
  - name: workers
    policy:
      gang:
        minCount: 4   # 4개가 동시에 뜰 수 있을 때만 스케줄
```

파드 쪽에는 spec.workloadRef에 name: training-job-workload, podGroup: workers를 적는다. Job이 무엇을 돌릴지 정한다면, Workload는 그 파드 묶음을 어떻게 배치할지를 정하는 리소스라고 이해했다.

| 기능 | 단계 | 켜는 법 |
|---|---|---|
| Workload API | alpha | kube-apiserver와 kube-scheduler에 GenericWorkload 기능 게이트, scheduling.k8s.io/v1alpha1 API 그룹 활성화 |
| 갱 스케줄링 | alpha | kube-scheduler에 GangScheduling 기능 게이트(Workload API 필요) |
| opportunistic batching | beta | 기본 켜짐. 끄려면 OpportunisticBatching 기능 게이트 |

opportunistic batching은 이미지, requests, 어피니티처럼 스케줄러가 보는 값이 똑같은 파드라면 앞 파드의 계산 결과를 뒤 파드에 재사용하는 최적화다. 디플로이먼트 레플리카는 대부분 서로 똑같으니 사용자가 할 일 없이 빨라진다. 다만 일부 기능을 쓰면 정확성을 위해 배칭이 꺼진다고 하니, 스케줄러 설정을 바꿔 쓰는 클러스터라면 문서의 제약을 한 번 봐야 한다.

## 2. 파드 통째 재시작, RestartAllContainers

v1.35에서 beta가 된 컨테이너 재시작 규칙(restartPolicyRules)에 새 동작이 붙었다. 지정한 종료 코드로 컨테이너가 끝나면 kubelet이 파드 안의 컨테이너를 전부 멈추고, init 컨테이너부터 다시 시작한다. 파드를 지우고 새로 만드는 것보다 훨씬 빠르다. 공식 글은 노드 1,000대 규모 학습에서 장애 때마다 파드를 다시 스케줄하는 비용이 한 달에 10만 달러가 넘을 수 있다고 했다.

| 그대로 유지 | 다시 실행 |
|---|---|
| 파드 UID, IP, 네트워크 네임스페이스 | init 컨테이너(순서대로 처음부터) |
| 파드 샌드박스와 붙은 장치 | 사이드카와 일반 컨테이너(이미 성공하거나 실패한 것도) |
| 모든 볼륨(emptyDir, PVC 포함) | 임시(ephemeral) 컨테이너는 종료만 되고 다시 뜨지 않는다 |

공식 예제 구조를 busybox로 바꿔서 kind에 띄워 봤다. kind 설정의 featureGates에 RestartAllContainersOnContainerExits: true를 넣으면 API 서버와 kubelet에 같이 켜진다. watcher 사이드카가 30초 뒤 종료 코드 88로 끝나면 파드 전체가 처음부터 다시 돈다.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: restart-all
spec:
  restartPolicy: Never
  volumes:
  - name: work
    emptyDir: {}
  initContainers:
  - name: setup
    image: busybox:1.37
    command: ["sh", "-c", "date >> /work/setup.log"]
    volumeMounts:
    - name: work
      mountPath: /work
  - name: watcher
    image: busybox:1.37
    restartPolicy: Always
    restartPolicyRules:
    - action: RestartAllContainers
      exitCodes:
        operator: In
        values: [88]
    command: ["sh", "-c", "sleep 30; exit 88"]
  containers:
  - name: main
    image: busybox:1.37
    command: ["sh", "-c", "cat /work/setup.log; sleep 3600"]
    volumeMounts:
    - name: work
      mountPath: /work
```

```bash
kubectl get pod restart-all -o wide -w          # IP와 노드는 그대로, RESTARTS만 오른다
kubectl logs restart-all -c main                # setup.log 줄이 재시작할 때마다 하나씩 는다
kubectl get pod restart-all -o jsonpath='{.status.conditions[?(@.type=="AllContainersRestarting")]}{"\n"}'
```

emptyDir가 유지되니 init 컨테이너가 쓴 줄이 쌓이고, main은 매번 처음부터 그 파일을 읽는다. 재시작 중에는 AllContainersRestarting 조건이 True가 됐다가 다시 False로 돌아간다. 주의할 점도 적혀 있었다. 이렇게 재시작할 때는 preStop 훅이 돌지 않고, 모든 컨테이너가 몇 번 다시 실행돼도 괜찮게(재진입 가능하게) 만들어야 한다.

## 3. etcd v3.6으로 올리기 전에 v3.5.26

5월에 etcd v3.6.0 소식을 정리하면서 백업, 복구 명령이 etcdutl로 옮겨 간다고 적었다. 이번 글은 그 v3.6으로 올릴 때의 함정이다.

{{< mermaid >}}
flowchart LR
  A["etcd v3.5.25 이하<br>멤버 정보: v2store가 기준<br>(v3store와 어긋났을 수 있음)"] -->|"바로 올리면"| Z["v3.6<br>v3store가 기준이 되면서<br>예전에 지운 멤버가 되살아남<br>좀비를 지울 때까지<br>클러스터 멈춤"]
  A -->|"먼저 올린다"| B["v3.5.26 이상<br>v2store 내용으로<br>v3store를 자동 동기화"]
  B --> C["모든 멤버가 healthy인지 확인"]
  C --> D["v3.6으로 업그레이드"]
{{< /mermaid >}}

v3.5까지는 멤버 정보의 기준이 v2store였고, v3.6부터는 v3store다. 오래된 클러스터에서는 두 저장소의 멤버 정보가 어긋나 있을 수 있는데, 그대로 v3.6으로 가면 v3store에만 남아 있던 옛 멤버가 다시 합의에 끼어든다.

| 알려진 원인 | 내용 |
|---|---|
| etcdctl snapshot restore 버그 | v3.4 이하에서 복구할 때 기존 멤버를 지우지 않고 새 멤버를 추가했다 |
| --force-new-cluster | v3.5 이하에서 드물게 옛 멤버가 덜 지워졌다. v3.5.22에서 고쳐졌다 |
| --unsafe-no-sync | 멤버 변경을 v3store에 쓰고 WAL에 쓰기 전에 죽으면 어긋날 수 있다 |

공식 글은 이 세 가지를 안 했다고 안심하지 말라고 했다. 아직 못 찾은 원인이 있을 수 있어서다. v3.5.26을 받을 수 없는 환경이라면 v3.6 업그레이드를 미루라고 했고, 우회 방법은 주지 않았다. CKA 시험 때는 단일 멤버 etcd라 멤버 목록을 볼 일이 없었는데, 운영 클러스터라면 업그레이드 전에 member list부터 보는 습관을 들여야겠다.

## 내 클러스터에서 확인할 것

```bash
kubectl -n kube-system get pods -l component=etcd -o jsonpath='{.items[*].spec.containers[0].image}{"\n"}'
ETCDCTL_API=3 etcdctl --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key \
  member list -w table                                   # 컨트롤 플레인 노드에서
kubectl api-resources --api-group=scheduling.k8s.io       # workloads가 보이면 Workload API가 켜진 것
```

- etcd 이미지가 3.5.25 이하면 3.6으로 바로 가지 말고 3.5.26 이상부터 올린다. kubeadm 클러스터는 kubeadm upgrade가 etcd도 같이 올리니, 어떤 etcd 버전으로 가는지 미리 본다.
- member list에 지금 컨트롤 플레인 노드 수보다 멤버가 많으면 이미 어긋난 것이다.
- 갱 스케줄링은 alpha라 운영 클러스터에서 켤 일은 아직 없다. 테스트 클러스터에서만 본다.

> **쉬운 설명**
>
> 갱 스케줄링은 4인 테이블 예약 같다. 4명이 다 앉을 자리가 없으면 2명만 먼저 앉히지 않고 다 같이 기다리게 한다. 2명만 앉아 있으면 자리만 차지하고 식사(작업)는 못 하기 때문이다. RestartAllContainers는 게임에서 '처음부터 다시하기'를 누르는 것이다. 게임기(파드)를 새로 사 오지 않고, 저장 파일(볼륨)은 남겨 둔 채 타이틀 화면(init 컨테이너)부터 다시 시작한다. etcd 좀비 멤버는 동아리 명단이 두 권이었는데 한 권에서만 탈퇴 처리가 된 것과 같다. 새 규칙으로 다른 명단을 기준으로 삼는 순간, 나간 사람이 투표에 다시 끼어든다. 그래서 v3.5.26이 먼저 두 명단을 맞춰 준다.

## 용어 정리

| 용어 | 뜻 |
|---|---|
| Workload API | 파드 묶음을 어떻게 스케줄할지 적는 리소스. v1.35 alpha |
| 갱 스케줄링 | 정해진 수(minCount)의 파드가 한꺼번에 들어갈 때만 배치하는 방식 |
| Permit 단계 | 스케줄러가 노드를 정한 뒤 바인딩하기 전에 기다리게 할 수 있는 단계 |
| opportunistic batching | 스케줄링 조건이 같은 파드의 계산 결과를 재사용하는 최적화 |
| RestartAllContainers | 지정한 종료 코드에 파드의 모든 컨테이너를 제자리에서 다시 시작하는 재시작 규칙 동작 |
| v2store, v3store | etcd 안의 옛 저장소와 새 저장소. v3.6부터 멤버 정보의 기준이 v3store |
| 좀비 멤버 | 예전에 지운 etcd 멤버가 업그레이드 뒤 다시 나타나 합의에 끼어드는 것 |

## 참고 자료

- Kubernetes 블로그, Introducing Workload Aware Scheduling: <https://kubernetes.io/blog/2025/12/29/kubernetes-v1-35-introducing-workload-aware-scheduling/>
- Kubernetes 블로그, New level of efficiency with in-place Pod restart: <https://kubernetes.io/blog/2026/01/02/kubernetes-v1-35-restart-all-containers/>
- Kubernetes 블로그, Avoiding Zombie Cluster Members When Upgrading to etcd v3.6: <https://kubernetes.io/blog/2025/12/21/preventing-etcd-zombies/>
- Kubernetes 문서, 파드 수명 주기: <https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/>
- etcd 문서, v3.5에서 v3.6으로 업그레이드: <https://etcd.io/docs/v3.6/upgrades/upgrade_3_6/>

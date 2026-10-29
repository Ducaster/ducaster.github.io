---
title: '[K8s 기초] 파드: 컨테이너를 한 번 더 감싸는 이유와 파드의 일생'
date: '2024-11-08T21:30:00+09:00'
categories:
- Kubernetes
tags:
- kubernetes
- pod
- container
- pause-container
- pod-lifecycle
- restartpolicy
- command
- args
- sidecar
- 워크로드
series:
- Kubernetes 기초
series_order: 5
---

쿠버네티스는 컨테이너를 바로 다루지 않고 파드라는 단위로 한 번 감싸서 다룬다. 왜 그렇게 하는지, 파드가 생겨서 사라질 때까지 어떤 상태를 거치는지를 kind에서 직접 띄워 보며 확인했다.

## 요약

- 파드는 쿠버네티스가 배포하는 가장 작은 단위다. 컨테이너 하나 이상을 묶고, 묶인 컨테이너는 IP(네트워크)와 볼륨을 같이 쓴다.
- 같은 파드의 컨테이너끼리는 localhost로 통신한다. 그래서 '항상 붙어 다녀야 하는 보조 컨테이너(사이드카)'를 같은 파드에 넣는다.
- 파드의 phase는 Pending, Running, Succeeded, Failed, Unknown 다섯 개뿐이다. kubectl get pods의 STATUS 열(CrashLoopBackOff 등)은 phase가 아니라 더 자세한 사유다.
- command는 이미지의 ENTRYPOINT를, args는 CMD를 덮어쓴다.
- 파드를 직접 만들면 죽거나 노드가 사라져도 다시 만들어지지 않는다. 그래서 보통은 디플로이먼트 같은 컨트롤러가 파드를 만들게 한다.

## 1. 왜 컨테이너가 아니라 파드인가

웹 서버와 그 로그를 밖으로 보내는 에이전트처럼, 항상 같은 서버에서 같이 떠야 하고 파일과 네트워크를 공유해야 하는 컨테이너 묶음이 있다. 쿠버네티스는 이 묶음을 파드라고 부르고, 파드 단위로 배치하고 재시작한다.

| 같은 파드의 컨테이너끼리 | 공유하나 |
|---|---|
| 네트워크(IP, 포트 공간) | 공유한다. localhost로 통신하고, 같은 포트를 두 컨테이너가 쓸 수 없다 |
| 볼륨 | 파드에 정의한 볼륨을 각자 마운트해서 공유한다 |
| 파일시스템(이미지) | 공유하지 않는다. 컨테이너마다 자기 이미지 |
| 배치되는 노드 | 항상 같은 노드 |
| 수명 | 파드가 지워지면 같이 지워진다 |

노드에서 보면 파드마다 pause라는 작은 컨테이너가 하나 더 떠 있다. 이 컨테이너가 파드의 네트워크 namespace를 붙들고 있고, 앱 컨테이너들이 거기에 합류하는 구조다.

```bash
kubectl run hello --image=nginx:1.27
kubectl get pod hello -o wide                       # 어느 노드인지 확인
docker exec study-worker crictl pods --name hello   # 파드 샌드박스(pause가 붙든 공간)
docker exec study-worker crictl ps --name hello     # 그 안의 앱 컨테이너(kubectl run은 컨테이너 이름을 파드 이름으로 짓는다)
```

## 2. 파드 하나 써 보기: 사이드카와 공유 볼륨

nginx가 쓰는 디렉터리에 다른 컨테이너가 5초마다 시각을 적는 파드를 만들었다.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: clock
  labels:
    app: clock
spec:
  containers:
  - name: web
    image: nginx:1.27
    ports:
    - containerPort: 80
    volumeMounts:
    - name: html
      mountPath: /usr/share/nginx/html
  - name: writer
    image: busybox:1.36
    command: ["sh", "-c"]
    args: ["while true; do date > /out/index.html; sleep 5; done"]
    volumeMounts:
    - name: html
      mountPath: /out
  volumes:
  - name: html
    emptyDir: {}
```

```bash
kubectl apply -f clock.yaml
kubectl get pod clock                           # READY 2/2
kubectl exec clock -c writer -- wget -qO- localhost   # writer에서 localhost로 nginx 호출. 시각이 나온다
kubectl logs clock -c web                       # 컨테이너가 둘이면 -c로 고른다
```

writer 컨테이너에서 localhost로 nginx에 붙는 게 신기했다. 같은 파드라 네트워크를 같이 쓰기 때문이다.

| 이미지(Dockerfile) | 파드(YAML) | 관계 |
|---|---|---|
| ENTRYPOINT | command | command를 쓰면 ENTRYPOINT를 덮어쓴다 |
| CMD | args | args를 쓰면 CMD를 덮어쓴다 |

## 3. 파드의 일생

{{< mermaid >}}
stateDiagram-v2
  [*] --> Pending: 생성됨
  Pending --> Running: 노드 배정, 이미지 받기, 컨테이너 시작
  Running --> Succeeded: 모든 컨테이너가 종료 코드 0으로 끝남
  Running --> Failed: 컨테이너가 실패로 끝나고 다시 시작하지 않음
  Running --> Unknown: 노드와 연락이 끊김
  Succeeded --> [*]
  Failed --> [*]
{{< /mermaid >}}

Pending은 스케줄 대기와 이미지 받는 시간까지 포함한다. Running은 '컨테이너가 하나라도 돌고 있거나, 시작·재시작하는 중'이라는 뜻이라, 계속 죽었다 살아나는 파드도 phase는 Running이다. kubectl get pods의 STATUS 열은 phase에 컨테이너 상태 사유를 섞어서 보여 준다.

| STATUS 열에 보이는 것 | 실제 의미 |
|---|---|
| ContainerCreating | 컨테이너 만드는 중(Pending) |
| ImagePullBackOff, ErrImagePull | 이미지를 못 받음. 이름·태그·레지스트리 권한 확인 |
| CrashLoopBackOff | 컨테이너가 계속 죽어서 재시작 간격을 늘리는 중 |
| Completed | 컨테이너가 정상 종료됨(Succeeded) |
| OOMKilled | 메모리 상한을 넘어 죽음 |
| Terminating | 지우는 중. 기본 30초 동안 정상 종료를 기다린다 |

restartPolicy는 파드 안 컨테이너를 같은 노드에서 다시 시작할지 정한다. 기본값은 Always이고, 잡처럼 끝나는 작업은 OnFailure나 Never를 쓴다. 노드가 사라지면 restartPolicy와 상관없이 그 파드는 끝이다.

```bash
kubectl run oops --image=busybox:1.36 -- sh -c 'echo bye; exit 1'
kubectl get pod oops -w                  # Error → CrashLoopBackOff, RESTARTS가 늘어난다
kubectl describe pod oops | grep -A5 'Last State'
kubectl logs oops --previous             # 직전에 죽은 컨테이너의 로그
kubectl delete pod oops clock hello
```

> **쉬운 설명**
>
> 컨테이너가 한 사람이라면 파드는 한 방을 같이 쓰는 룸메이트 묶음이다. 같은 방이라 주소(IP)가 하나고, 방 안에서는 큰 소리로 부르면(localhost) 들린다. 책상 위 공용 서랍(볼륨)도 같이 쓴다. 이사(배치)도 방 단위로 같이 한다. pause 컨테이너는 방 계약자 이름이라, 룸메이트가 바뀌어도 방(네트워크)은 그대로다. 파드를 직접 만드는 건 방을 혼자 계약한 것이라, 건물이 무너지면 누가 새 방을 구해 주지 않는다. 그 일은 다음에 볼 디플로이먼트가 한다.

## 헷갈렸던 것들

- 파드 phase는 다섯 개뿐이다. CrashLoopBackOff는 phase가 아니라 컨테이너 대기 사유다.
- 같은 파드의 컨테이너는 포트 공간을 같이 써서, 둘 다 80을 열 수 없다.
- 컨테이너가 둘 이상이면 logs, exec에 -c로 컨테이너를 고른다.
- command는 ENTRYPOINT를, args는 CMD를 덮어쓴다. 이름이 반대처럼 느껴져서 자꾸 헷갈렸다.
- kubectl run은 파드 하나를 만든다. 직접 만든 파드는 지워져도 다시 생기지 않는다.
- 실행 중인 파드의 대부분 필드는 바꿀 수 없다. 이미지 정도만 바뀌고, 나머지는 지우고 다시 만든다.

## 용어 정리

| 용어 | 뜻 |
|---|---|
| 파드 | 네트워크와 볼륨을 공유하는 컨테이너 묶음. 배포의 최소 단위 |
| 사이드카 | 메인 컨테이너를 돕기 위해 같은 파드에 넣는 보조 컨테이너 |
| pause 컨테이너 | 파드의 네트워크 namespace를 붙들고 있는 작은 컨테이너 |
| phase | 파드 생명주기의 큰 단계(Pending, Running, Succeeded, Failed, Unknown) |
| restartPolicy | 컨테이너가 끝났을 때 다시 시작할지 정하는 정책(Always, OnFailure, Never) |
| emptyDir | 파드가 살아 있는 동안만 있는 빈 디렉터리 볼륨 |

## 참고 자료

- Kubernetes 문서, 파드: <https://kubernetes.io/docs/concepts/workloads/pods/>
- Kubernetes 문서, 파드 생명주기: <https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/>
- Kubernetes 문서, 컨테이너 명령과 인수 정의: <https://kubernetes.io/docs/tasks/inject-data-application/define-command-argument-container/>
- Kubernetes 문서, 디버깅: 파드 상태 확인: <https://kubernetes.io/docs/tasks/debug/debug-application/debug-pods/>

---
title: '[KCNA] 컨테이너화: 이미지와 레이어, OCI와 CRI, 런타임, 파드 안의 컨테이너들'
date: '2026-08-19T21:30:00+09:00'
categories:
- KCNA
tags:
- kubernetes
- kcna
- container
- image
- dockerfile
- oci
- cri
- containerd
- cri-o
- runc
- runtimeclass
- sidecar
- init-container
- Kubernetes Fundamentals
series:
- KCNA
series_order: 5
---

Containerization은 예전 범위의 Containers와 Runtime 항목을 합친 것으로 봤다. 컨테이너가 커널 기능으로 격리한 프로세스라는 건 쿠버네티스 기초 때 정리했으니, 이번에는 객관식에 자주 나오는 이름들이 어느 층에 있는지를 잡는 데 집중했다. OCI, CRI, containerd, runc, dockershim이 서로 무슨 관계인지가 계속 헷갈렸다.

## 요약

- 컨테이너는 리눅스 커널의 네임스페이스(보이는 범위 격리)와 cgroup(자원 제한)으로 묶은 프로세스다. VM과 달리 호스트 커널을 같이 쓴다.
- 이미지는 읽기 전용 레이어를 쌓은 것이다. 태그는 다른 이미지를 가리키도록 바뀔 수 있고, 다이제스트(`sha256:...`)는 내용에서 계산되어 바뀌지 않는다.
- OCI는 이미지 형식(image-spec), 실행 방식(runtime-spec), 레지스트리 배포 방식(distribution-spec) 세 가지 표준을 만든다.
- kubelet은 CRI로 containerd나 CRI-O와 이야기하고, 이들이 runc 같은 OCI 런타임으로 컨테이너를 만든다. 더 강한 격리가 필요하면 RuntimeClass로 gVisor나 Kata Containers를 고른다.
- v1.24에서 빠진 건 dockershim(Docker Engine을 런타임으로 쓰게 해 주던 어댑터)이다. Docker로 만든 이미지는 OCI 이미지라서 그대로 돈다.
- 파드 안에는 앱 컨테이너, 순서대로 끝까지 도는 init 컨테이너, 앱과 같이 도는 사이드카(v1.33 stable), 디버깅용 임시 컨테이너가 있을 수 있다.

## 1. 컨테이너와 VM

| | VM | 컨테이너 |
|---|---|---|
| 격리 단위 | 하이퍼바이저 위의 게스트 OS 전체 | 호스트 커널 위의 프로세스 |
| 커널 | VM마다 따로 | 호스트와 같이 쓴다 |
| 시작 시간, 크기 | 수십 초, GB 단위 | 보통 1초 안팎, MB 단위 |
| 격리 강도 | 강하다 | 커널을 같이 써서 상대적으로 약하다 |

컨테이너를 만드는 커널 기능은 두 가지다. 네임스페이스는 프로세스가 볼 수 있는 범위를 나눈다(pid, net, mnt, uts, ipc, user, cgroup). cgroup은 쓸 수 있는 양을 제한한다(CPU, 메모리, 디스크 I/O, 프로세스 수). 쿠버네티스의 requests와 limits는 결국 cgroup 값으로 바뀐다. 최근 쿠버네티스는 cgroup v2를 기준으로 하고, cgroup v1 지원은 빠지는 중이다.

커널을 같이 쓰니 리눅스 컨테이너는 리눅스 노드에서, 윈도우 컨테이너는 윈도우 노드에서 돈다.

## 2. 이미지

이미지 이름은 `[레지스트리/][경로/]저장소[:태그][@다이제스트]` 모양이다. 레지스트리를 안 적으면 Docker Hub(`docker.io`), 태그를 안 적으면 `latest`가 붙는다. `nginx`는 `docker.io/library/nginx:latest`다.

| 쓰는 방식 | 예 | 특징 |
|---|---|---|
| 태그 | `nginx:1.29` | 사람이 읽기 쉽다. 같은 태그가 나중에 다른 이미지를 가리킬 수 있다 |
| 다이제스트 | `nginx@sha256:...` | 내용의 해시라 늘 같은 이미지다. 재현성과 공급망 보안에 좋다 |

`imagePullPolicy`를 안 적으면 기본값이 태그에 따라 정해진다. 태그가 `latest`이거나 없으면 Always, 그 밖의 태그나 다이제스트면 IfNotPresent다. 비공개 레지스트리는 `imagePullSecrets`에 인증 정보를 담은 Secret을 넣는다.

컨테이너가 실행되면 이미지 레이어 위에 쓰기 가능한 레이어가 하나 생긴다. 컨테이너가 다시 시작되면 이 레이어는 사라진다. 남겨야 하는 데이터는 볼륨에 쓴다.

이미지를 작게, 안전하게 만드는 습관은 이렇다.

```dockerfile
# 빌드 단계: 컴파일러와 소스는 여기까지만
FROM golang:1.25 AS build
WORKDIR /src
COPY . .
RUN CGO_ENABLED=0 go build -o /app ./cmd/server

# 실행 단계: 바이너리만 작은 이미지로 옮긴다
FROM gcr.io/distroless/static-debian12
COPY --from=build /app /app
USER 65532:65532          # root가 아닌 사용자
ENTRYPOINT ["/app"]
```

- 멀티 스테이지 빌드로 빌드 도구를 최종 이미지에서 뺀다.
- distroless, alpine처럼 작은 베이스 이미지를 쓴다. 들어 있는 게 적을수록 취약점도 적다.
- root가 아닌 사용자로 실행한다.
- 비밀번호나 키를 이미지에 넣지 않는다. 레이어에 그대로 남는다.
- 컨테이너 하나에 프로세스 하나를 둔다.

이미지를 만드는 도구는 Docker(BuildKit), Buildah, Podman 등이 있다. 결과물은 모두 OCI 이미지다.

## 3. 표준과 런타임의 층

{{< mermaid >}}
flowchart TB
  K["kubelet"] -->|"CRI (gRPC)"| H["고수준 런타임<br>containerd, CRI-O<br>이미지 받기, 컨테이너 관리"]
  H -->|"OCI runtime-spec"| L["저수준 런타임<br>runc, crun<br>네임스페이스, cgroup 설정"]
  H -.->|"RuntimeClass로 고르면"| S["샌드박스 런타임<br>gVisor(runsc), Kata Containers"]
  L --> C["컨테이너 프로세스"]
  S --> C
  R[("레지스트리")] -->|"OCI distribution-spec<br>OCI image-spec 이미지"| H
{{< /mermaid >}}

| 이름 | 무엇인가 |
|---|---|
| OCI | Open Container Initiative. 이미지, 런타임, 배포 표준을 만드는 Linux Foundation 산하 프로젝트 |
| CRI | Container Runtime Interface. kubelet이 런타임에 '이 파드의 컨테이너를 띄워라'라고 말하는 쿠버네티스 쪽 인터페이스 |
| containerd | CRI를 구현한 고수준 런타임. CNCF graduated. Docker Engine도 안에서 containerd를 쓴다 |
| CRI-O | 쿠버네티스 전용으로 만든 CRI 런타임. CNCF graduated |
| runc | OCI runtime-spec의 참조 구현. 실제로 네임스페이스와 cgroup을 설정해 프로세스를 띄운다 |
| gVisor | 사용자 공간에서 커널 호출을 가로채는 샌드박스 런타임 |
| Kata Containers | 컨테이너마다 가벼운 VM을 띄워 커널까지 분리하는 런타임 |
| dockershim | kubelet이 Docker Engine을 런타임처럼 쓰게 해 주던 어댑터. v1.24에서 제거 |

dockershim이 빠졌다고 Docker 이미지를 못 쓰는 게 아니다. 영향을 받은 건 노드의 Docker 소켓(`/var/run/docker.sock`)에 직접 붙던 도구들이다. 쿠버네티스에는 같은 모양의 플러그인 인터페이스가 세 개 있다. 런타임은 CRI, 네트워크는 CNI, 스토리지는 CSI다.

샌드박스 런타임은 RuntimeClass로 고른다.

```yaml
apiVersion: node.k8s.io/v1
kind: RuntimeClass
metadata:
  name: gvisor
handler: runsc          # 노드의 런타임 설정에 등록된 핸들러 이름
```

파드에는 `spec.runtimeClassName: gvisor`를 적는다.

## 4. 파드 안의 컨테이너들

| 종류 | 언제 돈다 | 쓰임 |
|---|---|---|
| init 컨테이너 | 앱 컨테이너보다 먼저, 하나씩 순서대로, 끝까지 | 설정 파일 만들기, 의존 서비스 기다리기 |
| 사이드카 | initContainers 안에 `restartPolicy: Always`로 적는다. 먼저 뜨고 앱과 같이 돌다가 앱보다 늦게 끝난다 | 로그 전송, 프록시. v1.33에서 stable |
| 앱 컨테이너 | init 컨테이너가 다 끝나고 사이드카가 뜬 뒤 | 본래 할 일 |
| 임시 컨테이너 | 실행 중인 파드에 `kubectl debug`로 붙인다 | 디버깅. 재시작되지 않고 포트도 못 연다 |

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: web
spec:
  initContainers:
  - name: wait-db                 # 끝나야 다음으로 넘어간다
    image: busybox:1.37
    command: ["sh", "-c", "until nslookup db; do sleep 2; done"]
  - name: log-shipper             # restartPolicy: Always면 사이드카
    image: fluent/fluent-bit:4.0
    restartPolicy: Always
    volumeMounts:
    - name: logs
      mountPath: /var/log/app
  containers:
  - name: app
    image: nginx:1.29
    volumeMounts:
    - name: logs
      mountPath: /var/log/nginx
  volumes:
  - name: logs
    emptyDir: {}
```

한 파드의 컨테이너들은 같은 네트워크 네임스페이스를 써서 서로 `localhost`로 통신하고, 볼륨을 같이 마운트할 수 있다. 여러 컨테이너를 한 파드에 넣는 전형적인 패턴은 세 가지로 불린다. 앱을 보조하는 사이드카, 밖으로 나가는 연결을 대신 맡는 앰배서더, 출력 형식을 바꿔 주는 어댑터다.

컨테이너가 끝날 때는 먼저 SIGTERM을 받고, `terminationGracePeriodSeconds`(기본 30초) 안에 안 끝나면 SIGKILL을 받는다. `preStop` 훅은 SIGTERM 전에 돈다.

> **쉬운 설명**
>
> 이미지는 밀키트, 레이어는 밀키트 안의 재료 봉지들, 컨테이너는 그걸 뜯어 조리 중인 요리다. OCI는 밀키트 포장 규격이라 어느 회사가 만든 밀키트든 어느 주방에서나 쓸 수 있다. kubelet은 주방장이고, CRI는 주방장이 조리 담당(containerd)에게 넘기는 표준 주문서다. 조리 담당은 가스레인지(runc)로 실제로 불을 켠다. 예전에는 주방장이 특정 회사 제품(Docker Engine)과 말하려고 통역사(dockershim)를 따로 뒀는데, 이제 통역사만 내보냈다. 밀키트는 그대로 쓴다.

## 헷갈렸던 것들

- Docker 이미지는 계속 쓸 수 있다. 빠진 건 dockershim이다.
- `latest`는 이름일 뿐 최신이라는 보장이 없다. 다이제스트만 내용을 고정한다.
- 컨테이너 안에 쓴 파일은 컨테이너가 다시 시작되면 사라진다.
- CRI는 쿠버네티스의 인터페이스, OCI는 컨테이너 업계 표준이다.
- containerd와 CRI-O는 고수준, runc는 저수준 런타임이다.
- 사이드카는 별도 필드가 아니라 initContainers에 `restartPolicy: Always`를 적은 것이다.
- 컨테이너는 호스트 커널을 같이 쓴다. 그래서 VM보다 가볍지만 격리는 약하다.

## 용어 정리

| 용어 | 뜻 |
|---|---|
| 네임스페이스(커널) | 프로세스가 볼 수 있는 자원 범위를 나누는 리눅스 기능. 쿠버네티스 네임스페이스와 다르다 |
| cgroup | 프로세스 묶음이 쓸 수 있는 CPU, 메모리 등을 제한하는 리눅스 기능 |
| 레이어 | 이미지를 이루는 읽기 전용 파일 시스템 변경분 |
| 다이제스트 | 이미지 내용의 sha256 해시. 같은 다이제스트는 늘 같은 이미지다 |
| OCI | 컨테이너 이미지, 런타임, 배포 표준을 만드는 프로젝트 |
| CRI | kubelet과 컨테이너 런타임 사이의 인터페이스 |
| RuntimeClass | 파드가 쓸 런타임 핸들러를 고르는 오브젝트 |
| 사이드카 컨테이너 | 앱 컨테이너와 같은 파드에서 같이 도는 보조 컨테이너 |

## 복습 문제

**1.** Which Linux kernel feature limits how much CPU and memory a container can use?

- A. Namespaces
- B. chroot
- C. cgroups
- D. SELinux

**2.** Which interface does the kubelet use to talk to container runtimes such as containerd and CRI-O?

- A. CRI
- B. CNI
- C. CSI
- D. The OCI distribution specification

**3.** Kubernetes removed dockershim in v1.24. What does this mean for container images that were built with Docker?

- A. They must be rebuilt with Buildah.
- B. They can run only on nodes that use Docker Engine.
- C. They must be converted to virtual machine images.
- D. They still run, because they are OCI-compliant images.

**4.** Which image reference always points to the same image content?

- A. `nginx:latest`
- B. `nginx@sha256:<digest>`
- C. `nginx:1.29`
- D. `nginx:stable`

**5.** A workload needs stronger isolation than a regular runc container and should run with gVisor. Which Kubernetes object selects that runtime for a Pod?

- A. PriorityClass
- B. StorageClass
- C. RuntimeClass
- D. IngressClass

**6.** Which type of container must run to completion before the app containers start?

- A. A regular init container
- B. An ephemeral container
- C. A sidecar container
- D. The main application container

**7.** Which organization maintains the image, runtime, and distribution specifications for containers?

- A. The CNCF Technical Oversight Committee
- B. Kubernetes SIG Node
- C. Docker, Inc.
- D. The Open Container Initiative

## 답과 풀이

1. **C** cgroup이 자원을 제한하고, 네임스페이스는 보이는 범위를 격리한다.
2. **A** CRI다. CNI는 네트워크, CSI는 스토리지 인터페이스다.
3. **D** Docker가 만든 이미지도 OCI 이미지라 containerd, CRI-O에서 그대로 돈다.
4. **B** 다이제스트는 내용의 해시다. 태그는 다른 이미지를 가리키도록 바뀔 수 있다.
5. **C** RuntimeClass의 handler가 노드에 등록된 런타임(runsc 등)을 가리킨다.
6. **A** 일반 init 컨테이너는 하나씩 끝까지 실행된다. 사이드카(`restartPolicy: Always`)는 끝나지 않고 앱과 같이 돈다.
7. **D** OCI가 image-spec, runtime-spec, distribution-spec을 관리한다.

## 참고 자료

- Kubernetes 문서, 컨테이너: <https://kubernetes.io/docs/concepts/containers/>
- Kubernetes 문서, 이미지: <https://kubernetes.io/docs/concepts/containers/images/>
- Kubernetes 문서, 컨테이너 런타임: <https://kubernetes.io/docs/setup/production-environment/container-runtimes/>
- Kubernetes 문서, CRI: <https://kubernetes.io/docs/concepts/architecture/cri/>
- Kubernetes 문서, RuntimeClass: <https://kubernetes.io/docs/concepts/containers/runtime-class/>
- Kubernetes 블로그, dockershim 제거 FAQ: <https://kubernetes.io/blog/2022/02/17/dockershim-faq/>
- Kubernetes 문서, init 컨테이너: <https://kubernetes.io/docs/concepts/workloads/pods/init-containers/>
- Kubernetes 문서, 사이드카 컨테이너: <https://kubernetes.io/docs/concepts/workloads/pods/sidecar-containers/>
- Kubernetes 문서, 파드 수명 주기: <https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/>
- Open Container Initiative: <https://opencontainers.org/>


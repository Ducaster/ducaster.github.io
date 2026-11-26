---
title: '[NCP-AIO] 배경 지식 3: GPU 소프트웨어 스택과 관리 도구, 드라이버부터 GPU Operator·DCGM까지'
date: '2026-11-24T21:20:00+09:00'
categories:
- NCP-AIO
tags:
- nvidia
- ncp-aio
- cuda
- container-toolkit
- ngc
- gpu-operator
- dcgm
- nvidia-smi
- nvsm
- docker
- 배경 지식
series:
- NCP-AIO
series_order: 4
---

GPU 서버에서 컨테이너 하나가 GPU를 쓰기까지 거치는 소프트웨어가 생각보다 많다. 호스트의 드라이버, 컨테이너 런타임에 GPU를 끼워 넣는 Container Toolkit, 이미지를 받는 NGC, 쿠버네티스에서 이걸 다 깔아 주는 GPU Operator가 있고, 상태를 보는 도구도 nvidia-smi, DCGM, NVSM 세 가지다. 시험의 NGC·VMI 컨테이너 배포, Docker 문제 해결, DCGM·NVSM·nvidia-smi로 문제 찾기가 여기에 걸린다.

## 요약

- 드라이버는 호스트에 깔고, CUDA 런타임과 라이브러리는 컨테이너 이미지 안에 넣는다. 컨테이너가 요구하는 CUDA 버전을 호스트 드라이버가 지원해야 한다.
- NVIDIA Container Toolkit이 컨테이너를 시작할 때 GPU 장치와 드라이버 라이브러리를 넣어 준다. nvidia-ctk runtime configure로 Docker, containerd, CRI-O를 설정한다.
- NGC 레지스트리(nvcr.io)에 API 키로 로그인할 때 사용자 이름은 문자 그대로 $oauthtoken이다.
- GPU Operator는 드라이버, Container Toolkit, 디바이스 플러그인, GPU Feature Discovery, DCGM Exporter, MIG Manager를 쿠버네티스 노드에 깔고 관리한다.
- nvidia-smi는 GPU 하나하나를 보는 도구, DCGM은 클러스터 단위 감시와 진단(dcgmi diag 1~4단계), NVSM은 DGX 시스템 전체의 상태 점검 도구다.

## 1. 층으로 보기

{{< mermaid >}}
flowchart TB
  K["쿠버네티스<br>디바이스 플러그인, GPU Operator"] --> R["컨테이너 런타임<br>Docker, containerd, CRI-O"]
  R --> T["NVIDIA Container Toolkit<br>GPU 장치와 드라이버 라이브러리를 컨테이너에 주입"]
  T --> D["호스트 드라이버<br>커널 모듈, libcuda, NVML"]
  D --> G["GPU"]
  I["컨테이너 이미지<br>CUDA 런타임, cuDNN, 프레임워크"] -.->|"실행 시"| R
{{< /mermaid >}}

CUDA는 두 군데에 나뉘어 있다. 커널 모듈과 libcuda, NVML 같은 드라이버 쪽은 호스트에 있고, CUDA 런타임과 cuDNN 같은 라이브러리는 이미지 안에 있다. 그래서 호스트에는 CUDA Toolkit을 깔 필요가 없고 드라이버만 있으면 된다. 대신 이미지가 요구하는 CUDA 버전을 호스트 드라이버가 지원해야 한다. nvidia-smi 오른쪽 위의 CUDA Version은 그 드라이버가 지원하는 가장 높은 CUDA 버전이다. 새 이미지만 CUDA 초기화에 실패하면 이 숫자부터 본다.

## 2. NVIDIA Container Toolkit

Docker는 원래 GPU를 모른다. Container Toolkit을 깔고 런타임 설정을 바꿔야 --gpus 옵션이 동작한다.

```bash
sudo nvidia-ctk runtime configure --runtime=docker     # /etc/docker/daemon.json을 고친다
sudo systemctl restart docker
sudo docker run --rm --runtime=nvidia --gpus all ubuntu nvidia-smi

sudo nvidia-ctk runtime configure --runtime=containerd # /etc/containerd/conf.d/99-nvidia.toml 생성
sudo systemctl restart containerd
```

Docker 쪽에서 자주 보는 문제를 정리했다.

| 증상 | 원인과 확인할 것 |
|---|---|
| could not select device driver "" with capabilities: [[gpu]] | Container Toolkit이 없거나 Docker에 런타임이 설정되지 않았다. daemon.json과 docker 재시작을 확인한다 |
| 컨테이너 안에서 Failed to initialize NVML: Unknown Error | systemd가 cgroup을 관리하는 시스템에서 systemctl daemon-reload 같은 일로 컨테이너가 GPU 접근을 잃었다. 컨테이너를 다시 만들면 돌아온다. 근본 대책은 CDI로 장치를 주입하거나 장치 노드를 명시하는 것 |
| 이미지 받기에서 401 Unauthorized | nvcr.io 로그인 정보나 API 키 문제 |
| docker 명령 자체가 안 됨 | systemctl status docker, journalctl -u docker로 데몬 상태를 본다. daemon.json 문법 오류도 흔하다 |
| 컨테이너가 바로 종료됨 | docker logs <컨테이너>, docker inspect로 종료 코드와 마지막 출력을 본다 |

## 3. NGC와 클라우드 VMI

NGC는 NVIDIA의 카탈로그다. GPU에 맞춰 빌드한 PyTorch, TensorFlow 같은 컨테이너와 모델, Helm 차트를 올려 둔다. 컨테이너 레지스트리 주소는 nvcr.io다.

```bash
docker login nvcr.io --username '$oauthtoken'    # 비밀번호 자리에 NGC API 키
docker pull nvcr.io/nvidia/pytorch:<태그>
ngc config set                                   # NGC CLI에 API 키, 조직, 팀 설정
```

$oauthtoken은 변수가 아니라 'API 키로 인증한다'는 뜻의 정해진 이름이다. 셸이 변수로 풀지 않게 작은따옴표로 감싼다. 조직 단위의 비공개 레지스트리도 같은 방식으로 쓴다.

클라우드 VMI(Virtual Machine Image)는 클라우드 마켓플레이스에 올라온 GPU용 VM 이미지다. 드라이버, Docker, Container Toolkit이 미리 들어 있어서 GPU 인스턴스를 띄우면 바로 NGC 컨테이너를 받아 돌릴 수 있다. AWS SAA 때 본 AMI와 같은 개념이다.

## 4. GPU Operator

쿠버네티스 노드마다 드라이버, Container Toolkit, 디바이스 플러그인을 손으로 맞추는 대신 GPU Operator가 맡는다.

| 구성 요소 | 하는 일 |
|---|---|
| Driver | 드라이버를 컨테이너로 설치한다. 노드에 이미 깔려 있으면 끌 수 있다 |
| Container Toolkit | 노드의 containerd, CRI-O에 NVIDIA 런타임을 설정한다 |
| Device Plugin | GPU를 nvidia.com/gpu 같은 자원으로 kubelet에 알린다 |
| GPU Feature Discovery | GPU 모델, 메모리, MIG 가능 여부를 노드 라벨로 붙인다 |
| DCGM Exporter | DCGM 지표를 Prometheus 형식으로 내보낸다 |
| MIG Manager | nvidia.com/mig.config 라벨대로 MIG를 구성한다 |
| Node Feature Discovery | 노드 하드웨어를 찾아 라벨로 붙인다. GPU 노드를 골라내는 데 쓴다 |

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: gpu-test
spec:
  restartPolicy: Never
  containers:
  - name: cuda
    image: nvcr.io/nvidia/cuda:<태그>
    command: ["nvidia-smi"]
    resources:
      limits:
        nvidia.com/gpu: 1          # 확장 자원은 limits에 적는다. 소수로는 못 준다
```

쿠버네티스 문서에 따르면 nvidia.com/gpu 같은 확장 자원은 정수로만 요청하고, requests를 적는다면 limits와 같아야 한다. GPU 하나를 쪼개 쓰려면 1편의 MIG나 시분할을 써야 한다.

## 5. 관리 도구 세 가지

| 도구 | 범위 | 주로 쓰는 때 |
|---|---|---|
| nvidia-smi | GPU 하나하나 | 지금 상태, 프로세스, 메모리, 온도, 토폴로지, MIG 설정 |
| DCGM | 노드와 클러스터 | 지속 감시, 상태 검사(health), 진단(diag), 지표 수집 |
| NVSM | DGX 시스템 전체 | GPU뿐 아니라 팬, 전원, 드라이브, PCIe 링크까지 시스템 상태 점검, 지원 요청용 로그 |

### nvidia-smi

```bash
nvidia-smi                                              # 요약
nvidia-smi -q -i 0                                      # GPU 0의 상세 정보(ECC, 클럭, Fabric 등)
nvidia-smi --query-gpu=index,name,memory.used,temperature.gpu --format=csv
nvidia-smi topo -m                                      # 1편의 연결 행렬
sudo dmesg | grep -i xid                                # 드라이버가 남긴 GPU 오류(Xid) 메시지
```

Xid는 NVIDIA 드라이버가 커널 로그에 남기는 GPU 오류 번호다. GPU가 갑자기 사라지거나 작업이 죽으면 커널 로그의 Xid부터 찾는다.

### DCGM

DCGM(Data Center GPU Manager)은 nv-hostengine이라는 데몬(nvidia-dcgm 서비스)이 GPU를 계속 지켜보고, dcgmi CLI나 API로 그 정보를 꺼내 쓴다.

```bash
sudo systemctl --now enable nvidia-dcgm
dcgmi discovery -l          # DCGM이 보는 GPU 목록
dcgmi diag -r 1             # 빠른 진단
dcgmi diag -r 3             # 긴 하드웨어 진단
```

| 진단 단계 | 이름 | 문서가 권하는 쓰임 |
|---|---|---|
| -r 1 | Quick | 작업 전 준비 상태 확인 |
| -r 2 | Medium | 작업이 실패한 뒤 마무리 점검(epilogue) |
| -r 3 | Long | 관리자가 하는 사후 분석 |
| -r 4 | Extended | 관리자가 하는 더 긴 사후 분석 |

Slurm에서 작업 전후에 돌리는 스크립트(prolog, epilogue)에 1, 2단계를 넣고, 고장이 의심되는 노드를 빼서 3, 4단계를 돌리는 식으로 이해했다. 쿠버네티스에서는 GPU Operator의 DCGM Exporter가 같은 지표를 Prometheus로 보낸다.

### NVSM

NVSM(NVIDIA System Management)은 DGX 같은 NVIDIA 서버용 시스템 관리 도구다. DGX OS에 들어 있고 nvsm-core 같은 systemd 서비스로 돈다. GPU만 보는 DCGM과 달리 PCIe 링크 폭이 낮게 잡힌 것처럼 놓치기 쉬운 시스템 문제도 잡는다고 한다.

```bash
sudo nvsm show health       # 시스템 상태 요약
sudo nvsm show gpus
sudo nvsm dump health       # /tmp/nvsm-health-<호스트>-<시각>.tar.xz로 진단 묶음 생성
```

NVIDIA 지원에 문제를 올릴 때 nvsm dump health로 만든 묶음을 첨부하라고 안내한다.

> **쉬운 설명**
>
> GPU를 쓰는 컨테이너는 렌터카와 같다. 드라이버는 도로와 신호등이라 지역(호스트)에 깔려 있고, CUDA 라이브러리는 차(이미지) 안의 엔진이다. 새 차가 최신 도로 규격을 요구하는데 지역 도로가 옛날 규격이면 차가 못 달린다. Container Toolkit은 차를 도로에 올려 주는 진입로, NGC는 검증된 차만 파는 공식 대리점이다. 점검 도구는 세 단계다. nvidia-smi는 계기판, DCGM은 차량 관제 센터, NVSM은 정비소의 전체 점검이다.

## 용어 정리

| 용어 | 뜻 |
|---|---|
| NVML | 드라이버가 제공하는 GPU 관리 라이브러리. nvidia-smi, DCGM이 이걸 쓴다 |
| NVIDIA Container Toolkit | 컨테이너 런타임에 GPU 장치와 드라이버 라이브러리를 넣어 주는 도구. nvidia-ctk |
| CDI | Container Device Interface. 컨테이너에 장치를 넣는 방법을 표준 형식으로 적는 규격 |
| NGC | NVIDIA의 컨테이너, 모델, 차트 카탈로그. 레지스트리는 nvcr.io |
| VMI | 클라우드용 GPU 최적화 VM 이미지 |
| GPU Operator | 쿠버네티스 노드에 GPU 소프트웨어를 깔고 관리하는 오퍼레이터 |
| DCGM | 데이터센터 GPU 감시, 진단 도구. 데몬은 nv-hostengine, CLI는 dcgmi |
| NVSM | DGX 같은 NVIDIA 서버의 시스템 관리 도구 |
| Xid | 드라이버가 커널 로그에 남기는 GPU 오류 번호 |

## 복습 문제

**1.** On a new host with the NVIDIA driver and Docker installed, docker run --gpus all fails with: could not select device driver "" with capabilities: [[gpu]]. What is missing?

- A. A MIG configuration applied to the host GPUs
- B. An NGC API key stored in the Docker configuration
- C. A full CUDA toolkit installed on the host OS
- D. The NVIDIA Container Toolkit for Docker

**2.** What username is used with docker login nvcr.io when authenticating with an NGC API key?

- A. The name of the NGC organization
- B. The email address of the NGC account
- C. Exactly the literal string $oauthtoken
- D. The word nvidia followed by the team name

**3.** Which dcgmi diag run level is intended as a quick readiness check before a job starts?

- A. -r 3
- B. -r 1
- C. -r 4
- D. -r 2

**4.** A container built with a newer CUDA version fails to initialize CUDA, while older images run fine. nvidia-smi on the host shows a lower CUDA Version than the image needs. What should be done?

- A. Upgrade the host driver to one that supports that CUDA version.
- B. Install the matching CUDA toolkit on the host operating system.
- C. Enable MIG mode so the newer CUDA runtime is able to load.
- D. Restart nv-hostengine so it registers the new CUDA version.

**5.** NVIDIA support asks for a complete health snapshot of a DGX system. Which command produces it?

- A. dcgmi discovery -l
- B. nvidia-smi topo -m
- C. sudo nvsm dump health
- D. nvidia-ctk runtime configure

## 답과 풀이

1. **D** Docker가 GPU를 넘기려면 Container Toolkit을 깔고 nvidia-ctk runtime configure로 런타임을 설정해야 한다. 호스트에 CUDA Toolkit은 필요 없다.
2. **C** 사용자 이름은 $oauthtoken 그대로이고 비밀번호 자리에 API 키를 넣는다.
3. **B** 1단계는 준비 상태 확인, 2단계는 작업 실패 뒤 점검, 3, 4단계는 관리자의 사후 분석용이다.
4. **A** nvidia-smi의 CUDA Version은 드라이버가 지원하는 최고 버전이다. 이미지의 CUDA 런타임은 이미지 안에 있으니 호스트 드라이버를 올려야 한다.
5. **C** nvsm dump health가 진단 묶음을 만든다. NVIDIA 지원 요청에 이 파일을 첨부한다.

## 참고 자료

- NVIDIA, Container Toolkit 설치 가이드: <https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html>
- NVIDIA, Container Toolkit 문제 해결: <https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/troubleshooting.html>
- NVIDIA, NGC User Guide: <https://docs.nvidia.com/ngc/latest/ngc-user-guide.html>
- NVIDIA, GPU Operator: <https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/latest/overview.html>
- NVIDIA, DCGM 시작하기: <https://docs.nvidia.com/datacenter/dcgm/latest/user-guide/getting-started.html>
- NVIDIA, DCGM 진단: <https://docs.nvidia.com/datacenter/dcgm/latest/user-guide/dcgm-diagnostics.html>
- NVIDIA, NVSM User Guide: <https://docs.nvidia.com/datacenter/nvsm/nvsm-user-guide/latest/index.html>
- NVIDIA, nvidia-smi 문서: <https://docs.nvidia.com/deploy/nvidia-smi/index.html>


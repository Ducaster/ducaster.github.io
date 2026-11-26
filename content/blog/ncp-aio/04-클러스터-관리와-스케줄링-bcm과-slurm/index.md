---
title: '[NCP-AIO] 배경 지식 4: 클러스터 관리와 스케줄링, BCM·Slurm·Run:ai·Fleet Command'
date: '2026-11-25T21:00:00+09:00'
categories:
- NCP-AIO
tags:
- nvidia
- ncp-aio
- bcm
- base-command-manager
- slurm
- kubernetes
- run-ai
- fleet-command
- cmsh
- 배경 지식
series:
- NCP-AIO
series_order: 5
---

쿠버네티스만 써 온 입장에서 NCP-AIO가 제일 낯선 부분은 클러스터를 다루는 도구들이었다. 노드에 OS를 깔고 이미지를 맞추는 BCM, HPC에서 오래 쓰인 작업 스케줄러 Slurm, 쿠버네티스 위에서 GPU를 팀별로 나눠 주는 Run:ai, 엣지 장비를 관리하는 Fleet Command가 있다. 실습 세 문제(BCM의 Slurm으로 클러스터 문제 해결, 쿠버네티스로 워크로드 실행, BCM으로 노드 추가) 중 둘이 BCM이라 가장 공을 들였다. BCM 내용은 Base Command Manager 11 관리자 매뉴얼과 설치 매뉴얼을 기준으로 했다.

## 요약

- BCM(Base Command Manager)은 예전 이름이 Bright Cluster Manager인 NVIDIA의 클러스터 관리 도구다. 헤드 노드 하나가 나머지 노드를 네트워크 부팅으로 프로비저닝하고, Slurm과 쿠버네티스도 설치해 준다.
- 노드는 헤드 노드에 있는 소프트웨어 이미지(기본 default-image)를 받아서 부팅한다. 설정은 노드 카테고리로 묶어서 한꺼번에 준다. CLI는 cmsh, GUI는 Base View다.
- Slurm은 slurmctld(컨트롤러), slurmd(노드마다), slurmdbd(계정 DB)로 이뤄진다. GPU는 GRES로 관리하고, 설정한 GPU 수와 노드가 찾은 수가 다르면 노드가 drain된다.
- Run:ai는 쿠버네티스 위에서 GPU를 프로젝트별 할당량으로 나눠 주고, 놀고 있는 GPU는 할당량을 넘어 빌려 쓰게 하는 플랫폼이다.
- Fleet Command는 엣지 장비에 AI 애플리케이션을 배포하고 관리하는 NVIDIA의 관리형 서비스다.

## 1. BCM

### 기본 개념

| 개념 | 설명 |
|---|---|
| 헤드 노드 | BCM이 설치된 관리 노드. 다른 노드를 프로비저닝하고 상태를 관리한다 |
| 일반 노드(regular node) | 계산을 하는 노드. 헤드 노드에서 이미지를 받아 부팅한다 |
| 소프트웨어 이미지 | 헤드 노드에 있는, 리눅스 파일 시스템 전체가 들어 있는 디렉터리. 기본 이름은 default-image |
| 노드 카테고리 | 같은 설정을 쓰는 노드 묶음. 노드는 항상 카테고리 하나에 속하고 처음엔 default다 |
| CMDaemon | 각 노드에서 도는 BCM 데몬. 설정과 상태를 주고받는다 |
| cmsh, Base View | BCM의 CLI와 웹 GUI |

카테고리와 이미지는 1대1이 아니다. 카테고리 여러 개가 같은 이미지를 쓸 수 있다. 노드는 카테고리 값을 물려받고, 노드에 따로 적은 값이 있으면 그게 이긴다. 쿠버네티스의 노드 라벨과는 다르게, 디스크 구성이나 역할 같은 설정 자체를 카테고리에 둔다.

장치 상태 중 헷갈린 게 DOWN과 CLOSED다. DOWN은 쓰려던 장치가 내려간 것이라 보통 장애이고, CLOSED는 관리자가 일부러 빼 둔 장치라 BCM이 대부분 무시한다.

### 노드가 프로비저닝되는 순서

{{< mermaid >}}
flowchart TB
  subgraph r1["네트워크 부팅"]
    direction LR
    A["노드 전원 켜기<br>BIOS에서 네트워크 부팅"] --> B["헤드 노드에서<br>PXE로 부팅"] --> C["node-installer 실행<br>헤드 노드에 인증서 요청"]
  end
  subgraph r2["node-installer 설치"]
    direction LR
    D["노드 식별<br>MAC, 스위치 포트, 콘솔"] --> E["소프트웨어 이미지를<br>로컬 디스크에 동기화"] --> F["부팅 완료<br>상태 UP"]
  end
  r1 --> r2
{{< /mermaid >}}

노드에 OS가 이미 깔려 있어도 기본 설정이면 헤드 노드의 이미지로 덮어쓴다. node-installer 단계까지 못 가면 커널 모듈이 더 필요한 경우가 많다고 설치 매뉴얼에 적혀 있다.

### 노드 추가하기

실습에 나오는 'BCM으로 노드 추가'를 매뉴얼 예제로 정리했다. cmsh는 모드로 들어가서 객체를 만들고, commit해야 저장된다. 프롬프트의 별표(*)는 아직 저장하지 않은 변경이 있다는 표시다.

```bash
cmsh
[basecm11]% device
[basecm11->device]% add physicalnode node005 10.141.0.5   # 노드 객체 만들기
[basecm11->device*[node005*]]% set category default        # 카테고리 지정
[basecm11->device*[node005*]]% commit                      # 여기서 저장된다
[basecm11->device[node005]]% exit
[basecm11->device]% newnodes                               # 부팅해서 식별을 기다리는 노드(MAC) 목록
[basecm11->device]% newnodes -s -n node005                 # 기다리는 노드에 이름 붙이기
[basecm11->device]% foreach --clone node001 -n node006..node008 ()   # 기존 노드를 복제해 여러 개 추가
[basecm11->device]% power -n node005 on                    # BMC로 전원 켜기
```

노드 객체만 먼저 만들어 두고(MAC 비워 둠), 실제 노드가 부팅해서 node-installer에 들어오면 그때 MAC을 연결하는 방식이 많이 쓰인다. 큰 클러스터에서는 MAC 대신 연결된 스위치 포트로 노드를 식별하는 쪽을 권한다. Base View에도 여러 노드를 한꺼번에 만드는 Node Creation Wizard가 있다.

### Slurm과 쿠버네티스 설치

| 도구 | 하는 일 |
|---|---|
| cm-wlm-setup | Slurm 같은 워크로드 매니저를 설치하고 설정한다. GPU 설정도 여기서 slurm.conf에 넣는다. Slurm에서 컨테이너를 돌리는 Enroot와 Pyxis도 같이 넣을 수 있다 |
| cm-kubernetes-setup | 쿠버네티스를 설치한다. --list-versions로 설치할 수 있는 버전을 본다. 마법사 안에서 NVIDIA GPU Operator도 같이 설치할 수 있다 |

시험 주제의 'BCM으로 NVIDIA 호스트에 쿠버네티스 설치와 초기화'가 cm-kubernetes-setup이다. CKA에서 kubeadm으로 하던 클러스터 구성을 BCM이 대신 하고, 버전이나 로컬 레지스트리 미러 같은 선택지는 마법사에서 고른다.

## 2. Slurm

Slurm은 HPC 클러스터에서 오래 쓰인 작업 스케줄러다. 사용자가 작업을 제출하면 큐에 넣었다가 자원이 나면 노드를 배정해 돌린다.

| 구성 요소 | 위치 | 하는 일 |
|---|---|---|
| slurmctld | 헤드 노드(컨트롤러) | 큐, 스케줄링, 노드 상태 관리 |
| slurmd | 계산 노드마다 | 배정된 작업을 실제로 실행한다 |
| slurmdbd | 보통 헤드 노드 | 작업 기록, 계정 정보를 DB에 저장한다 |

| 명령 | 쓰임 |
|---|---|
| sinfo | 파티션과 노드 상태(idle, alloc, mix, drain, down) |
| sinfo -R | drain, down된 노드와 이유 |
| squeue | 대기 중이거나 실행 중인 작업 |
| sbatch 스크립트.sh | 배치 작업 제출 |
| srun | 바로 실행하거나 작업 안에서 단계 실행 |
| scancel 작업ID | 작업 취소 |
| scontrol show node node001 | 노드 상세 정보(State, Reason, Gres) |
| scontrol update NodeName=node001 State=RESUME | drain된 노드를 다시 쓰기 |

GPU는 GRES(Generic RESource)로 관리한다. slurm.conf에 GresTypes=gpu와 노드별 Gres=gpu:8 같은 값을 적고, 노드의 gres.conf에서 AutoDetect=nvml을 쓰면 NVML로 GPU를 찾아 채운다.

```bash
#!/bin/bash
#SBATCH --job-name=gpu-check
#SBATCH --partition=<파티션>
#SBATCH --nodes=1
#SBATCH --gres=gpu:2          # 노드당 GPU 2개. --gpus=2처럼 작업 전체 개수로도 줄 수 있다
srun nvidia-smi -L
```

Slurm 문서에 적힌 함정 하나가 실습과 바로 이어질 것 같았다. 노드가 찾은 GPU를 slurm.conf가 다 적고 있지 않으면 slurmd가 그 노드를 drain시킨다. GPU를 추가하거나 바꾼 뒤 노드가 drain 상태면 sinfo -R로 이유를 보고, slurm.conf의 Gres 개수를 맞춘 뒤 resume한다.

{{< mermaid >}}
flowchart TB
  A["sinfo에서 노드가 drain, down"] --> B["sinfo -R<br>scontrol show node로 Reason 확인"]
  B --> C{"Reason이<br>gres/gpu 관련인가"}
  C -->|예| D["slurm.conf의 Gres와<br>노드가 찾은 GPU 수 맞추기"]
  C -->|아니오| E["journalctl -u slurmd<br>노드 연결, 디스크, 서비스 확인"]
  D --> F["scontrol update<br>NodeName=... State=RESUME"]
  E --> F
{{< /mermaid >}}

### Slurm과 쿠버네티스 비교

| | Slurm | 쿠버네티스 |
|---|---|---|
| 실행 단위 | 작업(job), 작업 단계(step) | 파드 |
| 제출 | sbatch, srun | kubectl apply |
| 동작 방식 | 큐에 쌓아 두고 자원이 나면 실행, 끝나면 종료 | 원하는 상태를 계속 유지 |
| 노드 묶음 | 파티션 | 노드 라벨, 노드 풀 |
| 노드 빼기 | State=DRAIN | kubectl cordon, drain |
| GPU 요청 | --gres=gpu:N, --gpus | resources.limits의 nvidia.com/gpu |
| 컨테이너 | Enroot, Pyxis로 srun --container-image | 기본 |

1월에 정리한 갱 스케줄링은 쿠버네티스가 Slurm이 원래 잘하던 '여러 노드를 한꺼번에 잡아야 시작하는 작업'을 따라가는 이야기였다는 걸 이번에 알았다.

## 3. Run:ai

Run:ai는 NVIDIA가 인수한, 쿠버네티스 위의 AI 워크로드 관리 플랫폼이다. 여러 팀이 GPU 클러스터 하나를 나눠 쓸 때 쓴다.

| 개념 | 설명 |
|---|---|
| 프로젝트 | 팀이나 과제 단위. 쿠버네티스 네임스페이스와 짝을 이루고 GPU 할당량을 가진다 |
| 부서(department) | 프로젝트 여러 개를 묶은 단위. 할당량을 위에서 나눈다 |
| 할당량 초과(over-quota) | 클러스터에 노는 GPU가 있으면 할당량보다 더 쓸 수 있다. 원래 주인이 필요하면 회수된다 |
| GPU 나눠 쓰기 | GPU 하나를 여러 워크로드가 조각으로 나눠 쓴다 |
| UI와 CLI | 웹 UI와 runai CLI로 워크로드를 제출하고 본다 |

Run:ai on DGX Cloud 문서의 책임 분담 표는 KCSA에서 정리한 공동 책임 모델과 같은 모양이었다. NVIDIA가 클러스터와 구성 요소를 관리하고, 고객은 사용자와 역할, 프로젝트 할당량, 자기 워크로드를 책임진다. 고객은 CRD나 오퍼레이터처럼 클러스터 범위 권한이 필요한 것을 설치할 수 없다. Agent Substrate 글에 나온 KAI Scheduler가 Run:ai의 스케줄러를 오픈소스로 공개한 것이다.

## 4. Fleet Command

Fleet Command는 매장, 공장, 병원처럼 여러 곳에 흩어진 엣지 장비에 AI 애플리케이션을 배포하고 관리하는 NVIDIA의 관리형 플랫폼이다. 클라우드 콘솔에서 새 장비를 프로비저닝하고, 몇 번의 클릭으로 애플리케이션을 배포하고, 원격 콘솔로 장비에 들어간다. 데이터센터 안쪽을 다루는 BCM과 달리 바깥에 흩어진 장비가 대상이다.

## 5. 실습 세 문제와 이어 보기

| 공식 페이지의 실습 | 미리 손에 익혀 둘 것 |
|---|---|
| BCM의 Slurm으로 클러스터 문제 해결 | sinfo -R, scontrol show node, journalctl -u slurmd, Gres 설정, State=RESUME |
| 쿠버네티스로 워크로드 실행 | GPU를 요청하는 파드나 Job 작성, kubectl describe, logs. CKA, CKAD 범위 |
| BCM으로 클러스터에 노드 추가 | cmsh의 device 모드, add physicalnode, 카테고리 지정, commit, newnodes, 전원 켜기 |

> **쉬운 설명**
>
> BCM은 학교 컴퓨터실 관리 프로그램과 같다. 선생님 PC(헤드 노드)에 표준 설치본(소프트웨어 이미지)을 두고, 학생 PC(일반 노드)를 켜면 네트워크로 그 설치본을 받아 똑같은 상태로 부팅한다. 반마다 설정이 다르면 반(카테고리)별로 묶어서 한 번에 바꾼다. Slurm은 컴퓨터실 예약 장부다. 학생이 '두 시간, GPU 두 대'라고 적어 내면 자리가 날 때 배정하고 시간이 끝나면 비운다. Run:ai는 학과별로 컴퓨터 대수를 정해 두고, 다른 학과 자리가 비어 있으면 잠깐 빌려 쓰게 해 주는 조교다. 주인이 오면 빌린 자리는 돌려줘야 한다.

## 용어 정리

| 용어 | 뜻 |
|---|---|
| BCM | Base Command Manager. NVIDIA의 클러스터 관리 도구. 예전 이름 Bright Cluster Manager |
| 헤드 노드 | BCM이 설치돼 다른 노드를 관리하는 노드 |
| 소프트웨어 이미지 | 노드에 내려 줄 리눅스 파일 시스템 전체가 담긴 헤드 노드의 디렉터리 |
| 노드 카테고리 | 같은 설정을 공유하는 노드 묶음 |
| node-installer | 네트워크 부팅한 노드에서 식별과 이미지 동기화를 맡는 BCM 구성 요소 |
| cmsh | BCM의 셸. 모드로 들어가 객체를 고치고 commit한다 |
| Slurm | HPC 작업 스케줄러. slurmctld, slurmd, slurmdbd |
| GRES | Slurm의 일반 자원. GPU를 이걸로 관리한다 |
| drain | Slurm에서 노드에 새 작업을 주지 않는 상태 |
| Pyxis, Enroot | Slurm에서 컨테이너를 돌리는 NVIDIA 플러그인과 컨테이너 도구 |
| Run:ai | 쿠버네티스 위에서 GPU를 팀별로 나눠 주는 플랫폼 |
| Fleet Command | 엣지 장비용 NVIDIA 관리형 배포, 관리 플랫폼 |

## 복습 문제

**1.** In NVIDIA Base Command Manager, what is a software image?

- A. A container image that each node pulls from nvcr.io
- B. A disk snapshot that is taken from a node after boot
- C. A Helm chart that installs Slurm on compute nodes
- D. A full Linux filesystem directory on the head node

**2.** After GPUs were added to a node, Slurm shows the node as drained, and sinfo -R points to a gres/gpu count mismatch. What should the administrator do?

- A. Fix the Gres count in slurm.conf and resume the node.
- B. Reboot the head node so slurmctld rereads the GPU list.
- C. Enable MIG mode on the GPUs so Slurm can count them again.
- D. Remove the node from BCM and provision it from scratch.

**3.** Which cmsh command in device mode lists nodes that have booted into the node-installer but have not yet been assigned an identity?

- A. foreach --clone
- B. status
- C. newnodes
- D. commit

**4.** Which Slurm daemon runs on each compute node and launches job steps there?

- A. slurmctld
- B. slurmd
- C. slurmdbd
- D. slurmrestd

**5.** In NVIDIA Run:ai, what lets a project use more GPUs than its guaranteed quota while other GPUs in the cluster sit idle?

- A. A PodDisruptionBudget set at the department level
- B. A MIG configuration that is applied per project
- C. A Slurm partition that has a higher priority value
- D. Over-quota use of idle GPUs that can be reclaimed

## 답과 풀이

1. **D** 소프트웨어 이미지는 헤드 노드에 있는 리눅스 파일 시스템 디렉터리다. 노드는 부팅할 때 이 이미지를 받는다.
2. **A** 노드가 찾은 GPU를 slurm.conf가 다 적고 있지 않으면 slurmd가 drain된다. 설정을 맞추고 scontrol update로 RESUME한다.
3. **C** device 모드의 newnodes가 식별을 기다리는 노드의 MAC 목록을 보여 주고, -s -n으로 이름을 붙인다.
4. **B** slurmd가 계산 노드마다 돈다. slurmctld는 컨트롤러, slurmdbd는 계정 DB, slurmrestd는 REST API다.
5. **D** 노는 GPU를 할당량보다 더 쓰게 하는 over-quota다. 원래 할당량 주인이 필요하면 회수된다.

## 참고 자료

- NVIDIA, Base Command Manager 문서: <https://docs.nvidia.com/base-command-manager/index.html>
- NVIDIA, BCM 11 Administrator Manual: <https://docs.nvidia.com/base-command-manager/manuals/11/admin-manual.pdf>
- NVIDIA, BCM 11 Installation Manual: <https://docs.nvidia.com/base-command-manager/manuals/11/installation-manual.pdf>
- NVIDIA, BCM 11 Containerization Manual: <https://docs.nvidia.com/base-command-manager/manuals/11/containerization-manual.pdf>
- SchedMD, Slurm Generic Resource(GRES) Scheduling: <https://slurm.schedmd.com/gres.html>
- NVIDIA, Run:ai on DGX Cloud 개요: <https://docs.nvidia.com/dgx-cloud/run-ai/latest/overview.html>
- NVIDIA, Fleet Command: <https://www.nvidia.com/en-us/data-center/products/fleet-command/>


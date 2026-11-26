---
title: '[NCP-AIO] 배경 지식 2: 서버 밖으로, InfiniBand·GPUDirect·스토리지·BlueField DPU'
date: '2026-11-23T21:10:00+09:00'
categories:
- NCP-AIO
tags:
- nvidia
- ncp-aio
- infiniband
- rdma
- gpudirect
- nccl
- magnum-io
- storage
- bluefield
- doca
- 배경 지식
series:
- NCP-AIO
series_order: 3
---

1편은 서버 한 대 안쪽이었다. 학습 작업이 여러 서버로 퍼지면 GPU들이 스텝마다 서로 기울기를 맞추고(all-reduce), 수많은 GPU가 같은 데이터셋을 동시에 읽고, 정해진 간격으로 체크포인트를 한꺼번에 쓴다. 이때 병목은 서버 밖, 노드 사이 네트워크와 저장소로 옮겨 간다. 시험 주제 중 Magnum IO 문제 해결, 스토리지 요구 사항과 성능, DPU에 DOCA 서비스 배포가 여기에 해당해서 한 편으로 묶었다.

## 요약

- GPU 클러스터는 보통 관리망, 스토리지망과 별도로 GPU끼리 통신하는 연산 패브릭을 둔다. 연산 패브릭은 RDMA를 쓰는 InfiniBand나 RoCE다.
- InfiniBand는 서브넷 매니저(OpenSM이나 UFM)가 있어야 포트가 Active가 된다. 물리 연결은 됐는데 State가 Initializing에 머물면 서브넷 매니저부터 본다.
- Magnum IO는 GPU 입출력 기술 묶음이다. GPUDirect RDMA, GPUDirect Storage, NCCL, NVSHMEM, UCX, HPC-X, SHARP가 들어 있다.
- GPUDirect Storage는 저장소와 GPU 메모리 사이를 CPU 메모리(바운스 버퍼)를 거치지 않고 잇는다. gdscheck.py -p로 설정을 확인하고, 조건이 안 맞으면 호환 모드로 돌아 성능 이득이 없다.
- BlueField DPU는 Arm 코어가 붙은 NIC다. DPU 위의 DOCA 서비스는 standalone kubelet이 /etc/kubelet.d의 YAML을 보고 스태틱 파드처럼 띄운다.

## 1. GPU 클러스터의 네트워크는 여러 개다

AWS SAA를 공부할 때 VPC 하나에 서브넷을 나눠 쓰는 그림에 익숙했는데, GPU 클러스터는 아예 용도별로 물리 네트워크를 나누는 경우가 많다.

| 네트워크 | 하는 일 |
|---|---|
| 아웃오브밴드(OOB) 관리망 | BMC로 전원, 콘솔을 다룬다. BCM이 노드 전원을 켜고 끌 때 쓴다 |
| 인밴드 관리망 | 프로비저닝(PXE 부팅), SSH, 모니터링 |
| 스토리지망 | 공유 파일 시스템과 노드 사이 |
| 연산 패브릭(compute fabric) | 학습 중 GPU끼리 통신. RDMA를 쓰는 InfiniBand나 RoCE |

RDMA(Remote Direct Memory Access)는 한 서버의 NIC가 다른 서버의 메모리에 CPU와 커널을 거치지 않고 직접 읽고 쓰는 방식이다. 수천 개 GPU가 매 스텝 통신하는 all-reduce에서는 이 차이가 학습 시간에 그대로 나타난다.

## 2. InfiniBand와 RoCE

| | InfiniBand | RoCE |
|---|---|---|
| 위치 | 전용 스위치와 어댑터로 만든 별도 패브릭 | 이더넷 위에서 RDMA |
| 관리 | 서브넷 매니저가 패브릭을 구성한다 | 손실 없는 이더넷 설정(PFC, ECN 등)이 필요하다 |
| 대표 도구 | ibstat, ibdev2netdev, UFM | 이더넷 스위치 설정과 같은 진단 도구 |

InfiniBand에서 가장 먼저 외워 둘 게 서브넷 매니저다. 서브넷 매니저가 패브릭의 주소(LID)를 나눠 주고 경로를 계산해야 포트가 Active가 된다. 스위치에 내장되거나, 호스트에서 OpenSM으로 돌리거나, NVIDIA UFM이 맡는다.

```bash
ibstat                # 포트별 State, Physical state, Rate
ibdev2netdev          # mlx5_0 같은 IB 장치와 네트워크 인터페이스 이름 대응
```

| ibstat 결과 | 해석 |
|---|---|
| Physical state: LinkUp, State: Active | 정상 |
| Physical state: LinkUp, State: Initializing | 케이블은 됐는데 서브넷 매니저가 포트를 구성하지 않았다 |
| Physical state: Disabled나 Polling | 케이블, 트랜시버, 반대편 포트를 본다 |
| Rate가 기대보다 낮음 | 케이블 규격이나 링크 폭 협상 문제 |

## 3. Magnum IO

Magnum IO는 하나의 제품이 아니고 GPU 입출력을 빠르게 하는 기술들의 묶음 이름이다.

| 구성 요소 | 하는 일 |
|---|---|
| GPUDirect RDMA | NIC가 GPU 메모리를 직접 읽고 쓴다. 호스트 메모리를 거치지 않는다. 커널 모듈 nvidia-peermem이 필요하다 |
| GPUDirect Storage(GDS) | 저장소와 GPU 메모리 사이 직접 경로 |
| NCCL | 여러 GPU, 여러 노드 사이 집합 통신(all-reduce 등) 라이브러리. NVLink, InfiniBand를 알아서 골라 쓴다 |
| NVSHMEM | GPU 메모리를 여러 GPU가 하나의 주소 공간처럼 쓰게 하는 라이브러리 |
| UCX, HPC-X | MPI 같은 HPC 통신을 받쳐 주는 통신 프레임워크와 그 묶음 |
| SHARP | 스위치 안에서 reduce 연산을 해 노드 사이 오가는 데이터를 줄인다(in-network compute) |

여러 노드 학습이 유난히 느릴 때 확인하는 순서를 이렇게 적었다.

```bash
ibstat | grep -E 'State|Rate'                  # 1. IB 포트가 Active이고 속도가 맞나
nvidia-smi topo -m                             # 2. GPU와 NIC가 가까이(PIX 등) 붙어 있나
lsmod | grep nvidia_peermem                    # 3. GPUDirect RDMA 모듈이 올라와 있나
NCCL_DEBUG=INFO <학습 명령>                     # 4. 로그에 NET/IB가 나오나, NET/Socket으로 떨어졌나
./build/all_reduce_perf -b 8 -e 8G -f 2 -g 8   # 5. nccl-tests로 all-reduce 대역폭 측정
```

NCCL 로그에 NET/Socket이 보이면 InfiniBand 장치를 못 찾았거나 쓰지 못해서 TCP 소켓으로 내려간 것이다. 학습은 돌아가지만 몇 배 느려진다. 컨테이너에서 돌릴 때는 IB 장치가 컨테이너 안에 보이는지도 같이 확인해야 한다.

## 4. AI 데이터센터의 스토리지

학습 클러스터의 저장소는 접근 방식이 극단적이다. 수백 개 GPU가 같은 데이터셋을 동시에 읽고, 체크포인트는 정해진 순간에 모든 노드가 한꺼번에 쓴다. 그래서 한 종류로 다 해결하지 않고 층을 나눈다.

| 층 | 쓰임 | 신경 쓸 점 |
|---|---|---|
| 노드 로컬 NVMe | 데이터셋 캐시, 임시 파일 | 빠르지만 노드가 바뀌면 사라진다 |
| 공유 고성능 파일 시스템 | 데이터셋, 체크포인트 | 여러 노드가 동시에 읽고 쓰는 대역폭, 메타데이터 처리량 |
| NFS 같은 일반 공유 스토리지 | 홈 디렉터리, 코드, 설정 | 용량보다 관리 편의 |
| 오브젝트 스토리지 | 원본 데이터, 장기 보관 | 학습 전에 빠른 층으로 옮겨 둔다 |

KCNA 스토리지 글에서 본 ReadWriteMany가 여기서 실제 요구 사항이 된다. 여러 노드가 같은 볼륨을 동시에 써야 해서 공유 파일 시스템이 필요하다.

### GPUDirect Storage

보통 GPU가 파일을 읽으면 데이터가 저장소에서 CPU 메모리의 임시 버퍼(바운스 버퍼)로 왔다가 다시 GPU로 간다. GDS는 이 중간 단계를 빼고 DMA로 바로 옮긴다.

{{< mermaid >}}
flowchart TB
  subgraph r1["GDS 없이"]
    direction LR
    S1[("저장소")] --> B["CPU 메모리<br>바운스 버퍼"] --> G1["GPU 메모리"]
  end
  subgraph r2["GDS로"]
    direction LR
    S2[("저장소")] -->|"DMA 직접 경로<br>(cuFile API)"| G2["GPU 메모리"]
  end
  r1 ~~~ r2
{{< /mermaid >}}

| 항목 | 내용 |
|---|---|
| API | 애플리케이션은 cuFile API로 읽고 쓴다 |
| 커널 모듈 | nvidia-fs. CUDA Toolkit 13.4부터는 따로 설치한다. 커널과 파일 시스템이 지원하면 PCI P2PDMA 경로를 쓸 수도 있다 |
| 설치 확인 | /usr/local/cuda-<버전>/gds/tools/gdscheck.py -p |
| 설정 파일 | /etc/cufile.json. 환경 변수 CUFILE_ENV_PATH_JSON으로 다른 파일을 지정할 수 있다 |
| 호환 모드 | GDS를 못 쓰는 환경에서는 cuFile이 일반 경로로 동작한다. 작업은 되지만 직접 경로의 이득이 없다 |

'GDS를 켰는데 빨라지지 않는다'면 호환 모드로 돌고 있는지부터 의심한다. gdscheck.py -p가 그 파일 시스템, 드라이버 조합에서 GDS를 지원하는지 보여 준다.

## 5. BlueField DPU와 DOCA

DPU(Data Processing Unit)는 고속 NIC에 Arm 코어와 가속기를 붙인 장치다. 네트워크, 스토리지, 보안 처리를 호스트 CPU 대신 맡는다. DPU 안에서 리눅스가 따로 돈다. 시험 주제의 'DPU-Arm'이 이 Arm 쪽 운영 체제를 가리킨다. DOCA는 DPU용 SDK와 서비스 묶음이다. DOCA Firefly(시간 동기화), BlueMan(DPU 상태를 보는 웹 대시보드), DOCA Telemetry Service 같은 서비스가 컨테이너로 나온다.

DOCA 서비스를 DPU에 띄우는 방식을 읽다가 반가웠다. DPU에 standalone kubelet이 돌고, 이 kubelet이 /etc/kubelet.d 폴더를 지켜본다. 서비스 YAML을 그 폴더에 넣으면 kubelet이 NGC에서 이미지를 받아 파드를 띄운다. API 서버 없이 kubelet이 파일을 보고 파드를 띄우는 구조라서, CKA에서 외운 스태틱 파드(/etc/kubernetes/manifests)와 같다. 문서에는 이 배포 방식이 아직 alpha라고 적혀 있다.

```bash
# DPU(Arm) 안에서
cp doca_firefly.yaml /etc/kubelet.d/        # NGC 리소스에서 받은 서비스 YAML
sudo crictl pods                            # 파드가 떴나
sudo crictl images                          # nvcr.io/nvidia/doca/... 이미지를 받았나
sudo crictl logs <container-id>
sudo journalctl -u kubelet --since -5m      # 파드가 안 보이면 kubelet 로그
rm /etc/kubelet.d/doca_firefly.yaml         # 지우면 kubelet이 파드를 내린다
```

문서가 강조한 함정은 YAML 들여쓰기다. 공백 두 칸 들여쓰기만 쓰라고 하고, 다른 칸 수를 쓰면 동작을 보장하지 않는다고 한다. kubectl apply처럼 친절한 오류가 나오지 않으니 파드가 안 뜨면 kubelet 로그를 봐야 한다.

> **쉬운 설명**
>
> GPU 클러스터를 물류 단지로 보면 연산 패브릭은 창고끼리 잇는 전용 고속도로다. InfiniBand의 서브넷 매니저는 이 도로의 관제 센터라서, 길은 다 깔렸어도 관제 센터가 신호를 켜지 않으면 차가 출발하지 못한다(Initializing). RDMA는 상대 창고 직원을 거치지 않고 지게차가 바로 선반에 물건을 올리는 방식이다. GPUDirect Storage는 택배를 사무실(CPU 메모리)에 내려놨다가 다시 옮기지 않고 작업장(GPU)으로 바로 넣는 것이다. DPU는 창고 입구에 따로 둔 경비실이다. 출입 확인, 짐 검사를 경비실이 맡으니 창고 안 직원(CPU)은 원래 일만 한다.

## 용어 정리

| 용어 | 뜻 |
|---|---|
| RDMA | CPU와 커널을 거치지 않고 다른 서버 메모리에 직접 읽고 쓰는 방식 |
| InfiniBand | RDMA를 기본으로 하는 고성능 네트워크. 서브넷 매니저가 필요하다 |
| RoCE | 이더넷 위에서 RDMA를 쓰는 방식 |
| 서브넷 매니저(SM) | InfiniBand 패브릭에 주소를 주고 경로를 계산하는 관리자. OpenSM, UFM 등 |
| Magnum IO | GPU 입출력 기술 묶음 이름 |
| NCCL | 여러 GPU, 여러 노드 사이 집합 통신 라이브러리 |
| GPUDirect RDMA | NIC와 GPU 메모리 사이 직접 전송 |
| GPUDirect Storage | 저장소와 GPU 메모리 사이 직접 전송. cuFile API |
| 바운스 버퍼 | 데이터를 옮길 때 중간에 거치는 CPU 메모리 임시 버퍼 |
| DPU | Arm 코어와 가속기를 붙인 NIC. BlueField |
| DOCA | DPU용 SDK와 서비스 묶음 |

## 복습 문제

**1.** A new InfiniBand fabric has been cabled. On every host, ibstat shows Physical state: LinkUp but State: Initializing. What is most likely missing?

- A. The nvidia-peermem kernel module on the hosts
- B. A cufile.json file on each compute node
- C. A subnet manager running somewhere on the fabric
- D. The Fabric Manager service on each host

**2.** Which technology lets a network adapter move data directly to and from GPU memory for communication between nodes?

- A. GPUDirect RDMA
- B. NVIDIA HPC-X
- C. GPUDirect Storage
- D. NVIDIA SHARP

**3.** gdscheck.py -p reports that GDS is not supported for the file system that holds a training dataset. Reads through cuFile still succeed. What explains this?

- A. The GPUs switch into MIG mode for the read path.
- B. The reads are routed through the NVSwitch fabric.
- C. Fabric Manager is blocking peer-to-peer transfers.
- D. cuFile is running in compatibility mode.

**4.** Where does the standalone kubelet on a BlueField DPU look for DOCA service definitions to start as pods?

- A. In ConfigMaps stored in the kube-system namespace
- B. In YAML files that are placed in /etc/kubelet.d
- C. In the service catalog of the NGC private registry
- D. In the BCM software image assigned to the DPU

**5.** During a multi-node training job, NCCL logs show NET/Socket for traffic between nodes instead of NET/IB. What is the most likely cause?

- A. NCCL cannot find or use the InfiniBand devices on the nodes.
- B. MIG mode is disabled on every GPU in the job.
- C. Persistence mode is turned off on the GPUs.
- D. The container images were pulled from nvcr.io.

## 답과 풀이

1. **C** 물리 링크는 올라왔는데 State가 Initializing이면 서브넷 매니저가 포트를 구성하지 않은 것이다. Fabric Manager는 NVSwitch용이라 InfiniBand와 상관없다.
2. **A** GPUDirect RDMA다. GPUDirect Storage는 저장소와 GPU 사이, SHARP는 스위치 안 연산, HPC-X는 통신 라이브러리 묶음이다.
3. **D** GDS를 쓸 수 없는 환경에서 cuFile은 호환 모드로 일반 경로를 쓴다. 작업은 되지만 직접 경로의 이득이 없다.
4. **B** DPU의 standalone kubelet은 /etc/kubelet.d의 YAML을 보고 파드를 띄운다. 스태틱 파드와 같은 방식이다.
5. **A** InfiniBand 장치를 찾지 못하거나 쓰지 못하면 NCCL이 TCP 소켓으로 내려간다. 컨테이너라면 IB 장치가 안에 보이는지도 확인한다.

## 참고 자료

- NVIDIA, Magnum IO: <https://www.nvidia.com/en-us/data-center/magnum-io/>
- NVIDIA, GPUDirect Storage 개요: <https://docs.nvidia.com/gpudirect-storage/overview-guide/index.html>
- NVIDIA, GPUDirect Storage 설치와 문제 해결: <https://docs.nvidia.com/gpudirect-storage/troubleshooting-guide/index.html>
- NVIDIA, DOCA Container Deployment Guide: <https://docs.nvidia.com/doca/sdk/doca-container-deployment-guide/index.html>
- NVIDIA, UFM Enterprise 사용자 매뉴얼: <https://docs.nvidia.com/networking/display/ufmenterpriseumv6196>
- NCCL Tests: <https://github.com/NVIDIA/nccl-tests>


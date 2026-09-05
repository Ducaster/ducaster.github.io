---
title: '[KCNA] 스토리지: 볼륨 종류, PV와 PVC와 StorageClass, 접근 모드, CSI'
date: '2026-09-05T16:10:00+09:00'
categories:
- KCNA
tags:
- kubernetes
- kcna
- storage
- volume
- emptydir
- persistentvolume
- pvc
- storageclass
- access-modes
- reclaim-policy
- csi
- statefulset
- Container Orchestration
series:
- KCNA
series_order: 9
---

스토리지는 외울 이름이 많다. 접근 모드 약자 네 개, 회수 정책 세 개, 바인딩 모드 두 개가 있고, 보기에서 서로 바꿔 넣기 좋다. CKA 때는 PV, PVC, 파드를 이어 붙이는 YAML만 손에 익혔는데, 이번에는 누가 무엇을 만들고 무엇이 언제 지워지는지를 그림으로 다시 그렸다.

## 요약

- 컨테이너 안에 쓴 파일은 컨테이너와 같이 사라진다. 볼륨은 파드에 붙어서 컨테이너가 다시 시작돼도 남는다.
- 임시 볼륨(emptyDir, configMap, secret, downwardAPI, projected)은 파드와 수명이 같다. 오래 남길 데이터는 PVC로 PersistentVolume을 쓴다.
- PV는 실제 저장소(클러스터 범위), PVC는 사용 요청(네임스페이스 범위), StorageClass는 PV를 그때그때 만드는 방법이다.
- 접근 모드는 RWO(노드 하나에서 읽기쓰기), ROX(여러 노드에서 읽기), RWX(여러 노드에서 읽기쓰기), RWOP(파드 하나에서만 읽기쓰기)다.
- 회수 정책은 Delete와 Retain이다. 동적으로 만든 PV는 기본이 Delete라서 PVC를 지우면 데이터도 지워진다.
- CSI는 스토리지 업체가 쿠버네티스 코드를 고치지 않고 드라이버를 붙이는 표준 인터페이스다.
- StatefulSet은 volumeClaimTemplates로 파드마다 PVC를 따로 만든다.

## 1. 볼륨 종류

| 볼륨 | 데이터가 사는 곳 | 수명과 특징 |
|---|---|---|
| emptyDir | 노드 디스크(`medium: Memory`면 메모리) | 파드가 노드에서 지워지면 사라진다. 컨테이너 재시작에는 남는다. 같은 파드의 컨테이너끼리 파일을 나눌 때 쓴다 |
| configMap, secret | API 오브젝트 | 키를 파일로 마운트한다. 원본이 바뀌면 잠시 뒤 파일도 바뀐다(subPath로 마운트하면 안 바뀐다) |
| downwardAPI | 파드 자신의 정보 | 라벨, 어노테이션, 자원 값을 파일로 넣는다 |
| projected | 여러 소스 | ServiceAccount 토큰, ConfigMap, Secret, downwardAPI를 한 디렉터리에 모은다 |
| hostPath | 노드의 경로 | 노드에 묶이고 보안 위험이 크다. Pod Security Baseline이 막는다 |
| persistentVolumeClaim | PV가 가리키는 실제 저장소 | 파드가 지워져도 남는다 |
| 일반 임시 볼륨(`ephemeral`) | StorageClass로 만든 PV | 파드와 같이 만들어지고 같이 지워지는 PVC다 |

## 2. PV, PVC, StorageClass

{{< mermaid >}}
flowchart TB
  P["파드<br>volumes: persistentVolumeClaim: data"] --> C["PVC data<br>네임스페이스 범위<br>20Gi, RWO, storageClassName: fast"]
  C -->|"1:1 바인딩"| V["PV<br>클러스터 범위"]
  V --> D[("실제 저장소<br>클라우드 디스크, NFS, Ceph")]
  SC["StorageClass fast<br>provisioner: CSI 드라이버"] -.->|"PVC가 들어오면 동적 생성"| V
  A["관리자"] -.->|"정적 프로비저닝: 미리 만들어 둠"| V
{{< /mermaid >}}

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fast
provisioner: ebs.csi.aws.com           # 이 CSI 드라이버가 디스크를 만든다
parameters:
  type: gp3
reclaimPolicy: Delete
volumeBindingMode: WaitForFirstConsumer
allowVolumeExpansion: true
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: data
  namespace: shop
spec:
  accessModes: ["ReadWriteOnce"]
  storageClassName: fast
  resources:
    requests:
      storage: 20Gi
---
apiVersion: v1
kind: Pod
metadata:
  name: db
  namespace: shop
spec:
  containers:
  - name: db
    image: postgres:18
    volumeMounts:
    - name: data
      mountPath: /var/lib/postgresql
  volumes:
  - name: data
    persistentVolumeClaim:
      claimName: data
```

PV의 일생은 프로비저닝(정적 또는 동적), 바인딩, 사용, 회수 순서다. PV 상태로는 Available(아직 안 묶임), Bound(묶임), Released(PVC가 지워졌지만 아직 회수 전), Failed가 있다.

StorageClass에 `storageclass.kubernetes.io/is-default-class: "true"` 어노테이션이 있으면 기본 클래스다. PVC에 storageClassName을 아예 안 적으면 기본 클래스를 쓰고, 빈 문자열(`""`)로 적으면 동적 프로비저닝 없이 클래스 없는 PV만 찾는다.

| 바인딩 모드 | 언제 PV를 만들고 묶나 |
|---|---|
| Immediate | PVC가 생기자마자. 파드가 어느 존에 뜰지 모르고 만들어서 존이 어긋날 수 있다 |
| WaitForFirstConsumer | 그 PVC를 쓰는 파드가 노드에 배치될 때. 파드의 존에 맞춰 만든다 |

## 3. 접근 모드와 회수 정책

| 접근 모드 | 약자 | 뜻 |
|---|---|---|
| ReadWriteOnce | RWO | 노드 하나에서 읽기쓰기로 마운트. 같은 노드의 파드 여럿은 같이 쓸 수 있다 |
| ReadOnlyMany | ROX | 여러 노드에서 읽기 전용 |
| ReadWriteMany | RWX | 여러 노드에서 읽기쓰기. NFS, CephFS, 클라우드 파일 스토리지 같은 것만 된다 |
| ReadWriteOncePod | RWOP | 클러스터 전체에서 파드 하나만 읽기쓰기. v1.29 stable, CSI 볼륨만 |

블록 디스크(EBS, Persistent Disk)는 보통 RWO만 된다. 여러 노드의 파드가 같이 쓰려면 RWX를 지원하는 파일 스토리지가 필요하다.

| 회수 정책 | PVC를 지우면 |
|---|---|
| Delete | PV와 실제 저장소가 같이 지워진다. 동적 프로비저닝의 기본값 |
| Retain | PV가 Released로 남고 데이터도 남는다. 관리자가 직접 정리하거나 다시 쓴다 |
| Recycle | 지원 중단. 대신 동적 프로비저닝을 쓴다 |

## 4. CSI

예전에는 클라우드 디스크나 NFS 같은 볼륨 플러그인이 쿠버네티스 코드 안(in-tree)에 있었다. 지금은 스토리지 업체가 CSI(Container Storage Interface) 드라이버를 따로 만들어 붙인다. 쿠버네티스를 새로 릴리스하지 않아도 드라이버를 고칠 수 있다. 예전 in-tree 플러그인들은 CSI 드라이버로 옮겨졌다.

CSI 드라이버는 보통 두 부분이다. 컨트롤러 쪽(Deployment)이 볼륨을 만들고 노드에 붙이고, 노드 쪽(DaemonSet)이 각 노드에서 마운트한다.

CSI 위에서 쓸 수 있는 기능도 있다.

- **볼륨 스냅숏**: VolumeSnapshot, VolumeSnapshotClass로 스냅숏을 뜨고, 스냅숏에서 새 PVC를 만든다.
- **볼륨 확장**: StorageClass에 `allowVolumeExpansion: true`가 있으면 PVC의 크기를 늘릴 수 있다. 줄일 수는 없다.
- **볼륨 복제**: 기존 PVC를 원본으로 새 PVC를 만든다.

클러스터 안에 스토리지를 직접 운영하는 CNCF 프로젝트로는 Ceph를 쿠버네티스에서 돌리는 Rook(graduated)이 있다.

## 5. StatefulSet과 스토리지

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: web
spec:
  serviceName: web
  replicas: 3
  selector:
    matchLabels:
      app: web
  template:
    metadata:
      labels:
        app: web
    spec:
      containers:
      - name: web
        image: nginx:1.29
        volumeMounts:
        - name: data
          mountPath: /usr/share/nginx/html
  volumeClaimTemplates:          # 파드마다 PVC가 따로 생긴다: data-web-0, data-web-1, data-web-2
  - metadata:
      name: data
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 1Gi
```

web-1 파드가 다시 만들어져도 data-web-1 PVC에 다시 붙는다. StatefulSet을 지우거나 복제본을 줄여도 PVC는 기본으로 남는다. 데이터를 실수로 잃지 않게 하려는 기본값이고, `persistentVolumeClaimRetentionPolicy`로 바꿀 수 있다.

> **쉬운 설명**
>
> 창고 임대와 같다. PV는 실제 창고 칸이고, PVC는 '20평, 우리 가게만 씀'이라고 쓴 임대 신청서다. StorageClass는 창고 회사의 상품 목록이라, 신청서가 들어오면 그 자리에서 칸을 새로 지어 준다(동적 프로비저닝). 계약이 끝나면 짐을 버릴지(Delete) 남겨 둘지(Retain)는 계약서에 미리 적혀 있다. emptyDir은 호텔 방 금고다. 방에 있는 동안은 쓰지만 체크아웃(파드 삭제)하면 비워진다.

## 헷갈렸던 것들

- RWO는 파드 하나가 아니라 노드 하나다. 파드 하나로 묶으려면 RWOP다.
- emptyDir은 컨테이너 재시작에는 남고, 파드가 지워지면 사라진다.
- PV는 클러스터 범위, PVC는 네임스페이스 범위다.
- 동적 프로비저닝의 기본 회수 정책은 Delete다. PVC를 지우면 데이터도 지워진다.
- storageClassName을 안 적는 것과 빈 문자열로 적는 것은 다르다.
- StatefulSet을 지워도 PVC는 기본으로 남는다.
- PVC 크기는 늘릴 수만 있고 줄일 수 없다.

## 용어 정리

| 용어 | 뜻 |
|---|---|
| PersistentVolume | 클러스터에 준비된 실제 저장소를 나타내는 오브젝트 |
| PersistentVolumeClaim | 파드가 쓸 저장소의 크기와 접근 모드를 적은 요청 |
| StorageClass | PV를 동적으로 만드는 방법(드라이버, 파라미터, 회수 정책)을 정한 오브젝트 |
| 동적 프로비저닝 | PVC가 들어올 때 StorageClass로 PV를 자동으로 만드는 것 |
| 접근 모드 | 볼륨을 몇 개의 노드나 파드에서 어떻게 마운트할 수 있는지 |
| 회수 정책 | PVC가 지워진 뒤 PV와 데이터를 어떻게 할지 |
| CSI | 스토리지 드라이버를 쿠버네티스에 붙이는 표준 인터페이스 |
| volumeClaimTemplates | StatefulSet이 파드마다 PVC를 만들 때 쓰는 틀 |

## 복습 문제

**1.** Which access mode allows a volume to be mounted read-write by only one Pod in the whole cluster?

- A. ReadWriteOnce
- B. ReadOnlyMany
- C. ReadWriteOncePod
- D. ReadWriteMany

**2.** Which object lets a cluster create PersistentVolumes on demand when a PersistentVolumeClaim is submitted?

- A. StorageClass
- B. VolumeAttachment
- C. CSINode
- D. LimitRange

**3.** A container in a Pod crashes and is restarted on the same node. What happens to the data in the Pod's emptyDir volume?

- A. It is deleted immediately.
- B. It is moved to a PersistentVolume.
- C. It is copied into etcd.
- D. It is kept until the Pod is removed from the node.

**4.** A dynamically provisioned PersistentVolume has the reclaim policy Delete. What happens when its PersistentVolumeClaim is deleted?

- A. The PersistentVolume becomes Available for other claims.
- B. The PersistentVolume and the underlying storage are deleted.
- C. The PersistentVolume moves to Released and the data is kept.
- D. Nothing happens until an administrator acts.

**5.** Which standard interface lets storage vendors provide volume drivers without changing the Kubernetes core code?

- A. CSI
- B. CNI
- C. CRI
- D. OCI

**6.** Which StatefulSet field creates a separate PersistentVolumeClaim for each replica?

- A. volumeMounts
- B. persistentVolumeClaimRetentionPolicy
- C. volumeClaimTemplates
- D. storageClassName

**7.** Which StorageClass volumeBindingMode delays binding and provisioning until a Pod that uses the claim is scheduled?

- A. Immediate
- B. Delayed
- C. OnDemand
- D. WaitForFirstConsumer

## 답과 풀이

1. **C** RWOP는 파드 하나로 묶는다. RWO는 노드 하나 기준이라 같은 노드의 파드들은 같이 쓸 수 있다.
2. **A** StorageClass의 provisioner가 PV를 만든다.
3. **D** emptyDir은 파드 수명을 따른다. 컨테이너가 다시 시작돼도 남는다.
4. **B** Delete면 PV와 실제 디스크가 같이 지워진다. 남기려면 Retain이다.
5. **A** CSI다. CNI는 네트워크, CRI는 런타임 인터페이스다.
6. **C** volumeClaimTemplates로 data-web-0처럼 파드마다 PVC가 생긴다.
7. **D** WaitForFirstConsumer는 파드가 배치된 노드와 존을 보고 PV를 만든다.

## 참고 자료

- Kubernetes 문서, 볼륨: <https://kubernetes.io/docs/concepts/storage/volumes/>
- Kubernetes 문서, 임시 볼륨: <https://kubernetes.io/docs/concepts/storage/ephemeral-volumes/>
- Kubernetes 문서, 퍼시스턴트 볼륨: <https://kubernetes.io/docs/concepts/storage/persistent-volumes/>
- Kubernetes 문서, 스토리지 클래스: <https://kubernetes.io/docs/concepts/storage/storage-classes/>
- Kubernetes 문서, 동적 프로비저닝: <https://kubernetes.io/docs/concepts/storage/dynamic-provisioning/>
- Kubernetes 문서, 볼륨 스냅숏: <https://kubernetes.io/docs/concepts/storage/volume-snapshots/>
- Kubernetes 문서, StatefulSet: <https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/>
- Kubernetes CSI 문서: <https://kubernetes-csi.github.io/docs/>
- Rook: <https://rook.io/>


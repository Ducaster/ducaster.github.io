---
title: '[K8s 기초] 볼륨, PV, PVC: 파드가 사라져도 데이터 남기기'
date: '2025-01-11T15:50:00+09:00'
categories:
- Kubernetes
tags:
- kubernetes
- volume
- emptydir
- hostpath
- persistentvolume
- persistentvolumeclaim
- storageclass
- dynamic-provisioning
- local-path
- 설정과 스토리지
series:
- Kubernetes 기초
series_order: 13
---

설정과 스토리지 두 번째. SAA 시험이 끝나서 다시 쿠버네티스로 돌아왔다. 12월에 v1.32가 나왔고 kind도 v0.26.0부터 기본 노드가 v1.32.0이라, kind를 올리고 클러스터를 다시 만들었다(인그레스 설정 파일 그대로). 컨테이너 안에 쓴 파일은 컨테이너와 같이 사라진다는 걸 첫 주에 봤는데, 이번에는 파드가 지워져도 남는 저장소를 붙여 봤다.

## 요약

- 볼륨은 파드에 붙는 디렉터리다. emptyDir은 파드와 수명이 같고, PVC로 붙인 볼륨은 파드가 사라져도 남는다.
- PV는 실제 저장 공간, PVC는 '이만큼 필요하다'는 요청이다. 쿠버네티스가 조건이 맞는 PV를 PVC에 묶어(Bound) 준다.
- StorageClass가 있으면 PVC를 만들 때 PV가 자동으로 만들어진다(동적 프로비저닝). kind는 local-path를 쓰는 standard가 기본이다.
- WaitForFirstConsumer 모드면 PVC를 쓰는 파드가 노드에 배치될 때까지 PVC가 Pending이다. 고장이 아니다.
- 동적으로 만든 PV는 기본 회수 정책이 Delete라서 PVC를 지우면 데이터도 지워진다.

## 1. 볼륨 종류

| 볼륨 | 수명 | 쓰는 때 |
|---|---|---|
| emptyDir | 파드와 같다 | 같은 파드 컨테이너끼리 파일 공유, 임시 캐시. medium: Memory로 메모리에 둘 수도 있다 |
| configMap, secret, projected | 원본 오브젝트를 따른다 | 설정 파일, 인증서 넣기 |
| hostPath | 노드의 디렉터리 | 노드 로그를 읽는 데몬셋 등. 노드에 묶이고 보안 위험이 커서 앱에는 피한다 |
| persistentVolumeClaim | PVC와 PV를 따른다 | 데이터베이스처럼 남아야 하는 데이터 |
| CSI 드라이버 볼륨 | 스토리지에 따라 | 클라우드 디스크(EBS 등), NFS, 분산 스토리지 |

## 2. PV, PVC, StorageClass

| 오브젝트 | 누가 만드나 | 하는 일 |
|---|---|---|
| PersistentVolume(PV) | 관리자 또는 프로비저너 | 실제 저장 공간 하나. 클러스터 범위 |
| PersistentVolumeClaim(PVC) | 앱 개발자 | 크기와 접근 방식을 적은 요청. 네임스페이스 범위 |
| StorageClass | 관리자 | 어떤 프로비저너로 어떤 디스크를 만들지 정한 틀 |

```bash
kubectl get storageclass
# NAME                 PROVISIONER             RECLAIMPOLICY   VOLUMEBINDINGMODE
# standard (default)   rancher.io/local-path   Delete          WaitForFirstConsumer
```

| accessModes | 뜻 |
|---|---|
| ReadWriteOnce(RWO) | 한 노드에서 읽기·쓰기 |
| ReadOnlyMany(ROX) | 여러 노드에서 읽기만 |
| ReadWriteMany(RWX) | 여러 노드에서 읽기·쓰기(NFS 같은 공유 스토리지가 필요하다) |
| ReadWriteOncePod(RWOP) | 파드 하나만 읽기·쓰기 |

## 3. 동적 프로비저닝 따라가기

아래 YAML을 --- 앞뒤로 나눠 pvc.yaml과 writer.yaml로 저장했다. PVC만 먼저 만들어 보려고서다.

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: data
spec:
  accessModes: ["ReadWriteOnce"]
  resources:
    requests:
      storage: 1Gi
---
apiVersion: v1
kind: Pod
metadata:
  name: writer
spec:
  containers:
  - name: app
    image: busybox:1.36
    command: ["sh", "-c", "date >> /data/log.txt; cat /data/log.txt; sleep 3600"]
    volumeMounts:
    - name: data
      mountPath: /data
  volumes:
  - name: data
    persistentVolumeClaim:
      claimName: data
```

{{< mermaid >}}
sequenceDiagram
  participant U as 나
  participant A as API 서버
  participant S as 스케줄러
  participant L as local-path 프로비저너
  participant K as kubelet (노드)
  U->>A: PVC data 생성
  Note over A: Pending (WaitForFirstConsumer)
  U->>A: 파드 writer 생성 (claimName: data)
  S->>A: writer를 study-worker2에 배치
  L-->>A: 노드가 정해진 PVC 발견
  L->>A: study-worker2의 디렉터리로 PV 생성
  Note over A: PVC Bound
  K->>K: 볼륨 마운트 후 컨테이너 시작
{{< /mermaid >}}

```bash
kubectl apply -f pvc.yaml                 # PVC만 먼저
kubectl get pvc data                      # Pending
kubectl describe pvc data | tail -2       # waiting for first consumer to be created before binding
kubectl apply -f writer.yaml
kubectl get pvc,pv                        # Bound, PV 이름은 pvc-<uid>
kubectl logs writer                       # 시각 한 줄
kubectl delete pod writer && kubectl apply -f writer.yaml
kubectl logs writer                       # 시각 두 줄. 앞 파드가 쓴 줄이 남아 있다
kubectl get pod writer -o wide            # 처음과 같은 노드다. local-path는 노드에 묶인 디스크라서
```

kind의 local-path는 노드 컨테이너 안의 디렉터리를 PV로 쓴다. 그래서 PV에 노드 친화성이 붙어 있고, 이 PVC를 쓰는 파드는 그 노드로만 간다. 클라우드 디스크(EBS 등)도 비슷하게 가용 영역에 묶이는데, WaitForFirstConsumer가 '파드가 갈 노드를 먼저 정하고 거기에 디스크를 만든다'는 순서를 지켜 준다.

```bash
docker exec study-worker2 ls /var/local-path-provisioner     # pvc-..._default_data
kubectl delete pod writer && kubectl delete pvc data
kubectl get pv                                               # 회수 정책 Delete라 PV도 사라진다
```

| 회수 정책 | PVC를 지우면 |
|---|---|
| Delete(동적 프로비저닝 기본) | PV와 실제 디스크를 지운다 |
| Retain | PV가 Released로 남고 데이터도 남는다. 관리자가 정리한다 |

> **쉬운 설명**
>
> 파드는 호텔 투숙객이고, 컨테이너 안 파일은 객실에 두고 간 짐이라 체크아웃(삭제)하면 치워진다. emptyDir은 객실 금고라 같은 방 투숙객끼리는 같이 쓰지만 체크아웃하면 비워진다. PV는 호텔 밖 창고의 칸 하나이고, PVC는 '1Gi짜리 창고 칸 하나 주세요'라는 신청서다. StorageClass는 창고 칸을 즉석에서 지어 주는 업체다. WaitForFirstConsumer는 업체가 '손님이 어느 건물에 묵을지 정해지면 그 건물 옆에 창고를 지을게요' 하고 기다리는 것이다.

## 헷갈렸던 것들

- PVC가 Pending이라고 다 고장은 아니다. WaitForFirstConsumer면 파드를 만들 때까지 기다린다.
- PV는 네임스페이스가 없고 PVC는 네임스페이스에 속한다.
- RWO는 '파드 하나'가 아니라 '노드 하나'다. 같은 노드의 여러 파드는 쓸 수 있다. 파드 하나로 묶으려면 RWOP를 쓴다.
- 동적 PV의 기본 회수 정책은 Delete다. 중요한 데이터면 Retain인 StorageClass를 쓰거나 PV 정책을 바꾼다.
- PVC 크기를 줄일 수는 없다. 늘리는 것도 StorageClass가 allowVolumeExpansion을 허용해야 된다.
- hostPath는 실습에는 편하지만 노드에 묶이고 노드 파일을 건드릴 수 있어 앱에는 쓰지 않는다.

## 용어 정리

| 용어 | 뜻 |
|---|---|
| 볼륨 | 파드에 붙는 디렉터리 |
| PV | 클러스터에 있는 실제 저장 공간 하나 |
| PVC | 저장 공간 요청. 조건이 맞는 PV와 묶인다 |
| StorageClass | PV를 자동으로 만드는 방식을 정한 틀 |
| 동적 프로비저닝 | PVC가 생기면 StorageClass가 PV를 만들어 주는 것 |
| 회수 정책 | PVC가 지워졌을 때 PV와 데이터를 어떻게 할지(Delete, Retain) |

## 복습 문제

**1.** 같은 파드의 두 컨테이너가 파일을 주고받게 emptyDir을 붙이고, 파드를 지웠다 만들면 파일이 남는지 확인해라.

**2.** 500Mi PVC notes를 만들고 nginx:1.27 파드 site가 /usr/share/nginx/html에 쓰게 해라. PVC가 언제 Bound가 되는지 확인해라.

**3.** notes의 PV 회수 정책을 Retain으로 바꾼 뒤 PVC를 지우면 PV가 어떤 상태가 되는지 확인해라.

## 답과 풀이

1. emptyDir은 파드와 같이 사라지니 파일이 남지 않는다. 남겨야 하면 PVC를 쓴다.

2. WaitForFirstConsumer라 파드를 만든 뒤에 Bound가 된다.

```bash
kubectl create -f - <<'YAML'
apiVersion: v1
kind: PersistentVolumeClaim
metadata: {name: notes}
spec: {accessModes: [ReadWriteOnce], resources: {requests: {storage: 500Mi}}}
YAML
kubectl get pvc notes                    # Pending
kubectl run site --image=nginx:1.27 --overrides='{"spec":{"volumes":[{"name":"n","persistentVolumeClaim":{"claimName":"notes"}}],"containers":[{"name":"site","image":"nginx:1.27","volumeMounts":[{"name":"n","mountPath":"/usr/share/nginx/html"}]}]}}'
kubectl get pvc notes -w                 # Bound
```

3. Retain이면 PV가 지워지지 않고 Released로 남는다. 그 PV를 다시 쓰려면 관리자가 claimRef를 지우거나 새 PV를 만들어야 한다.

```bash
PV=$(kubectl get pvc notes -o jsonpath='{.spec.volumeName}')
kubectl patch pv $PV -p '{"spec":{"persistentVolumeReclaimPolicy":"Retain"}}'
kubectl delete pod site && kubectl delete pvc notes
kubectl get pv $PV                       # STATUS Released
```

## 참고 자료

- Kubernetes 문서, 볼륨: <https://kubernetes.io/docs/concepts/storage/volumes/>
- Kubernetes 문서, 퍼시스턴트 볼륨: <https://kubernetes.io/docs/concepts/storage/persistent-volumes/>
- Kubernetes 문서, 스토리지 클래스: <https://kubernetes.io/docs/concepts/storage/storage-classes/>
- Kubernetes 문서, 동적 볼륨 프로비저닝: <https://kubernetes.io/docs/concepts/storage/dynamic-provisioning/>
- Kubernetes 블로그, v1.32 릴리스: <https://kubernetes.io/blog/2024/12/11/kubernetes-v1-32-release/>
- kind v0.26.0 릴리스: <https://github.com/kubernetes-sigs/kind/releases/tag/v0.26.0>
- local-path-provisioner: <https://github.com/rancher/local-path-provisioner>

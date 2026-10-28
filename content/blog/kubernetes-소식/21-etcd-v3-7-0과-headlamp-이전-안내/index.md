---
title: '[K8s 소식] etcd v3.7.0 정식 출시, Dashboard에서 Headlamp로 옮기는 단계별 안내'
date: '2026-07-18T15:00:00+09:00'
categories:
- Kubernetes
tags:
- kubernetes
- etcd
- etcd-v3.7
- rangestream
- v2store
- upgrade
- headlamp
- dashboard
- rbac
- kubeconfig
- 소식
series:
- Kubernetes 소식
series_order: 21
---

6월 초에 베타로 정리한 etcd 3.7이 7월 8일에 정식으로 나왔다. 베타 때 없던 내용이 꽤 붙어서 업그레이드할 때 볼 것 위주로 다시 정리했다. 7월 13일에는 지난번 '곧 나온다'던 Dashboard에서 Headlamp로 옮기는 단계별 안내가 올라와서, 내 kind 클러스터 기준으로 따라가 봤다.

## 요약

- etcd v3.7.0은 RangeStream, keys-only 조회 최적화, 리스 개선으로 쿠버네티스 컨트롤 플레인에서 etcd CPU 사용이 v3.6보다 크게 줄 거라고 한다. RangeStream은 쿠버네티스 v1.37의 EtcdRangeStream 기능 게이트로 쓸 수 있게 된다.
- 서버가 시작할 때 v3store만 읽는다. 다만 호환성 때문에 v2 스냅숏은 아직 만들고 --snapshot-count도 남아 있다. 이 둘은 v3.8에서 빠진다.
- 업그레이드 때 깨질 수 있는 것: --experimental- 플래그 전부 제거, v2 discovery와 v2 요청, v2 클라이언트 제거, 아키텍처별 태그 이미지 없이 멀티 아키텍처 이미지만 배포.
- Headlamp는 데스크톱에서는 내 kubeconfig로, 클러스터 안에서는 ServiceAccount나 OIDC로 API에 붙는다. Dashboard처럼 토큰을 붙여 넣는 로그인이 없다.
- Dashboard의 생성 마법사는 없고 YAML을 적용하는 방식이다. 옮긴 뒤에는 Dashboard용으로 만든 서비스 어카운트와 넓은 권한 바인딩을 꼭 지우라고 한다.

## 1. etcd v3.7.0

| 구분 | 내용 |
|---|---|
| RangeStream | 큰 조회 결과를 서버가 다 모았다가 보내지 않고 조각으로 흘려 보낸다. 서버와 클라이언트 양쪽의 지연과 메모리가 예측 가능해진다 |
| keys-only 조회 | etcdctl get --keys-only 같은 요청은 bbolt에서 값을 읽지 않고 메모리 인덱스만 본다(값으로 정렬할 때만 예외) |
| 리스 | 과부하 때 LeaseRevoke를 먼저 처리하고, FastLeaseKeepAlive로 갱신을 빠르게 한다 |
| watch | 겹치는 키 watch에서 find()가 빨라졌고, watch 전송 경로 지표가 새로 생겼다 |
| v3store로 부팅 | v3.4부터 이어 온 작업의 끝. 시작할 때 v2 저장소에 기대지 않는다 |
| protobuf 정리 | golang/protobuf, gogo/protobuf를 google.golang.org/protobuf로 바꿨다. 바이너리 사용자는 상관없고 Go 모듈로 가져다 쓰는 쪽만 코드 수정이 필요할 수 있다 |
| 기타 | 단일 멤버용 유닉스 소켓 엔드포인트, etcdutl 모든 명령에 타임아웃, 클라이언트에서 JWT 직접 설정 |
| 함께 올라간 것 | bbolt v1.5.1(파일 크기 제한 기능), raft v3.7.0(ReadIndex 경로에서 오래된 읽기 방지) |

베타 때는 v2store가 '완전히' 없어졌다고 읽었는데, 정식 글을 보니 v2 스냅숏 생성 하나는 아직 남아 있었다. 그래서 --snapshot-count 플래그도 3.7까지는 쓴다.

{{< mermaid >}}
flowchart TB
  subgraph before["올리기 전에"]
    direction LR
    A["3.6.11 이상인지 확인<br>(3.5면 3.5.26부터)"] --> B["--experimental- 플래그를<br>기능 게이트나<br>정식 플래그로 바꾸기"]
    B --> C["이미지 태그가<br>-arm64 같은 아키텍처별이면<br>멀티 아키텍처 태그로"]
  end
  subgraph during["올리는 중"]
    direction LR
    D["멤버 하나씩<br>롤링 업그레이드"] --> E["단계마다<br>endpoint health,<br>member list 확인"]
  end
  before --> during
{{< /mermaid >}}

1월의 좀비 멤버 글에서 3.5에서 3.6으로 갈 때 3.5.26을 거치라고 했는데, 이번에는 3.6에서 3.7로 갈 때 3.6.11 이상을 권한다. etcd는 매번 '바로 앞 마이너의 최신 패치'를 거치는 게 안전하다는 걸 이번에 확실히 외웠다. 쿠버네티스에서도 컨트롤 플레인은 마이너를 건너뛰지 못하는 것과 비슷하다.

## 2. Dashboard에서 Headlamp로, 단계별로

가장 큰 차이는 '누구로 접속하느냐'다. Dashboard는 클러스터 안에서만 돌고 서비스 어카운트 토큰을 붙여 넣어 로그인한다. Headlamp 데스크톱은 kubectl처럼 내 kubeconfig를 읽는다. 글의 표현으로는 '클러스터를 따라가는 UI가 아니라 내 신원을 따라가는 UI'다.

{{< mermaid >}}
flowchart LR
  subgraph desk["데스크톱 Headlamp"]
    U1["나"] --> H1["Headlamp 앱<br>~/.kube/config 읽음"]
  end
  subgraph incl["클러스터 안 Headlamp"]
    U2["브라우저"] --> I["인그레스<br>TLS, OIDC"]
    I --> H2["Headlamp 파드"]
  end
  H1 -->|"내 자격 증명<br>내 RBAC"| API["API 서버"]
  H2 -->|"OIDC 토큰이나<br>ServiceAccount"| API
{{< /mermaid >}}

| 단계 | 할 일 |
|---|---|
| 1. 지금 쓰는 것 적기 | 어떤 클러스터, 네임스페이스에서 무엇을(조회, 수정, 스케일, 디버깅) 하는지, Dashboard에 어떻게 접속하고 어떤 토큰과 바인딩으로 로그인하는지 |
| 2. kubeconfig 확인 | kubectl config current-context, kubectl get nodes(안 되면 내 네임스페이스의 get pods)가 되면 Headlamp도 된다 |
| 3. 전환 방식 | 같이 쓰다가 끄기(공유 클러스터 권장) 또는 한 번에 바꾸기 |
| 4. 설치 | 데스크톱은 macOS면 brew install --cask headlamp. 클러스터 안은 Helm 차트(headlamp/headlamp) |
| 5. 권한 | 최소 권한부터. Dashboard에 높은 권한 토큰을 쓰고 있었다면 옮긴 뒤 줄이거나 지운다 |
| 6. 생성 방식 | 폼 대신 YAML 적용. 마법사가 아쉬우면 kubectl create ... --dry-run=client -o yaml로 뽑아서 붙인다 |
| 7. Dashboard 제거 | Helm이면 helm uninstall kubernetes-dashboard -n kubernetes-dashboard. Dashboard용 서비스 어카운트, (클러스터)롤바인딩, 옛 문서 링크까지 정리 |

내 노트북에서는 데스크톱 앱 쪽이 맞았다. brew로 설치하고 열었더니 kubeconfig에 있는 kind 컨텍스트들이 클러스터 목록에 바로 나왔다. 클러스터 안 설치는 Helm 차트와 port-forward로 확인만 하는 정도면 된다.

```bash
helm repo add headlamp https://kubernetes-sigs.github.io/headlamp/
helm repo update
helm install headlamp headlamp/headlamp --namespace headlamp --create-namespace
kubectl -n headlamp port-forward svc/headlamp 8080:80      # http://localhost:8080
```

생성 폼이 없다는 게 처음엔 불편해 보였는데, 글의 설명대로 UI로만 만든 오브젝트는 다시 만들 수 없다. kubectl create --dry-run=client -o yaml로 뽑은 매니페스트를 붙이는 방식은 CKA, CKAD 시험 때 매번 쓰던 요령이라 오히려 익숙했다.

## 내 클러스터에서 확인할 것

```bash
kubectl -n kube-system get pods -l component=etcd -o jsonpath='{.items[*].spec.containers[0].image}{"\n"}'
grep -n 'experimental' /etc/kubernetes/manifests/etcd.yaml      # 컨트롤 플레인 노드에서
kubectl get sa,rolebinding,clusterrolebinding -A | grep -i dashboard
```

- etcd 매니페스트에 --experimental-로 시작하는 플래그가 남아 있으면 3.7에서는 시작하지 않을 수 있다. 오래전에 kubeadm으로 만든 클러스터일수록 확인한다.
- etcd 이미지를 직접 지정하면서 아키텍처 이름이 붙은 태그를 쓰고 있었다면 3.7부터는 없다.
- dashboard가 들어간 서비스 어카운트나 바인딩이 남아 있으면, 특히 cluster-admin에 묶인 것부터 지운다.

> **쉬운 설명**
>
> etcd 3.7은 오래된 장부 양식을 거의 다 버리고 새 장부만 쓰는 버전이다. 큰 서류 묶음도 한 번에 다 복사해 주지 않고 몇 장씩 나눠서 건네주니(RangeStream) 기다리는 시간과 책상 공간이 덜 든다. 다만 옛 양식에 맞춰 쓰던 메모(--experimental 플래그)는 더는 안 받는다. Headlamp로 옮기는 건 건물 안내 데스크에서 출입증(토큰)을 빌려 쓰던 방식에서, 내 신분증(kubeconfig)으로 어느 건물이든 드나드는 방식으로 바꾸는 것이다. 이사가 끝나면 안내 데스크에 맡겨 둔 만능 출입증(Dashboard용 높은 권한)을 꼭 회수해야 한다.

## 용어 정리

| 용어 | 뜻 |
|---|---|
| RangeStream | etcd에서 큰 범위 조회 결과를 조각으로 받는 RPC |
| keys-only | 값 없이 키 이름만 받는 조회 옵션 |
| 리스(lease) | etcd 키에 붙이는 만료 시간. 쿠버네티스의 리더 선출, 노드 하트비트 등에 쓰인다 |
| --snapshot-count | 몇 번의 변경마다 스냅숏을 남길지 정하는 etcd 플래그. v3.8에서 제거 예정 |
| 멀티 아키텍처 이미지 | 하나의 태그로 amd64, arm64 등 여러 아키텍처 이미지를 가리키는 매니페스트 리스트 |
| OIDC | 외부 신원 제공자로 로그인하는 표준. 클러스터 안 Headlamp의 공유 접속에 쓴다 |

## 참고 자료

- Kubernetes 블로그, Announcing etcd v3.7.0: <https://kubernetes.io/blog/2026/07/08/announcing-etcd-3.7/>
- Kubernetes 블로그, Kubernetes Dashboard to Headlamp: A Step-by-Step Guide: <https://kubernetes.io/blog/2026/07/13/kubernetes-dashboard-to-headlamp/>
- etcd 문서, v3.7 업그레이드: <https://etcd.io/docs/v3.7/upgrades/upgrade_3_7/>
- Headlamp 설치 문서: <https://headlamp.dev/docs/latest/installation/>

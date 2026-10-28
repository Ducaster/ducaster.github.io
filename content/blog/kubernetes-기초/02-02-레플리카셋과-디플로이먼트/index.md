---
title: '[K8s 기초] 레플리카셋과 디플로이먼트: 지워도 다시 생기는 파드, 버전 바꾸기'
date: '2024-11-16T15:10:00+09:00'
categories:
- Kubernetes
tags:
- kubernetes
- replicaset
- deployment
- self-healing
- rollout
- rollback
- scale
- owner-reference
- 워크로드
series:
- Kubernetes 기초
series_order: 6
---

앞 글에서 직접 만든 파드는 지우면 그냥 사라졌다. 이번에는 파드 개수를 지켜 주는 레플리카셋과, 그 레플리카셋을 갈아 끼우며 버전을 바꾸는 디플로이먼트를 kind에서 직접 흔들어 봤다.

## 요약

- 레플리카셋은 셀렉터에 맞는 파드를 정해진 개수만큼 유지한다. 파드가 지워지거나 노드가 죽으면 새로 만든다.
- 디플로이먼트는 레플리카셋을 관리한다. 파드 템플릿이 바뀌면 새 레플리카셋을 만들고, 새 것은 늘리고 옛것은 줄인다(롤링 업데이트).
- 옛 레플리카셋을 0개로 남겨 두기 때문에 kubectl rollout undo로 이전 버전으로 돌아갈 수 있다.
- 새 레플리카셋은 템플릿(이미지, 환경 변수 등)이 바뀔 때만 생긴다. replicas만 바꾸면 기존 레플리카셋의 개수만 바뀐다.
- 실제로는 레플리카셋을 직접 만들 일이 거의 없고, 디플로이먼트를 쓴다.

## 1. 레플리카셋: 개수를 지킨다

```bash
kubectl create deployment web --image=nginx:1.26 --replicas=3
kubectl get deployment,replicaset,pods -l app=web
```

```
NAME                  READY   UP-TO-DATE   AVAILABLE
deployment.apps/web   3/3     3            3

NAME                             DESIRED   CURRENT   READY
replicaset.apps/web-6d5f8c7b9d   3         3         3

NAME                       READY   STATUS
pod/web-6d5f8c7b9d-2xkqp   1/1     Running
pod/web-6d5f8c7b9d-8hn4w   1/1     Running
pod/web-6d5f8c7b9d-tq7zl   1/1     Running
```

이름이 줄줄이 이어진다. 디플로이먼트 web이 레플리카셋 web-해시를 만들고, 레플리카셋이 파드 web-해시-무작위를 만든다. 해시는 파드 템플릿에서 나온 값이고 파드 라벨 pod-template-hash에도 들어 있다(위 출력의 해시는 예시다).

```bash
kubectl delete pod web-6d5f8c7b9d-2xkqp       # 하나 지우면
kubectl get pods -l app=web                    # 곧바로 새 이름의 파드가 생겨 3개가 된다
kubectl get pod <남은 파드> -o jsonpath='{.metadata.ownerReferences[0].kind}{"/"}{.metadata.ownerReferences[0].name}'
# ReplicaSet/web-6d5f8c7b9d
```

라벨을 바꿔 파드를 레플리카셋에서 떼어 내는 실험도 해 봤다. 셀렉터에 안 맞게 된 파드는 레플리카셋의 관리 대상에서 빠지고, 레플리카셋은 개수를 맞추려고 하나를 새로 만든다. 떼어 낸 파드는 지우지 않고 그대로 두니, 문제 있는 파드를 서비스에서 빼서 살펴볼 때 쓸 수 있다.

```bash
kubectl label pod web-6d5f8c7b9d-8hn4w app=debug --overwrite
kubectl get pods -L app                        # app=web 3개 + app=debug 1개
```

## 2. 디플로이먼트: 버전을 바꾸고 되돌린다

```bash
kubectl set image deployment/web nginx=nginx:1.27
kubectl annotate deployment/web kubernetes.io/change-cause="nginx 1.27로 올림"
kubectl rollout status deployment/web
kubectl get replicaset -l app=web
```

```
NAME             DESIRED   CURRENT   READY
web-6d5f8c7b9d   0         0         0
web-7b9c6f5d4f   3         3         3
```

{{< mermaid >}}
flowchart TB
  D["Deployment web<br>replicas: 3<br>image: nginx:1.27"] --> R2["ReplicaSet web-7b9c6f5d4f<br>nginx:1.27 · 3개"]
  R2 --> P1["Pod"]
  R2 --> P2["Pod"]
  R2 --> P3["Pod"]
  D --> R1["ReplicaSet web-6d5f8c7b9d<br>nginx:1.26 · 0개<br>(롤백용으로 남겨 둠)"]
{{< /mermaid >}}

업데이트하는 동안 새 레플리카셋이 하나씩 늘고 옛 레플리카셋이 하나씩 줄었다. 기본 전략인 RollingUpdate는 원하는 개수의 25%까지 더 띄우고(maxSurge), 25%까지 모자라도(maxUnavailable) 된다는 규칙으로 속도를 정한다. 한꺼번에 다 내렸다 올리는 Recreate 전략도 있다.

```bash
kubectl rollout history deployment/web
kubectl rollout undo deployment/web                    # 바로 이전 버전(1.26)으로
kubectl rollout undo deployment/web --to-revision=2    # 특정 리비전으로
kubectl scale deployment/web --replicas=5              # 개수만 바꿀 때. 새 레플리카셋은 안 생긴다
```

| 바꾼 것 | 새 레플리카셋이 생기나 | 결과 |
|---|---|---|
| 이미지, 환경 변수, 라벨 등 파드 템플릿 | 생긴다 | 롤링 업데이트, 리비전 증가 |
| replicas | 안 생긴다 | 지금 레플리카셋의 개수만 바뀐다 |
| 셀렉터 | 바꿀 수 없다 | 디플로이먼트를 다시 만들어야 한다 |

> **쉬운 설명**
>
> 레플리카셋은 '항상 세 명이 근무해야 한다'는 규칙을 지키는 근무 관리자다. 한 명이 퇴근해 버리면(파드 삭제) 바로 대체 인력을 부른다. 명찰(라벨)을 바꿔 단 직원은 자기 팀원이 아닌 걸로 보고 새 사람을 부른다. 디플로이먼트는 인사팀이다. 새 매뉴얼(새 이미지)로 일할 팀을 꾸리면 새 팀 인원을 한 명씩 늘리고 옛 팀을 한 명씩 줄인다. 옛 팀 명단은 버리지 않고 보관해 두어서, 새 매뉴얼에 문제가 있으면 옛 팀을 다시 불러온다(롤백).

## 헷갈렸던 것들

- 디플로이먼트가 파드를 직접 만들지 않는다. 디플로이먼트 → 레플리카셋 → 파드.
- replicas만 바꾸면 새 레플리카셋이 생기지 않고 리비전도 그대로다.
- rollout undo를 하면 이전 리비전이 '새 리비전 번호'를 받는다. 번호가 되돌아가는 게 아니다.
- 옛 레플리카셋은 기본 10개까지 남는다(revisionHistoryLimit).
- 레플리카셋이 관리하는 파드를 직접 지워도 소용없다. 줄이려면 replicas를 줄인다.
- 변경 사유는 kubernetes.io/change-cause 어노테이션으로 남긴다. 예전 자료의 --record는 쓰지 않는 게 좋다.

## 용어 정리

| 용어 | 뜻 |
|---|---|
| 레플리카셋 | 셀렉터에 맞는 파드를 정해진 개수로 유지하는 컨트롤러 |
| 디플로이먼트 | 레플리카셋을 관리하며 롤링 업데이트와 롤백을 하는 컨트롤러 |
| 자가 치유 | 파드가 사라지면 컨트롤러가 다시 만들어 원하는 개수를 맞추는 것 |
| 롤아웃 | 디플로이먼트가 새 버전으로 바뀌는 과정 |
| 리비전 | 디플로이먼트의 파드 템플릿 버전 번호 |
| ownerReferences | 이 오브젝트를 만든 주인(예: 파드의 주인은 레플리카셋)을 가리키는 필드 |

## 복습 문제

**1.** 디플로이먼트 shop(nginx:1.26, 복제본 2개)을 만들고, 파드 하나를 지웠을 때 다시 생기는지 확인해라.

**2.** shop의 이미지를 nginx:1.27로 바꾼 뒤 레플리카셋이 몇 개인지, 각각 몇 개의 파드를 갖는지 확인해라.

**3.** shop을 이전 버전으로 되돌리고, rollout history에서 리비전 번호가 어떻게 바뀌었는지 확인해라.

## 답과 풀이

1. 지운 직후 다시 조회하면 새 이름의 파드가 있다.

```bash
kubectl create deployment shop --image=nginx:1.26 --replicas=2
kubectl delete $(kubectl get pod -l app=shop -o name | head -1)
kubectl get pods -l app=shop -w
```

2. 옛 레플리카셋은 0개, 새 레플리카셋이 2개를 갖는다.

```bash
kubectl set image deployment/shop nginx=nginx:1.27
kubectl rollout status deployment/shop
kubectl get rs -l app=shop
```

3. 1번 리비전으로 돌아가면 그 리비전이 3번이 되고, 목록에는 2와 3이 남는다.

```bash
kubectl rollout undo deployment/shop
kubectl rollout history deployment/shop
```

## 참고 자료

- Kubernetes 문서, 레플리카셋: <https://kubernetes.io/docs/concepts/workloads/controllers/replicaset/>
- Kubernetes 문서, 디플로이먼트: <https://kubernetes.io/docs/concepts/workloads/controllers/deployment/>
- Kubernetes 튜토리얼, 롤링 업데이트 수행: <https://kubernetes.io/docs/tutorials/kubernetes-basics/update/update-intro/>
- Kubernetes 문서, 소유자와 종속 오브젝트: <https://kubernetes.io/docs/concepts/overview/working-with-objects/owners-dependents/>

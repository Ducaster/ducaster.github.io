---
title: '[K8s 기초] 데몬셋, 스테이트풀셋, 잡, 크론잡: 디플로이먼트로 안 되는 일들'
date: '2024-11-22T21:40:00+09:00'
categories:
- Kubernetes
tags:
- kubernetes
- daemonset
- statefulset
- headless-service
- job
- cronjob
- volumeclaimtemplates
- 워크로드
series:
- Kubernetes 기초
series_order: 7
---

워크로드 세 번째이자 마지막. 디플로이먼트는 '어느 파드든 똑같고, 계속 떠 있는' 앱에 맞는다. 노드마다 하나씩 떠야 하는 에이전트, 이름과 저장소가 고정돼야 하는 데이터베이스, 한 번 돌고 끝나는 작업은 다른 컨트롤러를 쓴다. 네 가지를 kind에서 하나씩 띄워 봤다.

## 요약

- 데몬셋은 노드마다 파드를 하나씩 띄운다. 로그 수집기, 모니터링 에이전트, kube-proxy가 데몬셋이다.
- 스테이트풀셋은 파드에 web-0, web-1 같은 고정 이름과 파드별 저장소(PVC)를 주고, 순서대로 만들고 지운다. 헤드리스 서비스와 같이 쓴다.
- 잡은 파드가 성공으로 끝날 때까지 실행한다. 실패하면 기본 6번까지 다시 시도한다.
- 크론잡은 정해진 일정마다 잡을 만든다. 성공한 잡은 기본 3개, 실패한 잡은 1개까지 남긴다.
- 끝나는 작업인지, 노드마다 필요한지, 고정 이름·저장소가 필요한지 순서로 물어보면 고를 수 있다.

## 1. 어떤 컨트롤러를 고를까

{{< mermaid >}}
flowchart TD
  Q1{"끝나는 작업인가?"} -->|"예"| Q2{"정해진 시각마다 반복?"}
  Q2 -->|"예"| CJ["CronJob"]
  Q2 -->|"아니오"| J["Job"]
  Q1 -->|"아니오, 계속 떠 있다"| Q3{"노드마다 하나씩 필요?"}
  Q3 -->|"예"| DS["DaemonSet"]
  Q3 -->|"아니오"| Q4{"파드마다 고정 이름과<br>자기 저장소가 필요?"}
  Q4 -->|"예"| SS["StatefulSet"]
  Q4 -->|"아니오"| DP["Deployment"]
{{< /mermaid >}}

| 컨트롤러 | 파드 이름 | 몇 개 | 예 |
|---|---|---|---|
| Deployment | 무작위(web-해시-xxxxx) | 정한 개수 | 웹, API 서버 |
| StatefulSet | 고정 순번(db-0, db-1) | 정한 개수, 순서대로 | 데이터베이스, 메시지 큐 |
| DaemonSet | 무작위 | 노드마다 하나 | 로그 수집, 모니터링, kube-proxy, CNI |
| Job | 무작위 | 성공할 때까지 | 데이터 이전, 배치 계산 |
| CronJob | 잡이 만드는 이름 | 일정마다 잡 하나 | 백업, 정리 작업, 리포트 |

## 2. 데몬셋: 노드마다 하나

```yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: node-agent
spec:
  selector:
    matchLabels:
      app: node-agent
  template:
    metadata:
      labels:
        app: node-agent
    spec:
      containers:
      - name: agent
        image: busybox:1.36
        command: ["sh", "-c", "while true; do echo running on $NODE_NAME; sleep 30; done"]
        env:
        - name: NODE_NAME
          valueFrom:
            fieldRef:
              fieldPath: spec.nodeName
```

```bash
kubectl apply -f node-agent.yaml
kubectl get daemonset node-agent         # DESIRED 2
kubectl get pods -l app=node-agent -o wide
```

노드가 3개인데 파드는 2개였다. 컨트롤 플레인 노드에 'node-role.kubernetes.io/control-plane:NoSchedule' 테인트가 있어서다. kube-proxy와 kindnet은 이 테인트를 견디는 설정(톨러레이션)이 있어서 컨트롤 플레인에도 떠 있다. 테인트는 나중에 스케줄링을 공부할 때 더 보기로 했다.

## 3. 스테이트풀셋: 고정 이름과 자기 저장소

```yaml
apiVersion: v1
kind: Service
metadata:
  name: web
spec:
  clusterIP: None
  selector:
    app: web-ss
  ports:
  - port: 80
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: web
spec:
  serviceName: web
  replicas: 2
  selector:
    matchLabels:
      app: web-ss
  template:
    metadata:
      labels:
        app: web-ss
    spec:
      containers:
      - name: nginx
        image: nginx:1.27
        volumeMounts:
        - name: www
          mountPath: /usr/share/nginx/html
  volumeClaimTemplates:
  - metadata:
      name: www
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 1Gi
```

```bash
kubectl apply -f web-ss.yaml
kubectl get pods -l app=web-ss -w        # web-0이 Ready가 된 뒤에 web-1이 만들어진다
kubectl get pvc                          # www-web-0, www-web-1 (kind 기본 StorageClass가 만들어 준다)
kubectl exec web-0 -- sh -c 'echo web-0 > /usr/share/nginx/html/index.html'
kubectl delete pod web-0                 # 지우면
kubectl get pod web-0 -w                 # 같은 이름으로 다시 생기고
kubectl exec web-0 -- cat /usr/share/nginx/html/index.html   # 파일도 그대로 있다
```

헤드리스 서비스(clusterIP: None)를 같이 만들면 파드마다 web-0.web.default.svc.cluster.local 같은 고정 DNS 이름이 생긴다. 데이터베이스 복제본이 서로를 이름으로 찾을 때 이걸 쓴다.

## 4. 잡과 크론잡: 끝나는 작업

```bash
kubectl create job hello --image=busybox:1.36 -- sh -c 'echo hello from job; sleep 3'
kubectl get job hello                    # COMPLETIONS 1/1
kubectl logs job/hello

kubectl create cronjob tick --image=busybox:1.36 --schedule="*/1 * * * *" -- date
kubectl get cronjob tick
kubectl get jobs -w                      # 1분마다 tick-xxxxxxxx 잡이 생긴다
kubectl create job tick-now --from=cronjob/tick   # 일정을 기다리지 않고 한 번 실행
```

| 필드 | 뜻 | 기본값 |
|---|---|---|
| completions | 성공해야 하는 파드 수 | 1 |
| parallelism | 동시에 띄울 파드 수 | 1 |
| backoffLimit | 실패로 보기 전 재시도 횟수 | 6 |
| restartPolicy | 잡 파드는 OnFailure나 Never만 된다 | (지정 필요, create job은 Never) |
| successfulJobsHistoryLimit | 크론잡이 남기는 성공 잡 수 | 3 |
| failedJobsHistoryLimit | 크론잡이 남기는 실패 잡 수 | 1 |

크론잡 일정은 따로 정하지 않으면 컨트롤러 매니저의 시간대를 따르고, spec.timeZone으로 Asia/Seoul처럼 지정할 수 있다.

> **쉬운 설명**
>
> 디플로이먼트는 교대 근무 아르바이트다. 누가 와도 같은 일을 하니 이름표가 없다. 스테이트풀셋은 지정석이 있는 정직원이다. 1번 자리, 2번 자리가 정해져 있고 개인 사물함(PVC)이 있어서, 휴가 갔다 와도 같은 자리와 사물함을 쓴다. 데몬셋은 층마다 한 명씩 두는 경비원이라 층(노드)이 늘면 경비원도 는다. 잡은 한 번 맡기는 외주 작업이고, 크론잡은 '매일 아침 6시 청소' 같은 정기 예약이다.

## 헷갈렸던 것들

- 데몬셋 파드가 컨트롤 플레인 노드에 안 뜨는 건 테인트 때문이다. 톨러레이션을 주면 뜬다.
- 스테이트풀셋은 serviceName에 헤드리스 서비스를 지정해야 파드별 DNS가 생긴다.
- 스테이트풀셋을 지워도 PVC는 기본으로 남는다. 데이터를 지키려는 동작이라 직접 지워야 한다.
- 잡 파드의 restartPolicy는 Always가 안 된다.
- 끝난 잡의 파드는 로그를 볼 수 있게 남아 있다. 잡을 지우거나 ttlSecondsAfterFinished를 주면 정리된다.
- 크론잡 일정은 지정하지 않으면 한국 시간이 아닐 수 있다. 클러스터 시간대(보통 UTC)를 확인한다.

## 용어 정리

| 용어 | 뜻 |
|---|---|
| 데몬셋 | 노드마다 파드를 하나씩 유지하는 컨트롤러 |
| 스테이트풀셋 | 고정 이름, 순서, 파드별 저장소를 보장하는 컨트롤러 |
| 헤드리스 서비스 | 클러스터 IP 없이 파드별 DNS만 주는 서비스(clusterIP: None) |
| volumeClaimTemplates | 스테이트풀셋 파드마다 PVC를 하나씩 만들어 주는 템플릿 |
| 잡 | 파드가 성공으로 끝날 때까지 실행하는 컨트롤러 |
| 크론잡 | cron 형식 일정마다 잡을 만드는 컨트롤러 |

## 복습 문제

**1.** 2절의 데몬셋이 컨트롤 플레인 노드에도 뜨게 고쳐라.

**2.** 스테이트풀셋 web의 복제본을 3개로 늘리고, 새 파드 이름과 새 PVC 이름을 맞혀 본 뒤 확인해라.

**3.** 5분마다 date를 출력하는 크론잡 report를 한국 시간 기준으로 만들어라.

## 답과 풀이

1. 컨트롤 플레인 테인트를 견디는 톨러레이션을 파드 템플릿에 넣는다.

```bash
kubectl patch daemonset node-agent --type=merge -p '{"spec":{"template":{"spec":{"tolerations":[{"key":"node-role.kubernetes.io/control-plane","operator":"Exists","effect":"NoSchedule"}]}}}}'
kubectl get pods -l app=node-agent -o wide    # 3개
```

2. 순번이 이어져서 web-2와 www-web-2가 생긴다.

```bash
kubectl scale statefulset web --replicas=3
kubectl get pods -l app=web-ss
kubectl get pvc
```

3. --schedule로 일정을 주고, 시간대는 YAML의 spec.timeZone에 넣는다.

```bash
kubectl create cronjob report --image=busybox:1.36 --schedule="*/5 * * * *" --dry-run=client -o yaml -- date > report.yaml
# spec 아래에 timeZone: Asia/Seoul 추가
kubectl apply -f report.yaml
```

## 참고 자료

- Kubernetes 문서, 워크로드 관리: <https://kubernetes.io/docs/concepts/workloads/controllers/>
- Kubernetes 문서, 데몬셋: <https://kubernetes.io/docs/concepts/workloads/controllers/daemonset/>
- Kubernetes 문서, 스테이트풀셋: <https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/>
- Kubernetes 문서, 잡: <https://kubernetes.io/docs/concepts/workloads/controllers/job/>
- Kubernetes 문서, 크론잡: <https://kubernetes.io/docs/concepts/workloads/controllers/cron-jobs/>
- Kubernetes 튜토리얼, 스테이트풀셋 기초: <https://kubernetes.io/docs/tutorials/stateful-application/basic-stateful-set/>

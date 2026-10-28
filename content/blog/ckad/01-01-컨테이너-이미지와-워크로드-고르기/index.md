---
title: '[CKAD] 컨테이너 이미지와 워크로드 고르기: Dockerfile, Job, CronJob'
date: '2025-03-13T22:20:00+09:00'
categories:
- CKAD
tags:
- kubernetes
- ckad
- dockerfile
- container-image
- imagepullpolicy
- job
- cronjob
- daemonset
- statefulset
- 애플리케이션 설계와 빌드
series:
- CKAD
series_order: 2
---

애플리케이션 설계와 빌드(20%) 범위 중 '컨테이너 이미지 정의·빌드·수정'과 '알맞은 워크로드 리소스 고르기'다. CKA에서는 디플로이먼트만 깊게 봤는데, CKAD는 잡과 크론잡 옵션을 꽤 세세하게 묻는다고 해서 필드를 표로 정리했다.

## 요약

- 이미지는 Dockerfile로 만들고, 빌드한 뒤 태그를 붙여 저장소에 올리거나 tar로 저장한다. 멀티 스테이지 빌드로 실행 이미지를 작게 만든다.
- imagePullPolicy를 안 쓰면 태그가 :latest이거나 없을 때 Always, 그 밖의 태그나 다이제스트면 IfNotPresent가 된다.
- 계속 떠 있어야 하면 Deployment, 순서와 고정 이름·저장소가 필요하면 StatefulSet, 노드마다 하나면 DaemonSet, 한 번 끝나면 Job, 정해진 시간마다면 CronJob이다.
- 잡은 completions(몇 번 성공해야 끝), parallelism(동시에 몇 개), backoffLimit(재시도), activeDeadlineSeconds(시간 제한)로 동작을 정한다.

## 1. 이미지 정의와 빌드

```dockerfile
# 빌드 단계: 컴파일 도구가 있는 큰 이미지
FROM golang:1.23 AS build
WORKDIR /src
COPY . .
RUN CGO_ENABLED=0 go build -o /app ./cmd/server

# 실행 단계: 결과물만 담은 작은 이미지
FROM gcr.io/distroless/static:nonroot
COPY --from=build /app /app
USER nonroot
EXPOSE 8080
ENTRYPOINT ["/app"]
```

```bash
docker build -t registry.example.com/shop/api:1.0 .     # podman build도 같은 형식
docker tag registry.example.com/shop/api:1.0 registry.example.com/shop/api:stable
docker push registry.example.com/shop/api:1.0
docker save registry.example.com/shop/api:1.0 -o api-1.0.tar   # tar로 저장하라는 문제
docker images | grep shop/api
```

Dockerfile의 ENTRYPOINT·CMD는 쿠버네티스의 command·args와 짝이다. 파드에 command를 쓰면 ENTRYPOINT를, args를 쓰면 CMD를 덮어쓴다.

| Dockerfile | 파드 스펙 | 덮어쓰면 |
|---|---|---|
| ENTRYPOINT | command | 실행 파일 자체가 바뀐다 |
| CMD | args | 실행 파일에 넘기는 인자만 바뀐다 |

## 2. 이미지 참조와 pull 정책

| 이미지 표기 | imagePullPolicy를 안 쓰면 |
|---|---|
| nginx (태그 없음) | Always |
| nginx:latest | Always |
| nginx:1.27 | IfNotPresent |
| nginx@sha256:... (다이제스트) | IfNotPresent |

같은 태그에 내용이 바뀔 수 있으면(1.27처럼 패치가 계속 덮이는 태그) 노드에 남은 옛 이미지가 쓰일 수 있다. 정확히 같은 이미지를 보장하려면 다이제스트로 쓴다. 비공개 저장소는 docker-registry 타입 Secret을 만들어 imagePullSecrets에 넣는다.

```bash
k create secret docker-registry regcred --docker-server=registry.example.com \
  --docker-username=bot --docker-password='<토큰>'
# 파드 spec.imagePullSecrets: [{name: regcred}]
```

## 3. 워크로드 고르기

{{< mermaid >}}
flowchart TD
  Q["무엇을 돌리나?"] --> A{"끝나는 작업?"}
  A -->|"예"| B{"정해진 시간마다?"}
  B -->|"예"| CJ["CronJob"]
  B -->|"아니오"| J["Job"]
  A -->|"아니오, 계속 떠 있음"| C{"노드마다<br>하나씩?"}
  C -->|"예"| DS["DaemonSet<br>(로그 수집, 모니터링)"]
  C -->|"아니오"| D{"고정 이름과<br>파드별 저장소?"}
  D -->|"예"| SS["StatefulSet<br>(DB, 메시지 큐)"]
  D -->|"아니오"| DP["Deployment<br>(웹, API)"]
{{< /mermaid >}}

## 4. Job

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: resize
spec:
  completions: 6
  parallelism: 2
  backoffLimit: 3
  activeDeadlineSeconds: 600
  ttlSecondsAfterFinished: 3600
  template:
    spec:
      restartPolicy: Never
      containers:
      - name: resize
        image: busybox:1.36
        command: ["sh", "-c", "echo resizing; sleep 5"]
```

| 필드 | 뜻 | 기본 |
|---|---|---|
| completions | 성공한 파드가 이만큼 되면 잡 완료 | 1 |
| parallelism | 동시에 돌릴 파드 수 | 1 |
| backoffLimit | 실패한 뒤 재시도할 횟수. 넘으면 잡 실패 | 6 |
| activeDeadlineSeconds | 잡 전체 시간 제한. 넘으면 실행 중인 파드를 끝내고 실패 처리 | 없음 |
| ttlSecondsAfterFinished | 끝난 뒤 이 시간이 지나면 잡과 파드를 지운다 | 없음 |
| completionMode: Indexed | 파드마다 0부터 번호(JOB_COMPLETION_INDEX)를 준다 | NonIndexed |

위 잡은 2개씩 3번에 나눠 6개를 성공시키고, 10분 안에 못 끝내면 실패한다. 잡의 restartPolicy는 Never나 OnFailure만 된다. Never면 실패할 때마다 새 파드가 생기고, OnFailure면 같은 파드 안에서 컨테이너만 다시 시작한다.

## 5. CronJob

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: report
spec:
  schedule: "30 1 * * *"
  timeZone: "Asia/Seoul"
  concurrencyPolicy: Forbid
  startingDeadlineSeconds: 300
  successfulJobsHistoryLimit: 3
  failedJobsHistoryLimit: 1
  jobTemplate:
    spec:
      backoffLimit: 2
      template:
        spec:
          restartPolicy: OnFailure
          containers:
          - name: report
            image: busybox:1.36
            command: ["sh", "-c", "date; echo report"]
```

| 필드 | 뜻 |
|---|---|
| schedule | 분 시 일 월 요일. 30 1 * * *은 매일 01:30 |
| timeZone | 스케줄을 해석할 시간대. 없으면 kube-controller-manager의 시간대 |
| concurrencyPolicy | 이전 잡이 아직 돌 때: Allow(기본, 같이 돈다), Forbid(이번 건 건너뜀), Replace(이전 것을 멈추고 새로) |
| startingDeadlineSeconds | 예정 시각을 놓쳤을 때 이 시간 안이면 늦게라도 시작 |
| successfulJobsHistoryLimit / failedJobsHistoryLimit | 남겨 둘 성공·실패 잡 수(기본 3 / 1) |
| suspend | true면 새 잡을 만들지 않는다 |

스케줄 안에 TZ=나 CRON_TZ= 를 넣는 방식은 지원하지 않는다. 시간대는 timeZone 필드로 쓴다. 테스트할 때는 기다리지 말고 크론잡에서 잡을 바로 만든다.

```bash
k create job report-manual --from=cronjob/report
k get jobs,pods -l job-name=report-manual
k patch cronjob report -p '{"spec":{"suspend":true}}'
```

> **쉬운 설명**
>
> 워크로드 고르기는 직원 고용 형태를 정하는 일이다. 디플로이먼트는 언제든 교체 가능한 정규직 여러 명, 스테이트풀셋은 자리와 사물함이 정해진 담당자, 데몬셋은 층마다 한 명씩 두는 경비원, 잡은 일이 끝나면 퇴근하는 단기 계약직, 크론잡은 매일 정해진 시간에 오는 청소 업체다. 잡의 completions는 '몇 건을 끝내야 계약 종료', parallelism은 '한 번에 몇 명 투입', backoffLimit은 '몇 번 실패하면 계약 해지'다.

## 헷갈렸던 것들

- 태그가 없거나 :latest면 pull 정책 기본값이 Always다. 그 밖의 태그는 IfNotPresent.
- command는 ENTRYPOINT를, args는 CMD를 덮어쓴다.
- 잡의 restartPolicy에 Always는 안 된다. k create job은 Never, k create cronjob은 OnFailure로 만든다.
- backoffLimit 기본값은 6이다. activeDeadlineSeconds가 backoffLimit보다 먼저 걸리면 재시도가 남아도 실패한다.
- concurrencyPolicy 기본값은 Allow라 이전 잡이 끝나지 않아도 새 잡이 겹쳐서 돈다.
- 크론잡을 지금 바로 돌려 보려면 k create job --from=cronjob/<이름>.
- 크론잡 시간대는 timeZone 필드로. 스케줄 문자열에 TZ를 넣으면 거절된다.

## 용어 정리

| 용어 | 뜻 |
|---|---|
| 멀티 스테이지 빌드 | 빌드용 이미지와 실행용 이미지를 나눠 결과물만 옮기는 Dockerfile 방식 |
| 다이제스트 | 이미지 내용의 해시(sha256). 태그와 달리 바뀌지 않는다 |
| imagePullPolicy | 이미지를 언제 받을지(Always, IfNotPresent, Never) |
| completions / parallelism | 잡이 끝나는 성공 수 / 동시에 돌리는 파드 수 |
| concurrencyPolicy | 크론잡의 이전 잡이 돌 때 새 잡을 어떻게 할지 |

## 복습 문제

**1.** Build an image `app:2.0` from the Dockerfile in the current directory, and save it to `/opt/app-2.0.tar`.

**2.** Create a Job named `batch` that runs `echo done` with `busybox:1.36`. The Job must complete after 4 successful runs, run 2 Pods at a time, and retry at most 2 times on failure.

**3.** Create a CronJob named `weekly` that runs every Monday at 09:00 Korea Standard Time. If the previous Job is still running, skip the new run.

**4.** Run the CronJob `weekly` once now, without waiting for its schedule.

## 답과 풀이

1. 빌드와 저장을 차례로 한다. 문제가 podman을 쓰라고 하면 명령 이름만 바꾼다.

```bash
docker build -t app:2.0 .
docker save app:2.0 -o /opt/app-2.0.tar
```

2. 명령형으로 뼈대를 만들고 completions, parallelism, backoffLimit을 넣는다.

```bash
k create job batch --image=busybox:1.36 $do -- echo done > batch.yaml
# spec 아래: completions: 4, parallelism: 2, backoffLimit: 2
k apply -f batch.yaml
k get job batch -w
```

3. 요일은 0(일)부터라 월요일은 1이다. timeZone과 concurrencyPolicy: Forbid를 넣는다.

```bash
k create cronjob weekly --image=busybox:1.36 --schedule="0 9 * * 1" $do -- date > weekly.yaml
# spec 아래: timeZone: "Asia/Seoul", concurrencyPolicy: Forbid
k apply -f weekly.yaml
```

4. 크론잡의 잡 템플릿으로 잡을 바로 만든다.

```bash
k create job weekly-now --from=cronjob/weekly
```

## 참고 자료

- Kubernetes v1.32 문서, 이미지: <https://v1-32.docs.kubernetes.io/docs/concepts/containers/images/>
- Kubernetes v1.32 문서, 잡: <https://v1-32.docs.kubernetes.io/docs/concepts/workloads/controllers/job/>
- Kubernetes v1.32 문서, 크론잡: <https://v1-32.docs.kubernetes.io/docs/concepts/workloads/controllers/cron-jobs/>
- Kubernetes v1.32 문서, 컨테이너 명령과 인자 정의: <https://v1-32.docs.kubernetes.io/docs/tasks/inject-data-application/define-command-argument-container/>
- Docker 문서, 멀티 스테이지 빌드: <https://docs.docker.com/build/building/multi-stage/>


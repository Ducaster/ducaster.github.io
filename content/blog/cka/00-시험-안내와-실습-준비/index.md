---
title: '[CKA] 시험 안내와 실습 준비: 2025년 2월 개편 범위, 시험 환경, 명령형 명령'
date: '2025-02-08T21:30:00+09:00'
categories:
- CKA
tags:
- kubernetes
- cka
- ckad
- kubectl
- 시험후기
- dry-run
- killer-sh
- 시험 준비
series:
- CKA
series_order: 1
---

SAA를 따고 바로 CKA 공부를 시작했다. 객관식이던 SAA와 달리 CKA는 터미널에서 실제 클러스터를 다루는 실기 시험이라, 개념보다 손이 먼저 움직이게 만드는 게 목표다. 마침 2월 18일부터 출제 범위가 바뀐다고 해서, 바뀐 범위 기준으로 정리를 시작한다.

## 요약

- 2시간 동안 실제 클러스터에서 문제를 푸는 실기 시험이다. 2025년 3월 기준 Kubernetes v1.32 환경이고, 66% 이상이면 합격이다.
- 2025년 2월 18일부터 세부 항목이 바뀌었다. etcd 백업·복원이 빠지고 Helm·Kustomize, Gateway API, CRD·오퍼레이터, CNI·CSI·CRI 같은 확장 인터페이스가 들어왔다.
- 문제마다 지정된 호스트에 ssh로 들어가서 풀고, 끝나면 exit로 기본 호스트(base)에 돌아와야 한다.
- 시험 중에는 kubernetes.io/docs, kubernetes.io/blog, helm.sh/docs를 볼 수 있다. 외우는 것보다 문서에서 YAML을 빨리 찾는 연습이 중요하다.
- YAML은 처음부터 치지 않는다. kubectl 명령형 명령에 --dry-run=client -o yaml을 붙여 뼈대를 만들고 고친다.

## 1. 시험 정보 (2025년 3월 기준)

| 항목 | 내용 |
|---|---|
| 형식 | 온라인 감독, 실기(명령줄에서 여러 과제를 푼다) |
| 시간 | 2시간 |
| 환경 | Kubernetes v1.32, etcd v3.5 |
| 합격 기준 | 66% 이상 (CKAD도 66%, CKS는 67%) |
| 재시험 | 1회 포함 |
| 유효 기간 | 2년 |
| 시뮬레이터 | killer.sh 2회. 한 번 켜면 36시간 동안 쓸 수 있고, 20~25문제가 나온다 |
| 볼 수 있는 문서 | kubernetes.io/docs(번역본 포함), kubernetes.io/blog, helm.sh/docs |

시험 환경은 Kubernetes 새 마이너 버전이 나오고 4~8주 안에 그 버전으로 맞춰진다고 한다. 내가 볼 3월에는 v1.32다.

![CKA와 CKAD의 도메인별 출제 비중](./attachments/k8s-domain-weights.png)
_CKA는 트러블슈팅이 30%로 가장 크고, CKAD는 환경·구성·보안이 25%로 가장 크다. CKA는 2025년 2월 18일 개편 범위 기준_

## 2. 2025년 2월 18일 범위 개편

도메인 다섯 개와 비중은 그대로이고, 도메인 안의 세부 항목이 바뀌었다. 시험을 산 날짜와 상관없이 2월 18일 이후에 응시하면 새 범위다.

| 도메인 | 빠진 것 | 새로 들어온 것 |
|---|---|---|
| 클러스터 아키텍처·설치·구성 (25%) | etcd 백업·복원 | 클러스터 수명 주기 관리, 고가용성 컨트롤 플레인 구성, Helm·Kustomize로 구성 요소 설치, 확장 인터페이스(CNI, CSI, CRI), CRD 이해와 오퍼레이터 설치 |
| 워크로드와 스케줄링 (15%) | 매니페스트 관리·템플릿 도구 '알기' | 워크로드 오토스케일링, 파드 어드미션과 스케줄링(리소스 제한, 노드 어피니티 등) |
| 서비스와 네트워킹 (20%) | 노드의 호스트 네트워크 구성, CNI 플러그인 고르기 | NetworkPolicy 정의·적용, Gateway API로 인그레스 트래픽 관리 |
| 스토리지 (10%) | | StorageClass와 동적 프로비저닝 |
| 트러블슈팅 (30%) | | 클러스터·애플리케이션 리소스 사용량 모니터링 |

etcd 백업은 범위에서 빠졌지만 컨트롤 플레인을 이해하는 데 필요해서 클러스터 편에서 짧게 정리할 생각이다.

## 3. 시험 환경에서 미리 알아 둘 것

| 항목 | 내용 |
|---|---|
| 호스트 이동 | 과제마다 ssh로 접속할 호스트가 안내된다. 끝나면 exit로 base 호스트에 돌아온다. ssh 안에서 다시 ssh(중첩)는 안 된다 |
| 미리 설정된 도구 | 각 호스트에 kubectl과 k 별칭, bash 자동 완성, yq, curl, wget, man이 있다. base 호스트에는 이 도구들이 없다 |
| 관리자 권한 | sudo -i로 root가 된다 |
| 복사·붙여넣기 | 터미널에서는 Ctrl+Shift+C, Ctrl+Shift+V. 브라우저 같은 다른 앱에서는 Ctrl+C, Ctrl+V |

{{< mermaid >}}
flowchart LR
  B["base 호스트<br>(kubectl 없음)"] -->|"ssh 과제 호스트"| H["과제 호스트<br>k 별칭·자동 완성"]
  H -->|"문제 풀이"| H
  H -->|"exit"| B
  B -->|"다음 과제 호스트로 ssh"| H2["다른 과제 호스트"]
{{< /mermaid >}}

## 4. YAML은 명령으로 뼈대부터

시험 시간이 모자란 가장 큰 이유는 YAML을 손으로 치는 것이다. 명령형 명령에 --dry-run=client -o yaml을 붙이면 서버에 만들지 않고 YAML만 출력한다. 파일로 받아서 고친 뒤 apply 한다.

```bash
export do="--dry-run=client -o yaml"   # 자주 쓰니 변수로
k create deploy web --image=nginx:1.27 --replicas=3 $do > web.yaml
vim web.yaml
k apply -f web.yaml
```

| 만들 것 | 명령 |
|---|---|
| 파드 | `k run tmp --image=busybox:1.36 --restart=Never -- sleep 3600` |
| 디플로이먼트 | `k create deploy web --image=nginx:1.27 --replicas=3` |
| 서비스 | `k expose deploy web --port=80 --target-port=8080` |
| 잡, 크론잡 | `k create job hello --image=busybox:1.36 -- echo hi` / `k create cronjob backup --image=busybox:1.36 --schedule="0 2 * * *" -- date` |
| ConfigMap, Secret | `k create cm app-config --from-literal=MODE=prod` / `k create secret generic db-cred --from-literal=password=s3cr3t` |
| Role, RoleBinding | `k create role pod-reader --verb=get,list,watch --resource=pods` / `k create rolebinding dev-read --role=pod-reader --user=jane` |
| 인그레스 | `k create ingress web --rule="shop.example.com/*=web:80"` |

실제로 kubectl v1.32.2로 잡을 만들어 보면 이렇게 나온다. restartPolicy가 Never로 이미 들어가 있다.

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  creationTimestamp: null
  name: hello
spec:
  template:
    metadata:
      creationTimestamp: null
    spec:
      containers:
      - command:
        - echo
        - hi
        image: busybox:1.36
        name: hello
        resources: {}
      restartPolicy: Never
status: {}
```

크론잡으로 만들면 같은 자리에 restartPolicy: OnFailure가 들어간다. 직접 써 보기 전까지는 둘이 같은 줄 알았다.

인그레스는 함정이 하나 있다. --rule에 경로를 /로 쓰면 pathType이 Exact로 만들어져서 /login 같은 하위 경로가 안 잡힌다. /*로 써야 Prefix가 된다.

```bash
k create ingress web --rule="shop.example.com/=web:80" $do | grep pathType
#        pathType: Exact
k create ingress web --rule="shop.example.com/*=web:80" $do | grep pathType
#        pathType: Prefix
```

자주 쓰는 vim 설정도 시험 시작하자마자 넣는다. 들여쓰기가 탭으로 들어가면 YAML이 깨진다.

```bash
echo 'set expandtab tabstop=2 shiftwidth=2' >> ~/.vimrc
```

필드 이름이 기억 안 나면 문서를 뒤지기 전에 k explain부터 본다. k explain pod.spec.containers.livenessProbe처럼 점으로 내려가면 된다.

> **쉬운 설명**
>
> CKA는 운전면허 필기가 아니라 도로 주행이다. 교통 법규(개념)를 다 알아도 핸들을 빨리 못 돌리면 시간 안에 코스를 못 끝낸다. 명령형 명령은 자동 주차 보조 같은 거라서, 큰 틀은 기계한테 맡기고 나는 마지막 미세 조정(YAML 수정)만 한다. 시험장(시험 환경)에 대해서는 미리 알아 둬야 할 게 있다. 코스마다 다른 차(호스트)로 갈아타야 하고, 내리고 나서 다음 차로 타야 한다(exit 후 ssh).

## 5. 연습 계획

| 단계 | 할 일 |
|---|---|
| 1 | kind나 minikube로 v1.32 클러스터를 띄워 놓고 명령형 명령을 손에 익힌다 |
| 2 | kubeadm 설치·업그레이드는 VM 두세 대로 직접 해 본다(kind로는 kubeadm 과정을 연습하기 어렵다) |
| 3 | 도메인별로 정리하면서 복습 문제를 직접 친다 |
| 4 | 시험 1~2주 전에 killer.sh 1회차, 직전에 2회차. 실제 시험보다 어렵다는 평이 많다 |

## 헷갈렸던 것들

- 2월 18일 이후 응시면 새 범위다. 구매일이나 재시험 여부는 상관없다.
- 과제마다 호스트가 다르다. 이전 과제 호스트에서 그대로 풀면 엉뚱한 클러스터를 건드린다.
- base 호스트에는 kubectl이 없다. 과제 호스트로 ssh한 뒤에 풀어야 한다.
- k create ingress --rule="host/=svc:80"은 pathType Exact다. 하위 경로까지 받으려면 /*로 쓴다.
- 잡은 restartPolicy Never, 크론잡은 OnFailure로 만들어진다. 파드 기본값 Always는 잡에서 쓸 수 없다.
- Secret의 data는 base64로 인코딩될 뿐 암호화가 아니다. password=s3cr3t는 czNjcjN0으로 들어간다.

## 용어 정리

| 용어 | 뜻 |
|---|---|
| 실기 시험(performance-based) | 객관식 없이 실제 환경에서 과제를 수행하고 결과로 채점하는 시험 |
| 명령형 명령 | kubectl create, run, expose처럼 명령 한 줄로 리소스를 만드는 방식 |
| 선언형 | YAML에 원하는 상태를 적고 apply로 맞추는 방식 |
| --dry-run=client | 서버에 보내지 않고 클라이언트에서만 결과를 만들어 보는 옵션 |
| k explain | 리소스 필드의 구조와 설명을 보여 주는 명령 |

## 참고 자료

- Linux Foundation, CKA 시험 안내: <https://training.linuxfoundation.org/certification/certified-kubernetes-administrator-cka/>
- Linux Foundation, CKA 범위 변경 안내: <https://training.linuxfoundation.org/certified-kubernetes-administrator-cka-program-changes/>
- Linux Foundation, CKA·CKAD 시험 환경 안내: <https://docs.linuxfoundation.org/tc-docs/certification/tips-cka-and-ckad>
- Linux Foundation, 시험 중 허용 자료: <https://docs.linuxfoundation.org/tc-docs/certification/certification-resources-allowed>
- Kubernetes v1.32 문서, kubectl 빠른 참조: <https://v1-32.docs.kubernetes.io/docs/reference/kubectl/quick-reference/>
- Kubernetes v1.32 문서, 잡: <https://v1-32.docs.kubernetes.io/docs/concepts/workloads/controllers/job/>


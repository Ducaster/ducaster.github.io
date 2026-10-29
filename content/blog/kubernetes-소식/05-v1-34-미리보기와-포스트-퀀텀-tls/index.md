---
title: '[K8s 소식] v1.34 미리보기, 그리고 이미 켜져 있던 포스트 퀀텀 TLS'
date: '2025-08-02T15:20:00+09:00'
categories:
- Kubernetes
tags:
- kubernetes
- v1.34
- sneak-peek
- dra
- kyaml
- traffic-distribution
- hpa
- post-quantum
- tls
- ml-kem
- 소식
series:
- Kubernetes 소식
series_order: 5
---

7월 28일에 v1.34 미리보기 글이 나왔다. 8월 말 출시 예정이고 이번에는 제거나 지원 중단이 없다고 한다. 그보다 열흘 앞서 나온 포스트 퀀텀 암호(PQC) 글에 더 눈이 갔다. 따로 발표도 없었는데 v1.33부터 API 서버 TLS에 양자 내성 키 교환이 이미 켜져 있었다는 내용이다.

## 요약

- v1.34는 8월 말에 나오고, 제거·지원 중단 항목이 없다. 미리보기 글 기준이라 바뀔 수 있다.
- DRA(GPU 같은 장치 할당)의 기본 기능이 stable을 목표로 한다. 그러면 resource.k8s.io/v1 API가 기본으로 켜진다.
- kubectl get -o kyaml 출력이 들어올 예정이다. KYAML은 문자열을 항상 큰따옴표로 감싸고 {}와 []를 쓰는, 더 헷갈리지 않는 YAML 부분집합이다.
- 쿠버네티스 v1.33은 Go 1.24로 빌드돼, 따로 설정하지 않아도 TLS에서 하이브리드 포스트 퀀텀 키 교환(X25519MLKEM768)을 쓴다.
- v1.32(Go 1.23) 서버에 kubectl v1.33(Go 1.24)으로 붙으면 서로 다른 PQC 알고리즘이라 고전 암호로 조용히 떨어진다.

## 1. v1.34 미리보기

| 기능 | 예정 단계 | 한 줄 정리 |
|---|---|---|
| DRA 기본 기능(구조화된 파라미터) | stable | ResourceClaim, DeviceClass, ResourceSlice로 GPU 같은 장치를 요청·할당한다 |
| 이미지 풀에 ServiceAccount 토큰 사용 | beta, 기본 켜짐 | 오래 사는 imagePullSecrets 대신 파드마다 짧게 사는 토큰으로 레지스트리 인증 |
| 디플로이먼트 podReplacementPolicy | alpha | 옛 파드가 종료를 시작하자마자 새 파드를 만들지, 완전히 끝날 때까지 기다릴지 고른다 |
| kubelet·API 서버 트레이싱 | stable | OpenTelemetry로 API 서버부터 kubelet, 런타임까지 한 흐름으로 추적한다 |
| trafficDistribution PreferSameZone, PreferSameNode | beta | PreferClose는 지원 중단되고 PreferSameZone이 같은 뜻이 된다. PreferSameNode는 같은 노드 우선 |
| KYAML 출력 | kubectl 기능 | kubectl get -o kyaml |
| HPA 허용 오차 설정 | beta | HPA마다 scaleUp·scaleDown의 tolerance를 따로 정한다. 기본은 클러스터 전체 10% |

CKA 공부할 때 HPA 공식에서 '허용 오차 0.1'을 외웠는데, 이제 HPA마다 바꿀 수 있게 된다. 공식 글의 설명대로라면 파드가 아주 많은 디플로이먼트에서 10%는 수백 개 파드가 남는 차이일 수 있다.

KYAML 규칙을 따라 파드 하나를 손으로 써 봤다(실제 kubectl 출력이 아니라 규칙대로 쓴 예다).

```yaml
{
  apiVersion: "v1",
  kind: "Pod",
  metadata: {
    name: "hello",   # 주석이 된다
  },
  spec: {
    containers: [{
      name: "web",
      image: "nginx:1.27",
    }],
  },
}
```

KYAML은 YAML의 부분집합이라 어떤 버전의 kubectl에도 그대로 넣을 수 있다. 들여쓰기에 의미가 없고, 문자열을 항상 따옴표로 감싸서 NO가 false로 바뀌는 'Norway 문제' 같은 타입 착각이 없다. JSON과 비슷하지만 주석과 끝 쉼표를 허용하고 키에 따옴표가 필요 없다.

## 2. 이미 켜져 있던 포스트 퀀텀 TLS

양자 컴퓨터가 지금의 키 교환 방식을 깰 수 있다는 걱정 때문에, '지금 엿들어 저장해 두고 나중에 푼다'는 공격에 대비해 키 교환부터 바꾸는 중이라고 한다. 흐름은 이렇다.

| 시점 | 일어난 일 |
|---|---|
| 2024년 11월 | Chrome 131이 ML-KEM 하이브리드 키 교환 지원 |
| 2025년 2월 | Go 1.24가 crypto/tls에 X25519MLKEM768을 넣고, 설정이 없으면 기본으로 켰다 |
| 2025년 4월 | OpenSSL 3.5.0 지원. 쿠버네티스 v1.33이 Go 1.24로 빌드돼 나왔다 |
| 결과 | 쿠버네티스는 TLS 곡선 설정(CurvePreferences)을 따로 두지 않아서, v1.33 API 서버와 kubelet이 별도 KEP 없이 PQC 키 교환을 쓰게 됐다 |

공식 글은 OpenSSL 3.5로 직접 확인하는 방법을 보여 준다.

```bash
kubectl config view --minify --raw -o jsonpath='{.clusters[0].cluster.certificate-authority-data}' | base64 -d > ca.crt
echo -n Q | openssl s_client -connect 127.0.0.1:<포트> -CAfile ca.crt 2>/dev/null | grep 'Negotiated TLS1.3 group'
# Negotiated TLS1.3 group: X25519MLKEM768
```

함정도 있었다. Go 1.23은 표준 이전 초안(X25519Kyber768Draft00)을 기본으로 썼고, Go 1.24는 그걸 빼고 표준(X25519MLKEM768)으로 바꿨다.

{{< mermaid >}}
flowchart LR
  K["kubectl v1.33<br>(Go 1.24)<br>X25519MLKEM768"] -->|"공통 PQC 알고리즘 없음"| A["API 서버 v1.32<br>(Go 1.23)<br>X25519Kyber768Draft00"]
  A --> R["고전 키 교환(X25519)으로<br>조용히 떨어진다"]
{{< /mermaid >}}

시험 본 v1.32 클러스터에 새 kubectl을 쓰는 조합이 바로 이 경우라 웃음이 났다. 연결은 잘 되니 알아채기 어렵다. 또 ML-KEM 공개 키가 1.2KB 정도라 TLS ClientHello가 패킷 하나(보통 1500바이트)를 넘을 수 있고, 이걸 가정하지 못한 장비나 라이브러리에서 연결이 실패한 사례가 있다고 한다. 서명(인증서) 쪽 PQC는 아직 한참 뒤라고 한다.

## 내 클러스터에서 확인할 것

```bash
kubectl version -o yaml | grep -E 'gitVersion|goVersion'     # 클라이언트와 서버의 Go 버전
openssl version                                                # 3.5 이상이면 협상 그룹을 직접 볼 수 있다
```

- 클라이언트와 서버의 Go 버전이 1.23과 1.24로 갈려 있으면 PQC가 빠질 수 있다는 걸 알아 둔다.
- 앞단에 TLS를 끊는 오래된 장비나 프록시가 있으면 큰 ClientHello를 처리하는지 확인한다.
- HPA tolerance나 trafficDistribution 값은 v1.34가 나온 뒤 실제 문서로 다시 확인한다.

> **쉬운 설명**
>
> TLS 키 교환은 두 사람이 남이 엿들어도 모르게 비밀번호를 정하는 방법이다. 양자 컴퓨터가 생기면 지금 녹음해 둔 대화를 나중에 풀 수 있어서, 자물쇠를 미리 새것으로 바꾸는 중이다. 쿠버네티스는 자물쇠 공장(Go)이 기본 자물쇠를 새것으로 바꾸면서 저절로 새 자물쇠를 달게 됐다. 다만 한쪽이 시제품 자물쇠(초안), 한쪽이 정식 자물쇠(표준)를 들고 있으면 둘이 맞지 않아 예전 자물쇠로 대화한다.

## 용어 정리

| 용어 | 뜻 |
|---|---|
| DRA | Dynamic Resource Allocation. GPU 같은 장치를 요청하고 할당하는 API |
| KYAML | 쿠버네티스용으로 만든, 더 엄격한 YAML 부분집합 |
| PQC | Post-Quantum Cryptography. 양자 컴퓨터로도 깨기 어려운 암호 |
| ML-KEM | 표준화된 포스트 퀀텀 키 교환 방식. X25519MLKEM768은 기존 X25519와 섞은 하이브리드 |
| ClientHello | TLS 연결을 시작할 때 클라이언트가 보내는 첫 메시지 |

## 참고 자료

- Kubernetes 블로그, v1.34 미리보기: <https://kubernetes.io/blog/2025/07/28/kubernetes-v1-34-sneak-peek/>
- Kubernetes 블로그, 쿠버네티스의 포스트 퀀텀 암호: <https://kubernetes.io/blog/2025/07/18/pqc-in-k8s/>
- KEP-5295, KYAML: <https://github.com/kubernetes/enhancements/tree/master/keps/sig-cli/5295-kyaml>
- Go 1.24 릴리스 노트(crypto/tls): <https://go.dev/doc/go1.24#cryptotlspkgcryptotls>

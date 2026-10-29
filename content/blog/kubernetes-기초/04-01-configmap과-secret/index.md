---
title: '[K8s 기초] ConfigMap과 Secret: 설정을 이미지 밖으로 빼기'
date: '2024-12-29T15:20:00+09:00'
categories:
- Kubernetes
tags:
- kubernetes
- configmap
- secret
- environment-variable
- volume
- base64
- immutable
- 12-factor
- 설정과 스토리지
series:
- Kubernetes 기초
series_order: 12
---

개발 환경과 운영 환경에서 DB 주소만 다른데 이미지를 두 번 빌드하는 건 이상하다. 쿠버네티스는 설정은 ConfigMap, 비밀값은 Secret에 따로 두고 파드가 시작할 때 넣어 주는 방식을 쓴다. 넣는 방법 세 가지와, 값을 바꿨을 때 파드가 언제 알아채는지를 확인했다.

## 요약

- 이미지에는 코드만 두고, 환경마다 다른 값은 ConfigMap(일반 설정)과 Secret(비밀값)으로 뺀다. 같은 이미지를 개발·운영에 그대로 쓴다.
- 파드에 넣는 방법은 키 하나를 환경 변수로, 전체를 환경 변수로(envFrom), 파일로(볼륨) 세 가지다.
- 환경 변수로 넣은 값은 ConfigMap을 바꿔도 파드를 다시 시작하기 전까지 그대로다. 볼륨으로 넣은 파일은 잠시 뒤 바뀐다.
- Secret 값은 base64로 인코딩돼 있을 뿐 암호화가 아니다. etcd에도 기본으로 암호화 없이 저장된다.
- 바뀌면 안 되는 설정은 immutable: true로 잠글 수 있다.

## 1. 왜 설정을 밖으로 빼나

| 이미지 안에 설정을 넣으면 | ConfigMap·Secret으로 빼면 |
|---|---|
| 환경마다 이미지를 따로 빌드한다 | 같은 이미지에 환경별 값만 바꿔 넣는다 |
| 값 하나 바꾸려고 다시 빌드·배포한다 | 오브젝트만 고치고 파드를 다시 시작한다 |
| 비밀번호가 이미지 레이어에 남는다 | 비밀값은 Secret으로 따로 관리한다 |

## 2. 만들고 넣기

```bash
kubectl create configmap app-config --from-literal=MODE=prod --from-literal=LOG_LEVEL=info
echo 'greeting=hello' > app.properties
kubectl create configmap app-file --from-file=app.properties
kubectl create secret generic db-cred --from-literal=user=app --from-literal=password='s3cr3t'
kubectl get configmap app-config -o yaml
kubectl get secret db-cred -o yaml                 # data 값이 base64로 보인다
```

{{< mermaid >}}
flowchart LR
  CM["ConfigMap app-config<br>MODE, LOG_LEVEL"] -->|"① valueFrom: 키 하나"| E1["환경 변수 APP_MODE"]
  CM -->|"② envFrom: 전부"| E2["환경 변수 MODE, LOG_LEVEL"]
  CF["ConfigMap app-file<br>app.properties"] -->|"③ volume: 파일로"| F["/etc/app/app.properties"]
  S["Secret db-cred<br>user, password"] -->|"① valueFrom: 키 하나"| E3["환경 변수 DB_PASSWORD"]
  E1 --> P["파드"]
  E2 --> P
  F --> P
  E3 --> P
{{< /mermaid >}}

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: config-demo
spec:
  containers:
  - name: app
    image: busybox:1.36
    command: ["sh", "-c", "env | sort; cat /etc/app/app.properties; sleep 3600"]
    env:
    - name: APP_MODE
      valueFrom:
        configMapKeyRef:
          name: app-config
          key: MODE
    - name: DB_PASSWORD
      valueFrom:
        secretKeyRef:
          name: db-cred
          key: password
    envFrom:
    - configMapRef:
        name: app-config
    volumeMounts:
    - name: props
      mountPath: /etc/app
  volumes:
  - name: props
    configMap:
      name: app-file
```

```bash
kubectl apply -f config-demo.yaml
kubectl logs config-demo | grep -E 'APP_MODE|MODE|LOG_LEVEL|DB_PASSWORD|greeting'
```

## 3. 값을 바꾸면 언제 바뀌나

ConfigMap 두 개를 고친 뒤 1분쯤 지켜봤다.

```bash
kubectl create configmap app-config --from-literal=MODE=dev --from-literal=LOG_LEVEL=debug --dry-run=client -o yaml | kubectl apply -f -
echo 'greeting=bye' > app.properties
kubectl create configmap app-file --from-file=app.properties --dry-run=client -o yaml | kubectl apply -f -
kubectl exec config-demo -- printenv MODE              # 그대로 prod
kubectl exec config-demo -- cat /etc/app/app.properties   # 잠시 뒤 greeting=bye
```

| 넣는 방법 | ConfigMap을 바꾸면 |
|---|---|
| 환경 변수(valueFrom, envFrom) | 바뀌지 않는다. 파드를 다시 만들어야 한다(디플로이먼트면 kubectl rollout restart) |
| 볼륨 파일 | kubelet이 주기적으로 확인해서 잠시 뒤 바뀐다. 앱이 파일을 다시 읽어야 반영된다 |
| 볼륨 + subPath | 바뀌지 않는다 |

## 4. Secret은 '비밀 보관함'이 아니다

```bash
kubectl get secret db-cred -o jsonpath='{.data.password}' | base64 -d     # s3cr3t
```

이걸 해 보고 조금 놀랐다. base64는 누구나 풀 수 있는 인코딩이다. Secret이 ConfigMap과 다른 점은 이름과 다루는 방식이다.

| 항목 | 내용 |
|---|---|
| 저장 | 기본으로 etcd에 암호화 없이 저장된다. API 서버에 저장 시 암호화(EncryptionConfiguration)를 켤 수 있다 |
| 접근 | RBAC으로 get secret 권한을 좁혀야 한다. 그 네임스페이스에 파드를 만들 수 있는 사람은 Secret을 마운트해서 읽을 수 있다 |
| 노드 | 볼륨으로 넣은 Secret은 노드의 메모리 파일시스템(tmpfs)에 둔다 |
| 크기 | 하나에 1MiB까지 |
| 타입 | Opaque(일반), kubernetes.io/tls, kubernetes.io/dockerconfigjson 등 |

운영에서는 Git에 Secret YAML을 그대로 올리지 않고, 외부 비밀 저장소(AWS Secrets Manager, Vault 등)와 연결하는 도구를 쓴다고 한다.

> **쉬운 설명**
>
> 이미지가 요리 레시피라면 ConfigMap은 '오늘은 덜 맵게' 같은 주문 메모다. 레시피를 고치지 않고 메모만 바꿔 같은 요리를 지점마다 다르게 낸다. 메모를 주방장에게 말로 전하면(환경 변수) 주방장이 출근할 때 들은 대로만 하고, 벽에 붙여 두면(볼륨) 바뀐 메모를 곧 본다. Secret은 금고 비밀번호를 적은 메모인데, 봉투가 반투명(base64)이라 봉투를 들 수 있는 사람은 다 읽는다. 그래서 봉투를 누가 들 수 있는지(RBAC)를 따로 지켜야 한다.

## 헷갈렸던 것들

- 환경 변수로 넣은 값은 ConfigMap을 바꿔도 그대로다. rollout restart가 필요하다.
- Secret의 data는 base64다. YAML에 평문으로 쓰고 싶으면 stringData를 쓴다.
- base64는 암호화가 아니다.
- 참조한 ConfigMap이나 키가 없으면 파드가 시작하지 못한다. 없어도 되는 값이면 optional: true를 준다.
- ConfigMap과 파드는 같은 네임스페이스에 있어야 한다.

## 용어 정리

| 용어 | 뜻 |
|---|---|
| ConfigMap | 일반 설정 값을 키-값으로 담는 오브젝트 |
| Secret | 비밀번호, 토큰, 인증서 같은 민감한 값을 담는 오브젝트 |
| envFrom | ConfigMap·Secret의 모든 키를 환경 변수로 넣는 필드 |
| base64 | 바이너리를 문자로 바꾸는 인코딩. 암호화가 아니다 |
| immutable | 만든 뒤 값을 못 바꾸게 잠그는 필드 |
| 저장 시 암호화 | API 서버가 etcd에 쓰기 전에 Secret을 암호화하는 설정 |

## 참고 자료

- Kubernetes 문서, ConfigMap: <https://kubernetes.io/docs/concepts/configuration/configmap/>
- Kubernetes 문서, ConfigMap을 쓰도록 파드 구성: <https://kubernetes.io/docs/tasks/configure-pod-container/configure-pod-configmap/>
- Kubernetes 문서, Secret: <https://kubernetes.io/docs/concepts/configuration/secret/>
- Kubernetes 문서, Secret 모범 사례: <https://kubernetes.io/docs/concepts/security/secrets-good-practices/>
- Kubernetes 문서, 저장된 Secret 데이터 암호화: <https://kubernetes.io/docs/tasks/administer-cluster/encrypt-data/>

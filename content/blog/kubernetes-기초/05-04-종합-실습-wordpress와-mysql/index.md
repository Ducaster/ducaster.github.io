---
title: '[K8s 기초] 종합 실습: WordPress와 MySQL을 처음부터 올려 보기'
date: '2025-02-05T21:30:00+09:00'
categories:
- Kubernetes
tags:
- kubernetes
- wordpress
- mysql
- deployment
- service
- secret
- pvc
- ingress
- probe
- 종합실습
- 보안과 운영 맛보기
series:
- Kubernetes 기초
series_order: 17
---

기초 마지막 글. 지금까지 배운 것을 한 번에 써 보려고, 공식 튜토리얼의 WordPress·MySQL 예제를 가져와 조금 바꿔서 올렸다. 튜토리얼은 LoadBalancer 서비스를 쓰는데, kind에서는 인그레스로 바꾸고 프로브와 자원 설정을 더했다. 다 올린 뒤 파드를 지워도 글이 남는지까지 확인했다.

## 요약

- 쓴 오브젝트: 네임스페이스, Secret, PVC 두 개, 디플로이먼트 두 개, 서비스 두 개, 인그레스 하나.
- MySQL은 데이터 디렉터리를 PVC에 두고, 서비스는 헤드리스로 만들어 wordpress-mysql이라는 이름으로 찾게 했다.
- MySQL 디플로이먼트는 Recreate 전략을 썼다. RWO 볼륨 하나를 두 파드가 동시에 잡으면 안 되기 때문이다.
- 비밀번호는 Secret 하나를 두 파드가 환경 변수로 읽는다.
- 파드를 지우고 다시 만들어도 글과 DB가 PVC에 남아 있었다.

## 1. 전체 그림

{{< mermaid >}}
flowchart TB
  B["브라우저 http://localhost/"] -->|":80"| I["Ingress wp<br>/ → wordpress:80"]
  I --> SW["Service wordpress"]
  SW --> PW["wordpress 파드<br>(Deployment)"]
  PW -->|"DB 접속"| SM["Service wordpress-mysql<br>(헤드리스)"]
  SM --> PM["mysql 파드<br>(Deployment, Recreate)"]
  PW -.->|"/var/www/html"| VW[("PVC wp-pv-claim")]
  PM -.->|"/var/lib/mysql"| VM[("PVC mysql-pv-claim")]
  S["Secret mysql-pass"] -.->|"비밀번호"| PW
  S -.->|"비밀번호"| PM
{{< /mermaid >}}

| 쓴 것 | 어디서 배웠나 |
|---|---|
| Namespace | 오브젝트·네임스페이스 |
| Secret, 환경 변수로 넣기 | ConfigMap과 Secret |
| PVC, 동적 프로비저닝 | 볼륨·PV·PVC |
| Deployment, Recreate 전략 | 레플리카셋과 디플로이먼트 |
| Service, 헤드리스 서비스, DNS 이름 | 서비스, DNS |
| Ingress | 인그레스 |
| readinessProbe, requests·limits | 리소스 요청과 프로브 |

## 2. MySQL

```bash
kubectl create namespace wp
kubectl -n wp create secret generic mysql-pass --from-literal=password='change-me-please'
```

```yaml
apiVersion: v1
kind: Service
metadata:
  name: wordpress-mysql
  namespace: wp
spec:
  clusterIP: None
  selector:
    app: wordpress
    tier: mysql
  ports:
  - port: 3306
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: mysql-pv-claim
  namespace: wp
spec:
  accessModes: ["ReadWriteOnce"]
  resources:
    requests:
      storage: 2Gi
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: wordpress-mysql
  namespace: wp
spec:
  strategy:
    type: Recreate
  selector:
    matchLabels:
      app: wordpress
      tier: mysql
  template:
    metadata:
      labels:
        app: wordpress
        tier: mysql
    spec:
      containers:
      - name: mysql
        image: mysql:8.0
        env:
        - name: MYSQL_ROOT_PASSWORD
          valueFrom:
            secretKeyRef:
              name: mysql-pass
              key: password
        - name: MYSQL_DATABASE
          value: wordpress
        - name: MYSQL_USER
          value: wordpress
        - name: MYSQL_PASSWORD
          valueFrom:
            secretKeyRef:
              name: mysql-pass
              key: password
        ports:
        - containerPort: 3306
        readinessProbe:
          exec:
            command: ["mysqladmin", "ping", "-h", "127.0.0.1"]
          initialDelaySeconds: 10
          periodSeconds: 5
        resources:
          requests:
            cpu: 100m
            memory: 512Mi
          limits:
            memory: 1Gi
        volumeMounts:
        - name: mysql-data
          mountPath: /var/lib/mysql
      volumes:
      - name: mysql-data
        persistentVolumeClaim:
          claimName: mysql-pv-claim
```

MySQL은 처음 뜰 때 데이터 디렉터리를 초기화하느라 시간이 걸려서, readiness가 성공하기까지 READY 0/1로 한동안 있었다. mysqladmin ping은 서버가 떠 있으면 비밀번호 없이도 성공으로 끝나서 프로브로 쓰기 좋았다.

## 3. WordPress와 인그레스

```yaml
apiVersion: v1
kind: Service
metadata:
  name: wordpress
  namespace: wp
spec:
  selector:
    app: wordpress
    tier: frontend
  ports:
  - port: 80
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: wp-pv-claim
  namespace: wp
spec:
  accessModes: ["ReadWriteOnce"]
  resources:
    requests:
      storage: 1Gi
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: wordpress
  namespace: wp
spec:
  strategy:
    type: Recreate
  selector:
    matchLabels:
      app: wordpress
      tier: frontend
  template:
    metadata:
      labels:
        app: wordpress
        tier: frontend
    spec:
      containers:
      - name: wordpress
        image: wordpress:6.7-apache
        env:
        - name: WORDPRESS_DB_HOST
          value: wordpress-mysql
        - name: WORDPRESS_DB_USER
          value: wordpress
        - name: WORDPRESS_DB_PASSWORD
          valueFrom:
            secretKeyRef:
              name: mysql-pass
              key: password
        ports:
        - containerPort: 80
        readinessProbe:
          httpGet:
            path: /
            port: 80
          initialDelaySeconds: 10
          periodSeconds: 5
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            memory: 512Mi
        volumeMounts:
        - name: wp-data
          mountPath: /var/www/html
      volumes:
      - name: wp-data
        persistentVolumeClaim:
          claimName: wp-pv-claim
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: wp
  namespace: wp
spec:
  ingressClassName: nginx
  rules:
  - http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: wordpress
            port:
              number: 80
```

```bash
kubectl apply -f mysql.yaml -f wordpress.yaml
kubectl -n wp get pods,svc,pvc,ingress
kubectl -n wp rollout status deployment/wordpress
curl -sI localhost/ | head -3          # 302 → /wp-admin/install.php
```

브라우저로 localhost에 들어가니 WordPress 설치 화면이 나왔다. 사이트 이름과 관리자 계정을 정하고 글을 하나 썼다. WORDPRESS_DB_HOST에 서비스 이름만 적었는데도 붙은 건, 같은 네임스페이스라 DNS search 도메인이 뒤를 붙여 주기 때문이다.

## 4. 지워도 남는지

```bash
kubectl -n wp delete pod -l tier=mysql
kubectl -n wp delete pod -l tier=frontend
kubectl -n wp get pods -w              # 둘 다 새 이름으로 다시 뜬다
```

새 파드가 Ready가 된 뒤 새로 고침하니 아까 쓴 글이 그대로 있었다. 글과 설정은 MySQL의 /var/lib/mysql에, 업로드 파일과 테마는 /var/www/html에 있고, 둘 다 PVC라서다.

| 해 본 것 | 결과 | 이유 |
|---|---|---|
| mysql 파드 삭제 | 글이 남는다 | 데이터 디렉터리가 PVC |
| wordpress 이미지 태그 변경 | Recreate라 잠깐 끊긴 뒤 새 파드가 뜬다 | RWO 볼륨을 두 파드가 같이 잡지 않게 |
| 네임스페이스 wp 삭제 | 전부 사라진다 | PVC도 네임스페이스 안 오브젝트이고 회수 정책이 Delete |

> **쉬운 설명**
>
> 지금까지는 부품을 하나씩 만져 봤다면, 이번엔 가구 한 세트를 조립했다. WordPress는 가게 카운터, MySQL은 창고 장부다. 손님은 정문(인그레스)으로 들어와 카운터(wordpress 서비스)로 가고, 카운터 직원은 장부 담당(wordpress-mysql)을 이름으로 불러 기록을 남긴다. 직원이 바뀌어도(파드 재생성) 장부와 진열대 물건은 창고(PVC)에 있어서 그대로다. 금고 비밀번호(Secret)는 두 사람이 같은 쪽지를 본다.

## 헷갈렸던 것들

- RWO 볼륨을 쓰는 디플로이먼트는 롤링 업데이트 중에 새 파드가 볼륨을 못 잡아 멈출 수 있다. 하나만 도는 앱이면 Recreate가 안전하다.
- MySQL처럼 무거운 앱은 처음 뜰 때 오래 걸린다. readiness 없이 서비스에 바로 넣으면 WordPress가 연결 오류를 낸다.
- DB_HOST에 서비스 이름만 써도 되는 건 같은 네임스페이스라서다.
- 네임스페이스를 지우면 PVC와 데이터까지 지워진다.
- 실습용 비밀번호를 YAML에 넣지 않고 kubectl create secret으로 만들었다. Git에 올릴 파일에 비밀번호가 들어가지 않게 하려는 것이다.

## 용어 정리

| 용어 | 뜻 |
|---|---|
| Recreate 전략 | 옛 파드를 모두 지운 뒤 새 파드를 만드는 업데이트 방식 |
| 헤드리스 서비스 | 가상 IP 없이 DNS로 파드 IP를 돌려주는 서비스 |
| 동적 프로비저닝 | PVC를 만들면 StorageClass가 PV를 자동으로 만들어 주는 것 |
| readinessProbe | 준비가 안 된 파드를 서비스에서 빼 두는 검사 |

## 복습 문제

**1.** wordpress 디플로이먼트의 복제본을 2개로 늘리면 무슨 일이 생기는지 예상하고 확인해라.

**2.** MySQL 비밀번호를 바꾸려면 무엇을 고치고 무엇을 다시 시작해야 하는지 적어라.

**3.** wp 네임스페이스 전체를 지운 뒤 같은 YAML로 다시 올리면 예전 글이 보이는지 확인해라.

## 답과 풀이

1. 두 번째 파드가 다른 노드에 배치되면 RWO PVC를 붙이지 못해 ContainerCreating에 머문다(Multi-Attach 오류). 같은 노드면 뜨지만, 여러 파드가 같은 파일을 쓰는 건 RWX 스토리지가 있어야 안전하다.

```bash
kubectl -n wp scale deployment wordpress --replicas=2
kubectl -n wp get pods -o wide
kubectl -n wp describe pod <새 파드> | tail -5
```

2. Secret만 바꾸면 안 된다. MySQL은 처음 초기화할 때만 MYSQL_PASSWORD를 쓰기 때문에, DB 안의 사용자 비밀번호도 바꾸고, 환경 변수는 파드를 다시 시작해야 반영된다.

3. 보이지 않는다. 네임스페이스와 함께 PVC가 지워지고 회수 정책이 Delete라 데이터도 지워졌다.

## 참고 자료

- Kubernetes 튜토리얼, WordPress와 MySQL 배포: <https://kubernetes.io/docs/tutorials/stateful-application/mysql-wordpress-persistent-volume/>
- Docker Hub, mysql 공식 이미지: <https://hub.docker.com/_/mysql>
- Docker Hub, wordpress 공식 이미지: <https://hub.docker.com/_/wordpress>
- Kubernetes 문서, 디플로이먼트 전략: <https://kubernetes.io/docs/concepts/workloads/controllers/deployment/#strategy>

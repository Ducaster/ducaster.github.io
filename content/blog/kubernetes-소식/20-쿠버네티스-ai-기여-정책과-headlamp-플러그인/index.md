---
title: '[K8s 소식] 쿠버네티스의 AI 기여 정책, 그리고 Headlamp 플러그인 세 개'
date: '2026-06-27T15:00:00+09:00'
categories:
- Kubernetes
tags:
- kubernetes
- open-source
- ai-policy
- code-review
- headlamp
- cluster-api
- volcano
- knative
- gang-scheduling
- 소식
series:
- Kubernetes 소식
series_order: 20
---

6월은 큰 릴리스 없이 조용했다. 대신 읽을거리가 둘 있었다. 하나는 'AI 시대의 오픈소스 유지보수' 글로, 쿠버네티스 프로젝트가 AI로 만든 기여를 어떻게 받기로 했는지 정리한 것이다. 다른 하나는 6월 25일 하루에 세 편이 한꺼번에 올라온 Headlamp 플러그인 소개다. 지난번 Dashboard가 보관됐다는 소식 바로 뒤라 Headlamp 쪽 생태계가 어떻게 커지는지 보였다.

## 요약

- 쿠버네티스 AI 정책을 줄이면 '공개하고, 사람이 책임진다'다. PR 설명에 AI 도움을 받았다고 적고, AI를 공동 작성자로 올리거나 assisted-by 같은 트레일러를 다는 건 금지다.
- 리뷰어는 사람과 대화하길 기대한다. 리뷰 댓글에 AI로 답하면 안 되고, 바뀐 코드를 직접 설명하지 못하면 PR이 닫힌다.
- 유지보수 쪽에서는 AI 리뷰 도구를 시험 중이다. Copilot은 기여자 라이선스 문제로 한계가 있었고, 2026년 중반에 일부 프로젝트에 CodeRabbit을 들였다.
- Headlamp에 Cluster API, Volcano, Knative 플러그인이 나왔다. 각 프로젝트의 CRD 관계를 지도(map) 화면으로 보여 주고, 스케일이나 일시 정지, 트래픽 분할 같은 동작을 RBAC 범위 안에서 UI로 할 수 있다.

## 1. 쿠버네티스의 AI 기여 정책

글쓴이는 AI 덕분에 패치를 보내는 사람이 늘어난 건 좋은 일이지만, 코드를 만드는 속도만 빨라졌지 유지보수는 거의 나아지지 않았다고 짚었다. 실제로 AI 사용을 두고 PR마다 논쟁이 벌어져서 정책부터 만들었다고 한다. 작년 11월에 정리한 Ingress NGINX가 한두 명의 유지보수자로 버티다 은퇴한 걸 떠올리면, 유지보수자의 시간을 지키는 게 왜 중요한지 이해가 됐다.

| 원칙 | 내용 |
|---|---|
| 공개 | AI 도움을 받았으면 PR 설명에 적는다. 'This PR was written in part with the assistance of generative AI' 정도면 된다 |
| 사람의 책임 | 모든 변경의 책임은 사람에게 있다. AI를 커밋 공동 작성자로 올리기, AI 공동 서명, assisted-by나 co-developed 트레일러 모두 금지 |
| 공동 작성자 CLA 검사 | 공동 작성자까지 CLA 검사를 켰다. AI 에이전트는 CLA에 서명할 수 없으니 리뷰어가 알아챌 수 있다 |
| 사람과의 대화 | 리뷰 댓글에 AI로 답하지 않는다. 바뀐 내용을 직접 설명하지 못하면 PR을 닫는다 |
| 검증 의무 | 동작하는 것만으로는 부족하다. 왜 동작하는지 알고 유지보수할 수 있어야 한다 |

{{< mermaid >}}
flowchart TB
  A["PR 작성<br>AI 도움 받았으면<br>설명에 공개"] --> B["CLA 검사<br>공동 작성자 포함"]
  B --> C["AI 리뷰 도구 1차 지적<br>(일부 프로젝트)"]
  C --> D["사람 리뷰어와<br>사람 기여자의 대화"]
  D -->|"직접 설명 가능"| E["머지"]
  D -->|"설명 못 함"| F["PR 닫힘"]
{{< /mermaid >}}

| AI 리뷰 도구 | 경험 |
|---|---|
| 도입 절차 | 새 AI 도구를 들이는 절차부터 문서로 만들었다. kubernetes-sigs 저장소에서 직접 써 볼 유지보수자가 있는지가 중요한 기준이다 |
| GitHub Copilot | CNCF가 유지보수자에게 제공해 먼저 퍼졌다. 그런데 기여자에게 라이선스가 없으면 리뷰를 요청할 수 없어서, 유지보수자가 매번 요청해야 했다 |
| CodeRabbit | 2026년 중반 일부 프로젝트에 도입했다. 조정이 필요했지만 반응은 좋았다고 한다. agent-sandbox는 AI 리뷰 지적이 남아 있다는 라벨을 PR에 붙여 품질 관문처럼 쓴다 |
| 시험 중인 프로젝트 | Kueue, JobSet, Agent Sandbox |

'직접 설명하지 못하면 닫는다'는 규칙은 공부에도 그대로 맞는 말 같다. 이 블로그에 올리는 YAML도 내가 한 줄씩 설명할 수 있는 것만 남기려고 한다.

## 2. Headlamp 플러그인 세 개

지난번에 Dashboard에서 Headlamp로 넘어가는 이유 중 하나가 플러그인이었는데, 바로 세 개가 소개됐다. 공통점은 kubectl로 CRD 여러 개를 오가며 머릿속으로 이어 붙이던 관계를 한 화면의 지도와 상세 페이지로 보여 준다는 것이다.

| 플러그인 | 대상 프로젝트 | 보여 주는 것 | UI에서 할 수 있는 것 |
|---|---|---|---|
| Cluster API | 쿠버네티스 클러스터 자체를 쿠버네티스 오브젝트로 만드는 CAPI | Cluster, KubeadmControlPlane, MachineDeployment, MachineSet, Machine, MachinePool의 상태와 소유 관계, 부트스트랩 설정(KubeadmConfig), v1beta1과 v1beta2 모두 | MachineDeployment, MachineSet 스케일. 문제가 보이면 고치는 방법과 진단 명령을 안내 |
| Volcano | 배치, AI/ML용 스케줄러 | Job, Queue, PodGroup과 파드 사이 지도. Queue의 용량과 할당, PodGroup의 진행 상태와 막힌 이유 | Job 일시 정지와 재개, 잡의 모든 파드 로그 보기 |
| Knative | 서버리스 | KService, Revision, DomainMapping 지도. 실제로 적용되는 자동 확장 설정(서비스 어노테이션과 클러스터 기본값 중 무엇인지) | 리비전 간 트래픽 분할 편집(합이 100%인지 검사), 재배포, 파드 재시작 |

Volcano의 PodGroup이 반가웠다. 1월에 정리한 v1.35 갱 스케줄링과 4월 v1.36의 PodGroup API가 쿠버네티스 본체에 들어온 개념인데, Volcano는 오래전부터 같은 이름으로 같은 일을 해 왔다. 플러그인의 PodGroup 화면이 '최소 몇 개가 모여야 시작하는데 지금 몇 개인지'를 보여 준다니, 본체 PodGroup도 이런 화면이 있으면 좋겠다.

세 플러그인 모두 Prometheus 플러그인과 같이 쓰면 상세 페이지 안에 지표 그래프가 붙는다. Knative 플러그인은 Headlamp 데스크톱의 플러그인 카탈로그에서 검색해 설치하고, 글을 쓴 시점 버전은 0.3.0-beta였다. 공식 글들도 플러그인이 kubectl이나 각 프로젝트 CLI를 대신하려는 건 아니고, 자동화는 CLI로 하되 문제를 찾을 때 맥락을 한곳에 모아 주는 용도라고 했다.

## 내 클러스터에서 확인할 것

```bash
kubectl get crd -o name | grep -E 'cluster.x-k8s.io|volcano.sh|serving.knative.dev' | sort
kubectl auth can-i --list -n demo        # Headlamp에서 보일 동작은 결국 이 권한 범위다
```

- 첫 줄에 나오는 CRD 그룹이 있으면 그에 맞는 Headlamp 플러그인을 써 볼 만하다.
- Headlamp의 편집, 스케일 버튼은 내 RBAC 권한대로만 동작한다. UI를 팀에 열어 줄 때 권한부터 정리한다.
- 쿠버네티스 쪽 저장소에 PR을 낼 일이 있으면, AI 도움을 받은 부분을 설명에 적고 커밋 트레일러에는 AI를 넣지 않는다.

> **쉬운 설명**
>
> 쿠버네티스의 AI 정책은 조별 과제 규칙과 비슷하다. 계산기(AI)를 써도 되지만 '계산기 썼어요'라고 밝히고, 발표 때 교수님 질문에는 내가 직접 답해야 한다. 계산기를 조원 명단에 올릴 수는 없다. 답을 설명하지 못하면 과제는 반려된다. Headlamp 플러그인은 박물관 안내 지도와 같다. 전시실(CRD)마다 따로 돌아다니며 관계를 외우는 대신, 지도 한 장에서 '이 작품은 저 방의 연작'이라는 걸 바로 보고, 필요하면 그 자리에서 안내원에게(UI 버튼) 부탁할 수 있다.

## 용어 정리

| 용어 | 뜻 |
|---|---|
| CLA | 기여자 라이선스 동의서. 기여하기 전에 서명해야 한다 |
| 커밋 트레일러 | 커밋 메시지 끝의 Signed-off-by:, Co-authored-by: 같은 줄 |
| Cluster API | 쿠버네티스 클러스터의 생성, 업그레이드, 삭제를 쿠버네티스 오브젝트로 선언하는 하위 프로젝트 |
| Volcano | 큐, 우선순위, 갱 스케줄링을 제공하는 배치 스케줄러 |
| Knative | 쿠버네티스 위 서버리스 플랫폼. KService, Revision 단위로 배포와 트래픽 분할을 한다 |
| Headlamp 플러그인 | Headlamp UI에 새 리소스 화면과 동작을 더하는 확장 |

## 참고 자료

- Kubernetes 블로그, Open source maintainership in the age of AI: <https://kubernetes.io/blog/2026/06/26/open-source-maintainership-in-the-age-of-ai/>
- Kubernetes 블로그, Introducing the Cluster API plugin for Headlamp: <https://kubernetes.io/blog/2026/06/25/headlamp-cluster-api-plugin/>
- Kubernetes 블로그, Inspect Volcano workloads faster with Headlamp: <https://kubernetes.io/blog/2026/06/25/visual-context-volcano-headlamp-plugin/>
- Kubernetes 블로그, Introducing the Headlamp plugin for Knative: <https://kubernetes.io/blog/2026/06/25/headlamp-knative-plugin/>
- Headlamp: <https://headlamp.dev/>
